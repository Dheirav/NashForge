# NashForge — results at a glance

One page. Every figure below is in `results/` as JSON and reproducible from the repository.
Units are BB/100 (big blinds per 100 hands) at big blind 2, measured over 40,000 hands per
matchup with duplicate seating.

---

## The question

Three families of poker agent — a game-theoretic solver, evolutionary search, and reinforcement
learning — measured against **one panel with one instrument**, so differences between them are
differences between the algorithms rather than between three ways of grading them.

---

## Result 1 — the abstraction crossover

Which way of describing a poker hand is better depends on how much compute you give it.

| training budget | equity iterations | made-hand iterations | chips/hand to equity | ahead |
|---|---|---|---|---|
| 40 s | 1,075 | 5,600 | −3.136 ± 0.729 | made-hand |
| 160 s | 3,808 | 19,758 | −1.531 ± 0.164 | made-hand |
| 640 s | 14,850 | 73,158 | +0.273 ± 0.203 | *not separated* |
| 2560 s | 60,117 | 288,050 | **+0.916 ± 0.118** | **equity, 7.8σ** |

Made-hand bucketing is about five times cheaper per iteration, so at short budgets it simply
does more of them and wins. Equity bucketing overtakes it once both have had enough iterations
for the finer description to pay for itself. **The crossing point is the finding** — the answer
to "which abstraction" is not an abstraction, it is a budget.

---

## Result 2 — the three families compared

| family | wall-clock | vs random | vs always-call | **vs CFR agent** |
|---|---|---|---|---|
| CFR (the solver) | — | +377.2 | +722.9 | — |
| evolution, 50 generations | 3.16 h | +192.7 | +0.5 | **−370.1** |
| PPO, 500k hands | 0.26 h | +204.1 | +278.6 | **−59.5** |
| PPO, 2M hands | 1.02 h | +221.5 | +293.5 | **+10.4** |
| PPO, 8M hands | 4.81 h | +135.4 | +467.9 | **−10.7** |

**PPO reaches parity with the solver in about one hour. Evolutionary search does not reach it in
three.** Both families sit on the same wall-clock axis, so this compares budgets and not just
endpoints. The solver has no row against itself — that is zero by symmetry, a structural
identity rather than a measurement.

Read the **vs CFR** column. It is the only opponent from outside both families' lineage, and its
seed-to-seed spread is 33–79 BB/100 against the baselines' 73–637.

---

## Result 3 — what each method actually learned

**Evolutionary search learned to exploit randomness, not to play poker.** +206 BB/100 against a
random opponent, nothing against a station that never folds, and still −370 against the solver
after fifty generations. It did learn; what it learned did not transfer.

**PPO's learning transferred.** Untrained networks scored −399.1, −385.9 and −366.3 against the
solver; the same three after 8M hands scored −34.8, +35.4 and −32.7. All 27 measured rows
improved.

**PPO's budget ladder is flat after 2M hands.** +394.2 at 2M against +373.1 at 8M, on spreads of
33 and 48 — three quarters of each run's wall-clock bought nothing measurable.

---

## Result 4 — the table does not rank, and why

PPO at 2M draws level with the solver head to head (+10.4), yet the solver takes nearly twice as
much off both baselines. Two agents level against each other extract very different amounts from
the same weak opponents, so **strength here is not a scalar** and no single ranking of the three
families exists.

Three explanations were tested. Two failed:

- **An instrument artefact** — measuring the solver through both families' code paths gives
  bit-identical results. Ruled out.
- **The one-raise-per-street cap** — lifting it *widened* the gap, −430.1 to −437.4. Ruled out.

The third is the answer, and it was settled by measuring the edge of the tournament graph that
nobody had: **PPO against the evolved genome.**

| edge | BB/100 to the first named |
|---|---|
| CFR vs PPO | +10.4 — level |
| CFR vs evolution | +370.1 |
| **PPO vs evolution** | **+23.9** — spread 80.8, one seed lost |

