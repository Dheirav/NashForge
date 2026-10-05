# Bigger trees on one laptop: how much compute, and when a rung is done

5 October 2026. A literature read plus a read of `native/src/mccfr.hpp` and the rung summaries in
`results/cfr/ladder169l_v5x60/`. Nothing was run. Papers are cited; my inference is marked.

## 1. What the literature says

**No paper gives a rule of thumb for iterations per information set.** They all report
convergence against nodes touched or wall time. The theory gives the shape: external-sampling
regret at a node falls as 1/sqrt(T), and the bound grows with the square root of the actions
there (Lanctot et al. 2009; Gibson et al. 2012). So our rule, equal iterations per reached
decision point, is right to first order, and the inference from the bound is that a wider node
needs more visits than a narrow one, not the same.

Our "iterations per point" is also cruder than it looks. It is iterations over
`information_sets_reached`: v5x60 reads 210, 154 and 121 per point at 50, 70 and 100bb after 60M.
That is an average, and the nodes behind a three-bet or an overbet get a small fraction of it. The
solver keeps no per-node visit count, so that tail has never been measured.

**The best sampled variant at our scale is what we already run.** Pluribus's blueprint was
external-sampling MCCFR with linear discounting for the first 400 minutes, negative-regret pruning
after 200 minutes (below -300,000,000, on 95 percent of iterations, river and terminal actions
exempt), 4-byte integer regrets, memory only for the 413M of 665M sequences reached, and no stored
average after the first betting round: it averaged current-strategy snapshots instead (Pluribus
supplement). Brown and Sandholm (2019) put linear MCCFR at about 3x vanilla and found CFR+'s regret
floor does not help under sampling. DCFR was not shown to help MCCFR, and our 28 September grid
rejected it on head to head.

Three variants claim more, none shown at our scale:

- **VR-MCCFR** (Schmid et al. 2019): an order-of-magnitude speedup on Leduc and Goofspiel, two
  orders with CFR+. Needs a baseline per infoset-action, roughly doubling the table.
- **Average strategy sampling** (Gibson et al. 2012): sample a subset of the traverser's actions
  by the average strategy. 54 percent better than external sampling on a 68M-infoset no-limit game,
  with the margin growing as the action count grows. This is the variant built for more bet sizes.
- **Predictive CFR+** (Farina, Kroer and Sandholm 2021) and PDCFR+ (Xu et al. 2024) are full-width
  results, and even there PCFR+ lost to DCFR on two of the poker games. I found nothing showing
  them winning under sampling; the VR-MCCFR paper needed variance reduction before CFR+ worked with
  sampling, which suggests prediction on noisy regrets is worse (inference). They belong to the
  full-width solver.

A July 2026 preprint (Li, Chen and Huang) reports 19 to 34 percent lower exploitability on Leduc
from correlated chance sampling, at no cost. Abstract only, Leduc-sized, unreplicated.

**Exploitability at scale** is LBR (Lisy and Bowling 2017), a lower bound from a greedy one-step
exploiter. We know its blind spot: it rated d1501 and DCFR better while they lost head to head.
AIVAT (Burch et al. 2018) cut a match's standard deviation by 85 percent, 44 times fewer games.

## 2. Changes, ranked by gain per day of work

### 1. Count visits per node, and stop on a rule rather than at 60M

The 60M polish bought about 1.1 points on deep rungs and nothing on mid rungs (50.3 percent head to
head). The cheapest speedup is not spending iterations where they move nothing.

Change: a `uint32` visit counter per node, a reach-weighted histogram in the rung summary, and the
solver's own reach-weighted average positive regret, which bounds abstract-game exploitability
from above (Zinkevich et al. 2007) and is free to compute. Under sampling it is an estimate, so read
its trend, not its level (inference).

Rule: a rung is done when (a) the 10th percentile of reach-weighted visits clears the level the
mid rungs had when they tied (read off v5x60 once the counter exists), (b) doubling iterations moves
same-tree head to head by under 1 point over 5,000 matches, (c) paired LBR on both menus moves by
under one standard error, and (d) adjacent-hand fold jumps at shove nodes do not worsen. Each alone
has fooled us; (b) and (c) disagree in exactly the cases (d) catches.

- Gain: up to 3x wall time on rungs already converged, which goes to the rungs that are short.
- Cost: half a day. Memory: 4 bytes a node, under 2 percent.
- Confirm: on 70bb the 10th percentile should move between 20M and 60M (where head to head read
  48.9); on a mid rung it should already clear the bar at 20M.

### 2. A compact, variable-width training table

`InfoSetNode` holds two fixed arrays of six doubles plus a timestamp and lock, about 120 bytes
before key and hash overhead; H1 measured 1.8 GB for 6.95M infosets, about 260 bytes each. Yet 77
percent of exported nodes are two wide (1.75M of 2.26M in the 100bb cap-2 table). `MAX_ACTIONS = 6`
is also a hard cap on sizes per node, which a bigger menu hits first.

