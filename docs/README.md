# NashForge documentation

Start from the [project README](../README.md).

- **[training-plan.md](training-plan.md)** — the plan for the next phase: evolutionary
  search and PPO, heads-up first, measured against the CFR agent. Includes the 15 August
  audit of the 17-feature observation and what it says to do about it.

- **[abstraction-crossover.html](abstraction-crossover.html)** — the project report.
  What was withdrawn and why, how the CFR solver was validated, the training-budget
  crossover between the two card abstractions, and the exploitability investigation
  that did not reach a conclusion. Every claim is either measured, with its interval,
  or marked open.

## What used to be here

This directory previously indexed seventeen working documents: the hyperparameter
scaling laws, the global synthesis report, the Hall of Fame impact analysis, the
tournament results, and the sweep workflow guide among them.

They were removed rather than moved. [`CODEBASE_AUDIT.md`](../CODEBASE_AUDIT.md)
establishes that every result in them came from a fitness function that scored the
wrong player and a deck that dealt the same two hands every hand — an untrained
random network scored +451 BB/100 under that metric, where approximately zero is
what it must score. The documents are not wrong in their details; they are drawing
conclusions from an instrument that was measuring something else.

They remain in git history, and in `PokerBot_superseded_2026-08-12.tar.gz`:

```bash
git show pre-cfr-pipeline:HYPERPARAMETER_SCALING_LAWS.md
git log --diff-filter=D --name-only -- '*.md'
```

Open work is tracked in [`BACKLOG.md`](../BACKLOG.md), which records why each closed
item closed — including the three that closed on a negative result.
