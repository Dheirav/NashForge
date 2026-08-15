# NashForge — training plan: evolutionary search and PPO, heads-up first

**Status:** Phases 0–2 complete. Written 15 August 2026, last updated the same day.

The goal is a comparison: how close do evolutionary search and policy gradient get to a
solver-derived strategy, given the same budget on the same engine? Heads-up first, six-max
after, so that both methods can be measured against the CFR agent.

---

## Why this is worth doing now

Every previous attempt in this repository measured agents against **other agents bred on a
broken metric** — self-referential, which is how a reported best of 5213 BB/100 survived 89
training runs. [`CODEBASE_AUDIT.md`](../CODEBASE_AUDIT.md) has the details.

What exists now that did not: a **CFR agent as an independent yardstick**. It was validated
against Kuhn poker's analytic value of −1/18 and against exact exploitability on Leduc, and it
shares no lineage with anything a GA or PPO run will produce. That turns this from another
round of tournaments into a comparison with a reference point.

Heads-up first is not just variance reduction. It is the only table size where the CFR agent
can serve as the benchmark at all — the solver work is heads-up throughout.

---

## The observation: audited, 15 August

Before planning training, the 17-feature observation was measured rather than assumed.
1,500 sampled decision states per table size, true equity by Monte Carlo at 400 samples,
reproduced by `scripts/audit_observation.py`.

### It carries six dimensions in seventeen slots

| | heads-up | 6-handed |
|---|---|---|
| components explaining 90% of variance | **6** | **6** |
| live slots | 16 of 17 | 17 of 17 |

`players_in_hand` has a standard deviation of **exactly 0.0000** heads-up — it is always 2.
Two pairs are perfect duplicates: `players_behind`/`opponent_all_in` at r = −1.000 (heads-up
only) and `stack_normalized`/`commitment` at r = −1.000 (both sizes). Six-handed,
`players_behind`/`players_in_hand` sit at r = +0.979.

### All card information is in one slot

Predicting a state's true equity:

| | heads-up | 6-handed |
|---|---|---|
| from all 17 features | 0.421 | 0.481 |
| from `hand_strength` alone | 0.238 | 0.219 |
| **from everything except `hand_strength`** | **0.013** | **0.024** |

Remove that one feature and the other sixteen know essentially nothing about the hand.
Postflop the concentration is starker: all features reach 0.475, `hand_strength` alone
reaches 0.423.

### And that slot is lossy in a way training cannot fix

Grouping postflop states by near-identical `hand_strength` — states the agent physically
cannot tell apart — and measuring the true equity within each group:

| `hand_strength` | n | equity range | std |
|---|---|---|---|
| 0.73 | 38 | **0.907** | 0.173 |
| 0.58 | 43 | 0.890 | 0.253 |
| 0.60 | 35 | 0.861 | 0.231 |

The worst group spans 0.907 of equity: two hands the agent receives as an identical input can
be a 5% underdog and a 95% favourite. This is the decisive statistic, not the R² figures
above — those are linear fits and understate what a network could extract, whereas identical
inputs are an information limit no model escapes.

The cause is known and not accidental. Postflop, `hand_strength` is
`made_hand_strength(hole, board)` — scoring only the hand made so far. It is the same signal
the CFR work measured as **provably blind to draws**: on a two-heart board, the nut flush draw
and the same overcards without it are the same number. The
[abstraction crossover](abstraction-crossover.html) found that blindness costs real chips above
roughly ten minutes of training. The network observation has been carrying it the whole time.

### The fix is cheap, and was measured

Four binary features — flush draw, open-ended straight draw, paired board, three-to-a-flush —
computed from suit counts and rank gaps, no simulation:

| | before | after |
|---|---|---|
| R² overall | 0.421 | **0.503** |
| **R² postflop** | 0.475 | **0.637** |

A 34% relative gain postflop. The within-group spread falls only 0.168 → 0.158, so draws
explain part of the blindness rather than all of it — kicker quality and board interaction
remain invisible. That is a reason to expect more from a richer card representation later, not
a reason to skip the cheap win now.

