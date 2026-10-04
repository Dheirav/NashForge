"""
An anytime-valid verdict between versions, safe to read after every burst.

    venv/bin/python scripts/burst_verdict.py --label "v5xRR3 purified"
    venv/bin/python scripts/burst_verdict.py --label "v5xRR3 purified" balanced-next
    venv/bin/python scripts/burst_verdict.py --label "v5xRR3 purified" --opponent Blueprint

Deciding after each burst with a fixed-sample test is a sequential test read at the wrong level:
five looks at a nominal 5 percent give about 14 percent false positives. The intervals printed
here are confidence sequences (evaluation/sequential.py), which hold at every sample size at once,
so the verdict may be read after every burst and acted on whenever it says so, and the error rate
stays at alpha. An "undecided" line is the instruction to keep playing; the "about N more" figure
beside it is a projection at the observed rate, an estimate for planning and nothing more.

Two quantities, each with its own verdict: match win rate (the rating moves on this) and chips per
decision hand (better resolved, but a different estimand and dominated by all-ins). The opponent
mix of each version is printed because the interval says nothing about it: two versions that met
different opponents are compared on their opponents as much as on themselves.
"""
import argparse
import ast
import glob
import json
import os
import re
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation.sequential import (ALPHA, NO_CLIP, chips_verdict_one, chips_verdict_two,  # noqa: E402
                                   match_verdict_one, match_verdict_two)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH = os.path.expanduser("~/pokerbot-scratch/chipzen")
MATCH_DIRS = [os.path.join(ROOT, "results", "chipzen", "matches"), os.path.join(SCRATCH, "matches")]
RUN_LOG = os.path.join(SCRATCH, "run.log")


def hand_nets(rows, seat):
    """
    Net chips per hand for our seat: our stack after the hand minus before it.

    Payouts minus puts read a raise's amount as everything put in, when it is the street's total,
    and ran optimistic by +100 to +190 a hand until 2 October; the stack difference has no such
    trap, which is why decompose moved to it.
    """
    net, before = {}, None
    for r in rows:
        if r.get("frame") == "round_start":
            before = (r.get("state") or {}).get("stacks")
        elif r.get("frame") == "round_result":
            res = r["result"]
            after = res.get("stacks")
            if before and after:
                net[res["hand_number"]] = after[seat] - before[seat]
            before = None
    return net


def logged_outcomes(path):
    """match_id -> 'won' / 'lost' / None from the client's 'match ... ended:' lines."""
    out = {}
    if not os.path.exists(path):
        return out
    pattern = re.compile(r"match (\S+) ended: (\{.*\})\s*$")
    with open(path, errors="replace") as handle:
        for line in handle:
            m = pattern.search(line)
            if m:
                try:
                    out[m.group(1)] = ast.literal_eval(m.group(2)).get("outcome")
                except (ValueError, SyntaxError):
                    pass
    return out


def outcome_of(rows, seat, logged):
    """
    True for a win, False for a loss, None if the file cannot say.

    The run log is the arena's own word; the match_end net and then the last hand's stacks are the
    fallbacks for matches the log missed. A match that stopped with both players holding chips and
    no logged outcome is left out rather than guessed.
    """
    if logged in ("won", "lost"):
        return logged == "won", "run.log"
    for r in rows:
        if r.get("frame") == "match_end" and r.get("results"):
            net = next((x["net_chips"] for x in r["results"] if x["seat"] == seat), None)
            if net:
                return net > 0, "match_end"
    last = next((r["result"].get("stacks") for r in reversed(rows) if r.get("frame") == "round_result"), None)
    if last and 0 in last:
        return last[seat] > 0, "stacks"
    return None, "unresolved"


