# Why the cap-2 solvers lose to the one-raise ones, and what the literature does about it

17 September 2026. Written after the cross-tree gates of Thursday morning and the warm-start
lanes of Thursday afternoon (NEXT.md, "What Thursday morning measured" and "lanes R, S and T").
Lane U's frozen-phase result is appended at the end when it lands.

## What was measured

Every cap-2 rung in the bot loses to the one-raise rung at the same depth, head to head, with
both bucketing the same way and the one-raise agent never re-raising: 19 to 30 BB/100 at 3M
and 10M iterations, at every depth from 12bb to 100bb. The one-raise strategy is a legal
strategy inside the cap-2 game, so a converged cap-2 solve cannot lose to it; the number is a
measure of how far from converged the cap-2 solves are.

The gap closes with iterations and shows no floor. The 18bb rung against its one-raise rung:

| iterations | cold | proportional warm start (lane S/T) |
|---|---|---|
| 3M | −35.1 ± 6.0 | |
| 10M | −26.0 ± 0.4 | −21.9 ± 1.0 (weight 1M), −21.5 ± 3.7 (weight 5M), −25.4 ± 3.1 (scale 10) |
| 50M | −12.7 ± 0.8 | |

The tree is fully reached by about 4M iterations (235k infosets, flat after that), and at 50M
replacing the random-on-miss fallback with check/call moves the number by one point where at
10M it moved twelve. So what remains is the quality of play at nodes the solver has visited
thousands of times, which is the slow part of MCCFR convergence, not holes.

## How this compares with published MCCFR runs

Brown and Sandholm's discounted-CFR paper reports external-sampling MCCFR on HUNL subgames in
terms of nodes touched: at about 10^10 nodes touched, plain and linear MCCFR sit at roughly 100
to 300 mbb/g of exploitability on their subgames 3 and 4 (their figures 10 and 11). Our 50M
iterations at 18bb is on the order of 10^10 node visits, and the cross-tree gap of 12.7 BB/100
is 127 mbb/g. So the solver is doing about what sampled CFR does at this budget. This is not a
defect in the port; it is the algorithm's rate.

The same paper's full-width variants (CFR+, DCFR) reach 1 mbb/g, "essentially solved", in
about 1,000 iterations on the same subgames. That is the standard research answer for an
abstraction of this size: build the abstract game explicitly, with chance as bucket-transition
tables computed once from sampled deals, and run full-width CFR+ or DCFR over it. Our abstract
game projects to 7.6M information sets at 18bb, which is well inside what those solvers handle
in memory. That is the structural fix and it is post-season work, because it is a new solver
path, not a parameter.

What the literature says about the levers we do have:

- **Linear discounting with MCCFR** is the recommended combination (the paper's "Linear MCCFR":
  multiply all regrets and strategy sums by n/(n+1) after each period of 10^7 nodes touched;
  the "initial discount" variant, a single 1/10 after the first period, does about as well).
  Our per-node cumulative discount, fixed on 15 September, is the per-iteration form of the same
  thing, so the rule is right. DCFR's β = 0 or negative is for full-width runs and is not shown
  to help MCCFR; CFR+'s regret floor is reported not to help with sampling. No change indicated.
- **Regret-based pruning** (Brown and Sandholm 2015, 2017; used in Pluribus): after a warm-up,
  most traversals skip actions whose cumulative regret is very negative, with exemptions for
  the river and for actions that end the hand. Pluribus's blueprint used it with linear MCCFR.
  It speeds a run by not traversing hopeless subtrees; reported gains are large in nodes touched,
  though the ceiling per iteration count is unchanged. Not implemented here; a day's work, and a
  candidate for post-season.
- **Warm starting** (Brown and Sandholm 2016): initialise regrets from an input strategy profile
  so CFR provably skips the iterations that profile is worth, at the cost of one traversal. The
  method sets *substitute regrets* from the counterfactual values of the input strategies, chooses
  T to match the input's quality, and reports that solving a coarser abstraction first and warm
  starting the full game from it improves convergence overall. Their experiment warm-started
  full Flop Hold'em from a 5,000-bucket MCCFR strategy at T = 70 with a scaling λ = 0.08.

## What our warm start did, and why it fell short

Lane S's warm start (`MCCFR::warm_start`, mode `proportional`) sets a node's regrets
proportional to the prior's probabilities at a chosen magnitude, so regret matching plays the
prior from the first iteration. That is the cheap form, not Brown and Sandholm's. It bought
about 6M cold iterations (−21.9 against −26.0 at 10M), a 1.6x speed-up, and heavier priors did
not improve it.

Two reasons, and the second is the one the literature addresses:

1. **The linear rule discounts a prior placed at iteration N by about N/T.** By 10M a prior at
   1M carries a tenth of its weight. Making it heavier (lane T) did not help, so this is not the
   binding constraint.
2. **The prior says nothing about the actions the coarser game did not have.** Proportional
   seeding gives the re-raise actions zero regret, and the shared nodes' probabilities are the
   one-raise equilibrium, which is not the cap-2 equilibrium at those nodes once re-raises exist.
   The run then has to *discover* that re-raising is good at each node by accumulating regret
   from scratch, which is most of the remaining work. Brown and Sandholm's substitute regrets
   are exactly the fix: regrets are set from the counterfactual values of every action under
   the prior, so an action the prior never took but which is better than the prior gets
   positive regret before the first real iteration.

## Lane U: the substitute regrets, sampled

