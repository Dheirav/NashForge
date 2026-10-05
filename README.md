# NashForge

**A heads-up no-limit Hold'em bot built on counterfactual regret minimisation, and the
instrument it was measured on against evolutionary search and PPO.**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: PolyForm Noncommercial](https://img.shields.io/badge/License-PolyForm%20Noncommercial-blue.svg)](https://polyformproject.org/licenses/noncommercial/1.0.0)

NashForge is a three-time champion of the [Chipzen](https://chipzen.ai) arena, a weekly
heads-up no-limit Hold'em tournament for bots with blinds rising every twenty hands. It won
season 6 (15 to 20 September 2026), season 7 (knockouts 26 to 28 September) and season 8
(29 September to 5 October), every time played remotely from a laptop.

Playing remotely gives it no edge over a bot running on the platform's own machines. The
remote bot plays under the same 30-second clock and through the same API as every entrant,
and it does no search at play time. Each decision is a lookup in tables solved beforehand:
in the season 8 final the median took 0.57 milliseconds and the slowest 2.9. Once a match
starts, no person is involved. The same strategy family also runs as an uploaded bot,
OptimumPoker, inside Chipzen's sandbox, which allows numpy only, no compiled code, and
250 MB. There it is 26 MB zipped and 86 MB at peak, and on 12,753 test decisions it chose
the same action as the remote bot every time. The uploaded build carries v5x purified, the
set that played the season 8 round robin, without the opponent reads. The set that won the
final, v5xRR3 purified, is the same thing with three of its stack depths retrained.

In season 6 it went 4-1 in the round-robin as the top seed and 3-0 through the playoffs, and
won every match it played. The one loss was a walkover from a timer bug of my own, which
turned out to be the most useful lesson of the week. The record, with the platform's own
pages and the match identifiers anyone with a free Chipzen login can resolve, is in
[`docs/season6/`](docs/season6/README.md).

In season 7 it went 5-2 in the round-robin, came into the knockouts as the fourth seed, and
won all three: v003 in the
quarter-final (84 hands), wsp in the semi-final (60 hands) and melly in the final (4 hands).
The same solver set played every knockout match, chosen beforehand from its results against
fitted copies of each opponent rather than changed on match day.

In season 8 it went 7-1 in the round-robin, level on top with Blueprint, and again won all
three knockouts: melly (50 hands), PoetAndCoder (6) and Blueprint in the final (51). Every
match it played, it won; the one loss was again a walkover, the bot not connected. The final
was not a clean win. We were down to a fifth of the chips by hand 36, came back on one called
shove that hit from about a third of the equity, and won when Blueprint called its last chips
with a pair of fives. The record and what the season taught is in
[`docs/season8-summary.md`](docs/season8-summary.md).

The project started as a comparison. Three families of agent, CFR, evolutionary search and
PPO, were trained on the same abstracted game and measured on the same panel, and the
solver beat the other two by a wide margin. The solver family is what became the bot.

---

## What the bot is

**The solver.** External-sampling Monte Carlo CFR with linear discounting, warm start from a
smaller tree (mapped by action, so a tree that inserts a size keeps what was learnt) and
regret-based pruning, written in C++ (`native/`) and bound to Python with nanobind.
Discounted CFR was tried in four settings and loses to linear by 22 BB/100 or more. It runs at about half a millisecond per iteration on one core; a 20-million-
iteration solve of one stack depth takes about three hours on two.

**The abstraction.** 169 preflop hand classes (every distinct starting hand). Postflop, hands
are clustered by k-means over sampled equity against a random hand, with the board's flush
and straight texture folded in; an equity-histogram feature clustered by earth mover's
distance (Johanson et al., 2013) is wired in and pinned against the native mirror, and is
the next thing to train on. Betting is a tree of a few raise sizes per raise, with schedules
that can taper so that later raises get fewer sizes, which is what makes a third raise
affordable. A schedule can also differ by street: adding a half-pot re-raise on every street
but the river cut the balanced set's measured leak at 70bb from +56.5 to +16.1 BB/100, at no
cost head to head, for a tree three times the size.

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

Four instruments came out of the season 8 post-mortem, because most of our tests turned out
unable to see what we had changed (`docs/research/2026-10-05-synthesis.md`). The burst
decomposition takes the luck out of called all-ins (`--allin-adjust`, exact over every
runout). `scripts/burst_verdict.py` gives a verdict that stays valid however often it is
read, where a fixed test read after every burst picks a false winner one time in five.
`scripts/copy_validate.py` scores a fitted copy at its bot's own later decisions, and showed
that the copies used to pick sets did not behave like their bots. And local best response can
probe the tree's all-in-only raise level with real small raises (`--offtree-third-raise`).

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

Exploitability is measured as a lower bound only. Since 25 September, Local Best Response
run on the current ladder beats every set when it may bet sizes the tree lacks (the balanced
set gave up +56.5 BB/100 at 70bb to sizes between ours) and finds nothing when it is held to
our own sizes, which is how the per-street schedule below was chosen. LBR is a greedy
exploiter with a blind spot: it rated a discounted-CFR solve as harder to exploit while that
solve lost 24 BB/100 head to head. So no change is adopted on LBR alone. The week's
measurements are in [`docs/solver-work-2026-09.md`](docs/solver-work-2026-09.md).

---

## Getting started

```bash
python3.12 -m venv venv
venv/bin/pip install numpy numba torch pygame websockets requests
native/build.sh                                   # needs cmake, ninja, nanobind; installs by rename
venv/bin/python -m pytest -q                      # 550 tests, about 9 minutes
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
venv/bin/python scripts/chipzen_decompose.py --label v7b --allin-adjust   # read a burst
venv/bin/python scripts/burst_verdict.py --label v7b                      # is it decided yet
venv/bin/python -m gui.main                                     # play the solver yourself
```

The arena bot is started with `tools/chipzen-run.sh` and watched with
`tools/chipzen-progress.sh --watch`; it needs a Chipzen bot token in the environment. The
solved strategies are not in the repository. The code, the instruments and the match ledger are;
the scouted profiles of other bots are not.

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
| `results/` | Every measurement as JSON, one file per question; the arena ledger under `results/chipzen/`. |
| `tests/` | 550 tests. Was an empty directory before the audit. |
| `docs/` | The arena (`chipzen.md`, `season6/`, `season8-summary.md`), the training plan, the research notes (`research/`). |

## Reading the repository

`NEXT.md`, the working document that holds the next thing to do and the current state of
every set, is kept locally from 22 September 2026 and is not in the repository; its history
to that date is. `CODEBASE_AUDIT.md` (12 August 2026) is authoritative on what in this
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

[PolyForm Noncommercial 1.0.0](LICENSE), from 22 September 2026. Read it, run it,
learn from it, build on it and share what you build, for any noncommercial purpose;
entering it or a derivative of it in a prize competition is commercial use and is not
licensed. The solved strategies are not distributed at all. Versions before this date were
MIT-licensed and remain so.
