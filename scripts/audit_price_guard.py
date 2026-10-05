"""
Where the misread-price guard (`ArenaPlayer.price_misread`) would have fired, and what it would have been worth.

    venv/bin/python scripts/audit_price_guard.py
    venv/bin/python scripts/audit_price_guard.py --matches-dir ~/Code/PokerBot/results/chipzen/matches --price 0.25

Read-only over the per-match JSONL. Each logged fold is put through the guard's conditions as far as the record
allows: the strategy folded (no rule answered and no read changed it), there was a bet to call, the history it
answered was misread (a `collapsed:` re-read, or a history ending in all-in while the bettor kept chips beyond what
we can call), the answer was not the river solve's, the real price was at or under the threshold and the hand beat a
random one often enough. Neither stack is in the decision row, so both are rebuilt from the hand's starting stacks
and the action history up to our action.

The value of a call is estimated only when the arena showed their cards, which it does at a showdown and, in these
logs, on hands we folded too. It is our exact equity against their hand over the cards still to come, times the pot
after the call, less the call. That treats the call as the last chip in, which it is not when the bettor kept chips:
a call can meet another bet on a later street, and this estimate ignores whatever happens then, in both directions.
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chipzen.player import ArenaPlayer  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MATCHES = os.path.join(ROOT, "results", "chipzen", "matches")
_RANKS = "23456789TJQKA"
_SUITS = "hdcs"
#: Reads that may leave a fold in place without having chosen it (see the guard's `adjusted` test in decide()).
UNTOUCHED = (None, "short-stack solution")


def card_index(card):
    """'Kh' to the native deck index, suit * 13 + rank, the same as engine.cards.Card.index."""
    return _SUITS.index(card[1]) * 13 + _RANKS.index(card[0])


def contributions(history):
    """Chips each seat has put in, all streets, as chipzen.bridge._contributions counts them."""
    from chipzen.bridge import _contributions
    return _contributions(history)


def matches(path):
    """(version, seat, hands) per match in one file; hands are (start, decisions, result) in log order."""
    out, current, hand = [], None, None
    for line in open(path):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        frame = row.get("frame")
        if frame == "match_start":
            current = {"version": (row.get("version") or {}).get("label"), "seat": row.get("seat"),
                       "match": row.get("match_id") or os.path.basename(path)[:8], "hands": []}
            out.append(current)
        elif current is None:
            continue
        elif frame == "round_start":
            hand = {"start": row.get("state") or {}, "decisions": [], "result": None}
            current["hands"].append(hand)
        elif frame == "decision" and hand is not None:
            hand["decisions"].append(row)
        elif frame == "round_result" and hand is not None:
            hand["result"] = row.get("result") or {}
            hand = None
    return out


def spots(match, price_cap, equity_floor, checks):
    """Every decision of the match the guard would have called, with what the record says about it."""
    import pokerbot_native as native
    seat = match["seat"]
    for hand in match["hands"]:
        result = hand["result"]
        if not result or seat is None:
            continue
        stacks = hand["start"].get("stacks")
        history = result.get("action_history") or []
        # Our k-th decision is our k-th voluntary action in the arena's history.
        ours = [i for i, a in enumerate(history) if a.get("seat") == seat and not str(a.get("action", "")).startswith("post")]
        for k, d in enumerate(hand["decisions"]):
            to_call = int(d.get("to_call") or 0)
            read = d.get("adjusted")
            if d.get("choice") != 0 or to_call <= 0 or d.get("fallback") \
                    or (read not in UNTOUCHED and not str(read).startswith("river shove")):
                continue
            checks["strategy folds facing a bet"] += 1
            if k >= len(ours) or not stacks or history[ours[k]].get("phase") != d.get("phase"):
                checks["unmatched to the action history"] += 1
                continue
            before = history[:ours[k]]
            put = contributions(before)
            opponent_stack = int(stacks[1 - seat]) - put[1 - seat]
            mine = int(stacks[seat]) - put[seat]
            companion = d.get("companion")
            if companion and not str(companion).startswith("collapsed:"):
                # A companion answered on its own translation, which the record does not keep.
                checks["companion answered (history not logged)"] += 1
                continue
            river = d.get("river")
            if river and "error" not in river:
                # The river solve priced the arena's own pot; the guard leaves its folds alone.
                checks["river-solve folds"] += 1
                continue
            if not ArenaPlayer._misread(companion, d.get("history"), opponent_stack, to_call, mine):
                checks["all-in read that covers our stack (a real all-in)"] += int(
                    ArenaPlayer._misread(companion, d.get("history"), opponent_stack))
                continue
            checks["misread folds"] += 1
            called = min(to_call, mine) if mine > 0 else to_call
            pot = int(d.get("pot") or 0) - (to_call - called)
            price = called / float(pot + called)
            hole, board = d.get("hole") or [], d.get("board") or []
            equity_random = float(native.equity_vs_random([card_index(c) for c in hole],
                                                          [card_index(c) for c in board], 200, 17))
            if price > price_cap or equity_random < equity_floor:
                checks["misread folds outside the thresholds"] += 1
                continue
            shown = {s.get("seat"): s.get("hole_cards") for s in (result.get("showdown") or [])}
            theirs = shown.get(1 - seat)
            value = equity = None
            if theirs:
                edge = native.allin_edge([card_index(c) for c in hole], [card_index(c) for c in theirs],
                                         [card_index(c) for c in board], True)
                equity = (1.0 + float(edge)) / 2.0
                value = equity * (pot + called) - called
            yield {"match": match["match"][:8], "version": match["version"], "opponent": d.get("opponent"),
                   "hand": d.get("hand"), "phase": d.get("phase"), "hole": "".join(hole), "board": "".join(board),
                   "theirs": "".join(theirs) if theirs else None, "pot": pot, "call": called, "price": price,
                   "equity_random": equity_random, "equity": equity, "value": value,
                   "kind": "collapsed" if str(companion or "").startswith("collapsed:") else "all-in read, chips behind",
                   "opponent_stack": opponent_stack, "history": d.get("history"), "companion": companion}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--matches-dir", default=MATCHES)
    parser.add_argument("--price", type=float, default=ArenaPlayer.MISREAD_PRICE)
    parser.add_argument("--equity", type=float, default=ArenaPlayer.MISREAD_EQUITY)
    parser.add_argument("--json", help="write the firings here as well")
    args = parser.parse_args()

    class Count(dict):
        def __missing__(self, key):
            return 0
    checks = Count()
    fired = []
    files = sorted(glob.glob(os.path.join(os.path.expanduser(args.matches_dir), "*.jsonl")))
    for path in files:
        for match in matches(path):
            fired.extend(spots(match, args.price, args.equity, checks))

    print(f"{len(files)} match files, price at most {args.price:g}, equity against random at least {args.equity:g}")
    for key, value in checks.items():
        print(f"  {key}: {value}")
    known = [f for f in fired if f["value"] is not None]
    total = sum(f["value"] for f in known)
    print(f"firings: {len(fired)}, with their cards shown: {len(known)}, "
          f"estimated chips from calling instead: {total:+,.0f}"
          + (f" ({total / len(known):+,.0f} a firing)" if known else ""))
    print("  (the call is scored as the last chip in; later streets' betting is ignored)")
    print()
    header = f"{'match':8} {'hand':>4} {'opponent':14} {'phase':6} {'ours':5} {'board':11} {'theirs':6} " \
             f"{'pot':>7} {'call':>6} {'price':>5} {'eqR':>5} {'eq':>5} {'value':>8}  kind"
    print(header)
    for f in fired:
        print(f"{f['match']:8} {f['hand']:>4} {str(f['opponent'])[:14]:14} {f['phase']:6} {f['hole']:5} "
              f"{f['board']:11} {f['theirs'] or '-':6} {f['pot']:>7,} {f['call']:>6,} {f['price']:5.2f} "
              f"{f['equity_random']:5.2f} {('%.2f' % f['equity']) if f['equity'] is not None else '-':>5} "
              f"{('%+8.0f' % f['value']) if f['value'] is not None else '-':>8}  {f['kind']}")
    if args.json:
        with open(args.json, "w") as handle:
            json.dump(fired, handle, indent=1)


if __name__ == "__main__":
    main()
