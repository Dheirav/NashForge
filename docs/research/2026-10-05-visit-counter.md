# A visit counter per information set, and a rule for when a rung is done

5 October 2026, branch `visit-counter`. Item 1 of the ranked changes in
`2026-10-05-convergence-and-compute.md`. Built, tested, and shown on one small run; the bar
in leg (a) of the rule is still provisional. The same night it was calibrated on two rungs and
one rung was checked at 10M against 20M on the gate and LBR (the last section).

## Why

Every training budget so far has been set by iterations per reached point, which is
iterations over `information_sets_reached`. That is an average. On 3 October the mid rungs
(12 to 35bb) read 87 to 285 iterations a point and were already converged at 20M, because
polishing them to 60M tied head to head (50.3). The deep rungs read about 51 and the 60M polish
bought them about a point. So the average ranked the rungs correctly, but it cannot say which
nodes inside a rung are short. The nodes behind a three-bet or an overbet get a small share of
it, and the solver kept no count, so that tail had never been measured.

## What was built

**Two `uint32` counters in `InfoSetNode` (`native/src/mccfr.hpp`), not one, at zero memory.**
The node was 120 bytes with 4 bytes of padding after `num_actions` and 7 after the lock byte.
Both counters sit in that padding, and a `static_assert` pins the size at 120, so a later edit
that grows the node fails to compile instead of quietly costing 8 bytes on tens of millions
of nodes. The convergence doc budgeted 4 bytes a node; it costs none.

- `avg_visits`: incremented where `strategy_sum` is, so it counts the samples the exported
  average strategy is made of. Under external sampling the owner's node is entered as the
  non-traverser on one sampled path, so its expected value is T times the chance probability
  times the owner's own reach. It respects `average_from` and the frozen warm phase, because
  samples that never reach the average are not part of it.
- `regret_visits`: incremented with each regret update, made with the owner as the traverser,
  so T times chance times the opponent's reach.

Both are written only when `set_count_visits(True)` is on. Off, the solver takes the old path
and draws no extra random number, and the golden test (`tests/test_native.py`) is byte-identical.
The increments happen inside the node lock under threads, so a threaded run loses no counts.
They saturate at 2^32 - 1 rather than wrapping, since a wrapped root would read as the rare tail.

**Export.** `NoLimitSolver.visits_flat(key_width)` returns the keys in the same padded, sorted
form as `average_strategy_flat`, so row i of the counts is row i of the strategy.
`scripts/cfr/train_nolimit.py --count-visits` writes `<name>.visits.npz` beside the flat pair
(`cfr/visits.py` reads and writes it), and `--visit-snapshots N ...` also writes
`<name>.visits.N.npz` after N iterations, counted after any frozen warm phase. One run then gives
the T and 2T pair the rule compares, which costs half as much as two runs.

**Report.** `scripts/cfr/visit_report.py A.visits.npz [B.visits.npz]` prints the distribution of
`avg_visits` over reached nodes: percentiles, the share under 10, 100 and 1,000 samples, the
share with none, overall, by street, and by raise depth on the street. Each row has a
node-weighted view and a reach-weighted one. Node-weighted counts every reached node once, which
is the pessimist's view, because most of the deep tail is almost never played. Reach-weighted
weights a node by `avg_visits x regret_visits`, which is proportional to its probability of being
reached in play times the chance probability of the owner's bucket. That last factor makes it a
proxy and not an exact reach (within about 2x preflop across the 169 classes, more postflop with
texture), but it ranks the tail by how often it is played, which is what the rule needs. With two
snapshots it also prints, per street, the ratio of counts on the nodes both reached. Where reach
has settled that ratio is the ratio of iterations; where it is still moving it drifts, which is a
second, free sign that a street has not settled.

## The stopping rule

A rung is done when all three of these hold, comparing a solve at T with one at 2T on the same
tree:

- **(a) Visits.** On the worst street-and-depth line, the reach-weighted 10th percentile of
  `avg_visits` at 2T is at or above the bar. This is the only leg the solver can check by itself,
  and the report checks it. It is judged per line and not over the whole tree because the reach
  weight sits on the first decisions: on the demo below the whole-tree figure was 26,022 while the
  river after three raises read 447, so a whole-tree percentile lets the busy lines pass for the
  rare ones, which is the averaging this counter exists to look past.