`MCCFR::warm_start` mode `frozen` (trainer flag `--warm-mode frozen`): for the first N
iterations every node plays the prior (uniform where the prior has no entry) instead of regret
matching, regrets accumulate as normal, and the average is not accumulated; then regret matching
takes over. At the end of the phase each node holds N iterations of measured regret against the
prior, for every action including the re-raises. This is the paper's one traversal, sampled,
with T = N and λ = 1; on Kuhn a wrong prior held for 10% of the run recovers fully (−0.0557
against −1/18 = −0.0556), where the proportional form needed a light prior to do the same.

Results, 17 September evening. First on the old instrument (random on a miss, one training
run each): N = 3M −29.2 ± 1.6, N = 1M −30.6 ± 2.1, both worse than cold's −26.0; N = 300k
−29.6 ± 4.7; N = 30k −23.9 ± 2.4; **N = 100k −16.4 ± 2.3**. A long frozen phase measures regret
against an opponent who never re-raises and stores confident wrong lessons about aggression,
which the run then has to unlearn; a short one gives the direction of every action without
the bias. That is the paper's point that T must match the prior's quality, and the one-raise
prior's quality in the cap-2 game is low.

Then on the new instrument (`tools/xtree-gate.sh`, check/call on a miss), with the 100k
result replicated at two more seeds and a second cold seed for the run-to-run variance:

| 18bb cap-2 at 10M | vs one-raise, check/call on a miss |
|---|---|
| cold, seeds 0 and 1 | −21.6 ± 2.0, −17.8 ± 3.6 |
| frozen 100k, seeds 0, 1, 2 | −11.4 ± 1.4, −13.7 ± 2.2, −14.1 ± 2.2 |
| cold 50M, seed 0 | −8.1 ± 2.7 |

**The light frozen warm start is real and worth about 3x in iterations**: three seeds near
−13 against two cold seeds near −20, and −13 is where the cold curve sits at roughly 30M.
Two lessons about instruments came with it: random-on-miss inflated every gap and its noise
(cold 10M read −26.0 there and −21.6 here), and single training runs differ by about 4 points
seed to seed at 10M, so a solver claim needs two seeds.

## What to do with the result

- Post-season, first: every cap-2 rung warm-started (frozen 100k from its one-raise rung) at
  20M on six threads, about a night for the ladder, each gated on `tools/xtree-gate.sh` at two
  seeds, then the replay, then bursts; by the curve a warm 20M should land at or past cold 50M.
- In parallel, the full-width solver on the explicit abstract game (the chance tables exist:
  `scripts/cfr/chance_tables.py`, `results/cfr/chance/nolimit_18bb.npz`, tested), prototyped at
  8bb and gated the same way; it is the route to "solved" rather than "3x faster".
- The cross-tree gate against the one-raise rung, check/call on a miss, two seeds, is the
  instrument for solver work from now on; the same-tree gate reads +2.9 between solves that
  differ by 13 points on it, and random-on-miss measures the fallback.

## Sources

- Brown and Sandholm, "Strategy-Based Warm Starting for Regret Minimization in Games", AAAI 2016.
  https://ojs.aaai.org/index.php/AAAI/article/view/10056
- Brown and Sandholm, "Solving Imperfect-Information Games via Discounted Regret Minimization",
  AAAI 2019. https://arxiv.org/abs/1809.04040 (the MCCFR section and figures 10 and 11)
- Brown and Sandholm, "Regret-Based Pruning in Extensive-Form Games", NIPS 2015; "Reduced Space
  and Faster Convergence in Imperfect-Information Games via Pruning", ICML 2017.
  https://arxiv.org/abs/1609.03234
- Brown and Sandholm, "Superhuman AI for multiplayer poker" (Pluribus), Science 2019, supplement:
  linear MCCFR with negative-regret pruning on 95% of traversals after a warm-up, river and
  hand-ending actions exempt.

## 19 September: the recipe taken to 100M, and where it stalls

Lane AB ran the 18bb and 12bb cap-2 rungs at 100M with everything on: frozen 100k warm start,
pruning at −300 stacks from 10%, three threads each (5.4 h and 3.5 h). Against the one-raise
rung, check/call on a miss:

| rung | 3M cold | 10M cold | 10M warm | 50M cold | **100M warm, pruned** |
|---|---|---|---|---|---|
| 18bb | −35.1 | −21.6 / −17.8 | −11.4 / −13.7 / −14.1 | −8.1 | **−8.0 ± 2.2** |
| 12bb | | | | | **−3.7 ± 3.1** (warm 20M: +4.2 ± 3.9) |

Same-tree, 100M against the 20M warm solve: 18bb +7.5 ± 3.0, 12bb +12.2 ± 7.0. So the solves
still improve on their own tree, and the cross-tree gap still narrows, but on a log scale it is
flattening: 18bb has gone −35, −22, −13, −8, and the last doubling of effort bought nothing over
cold 50M. 12bb is level with its one-raise rung at two budgets, which at a near push-or-fold
depth is about the ceiling.

Reading: the sampled solver, warm-started and pruned, gets a cap-2 rung to within about 8
BB/100 of the one-raise rung at 18bb for five hours of three threads, and no further at any
budget we can afford. That is good enough for companions (these are the best we have) and not
enough for the cap-2-primary plan. The remaining gap is either the sampled solver's floor at
this abstraction (the full-width solver's question) or the abstraction itself (six postflop
strength classes; a re-raised pot may need more). The 8bb full-width prototype, gated the same
way, is the next experiment, before any more iterations are spent.