---

## What to do about the features

**Remove two slots. No information is lost.**

- `commitment` — r = −1.000 with `stack_normalized` in both table sizes; algebraically the
  same number, since stack + contributed = starting stack.
- `players_in_hand` — constant heads-up, and 97.9% explained by `players_behind` six-handed.

**Keep `players_behind` and `opponent_all_in` both**, despite being perfect duplicates
heads-up. They are independent six-handed, and one shared layout across table sizes is worth
more than one wasted slot — the cost is a few weights, and it keeps the two configurations
comparable.

**Add the four draw and texture features.** 17 → 19 slots that carry more than the original
seventeen did.

**Do not add Monte Carlo equity per decision.** It costs ~10.6 ms per call at 400 samples,
against ~8 µs for made-hand strength. The CFR work measured the same trade-off from the other
side: equity bucketing costs 44.05 ms per solver iteration against 8.11 ms, a factor of 5.4.
Per-decision equity in a training loop making millions of decisions is not affordable, which
is exactly why the draw features matter — they recover much of what equity knows for nothing.

**Optional, unmeasured:** an "equity if I improve" scalar, or a two-card lookahead. Worth
testing after the cheap features land, not before.

This invalidates every saved genome. All of them came from the invalidated pipeline, so
nothing of value is lost.

---

## Decisions taken, 15 August

| | Decision | Why |
|---|---|---|
| Feature change | **Approved** — 17 → 19 | Measured; invalidates saved genomes, all of which came from the invalidated pipeline |
| Layout | **One shared layout** for both table sizes | Two layouts re-open the exact crack the audit found bugs in — `FeatureCache` and `get_state_vector` had drifted apart. Costs two dead slots heads-up |
| Budget axis | **Hands played**, not wall-clock | GA is CPU-parallel and PPO is not; wall-clock would compare hardware as much as algorithms. Wall-clock is still recorded alongside |
| PPO device | **CPU**, pending a profile | The network is a small MLP over 19 inputs; the Python engine is almost certainly the bottleneck. GPU adds a second memory pool on a box that has died twice from memory pressure |
| PPO self-play | Snapshot every ~10 updates, pool of last 5–10 | Sample from the pool most of the time, with some probability of facing the current policy |

## Progress

Updated as work lands. "Blocked" means waiting on a decision, and the decision is named.

| | Item | State |
|---|---|---|
| 0a | Tests for `rl/` | **done** — 9 tests, `tests/test_rl.py` |
| 0b | Duplicate play | **done** — `cfr/play.py`, ~14% noise reduction |
| 0c | Benchmark harness | **done** — `evaluation/`, 9 tests |
| 1 | Rebuild the observation, 17 → 19 | **done** — effective dimensions 6 → 9 |
| 2 | Evolutionary search, heads-up | **done** — learned to exploit randomness, nothing transferred |
| 3 | PPO with self-play, heads-up | **unblocked — next**; still needs snapshot pooling built |
| 4 | The comparison | blocked on 3 |
| 5 | Six-max | blocked on 4; also needs the `play_match` stack-drift fix below |

## Phases

### Phase 0 — make the measurement trustworthy

The audit's Step 1, never carried out for networks.

- **Tests for `rl/`.** 1,917 lines, currently **zero coverage**. Minimum: chip conservation
  through the environment, observation shape and bounds, that the policy never emits an
  illegal action, that one PPO update runs without producing NaN. Training against an untested
  environment is how the previous round produced numbers nobody could trust.