- **(b) Head to head.** Doubling from T to 2T moves same-tree head to head by under 1 point:
  `scripts/chipzen_duel.py --arena-matches 5000`, match-win percentage points, about ±0.7 at
  5,000. A delta under 1 with a wider standard error than that is reported as not measured,
  because it cannot resolve a sub-point move, and so is a delta given without its standard error
  (`--h2h-delta` alone), as leg (c) already treated a missing one. Before the review the report
  passed (b) on the delta alone, so the verdict could read "done" on a width nobody had given.
- **(c) LBR.** Paired LBR, T against 2T on the same per-hand seeds (`scripts/lbr_ladder.py` on
  both, pooled with `scripts/lbr_paired_report.py`), moves by under one standard error, on both
  menus (our sizes and between ours).

The report takes (b) and (c) as `--h2h-delta/--h2h-se` and `--lbr-delta/--lbr-se` and prints
pass, FAIL or not measured per leg. The verdict is "done" only when all three pass: a leg with no
measurement is not a passed leg.

Why three. Each has fooled us alone. LBR rated d1501 and DCFR better while both lost head to head,
and on 27 September it saw nothing between 20M and 60M on the deep rungs while two head to heads
agreed on about a point. Head to head alone cannot see a rare bad node that neither copy reaches
in 5,000 matches, such as v5f's 98 percent pocket-jacks shove. The visit count is the one that
sees that tail directly, while it says nothing about whether those visits have converged; that is
what (b) and (c) are for. The convergence doc's fourth leg, (d) adjacent-hand fold jumps at shove
nodes, has its own script since the same night, `scripts/fold_jumps.py` on branch `fold-jumps`
(see `2026-10-05-fold-jumps.md` there).

**The bar is provisional at 100 samples.** An average of n regret-matching draws has a
per-action standard error of at most 0.5 / sqrt(n), which is 0.05 at 100, about the smallest
mixing error head to head has resolved. The real bar should be read off a mid rung at 20M, where
polishing to 60M tied, by re-running one with `--count-visits` (about 46 minutes on 3 threads for
12bb; not run here, because the brief capped this work at 20 minutes of training).

## The demo: 12bb (4,2,1), 4M with a snapshot at 2M

The recipe of `results/cfr/experiments/cap2_12bb_t421_20m_warm.json` (169 preflop classes, 6
postflop buckets with texture, equity 200, linear, frozen warm start of 100,000 from
`ladder169l/nolimit_12bb.pkl`, pruning after 10 percent), with only the iterations, the threads
(2, not 3) and the output changed, plus `--count-visits --visit-snapshots 2000000`. One run of
4M, so the 2M counts are a snapshot of the same run. 1,048.6 s of training at 0.256 ms an
iteration on a loaded machine; 69,659 nodes reached, 191 MB resident. Files in
`results/cfr/visit_counter_demo/`, the full report in `12bb_t421_report.txt` and `.json`.

    venv/bin/python scripts/cfr/visit_report.py \
        results/cfr/visit_counter_demo/12bb_t421_4m.visits.2000000.npz \
        results/cfr/visit_counter_demo/12bb_t421_4m.visits.npz

Average-strategy samples per reached node, node-weighted, then the reach-weighted 10th percentile:

| | nodes | p10 | p50 | p90 | under 10 | under 100 | under 1,000 | none | reach-wtd p10 |
|---|---|---|---|---|---|---|---|---|---|
| all, 2M | 69,173 | 0 | 77 | 3,165 | 25.6% | 53.3% | 80.7% | 10.3% | 11,830 |
| all, 4M | 69,659 | 1 | 155 | 6,711 | 20.6% | 44.5% | 73.1% | 8.5% | 26,022 |
| preflop, 4M | 4,056 | 15 | 3,225 | 30,946 | 9.5% | 16.2% | 35.0% | 6.9% | 12,072 |
| flop, 4M | 1,824 | 44 | 3,142 | 56,504 | 6.9% | 13.8% | 31.2% | 5.0% | 73,897 |
| turn, 4M | 18,979 | 1 | 88 | 5,610 | 26.0% | 51.5% | 77.7% | 9.8% | 19,399 |
| river, 4M | 44,800 | 1 | 142 | 4,037 | 19.9% | 45.3% | 76.3% | 8.3% | 4,300 |

