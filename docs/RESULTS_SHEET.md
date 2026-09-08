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

| family | hands | vs random | vs always-call | **vs CFR agent** |
|---|---|---|---|---|
| CFR (the solver, 250k) | — | +245.9 | +603.4 | — |
| evolution, 50 generations | 36,000,000 | +202.7 | −0.2 | **−200.9** |
| PPO | 500,000 | +191.2 | +372.6 | **−79.7** |
| PPO | 2,000,000 | +137.2 | +373.2 | **−73.5** |
| PPO | 8,000,000 | +226.8 | +329.1 | **−72.0** |

**Both learned families lose to the solver**, PPO by about 75 BB/100 and evolutionary search by
about 200. Neither beats it at any budget.

**Evolutionary search spent 36,000,000 hands to PPO's 500,000 — seventy-two times as many — and
is 121 BB/100 further behind.** That is the firm comparison: both families moved together when
the panel changed, so it does not depend on which solver holds the seat.

The axis is **hands**, not wall-clock. An earlier version of this sheet used wall-clock and said
PPO reached parity "in about an hour". The identical 8M-hand run read 4.81 h on a quiet machine
and 10.42 h sharing cores with another job, so that axis was measuring the machine. Hands are
exact and are what both families actually spend. The solver is off the axis entirely: it
traverses a tree rather than playing hands, and here it is the opponent rather than a competitor.

Read the **vs CFR** column. It is the only opponent from outside both families' lineage, and its
seed-to-seed spread is three to ten times tighter than the baselines'.

---

## Result 3 — what each method actually learned

**Evolutionary search learned to exploit randomness, and a little else.** +202.7 BB/100 against a
random opponent, nothing against a station that never folds, and −200.9 against the solver after
fifty generations. Its gain over an untrained genome from the same distribution is
**+50.0 ± 20 BB/100** — small, but separated from zero.

That last figure was previously reported as +33.8 ± 37, "no change". It was measured against a
solver with two minutes of training, whose exploitation of a weak opponent was large enough to
bury the difference. A better opponent made a real effect visible rather than hiding one.

**PPO learns more, and still loses.** Untrained networks score around −250 against the solver and
about −75 after eight million hands, so the training is doing something substantial. It is not
enough to reach parity with a converged solver.

**PPO's ladder is flat.** −79.7 at 500,000 hands, −73.5 at 2,000,000, −72.0 at 8,000,000. Sixteen
times the training buys roughly 8 BB/100, well inside the seed spread. An earlier version of this
sheet said more training helped; that was an artefact of measuring against an under-trained
opponent.

---

## Result 4 — a finding withdrawn: the ranking is transitive after all

An earlier version of this sheet said the three families could not be ranked at all. That rested
on two edges measured against the under-trained panel: PPO drew level with the solver (+10.4)
while the solver beat the evolved genome by +370.1, and yet PPO beat that same genome by only
+23.9 where transitivity demanded about +360. No single ordering allowed both.

Both of those edges moved when the panel was replaced with a converged solver. Re-measured on the
current panel — 40,000 hands per seed, three seeds:

| edge | BB/100 to the first named |
|---|---|
| CFR vs PPO (2M) | +73.5 |
| CFR vs evolution | +200.9 |
| **PPO vs evolution** | **+96.5** — per seed +75.2, +273.3, −58.9 |

Transitivity now predicts **+127.4** for the third edge. The measurement is +96.5 with a
standard error of ±96.5 across the three seeds, which span 332 BB/100. **The discrepancy is a
quarter of the size of the error bar, so there is no intransitivity left to explain.** The
original observation was a property of the panel, not of the agents.

Two of the three explanations tried in August still stand as ruled out, and are worth keeping for
what they cost: measuring the solver through both families' code paths gives bit-identical results
(not an instrument artefact), and lifting the one-raise-per-street cap *widened* the gap rather
than closing it (not the abstraction). The third explanation was accepted on evidence that has
since been withdrawn.

### What survives — and it is smaller than the story it replaces

Counting what each agent actually does against a station that never folds, ~300,000 decisions each:

| | score | fold | check/call | raise ½ | raise pot | raise 2× | all-in |
|---|---|---|---|---|---|---|---|
| CFR solver | +603.4 | 0.3% | 45.4% | 29.4% | 16.0% | 7.3% | 1.6% |
| PPO, 2M hands | +397.3 | 2.7% | 42.4% | 23.8% | 19.2% | 11.7% | 0.2% |

