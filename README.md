# NashForge

**A heads-up no-limit Hold'em bot built on counterfactual regret minimisation, and the
instrument it was measured on against evolutionary search and PPO.**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

NashForge won season 6 of the [Chipzen](https://chipzen.ai) arena (15 to 20 September
2026): a weekly heads-up no-limit Hold'em tournament for bots on a 30-second clock, with
blinds rising every twenty hands. It went 4-1 in the round-robin as the top seed and 3-0
through the playoffs, played remotely from a laptop, and won every match it played. The one
loss was a walkover from a timer bug of my own, which turned out to be the most useful
lesson of the week.

The project started as a comparison. Three families of agent, CFR, evolutionary search and
PPO, were trained on the same abstracted game and measured on the same panel, and the
solver beat the other two by a wide margin. The solver family is what became the bot.

---

## What the bot is

**The solver.** External-sampling Monte Carlo CFR with linear discounting, warm start from a
smaller tree and regret-based pruning, written in C++ (`native/`) and bound to Python with
nanobind. It runs at about half a millisecond per iteration on one core; a 20-million-
iteration solve of one stack depth takes about three hours on two.

**The abstraction.** 169 preflop hand classes (every distinct starting hand). Postflop, hands
are clustered by k-means over sampled equity against a random hand, with the board's flush
and straight texture folded in; an equity-histogram feature clustered by earth mover's
distance (Johanson et al., 2013) is wired in and pinned against the native mirror, and is
the next thing to train on. Betting is a tree of a few raise sizes per raise, with schedules
that can taper so that later raises get fewer sizes, which is what makes a third raise
affordable.

**The ladder.** One solver per stack depth, from 5 to 100 big blinds, because the right
strategy at 100 big blinds is nothing like the right strategy at 12. The bot reads the
effective stack, picks the rung, and switches as the blinds climb. Off-tree bet sizes are
mapped to the nearest size in the tree.

**The arena bot** (`chipzen/`). Plain Python reading the solved strategies from flat tables,
answering in under 200 ms against the 30-second clock. Every opponent is profiled from its
public hand histories before a fixture, and a small set of reads sized to that profile
adjusts the solver's answer where the opponent is clearly not playing equilibrium poker:
never bluffing on the river, folding the blind to any open, calling everything.

