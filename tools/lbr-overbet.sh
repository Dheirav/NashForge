#!/usr/bin/env bash
# Paired LBR, translation off and on (scripts/lbr_ladder.py --bridge-translation --paired):
# the same per-hand seeds with LBR's off-tree sizes read by abstraction.translation and
# then by chipzen/bridge.py, so the per-hand difference is what the mismatch was worth.
# One stream, chunks in sequence, seeds 1000k+7 as in the 25 Sept and third-raise lanes.
# It waits for 2,500 MB available before each chunk. Writes into this worktree.
#   tools/lbr-overbet.sh [out-dir]        progress: tools/lbr-overbet-progress.sh --watch
set -u
cd "$(dirname "$0")/.."
M=${LADDERS:-$HOME/Code/PokerBot/results/cfr}
OUT=${1:-$PWD/results/cfr/lbr_overbet_$(date +%F)}
LADDER=${LADDER:-ladder169l_v5xRR3}; RUNG=${RUNG:-70bb}; LANE=${LANE:-rr3_${RUNG}_between}
CHUNKS=${CHUNKS:-2}; HANDS=${HANDS:-8000}; SIZES=${SIZES:---between-sizes}
mkdir -p "$OUT"; L=$OUT/lane.log
stamp() { echo "$(date '+%F %T') $*" >> "$L"; }
[ -f "$OUT/started" ] || date +%s > "$OUT/started"
echo "$CHUNKS" > "$OUT/chunks"; echo "$LANE" > "$OUT/name"
stamp "start: $LANE, $CHUNKS chunks of $HANDS hands, $SIZES, $(readlink -f "$M/$LADDER/cap2_$RUNG.pkl")"
for k in $(seq 1 "$CHUNKS"); do
  out="$OUT/${LANE}_$(printf %02d "$k").json"
  [ -s "$out" ] && continue                               # a rerun resumes
  while [ "$(free -m | awk 'NR==2{print $7}')" -lt 2500 ]; do sleep 60; done
  /usr/bin/time -f "$LANE chunk $k: maxrss %M KB, %e s" -a -o "$OUT/time.log" \
    venv/bin/python scripts/lbr_ladder.py --ladder "$M/$LADDER" --rungs "$RUNG" --hands "$HANDS" \
      --seed $((1000 * k + 7)) $SIZES --bridge-translation --paired \
      --trace "$OUT/${LANE}_trace.jsonl" --out "$out" >> "$OUT/${LANE}.log" 2>&1 \
    || stamp "$LANE chunk $k failed: $(tail -1 "$OUT/${LANE}.log" | cut -c1-120)"
done
stamp "lane complete"
touch "$OUT/done"
