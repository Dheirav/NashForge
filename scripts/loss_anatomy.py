"""
How a bot loses: its lost matches taken apart hand by hand, with both players' cards.

    venv/bin/python scripts/loss_anatomy.py wsp Shadow --since 2026-09-19 --out report.md

The scout cache (`results/chipzen/scout/hands/`) holds both hole cards for every
hand, folds included, so each chip a bot lost can be put in one of five places:

- **folded the best hand**: it folded, and against the cards the other side held
  its equity at that moment was at least a half. Pressure works on it.
- **folded behind**: it folded and was behind. The fold was right; what it cost
  is only what it had put in before.
- **paid off**: it called or checked down to a showdown and lost with a hand
  that was not air. Value betting into it works.
- **bluff called**: it bet or raised on the river holding air (under 0.4 equity
  against a random hand) and lost the showdown. Calling it down works.
- **all in behind or flipped**: the money went in before the river. The share of
  those it was behind in says whether it overplays hands or just ran bad.

For each bot: the split over lost matches and over won ones, the biggest losing
hands with the action, and who beat it. Equity against the actual opposing hand
is Monte Carlo from the native evaluator (`scripts/score_reads.py`'s, not
`allin_edge`, which is wrong on an empty or full board until branch
`native-allin-edge` is merged). Scout amounts are chips added, not street totals.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
MAIN = os.path.expanduser("~/Code/PokerBot")
sys.path.insert(0, MAIN)

import pokerbot_native as native  # noqa: E402
from chipzen.bridge import parse_cards  # noqa: E402

AIR = 0.40
CATEGORIES = ("folded the best hand", "folded behind", "paid off", "bluff called", "all in behind or flipped")


def _ix(cards):
    return [c.index for c in parse_cards(cards)]


def _board(text):
    return [text[i:i + 2] for i in range(0, len(text or ""), 2)]


def equity(mine, theirs, board, samples=600, seed=1):
    used = set(mine) | set(theirs) | set(board)
    deck = np.array([c for c in range(52) if c not in used])
    rng = np.random.default_rng(seed)
    runs = [[]] if len(board) == 5 else [rng.choice(deck, 5 - len(board), replace=False) for _ in range(samples)]
    w = t = 0
    for extra in runs:
        full = list(board) + [int(c) for c in extra]
        a = native.score_hand_7([c % 13 for c in mine + full], [c // 13 for c in mine + full])
        b = native.score_hand_7([c % 13 for c in theirs + full], [c // 13 for c in theirs + full])
        w += a > b
        t += a == b
    return (w + t / 2) / len(runs)


def vs_random(mine, board, samples=400, seed=2):
    return float(native.equity_vs_random(mine, board, samples, seed))


BOARD_AT = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}


def anatomy(hand, seat):
    """(net chips to `seat`, category or None for a win, detail dict)."""
    acts = hand.get("actions") or []
    hole = hand.get("hole_cards") or {}
    mine, theirs = hole.get(str(seat)), hole.get(str(1 - seat))
    if not mine or not theirs:
        return None
    # Heads-up only: a tournament table seats more than two, and the chip split below assumes seats 0 and 1.
    if seat not in (0, 1) or any(int(a.get("seat", 0)) not in (0, 1) for a in acts):
        return None
    board = _board(hand.get("board"))
    put = [0, 0]
    bb = next((a["amount"] for a in acts if a["action"] == "post_big_blind"), 100) or 100
    fold = None
    last_phase = "preflop"
    river_aggr = False
    for a in acts:
        s = a["seat"]
        put[s] += int(a.get("amount") or 0) if a["action"] in ("post_small_blind", "post_big_blind", "call", "raise") else 0
        last_phase = a["phase"]
        if a["action"] == "fold":
            fold = (s, a["phase"])
        if s == seat and a["phase"] == "river" and a["action"] == "raise":
            river_aggr = True
    winners = hand.get("winner_seats") or [hand.get("winner_seat")]
    pot = put[0] + put[1]
    if seat in winners:
        net = pot / len(winners) - put[seat]
    else:
        net = -put[seat]
    detail = {"bb": bb, "net_bb": net / bb, "mine": mine, "theirs": theirs, "board": board,
              "line": " ".join(f"{'X' if a['seat'] == seat else 'o'}:{a['action'][0]}{a.get('amount') or ''}@{a['phase'][0]}"
                               for a in acts if not a["action"].startswith("post"))}
    m, t = _ix(mine), _ix(theirs)
    allin = not fold and (last_phase != "river" or len(board) < 5)
    if net >= 0:
        # Won all-ins are kept for the equity line: counting only the lost ones makes "behind" true by construction.
        if allin:
            detail["allin_eq"] = equity(m, t, _ix(board[:BOARD_AT.get(last_phase, 0)]))
        return net, None, detail
    if fold and fold[0] == seat:
        shown = board[:BOARD_AT[fold[1]]]
        eq = equity(m, t, _ix(shown))
        detail["eq"] = eq
        return net, ("folded the best hand" if eq >= 0.5 else "folded behind"), detail
    b = _ix(board)
    if last_phase != "river" or len(board) < 5 and not fold:
        # the betting ended before the river with both in: an all-in
        pre = board[:BOARD_AT.get(last_phase, 0)]
        eq = equity(m, t, _ix(pre))
        detail["eq"] = eq
        return net, "all in behind or flipped", detail
    strength = vs_random(m, b)
    detail["strength"] = strength
    if river_aggr and strength < AIR:
        return net, "bluff called", detail
    return net, "paid off", detail


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="+")
    parser.add_argument("--since", default="2026-09-19")
    parser.add_argument("--scout-dir", default=os.path.join(MAIN, "results", "chipzen", "scout"))
    parser.add_argument("--top", type=int, default=6)
    parser.add_argument("--out")
    args = parser.parse_args()
    since = dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.timezone.utc)
    matches = json.load(open(os.path.join(args.scout_dir, "season_matches.json"))).values()
    out = [f"# How they lose: the division's matches since {args.since}", "",
           "Each chip a bot lost, by where it went (see the script's docstring). bb: big blinds at the time. "
           "Hindsight against the cards the other side held, so a single hand says little; the split over many does.", ""]
    for name in args.names:
        mine = [m for m in matches if name in [p["name"] for p in m["participants"]]
                and dt.datetime.fromisoformat(m["at"].replace("Z", "+00:00")) >= since]
        split = {True: Counter(), False: Counter()}
        hands_n = {True: 0, False: 0}
        worst, beaten_by, allin_eq = [], Counter(), []
        wins = losses = 0
        for m in mine:
            me = next(p for p in m["participants"] if p["name"] == name)
            other = next(p for p in m["participants"] if p["name"] != name)["name"]
            path = os.path.join(args.scout_dir, "hands", f"{m['id']}.json")
            if not os.path.exists(path):
                continue
            lost = (me["net"] or 0) < 0
            wins += not lost
            losses += lost
            if lost:
                beaten_by[other] += 1
            for hand in json.load(open(path)):
                got = anatomy(hand, me["seat"])
                if not got:
                    continue
                net, cat, d = got
                hands_n[lost] += 1
                if "allin_eq" in d:
                    allin_eq.append(d["allin_eq"])
                if cat:
                    split[lost][cat] += -d["net_bb"]
                    if cat == "all in behind or flipped":
                        allin_eq.append(d.get("eq", 0.5))
                    if lost:
                        worst.append((d["net_bb"], cat, other, d))
        out += [f"## {name}", "", f"{wins + losses} matches with hands cached: {wins} won, {losses} lost. "
                f"Beaten by: {', '.join(f'{o} {n}' for o, n in beaten_by.most_common(6)) or 'nobody'}.", ""]
        if not hands_n[True]:
            out += ["No lost match with hands to read.", ""]
            continue
        out += ["| where the chips went (bb lost per 100 hands) | in its lost matches | in its won matches |", "|---|---|---|"]
        for cat in CATEGORIES:
            a = 100 * split[True][cat] / max(hands_n[True], 1)
            b = 100 * split[False][cat] / max(hands_n[False], 1)
            out.append(f"| {cat} | {a:.0f} | {b:.0f} |")
        if allin_eq:
            behind = sum(1 for e in allin_eq if e < 0.45)
            out.append(f"\nCalled all-ins before the river, won and lost: {len(allin_eq)}, behind in {behind} "
                       f"({100 * behind / len(allin_eq):.0f}%), mean equity {np.mean(allin_eq):.2f}.")
        out += ["", f"Its {args.top} biggest losing hands:", ""]
        for net_bb, cat, other, d in sorted(worst, key=lambda t: t[0])[:args.top]:
            extra = f" eq {d['eq']:.2f}" if "eq" in d else (f" strength {d['strength']:.2f}" if "strength" in d else "")
            out.append(f"- {net_bb:+.0f} bb vs {other}: {' '.join(d['mine'])} against {' '.join(d['theirs'])} "
                       f"[{' '.join(d['board'])}], {cat}{extra}. `{d['line'][:140]}`")
        out.append("")
        print(f"  {name}: {wins + losses} matches read", flush=True)
    text = "\n".join(out)
    if args.out:
        open(args.out, "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
