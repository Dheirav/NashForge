#!/usr/bin/env bash
# Train the depth ladder for the arena: one solver per effective stack, in big
# blinds. Elimination matches drift from 100bb down to a few, and a 100bb
# strategy played short is the wrong game, so each rung is a solution of the
# game at its own depth. Native, 250,000 iterations each, ~70s a rung at 100bb
# and faster below it.
#   tools/train-ladder.sh                # default rungs
#   tools/train-ladder.sh 70 50          # chosen rungs
# Watch: tail -f ~/pokerbot-scratch/ladder/train.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$HOME/pokerbot-scratch/ladder"; mkdir -p "$DIR"
OUT_DIR="${LADDER_DIR:-results/cfr/ladder}"; SAMPLES="${EQUITY_SAMPLES:-40}"; TEXTURE_FLAG="${TEXTURE:+--texture}"; PREFLOP_FLAG="${PREFLOP_BUCKETS:+--preflop-buckets $PREFLOP_BUCKETS}"; RULE_FLAG="${UPDATE_RULE:+--update-rule $UPDATE_RULE}"; mkdir -p "$OUT_DIR"
DEPTHS=("$@"); [ ${#DEPTHS[@]} -eq 0 ] && DEPTHS=(70 50 35 25 18 12 8 5)
cd "$ROOT"
for bb in "${DEPTHS[@]}"; do
  out="$OUT_DIR/nolimit_${bb}bb.pkl"
  if [ -f "$out" ]; then echo "$(date '+%H:%M:%S') ${bb}bb exists, skipping"; continue; fi
  echo "$(date '+%H:%M:%S') ${bb}bb: training (stack $((bb*2)), big blind 2)"
  venv/bin/python scripts/cfr/train_nolimit.py --iterations "${ITERATIONS:-250000}" --stack $((bb*2)) \
      --big-blind 2 --equity-samples "$SAMPLES" $TEXTURE_FLAG $PREFLOP_FLAG $RULE_FLAG --eval-hands 2000 --output "$out" > "$DIR/$(basename "$OUT_DIR")_${bb}bb.log" 2>&1 \
    && echo "$(date '+%H:%M:%S') ${bb}bb: done  $(grep -E 'ms/iteration|infosets' "$DIR/$(basename "$OUT_DIR")_${bb}bb.log" | tail -1)" \
    || echo "$(date '+%H:%M:%S') ${bb}bb: FAILED, see $DIR/$(basename "$OUT_DIR")_${bb}bb.log"
done
echo "$(date '+%H:%M:%S') ladder complete"
