# What to do next

One page, kept current. [`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the full phase plan and its results. This
file is only the next thing to do.

**Last updated:** 20 August 2026 · `main` at `813f457` · 233 tests passing

---

## Where this stands

| | | |
|---|---|---|
| CFR | measured | Validated against Kuhn's −1/18 and exact Leduc exploitability. Produced the abstraction crossover, +0.916 ± 0.118 chips/hand at the 2560s budget |
| Evolutionary search | measured | Learned to exploit randomness; nothing transferred against the solver |
| PPO | measured | Closes the gap to the CFR agent: −380.9 → −11.6 BB/100 after 8M hands. Flat after 2M |

All three families are now measured on the same panel with the same instrument, which is the
condition Phase 4 has been waiting on since the plan was written.

Phase 3's result, in one line: PPO learned and **what it learned transferred**. Against the
solver the untrained networks scored −384.6, −381.7 and −376.3 BB/100; after 8M hands the same
three scored −36.2, +34.3 and −33.0. Evolutionary search, same panel and same bar, moved
−403.9 → −370.1 and was scored *no change*. All 27 rows improved; CFR lookup miss rate 0.0%.
Full tables in [`docs/training-plan.md`](docs/training-plan.md) and
`results/ppo/phase3_endpoint.json`.

---

## The next step: Phase 4 — the comparison

All three families on one panel with one instrument, across the budget ladder. This is what the
project's title promises and what the report is missing. It is mostly assembly: the
measurements exist, in `results/cfr/`, `results/evolution/` and `results/ppo/`.

Four things to carry into it rather than rediscover:

**The PPO ladder is flat after 2M hands.** +387.6 BB/100 against the CFR agent at 2M, +369.2 at
8M, on seed spreads of 40 and 62. Three quarters of each run's wall-clock bought nothing
measurable. Do not spend Phase 4's budget on the assumption that more hands help.

**Only the CFR column is quotable.** Seed spreads against the solver are 40–134 BB/100; against
random and always-call they run 92–609. Against always-call at 8M the three seeds scored
+435.1, +185.2 and +794.3 — direction certain, magnitude unresolved. Compare families on the
opponent from outside their lineage, and treat the baselines as floor checks.

**The two families are not on one budget axis yet.** Evolution's ladder is generations at a
fixed hand count; PPO's is hands. They are the same wall-clock only by coincidence, and the
comparison has to say which axis it is using before it plots anything.

**Break-even is against *this* CFR agent** — six buckets, one raise per street. Not a strong
solver, and not an exploitability figure. Item 1 closed with no usable bound, so no-limit still
has none. The comparison should say so where it would otherwise be read as a strength claim.

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
