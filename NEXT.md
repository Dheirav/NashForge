# What to do next

One page, kept current. [`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the full phase plan and its results. This
file is only the next thing to do.

**Last updated:** 20 August 2026 · `main` at `3b21fb0` · 233 tests passing (9m32s)

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

## The next step: explain the non-transitivity

The comparison produced a result it does not explain, and it is the most interesting thing in
the table. PPO at 2M hands draws level with the CFR agent head to head (+10.4), yet the solver
takes far more off both baselines — +377.2 against random to PPO's +221.5, and +722.9 against
always-call to PPO's +293.5.

Two agents that are level against each other extract very different amounts from the same weak
opponents. So **strength here is not a scalar**, and any single-number ranking of the three
families would be a fiction. It also cuts against the intuition that a near-equilibrium
strategy should be the *less* exploitative one, which is why it is worth a look rather than a
footnote.

Both cheap explanations were checked on 20 August and **both are dead**:

- ~~An instrument artefact.~~ `scripts/diagnostics/check_instrument.py`: the two measurement
  paths agree bit-for-bit at 40,000 hands, reproducing +377.2 and +722.9 exactly.
- ~~The raise cap.~~ `scripts/diagnostics/check_raise_cap.py`: lifting it to two raises per
  street *widened* the gap against always-call, −430.1 to −437.4. The cap was not suppressing
  PPO. Note the solver goes off-tree above cap 1 — 19.3% lookup misses, concentrated in the
  random matchup — so its cap-2 column is not a measurement of the solver.

**What remains is that the non-transitivity is real**: these strategies beat each other in a
loop, and no single ranking of the three families exists. That is the finding, and it is a
better one than the leaderboard it denies. The mechanism is still not established — two
candidates are ruled out, not all of them — so the next step is to look for the third rather
than to assume the question is closed.

---

## After that

**Item 5 — do not lose to Slumbot.** The one open goal that is not an internal measurement.
Every strength figure here was computed by this project about itself, and item 1 closed with no
usable bound, so no-limit has no exploitability figure at all. The brief, its milestones and
its measurement protocol are in [`docs/EXTERNAL_BENCHMARK.md`](docs/EXTERNAL_BENCHMARK.md); M1
is 10,000 hands with a confidence interval, any result, because it would be the first number
here that someone else's agent produced. Most of the work is action translation, and no code
for it exists yet.

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
