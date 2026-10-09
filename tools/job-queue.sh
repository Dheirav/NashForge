#!/usr/bin/env bash
# A job queue that keeps the machine busy between fixtures without anyone starting the next job by hand.
#   tools/job-queue.sh run    [dir]            the runner (detach it: setsid nohup tools/job-queue.sh run DIR)
#   tools/job-queue.sh status [dir] [--watch]  what runs, what waits and why, what finished
# dir defaults to ~/pokerbot-scratch/queue. Files there:
#   queue.txt    one job a line, `name|slots|est_min|mem_mb|on_window|after|command`; append at any time.
#                slots: cores it uses; est_min: wall time, used only to decide whether it fits before the next
#                window (never shown as an ETA); mem_mb: what it needs free when it starts; on_window: `stop`
#                (SIGSTOP the job's process group until the window ends: trainers, which run no `timeout`) or
#                `kill` (kill it and queue it again: measurements, whose scripts skip finished results); after:
#                comma list of job names that must have exited 0, or `sh:<test>`, or empty.
#   windows.txt  `start|end|pid|label`, local time `YYYY-MM-DD HH:MM`. Nothing starts inside a window, nothing
#                starts that would not finish before the next one (est_min x 1.3), and a window with a pid ends
#                early once that pid has exited (a fixture timer).
# A job starts only when max(load, the queue's own slots) + its slots <= 8, MemAvailable less what running jobs have yet to grow into leaves 1,200 MB after its
# mem_mb, and two minutes have passed since the last start, so load and memory have caught up. In a window, if
# MemAvailable falls under 900 MB, stopped jobs are killed and queued again: the fixture bot comes first. The
# runner exits when <dir>/stop exists or after 13 Oct. GAP and TICK (seconds) override the start gap and the tick, for tests.
set -u
cmd=${1:-status}; Q=${2:-$HOME/pokerbot-scratch/queue}; [ "${2:-}" = "--watch" ] && Q=$HOME/pokerbot-scratch/queue
S=$Q/state; mkdir -p "$S" "$Q/logs"
stamp() { echo "$(date '+%F %T') $*" >> "$Q/runner.log"; }
jobs_lines() { grep -vE '^\s*(#|$)' "$Q/queue.txt" 2>/dev/null; }
field() { echo "$1" | cut -d'|' -f"$2"; }
window_now() {  # prints the label of the window we are in, if any
  local now s e p lab; now=$(date +%s)
  while IFS='|' read -r s e p lab; do [ -z "$s" ] && continue; case $s in \#*) continue;; esac
    s=$(date -d "$s" +%s) e=$(date -d "$e" +%s)
    if [ "$now" -ge "$s" ] && [ "$now" -lt "$e" ] && { [ -z "$p" ] || kill -0 "$p" 2>/dev/null; }; then echo "$lab"; return; fi
  done < "$Q/windows.txt"; }
next_window() {  # epoch of the next window start, or empty
  local now s e p lab best=""; now=$(date +%s)
  while IFS='|' read -r s e p lab; do [ -z "$s" ] && continue; case $s in \#*) continue;; esac
    s=$(date -d "$s" +%s); [ "$s" -gt "$now" ] && { [ -z "$best" ] || [ "$s" -lt "$best" ]; } && best=$s
  done < "$Q/windows.txt"; echo "$best"; }
