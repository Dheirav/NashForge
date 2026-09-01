# What to do next

One page, kept current. [`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the full phase plan and its results. This
file is only the next thing to do.

**Last updated:** 1 September 2026 · `main` at `d3d9a02` · 233 tests + 44 Slumbot tests

---

## Where this stands

| | | |
|---|---|---|
| CFR | measured | Validated against Kuhn's −1/18 and exact Leduc exploitability. Produced the abstraction crossover, +0.916 ± 0.118 chips/hand at the 2560s budget |
| Evolutionary search | measured | Learned to exploit randomness; nothing transferred against the solver |
| PPO | measured | Closes the gap to the CFR agent: −383.8 → −10.7 BB/100 after 8M hands. Flat after 2M |

All three are measured, and **Phase 4 — the comparison the project's title promises — is done**
(`results/comparison/phase4.json`). One panel, 40,000 hands, one wall-clock axis, in BB/100:

| family | wall-clock | vs random | vs always-call | vs CFR |
|---|---|---|---|---|
| CFR (the solver) | — | +377.2 | +722.9 | — |
| evolution, 50 generations | 3.16 h | +192.7 | +0.5 | −370.1 |
| PPO, 2M hands | 1.02 h | +221.5 | +293.5 | **+10.4** |
| PPO, 8M hands | 4.81 h | +135.4 | +467.9 | −10.7 |

**PPO reaches break-even against the solver in about an hour. Evolutionary search, given three
times that compute, is still 370 BB/100 behind.**

---

## Closed, 20 August: the Phase 4 intransitivity

It is **explained** — see
[`docs/training-plan.md`](docs/training-plan.md). All three candidate explanations were tested:
the instrument agrees bit-for-bit, lifting the raise cap widened the gap rather than closing it,
and the third turned out to be the answer.

The tournament graph's missing edge settles it. PPO against the evolved genome scores **+23.9
BB/100** (per seed −12.7, +68.2, +16.3, spread 80.8) where transitivity predicted about +360.
PPO is level with the solver *and* level with the genome the solver beats by 370, which no
single ordering allows.

The mechanism is in the action counts. Against a station that never folds the solver goes all-in
on **15.0%** of its decisions and PPO on **0.1%**; the two raise at similar rates, so the
difference is sizing rather than frequency. Self-play optimises against a peer, and its
snapshots fold — so the policy never learned to jam into an opponent who does not. Against the
solver that costs nothing; against anything weak it leaves the value uncollected.

**Do not quote a single-number ranking of the three families.** The data does not support one.

---

## Now: item 5 — M1 is done, M2 is the next question

**M1: −1750.2 ± 524 mbb/hand over 10,000 hands** (`results/slumbot/m1.json`). Zero protocol
errors, 8.7% lookup miss rate, exact 5,000/5,000 seat split. The first figure here that somebody
else's agent produced, and a heavy loss — reported as one.

What is playing: a 100bb, one-raise-per-street, six-bucket, 4,000-iteration solver against a
200bb unlimited-raise opponent. M1 asked for a number, not a good one.

**Do not use `baseline_winnings` as a win rate.** It looked like free variance reduction —
correlated 0.85, 37% tighter — but its own mean is −1682 mbb/hand, so differencing changes the
estimand rather than the precision. It measures how this agent did *relative to Slumbot's
baseline holding the same cards* (−68 ± 301), which is a different question. Quoting it as the
result would have been wrong by a factor of twenty-five, flatteringly.

### M2 — within 200 mbb/hand

**Train a solver at 200bb first, then measure.** Not because Slumbot demands it: 200bb is the
ACPC convention and what published work reports against, and this project's 100bb was an
unexamined default in `results/cfr/nolimit_strategy.json`. Moving to it once makes every future
external comparison possible; retraining per opponent would leave no agent with a fixed identity.
Note it invalidates the existing panel figures unless both solvers are kept, which is a real cost
to weigh.

Then the hand count: at the measured spread of 2,169 chips/hand, ±200 mbb/hand needs about
**45,000 hands** — roughly 30 hours at the API's 0.4 hands/second. There is no shortcut through
the baseline. Retraining before spending 30 hours of someone else's free API is the sensible
order.

Also worth raising: 4,000 solver iterations is very few. The crossover ran to 288,000 at a
2,560-second budget. Iteration count may matter more than depth.

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