- **Duplicate play.** *Done, 15 August.* `alternate_seats` swapped the policies but drew fresh
  cards each time, so position cancelled and card luck did not. `_play_one` now records each
  chance outcome and the replay reuses it, so both policies hold the same cards against the
  same opposing cards. On by default; `duplicate=False` reproduces the old behaviour.

  **It buys about 14%, not the large factor the audit implied.** Per-hand outcomes swing by a
  full ±200 stack depending on whether an all-in happened, and that is driven by the action
  sampling, which sharing cards cannot cancel. It is free and strictly better, so it stays on
  — but hand count remains the real variance lever, and coupling the action stream is the next
  option if more is ever needed.

  Guarded by two tests: that the noise drops, averaged over seeds because a single run's
  standard error is itself noisy; and that the *expectation* does not move, since a duplicate
  run that drifts off a symmetric matchup's true zero would silently corrupt every comparison
  built on the harness.
- **One benchmark harness.** Any agent against a fixed panel: random, always-call, and the
  **CFR agent**. Error bars on every figure, seats duplicated, hand counts sized from the
  measured noise floor rather than convention.

### Phase 1 — rebuild the observation — DONE, 15 August

17 → 19: `commitment` and `players_in_hand` removed, four draw and texture features added,
`get_state_features` deleted. Re-running `scripts/audit_observation.py` confirms it did what
this document claimed:

| | before | after |
|---|---|---|
| effective dimensions | 6 of 17 | **9 of 19** |
| dead slots (std ≈ 0) | 1 | **0** |
| perfect duplicate pairs | 2 | 1 (kept for six-max) |
| R² against true equity | 0.421 | **0.499** |
| R² postflop | 0.475 | **0.633** |
| within-group equity std | 0.175 | **0.086** |

The last row is the one that matters, and measuring it required correcting the audit. It had
grouped states by `hand_strength` alone — which *was* the entire card signature and no longer
is. Grouped by all five card features, states the agent genuinely cannot distinguish now
differ in true equity by half as much. Grouping on strength alone would have understated the
gain while appearing to measure the same thing.

**The change needed nine coordinated edits, not the four predicted.** The Phase 0a tripwire
caught `PokerEnv.OBS_SIZE` and `PPOConfig.obs_size`; the failing suite caught three more that
nothing pointed at: `FeatureCache.__slots__`, whose declared attribute list rejected the two
new cache fields on assignment; `training/config.py`'s `input_size`, which was still building
networks with 17 inputs; and a hardcoded `GENOME_SIZE = 3430` in the tests. That constant is
now derived from the network config, since a written-down width is exactly what disagreed with
reality here.

### Phase 2 — evolutionary search, heads-up — DONE, 15 August

Fifty generations, population 30, **24,000 hands per genome** — a budget set from the measured
noise floor rather than convention. Re-scoring the same population under different hands moves
a genome by 136 BB/100 at 2,000 hands, 66 at 8,000 and 31 at 24,000.

**The endpoint result.** Final genome against an untrained one from the same initial
distribution, both against the same panel at 40,000 hands (±14 BB/100):

| opponent | untrained | after 50 generations | difference | |
|---|---|---|---|---|
| random | −13.4 ± 14 | **+192.7 ± 15** | **+206.1 ± 39** | improved |
| always-call | −8.1 ± 14 | +0.5 ± 4 | +8.6 ± 28 | no change |
| CFR | −403.9 ± 13 | −370.1 ± 14 | +33.8 ± 37 | no change |

**Evolutionary search learned to exploit randomness, not to play poker.** It punishes an
opponent that folds and raises at random by 206 BB/100, gains nothing against a station that
never folds, and is still beaten by the solver by 370 BB/100 after fifty generations. That is
a sharper finding than the audit's prediction that the method would simply plateau — it did
learn, and what it learned did not transfer.

Only the panel makes that visible. Self-play fitness sat near zero throughout, as the zero-sum
property requires, and says nothing about whether anything was learned.

### Phase 2's three false results, and what caught each

Every one of them looked like a finding, and each was caught by a check that already existed.
Recorded because the pattern is the argument for the framework, more than any single number in
it.

**The per-generation panel curve.** Taken over 3,000 hands, ±57 BB/100, and read during the run
as rising from +111 to +214. Across eleven readings it scattered with a standard deviation of
56 — indistinguishable from a constant. A measurement that coarse does not return "no result";
it returns a plausible shape. The endpoint test at 40,000 hands found the real effect the
curve could never have resolved.

