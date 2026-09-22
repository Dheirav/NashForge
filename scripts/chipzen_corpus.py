"""
Profile the eleven bots of Chipzen's published corpus, in the scout's terms.

    venv/bin/python scripts/chipzen_corpus.py --dir ~/pokerbot-scratch/kaggle

247,946 heads-up hands between eleven LLM-written bots, with both players'
hole cards, published by the platform on 23 August 2026 (kaggle.com,
`daveatchipzen/llm-poker-bots-248k-holdem-hands`). It is the same population
our archetypes imitate and about sixty times the hands our scout can fetch
per bot, so it is the right place to ask what the field's shapes actually
are rather than tuning thresholds against five summary rows.

This computes, per agent, the statistics `chipzen_calibrate.py` compares an
archetype against (VPIP, PFR, three-bet and fold-to-three-bet, fold to a bet,
call share, showdown rate and what is won there, the blind's fold to an open),
plus what an archetype needs and the scout cannot see: the equity of the
hands each bot puts chips in with, and the size of its raises against the pot.

Caveat the publishers make and it is worth repeating: the matches are
elimination format with escalating blinds, so late hands are short-stacked
and an agent's average match length is itself a signal. Rates here pool over
match phases; `--max-bb` restricts to hands at or under a blind level when
that matters.
"""
import argparse
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.cards import Card  # noqa: E402

RANKS = "23456789TJQKA"
SUITS = "cdhs"


def card_index(token: str) -> int:
    return SUITS.index(token[1]) * 13 + RANKS.index(token[0])


def equity_of(hole: str, board: str, samples: int, seed: int) -> float:
    import pokerbot_native as native
    cards = [card_index(t) for t in hole.split()]
    table = [card_index(t) for t in (board or "").split()]
    return float(native.equity_vs_random(cards, table[:5], samples, seed))


def profile(actions: pd.DataFrame, hands: pd.DataFrame, samples: int) -> dict:
    """Per agent, the counts the scout keeps, walking each hand's actions in order."""
    rows = defaultdict(lambda: defaultdict(float))
    hands_by_key = {(h["match_id"], h["hand_number"]): h for h in hands.to_dict("records")}
    for (match_id, hand_number), group in actions.groupby(["match_id", "hand_number"], sort=False):
        hand = hands_by_key.get((match_id, hand_number))
        if hand is None:
            continue
        phase = None
        raises = 0
        entered = {0: False, 1: False}
        raised_pre = {0: False, 1: False}
        faced_raise_pre = {0: 0, 1: 0}
        folded_to_raise_pre = {0: 0, 1: 0}
        previous = None
        pot = 0.0
        for a in group.sort_values("action_idx").itertuples():
            agent = a.agent
            row = rows[agent]
            if a.action_type.startswith("post"):
                pot = a.pot_after
                continue
            if a.phase != phase:
                phase, raises, previous = a.phase, 0, None
            seat = int(a.seat)
            if a.action_type == "raise":
                row["raises"] += 1
                # Size against the pot before the raise, as the scout bins it.
                to_call = max(pot - 2 * min(pot / 2, pot), 0)
                row[f"size_{_size_bin(a.amount, pot)}"] += 1
            if previous == "raise":
                row["bets_faced"] += 1
                row["folds" if a.action_type == "fold" else
                    ("raise_answers" if a.action_type == "raise" else "calls")] += 1
            if phase == "preflop":
                if raises >= 1 and previous == "raise":
                    faced_raise_pre[seat] += 1
                    if raises >= 2 or raised_pre[seat]:
                        row["three_bets_faced"] += 1
                        row["fold_to_three_bet"] += int(a.action_type == "fold")
                    else:
                        row["opens_faced"] += 1
                        row["bb_fold_to_open"] += int(a.action_type == "fold")
                        row["three_bet_chances"] += 1
                        row["three_bet"] += int(a.action_type == "raise")
                if a.action_type in ("call", "raise"):
                    entered[seat] = True
                if a.action_type == "raise":
                    raised_pre[seat] = True
            row["decisions"] += 1
            if a.action_type == "raise":
                raises += 1
            previous = a.action_type
            pot = a.pot_after
        # Per-hand counters, from the hand row.
        for seat in (0, 1):
            agent = hand[f"agent_seat{seat}"]
            row = rows[agent]
            row["hands"] += 1
            row["vpip"] += int(entered[seat])
            row["pfr"] += int(raised_pre[seat])
            row["showdowns"] += int(bool(hand["showdown"]))
            if hand["showdown"]:
                row["showdowns_won"] += int(hand["winner"] == agent)
            if entered[seat] and samples:
                row["entered_equity"] += equity_of(hand[f"hole_seat{seat}"], "", samples,
                                                   abs(hash((match_id, hand_number, seat))) % (2 ** 62))
                row["entered_equity_n"] += 1
    return rows


