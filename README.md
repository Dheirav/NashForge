# NashForge

**A Multi-Agent Framework for Comparative Evaluation of Game-Theoretic, Evolutionary, and Reinforcement Learning Agents in Imperfect-Information Games**

Counterfactual regret minimization on heads-up no-limit Hold'em, over a verified poker engine —
with evolutionary search and PPO measured against it on the same instrument.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Where it stands (September 2026)

**NashForge won season 6 of the [Chipzen](https://chipzen.ai) arena** (15 to 20 September
2026), a heads-up no-limit Hold'em arena for bots on a 30-second clock with blinds rising
every twenty hands: 4-1 in the round-robin as the top seed, then 3-0 through the playoffs,
every match it played won and the one loss a walkover from a timer bug of my own. The bot
that played is the CFR family below: a ladder of solvers, one per stack depth from 5 to
100 big blinds, trained in C++ (`native/`) and played through a Python bot (`chipzen/`)
from this laptop, with opponent reads sized to scouted hand histories. The solved
strategies are not in the repository; the code, the instruments and the match ledger are.

The comparison the title promises is done as well: on one panel at 40,000 hands, the
solver beats PPO by about 75 BB/100 and evolutionary search by about 200, with evolution
spending seventy times PPO's hands to finish further behind (`results/comparison/`).

What is current, and what to do next, is always in [`NEXT.md`](NEXT.md). The arena
week's rules, learnt the expensive way, are in `CLAUDE.md`; the arena itself is described
in [`docs/chipzen.md`](docs/chipzen.md) and [`docs/arena-plan.md`](docs/arena-plan.md).

---

## Read this first

This repository previously trained poker agents with an evolutionary algorithm and published
scaling laws, tournament rankings and hyperparameter findings from them. **All of it was
wrong.** [`CODEBASE_AUDIT.md`](CODEBASE_AUDIT.md) establishes, by executing the code rather
than reading it, that the fitness function scored the wrong player and the deck re-dealt the
same two hands every hand. An untrained random network scored +451 BB/100 under that metric;
it now scores approximately zero, as it must.

The rules engine and its chip accounting survived the audit intact and are kept. Everything
built on top of the broken metric was archived:

```bash
git show pre-cfr-pipeline:scripts/training/hyperparam_sweep.py   # read a deleted file
git checkout pre-cfr-pipeline -- scripts/analysis                # restore a directory
```

What replaced it is CFR: a family of algorithms that provably converges toward a Nash
equilibrium in imperfect-information games, and — more to the point — comes with measures
that say how far from one you actually are.

---

## What is here

| Directory | Contents |
|---|---|
| `engine/` | Texas Hold'em rules, betting, side pots, hand evaluation. Verified correct by the audit; six behaviours checked against known-correct answers. |
| `games/` | The traversable game interface plus Kuhn poker, Leduc Hold'em and abstracted heads-up no-limit. CFR traverses a game rather than playing it, which the engine's in-place simulator cannot support. |
| `abstraction/` | Card bucketing (Chen preflop, k-means over a strength signal postflop) and the six-action bet abstraction. |
| `cfr/` | Vanilla CFR, external-sampling MCCFR, four regret update rules, exact exploitability for small games, and Local Best Response for no-limit. |
| `native/` | The C++ core: external-sampling MCCFR with linear discounting, warm start and pruning, the abstract game, the hand evaluator, equity and histogram sampling. Bound with pybind11; `native/build.sh` builds it. |
| `chipzen/`, `slumbot/` | The arena bot (remote, through the Chipzen SDK) and the Slumbot bridge. |
| `evaluation/` | The benchmark loop, the duplicate-hand panel and the cross-tree gate every solver is measured on. |
| `scripts/`, `tools/` | Entry points (training, gates, the duel, the replay, the burst decomposition) and the shell wrappers for the arena. |
| `tests/` | 410 tests, about 6½ minutes; collection alone is about half of that. Was an empty directory before the audit. |
| `results/` | Measurements as JSON, one file per question; the arena ledger and scouted profiles under `results/chipzen/`. |
| `training/`, `rl/` | Genetic operators and a PPO implementation, both measured against the solver in Phase 4. Retained; not the current line of work. See below. |

## Why anyone should believe it

CFR is easy to write and hard to write correctly, and a solver that has converged to the
wrong thing looks exactly like one that has converged. Three checks pin it down:

- **Kuhn poker** has an analytically known game value of **−1/18** to the first player. The
  solver reproduces it.
- **Leduc Hold'em** is small enough to traverse exactly, so exploitability is *computed*, not
  estimated, and must fall toward zero.
- **No-limit** cannot be traversed at all, so exploitability is bounded from below by Local
  Best Response (Lisý & Bowling, 2017). This is a bound in one direction only, and that
  direction matters — see the caveat below.

---

## Install

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install numpy numba
```

Numba is not optional in practice: the hand evaluator is on the hot path of every CFR
traversal.

## Run the tests

```bash
venv/bin/python -m pytest -q      # 410 tests, about 6½ minutes; one file while iterating
```

## Run the experiments

Each script answers one question and writes one JSON file under `results/cfr/`.

```bash
# Which regret update rule converges fastest? (Leduc, exact exploitability)
python scripts/cfr/compare_update_rules.py

# How large is the abstract game, and what fits in memory?
python scripts/cfr/measure_abstraction.py

# Train a no-limit agent over the abstraction
python scripts/cfr/train_nolimit.py

# How exploitable is the trained agent?
python scripts/cfr/measure_exploitability.py

# Is Monte-Carlo equity bucketing worth 5.4x the cost of made-hand bucketing?
python scripts/cfr/compare_strength_signals.py

# Does equity bucketing overtake it given enough wall-clock? (long: hours)
python scripts/cfr/crossover.py --budgets 40 160 640 2560 --seeds 3
```

`crossover.py` checkpoints after every measurement and skips seeds already present in its
output file, so an interrupted run resumes rather than restarting.

---

## Reading an LBR number

Local Best Response plays a *greedy* best response, not a true one, so what it wins is a
**lower bound** on exploitability. The asymmetry is the whole point:

- A **large positive** LBR proves the strategy is exploitable by at least that much.
- A value **near or below zero proves nothing at all.** It means this particular exploiter
  failed to win, not that the strategy is near equilibrium. Negative exploitability does not
  exist.

Two LBR figures may only be compared where both clear zero. `crossover.py` enforces this and
labels any budget where the bound goes slack rather than reporting a winner from it.

**Current status of the crossover question: unresolved.** Across 40/160/640/2560-second
budgets and three seeds, only the 40s rung produced bounds informative for both signals, and
there the cheap made-hand bucketing was ahead. Above that the bound goes slack before the two
curves separate, so whether equity bucketing ever repays its cost is not answered by the data
in `results/cfr/crossover.json`. Strengthening LBR is a prerequisite, not a refinement — see
[`BACKLOG.md`](BACKLOG.md).

---

## Retained but not current

`training/` and `rl/` hold the genetic operators and a PPO implementation. The audit found
both sound as *code*; what was broken was the fitness function they optimised and the feature
vector they saw. They are kept because that verdict makes them worth recovering, not because
they are on the critical path. `scripts/run_ppo_training.py` still drives PPO.

Be clear-eyed about the ceiling if you return to them: self-play policy gradient does not
converge to a Nash equilibrium in imperfect-information games. It yields a strong but
exploitable bot. That is why the current work is CFR.

---

## Open work

**[`NEXT.md`](NEXT.md)** — one page, what to do next and how to pick it up cold.

[`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the phase plan and its results.

## License

MIT — see [LICENSE](LICENSE).