The two raise at almost exactly the same rate — 54.3% against 54.9% — and PPO's raises are on
average the *larger* of the two, yet it collects 206 BB/100 less from the same opponent. So the
previous explanation does not carry the difference either: that version read "PPO has eliminated
the all-in", against a solver that jammed 15.0% of the time. A converged solver jams **1.6%**.
The remaining difference is *which spots* get bet, which counting frequencies cannot see.

PPO does fold 2.7% of the time against an opponent who never folds — a pure loss, and a genuine
mark of self-play against snapshots that do fold — but it is far too small to account for 206
BB/100. **This is left open rather than explained away.**

---

## Result 5 — the first number this project did not compute about itself

Every figure above was measured by this project's own instrument. **Slumbot** is a fixed CFR
strategy at heads-up no-limit behind a public API, used as a benchmark in published work.

**−987 ± 374 mbb/hand over 10,000 hands.** We lose, heavily.

An earlier run with a 4,000-iteration solver read −1750 ± 524; retraining that solver to 150,000
iterations halved the gap. **The −987 is itself now stale**: the solver has since been retrained
again on a corrected game and a re-measurement is outstanding.

| check | |
|---|---|
| protocol errors | 0 of 10,000 hands |
| lookup miss rate | 8.7% — the genuinely off-tree nodes, not a broken lookup |
| seat split | 5,000 / 5,000, exact |

What is playing: a **100bb, one-raise-per-street, six-bucket** solver against a
**200bb unlimited-raise** opponent built with serious compute. GTO Wizard beats Slumbot by
194 ± 41 mbb/hand; this is 987 the other way. The milestone asked for a number with a
confidence interval, not a good one, and a loss reported as a loss is the point.

**One trap avoided.** Slumbot returns a `baseline_winnings` field that looked like free variance
reduction — correlated 0.85 with actual winnings, 37% tighter. Differencing it gives −68 ± 301,
which is nearly break-even. It is not the win rate: the baseline's own mean is −1682 mbb/hand,
so differencing changes *what is being estimated*, not its precision. It measures how this agent
did relative to Slumbot's baseline holding the same cards. Quoting it would have been wrong by a
factor of twenty-five, in the flattering direction.

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
- **285 automated regression tests.**

### Seven measurement failures, all reported

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

5. **Two implementations of betting, differing by 20%.** `engine.PokerGame` sized a pot-fraction
   raise off the pot *before* the call; `games/nolimit.py`, where the solver trains, sized it
   *after* — the standard convention. Every raise in the engine was about a fifth too small, so
   strategies were scored making bets they had not been fitted for.
6. **The traversal game did not end hands at an all-in.** It kept asking a check/call from players
   holding nothing. Those filler actions extend the information-set key, so the same hand keyed
   differently in the two games and part of every solver's table was fitted for situations that
   cannot occur.
7. **The calling station was raising.** `always_call_policy` indexed by position in the legal
   list, so with nothing to call it picked *raise half pot*. The passive baseline raised whenever
   checking was free. This was why two evaluation paths gave opposite verdicts on the same two
   strategies — they now agree to 4.8 BB/100, from 232.4.

**And the panel itself.** Every figure about PPO and evolutionary search was measured against a
solver with **4,000 iterations — about two minutes of training**. A properly converged one beats
it by +165 BB/100, and re-measuring against that overturned four published claims: PPO does not
beat the solver, more training does not close the gap, evolutionary search *did* learn something
transferable after all, and the intransitivity of Result 4 dissolved. An under-trained solver is far more exploitative than a
converged one, which flattered one family and buried the other's improvement.

Each was caught by a check that already existed. **A measurement that is too coarse or subtly
wrong does not return "no result" — it returns a plausible one.** Four of the seven were found by
improving the instrument rather than by gathering new data, which is the pattern worth taking
from this project.

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
venv/bin/python -m pytest -q                          # 285 tests; collection alone ~6 min
venv/bin/python scripts/endpoint_test_ppo.py --seed 0 1 2   # Result 3
venv/bin/python scripts/phase4_comparison.py               # Result 2
venv/bin/python scripts/make_figures.py                    # every figure
venv/bin/python scripts/diagnostics/check_instrument.py    # the instrument check
```