**"The evolved agent beats a game-theoretic solver."** The CFR row first read +60.8, alongside
a 74.3% lookup miss rate. The miss-rate counter exists precisely so a benchmark that has
quietly become a second random opponent shows up as a number. In the previous regime this
would have been published.

**"Half the abstraction is unreachable."** The explanation offered for that miss rate — that
the solver covers 47% of its information sets at 4,000 iterations and 51% at 59,050, so a
network opponent lands off its trajectory and more training cannot help — was itself wrong,
and was committed. Nothing was missing: every lookup found its key. The solver stores one
probability per *legal action at a node*, so arrays are mostly length 2 or 5, and the harness
discarded anything that was not length 6. That was 77.5% of successful lookups. The tell was
available and misread — a 100% hit rate against a random opponent should have ruled out
"structurally unreachable" immediately.

### Phase 3 — PPO with genuine self-play, heads-up

One thing needs building first. PPO currently trains against `RandomOpponent`, or against a
Hall of Fame pool that is **empty** — and would be tainted if it were not, since every genome
in it was bred on the broken metric. The audit is specific that it should train against
current and past versions of itself, so periodic policy snapshots into the opponent pool is
the work.

### Phase 4 — the comparison

Both methods on the same budget ladder, both against the same panel, seeds and intervals
throughout. This is the deliverable, and it extends the existing report rather than starting
a new one.

### Phase 5 — six-max

After heads-up is complete. Note that the CFR agent cannot serve as a benchmark there, so the
panel loses its yardstick and the comparison becomes relative again. Worth planning separately
rather than assuming the heads-up design transfers.

---

## What to expect, stated in advance

The audit predicts both outcomes, and recording them now is what makes them findings rather
than surprises later.

**Evolutionary search will plateau.** It receives one scalar per genome per generation and
performs no credit assignment, so it cannot learn "in this spot, this action". Better features
raise the plateau; they do not remove it.

**PPO will produce a strong but exploitable bot.** Self-play policy gradient does not converge
to a Nash equilibrium in imperfect-information games. That is a property of the method, not a
bug to be found.

The value is not beating CFR. It is measuring *where* each method plateaus and *by how much*,
against a benchmark that does not share their lineage.

---

## Hazards

**`reset_hand()` does not restore stacks.** Once a player busts, every subsequent hand is
instantly over with no player to act, and a loop that only calls `reset_hand()` spins forever
producing nothing — silently, with no error raised. This hung the feature audit's sampler
before it was found.

*Checked, 15 August: the existing training paths are safe.* `training/fitness.py` never calls
`reset_hand` — its game pool calls `game.__init__` with fresh stacks per hand, which is the
correct cash-game semantics. `training/self_play.play_match` reuses a table but guards it,
resetting every stack once fewer than two players have chips. New code that reuses a table
still needs the guard; the existing code has it.

**Six-max stack drift in `play_match`, for Phase 5.** That guard fires only when fewer than
*two* players remain solvent. Six-handed, a player who busts stays at zero while the other five
play on, so a long match drifts from a cash game toward a tournament with progressively unequal
stacks. Per-hand chip deltas stay correct — `hand_start_stacks` measures from the top of each
hand — but the *game being played* changes as it goes, and short stacks play differently.
Heads-up is unaffected: one bust leaves one solvent player, the guard fires, both stacks reset.
Worth resolving before six-max evaluation, not before heads-up.

**The machine is memory-limited, not CPU-limited.** 16 cores against 7.7 GiB, and WSL has been
terminated twice under memory pressure this week. Torch has CUDA available, so PPO can train
on the GPU; the evolutionary runs are CPU-parallel and are the ones to watch.

**Wall-clock budgets measure the machine.** Any budget-ladder experiment needs the quiet-machine
gate, and load should be sampled inside each training window rather than once per measurement —
see the crossover run's instrumentation.