Change: contiguous `float32` regret and sum arrays by per-node offset, `int32` last visit, the
packed `uint64` key from the engineering audit. Pluribus used int32 regrets, so precision is not
the risk. Optionally Pluribus's snapshots in place of a stored postflop average, halving it again.

- Gain: 3 to 5x more reached nodes per GB (my arithmetic: 2.8 actions a node on average, about 22
  bytes of values against 96). Untested inference: faster iterations from cache, and possibly why
  threads scaled 4x on the small 20bb game but barely on v5i's 70bb (0.093 to 0.080 ms from 3 to 8).
- Cost: 1.5 to 2 days. Memory: today 5 GB of headroom is about 19M nodes; after, 60M or more.
- Confirm: Kuhn -1/18 and exact Leduc; new table against old, same seed, 20M, two seeds, same-tree
  head to head inside ±0.7 over 5,000 matches; peak RSS and ms per iteration at 3 and 8 threads.

### 3. Warm start by action, frozen briefly, on every bigger tree

Our own evidence: a 100k frozen phase from the one-raise rung was worth about 3x in iterations on
18bb cap-2 (three seeds against two). Brown and Sandholm (2016) found warm starting from a coarser
abstraction cheaper overall. `cfr/warm.py` already maps across trees by action.

Change: the default for any rung that adds sizes, frozen for about 1 percent of the run (1M and 3M
of 10M were worse than cold: a long frozen phase learns confident wrong lessons about the new
actions). More card classes need a bucket map, nearest class by mean equity (not built).

- Gain: 2 to 3x for an added-size tree (measured once, one depth); unknown for added classes.
- Cost: none for sizes, half a day for classes. Memory: the prior during the frozen phase.
- Confirm: warm 20M against cold 60M on the new tree, same-tree head to head, two seeds.

### 4. Average strategy sampling on wide nodes

External sampling walks every traverser action. Pruning skips hopeless ones but tied on and off
(-1.1 ± 1.6) because today's nodes are narrow. Gibson's gain grows with the menu.

- Gain: 1.3 to 2x on menus of five or more actions; nothing on today's trees.
- Cost: a day, with their parameters (epsilon 0.05, beta 10^6, tau 1,000, stable across all their
  games). Memory: none.
- Confirm: same-tree head to head at equal wall time, AS against external sampling, two seeds.

### 5. Parallel lanes over threads, and what not to do

Two 3-thread jobs gave 1.84x one job; eight threads on one gave about 1.15x. Spend cores on lanes
until change 2 says whether the table is the bottleneck. Two lanes beside the live bot need about
2.5 GB each, tight past 9M nodes today.

Not now: VR-MCCFR (doubles the table, and common random numbers already attack the chance
variance that dominates here; inference), PCFR+ and PDCFR+ (full-width only), DCFR (measured worse).

## How much compute a bigger tree needs

The (4,3,2,1) 70bb rung reached about 3x its control's points and tied at equal iterations, so the
per-point rule held. At v5x60's 0.14 ms an iteration on 3 threads, a 70bb tree with 3x the points
needs about 180M iterations: 7 hours cold on one lane, about 2.5 warm if change 3's 3x holds. One
night per deep rung is affordable, which is why the counter and stopping rule come first: they say
which rungs need the night.

## References

- Pluribus supplement, Science 2019: https://noambrown.com/papers/19-Science-Superhuman_Supp.pdf
- Brown and Sandholm, Discounted Regret Minimization, AAAI 2019: https://arxiv.org/abs/1809.04040
- Brown and Sandholm, Strategy-Based Warm Starting, AAAI 2016:
  https://ojs.aaai.org/index.php/AAAI/article/view/10056
- Brown and Sandholm, Faster Convergence via Pruning, ICML 2017: https://arxiv.org/abs/1609.03234
- Schmid et al., VR-MCCFR, AAAI 2019: https://arxiv.org/abs/1809.03057
- Gibson et al., MCCFR in Games with Many Player Actions, NIPS 2012:
  https://proceedings.neurips.cc/paper_files/paper/2012/file/3df1d4b96d8976ff5986393e8767f5b2-Paper.pdf
- Lanctot et al., Monte Carlo Sampling for Regret Minimization, NIPS 2009:
  https://mlanctot.info/files/papers/nips09mccfr.pdf
- Farina, Kroer and Sandholm, Predictive Blackwell Approachability, AAAI 2021:
  https://arxiv.org/abs/2007.14358
- Xu et al., Weighted Counterfactual Regret with Optimistic OMD, IJCAI 2024:
  https://arxiv.org/abs/2404.13891
- Lisy and Bowling, Equilibrium Approximation Quality of No-Limit Poker Bots, 2017:
  https://arxiv.org/abs/1612.07547
- Burch et al., AIVAT, AAAI 2018: https://arxiv.org/abs/1612.06915
- Li, Chen and Huang, Correlated Chance Sampling for MCCFR, 2026 (abstract only):
  https://arxiv.org/abs/2607.27035
- Zinkevich et al., Regret Minimization in Games with Incomplete Information, NIPS 2007:
  https://papers.nips.cc/paper/3306-regret-minimization-in-games-with-incomplete-information
