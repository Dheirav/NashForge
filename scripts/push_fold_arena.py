"""
The same short-stack pricing, for the bots we actually play.

    venv/bin/python scripts/push_fold_arena.py --max-bb 12
    venv/bin/python scripts/push_fold_arena.py --names hoops Blueprint wsp --out errors.md

`push_fold_errors.py` priced the published corpus, where every hand carries
its stacks. The scout's cached hands do not, but they do not need to: an arena
match starts at 10,000 chips a seat and every chip that moves is an action, so
walking a match in order reconstructs the stack at the start of each hand. The
blinds come from the posts, which escalate through a match.

Same measurement as the corpus one: at or under `--max-bb` big blinds, what a
bot gives up per decision by shoving or folding against the exact solution of
the push-fold game (`push_fold.py`). Read it as an upper bound on what a
short-stack exploiter could take from that bot preflop, and note that the
scout's cache holds 40 matches a bot, so the counts are thousands rather than
the corpus's tens of thousands.
"""
import argparse
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.push_fold import combos_of, hand_labels, solve  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HANDS = os.path.join(ROOT, "results", "chipzen", "scout", "hands")
RANKS = "23456789TJQKA"
ARENA_STACK = 10000


def hand_class(cards) -> str:
    (r1, s1), (r2, s2) = (cards[0][0], cards[0][1]), (cards[1][0], cards[1][1])
    high, low = (r1, r2) if RANKS.index(r1) >= RANKS.index(r2) else (r2, r1)
    return f"{high}{high}" if r1 == r2 else f"{high}{low}{'s' if s1 == s2 else 'o'}"


