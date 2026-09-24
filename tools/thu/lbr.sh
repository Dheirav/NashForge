#!/usr/bin/env bash
# The measurement this project has never had: how exploitable is what we play?
#
# Three runs, cheapest first, so a budget kill still leaves something:
#   1. 70bb on our own bet sizes        — the baseline number
#   2. 70bb on sizes BETWEEN ours       — the translation attack nobody has
#                                         pointed at us; pseudo-harmonic
#                                         mapping is supposed to absorb it
#   3. 100bb on our own sizes           — the depth most fixtures start at
#
# A clearly positive number proves the rung is exploitable by at least that
# much and says where. Near zero proves nothing: it means the greedy exploiter
# failed, not that the rung is sound. That asymmetry is the whole point of the
# bound and it goes in every sentence that quotes the number.
set -u
set -o pipefail   # a step that fails inside a pipeline must not report success
cd "$HOME/Code/PokerBot"
HANDS=${HANDS:-1500}
venv/bin/python scripts/lbr_ladder.py --rungs 70bb --hands "$HANDS" \
  --out results/cfr/lbr_v5i_70bb.json 2>&1 | tail -5
echo
venv/bin/python scripts/lbr_ladder.py --rungs 70bb --hands "$HANDS" --between-sizes \
  --out results/cfr/lbr_v5i_70bb_between.json 2>&1 | tail -5
echo
venv/bin/python scripts/lbr_ladder.py --rungs 100bb --hands "$HANDS" \
  --out results/cfr/lbr_v5i_100bb.json 2>&1 | tail -5

for f in results/cfr/lbr_v5i_70bb.json results/cfr/lbr_v5i_70bb_between.json results/cfr/lbr_v5i_100bb.json; do
  [ -s "$f" ] || { echo "LBR did not write $f" >&2; exit 1; }
done
