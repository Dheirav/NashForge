#!/usr/bin/env bash
# Progress for tools/lbr-overbet.sh: chunks written out of the total, elapsed, and an ETA
# from the rate measured so far (none until a chunk has finished). A chunk is both arms,
# so nothing moves for its first several minutes. A pooled difference before the lane
# finishes is a counter, not a result.
#   tools/lbr-overbet-progress.sh [out-dir] [--watch]
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -n "${1:-}" ] && [ "$1" != "--watch" ]; then OUT=$1; shift
else OUT=$(ls -td "$ROOT"/results/cfr/lbr_overbet_* 2>/dev/null | head -1); fi
[ -n "$OUT" ] && [ -f "$OUT/started" ] || { echo "no lbr_overbet lane found"; exit 1; }
report() {
  local now started chunks name n elapsed eta="no rate yet"
  now=$(date +%s); started=$(cat "$OUT/started"); chunks=$(cat "$OUT/chunks"); name=$(cat "$OUT/name")
  elapsed=$((now - started)); n=$(ls "$OUT"/${name}_[0-9][0-9].json 2>/dev/null | wc -l)
  if [ -f "$OUT/done" ]; then eta="lane complete"
  elif [ "$n" -gt 0 ]; then
    local left=$(( (chunks - n) * elapsed / n )); eta="ETA $(date -d "@$((now + left))" '+%H:%M %Z') ($((left / 60)) min left)"
  fi
  echo "=== $(date '+%H:%M:%S %Z'), $OUT"
  printf '  %s: %d/%d chunks, elapsed %d min, %s\n' "$name" "$n" "$chunks" $((elapsed / 60)) "$eta"
  [ -f "$OUT/time.log" ] && tail -2 "$OUT/time.log" | sed 's/^/  /'
  grep -h "failed" "$OUT/lane.log" 2>/dev/null | sed 's/^/  /'
  [ "$n" -gt 0 ] && "$ROOT/venv/bin/python" "$ROOT/scripts/lbr_paired_report.py" "$OUT"/${name}_[0-9][0-9].json | sed 's/^/  /'
  echo
}
if [ "${1:-}" = "--watch" ]; then while :; do report; sleep 60; done; else report; fi