def walk_match(hands):
    """
    Yield (hand, stacks_at_start, big_blind, sb_seat) for a match, in order.

    Stacks are reconstructed: both seats start at 10,000 and each hand moves
    what its actions put in and its payouts take out. The cache has no payouts,
    so the winner takes the contested pot: each seat's contributions are summed
    from the actions, and the winner is credited the total. A split gives half
    each. That reproduces the arena's accounting for every hand that is not a
    side-pot case, which heads-up cannot produce.
    """
    stacks = [ARENA_STACK, ARENA_STACK]
    for hand in sorted(hands, key=lambda h: h.get("hand_number", 0)):
        actions = hand.get("actions") or []
        if not actions:
            continue
        big_blind = max((int(a.get("amount") or 0) for a in actions
                         if a.get("action") == "post_big_blind"), default=0)
        sb_seat = next((int(a["seat"]) for a in actions if a.get("action") == "post_small_blind"), 0)
        if not big_blind or min(stacks) <= 0:
            return
        yield hand, list(stacks), big_blind, sb_seat
        # What each seat put in, summed per street: a raise's amount is the
        # level for that street, a call's is the increment.
        contributed = [0, 0]
        by_street = defaultdict(lambda: [0, 0])
        for a in actions:
            seat = int(a["seat"])
            if seat not in (0, 1):
                continue
            amount = int(a.get("amount") or 0)
            phase = a.get("phase") or "preflop"
            if a.get("action") in ("raise", "bet", "all_in"):
                by_street[phase][seat] = amount
            elif a.get("action") in ("call", "post_small_blind", "post_big_blind"):
                by_street[phase][seat] += amount
        for levels in by_street.values():
            contributed[0] += levels[0]
            contributed[1] += levels[1]
        pot = sum(contributed)
        winners = hand.get("winner_seats") or ([hand["winner_seat"]] if hand.get("winner_seat") is not None else [])
        for seat in (0, 1):
            stacks[seat] -= contributed[seat]
        if winners:
            share = pot / len(winners)
            for seat in winners:
                if int(seat) in (0, 1):
                    stacks[int(seat)] += share


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--names", nargs="*", help="bots to price (default: every name in the match index)")
    parser.add_argument("--max-bb", type=float, default=12.0)
    parser.add_argument("--shove-fraction", type=float, default=0.8)
    parser.add_argument("--table", default=os.path.join(ROOT, "results", "cfr", "chance", "nolimit_12bb_preflop_allin.npy"))
    parser.add_argument("--rung", default=os.path.join(ROOT, "results", "cfr", "ladder169l", "nolimit_12bb.pkl"))
    parser.add_argument("--out")
    args = parser.parse_args()

    from scripts.chipzen_scout import index_matches
    from scripts import chipzen_run as run

    edge = np.load(args.table)
    labels = hand_labels(args.rung)
    combos = combos_of(labels)
    index = {label: i for i, label in enumerate(labels)}
    by_name = index_matches(run._config())["by_name"]
    names = args.names or sorted(by_name)

    rows = defaultdict(lambda: {"shove_spots": 0, "shoved": 0, "shove_cost": 0.0,
                                "call_spots": 0, "called": 0, "call_cost": 0.0, "depths": []})
    solutions = {}
    for name in names:
        for match in by_name.get(name, []):
            path = os.path.join(HANDS, f"{match['id']}.json")
            if not os.path.exists(path):
                continue
            seat = match.get("seat")
            if seat is None:
                continue
            with open(path) as handle:
                hands = json.load(handle)
            for hand, stacks, big_blind, sb_seat in walk_match(hands):
                depth = min(stacks) / big_blind
                if depth > args.max_bb:
                    continue
                hole = (hand.get("hole_cards") or {}).get(str(seat))
                if not hole or len(hole) != 2:
                    continue
                klass = index.get(hand_class(hole))
                if klass is None:
                    continue
                key = round(depth * 2) / 2
                if key not in solutions:
                    solutions[key] = solve(edge, combos, max(key, 1.0))
                _, _, _, value_shove, value_call = solutions[key]
                row = rows[name]
                row["depths"].append(depth)
                shoved_by = None
                for a in hand.get("actions") or []:
                    if str(a.get("action", "")).startswith("post"):
                        continue
                    acting = int(a["seat"])
                    amount = int(a.get("amount") or 0)
                    is_shove = a.get("action") == "raise" and amount >= args.shove_fraction * stacks[acting]
                    if shoved_by is None:
                        if acting == seat:
                            if acting != sb_seat and a.get("action") == "check":
                                break
                            row["shove_spots"] += 1
                            row["shoved"] += int(is_shove)
                            row["shove_cost"] += max(value_shove[klass], -0.5) - (value_shove[klass] if is_shove else -0.5)
                            if not is_shove:
                                break
                        if is_shove:
                            shoved_by = acting
                        elif a.get("action") == "fold":
                            break
                    else:
                        if acting == seat:
                            row["call_spots"] += 1
                            called = a.get("action") == "call"
                            row["called"] += int(called)
                            row["call_cost"] += max(value_call[klass], -1.0) - (value_call[klass] if called else -1.0)
                        break

    lines = ["| bot | hands ≤ %gbb | median depth | shove spots | shoves | cost (bb) | call spots | calls | cost (bb) | total bb/decision |" % args.max_bb,
             "|---|---|---|---|---|---|---|---|---|---|"]
    for name in sorted(rows, key=lambda n: -(rows[n]["shove_cost"] + rows[n]["call_cost"]) / max(rows[n]["shove_spots"] + rows[n]["call_spots"], 1)):
        r = rows[name]
        spots = r["shove_spots"] + r["call_spots"]
        if spots < 50:
            continue
        lines.append(
            f"| {name} | {len(r['depths']):,} | {np.median(r['depths']):.1f} | {r['shove_spots']:,} | "
            f"{100 * r['shoved'] / max(r['shove_spots'], 1):.0f}% | {r['shove_cost'] / max(r['shove_spots'], 1):.3f} | "
            f"{r['call_spots']:,} | {100 * r['called'] / max(r['call_spots'], 1):.0f}% | "
            f"{r['call_cost'] / max(r['call_spots'], 1):.3f} | "
            f"**{(r['shove_cost'] + r['call_cost']) / max(spots, 1):.3f}** |")
    table = "\n".join(lines)
    print(table)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(f"# Short-stack errors of the bots we play, at or under {args.max_bb:g} big blinds\n\n"
                         "From the scout's cached hands, stacks reconstructed by walking each match.\n\n"
                         + table + "\n")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
