"""
What a ladder that has not played yet would have done in the logged hands.

    venv/bin/python scripts/chipzen_replay.py --ladder-dir results/cfr/ladder169
    venv/bin/python scripts/chipzen_replay.py --ladder-dir results/cfr/ladder169 --baseline-dir results/cfr/ladder200t

The arena quota is twenty matches a day, so a new solver set cannot be tried
on the platform the evening it is built. The match logs hold every decision
with our cards, the board, the solver's own history key and the legal mask,
which is everything a lookup needs, so the question "what would the new set
do here" is answered offline for all 9,780 logged decisions rather than for
the twenty matches tomorrow allows.

Two things this is not. It is not a win-rate: the opponent's replies to a
different action are unknown, so only the first divergence in a hand is real.
And it is not the whole player: a miss on the primary solver is counted as a
miss, not re-answered by the companion, because the companion's history is on
its own schedule and the log holds only the primary's.

The baseline set is looked up the same way, and the logged choice's
probability under it is the check on the method: the bot sampled from that
distribution, so it should be high. Rungs are loaded one at a time, because a
full set is 2.4 GB and the live bot already holds one.
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from math import log

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np  # noqa: E402

from chipzen.player import load_solver  # noqa: E402
from evaluation.benchmark import NUM_ACTIONS, _solver_actions  # noqa: E402
from scripts.chipzen_review import DIRS, ACTION, hands_of, load, net  # noqa: E402
from scripts.chipzen_run import ladder_paths  # noqa: E402
from slumbot.bridge import parse_cards  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "chipzen", "replay.md")


def depth_of(path):
    name = os.path.basename(path)
    if "strategy" in name:
        return 200.0                     # the shipped 200bb solver, the one rung not named by depth
    return float(name.split("_")[1].replace("bb.pkl", ""))


def rung_for(depths, effective_bb):
    """`ArenaPlayer.solver_for`, on file names, so nothing is loaded to choose."""
    if effective_bb <= 0:
        return min(depths)
    return min(depths, key=lambda d: abs(log(d) - log(effective_bb)))


def lookup(solver, decision):
    """The solver's distribution over the arena's legal actions, or None on a miss."""
    hole = parse_cards(decision["hole"])
    board = parse_cards(decision["board"] or [])
    key = (tuple(c.index for c in hole), tuple(c.index for c in board))
    bucket = solver.abstraction.bucket(hole, board, np.random.default_rng(hash(key) % (2 ** 32)))
    probabilities = solver.strategy.get(f"{bucket}|{decision['history']}")
    if probabilities is None:
        return None
    # Spread onto the six abstract actions exactly as `cfr_agent` does: an
    # entry is stored over the node's own legal-action list, not six wide.
    actions = _solver_actions(decision["history"], decision["to_call"], solver.schedule)
    if len(actions) != probabilities.size:
        return None                      # the reconstruction disagrees with the stored width
    mask = np.asarray(decision["legal"], dtype=float)
    weights = np.zeros(NUM_ACTIONS)
    for action, probability in zip(actions, probabilities):
        weights[action] = float(probability) * mask[action]
    return weights / weights.sum() if weights.sum() > 0 else None


def answer(ladder_dir, deep_primary, decisions):
    """Distribution per decision id, loading one rung at a time."""
    _, ladder, _ = ladder_paths(ladder_dir, deep_primary)
    by_depth = {depth_of(p): p for p in ladder}
    grouped = defaultdict(list)
    for d in decisions:
        grouped[rung_for(list(by_depth), d["effective_bb"])].append(d)
    out = {}
    for depth, rows in sorted(grouped.items()):
        solver = load_solver(by_depth[depth], np.random.default_rng(0))
        for d in rows:
            out[id(d)] = lookup(solver, d)
        del solver
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ladder-dir", required=True)
    parser.add_argument("--baseline-dir", default=os.path.join(ROOT, "results", "cfr", "ladder200t"))
    parser.add_argument("--no-deep-primary", action="store_true")
    parser.add_argument("--worst", type=int, default=8)
    parser.add_argument("--label-prefix", help="only matches whose version label starts with this, "
                        "e.g. v3: the baseline check is only clean on matches the baseline set played")
    parser.add_argument("--out", default=OUT)
    args = parser.parse_args()
    deep = not args.no_deep_primary

    all_hands = []
    for directory in DIRS:
        for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
            rows = load(path)
            if args.label_prefix:
                label = next((r.get("version", {}).get("label", "") for r in rows
                              if r.get("frame") == "match_start"), "")
                if not label.startswith(args.label_prefix):
                    continue
            seat, opponent, hands, _ = hands_of(rows)
            for h in hands:
                all_hands.append((h, seat, opponent, os.path.basename(path)[:8]))
    decisions = [d for h, *_ in all_hands for d in h["decisions"]]

    new = answer(args.ladder_dir, deep, decisions)
    old = answer(args.baseline_dir, deep, decisions)

    lines = [f"# Replay: {os.path.relpath(args.ladder_dir, ROOT)} on the logged hands", "",
             f"{len(decisions)} decisions from {len(all_hands)} hands"
             + (f" (matches labelled {args.label_prefix}*)" if args.label_prefix else "")
             + f"; baseline {os.path.relpath(args.baseline_dir, ROOT)}.", ""]

    # ---- coverage and agreement --------------------------------------------
    cov = Counter()
    p_new, p_old, changed = [], [], Counter()
    by_street = defaultdict(lambda: {"n": 0, "p_new": 0.0, "p_old": 0.0, "differs": 0})
    for d in decisions:
        n, o = new[id(d)], old[id(d)]
        cov["logged miss"] += int(bool(d.get("miss")))
        cov["new miss"] += int(n is None)
        cov["baseline miss"] += int(o is None)
        if n is None or o is None:
            continue
        cov["compared"] += 1
        row = by_street[d["phase"]]
        row["n"] += 1
        row["p_new"] += n[d["choice"]]
        row["p_old"] += o[d["choice"]]
        if int(n.argmax()) != int(o.argmax()):
            row["differs"] += 1
            changed[(ACTION[int(o.argmax())], ACTION[int(n.argmax())])] += 1
    lines += ["## Coverage", "",
              f"logged misses {cov['logged miss']}, baseline lookup misses {cov['baseline miss']} "
              f"(these should match), new-set misses {cov['new miss']}; {cov['compared']} decisions compared.", "",
              "## Agreement with what was played", "",
              "Mean probability the set gives the action actually taken. The baseline played these, "
              "so its column is the check on the lookup; the new set's column is how differently it would play.", "",
              "| street | compared | P(baseline) | P(new) | most likely action differs |", "|---|---|---|---|---|"]
    for street in ("preflop", "flop", "turn", "river"):
        r = by_street[street]
        if r["n"]:
            lines.append(f"| {street} | {r['n']} | {r['p_old'] / r['n']:.2f} | {r['p_new'] / r['n']:.2f} "
                         f"| {r['differs']} ({100 * r['differs'] / r['n']:.0f}%) |")
    lines += ["", "Most common changes of most-likely action (baseline → new):", ""]
    for (a, b), n in changed.most_common(8):
        lines.append(f"- {a} → {b}: {n}")

    # ---- the big calls ------------------------------------------------------
    big = [d for d in decisions if d["to_call"] > 0 and d["to_call"] >= d["pot"] - d["to_call"]
           and d["choice"] == 1 and new[id(d)] is not None and old[id(d)] is not None]
    lines += ["", "## Calls of a bet of the pot or more", "",
              f"{len(big)} such calls were made. Call probability under each set:", "",
              "| hand | street | ours | board | to call | pot | baseline call | new call |", "|---|---|---|---|---|---|---|---|"]
    for d in sorted(big, key=lambda d: -d["to_call"])[:20]:
        lines.append(f"| {d['hand']} | {d['phase']} | {' '.join(d['hole'])} | {' '.join(d['board'] or []) or '-'} "
                     f"| {d['to_call']:,} | {d['pot']:,} | {old[id(d)][1]:.2f} | {new[id(d)][1]:.2f} |")
    if big:
        lines += ["", f"Mean call probability over all {len(big)}: baseline "
                  f"{np.mean([old[id(d)][1] for d in big]):.2f}, new {np.mean([new[id(d)][1] for d in big]):.2f}."]

    # ---- the expensive hands, re-asked -------------------------------------
    lost = sorted((x for x in all_hands if x[0]["result"] and net(x[0], x[1]) < 0),
                  key=lambda x: net(x[0], x[1]))[:args.worst]
    lines += ["", f"## The {len(lost)} most expensive hands, re-asked", "",
              "Only the first decision that differs is a real divergence; after it the opponent's "
              "replies are unknown.", ""]
    for h, seat, opponent, tag in lost:
        start, result = h["start"], h["result"]
        showdown = {s["seat"]: s.get("hole_cards") or s.get("cards") for s in result.get("showdown") or []}
        theirs = showdown.get(1 - seat)
        lines.append(f"**{net(h, seat):+,} vs {opponent}**, hand {start['hand_number']} ({tag}), we held "
                     f"{' '.join(start['your_hole_cards'])}" + (f", they showed {' '.join(theirs)}" if theirs else "") + ".")
        for d in h["decisions"]:
            n = new[id(d)]
            board = " ".join(d.get("board") or []) or "-"
            if n is None:
                verdict = "new set: no entry"
            else:
                dist = ", ".join(f"{ACTION[i]} {p:.2f}" for i, p in enumerate(n) if p > 0.005)
                verdict = f"new set: {dist}"
            lines.append(f"  - {d['phase']:7} board {board:14} key `{d['history']}` to call {d['to_call']:,} "
                         f"→ played **{ACTION.get(d['choice'])}**; {verdict}")
        lines.append("")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