Transitivity predicted about **+360** for that edge. **PPO is level with the solver and also
level with the genome the solver beats by 370** — no single ordering permits both.

### The mechanism

Counting what each agent does against a station that never folds, ~250,000 decisions each:

| | fold | check/call | raise ½ | raise pot | raise 2× | all-in |
|---|---|---|---|---|---|---|
| CFR solver | 1.5% | 24.2% | 20.9% | 21.0% | 17.3% | **15.0%** |
| PPO, 2M hands | 3.5% | 34.1% | 35.3% | 13.2% | 13.8% | **0.1%** |

They raise at similar *rates* (74.3% vs 62.4%), so frequency is not it. **PPO has effectively
eliminated the all-in from its strategy.** Against an opponent who never folds the value is in
large bets — and PPO trained by self-play against snapshots of itself, which do fold, so it
never met an opponent worth jamming into. Against the solver that costs nothing and they are
level; against anything weak it leaves the value uncollected.

This is the audit's "strong but exploitable" prediction made specific: **self-play optimises for
a peer and produces a policy that cannot punish a weak opponent.**

---

## Why these numbers can be believed

A solver that has converged to the wrong thing looks exactly like one that has converged, so the
instrument is validated before any result is quoted.

- **Kuhn poker** has an analytically known value of −1/18. The solver reproduces it.
- **Leduc Hold'em** is small enough to traverse exactly, so exploitability is *computed*, not
  estimated, and falls toward zero.
- **No-limit** cannot be traversed. Local Best Response was tried as a lower bound and, after
  four defects fixed and three valuation models, still could not beat a converged strategy. That
  investigation was **closed with no usable bound** — no-limit has no exploitability figure here,
  and the report says so rather than substituting a flattering one.
- **233 automated regression tests.**

### Four measurement failures, all reported

1. **The audit of 12 August.** The old fitness function scored the wrong player and the deck
   re-dealt the same two hands every hand. An untrained random network scored +451 BB/100 under
   it. 89 training runs and every previously published report were **withdrawn**.
2. **A curve that was noise.** A per-generation panel score appeared to rise from +111 to +214
   BB/100; across eleven readings it scattered with σ = 56 against a measurement error of 57 —
   indistinguishable from a constant.
3. **A benchmark that had quietly become random.** A row reported the evolved agent beating the
   solver by +60.8 BB/100 beside a **74.3% lookup miss rate**. Re-measured at 0.0%, it read
   −370.1 and the verdict changed from "improved" to "no change".
4. **An order-dependent instrument, found on 20 August.** A panel score depended on which
   matchups had been measured before it — the same matchup read −28.9, −29.5 and −3.9. Found not
   because a result looked wrong, but because *a fix for a smaller version of the bug failed its
   own test*, which exposed two further layers. Re-measuring moved every figure less than its own
   seed spread, and the seed spreads tightened.

Each was caught by a check that already existed. **A measurement that is too coarse or subtly
wrong does not return "no result" — it returns a plausible one.**

---

## Seeing it run

```bash
venv/bin/python -m gui.main                  # play the solver yourself
venv/bin/python -m gui.main --opponent random
```

The left panel shows the agent's **actual mixed strategy at the node it just acted on** — read
from the agent itself, not recomputed alongside it. Equilibrium play is a distribution over
actions, not a move, and this is where that becomes visible.

The viewer runs through `evaluation.benchmark`'s own loop, so the game on screen is the game the
measurements score — the same mask, the same solver tree, the same settle.

## Reproducing the numbers

```bash
venv/bin/python -m pytest -q                          # 233 tests, ~9m30s
venv/bin/python scripts/endpoint_test_ppo.py --seed 0 1 2   # Result 3
venv/bin/python scripts/phase4_comparison.py               # Result 2
venv/bin/python scripts/make_figures.py                    # every figure
venv/bin/python scripts/diagnostics/check_instrument.py    # the instrument check
```
