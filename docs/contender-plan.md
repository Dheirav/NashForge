# The Slumbot contender

Written 13 September 2026, after the taper experiment. It answers one question:
what to do next now that the training lever, the depth lever and the card
abstraction have all been measured and none of them moved the Slumbot number.

## The decision

Build a second solver for Slumbot only, with a deeper betting tree, and gate it
on the **lookup miss rate** rather than on the win rate. The six-action,
one-raise solver that every Phase 4 figure was measured against stays exactly as
it is, because it is the instrument the three-family comparison rests on and
widening it would invalidate every PPO and evolution checkpoint (their output
layers are six wide). The two goals stop blocking each other.

## Why the miss rate, and why depth first

The 200bb measurement on record is **−997.8 ± 396 mbb/hand** over 9,999 hands
(`results/slumbot/m1_200bb_250k.json`). Two counters came back with it and they
are different things:

| counter | what it counts | value |
|---|---|---|
| `lookup_miss_rate` | decisions at a history the solver has no entry for | **11.9%** (2,915 of 24,527) |
| `off_abstraction` | bets larger than three times pot and short of a shove | 609 |

A bet *size* never produces a lookup miss, because `slumbot/bridge.py` maps it
onto the sizes we have with the pseudo-harmonic translation. A second raise on a
street does, because the shipped solver has one raise per street and there is no
key for the node. At every one of those decisions `cfr_agent` falls back to a
uniformly random legal action, and these are re-raised pots, so they are the
expensive ones. So 11.9 percent is a measurement of the depth problem specifically,
and it is a count, which means it is tight: ±0.4 percent at 10,000 hands and
about ±1.3 percent at 1,000.

That is the whole reason to gate on it. The win rate is ±396 at 10,000 hands and
costs 12h20m at the measured 4.44 s/hand, so two solvers 200 mbb apart cannot be
told apart by it at any budget this project will spend. The taper week showed the
same thing from the inside: `[4,1]` and `[4,2]` exist, the baselines cannot rank
them and LBR is slack on all of them. Building solvers is now cheap and ranking
them is not, so the next step has to be one whose success is visible in a number
we can afford.

Width, meaning more than three bet sizes, is the opposite case. It never shows in
the miss rate, it only shows in the ±396, and it means changing `NUM_ACTIONS`
across ten files. It is the expensive change that is also the unmeasurable one,
so it waits until depth has been settled.

## What `[4,2]` actually is

`normalise_schedule((4, 2))` is one bet with all four sizes and **one re-raise**
carrying the two largest, two times pot and all-in. It is not four raises. It
covers "bet, raise" on every street and nothing deeper, so it removes every miss
at raise depth two and none at depth three or beyond. How much of the 11.9
percent that is, nobody has counted, and step 3 counts it.

Measured at 100bb on 11 September: 80,517 information sets reached of 1,283,568
on paper, 6,522,195 iterations in 71 minutes at 0.656 ms/iteration, 202 MB. The
one-raise tree grew 2 percent going from 100bb to 200bb (23,454 to 23,963), so
the 200bb build should cost about the same.

## Steps, with measured costs

**1. Make the bridge honest about the schedule.** Small, and without it step 3
lies. Three things:

- `_as_abstract` translates over `RAISE_FRACTIONS`, all three sizes, at every
  depth. At depth one under `[4,2]` only two-times-pot and all-in are legal, so a
  Slumbot re-raise of a third of the pot translates to half-pot, a code the
  solver never had at that depth, and misses for the wrong reason. It has to
  translate over `raise_sizes_at(schedule, raises_this_street)`.
- `SolverPlayer` defaults to `raise_cap=1` and `scripts/slumbot_measure.py`
  never passes anything else. Both should read the schedule from the pickle's
  `args`, the way `_strategy_depth` already reads the stack.
- Record misses **by raise depth**, so the run says where the remaining misses
  live rather than only how many there are. That histogram is what chooses the
  next taper, if there is one.

Tests for the translation and the depth histogram go in the bridge's own test
file. Nothing here touches the game or the solver.

**2. Train `[4,2]` at 200bb.** `--stack 400 --raise-cap 4 2`, native, the same
6,522,195 iterations as the 100bb build so the two are the same recipe. Expect
about 71 minutes; the run prints its own rate and ETA.

**3. One thousand hands against Slumbot, for the miss rate.** 74 minutes at the
measured rate. This is the gate, read two ways:

- the rate itself, against 11.9 percent, at about ±1.3
- the depth histogram: what fraction of the remaining misses are at depth three
  and beyond, which is what `[4,2,1]` would buy and `[4,2]` cannot

Do not read the win rate from this run. At 1,000 hands it is roughly ±1,250 and
means nothing, and a favourable-looking partial is exactly the stopping-rule
error `docs/EXTERNAL_BENCHMARK.md` warns about.

**4. Only if the gate passes, the full 10,000 hands.** 12h20m, `--resume` on, and
the result stands next to −997.8 ± 396 with the same caveat block. Pass means the
miss rate fell by more than the interval can explain and the histogram does not
say a third level would remove most of what is left. If it does say that, train
`[4,2,1]` first, because it costs one more training run and one more 74-minute
gate and not another 12 hours.

## What is not being done, and why

**The comparison instrument is untouched.** `nolimit_strategy.pkl` stays the
100bb one-raise 250k solver, and the contender is reached only through
`--strategy`, which is already how the 200bb solver is used.

**No internal head-to-head as a gate.** `[4,2]` against the one-raise solver
mostly measures the narrower solver playing at random when it is re-raised, and
the 2.4x overstatement of internal edges against external ones is on record. It
is worth an hour as a sanity check and it is not the decision.

**No bundling.** The 200-sample equity estimator and any width change are each a
separate retrain with their own gate. Two changes in one run produce a result that
cannot be attributed, which is the mistake `NEXT.md` item 1b already names.

**No new Slumbot run for the solvers that exist.** The 100bb tapers were never
going to be measured at 200bb, and 12 hours on a solver the miss rate cannot yet
speak for is the discipline `docs/retrain-plan.md` set: Slumbot last, and only
once the solver it measures is final.
