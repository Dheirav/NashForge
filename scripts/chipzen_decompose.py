"""
A burst decomposed: where the chips went, by depth and by which solver decided.

    venv/bin/python scripts/chipzen_decompose.py --label v7b
    venv/bin/python scripts/chipzen_decompose.py --label v7 v7b v6 --opponent Blueprint

The headline of a twenty-match burst is ±40 chips a hand and put the wrong set
forward twice in season 6 (NEXT.md, 18 September). What decided v6 was fifteen
preflop jams by the cap-2 primary at −2,545 each; what decided v7 was the 109
hands the companion took over at −423 each; neither shows in a win rate. So a
burst is read like this before anything is recommended on it: chips per hand
overall, at deep and short stacks, on the hands a companion or the rule
decided, on our preflop jams and on river calls against a shove, with the
standard error of each, since 300 short-stack hands cannot resolve 30 chips.

Everything is counted from the per-match JSONL (`chipzen.client` writes one
line per decision and one per hand result); nothing here judges a play.
"""
import argparse
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MATCHES = os.path.join(ROOT, "results", "chipzen", "matches")
DEEP = {"50bb", "70bb", "100bb", "200bb"}


def hand_nets(rows, seat):
    """Net chips per hand for our seat, from the result frames' payouts and our own puts."""
    net = {}
    for r in rows:
        if r.get("frame") != "round_result":
            continue
        res = r["result"]
        pay = sum(p["amount"] for p in res["payouts"] if p["seat"] == seat)
        put = 0
        for a in res.get("action_history", []):
            if a["seat"] == seat:
                if a["action"] in ("raise", "bet", "all_in"):
                    put = a["amount"]              # a raise's amount is the total put in this street
                elif a["action"] in ("call", "post_small_blind", "post_big_blind"):
                    put += a["amount"]
        net[res["hand_number"]] = pay - put
    return net


def classify(decisions):
    """The categories one hand falls into, from its decision records."""
    cats = {"all"}
    cats.add("deep" if decisions[0]["solver"] in DEEP else "short")
    if any(d.get("companion") for d in decisions):
        cats.add("companion decided")
    if any(d.get("fallback") for d in decisions):
        cats.add("rule decided")
    if any(d["phase"] == "preflop" and d["choice"] == 5 for d in decisions):
        cats.add("we jammed preflop")
    if any(d["phase"] == "preflop" and d["history"].endswith("5") and d["choice"] == 1 for d in decisions):
        cats.add("called a preflop jam")
    if any(d["phase"] == "river" and d["history"].endswith("5") and d["choice"] == 1 for d in decisions):
        cats.add("called a river shove")
    if any(d.get("adjusted") for d in decisions):
        cats.add("a read fired")
    return cats


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", nargs="+", required=True, help="version label prefixes, e.g. v7 v7b")
    parser.add_argument("--opponent", help="only matches against this bot")
    parser.add_argument("--matches-dir", default=MATCHES)
    args = parser.parse_args()

    per_label = defaultdict(lambda: defaultdict(list))
    for path in glob.glob(os.path.join(args.matches_dir, "*.jsonl")):
        with open(path) as handle:
            rows = [json.loads(line) for line in handle]
        if not rows or rows[0].get("frame") != "match_start" or "version" not in rows[0]:
            continue
        label = rows[0]["version"]["label"]
        tag = next((l for l in args.label if label.startswith(l + ":") or label == l), None)
        if tag is None:
            continue
        seat = rows[0]["seat"]
        decisions = defaultdict(list)
        opponent = None
        for r in rows:
            if "history" in r:
                decisions[r["hand"]].append(r)
                opponent = r.get("opponent")
        if args.opponent and opponent != args.opponent:
            continue
        nets = hand_nets(rows, seat)
        for hand, ds in decisions.items():
            if hand not in nets:
                continue
            for cat in classify(ds):
                per_label[tag][cat].append(nets[hand])

    order = ["all", "deep", "short", "companion decided", "rule decided", "we jammed preflop",
             "called a preflop jam", "called a river shove", "a read fired"]
    labels = [l for l in args.label if l in per_label]
    print(f"chips per hand ± standard error (hands), on decision hands"
          + (f" against {args.opponent}" if args.opponent else "") + "\n")
    print("| category | " + " | ".join(labels) + " |")
    print("|---|" + "---|" * len(labels))
    for cat in order:
        cells = []
        for l in labels:
            x = np.array(per_label[l].get(cat, []), dtype=float)
            if x.size == 0:
                cells.append("—")
            else:
                se = x.std() / np.sqrt(x.size) if x.size > 1 else float("nan")
                cells.append(f"{x.mean():+.0f} ± {se:.0f} ({x.size})")
        print(f"| {cat} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