def _size_bin(amount: float, pot: float) -> str:
    if pot <= 0:
        return "1-2"
    f = amount / pot
    return "<half" if f < 0.5 else ("half-1" if f < 1 else ("1-2" if f < 2 else "2+"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=os.path.expanduser("~/pokerbot-scratch/kaggle"))
    parser.add_argument("--matches", type=int, default=0, help="limit to this many matches (0: all)")
    parser.add_argument("--max-bb", type=int, default=0, help="only hands at or under this big blind (0: all)")
    parser.add_argument("--equity-samples", type=int, default=0,
                        help="Monte Carlo samples for the equity of hands entered with (0: skip, it is the slow part)")
    parser.add_argument("--out", help="write the table here as markdown")
    args = parser.parse_args()

    hands = pd.read_parquet(os.path.join(args.dir, "hands.parquet"))
    actions = pd.read_parquet(os.path.join(args.dir, "actions.parquet"))
    if args.max_bb:
        hands = hands[hands["big_blind"] <= args.max_bb]
    if args.matches:
        keep = set(hands["match_id"].unique()[: args.matches])
        hands = hands[hands["match_id"].isin(keep)]
    actions = actions.merge(hands[["match_id", "hand_number"]], on=["match_id", "hand_number"], how="inner")
    print(f"{len(hands):,} hands, {len(actions):,} actions, {hands['match_id'].nunique():,} matches", flush=True)

    rows = profile(actions, hands, args.equity_samples)
    columns = ["hands", "VPIP", "PFR", "3bet", "fold to 3bet", "fold to bet", "call share",
               "showdown", "won SD", "BB folds to open", "raise sizes", "entered eq"]
    lines = ["| agent | " + " | ".join(columns) + " |", "|---|" + "---|" * len(columns)]
    for agent in sorted(rows):
        r = rows[agent]
        answers = max(r["calls"] + r["raise_answers"], 1)
        sizes = {b: r[f"size_{b}"] for b in ("<half", "half-1", "1-2", "2+")}
        total_sizes = max(sum(sizes.values()), 1)
        cells = [f"{int(r['hands']):,}",
                 f"{r['vpip'] / max(r['hands'], 1):.0%}", f"{r['pfr'] / max(r['hands'], 1):.0%}",
                 f"{r['three_bet'] / max(r['three_bet_chances'], 1):.0%}",
                 f"{r['fold_to_three_bet'] / max(r['three_bets_faced'], 1):.0%}",
                 f"{r['folds'] / max(r['bets_faced'], 1):.0%}",
                 f"{r['calls'] / answers:.0%}",
                 f"{r['showdowns'] / max(r['hands'], 1):.0%}",
                 f"{r['showdowns_won'] / max(r['showdowns'], 1):.0%}",
                 f"{r['bb_fold_to_open'] / max(r['opens_faced'], 1):.0%}",
                 " ".join(f"{b}:{v / total_sizes:.0%}" for b, v in sizes.items() if v),
                 f"{r['entered_equity'] / r['entered_equity_n']:.3f}" if r["entered_equity_n"] else "—"]
        lines.append(f"| {agent} | " + " | ".join(cells) + " |")
    table = "\n".join(lines)
    print(table)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(f"# The eleven bots of the published corpus, in the scout's terms\n\n"
                         f"{len(hands):,} hands from `{args.dir}`"
                         + (f", big blind at most {args.max_bb}" if args.max_bb else "") + ".\n\n" + table + "\n")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
