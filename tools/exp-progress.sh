#!/usr/bin/env bash
# Progress for an experiment lane that trains a few rungs one after another
# (~/pokerbot-scratch/ladder169/lane*.sh). Shows the lane's own stamps, the
# running trainer's "<done>/<total> ... eta" line, which is measured from its
# own rate, and every gate written so far. Trainers not yet started have no
# rate, so they are not given an ETA.
#   tools/exp-progress.sh [lane-log] [--watch]
if [ -n "${1:-}" ] && [ "$1" != "--watch" ]; then lane=$1; shift
else lane=$(ls -t ~/pokerbot-scratch/ladder169/lane*_*.log 2>/dev/null | head -1); fi
[ -n "$lane" ] || { echo "no lane log found"; exit 1; }
watch=""; [ "${1:-}" = "--watch" ] && watch=1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
report() {
  echo "=== $(date '+%H:%M:%S %Z') — $(basename "$lane")"
  sed 's/^/  /' "$lane"
  # Every rung with a "train <rung>" stamp and no "exit" stamp yet is running;
  # since lane P they run in parallel, so all of them are shown.
  for rung in $(grep -oE 'train [a-z0-9_]+ \(' "$lane" | awk '{print $2}' | sort -u); do
    grep -q "train $rung exit" "$lane" && continue
    local f; f=$(ls -t ~/pokerbot-scratch/cap2/exp*_${rung}.log 2>/dev/null | head -1)
    local line; line=$(grep -E '^ +[0-9,]+/[0-9,]+' "$f" 2>/dev/null | tail -1 | sed 's/^ *//')
    if [ -n "$line" ]; then echo "  $rung RUN  $line"; else echo "  $rung RUN  fitting the abstraction, no rate yet"; fi
    grep -qE 'Traceback|Error' "$f" 2>/dev/null && echo "  $rung FAILED, see $f"
  done
  for gate in "$ROOT"/results/cfr/ladder169l/gate_10m_vs_v5_*.json "$ROOT"/results/cfr/ladder169l_v6/gate_10m_vs_3m_*.json "$ROOT"/results/cfr/ladder169l_v6/xtree_*.json "$ROOT"/results/cfr/ladder169l_v6/gate_50m_*.json "$ROOT"/results/cfr/ladder169l_v6/gate_warm*.json "$ROOT"/results/cfr/ladder169l_v6/xtree_cap2_frozen_*.json; do
    [ -f "$gate" ] || continue
    printf '  GATE %s: ' "$(basename "$gate" .json)"
    "$ROOT/venv/bin/python" -c "import json; d=json.load(open('$gate')); print(f\"{d['mean']:+.1f} ± {d['stderr']:.1f} BB/100 to the first over {d['hands']:,} hands x {len(d['seeds'])} seeds\")"
  done
  echo
}
if [ -n "$watch" ]; then while :; do report; sleep 120; done; else report; fi
