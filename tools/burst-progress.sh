#!/usr/bin/env bash
# Progress of a quota burst: matches finished out of the target, won and lost,
# elapsed, and an ETA from the rate measured so far, capped at the burst's own
# deadline. Reads the burst's log (for the target, start and deadline) and the
# bot's status file (for the counts); changes nothing.
#   tools/burst-progress.sh [burst-log] [--watch]
D=~/pokerbot-scratch/chipzen; S=$D/status.json
log=$(ls -t $D/burst_*.log 2>/dev/null | grep -v dryrun | head -1); watch=""
for arg in "$@"; do [ "$arg" = "--watch" ] && watch=1 || log=$arg; done
field() { "$HOME/Code/PokerBot/venv/bin/python" -c "import json;print(json.load(open('$S')).get('$1', 0))" 2>/dev/null || echo 0; }
report() {
  echo "=== $(TZ=Asia/Kolkata date '+%H:%M:%S IST') — $(basename "$log")"
  target=$(grep -m1 -oE 'up to [0-9]+ matches' "$log" | grep -oE '[0-9]+')
  deadline=$(grep -m1 -oE 'deadline [0-9-]+ [0-9:]+' "$log" | cut -d' ' -f2-)
  start=$(grep -m1 ' starting ' "$log" | cut -c1-19)
  if [ -z "$start" ]; then echo "  armed, not started: $(head -1 "$log" | cut -c21-120)"; echo; return; fi
  if grep -q 'burst over' "$log"; then echo "  $(grep 'burst over' "$log" | cut -c21-)"; echo; return; fi
  f=$(field matches_finished); a=$(field matches_active); w=$(field wins); l=$(field losses); h=$(field hands)
  now=$(date +%s); el=$(( now - $(date -d "$start" +%s) ))
  echo "  $f / ${target:-?} matches finished ($w won, $l lost), $a playing, $h hands, elapsed $((el / 60))m"
  if [ "$f" -gt 0 ] && [ -n "$target" ]; then
    left=$(( (target - f) * el / f )); eta=$(( now + left )); cap=$(date -d "$deadline" +%s)
    [ "$eta" -gt "$cap" ] && eta=$cap && note=" (the deadline; it stops there)" || note=" from the measured rate"
    echo "  ETA $(TZ=Asia/Kolkata date -d @$eta '+%H:%M IST')$note"
  else
    echo "  no match finished yet, so no rate; deadline $(TZ=Asia/Kolkata date -d "$deadline" '+%H:%M IST')"
  fi
  echo "  a burst of twenty is about ±11 points; read it decomposed (scripts/chipzen_decompose.py), not by this"
  echo
}
if [ -n "$watch" ]; then while true; do clear; report; sleep 30; done; else report; fi