The rarest lines, reach-weighted 10th percentile at 2M and 4M, and the share of play (by the reach
proxy) at nodes under 1,000 samples:

| line | nodes | rw p10, 2M | rw p10, 4M | play under 1,000, 2M | 4M |
|---|---|---|---|---|---|
| preflop, 2 raises | 2,028 | 1,008 | 1,866 | 9.8% | 4.7% |
| preflop, 3 raises | 338 | 1,046 | 2,280 | 9.2% | 4.4% |
| flop, 3 raises | 24 | 1,372 | 2,988 | 1.8% | 3.2% |
| turn, 3 raises | 72 | 820 | 1,657 | 13.1% | 3.9% |
| river, 2 raises | 7,320 | 384 | 812 | 26.7% | 11.9% |
| river, 3 raises | 72 | 220 | 447 | 92.1% | 26.9% |

What this shows:

- **The average hides a long tail, but the tail is mostly lines nobody plays.** Node-weighted, 44.5
  percent of reached nodes have under 100 samples at 4M and 8.5 percent have none (5,928 nodes,
  created as the traverser's and never entered by their owner's own play). Reach-weighted, only
  0.01 percent of play is at nodes under 100. So the old iterations-per-point figure (4M over
  69,659 is 57) is pessimistic about where play happens and silent about where it does not.
- **The rare tail is the river after raises.** Every line but two clears 1,000 reach-weighted
  samples at the 10th percentile by 4M; the river after two raises reads 812 and after three 447.
  That is the convergence doc's suspicion made concrete, and it is the line a budget should be set
  by on a deep rung.
- **Counts doubled where reach has settled, and stopped where the owner stopped playing.** On the
  69,173 nodes both snapshots reached the median ratio is 1.93x against 2.00x in iterations, and
  1.99x on the river. Preflop (1.79x) and flop (1.74x) are lower because 27.9 and 17.1 percent of
  their nodes got no new sample at all between 2M and 4M (median 253 and 144 samples held): lines
  whose owner's regret matching went to exactly zero, so their average froze at what early play
  left. They are not played, so they cost nothing against an opponent who stays on the tree, but
  they are exactly where a frozen early mix sits waiting for an opponent who forces the line.
- **Leg (a) passes at the provisional bar of 100 at both 2M (worst line 220) and 4M (447), so the
  bar does not discriminate on this rung.** That is consistent with 12bb being a mid rung, which
  was converged by 20M, but one rung cannot calibrate it. Visits scale with iterations where
  reach has settled, so 12bb at 20M would sit near 2,000 to 2,500 on its worst line (a projection,
  five times the 4M count, not a measurement). The converged level is an upper bound on the bar,
  not the bar, because 20M was sufficient there without being shown necessary. Legs (b) and (c)
  were not measured, as the brief asked, so the report's verdict is "not measured".

**Overhead with the counter on.** The off path is the old one (the golden test is identical). On,
it is two predictable branches and an increment inside a lock already held. A single-thread timing
on the small test game, 20,000 iterations, three alternations, read 0.50, 0.55 and 0.80 ms an
iteration off against 0.67, 0.57 and 0.58 on: the machine was loaded by the demo run and the noise
is larger than any difference, so I can say only that the cost is not visible at that resolution.

## Caveats from the review

The reviewer confirmed the counter does what it says, and these four limits are on how the counts
should be read.

- **The reach proxy holds only for self-play.** `avg_visits x regret_visits` is proportional to
  reach because each counter carries one player's reach and the two players are both the solver.
  Against a scripted opponent (`--opponent-archetype`, `--opponent-mix`) the two counters move
  together on our nodes, so avg visits equal regret visits and the product is one count squared.
  That carries the opponent's reach twice and our own not at all, so it is not a reach. The
  reach-weighted columns of such a run are not comparable with a self-play run's, and should not
  set a bar.
- **Linear and DCFR averaging shrink the effective sample.** `avg_visits` counts every sample that
  fed the average once, while linear averaging weights the sample at iteration t by t. With weights
  growing as t to the power gamma, the effective count (Kish's (sum w)^2 / sum w^2, for a node
  visited evenly through the run) is (2 gamma + 1) / (gamma + 1)^2 of the raw one: about 3/4 for
  linear, and 5/9 for DCFR's gamma of 2. The 0.5 / sqrt(n) argument for the bar should use that
  smaller n, so a raw count of 100 under linear is worth about 75 uniform samples.
