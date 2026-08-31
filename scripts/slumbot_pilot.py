"""
A few hundred hands against Slumbot, to shake out protocol bugs.

Step 4 of `docs/EXTERNAL_BENCHMARK.md`, and its instruction is explicit: **do not
read the result**. A win rate over a few hundred hands has an interval wider than
anything it could tell us, and reading one here is how a pilot becomes a finding
that has to be withdrawn later. This prints protocol health and writes the hands
to disk; it does not print a win rate, and the file is there for M1 to be
computed from deliberately rather than glanced at now.

What counts as healthy
----------------------
**Every hand completes.** A protocol error loses a hand to the bridge rather than
to poker, and at any rate makes the hand count a lie.

**The miss rate is low.** It is the fraction of decisions where the strategy had
no entry for the node and the agent chose among legal actions at random. This
project published a result once at a 74.3% miss rate, where the benchmark had
quietly become a second random opponent; the counter exists so that shows up as a
number. Some misses are expected here and are not a bug: Slumbot re-raises and the
solver knows one raise per street, so those nodes are genuinely off-tree.

**Position alternates.** If `client_pos` never changes, every hand is played from
one seat, and the result carries a positional bias that no number of hands will
average away.

Usage
-----
    venv/bin/python scripts/slumbot_pilot.py --hands 300
"""
import argparse
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

import numpy as np

from slumbot import SlumbotError, play_hand
from slumbot.player import SolverPlayer

STRATEGY = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")
OUT = os.path.join(ROOT, "results", "slumbot")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hands", type=int, default=300)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default=os.path.join(OUT, "pilot.json"))
    args = parser.parse_args()

    player = SolverPlayer(STRATEGY, np.random.default_rng(args.seed))
    hands, errors, positions = [], [], Counter()
    token = None

    print(f"{args.hands} hands, seed {args.seed} — protocol health only\n")
    for index in range(args.hands):
        try:
            state = play_hand(player, token)
            token = state.token
            positions[state.client_pos] += 1
            hands.append({
                "action": state.action,
                "client_pos": state.client_pos,
                "hole_cards": state.hole_cards,
                "board": state.board,
                "winnings": state.winnings,
                "baseline_winnings": state.baseline_winnings,
            })
        except SlumbotError as error:
            errors.append(f"hand {index + 1}: {error}")
        if (index + 1) % 50 == 0:
            print(f"  {index + 1:>4} hands, {len(errors)} errors, "
                  f"miss rate {player.stats.miss_rate:.1%}", flush=True)

    report(player, hands, errors, positions, args)


def report(player, hands, errors, positions, args):
    stats = player.stats
    print(f"\n{'-' * 58}")
    print(f"completed          {len(hands)}/{args.hands}")
    print(f"protocol errors    {len(errors)}")
    for line in errors[:5]:
        print(f"    {line}")
    print(f"decisions          {stats.decisions}")
    print(f"actions sent       {dict(stats.actions_sent)}")
    print(f"lookup miss rate   {stats.miss_rate:.1%} "
          f"({stats.misses}/{stats.consulted})")
    print(f"off-abstraction    {stats.off_abstraction} bets too large to describe")
    print(f"seat distribution  {dict(positions)}")

    if len(positions) < 2:
        print("\n  Position never alternated. Every hand was played from one")
        print("  seat, so any result carries a positional bias that more hands")
        print("  will not average away. This has to be handled before M1.")

    if stats.miss_rate > 0.25:
        print(f"\n  A {stats.miss_rate:.0%} miss rate means the agent chose at")
        print("  random that often. A result measured here is substantially a")
        print("  measurement of a random agent wearing the solver's name.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as handle:
        json.dump({"hands": hands, "errors": errors,
                   "decisions": stats.decisions,
                   "miss_rate": stats.miss_rate,
                   "off_abstraction": stats.off_abstraction,
                   "note": "PILOT — protocol shakedown. Not a result. "
                           "The win rate over these hands is not to be quoted."},
                  handle, indent=1)
    print(f"\nwrote {args.out}")
    print("The win rate is deliberately not printed: this is a pilot, and the")
    print("interval over a few hundred hands is wider than anything it says.")


if __name__ == "__main__":
    main()