running() { local f n; for f in "$S"/*.pid; do [ -e "$f" ] || continue; n=$(basename "$f" .pid); [ -e "$S/$n.exit" ] || echo "$n"; done; }
# Names first, then an optional `sh:<test>` that runs to the end of the field (9 Oct: a mixed list was read as one
# job named "sh:[", which never finished, so the job waited forever).
deps_ok() { local names=$1 t="" d; [ -z "$names" ] && return 0
  case $names in *sh:*) t=${names#*sh:}; names=${names%%sh:*}; names=${names%,};; esac
  for d in ${names//,/ }; do [ "$(cat "$S/$d.exit" 2>/dev/null)" = 0 ] || return 1; done
  [ -z "$t" ] || bash -c "$t" >/dev/null 2>&1; }
# Memory a running job was given but has not grown into yet: a trainer loading its tables looks small for minutes
# (9 Oct 04:52, the second balanced trainer started beside the first, both reached 2.3 GB, and memory ran short).
pending_mem() { local n g need rss tot=0
  for n in $(running); do need=$(field "$(jobs_lines | grep "^$n|")" 4); g=$(cat "$S/$n.pid")
    rss=$(ps -eo pgid=,rss= | awk -v g="$g" '$1 == g { s += $2 } END { print int(s / 1024) }')
    [ "$need" -gt "$rss" ] && tot=$(( tot + need - rss )); done; echo $tot; }
requeue() { rm -f "$S/$1.pid" "$S/$1.start" "$S/$1.paused" "$S/$1.end" "$S/$1.exit"; }
start_job() { local n=$1 c=$2
  date +%s > "$S/$n.start"; stamp "start $n"
  setsid bash -c 'echo $$ > "$4"; nice -n 10 bash -c "$1" > "$2" 2>&1; rc=$?; date +%s > "$5"; echo $rc > "$3"' \
    _ "$c" "$Q/logs/$n.log" "$S/$n.exit" "$S/$n.pid" "$S/$n.end" < /dev/null > /dev/null 2>&1 &
  sleep 1; }

run() {
  echo $$ > "$Q/runner.pid"; stamp "runner up (pid $$)"; local last=0
  while :; do
    [ -e "$Q/stop" ] && { stamp "stop file, runner exits"; exit 0; }
    [ "$(date +%Y%m%d)" -gt 20261013 ] && { stamp "past 13 Oct, runner exits"; exit 0; }
    for f in "$S"/*.exit; do [ -e "$f" ] || continue; n=$(basename "$f" .exit)
      [ -e "$S/$n.reported" ] || { stamp "end $n: exit $(cat "$f")"; touch "$S/$n.reported"; }; done
    win=$(window_now); avail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
    if [ -n "$win" ]; then
      for n in $(running); do line=$(jobs_lines | grep "^$n|"); mode=$(field "$line" 5); g=$(cat "$S/$n.pid")
        if [ "$mode" = stop ] && [ ! -e "$S/$n.paused" ]; then kill -STOP -- -"$g" 2>/dev/null; touch "$S/$n.paused"; stamp "paused $n for: $win"
        elif [ "$mode" = kill ]; then kill -- -"$g" 2>/dev/null; sleep 2; requeue "$n"; stamp "killed $n for: $win (queued again)"; fi
        if [ -e "$S/$n.paused" ] && [ "$avail" -lt 900 ]; then kill -CONT -- -"$g" 2>/dev/null; kill -- -"$g" 2>/dev/null; sleep 2
          requeue "$n"; stamp "killed paused $n: $avail MB free in the window (queued again)"; fi
      done; echo "in window: $win" > "$S/reasons"; sleep ${TICK:-20}; continue
    fi
    for n in $(running); do [ -e "$S/$n.paused" ] && { kill -CONT -- -"$(cat "$S/$n.pid")" 2>/dev/null; rm -f "$S/$n.paused"; stamp "resumed $n"; }; done
    now=$(date +%s); nw=$(next_window); : > "$S/reasons.tmp"
    own=0; for n in $(running); do own=$(( own + $(field "$(jobs_lines | grep "^$n|")" 2) )); done
    load=$(awk '{print int($1 + 0.5)}' /proc/loadavg); used=$(( load > own ? load : own )); avail=$(( avail - $(pending_mem) ))
    if [ $(( now - last )) -ge ${GAP:-120} ]; then
      while IFS= read -r line; do n=$(field "$line" 1); [ -e "$S/$n.pid" ] && continue
        sl=$(field "$line" 2) est=$(field "$line" 3) mem=$(field "$line" 4) aft=$(field "$line" 6) c=$(echo "$line" | cut -d'|' -f7-)
        if ! deps_ok "$aft"; then echo "$n: waiting on ${aft:0:60}" >> "$S/reasons.tmp"; continue; fi
        if [ -n "$nw" ] && [ $(( now + est * 78 )) -gt "$nw" ]; then echo "$n: would not finish before the next window" >> "$S/reasons.tmp"; continue; fi
        if [ $(( used + sl )) -gt 8 ]; then echo "$n: needs $sl cores, $used busy" >> "$S/reasons.tmp"; continue; fi
        if [ $(( avail - mem )) -lt 1200 ]; then echo "$n: needs $mem MB plus 1,200 spare, $avail free" >> "$S/reasons.tmp"; continue; fi
        start_job "$n" "$c"; last=$now; break
      done < <(jobs_lines)
      mv "$S/reasons.tmp" "$S/reasons"
    fi
    sleep ${TICK:-20}
  done; }

status() {
  echo "=== $(date '+%a %d %b %H:%M:%S IST')  queue $Q  (runner $( [ -s "$Q/runner.pid" ] && kill -0 "$(cat "$Q/runner.pid")" 2>/dev/null && echo up || echo DOWN))"
  local w; w=$(window_now); nw=$(next_window)
  [ -n "$w" ] && echo "  in window: $w"; [ -n "$nw" ] && echo "  next window: $(date -d @"$nw" '+%a %H:%M') ($(grep -m1 "^$(date -d @"$nw" '+%F %H:%M')" "$Q/windows.txt" | cut -d'|' -f4))"
  echo "  load $(cut -d' ' -f1 /proc/loadavg), $(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo) MB free"
  local total=0 ok=0 bad=0
  while IFS= read -r line; do n=$(field "$line" 1); total=$((total + 1))
    if [ -e "$S/$n.exit" ]; then rc=$(cat "$S/$n.exit"); d=$(( $(cat "$S/$n.end") - $(cat "$S/$n.start") ))
      [ "$rc" = 0 ] && ok=$((ok + 1)) || bad=$((bad + 1))
      printf '  %-4s %-18s %dh%02dm\n' "$( [ "$rc" = 0 ] && echo done || echo "FAIL($rc)")" "$n" $((d/3600)) $((d%3600/60))
    elif [ -e "$S/$n.pid" ]; then el=$(( $(date +%s) - $(cat "$S/$n.start") ))
      prog=$(tr '\r' '\n' < "$Q/logs/$n.log" 2>/dev/null | grep -E '^ +[0-9,]+/[0-9,]+' | tail -1 | sed 's/^ *//;s/  */ /g')
      [ -z "$prog" ] && prog=$(tr '\r' '\n' < "$Q/logs/$n.log" 2>/dev/null | grep -v '^\s*$' | tail -1 | cut -c1-110)
      printf '  RUN  %-18s %dh%02dm%s  %s\n' "$n" $((el/3600)) $((el%3600/60)) "$( [ -e "$S/$n.paused" ] && echo ' PAUSED')" "${prog:-no output yet}"
    else r=$(grep -m1 "^$n:" "$S/reasons" 2>/dev/null | cut -d: -f2-); printf '  wait %-18s%s\n' "$n" "${r:- next in line}"; fi
  done < <(jobs_lines)
  echo "  jobs finished $ok of $total$( [ $bad -gt 0 ] && echo ", $bad failed")  (running jobs show their own measured progress; queued ones have no rate yet, so no ETA)"
  tail -4 "$Q/runner.log" 2>/dev/null | sed 's/^/  | /'; }

case $cmd in
  run) run;;
  status) if [ "${*: -1}" = "--watch" ]; then while :; do clear; status; sleep 30; done; else status; fi;;
  *) echo "usage: $0 run|status [dir] [--watch]"; exit 1;;
esac
