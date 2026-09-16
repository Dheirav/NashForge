#!/usr/bin/env bash
# Progress for a Slumbot run (scripts/slumbot_pilot.py or slumbot_measure.py).
#   tools/slumbot-progress.sh <logfile> [--watch]
# Hands done of total, elapsed since the log started, and an ETA from the
# measured rate of this run only. The win rate is deliberately not shown: at
# 1,000 hands it is about ±1,250 mbb/hand and reading it is the stopping-rule
# error. The miss rate is shown because it is the number the run is for.
log=${1:?usage: $0 <logfile> [--watch]}; shift
watch=""; [ "${1:-}" = "--watch" ] && watch=1
report() {
  [ -f "$log" ] || { echo "no log yet at $log"; return; }
  local total; total=$(grep -oE '^[0-9]+ hands' "$log" | head -1 | grep -oE '[0-9]+')
  [ -z "$total" ] && total=$(grep -oE '[0-9,]+ hands against Slumbot' "$log" | head -1 | grep -oE '[0-9,]+' | tr -d ,)
  local line; line=$(grep -E '^ +[0-9,]+(/| hands)' "$log" | tail -1)
  local done; done=$(echo "$line" | grep -oE '[0-9,]+' | head -1 | tr -d ,)
  # Elapsed from the running process itself when there is one (the log's own
  # timestamps do not exist, and its birth time lied by two hours on 15 Sept
  # when a killed chain had created it earlier); the log's mtime otherwise.
  local elapsed pid
  pid=$(ps -eo pid,args | grep -E "^ *[0-9]+ venv/bin/python scripts/slumbot_(pilot|measure).py" | awk '{print $1}' | head -1)
  if [ -n "$pid" ]; then
    elapsed=$(ps -o etimes= -p "$pid" | tr -d ' ')
  else
    elapsed=$(( $(date +%s) - $(stat -c %Y "$log") ))
  fi
  echo "=== $(date '+%H:%M:%S %Z') — $(basename "$log")"
  if [ -n "$done" ] && [ "$done" -gt 0 ] && [ -n "$total" ]; then
    local rate eta; rate=$(awk -v d="$done" -v e="$elapsed" 'BEGIN{printf "%.2f", d/e}')
    eta=$(awk -v d="$done" -v t="$total" -v e="$elapsed" 'BEGIN{printf "%d", (t-d)*e/d/60}')
    echo "  $done / $total hands, elapsed $((elapsed/60)) min, $rate hands/s, eta $eta min"
    echo "  $line" | sed -E 's/\[[^]]*mbb\/hand so far\]//'
  else
    echo "  no hands counted yet (elapsed $((elapsed/60)) min)"
  fi
  grep -E 'miss rate|Traceback|Error|wrote' "$log" | tail -2 | sed 's/^/  | /'
  echo
}
if [ -n "$watch" ]; then while :; do report; sleep 120; done; else report; fi
