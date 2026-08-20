---
name: train
description: Run a NashForge/PokerBot training run correctly and measure whether it learned anything. Use when asked to train an agent, run PPO or evolutionary search, resume a run, evaluate a checkpoint, or judge whether a training curve shows real improvement.
---

# Training, and measuring whether it worked

Never skip straight to training. The order is **preflight → train → endpoint
test**, and the last step is the only one that answers the question.

## The rule that overrides everything

**Do not read a learning curve measured at 3,000 hands.** Phase 2's had an
error of about ±57 BB/100, and across eleven readings it scattered with a
standard deviation of 56 — indistinguishable from a constant. Its apparent rise
was noise. The real effect appeared only in the endpoint test.

This is the single most repeated failure in this project's history. If asked
whether a run is improving, and the only evidence is a per-generation panel
score, the honest answer is **"that measurement cannot tell us."**

40,000 hands gives ±15 BB/100, which resolves the ~35 BB/100 the training
instrument can express. That is the bar.

## Evolutionary search

```bash
venv/bin/python scripts/preflight_training.py    # must pass first — no arguments
venv/bin/python scripts/train_evolution.py
venv/bin/python scripts/endpoint_test.py         # the answer — no arguments
```

`preflight_training.py` runs the real loop briefly and checks the properties
that were false during the 89 invalid runs. Tests passing is not a substitute:
the tests exercise components, and what failed before was the loop as a whole.
It prints `[PASS]`/`[FAIL]` per property. **A FAIL means do not train.**

`endpoint_test.py` compares the trained genome against an untrained one drawn
from the same initial distribution, both against the same panel, both at 40,000
hands. **The comparison that matters is the difference between the two
columns** — each on its own is a fact about the opponent as much as the agent.

## PPO

```bash
venv/bin/python scripts/preflight_ppo.py                    # defaults: 200k hands, 40k panel
venv/bin/python scripts/preflight_ppo.py --calibrate --ent-coef 0.01 0.02
venv/bin/python scripts/train_ppo.py --seed 0
venv/bin/python scripts/train_ppo.py --seed 0 --resume
```

`train_ppo.py` **requires `--seed`**. It also takes `--rungs` (a budget ladder)
and `--monitor-hands`. `preflight_ppo.py` takes `--hands`, `--panel-hands`,
`--panel-seed`, `--from-checkpoints` and `--seed-check`.

There is **no PPO equivalent of `endpoint_test.py`** — that script is
evolution-specific (it builds genomes through `EvolutionTrainer`). Measuring a
PPO run at the same standard means building the comparison, not reusing it.

## Traps

- **`hall_of_fame/` is empty and its former contents would be invalid anyway** —
  every genome in it was bred on the metric the audit withdrew. `rl/ppo/trainer.py`
  loads opponents from `hof_dir`; that path is not a source of opponents yet.
  Self-play here means snapshotting the policy into the pool as training goes.
- **Any number predating `CODEBASE_AUDIT.md` (12 August 2026) is withdrawn.**
  The old fitness function scored the wrong player and the deck re-dealt the
  same two hands every hand; an untrained random network scored +451 BB/100
  under it. Do not quote the superseded reports back — they are deleted from the
  tree and live only in git history and the `_superseded_` tarball.
- **Budget for the test suite.** `pytest --collect-only` alone takes ~5 minutes
  (207 tests). Run one file while iterating.
- **`scripts/train_evolution.py` is the pattern to copy** for any new trainer:
  it records self-play reward *and* an independent panel score, and writes a
  resumable history. Do both.

## Reporting a result

State the hand count the measurement was taken at. A number without it is not
comparable to anything in `docs/training-plan.md`, and at 3,000 hands it is not
a result at all. If the endpoint test has not been run, say the run is unmeasured
rather than describing the curve.
