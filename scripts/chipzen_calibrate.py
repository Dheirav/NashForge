"""
Measure the field archetypes with the scout's own yardstick.

    venv/bin/python scripts/chipzen_calibrate.py                 # all four, 300 matches each
    venv/bin/python scripts/chipzen_calibrate.py --kinds station --matches 500

The archetypes (chipzen/archetypes.py) are shaped like the scout table; this
plays each against v5i in arena matches, writes every hand in the platform's
own record format, and runs the scout's `profile` and `summarise` over them,
so an archetype's VPIP, PFR, fold-to-bet and call share are computed by the
same code that computed Fold-ver-3's. The table it prints puts each archetype
beside its target bot. Tuning is by hand: change a threshold, rerun, compare.
"""
import argparse
import os
import sys


import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstraction.equity import FULL_DECK  # noqa: E402
from chipzen.archetypes import ARCHETYPES, build_archetype  # noqa: E402
from scripts.chipzen_duel import ARENA_STACK, Dealer, arena_big_blind, build  # noqa: E402
from scripts.chipzen_scout import profile, summarise  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TARGETS = {"station": "Fold-ver-3", "nit": "Shadow", "maniac": "v003", "foldraise": "Blueprint", "hoops": "hoops"}
#: The corpus shapes have no scout file; their target is the published row
#: (private repo, corpus_profiles.md), as VPIP/PFR/3bet/fold-to-3bet/fold-to-bet/
#: call share/showdown/won-SD/BB-folds-to-open, in percent.
CORPUS_TARGETS = {
    "sticky":      dict(vpip=71, pfr=9, three_bet=8, fold_to_three_bet=0, fold_to_bet=0,
                        call_share_of_answers=97, showdown_rate=96, showdown_win=48, bb_fold_to_open=0),
    "nofold3bet":  dict(vpip=74, pfr=47, three_bet=8, fold_to_three_bet=0, fold_to_bet=18,
                        call_share_of_answers=88, showdown_rate=66, showdown_win=47, bb_fold_to_open=2),
    "folder":      dict(vpip=0, pfr=0, three_bet=0, fold_to_three_bet=0, fold_to_bet=100,
                        call_share_of_answers=60, showdown_rate=8, showdown_win=67, bb_fold_to_open=100),
    "wildpassive": dict(vpip=82, pfr=61, three_bet=46, fold_to_three_bet=0, fold_to_bet=0,
                        call_share_of_answers=81, showdown_rate=95, showdown_win=46, bb_fold_to_open=0),
}
COLUMNS = ("vpip", "pfr", "three_bet", "fold_to_three_bet", "fold_to_bet", "call_share_of_answers",
           "showdown_rate", "showdown_win", "bb_fold_to_open")


def record(dealer: Dealer, net):
    """One hand in the platform's shape, the archetype in `seats[1]`'s seat."""
    board = "".join(str(FULL_DECK[c]) for c in dealer.board_cards[:5])
    winners = [s for s in (0, 1) if net[s] > 0]
    return {"hand_number": dealer.hand_number, "board": board, "pot_size": float(dealer.pot),
            "winner_seat": winners[0] if winners else None, "winner_seats": winners,
            "hole_cards": {str(s): [str(FULL_DECK[c]) for c in dealer.hole[s]] for s in (0, 1)},
            "actions": [dict(a) for a in dealer.history]}


def play_recorded(players, rng, matches):
    """Arena matches as `chipzen_duel.play_match` plays them, keeping every hand; the archetype is players[1]."""
    hands_by_match, match_rows = {}, []
    deck = np.arange(52)
    for m in range(matches):
        stacks = [ARENA_STACK, ARENA_STACK]
        hands = []
        hand = 0
        while min(stacks) > 0 and hand < 400:
            hand += 1
            bb = arena_big_blind(hand)
            rng.shuffle(deck)
            cards = [int(c) for c in deck[:9]]
            if hand % 2 == 1:
                d = Dealer(players, cards, stacks, bb // 2, bb, hand, ("a", "b"))
                net = d.play()
                rec = record(d, net)
            else:
                d = Dealer([players[1], players[0]], cards, [stacks[1], stacks[0]], bb // 2, bb, hand, ("b", "a"))
                swapped = d.play()
                net = [swapped[1], swapped[0]]
                rec = record(d, swapped)
                # The dealer seated the archetype at 0 this hand; relabel so it is seat 1 throughout.
                for a in rec["actions"]:
                    a["seat"] = 1 - a["seat"]
                rec["hole_cards"] = {"0": rec["hole_cards"]["1"], "1": rec["hole_cards"]["0"]}
                rec["winner_seats"] = [1 - s for s in rec["winner_seats"]]
                rec["winner_seat"] = rec["winner_seats"][0] if rec["winner_seats"] else None
            stacks = [stacks[0] + net[0], stacks[1] + net[1]]
            hands.append(rec)
        mid = f"cal-{m}"
        hands_by_match[mid] = hands
        match_rows.append({"id": mid, "vs": ["v5i"], "seat": 1, "rated": True})
    return match_rows, hands_by_match


def target_summary(name):
    import json
    path = os.path.join(ROOT, "results", "chipzen", "scout", f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path) as handle:
        return json.load(handle).get("summary")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kinds", nargs="+", default=list(ARCHETYPES))
    parser.add_argument("--matches", type=int, default=300)
    parser.add_argument("--ladder", default="results/cfr/ladder169l_v5i")
    parser.add_argument("--seed", type=int, default=5)
    args = parser.parse_args()

    opponent = build(args.ladder, "--deep-primary --stack-cap", "v5i", np.random.default_rng(args.seed), None)
    print("| shape | " + " | ".join(COLUMNS) + " |")
    print("|---|" + "---|" * len(COLUMNS))
    for kind in args.kinds:
        arch = build_archetype(kind, np.random.default_rng(args.seed + 1))
        rows, hands = play_recorded([opponent, arch], np.random.default_rng(args.seed + 2), args.matches)
        row = profile(kind, rows, hands)
        stats = {"rating": 0, "matches_played": 0, "wins": 0, "losses": 0, "bb_per_100": 0.0,
                 "bb_hands_counted": 0, "llm_author_model": None, "bot_kind": "archetype"}
        summary = summarise(row, stats)
        target = target_summary(TARGETS[kind]) if kind in TARGETS else None
        corpus = CORPUS_TARGETS.get(kind)
        fmt = lambda s, k: (f"{100 * s[k]:.0f}%" if isinstance(s.get(k), (int, float)) else "?")
        print(f"| {kind} ({row['hands']} hands) | " + " | ".join(fmt(summary, k) for k in COLUMNS) + " |")
        if target:
            print(f"| target {TARGETS[kind]} | " + " | ".join(fmt(target, k) for k in COLUMNS) + " |")
        elif corpus:
            print(f"| target corpus | " + " | ".join(f"{corpus.get(k, 0)}%" for k in COLUMNS) + " |")


if __name__ == "__main__":
    main()
