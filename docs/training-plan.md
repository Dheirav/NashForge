# Training plan — evolutionary search and PPO, heads-up first

**Status:** planned, not started. Written 15 August 2026.

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

## Phases

### Phase 0 — make the measurement trustworthy

The audit's Step 1, never carried out for networks.

- **Tests for `rl/`.** 1,917 lines, currently **zero coverage**. Minimum: chip conservation
  through the environment, observation shape and bounds, that the policy never emits an
  illegal action, that one PPO update runs without producing NaN. Training against an untested
  environment is how the previous round produced numbers nobody could trust.
- **Duplicate play.** Deal identical cards to both seats and replay with positions swapped, so
  card luck cancels between runs rather than being averaged over. The audit measured
  **±258 BB/100 over 600 hands** six-handed; this reduces variance far more than playing more
  hands. `cfr/play.py` alternates seats but does not duplicate cards — that is the piece to
  add, and it belongs in a shared harness rather than in each caller.
- **One benchmark harness.** Any agent against a fixed panel: random, always-call, and the
  **CFR agent**. Error bars on every figure, seats duplicated, hand counts sized from the
  measured noise floor rather than convention.

### Phase 1 — rebuild the observation

As decided above: 17 → 19, remove two redundant slots, add four card features. Delete
`engine.features.get_state_features` while here — it is a board-*blind* twin of the live path
that nothing currently calls but everything could, and it is exported from `engine/__init__.py`
where the next person will find it.

Re-run `scripts/audit_observation.py` afterwards. Effective dimensionality and postflop R²
should both rise; if they do not, the change did not do what this document claims.

### Phase 2 — evolutionary search, heads-up

Seeds, wall-clock budget ladder, measured against the Phase 0 panel.

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
before it was found. Any training or evaluation loop that reuses a table across hands must
rebuild it when a stack reaches zero. **Check `training/fitness.py` for this before Phase 2.**

**The machine is memory-limited, not CPU-limited.** 16 cores against 7.7 GiB, and WSL has been
terminated twice under memory pressure this week. Torch has CUDA available, so PPO can train
on the GPU; the evolutionary runs are CPU-parallel and are the ones to watch.

**Wall-clock budgets measure the machine.** Any budget-ladder experiment needs the quiet-machine
gate, and load should be sampled inside each training window rather than once per measurement —
see the crossover run's instrumentation.
