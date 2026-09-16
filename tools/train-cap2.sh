#!/usr/bin/env bash
# Full-size raise-cap-2 solvers for the arena: every size on the re-raise, so
# the main solver knows what a three-bet means. About 390k reachable
# information sets at 100bb; 3M iterations is ~8 per set, in line with the
# one-raise ladder's density.
#   LADDER_DIR=results/cfr/ladder200t EQUITY_SAMPLES=200 TEXTURE=1 tools/train-cap2.sh 70 50
#   PREFLOP_BUCKETS=169 keeps every starting hand its own class (see abstraction.buckets).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$HOME/pokerbot-scratch/cap2"; mkdir -p "$DIR"
OUT_DIR="${LADDER_DIR:-results/cfr/ladder}"; SAMPLES="${EQUITY_SAMPLES:-40}"; TEXTURE_FLAG="${TEXTURE:+--texture}"; PREFLOP_FLAG="${PREFLOP_BUCKETS:+--preflop-buckets $PREFLOP_BUCKETS}"; RULE_FLAG="${UPDATE_RULE:+--update-rule $UPDATE_RULE}"; mkdir -p "$OUT_DIR"
ITER="${ITERATIONS:-3000000}"
cd "$ROOT"
for bb in "$@"; do
  out="$OUT_DIR/cap2_${bb}bb.pkl"
  if [ -f "$out" ]; then echo "$(date '+%H:%M:%S') ${bb}bb cap2 exists, skipping"; continue; fi
  echo "$(date '+%H:%M:%S') ${bb}bb cap2: training ($ITER iterations)"
  venv/bin/python scripts/cfr/train_nolimit.py --iterations "$ITER" --raise-cap 2 --stack $((bb*2)) \
      --big-blind 2 --equity-samples "$SAMPLES" $TEXTURE_FLAG $PREFLOP_FLAG $RULE_FLAG --eval-hands 2000 --output "$out" \
      > "$DIR/$(basename "$OUT_DIR")_cap2_${bb}bb.log" 2>&1 \
    && echo "$(date '+%H:%M:%S') ${bb}bb cap2: done  $(grep -E 'ms/iteration' "$DIR/$(basename "$OUT_DIR")_cap2_${bb}bb.log" | tail -1)" \
    || echo "$(date '+%H:%M:%S') ${bb}bb cap2: FAILED"
done
echo "$(date '+%H:%M:%S') cap2 complete"
