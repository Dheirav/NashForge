# What to do next

One page, kept current. [`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the full phase plan and its results. This
file is only the next thing to do.

**Last updated:** 20 August 2026 · `main` at `95432c9` · 233 tests passing

---

## Where this stands

| | | |
|---|---|---|
| CFR | measured | Validated against Kuhn's −1/18 and exact Leduc exploitability. Produced the abstraction crossover, +0.916 ± 0.118 chips/hand at the 2560s budget |
| Evolutionary search | measured | Learned to exploit randomness; nothing transferred against the solver |
| **PPO** | **trained, unmeasured** | Three seeds finished 18 August. Nine checkpoints, no result |

Phase 3's *training* is done and its *measurement* is not, and those are not the same thing.
Three seeds ran to 8M hands each on 17–18 August, about 4.7 hours apiece, leaving rungs at
500k, 2M and 8M in `~/pokerbot-scratch/phase3/seed{0,1,2}/`. Every one of them ended by
printing the instruction that is still outstanding: run the endpoint test against the rungs,
and report the spread across seeds rather than the error bar of any single one.

---

## The next step: an endpoint test for PPO

`scripts/endpoint_test.py` cannot do it. It is evolution-specific by construction — it globs
`phase2/runs/run_*`, loads `best_genome.npy`, and builds agents through `EvolutionTrainer`. It
takes no arguments and cannot open a `.pt`. Measuring PPO at the same standard means building
the comparison, not reusing it.

Most of the parts already exist in `scripts/train_ppo.py` and should be reused rather than
rewritten: `build_panel()`, `panel_scores()`, and the PPO→panel adapter that puts a policy
behind the panel's `(game, seat, mask, history)` signature.

What the new script has to do:

1. Load each rung checkpoint, **and an untrained policy from the same initialisation**. The
   difference between the two columns is the result; either column alone is a fact about the
   opponent as much as about the agent.
2. Play **40,000 hands** against the same panel — random, always-call, and the CFR agent. That
   is ±14 BB/100.
3. Report the **spread across the three seeds**, not one seed's bar. At 200,000 hands these
   same three seeds scored −68.6, +19.5 and −3.3 against the CFR agent: 46 BB/100 apart on seed
   alone, which is over three times the 40,000-hand error bar. Quoting one seed understates the
   uncertainty threefold.
4. Require `--seed`, as `scripts/train_ppo.py` does, so a measurement cannot be taken
   unreproducibly by accident.
5. Write `results/ppo/` as JSON, matching the shape of the other two families.

**Do not read the training curve instead.** The panel score recorded during the run is over
10,000 hands, about ±50 BB/100 — monitoring, not measurement. Phase 2's per-generation curve
was read as rising from +111 to +214 BB/100 while being indistinguishable from a constant.
This is the single most repeated failure in this project's history.

---

## After that

**Phase 4 — the comparison.** All three families on one panel with one instrument, across the
budget ladder the Phase 3 rungs were built to provide. This is what the project's title
promises and what the report is missing. It is waiting on the step above and nothing else.

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
