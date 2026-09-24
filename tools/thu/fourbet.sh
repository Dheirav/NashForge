#!/usr/bin/env bash
# The only structural gap with a match attached to it.
#
# Facing a re-raise our tree offers fold, call or all-in, nothing in between.
# Across every logged match that node came up 855 times and we folded 568 of
# them, and on 23 September it turned a 2,100 chip mistake into a 7,935 one.
# The fix is a third raise level that holds a sized raise, which is (4,3,2) at
# 42M information sets against (4,2,1)'s 3.4M.
#
# 20M iterations, the operating point established on 23 September: coverage
# saturates there (389,086 entries against 390,110 at 60M) and this is an
# experiment, not a set that plays. If it wins it gets the 60M pass afterwards.
set -u
set -o pipefail   # a step that fails inside a pipeline must not report success
cd "$HOME/Code/PokerBot"
E=results/cfr/experiments
out=$E/cap432_70bb_20m.pkl
venv/bin/python -u scripts/cfr/train_nolimit.py --iterations 20000000 --raise-cap 4 3 2 \
  --stack 140 --big-blind 2 --buckets 20 --preflop-buckets 169 --abstraction-samples 800 \
  --equity-samples 200 --update-rule linear --strength histogram --hist-bins 20 \
  --hist-runouts 100 --hist-opponents 50 --table-threads 4 --texture --seed 0 --threads 4 \
  --prune-after 0.1 --prune-stacks 300 --output "$out" 2>&1 | tail -6
venv/bin/python scripts/strategy_sweep.py "$out" --threshold 0.15 --top 3
D=results/cfr/ladder169l_fb; rm -rf $D; mkdir -p $D
for f in results/cfr/ladder169l_v5i/*; do cp -P "$f" $D/; done
for ext in .pkl .flat.pkl .flat.npz .json; do ln -sf ../experiments/cap432_70bb_20m$ext $D/cap2_70bb$ext; done
venv/bin/python scripts/chipzen_duel.py --a $D "--a-flags=--deep-primary --stack-cap" --a-label fourbet \
  --b results/cfr/ladder169l_v5i "--b-flags=--deep-primary --stack-cap" --b-label v5i \
  --hands 60000 --stack-bb 70 --seed 77 --workers 4 \
  --output results/chipzen/duels/fourbet_vs_v5i_70bb.json 2>&1 | grep -E 'chips/hand'
echo
echo "The bar, written before the run: more than +6 chips a hand at 70bb, which"
echo "is two standard errors on this instrument, and no new heavy-shove node in"
echo "the sweep. Anything less and the extra twelve times the tree is not paying."

[ -s "$out" ] || { echo "the four-bet rung was never written to $out" >&2; exit 1; }
