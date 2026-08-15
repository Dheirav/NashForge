# What to do next

One page, kept current. [`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the full phase plan and its results. This
file is only the next thing to do.

**Last updated:** 16 August 2026 · `main` at `0399361` · 197 tests passing

---

## Where this stands

Two of the three agent families the project compares are done and measured.

| | | |
|---|---|---|
| CFR | done | Validated against Kuhn's −1/18 and exact Leduc exploitability. Produced the abstraction crossover |
| Evolutionary search | done | Learned to exploit randomness; nothing transferred against the solver |
| **PPO** | **not started** | The remaining leg |

---

## The next step: Phase 3 — PPO with self-play

Two parts, and the first is a prerequisite rather than a nicety.

### 1. Build snapshot pooling

`rl/ppo/trainer.py` currently trains against `RandomOpponent`, or against a Hall of Fame pool
loaded from `hof_dir` — which is **empty**, and whose contents would be invalid anyway, since
every genome in it was bred on the metric the audit withdrew.

The audit is specific that self-play means training against *current and past versions of
itself*. So: snapshot the policy into the opponent pool periodically, sample from that pool
most of the time, and face the current policy the rest.

The parameters were decided on 15 August and are recorded in
[`docs/training-plan.md`](docs/training-plan.md#decisions-taken-15-august): snapshot every ~10
updates, keep the last 5–10, CPU rather than GPU.

### 2. Train and measure

Reuse what Phase 2 established rather than rebuilding it:

- `scripts/train_evolution.py` is the pattern to follow — it records self-play reward *and* an
  independent panel score, and writes a resumable history.
- `scripts/preflight_training.py` must pass first. It runs the real loop briefly and checks the
  properties that were false during the 89 invalid runs.
- `scripts/endpoint_test.py` produces the result. Compare the trained policy against an
  untrained one from the same initialisation, both against the same panel, at **40,000 hands**.

**Do not read a learning curve measured at 3,000 hands.** Phase 2's was ±57 BB/100 and its
apparent rise was noise; the real effect only appeared in the endpoint test. This is the single
most repeated failure in this project's history.

---

## After that

**Phase 4 — the comparison.** All three families on one panel with one instrument. This is what
the project's title promises and what the report is missing.

**Phase 5 — six-max.** Note the CFR agent cannot serve as a benchmark there, so the panel loses
its only opponent from outside the lineage. Also needs the `play_match` stack-drift fix
described in [`docs/training-plan.md`](docs/training-plan.md).

---

## Closed — do not reopen without new information

- **Exploitability via LBR.** Four defects and three valuation models in, it still cannot beat a
  converged strategy. Stopped deliberately; the reasoning is in `BACKLOG.md` item 1.
- **Re-running the exploitability crossover.** Superseded by the head-to-head result, which
  answered the same question conclusively in four hours.

---

## Picking this up cold

```bash
python -m pytest tests/ -q              # expect 197 passed
python scripts/audit_observation.py     # the 19-feature observation, both table sizes
python scripts/make_figures.py          # rebuilds every figure from the repo alone
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
