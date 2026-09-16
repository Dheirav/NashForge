#!/usr/bin/env bash
# Deeper-tree companions for the arena ladder: (4, 2) tapers at the given
# depths, asked only when the one-raise solver has no entry (a re-raise).
# 1,000,000 native iterations each, which over the taper's ~80k reachable
# information sets is about the density the 250k one-raise solvers have.
#   tools/train-companions.sh 50 25
# Watch: tail -f ~/pokerbot-scratch/ladder/companions.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$HOME/pokerbot-scratch/ladder"; mkdir -p "$DIR"
OUT_DIR="${LADDER_DIR:-results/cfr/ladder}"; SAMPLES="${EQUITY_SAMPLES:-40}"; TEXTURE_FLAG="${TEXTURE:+--texture}"; PREFLOP_FLAG="${PREFLOP_BUCKETS:+--preflop-buckets $PREFLOP_BUCKETS}"; RULE_FLAG="${UPDATE_RULE:+--update-rule $UPDATE_RULE}"; mkdir -p "$OUT_DIR"
cd "$ROOT"
for bb in "$@"; do
  out="$OUT_DIR/taper42_${bb}bb.pkl"
  if [ -f "$out" ]; then echo "$(date '+%H:%M:%S') ${bb}bb taper exists, skipping"; continue; fi
  echo "$(date '+%H:%M:%S') ${bb}bb taper (4,2): training"
  venv/bin/python scripts/cfr/train_nolimit.py --iterations "${ITERATIONS:-1000000}" --raise-cap 4 2 \
      --stack $((bb*2)) --big-blind 2 --equity-samples "$SAMPLES" $TEXTURE_FLAG $PREFLOP_FLAG $RULE_FLAG --eval-hands 2000 --output "$out" > "$DIR/$(basename "$OUT_DIR")_taper42_${bb}bb.log" 2>&1 \
    && echo "$(date '+%H:%M:%S') ${bb}bb taper: done  $(grep -E 'ms/iteration' "$DIR/$(basename "$OUT_DIR")_taper42_${bb}bb.log" | tail -1)" \
    || echo "$(date '+%H:%M:%S') ${bb}bb taper: FAILED, see $DIR/$(basename "$OUT_DIR")_taper42_${bb}bb.log"
done
echo "$(date '+%H:%M:%S') companions complete"
