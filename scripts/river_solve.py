"""
Re-solve the rivers the bot already played, and compare with what it did.

    venv/bin/python scripts/river_solve.py --ladder-dir results/cfr/ladder200t --last 10
    venv/bin/python scripts/river_solve.py --ladder-dir results/cfr/ladder200t --opponent Blueprint

For every river decision in the match logs, rebuild the chip state from the
hand's frames (the decision record carries pot and to-call; the stacks come
from the round's start stacks less each seat's contributions up to that
action), take the blueprint's ranges along the logged history, solve the river
(cfr/river.py) and print the solved distribution beside the action played.
Writes `results/chipzen/river_resolve.md`.

The same caveat as the replay: after the first divergence the opponent's
replies are unknown, so this is a check that the solver disagrees where the
chips went, not a win rate. Solving a river costs a few seconds, so --last
bounds the run.
"""
import argparse
import glob
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np  # noqa: E402

from cfr.river import decide_river  # noqa: E402
from chipzen.player import load_solver  # noqa: E402
from scripts.chipzen_replay import depth_of, rung_for  # noqa: E402
from scripts.chipzen_review import ACTION, DIRS, hands_of, load, net  # noqa: E402
from scripts.chipzen_run import ladder_paths  # noqa: E402
from slumbot.bridge import parse_cards  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "chipzen", "river_resolve.md")


def chip_state(hand, seat, decision):
    """
    The arena state at a logged river decision, rebuilt from the round frames.

    Our stack and theirs at that moment are the start stacks less everything
    each seat put in before the action; the decision's own pot and to-call are
    on its record. Returns None if the frames do not line up.
    """
    start = hand["start"]
    result = hand["result"]
    if not result:
        return None
    history = result.get("action_history") or []
    ours_before = [d for d in hand["decisions"] if d is not decision]
    ordinal = sum(1 for d in ours_before if hand["decisions"].index(d) < hand["decisions"].index(decision))
    contributed = [0, 0]
    seen_ours = 0
    posted_sb = None
    for action in history:
        kind = action["action"]
        if kind == "post_small_blind":
            posted_sb = action["seat"]
        if kind.startswith("post"):
            contributed[action["seat"]] += int(action.get("amount") or 0)
            continue
        if action["seat"] == seat:
            if seen_ours == ordinal:
                break
            seen_ours += 1
        contributed[action["seat"]] += int(action.get("amount") or 0)
    stacks = start["stacks"]
    return {
        "pot": decision["pot"], "to_call": decision["to_call"],
        "your_stack": stacks[seat] - contributed[seat],
        "opponent_stacks": [stacks[1 - seat] - contributed[1 - seat]],
        "board": decision["board"], "your_hole_cards": decision["hole"],
        "action_history": history,
    }, posted_sb == seat


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ladder-dir", default=os.path.join(ROOT, "results", "cfr", "ladder200t"))
    parser.add_argument("--no-deep-primary", action="store_true")
    parser.add_argument("--last", type=int, default=20, help="most recent river decisions to solve")
    parser.add_argument("--opponent")
    parser.add_argument("--iterations", type=int, default=400)
    parser.add_argument("--budget", type=float, default=8.0)
    parser.add_argument("--out", default=OUT)
    args = parser.parse_args()

    rivers = []
    for directory in DIRS:
        for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
            seat, opponent, hands, _ = hands_of(load(path))
            if args.opponent and opponent != args.opponent:
                continue
            for h in hands:
                for d in h["decisions"]:
                    if d["phase"] == "river" and len(d.get("board") or []) == 5:
                        rivers.append((h, seat, opponent, d, os.path.basename(path)[:8]))
    rivers = rivers[-args.last:]
    if not rivers:
        sys.exit("no river decisions in the logs")

    _, ladder, _ = ladder_paths(args.ladder_dir, not args.no_deep_primary)
    by_depth = {depth_of(p): p for p in ladder}
    loaded = {}
    lines = [f"# Rivers re-solved: {os.path.relpath(args.ladder_dir, ROOT)}", "",
             f"{len(rivers)} river decisions, {args.iterations} iterations each, {args.budget:.0f} s budget.", "",
             "| match | hand | vs | net | ours | board | pot | to call | played | solved distribution | ms |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    agree = Counter()
    for h, seat, opponent, d, tag in rivers:
        rebuilt = chip_state(h, seat, d)
        if rebuilt is None:
            continue
        state, we_are_sb = rebuilt
        depth = rung_for(list(by_depth), d["effective_bb"])
        if depth not in loaded:
            loaded[depth] = load_solver(by_depth[depth], np.random.default_rng(0))
        solver = loaded[depth]
        legal = np.asarray(d["legal"], dtype=float)
        try:
            out = decide_river(state, parse_cards(d["hole"]), parse_cards(d["board"]), d["history"],
                               solver.strategy, solver.abstraction, solver.schedule, we_are_sb,
                               np.random.default_rng(0), legal, args.iterations, args.budget)
        except Exception as error:
            lines.append(f"| {tag} | {d['hand']} | {opponent} | | {' '.join(d['hole'])} | {' '.join(d['board'])} "
                         f"| {d['pot']:,} | {d['to_call']:,} | {ACTION.get(d['choice'])} | failed: {error} | |")
            continue
        dist = ", ".join(f"{ACTION[a]} {p:.2f}" for a, p in sorted(out.distribution.items()) if p > 0.005)
        top = max(out.distribution, key=out.distribution.get)
        agree["same most likely" if top == d["choice"] else "differs"] += 1
        lines.append(f"| {tag} | {d['hand']} | {opponent} | {net(h, seat):+,} | {' '.join(d['hole'])} | "
                     f"{' '.join(d['board'])} | {d['pot']:,} | {d['to_call']:,} | **{ACTION.get(d['choice'])}** "
                     f"| {dist} | {out.ms:.0f} |")
    lines += ["", f"Most likely action agrees with the play in {agree['same most likely']} of "
              f"{sum(agree.values())} rivers."]
    text = "\n".join(lines)
    print(text)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as handle:
        handle.write(text + "\n")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
