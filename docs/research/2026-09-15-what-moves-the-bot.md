# What actually moves this bot: the answer from four reviews

Written 15 September 2026, about 00:30 IST, after the lossless-preflop retrain lost its
gate. Four reviews were run in parallel and their full reports sit beside this file:
`2026-09-15-solver-averaging-audit.md` (our own C++ read line by line),
`2026-09-15-cfr-convergence-review.md` (the literature on sampled CFR at rare nodes),
`2026-09-15-strength-levers-review.md` (what moved published bots, ranked for our compute)
and `2026-09-15-exploitation-review.md` (beating a weak field with little data). This page
is the synthesis and the plan. Where a reviewer's claim is inference rather than a paper,
the source file says so; here I only keep what our own measurements agree with.

## The problem we were facing, and its actual cause

The 169-class preflop lost the same-tree gate at every budget (−15.8 ± 3.8 at 250k,
−5.7 ± 1.5 at 1M, −4.4 ± 1.8 on the cap-2 tree at 3M), while the replay showed it folding
exactly the hands that lost to Blueprint. Reading the strategy explained the contradiction:
facing a shove it was 50/50 in every hand class and jagged between neighbouring hands, which
is what an unconverged average looks like, not a tighter one.

The audit found why, and it is not "too few iterations" in the simple sense. Three things
compound:

1. **The average strategy is accumulated only where a node's owner reaches it, unweighted.**
   That is the correct external-sampling estimator, but it means a node behind an action the
   owner rarely takes (a three-bet shove) collects a few near-uniform samples early and then
   almost nothing, while its regrets keep converging because the traverser enumerates every
   action. A node never averaged at all is returned as an exact uniform, which downstream is
   indistinguishable from a deliberate 50/50 and invisible to the miss counter.
2. **Linear averaging existed in the C++ but Python could not reach it**, and it would not
   have worked anyway: the discount was applied once per visit at the current iteration's
   rate rather than cumulatively since the node's last visit, so at a rarely visited node
   every rule collapsed to vanilla. That was invisible on Leduc, where every node is visited
   every iteration, which is why the rule comparison in `update_rules_leduc.json` never saw
   it.
3. **A preflop all-in is scored by one sampled runout**, so every regret sample at the shove
   node carries ±100bb of board noise on top of the scarcity.

Both code faults are fixed tonight: `--update-rule linear` on the trainer, and the discount
now covers the whole gap since a node was last touched, in the C++ and the Python reference,
pinned by a test. The literature backs linear weighting under sampling specifically (Brown
and Sandholm 2019: discounted MCCFR beats vanilla in HUNL; CFR+'s regret floor does not
help with sampling), and Pluribus additionally skipped averaging for the first part of the
run. The first experiment is queued: the 169-class one-raise rung at a million iterations
under linear, played off against tonight's vanilla million and six-class million. The
confirming reading is mechanical before it is a win rate: adjacent-hand fold jumps at the
shove node under 0.1 rather than 0.42, AA and KK calling above 0.95, and the gate at or
above zero.

So the lossless preflop was the right diagnosis and a badly served one. It stays. What
changes is the solver's bookkeeping under it.

## Overall improvement, ranked

The strength review's framing is worth keeping in front of us: always-fold loses 750
mbb/hand heads-up, and we are at −997 ± 396 against Slumbot. At the mean, the bot is
worse than folding every hand, so it is bleeding chips with the hands it plays rather than
playing a coarse equilibrium. That reframes the order: fix what loses chips before
refining what wins them.

**Tier 1, this week, low risk.**

- **Linear averaging with the cumulative discount** (done, running). Every published bot
  weights late iterations more; ours did not, at exactly the nodes that decide big pots.
- **Never miss on re-raises.** Cap-2 at every depth with all-in as the third raise and every
  re-raise translated over the schedule's own sizes. The 11.9 percent Slumbot miss rate is
  the direct cost of the one-raise tree, and the bridge now reads the schedule from the
  pickle and counts misses by depth, so the 200bb cap-2 contender training tonight gets an
  honest 1,000-hand miss-rate read.
- **Purification postflop, preflop left mixed.** Tartanian7 measured +17 to +25 mbb/h
  against Slumbot-class bots from taking the argmax of the average strategy postflop; its
  stated purpose is to compensate for an unconverged blueprint, which is our situation.
  A quarter day, no compute, and it can be measured on the same-tree gate.
- **Split the Slumbot loss** by miss against hit, street and position from the existing
  logs. Half a day, and it says which of the above is the leak.

**Tier 2, next two weeks, medium risk, and the largest documented gain.**

- **River endgame solving on the exact hand.** Solve the river subgame with the blueprint's
  ranges as priors, the opponent's actual bet size added to the tree, over the 1,081 exact
  hands, with about 1,000 CFR+ iterations. Ganzfried and Sandholm measured +29 to +87 mbb/h
  on river hands from an already strong, purified base; ours has a six-bucket river, so the
  headroom is larger. It also removes river card abstraction and river off-tree misses in
  one stroke. Two to three days in C++, seconds per river decision, well inside the
  30-second clock. Unsafe re-solving, not safe: the 2017 measurements and every later bot
  agree.
- **Opponent exploitation with measured triggers, done properly.** The two rules we have
  are the right shape. The review's sample-size arithmetic says our 100-bet gate is two to
  four times more conservative than it needs to be (45 bets separate a 25 percent folder
  from a 45 percent one at power 0.8), so a sequential trigger gets the exploit online a
  day earlier. The structural version is a data-biased response per opponent (Johanson and
  Bowling 2009, which works at hundreds of hands where restricted Nash needs a hundred
  thousand), solved overnight from the equilibrium's regrets and swapped in by name. Three
  to four days, and it needs per-node counts logged first.

**Tier 3, the month.** Fifty to two hundred imperfect-recall postflop buckets with the
169 preflop, which the papers put at +25 mbb/g in limit and which every published bot
has; 100M discounted-CFR iterations (about nine wall-hours on eight cores); then turn
re-solving Modicum-style, which took a 4-core laptop from −11 to +11 against Slumbot.

**Not worth doing at this scale**, and the reviews are unanimous: potential-aware or EMD
buckets (a second-order refinement measured at 5,000 buckets), and board texture folded
into six buckets, which multiplies the key space and thins every key. Our own bucket sweep
already said six was right at our budget; the reviews add that both arms of that sweep
were probably unconverged, so it is a statement about density, not about buckets.

## The plan for the week

1. Tonight: linear-averaging experiment on the one-raise rung; Slumbot 1,000 hands with
   the 200bb cap-2 contender for the miss rate. Both queued.
2. Tuesday: if linear closes the gap, retrain the ladder under linear with the 169
   preflop; purify postflop; gate at 40,000 hands; swap between fixtures only on a win.
3. Wednesday and Thursday belong to the submission. The river solver starts after it.
