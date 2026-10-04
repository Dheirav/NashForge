#!/usr/bin/env bash
# Progress for tools/lbr-thirdraise.sh: chunks written per rung out of the total, elapsed,
# and an ETA from the rate measured so far (none until a chunk has finished), plus the
# peak memory of each finished chunk and the paired difference pooled over what is done.
# A pooled difference before the lane finishes is a counter, not a result.
#   tools/lbr-thirdraise-progress.sh [out-dir] [--watch]
if [ -n "${1:-}" ] && [ "$1" != "--watch" ]; then OUT=$1; shift
else OUT=$(ls -td "$HOME"/Code/PokerBot/results/cfr/lbr_thirdraise_* 2>/dev/null | head -1); fi
[ -n "$OUT" ] && [ -f "$OUT/started" ] || { echo "no lbr_thirdraise lane found"; exit 1; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
report() {
  local now started chunks elapsed done_all=0 total=0
  now=$(date +%s); started=$(cat "$OUT/started"); chunks=$(cat "$OUT/chunks"); elapsed=$((now - started))
  echo "=== $(date '+%H:%M:%S %Z'), $OUT"
  for name in rr3_70bb rr3_100bb cap4321_70bb; do
    local n; n=$(ls "$OUT"/${name}_[0-9][0-9].json 2>/dev/null | wc -l)
    done_all=$((done_all + n)); total=$((total + chunks))
    local eta="no rate yet"
    if [ "$n" -gt 0 ] && [ "$n" -lt "$chunks" ]; then
      local left=$(( (chunks - n) * elapsed / n )); eta="ETA $(date -d "@$((now + left))" '+%H:%M %Z') ($((left / 60)) min)"
    elif [ "$n" -ge "$chunks" ]; then eta="done"; fi
    printf '  %-13s %2d/%d chunks  %s\n' "$name" "$n" "$chunks" "$eta"
  done
  printf '  elapsed %d min, %d/%d chunks overall\n' $((elapsed / 60)) "$done_all" "$total"
  [ -f "$OUT/time.log" ] && tail -3 "$OUT/time.log" | sed 's/^/  /'
  grep -h "failed" "$OUT/lane.log" 2>/dev/null | sed 's/^/  /'
  ls "$OUT"/*_[0-9][0-9].json >/dev/null 2>&1 && "$ROOT/venv/bin/python" "$ROOT/scripts/lbr_paired_report.py" "$OUT"/*_[0-9][0-9].json | sed 's/^/  /'
  [ -f "$OUT/done" ] && echo "  lane complete"
  echo
}
if [ "${1:-}" = "--watch" ]; then while :; do report; sleep 60; done; else report; fi