**The instruments** (`evaluation/`, `scripts/`). A solver is never believed on its own
training curve. Each new one goes through a cross-tree gate (against a simpler solver in the
real game, two seeds), a duel (two whole bots over hundreds of arena-style matches on the
arena's blind schedule), a replay against the logged match record, and a burst of rated
matches read by its decomposition (by depth, by which solver decided each hand) rather than
its win rate. Every instrument is pinned to read zero on a mirror, because three of them
had defects that told confident wrong stories about the solver before that test existed.

---

## The comparison

One panel, 40,000 hands, every family against the same opponents, in big blinds per 100
hands (`results/comparison/phase4_native.json`):

| family | training hands | vs random | vs always-call | vs the solver |
|---|---|---|---|---|
| CFR solver | | +258.7 | +647.3 | |
| evolutionary search, 50 generations | 36,000,000 | +202.7 | −0.2 | **−211.8** |
| PPO | 500,000 | +191.2 | +372.6 | **−84.6** |
| PPO | 8,000,000 | +226.8 | +329.1 | **−74.9** |

Both learned families lose to the solver, PPO by about 75 BB/100 at every training budget
and evolution by about 200, and evolution spent seventy times PPO's hands to finish further
behind. The result was re-measured against an independently implemented solver (the C++
core, seeded differently from the Python one) and every number moved by less than its own
interval. This is not because the learned agents are weak against ordinary opponents; both
beat a random player by 200 BB/100. It is that self-play policy gradient and fitness-driven
search do not converge to an equilibrium in an imperfect-information game, while CFR does,
so the solver finds the holes they leave.

---

## Why anyone should believe it

CFR is easy to write and hard to write correctly, and a solver that has converged to the
wrong thing looks exactly like one that has converged. The checks, in order of strength:

- **Kuhn poker** has an analytically known value of −1/18 to the first player, and the
  solver reproduces it.
- **Leduc Hold'em** is small enough to traverse exactly, so exploitability is computed, not
  estimated, and falls toward zero.
- **A full-width CFR+ solve** of the small no-limit games ties the sampled solver on the same
  tree, which says the sampling is not the error.
- **Self-play reads zero.** A solver against itself at its own stack, on the gate, with zero
  misses, and the duel's mirror even, both in the test suite.
- **The arena.** A public record of every rated hand, with replays, against bots built by
  other people.

What is *not* claimed: exploitability of the no-limit strategies. Local Best Response was
tried and could not beat a converged strategy after four defects and three valuation
models; a lower bound that reads zero proves nothing, and the reasoning for stopping is in
`BACKLOG.md`.

---

## Getting started

```bash
python3.12 -m venv venv
venv/bin/pip install numpy numba torch pygame websockets requests
native/build.sh                                   # needs cmake, ninja, nanobind; installs by rename
venv/bin/python -m pytest -q                      # 410 tests, about 6½ minutes
```

Numba is on the hot path of every Python-side evaluation; the native module is what trains.
The build installs by rename so a rebuild under a running training is safe.

```bash
venv/bin/python scripts/preflight_training.py     # must pass before any training run
venv/bin/python scripts/cfr/train_nolimit.py --iterations 20000000 --raise-cap 4 2 1 \
    --stack 200 --big-blind 2 --texture --preflop-buckets 169 --update-rule linear \
    --threads 2 --output results/cfr/experiments/cap2_100bb.pkl
tools/xtree-gate.sh results/cfr/experiments/cap2_100bb.pkl      # the cross-tree gate
venv/bin/python scripts/chipzen_duel.py --a <ladder A> --b <ladder B> --arena-matches 600
venv/bin/python scripts/chipzen_decompose.py --label v7b        # read a burst
venv/bin/python -m gui.main                                     # play the solver yourself
```

The arena bot is started with `tools/chipzen-run.sh` and watched with
`tools/chipzen-progress.sh --watch`; it needs a Chipzen bot token in the environment. The
solved strategies are not in the repository. The code, the instruments, the match ledger and
the scouted profiles are.

---

## Layout

| directory | what is there |
|---|---|
| `engine/` | Hold'em rules, betting, side pots, hand evaluation. Verified by the audit and the one part everything else is built on. |
| `games/` | The traversable game interface, Kuhn, Leduc and abstracted no-limit. CFR traverses a game rather than playing it. |
| `abstraction/` | Card classes (preflop, k-means over equity or equity histograms postflop, board texture) and the betting schedules. |
| `cfr/` | The Python solvers (vanilla, MCCFR, four update rules), exact exploitability for small games, full-width CFR+, the river re-solver, the flat strategy tables. |
| `native/` | The C++ core: MCCFR, the abstract game, the hand evaluator, equity and histogram sampling. `build.sh` builds it. |
| `chipzen/`, `slumbot/` | The arena bot and the Slumbot bridge. |
| `evaluation/` | The benchmark loop, the duplicate-hand panel, the cross-tree gate. |
| `scripts/`, `tools/` | Entry points (training, gates, duel, replay, decomposition, scouting) and the shell wrappers for the arena. |
| `training/`, `rl/` | Evolutionary search and PPO, both measured in the comparison above. Retained; not the current line of work. |
| `results/` | Every measurement as JSON, one file per question; the arena ledger and scouted profiles under `results/chipzen/`. |
| `tests/` | 410 tests. Was an empty directory before the audit. |
| `docs/` | The arena (`chipzen.md`, `arena-plan.md`), the training plan, the research notes. |

## Reading the repository

`NEXT.md` is one page, kept current, and holds the next thing to do and how to pick the
project up cold. `CODEBASE_AUDIT.md` (12 August 2026) is authoritative on what in this
repository is and is not trustworthy. `docs/training-plan.md` holds the full phase plan
and its results; `BACKLOG.md` the reasoning and everything closed. The arena week's rules,
learnt the expensive way, are in `CLAUDE.md`.

---

## History: the audit

This repository once trained poker agents with an evolutionary algorithm and published
scaling laws, tournament rankings and hyperparameter findings from them. All of it was
wrong. `CODEBASE_AUDIT.md` established, by executing the code rather than reading it, that
the fitness function scored the wrong player and the deck re-dealt the same two hands every
hand: an untrained random network scored +451 BB/100 under that metric, and scores
approximately zero under the corrected one, as it must. The rules engine survived the audit
intact and was kept. Everything built on the broken metric was removed from the tree and
lives in git history (`git show pre-cfr-pipeline:<path>`) and in a tarball. No number from
before the audit is quoted anywhere in the current documents.

What replaced it is CFR, because it provably converges toward a Nash equilibrium in
imperfect-information games and, more to the point, comes with ways to check that it has.

## License

MIT, see [LICENSE](LICENSE).