- **`regret_visits` includes iterations that fed no average.** It counts the frozen warm phase and
  the iterations before `average_from`, while `avg_visits` does not. Its ratio to `avg_visits` is
  therefore not the opponent's reach on runs with either, and the reach proxy carries the
  same bias, which is roughly a constant factor per run but not across runs with different warm
  or `average_from` settings.
- **An out-of-range snapshot used to be skipped silently.** `--visit-snapshots` drops any value not
  inside the run's iterations (zero, a negative, or at or past the end, which the final write covers
  anyway). The trainer now prints a warning naming the skipped values, because the T and 2T pair is
  the reason to ask for a snapshot and a typo would otherwise show up only when the report is handed
  a file that was never written.

The visits file now strips only `.pkl` from `--output`, as `cfr.flat.flat_paths` does, so it always
sits beside the flat pair: `--output rung_0.5` used to write `rung_0.visits.npz`, which `rung_0.7`
would have overwritten.

## What is not done

- The bar in (a) is still a reasoned guess. The calibration below puts the converged level near
  1,700 on the worst line for the (4,2,1) six-class trees, but that is one rung's evidence and
  an upper bound, not the bar.
- Legs (b) and (c) have been measured on one rung only (the 70bb self-play rung below), and (c) on
  one LBR menu, where the rule asks for both.
- `--visit-snapshots` writes counts only, not a strategy, so (b) and (c) at T still need the
  T-iteration pickle from its own run.
- The reach-weighted view is a proxy, off by the chance probability of the owner's bucket, and
  only for self-play (see the caveats above).

## Calibration and the 10M check, 5 October night

**The calibration.** Two counted 20M runs with snapshots at 5M and 10M, on the visit-counter
module, outputs in `results/cfr/visit_calibration/` (untracked; moved from the visit-counter worktree on 6 Oct), logs in
`~/pokerbot-scratch/night5oct/`. Both are self-play, so the reach proxy holds. The 25bb run is the
real `cap2_25bb_t421_20m_warm` recipe (frozen warm start of 100,000, 3 threads, 155,101 nodes
reached) and the 70bb run is a cold (4,2,1) six-class rung (2 threads, 387,958 reached).
Reach-weighted 10th percentile of `avg_visits` on the worst line, from `visit_report.py` on each
file alone:

| rung | 5M | 10M | 20M | worst line |
|---|---|---|---|---|
| 25bb (4,2,1), warm | 735 | 1,735 | 3,863 | river after two raises |
| 70bb (4,2,1), cold | 657 | 1,758 | 3,484 | river after two raises (three at 20M) |

Visits roughly double with iterations on both, which means reach has settled on the rare lines
by 5M. The counts alone cannot say when the strategy has settled, which is why the two other legs
exist.

**The 10M check** (`~/pokerbot-scratch/check10m/`). The 70bb recipe trained again to 10M on its
own run (`selfplay_70bb_t421_10m.pkl`, 386,554 nodes reached against 387,958 at 20M) and played
against the 20M solve:

- Cross-tree gate (`tools/xtree-gate.sh`, 40,000 hands, seeds 0 1 2, check/call on a miss, no miss
  in either direction): **+0.3 ± 2.5 BB/100** for 10M against 20M (seeds +5.0, -0.7, -3.5).
- LBR at 70bb, four chunks of 8,000 hands on paired seeds (1000k+7), default menu, no bridge
  translation: 10M +30.3, 20M +27.4. Paired difference **+2.8 ± 16.5** (chunk differences -41.3,
  +0.7, +36.6, +15.4).

- Arena head to head (`scripts/chipzen_duel.py --arena-matches 5000 --workers 4`, seed 0, both
  seats v5f's ladder under `--deep-primary` with only the 70bb rung swapped,
  `~/pokerbot-scratch/h2h10m/`): **10M wins 50.1% ± 0.7**, 546,525 decisions against 547,047,
  no companion calls. This is leg (b) as the rule defines it, and it passes: a delta of 0.1 at
  the rule's ±0.7. One caveat on its reach: only the 70bb rung differs, and it plays only where the
  effective depth is nearest 70bb in ratio (about 59 to 84bb), so part of each match is the same
  bot on both sides. The 27 September head to head swapped three deep rungs.

