"""
Score the reads that fired in logged matches against the cards the opponent held.

    venv/bin/python scripts/score_reads.py results/chipzen/matches/<id>.jsonl ...
    venv/bin/python scripts/score_reads.py --since "2026-09-25 21:55" --opponent PoetAndCoder

A read replaces the solver's action. Whether it helped is only visible against
what the opponent actually held, and the platform shows the winner's cards even
without a showdown, so every read that turns a call into a fold is fully
scorable: calling was worth equity x (pot + to call) - to call. That is exact
when the call ends the betting (an all-in, or the river) and approximate
otherwise. A read that turns a fold into an open is scored against folding,
which costs the small blind.

On 25 September this was done three times by hand and gave: "shove call
declined" against Shadow, 12 firings, 19,785 chips given up; against Blueprint,
60 firings, -0.34 ± 1.25 bb each; "opened into a folding blind", +0.38 ± 0.43.

The equity is Monte Carlo over the runout from the native evaluator, not
`pokerbot_native.allin_edge`: until branch `native-allin-edge` is merged that
function scores an empty board as a river and a full one past the end of its
arrays, and it read T7s as 70% against AK.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pokerbot_native as native  # noqa: E402
from chipzen.bridge import parse_cards  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
#: Reads that replace a call with a fold: scored by what the call was worth.
CALL_TO_FOLD = {"shove call declined", "river bet believed", "big bet believed"}
#: Reads that replace a fold with an open or a call: scored against folding.
FOLD_TO_ACTION = {"opened into a folding blind", "three-bet into a folder", "small bet called"}


def equity(mine, theirs, board, samples=20000, seed=1):
    """P(win) + P(tie)/2 for `mine`; exact on a full board, sampled otherwise."""
    used = set(mine) | set(theirs) | set(board)
    deck = np.array([c for c in range(52) if c not in used])
    rng = np.random.default_rng(seed)
    runs = [[]] if len(board) == 5 else [rng.choice(deck, 5 - len(board), replace=False) for _ in range(samples)]
    win = tie = 0
    for extra in runs:
        full = list(board) + [int(c) for c in extra]
        a = native.score_hand_7([c % 13 for c in mine + full], [c // 13 for c in mine + full])
        b = native.score_hand_7([c % 13 for c in theirs + full], [c // 13 for c in theirs + full])
        win += a > b
        tie += a == b
    return (win + tie / 2) / len(runs)


def _cards(names):
    return [c.index for c in parse_cards(names)]


def score(paths, samples):
    """{read: [(value in big blinds, one-line description)]}; positive = the read helped."""
    out = defaultdict(list)
    for path in paths:
        rows = [json.loads(line) for line in open(path)]
        me = rows[0]["seat"]
        results = {r["result"]["hand_number"]: r["result"] for r in rows if r.get("frame") == "round_result"}
        starts = {r["state"]["hand_number"]: r["state"] for r in rows if r.get("frame") == "round_start"}
        for d in rows:
            read = d.get("adjusted") if d.get("frame") == "decision" else None
            if not read or d["hand"] not in results:
                continue
            h = results[d["hand"]]
            bb = max((a["amount"] for a in h["action_history"] if a["action"] == "post_big_blind"), default=100)
            if read in CALL_TO_FOLD:
                shown = {s["seat"]: s["hole_cards"] for s in h.get("showdown") or []}
                theirs = shown.get(1 - me)
                if not theirs:
                    continue
                eq = equity(_cards(d["hole"]), _cards(theirs), _cards(d["board"]), samples)
                called = eq * (d["pot"] + d["to_call"]) - d["to_call"]
                out[read].append((-called / bb, f"#{d['hand']} {d['phase']} {' '.join(d['hole'])} vs "
                                                f"{' '.join(theirs)} [{' '.join(d['board'])}] eq {eq:.2f}"))
            elif read in FOLD_TO_ACTION:
                small = next((a["amount"] for a in h["action_history"] if a["action"] == "post_small_blind"), 0)
                gained = h["stacks"][me] - starts[d["hand"]]["stacks"][me]
                folding = -small if read == "opened into a folding blind" else 0
                out[read].append(((gained - folding) / bb, f"#{d['hand']} {d['phase']} {' '.join(d['hole'])}"))
            else:
                out[read].append((float("nan"), f"#{d['hand']} not scorable from the log"))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--since", help="every logged match starting at or after this local time")
    parser.add_argument("--opponent")
    parser.add_argument("--samples", type=int, default=20000)
    args = parser.parse_args()
    paths = list(args.paths)
    if args.since:
        since = dt.datetime.fromisoformat(args.since).timestamp()
        for f in glob.glob(os.path.join(ROOT, "results", "chipzen", "matches", "*.jsonl")):
            first = json.loads(open(f).readline())
            opp = [s["display_name"] for s in first.get("seats", []) if not s.get("is_self")]
            if first.get("at", 0) >= since and (not args.opponent or opp[:1] == [args.opponent]):
                paths.append(f)
    if not paths:
        raise SystemExit("no match records")
    print(f"{len(paths)} match record(s)\n")
    for read, rows in sorted(score(paths, args.samples).items()):
        values = [v for v, _ in rows if not math.isnan(v)]
        if not values:
            print(f"{read}: {len(rows)} firing(s), none scorable from the log\n")
            continue
        n = len(values)
        mean = sum(values) / n
        se = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1) / n) if n > 1 else float("nan")
        print(f"{read}: {n} scored, {mean:+.2f} ± {se:.2f} bb a firing (positive: the read helped), "
              f"total {sum(values):+.1f} bb")
        for v, text in sorted(rows, key=lambda t: t[0])[:3]:
            print(f"   worst: {v:+.1f} bb  {text}")
        print()


if __name__ == "__main__":
    main()