def load(dirs, run_log, labels, opponent=None, include_unrated=False):
    """Per label prefix, the matches in time order, each with its outcome and decision-hand nets."""
    logged = logged_outcomes(run_log)
    seen, per = set(), {l: [] for l in labels}
    skipped = Counter()
    for d in dirs:
        for path in glob.glob(os.path.join(d, "*.jsonl")):
            with open(path) as handle:
                rows = [json.loads(line) for line in handle if line.strip()]
            if not rows or rows[0].get("frame") != "match_start" or "version" not in rows[0]:
                continue
            head = rows[0]
            label = head["version"].get("label", "")
            tag = next((l for l in labels if label.startswith(l + ":") or label == l), None)
            if tag is None:
                continue
            mid = head.get("match_id") or os.path.basename(path)[:-len(".jsonl")]
            if mid in seen:                            # the same match can sit in both directories
                continue
            seen.add(mid)
            if not head.get("rated") and not include_unrated:
                skipped["unrated"] += 1
                continue
            seat = head["seat"]
            opp = next((s["display_name"] for s in head.get("seats", []) if not s.get("is_self")), None)
            if opp is None:
                opp = next((r.get("opponent") for r in rows if "history" in r and r.get("opponent")), None)
            if opponent and opp != opponent:
                continue
            won, source = outcome_of(rows, seat, logged.get(mid))
            if won is None:
                skipped["no outcome"] += 1
                continue
            nets = hand_nets(rows, seat)
            decided = sorted({r["hand"] for r in rows if "history" in r})
            per[tag].append({
                "id": mid, "at": head.get("at") or os.path.getmtime(path), "opponent": opp, "won": won,
                "source": source, "nets": [nets[h] for h in decided if h in nets],
            })
    for l in labels:
        per[l].sort(key=lambda m: m["at"])
    return per, skipped


def show(v):
    lo, hi = v.interval
    n = " and ".join(f"{x:,}" for x in v.n)
    rate = "match win rate" in v.what
    fmt = (lambda x: f"{x:+.1%}" if "minus" in v.what else f"{x:.1%}") if rate else (lambda x: f"{x:+,.0f}")
    print(f"  {v.what}  (n = {n})")
    print(f"    estimate {fmt(v.estimate)}, anytime-valid interval [{fmt(lo)}, {fmt(hi)}]")
    for note in v.notes:
        print(f"    {note}")
    print(f"    verdict: {v.verdict}" + (f"; {v.projection}" if v.projection else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", nargs="+", required=True,
                        help="one version label prefix (judged against --p0), or two (A against B)")
    parser.add_argument("--opponent", help="only matches against this bot")
    parser.add_argument("--p0", type=float, default=0.5, help="the win rate a single version is judged against")
    parser.add_argument("--alpha", type=float, default=ALPHA)
    parser.add_argument("--clip", type=float, default=NO_CLIP,
                        help="clip per-hand nets to ±this; the default is the effective stack, so nothing is clipped")
    parser.add_argument("--matches-dir", nargs="+", default=MATCH_DIRS)
    parser.add_argument("--run-log", default=RUN_LOG)
    parser.add_argument("--include-unrated", action="store_true")
    args = parser.parse_args()
    if len(args.label) > 2:
        parser.error("--label takes one version or two")

    per, skipped = load(args.matches_dir, args.run_log, args.label, args.opponent, args.include_unrated)
    print(f"alpha {args.alpha}, every interval valid at every sample size (read it after any burst)"
          + (f", against {args.opponent} only" if args.opponent else ""))
    if skipped:
        print("left out: " + ", ".join(f"{v} {k}" for k, v in skipped.items()))
    for l in args.label:
        ms = per[l]
        mix = Counter(m["opponent"] for m in ms)
        hands = sum(len(m["nets"]) for m in ms)
        print(f"\n{l}: {len(ms)} matches, {sum(m['won'] for m in ms)} won, {hands:,} decision hands; opponents "
              + (", ".join(f"{o} {c}" for o, c in mix.most_common()) or "none"))

    def per_match(*labels):
        ms = [m for l in labels for m in per[l]]
        return sum(len(m["nets"]) for m in ms) / len(ms) if ms else None

    print()
    for l in args.label:
        show(match_verdict_one([m["won"] for m in per[l]], args.p0, args.alpha, name=l))
    for l in args.label:
        nets = [x for m in per[l] for x in m["nets"]]
        show(chips_verdict_one(nets, 0.0, args.clip, args.alpha, name=l, per_match=per_match(l)))
    if len(args.label) == 2:
        a, b = args.label
        show(match_verdict_two([m["won"] for m in per[a]], [m["won"] for m in per[b]], args.alpha, names=(a, b)))
        show(chips_verdict_two([x for m in per[a] for x in m["nets"]], [x for m in per[b] for x in m["nets"]],
                               args.clip, args.alpha, names=(a, b), per_match=per_match(a, b)))
        if set(m["opponent"] for m in per[a]) != set(m["opponent"] for m in per[b]):
            print("\n  the two versions met different opponents, so the difference is partly an opponent difference")


if __name__ == "__main__":
    main()
