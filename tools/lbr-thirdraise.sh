#!/usr/bin/env bash
# Paired third-raise LBR on the rungs that have an all-in-only raise level: v5xRR3 at
# 70bb and 100bb, (4, 2, 1), where it is the third raise of a street, and the (4, 3, 2, 1)
# 70bb rung, where it is the fourth. Each chunk plays probes off and on over the same
# per-hand seeds (scripts/lbr_ladder.py --paired), so the difference is exact per hand.
# The chunk shape and seeds are the 25 Sept lanes' (8,000 hands, seed 1000k+7), so a
# chunk here sits beside a chunk there. Not for match day: one stream per rung, all three
# at once, so it waits for free memory and runs nothing while the bot is live.
#   tools/lbr-thirdraise.sh [out-dir]        progress: tools/lbr-thirdraise-progress.sh --watch
set -u
cd "$(dirname "$0")/.."                                   # the worktree that has the probe code
M=${LADDERS:-$HOME/Code/PokerBot/results/cfr}      # LADDERS: a fake tree, to exercise the lane
OUT=${1:-$M/lbr_thirdraise_$(date +%F)}
CHUNKS=${CHUNKS:-16}; HANDS=${HANDS:-8000}; PROBES=${PROBES:-"0.4 0.6 1.0"}
mkdir -p "$OUT"; L=$OUT/lane.log
stamp() { echo "$(date '+%F %T') $*" >> "$L"; }
[ -f "$OUT/started" ] || date +%s > "$OUT/started"
echo "$CHUNKS" > "$OUT/chunks"
stamp "start: $CHUNKS chunks of $HANDS hands per rung, probes $PROBES, into $OUT"
run() { local name=$1 ladder=$2 rung=$3
  stamp "$name: $(readlink -f "$M/$ladder/cap2_$rung.pkl")"
  for k in $(seq 1 "$CHUNKS"); do
    local out="$OUT/${name}_$(printf %02d "$k").json"
    [ -s "$out" ] && continue                             # a rerun resumes
    while [ "$(free -m | awk 'NR==2{print $7}')" -lt 1500 ]; do sleep 60; done
    /usr/bin/time -f "$name chunk $k: maxrss %M KB, %e s" -a -o "$OUT/time.log" \
      venv/bin/python scripts/lbr_ladder.py --ladder "$M/$ladder" --rungs "$rung" --hands "$HANDS" \
        --seed $((1000 * k + 7)) --offtree-third-raise $PROBES --paired \
        --trace "$OUT/${name}_trace.jsonl" --out "$out" >> "$OUT/${name}.log" 2>&1 \
      || stamp "$name chunk $k failed: $(tail -1 "$OUT/${name}.log" | cut -c1-120)"
  done
  stamp "$name done"; }
run rr3_70bb ladder169l_v5xRR3 70bb & run rr3_100bb ladder169l_v5xRR3 100bb & run cap4321_70bb ladder169l_v5i_cap4321 70bb & wait
stamp "lane complete"
touch "$OUT/done"
