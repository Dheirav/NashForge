# What to do next

One page, kept current. [`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the full phase plan and its results. This
file is only the next thing to do.

**Last updated:** 11 September 2026 · `main` at `9912610` · 293 tests (~6m09s, collection ~3m24s)

---

## Where this stands

| | | |
|---|---|---|
| CFR | measured | Validated against Kuhn's −1/18 and exact Leduc exploitability. Produced the abstraction crossover, +0.916 ± 0.118 chips/hand at the 2560s budget |
| Evolutionary search | measured | Loses to the solver by 211.8 BB/100. Fifty generations are worth +43.9 ± 20 — small, separated, and invisible against a weaker opponent |
| PPO | measured | Loses to the solver by about 75 BB/100 at every rung. Flat: more training does not close it |

All three are measured, and **Phase 4 — the comparison the project's title promises — is done**
(`results/comparison/phase4_native.json`). One panel, 40,000 hands, a hands axis, in BB/100:

| family | hands | vs random | vs always-call | vs CFR |
|---|---|---|---|---|
| CFR (the solver, 250k) | — | +258.7 | +647.3 | — |
| evolution, 50 generations | 36,000,000 | +202.7 | −0.2 | **−211.8** |
| PPO | 500,000 | +191.2 | +372.6 | **−84.6** |
| PPO | 2,000,000 | +137.2 | +373.2 | **−72.5** |
| PPO | 8,000,000 | +226.8 | +329.1 | **−74.9** |

Every row on one panel, 11 September, measured against a solver trained by the **C++ core**
(`results/comparison/phase4_native.json`). CFR lookup miss rate 0.0% throughout.

**This table is a re-measurement and every conclusion survived it.** The native solver bucketing
is seeded from the cards rather than from Python's tuple hash, so it is a genuinely independent
implementation with different draws, in another language. Against the previous panel the same
figures were +245.9 / +603.4 for the solver, −200.9 for evolution and −79.7 / −73.5 / −72.0 for
PPO. **Every one moved by less than its own interval**, and the columns that structurally cannot
move — PPO and evolution against random and always-call, which never touch the solver — are
identical to the decimal. See `docs/retrain-plan.md`.

**Both learned families lose to the solver.** PPO by about 75 BB/100, evolutionary search by
about 200. Neither ever beat it: the earlier reading came from a panel whose CFR agent had
**4,000 iterations — about two minutes of training**.

**Evolutionary search still spent 36,000,000 hands to PPO's 500,000** — seventy-two times as many
— and is 127 BB/100 further behind. That comparison survives both the panel change and the
re-measurement on an independent solver, and is the firm result.

### Three claims the panel upgrade overturned

Figures in this section are the **v2 (Python-trained) panel's**, kept as the record of what that
upgrade changed. The live table above is the native panel's re-measurement.

| claim | measured against the 4k panel | against the 250k panel |
|---|---|---|
| PPO beats the solver at 8M | +36.4 ± 13 | **−72.0**, t = −10 |
| More training helps | ladder rises | **flat**: −79.7, −73.5, −72.0 |
| Evolution learned nothing transferable | +33.8 ± 37, no change | **+50.0 ± 20, improved** |

None were bad measurements. They were correct readings against an opponent too weak to
distinguish anything, and the two errors point in **opposite directions** for one reason: an
under-trained solver is far more exploitative than a converged one. The 4k agent beat random by
+383.6 and always-call by +719.6, where the 250k agent manages +245.9 and +603.4. That
exploitation flattered PPO's relative position and buried evolution's improvement underneath it.

It is the same equilibrium-versus-exploitation trade this project has now measured four times,
and the fourth occasion on which **changing the instrument overturned a finding rather than new
data doing it**.

**On evolution's fitness.** The finding that its ranking signal cannot be selected on stands —
repeatability is r = +0.12 at the real budget, and shared cards do not help. But "fifty
generations were largely drift" was too strong: selection on that weak signal still produced
**+43.9 ± 20 BB/100**, measurable once the opponent stopped drowning it out. A noisy ranking and a
real improvement are compatible; the earlier phrasing denied the second.

---

## Now — the next thing to do

**Both Slumbot steps are done, and the answer is that neither lever moved the number.**
Path A completed on 10 September: a 200bb solver trained to 250,000 iterations
(`results/cfr/nolimit_strategy_200bb_250k.pkl`, 3h30m, 23,970 information sets) and measured
against Slumbot over 9,999 hands (`results/slumbot/m1_200bb_250k.json`, 739 min).

| solver | stack depth | vs Slumbot | miss rate |
|---|---|---|---|
| 4,000 iterations | 100bb | −1750.2 ± 524 | 8.7% |
| 150,000 iterations | 100bb | −986.6 ± 374 | 10.4% |
| 250,000, corrected game | 200bb | **−997.8 ± 396** | 11.9% |

The difference between the last two is **−11.2 mbb/hand against a combined interval of ±545**,
which is not separated. Three improvements went into that gap and none of them showed: the all-in
fix, another 100,000 iterations, and matching Slumbot's stack depth. The 200bb retrain was still
worth doing, because the agent is no longer handicapping itself and the figure is now the honest
one, but it did not buy anything.

**What this says about where to go next.** The training lever is spent and the depth lever is
spent, so the binding constraint is the action abstraction: one raise per street and six card
buckets, against an opponent with an unrestricted betting tree. The rising miss rate is the same
message from another direction, 8.7 to 10.4 to 11.9 percent, because deeper stacks and a better
solver reach more nodes the abstraction cannot express.

**1. Card buckets: settled 11 September, and six is right at every budget tested.**
Six against twenty, wall-clock budgets over a 128-fold range, three seeds, played head to head
(`results/cfr/bucket_sweep_long.json`, `scripts/cfr/bucket_sweep.py`). Chips per hand to six:

| budget | 6 vs 20 | iterations, 6 / 20 |
|---|---|---|
| 40s | +3.307 ± 1.159 | 1,567 / 1,683 |
| 160s | +2.499 ± 0.473 | 5,242 / 5,900 |
| 640s | +1.372 ± 0.536 | 18,092 / 20,433 |
| 1280s | +1.423 ± 0.404 | 34,775 / 38,133 |
| 2560s | +0.497 ± 0.317 | 66,183 / 75,050 |
| 5120s | **+0.624 ± 0.259** | 134,500 / 145,442 |

**The gap declines and then plateaus around +0.5 to +0.6, still separated from zero.** The earlier
three-arm ladder stopped at 1280s with the gap falling by a factor of four, which read as an
approaching crossing. It is not one. At big blind 2 the residual is about 31 BB/100, so it is a
real edge rather than a rounding artefact. Fifty buckets was dropped after the first sweep: it lost
to twenty at every rung with no closing trend.

**Twenty buckets was not short of time.** It is cheaper per iteration at every rung and bought 7 to
13 percent more traversals at equal wall-clock, so the budget axis favoured the finer arm and it
still lost. Its disadvantage is the partition, not the compute. The docstring's worry that
wall-clock would unfairly penalise a finer abstraction was backwards, and is corrected there.

**Scope.** The top rung is 134,500 iterations against the shipped solver's 250,000, so this is 55
percent of production budget, not beyond it. The plateau across the last three rungs carries the
conclusion rather than arrival at production scale. Two of eighteen matchups trained under a load
imbalance, both in seed 0's top rungs, worst 1.4.

**So the card abstraction is not the lever, and the raise cap is the only untested dimension left.**

**1b. The card abstraction is noise-limited, and this qualifies 1. Measured 11 September.**

| | |
|---|---|
| equity estimate sd at 40 samples | **0.0667** |
| distance between adjacent bucket centroids | 0.101 to 0.170 |
| situations that change bucket on a re-roll at the same 40 samples | **42%** |

At 200 samples the sd falls to 0.0307 and at 1,000 to 0.0134.

**The noise in the estimate is about half the gap between adjacent buckets.** So
a large fraction of hands are placed by Monte Carlo error rather than by hand
strength, and that is a property of the estimator, not of the partition.

**Read the bucket sweep in that light.** Fifty buckets spaces centroids roughly
0.02 apart against noise of 0.067, more than three bucket widths, so assignment
at fifty was close to random. The sweep therefore measured **how many buckets our
equity estimator can resolve**, not how many buckets are worth having. Six won
because six is near the limit of what a 0.067 error can distinguish. Do not
quote it as "six buckets is correct" without that condition.

**What to do about it.** The 4.3x speedup means 200 samples now costs about what
40 cost before, so the precision is affordable. Whether it produces a better
solver is empirical and has the same shape as everything else here: train at 40
and at 200 on equal wall-clock and play them off. It changes the abstraction, so
it bundles with a retrain rather than going in quietly, and it must not be
bundled with the taper or a win will not be attributable.

**1c. Speed, 11 September: 32.4 -> 7.47 ms/iteration, 4.3x.** Two changes, both
committed and verified answer-for-answer. `score_hand_7` replaced an uncompiled
evaluator that was 68% of runtime across 6.4 million calls per 2,000 iterations;
the rollout's sampling moved inside the compiled loop. Four other routes were
tried and reverted, recorded in `4dfd175` so they are not tried again: suit
isomorphism, caching `_street_actions`, scoring showdowns, and dropping
`equity_samples`. The last of those turned out to point the wrong way entirely,
which is finding 1b.

The 250,000-iteration solver is now about 50 minutes rather than 3h30m, and a
5,120-second budget buys roughly 580,000 iterations rather than 134,500.

**2. The memory growth: found and fixed, 11 September.** `games/nolimit.py` memoised
`bucket_for` in `_bucket_cache` with no ceiling. Keyed on (hole, board) it spans roughly
1,326 × 2.1 million, so it never saturates: 2,800,227 entries and 491 MB by 60,000 iterations,
which is what put a 1280-second ceiling on the first sweep.

Capping it at `BUCKET_CACHE_LIMIT = 500_000` costs **5.2 percent** of iteration speed and removes
**90 percent** of the growth (18.50 to 19.47 ms/it; +721.1 MB to +72.6 MB over 60,000 iterations).
Clearing is safe rather than merely cheap: `bucket_for` seeds its generator from `hash(key)`, so it
is a pure function of hole and board and the memo only ever saved recomputation.
`test_nolimit.py` pins that property and pins that the cap binds.

Three diagnostics were needed because the first two were blind. An object-count histogram showed
nothing growing, because `gc.get_objects()` returns only GC-tracked containers and a dict of
untracked string keys and numeric values is one object whose count never moves. `malloc_trim`
recovered nothing, ruling out freed-but-unreturned pages. Measuring container **lengths** rather
than counting objects found it immediately.

**3. Raise cap 2, if anything external is to improve.****3. Raise cap 2, if anything external is to improve.** This is the untested lever and it is the
one the evidence now points at. It is also expensive: lifting the cap multiplies the betting tree,
and `check_raise_cap.py` already found that lifting it *widened* the internal gap, so this is a
question rather than a plan. Measure the tree size first and decide from that, because a run that
does not fit in memory is how this project lost six hours before.

**4. Two solvers, and the panel still does not move.** `nolimit_strategy.pkl` remains the
100bb 250k solver that every Phase 4 figure was measured against. The 200bb solver is used by the
Slumbot bridge only, through `--strategy`, and is never promoted. Internal comparison is at 100bb,
the external number is at 200bb, and each figure says which.

**5. Phase 5 — six-max.** After heads-up. Needs the `play_match` stack-drift fix, and the CFR
agent cannot serve as a benchmark there, so the panel loses its only opponent from outside the
lineage.

---

## Withdrawn, 8 September: the Phase 4 intransitivity

**It was the panel.** The August finding — that the three families could not be ranked — rested
on two edges taken against the 4,000-iteration solver: PPO level with it (+10.4) while it beat
the evolved genome by +370.1, against a measured PPO-vs-genome edge of only +23.9.

Re-measured on the converged panel, three seeds at 40,000 hands each:

| edge | BB/100 to the first named |
|---|---|
| CFR vs PPO (2M) | +73.5 |
| CFR vs evolution | +200.9 |
| **PPO vs evolution** | **+96.5** — per seed +75.2, +273.3, −58.9, spread 332.2 |

Transitivity predicts +127.4 for the third edge and it measured +96.5 ± 96.5 (SE across seeds).
**The shortfall is a quarter of its own error bar.** Nothing to explain.

The mechanism claimed in August goes with it. "PPO has eliminated the all-in" was stated against
a solver that jammed on 15.0% of decisions; a converged solver jams on **1.6%**, PPO on 0.2%.
The two now raise at 54.3% and 54.9% and PPO's raises are the larger, yet it takes +397.3 off a
calling station to the solver's +603.4. The difference is in *which spots*, which counting cannot
see. Open, not explained.

**Still true:** the two baselines cannot rank agents (see below), so do not quote a ranking taken
from a random or always-call column. That is a weaker claim than the withdrawn one and it is the
one the data supports.

Reproduce: `venv/bin/python scripts/diagnostics/check_intransitivity.py --hands 40000 --seeds 0 1 2`

---

## Closed, 2 September: the solver was under-trained, and it was worth half the gap

The solver that then held `nolimit_strategy.pkl` — now kept as `nolimit_strategy_4k.pkl` —
had **4,000 iterations**, about two minutes of
training at the crossover's measured 32 iterations/second. Retraining the same abstraction for
**150,000** iterations (2h56m) and re-measuring:

| | vs Slumbot | vs the 4k solver | vs random | vs always-call |
|---|---|---|---|---|
| 4,000 iterations | −1750 ± 524 | — | +377.2 | +722.9 |
| **150,000 iterations** | **−987 ± 374** | **+185.0 ± 13** | +280.1 | +827.7 |

**Training was the binding constraint, not the abstraction.** It halved the Slumbot gap and wins
the head-to-head by fourteen standard errors.

**Three things this turned up, all worth keeping:**

**Internal strength overstates external gain by ~2.4x.** +185 ± 13 BB/100 internally became
+76 ± 64 against Slumbot. Beating your own previous agent is evidence about a third party, not a
measurement of one.

**The baselines still cannot rank.** The 150k solver is decisively stronger yet scores *worse*
against random (+280.1 against +377.2). Ranking these two by their random score would have picked
the weaker agent. The baselines rank badly on their own; that much survived the
withdrawal above.

**~~`train_nolimit.py`'s evaluation disagrees with `evaluation.benchmark`.~~ Resolved 8
September** — see [`docs/training-plan.md`](docs/training-plan.md). The cause was
`cfr/play.py`'s `always_call_policy`, which indexed by position in the legal-action list rather
than by abstract action: with nothing to call the list is `[1,2,3,4,5]`, so index 1 is action 2,
**raise half pot**. The "calling station" raised every time checking was free. Every "vs always
call" figure the trainer printed was against a semi-aggressive opponent.

Fixed. The same solver now scores +605.0 through benchmark and +609.9 through `play_hands` — a
gap of 4.8 BB/100, inside noise, against 232.4 before. **The trainer's evaluation is trustworthy
again.**

Found on the way, and also fixed: the traversal game produced decision nodes after an all-in was
called, asking a check/call from players with no chips. Those filler actions extended the
information-set key, so the same hand keyed differently than in the engine. 250,000 iterations
now reach 23,470 information sets rather than 25,154 — the spurious nodes gone. A solver was
retrained for 4h48m expecting this to close the evaluation gap; it did not, and the widening gap
is what led to the baseline bug. `results/cfr/nolimit_strategy_v2_250k.pkl` is the first solver
trained on a game that matches the engine.

### That lever is now spent

At the time this read "more iterations, not less abstraction", and it was right — 4,000 → 150,000
was worth +185 ± 13. It has since been measured to exhaustion: **150,000 → 250,000 bought
+12.3 ± 7**, and information sets reached saturated. On the corrected game 250,000 iterations
reach 23,470 of 49,200, down from 25,154 before the all-in fix removed the spurious nodes.

Roughly half the abstraction is unreachable in practice under this betting tree, so further
iterations refine a fixed set rather than finding new ones. The next gain has to come from
somewhere else — which is why the Now section leads with 200bb.

Two things to fix before any longer run:

- **`train_nolimit.py` prints nothing during training and saves only at the end.** A 500,000
  iteration attempt ran six hours, reached ~4.9 GB, and was killed with nothing written. It needs
  a progress line and periodic checkpointing.
- **Memory, not time, is the ceiling.** The abstraction's table is 4.7 MB; the solver's
  bookkeeping reached 4.9 GB. 150,000 iterations peaked around 1.6 GB, so roughly 250,000 is what
  this machine can hold.

---

## Fixed 2–3 September: the two betting implementations, and what it cost

`training/fitness.py` sized a pot-fraction raise off the pot *before* the call where
`games/nolimit.py` sized it *after* — the standard convention — so every raise in the engine was
about 20% smaller than the same abstract action in the game the solver trains in. Fixed;
`tests/test_betting_equivalence.py` now asserts agreement across the enumerated betting tree
instead of characterising a gap.

PPO trains through that function, so all three seeds were retrained at 8M hands and re-measured.
**The Phase 3 finding survives** — the 2M rung against the CFR agent moved from +394.2 to +393.9 —
but **the seed spreads widened five- to six-fold** (2M vs CFR: 32.5 → 181.8). The number barely
moved; the confidence in it dropped a lot, and the cause is not established. See
[`docs/training-plan.md`](docs/training-plan.md).

**Cost:** `scripts/train_ppo.py` hardcodes its output directory, so the retrain overwrote the
August checkpoints. The pre-fix numbers survive as records; the agents behind them do not.

### Still to do, in order

1. ~~Retrain evolutionary search.~~ **Will not be done.** `preflight_training.py` refuses, and it
   is right: repeatability is r = +0.12 at the real 6,000-hand budget, and giving every genome the
   same cards does not help (spearman +0.01). The genomes are near-indistinguishable, so selection
   sorts noise and three hours would buy nothing. Phase 4's evolution row stays on the old raise
   convention and is marked as such.
2. ~~Re-run Phase 4 once evolution is refitted.~~ The precondition cannot be met — item 1 closed
   evolution as never-to-be-refitted. Phase 4 was re-run without it, on the corrected sizing and
   the six-seed PPO data; evolution's row carries † and stays on the old convention.
3. ~~Re-run Slumbot because the raise fix changed the agent.~~ That reason was wrong — the
   Slumbot pipeline never imports `training/fitness.py`, and `slumbot/bridge.py` already sized its
   raises off the pot after the call. Declining on those grounds was right at the time, and the
   grounds have since changed: **−987 ± 374 is stale now**, because the all-in fix means the
   current solver plays a game the old one did not. See the Now section above.
4. ~~Widen the seed count.~~ **Done** — six seeds, `results/ppo/phase3_endpoint_6seed.json`.

---

## After that

**Phase 5 — six-max.** After heads-up is complete. Note the CFR agent cannot serve as a
benchmark there, so the panel loses its only opponent from outside the lineage. Also needs the
`play_match` stack-drift fix described in [`docs/training-plan.md`](docs/training-plan.md).

---

## Closed — do not reopen without new information

- **Exploitability via LBR.** Four defects and three valuation models in, it still cannot beat a
  converged strategy. Stopped deliberately; the reasoning is in `BACKLOG.md` item 1.
- **Re-running the exploitability crossover.** Superseded by the head-to-head result, which
  answered the same question conclusively in four hours.

---

## The solvers on disk

Four now, and which one is `nolimit_strategy.pkl` has changed, so a figure without a named solver
cannot be placed.

| file | iterations | game | role |
|---|---|---|---|
| `nolimit_strategy.pkl` | 250,000 | corrected (all-in terminates) | **the panel opponent** |
| `nolimit_strategy_v2_250k.pkl` | 250,000 | corrected | same solver, kept under its own name |
| `nolimit_strategy_250k.pkl` | 250,000 | pre-all-in-fix | superseded |
| `nolimit_strategy_150k.pkl` | 150,000 | pre-all-in-fix | produced the −987 Slumbot figure |
| `nolimit_strategy_4k.pkl` | 4,000 | pre-all-in-fix | the old panel; every pre-8-September figure |

All are tracked — `.gitignore` negates `*.pkl` under `results/`, because a solved strategy is a
result and the 4,000-iteration one was once missing from the repository entirely.

---

## Picking this up cold

```bash
venv/bin/python -m pytest -q            # expect 233 passed; collection alone takes ~5 min
venv/bin/python scripts/audit_observation.py   # the 19-feature observation, both table sizes
venv/bin/python scripts/make_figures.py        # rebuilds every figure from the repo alone
venv/bin/python -m gui.main                    # play the CFR agent, through the benchmark's own loop
```

Two conventions worth knowing before starting a long run:

**Checkpoint at 10% of the run**, via `evaluation.checkpoint_every`. Ten saves whatever the
unit.

**Never checkpoint into `/tmp`.** WSL wipes it on restart, and doing so cost 49 minutes of
training on 14 August. Use `~/pokerbot-scratch` or `results/`.

And the habit that matters more than either: **before trusting a number, check its error bar
against the spread of the thing it is measuring.** Three separate results in this project have
looked like findings and been noise, and each was caught by a check that already existed rather
than by a new one.

---

## A note on the history rewrite

On 20 August every commit reachable from `main` was re-hashed, to strip `Co-Authored-By`
trailers. File contents were unaffected — verified by comparing all 104 commit trees against
the pre-rewrite history, with no mismatches — but **every SHA quoted before that date is
dead**. Three references in tracked files were remapped; if an old SHA turns up in a note
elsewhere, resolve it by subject against the current `main` rather than trying to check it out.