So 10M and 20M are level on this rung on all three instruments. The gate and LBR alone would not
have been enough, because of their width. The gate
cannot see a 1-point match-win difference: on 21 September v5m against v5h read 51.1 ± 0.7 in
matches while reading -1.2 ± 2.5 chips a hand at 70bb. The LBR difference is too wide to see
anything under about 30 BB/100. And these are the two instruments that saw nothing between 20M and
60M on 27 September, when two head to heads agreed 60M was about a point stronger.

**What earlier results agree and disagree with it.**

- Agree, on the same kind of tree: node coverage stops growing by 20M on six-class trees (389,086
  entries against 390,110 at 60M), a warm 10M played level with a cold 20M (-0.7 ± 0.7 head to
  head), the mid rungs polished to 60M tied (50.3), v5s60 was level with v5s, and the 40-class gain
  at 20M was gone at 60M.
- Disagree, on bigger trees: lane Y (19 September) found the deep cap-2 rungs at 20M warm beat their
  10M solves on the same tree by +6.1 ± 2.2, +2.8 ± 0.9 and +4.7 ± 1.3 at 50, 70 and 100bb (but the 70bb
  pair does not reproduce on the 6 October gate, +1.9 ± 0.3 to the 10M; see `2026-10-06-visit-bar.md`), and the
  cap-2 18bb and 12bb rungs at 100M beat their 20M by +7.5 ± 3.0 and +12.2 ± 7.0. The 20-class
  histogram rungs reached 1.48M of 11.45M information sets at 20M and were under-trained.

**The exploiter rung and purified play (same night, `~/pokerbot-scratch/xrung10m/`).** Two gaps in
the check above: it played the rungs mixed while the live sets play `--purify all`, and it was a
self-play rung while the live sets' deep rungs train against a scripted station share. So the
self-play pair was played again purified, and v5xRR3's own 70bb rung (`br25_station_70bb_t421_20m`,
station share 0.25) was retrained at 10M with every other argument the same (1,957 s, 389,643
information sets against 390,376) and measured inside v5xRR3's ladder:

| comparison, 10M against 20M | result |
|---|---|
| self-play rung, arena, purified | 50.6% ± 0.7 of 5,000 |
| exploiter rung, arena, purified, seeds 0 and 1 | 48.7 and 49.9, pooled **49.3% ± 0.5** of 10,000 |
| exploiter rung, arena, mixed | 50.0% ± 0.7 of 5,000 |
| exploiter rung against the station archetype | 73.4% against 73.9%, ± 0.6 each |
| exploiter rung, cross-tree gate (mixed, 70bb only) | **+2.8 ± 0.8 BB/100 to 10M** (seeds +2.5, +4.3, +1.6) |

The self-play result holds purified. On the exploiter rung nothing separates the two: the purified
head to head leans 0.7 ± 0.5 points to 20M, which is under the rule's 1-point bar but cannot rule out
a sub-point gap, and its job, beating the station, is level. The gate favours 10M at 3.5 standard
errors, which the arena does not repeat, mixed or purified; it is a single rung at a fixed 70bb
with check/call on a miss, and I have no explanation for it, so it is not read as 10M being better.

**What follows.**

- On six-class (4,2,1) trees, trials and experiments can stop at 10M, which halves their cost.
- The two head to heads that found the 60M polish worth about a point were both on 20-class
  histogram rungs (v5iP's `hist20_70bb_t421_60m` against 20M, and v5m against v5h, both `hist20`).
  The one six-class polish, v5x60 (`br25_station_70bb_t421_60m`), read 49.4 head to head against
  v5x on 29 September, no gain. So on six-class trees no instrument has shown a gain past 10M.
  The 60M polish is a rule for histogram sets. Six-class self-play rungs can play at 10M, measured
  mixed and purified. Six-class exploiter rungs can be trialled at 10M; a set that will play keeps
  20M for now, because the purified head to head leans 0.7 ± 0.5 to 20M and the extra 10M costs
  about half an hour a rung.
- Cap-2, histogram and (4,3,2,1) trees are not covered. They need their own counts, and the
  history says they need more than 20M.
- A candidate bar for leg (a) is about 1,700 on the worst line, which is what both rungs had at the
  budget where the 70bb one was level. It comes from one checked rung and it may be higher than
  necessary, because 10M was not shown to be the smallest budget that ties.
