"""
Every logged decision `--capped-price` would have answered differently, and what it would have been worth.

    venv/bin/python scripts/audit_capped_price.py --matches-dir ~/Code/PokerBot/results/chipzen/matches
    venv/bin/python scripts/audit_capped_price.py --matches-dir ... --json capped.json

Read-only over the per-match JSONL. The flag changes two things, and both only where the arena's bet covers our
stack (to call at least what we have), because everywhere else the capped call and pot are the arena's own:

- the fallback rule (`fallback_choice`) on a decision the rule made, where the logged answer was a fold and no read
  changed it. The rule is re-run on the hand's strength class, read from the abstraction of the rung that answered
  (the side file of its flat pair; nothing else of the strategy is loaded), at both prices, and the logged fold
  must come back from the uncapped run or the row is counted as unreproduced;
- "called for pot odds", on any logged fold: with the flag a call that puts us all in fires it as their all-in does,
  at the capped call against the capped pot. That needs no class, as the rule does not read one.

The capped price only ever lowers the price, and both rules are monotone in it, so the flag can turn a fold into a
call and never the reverse. A match logged without a version frame (season 6's first week) does not say which rung
answered; its rule folds are kept when the price alone decides (a call at a sixth of the pot or less calls with
any class) and listed as unknown otherwise.

The value of a changed call is exact when their cards were shown, which in these logs they are at a showdown and on
our folds: the call puts our last chip in and their uncalled excess comes back, so nothing is bet after it, and our
equity against their hand over the cards to come (pokerbot_native.allin_edge, as chipzen_decompose.py --allin-adjust
scores an all-in) times the pot after the call, less the call, is what calling was worth against folding.

The flag's second half (5 October, later the same day) adds the short-stack table and the reads that weigh a price:

- the short-stack table (`ShortStackRanges.calls`, logged as `short-stack solution`): the table is re-run on the
  logged hand, depth and history at both prices, the logged answer must come back uncapped, and a row is changed
  when the capped price answers differently. The table is monotone in the price as well, so only a fold can move;
- "their re-raise is value": its price is recomputed on each logged firing. It fires only when the strategy wanted
  a raise, and the arena offers no raise once the bet covers our stack, so the logs should hold no such firing;
- "re-raise defended" and "river bluff caught" sit behind --reraise-defence and --aggro-reads, which only the duel
  takes, so no arena match played them. Their eligible spots (the read's own conditions, a logged fold facing a
  bet that covers our stack) are counted, since the opponent's floor at the time is not logged and the value
  cannot be scored;
- "big bet believed", "small bet called" and "shove call declined" read their bet's size as a tell and keep the
  full bet under the flag. Their firings facing a bet that covers our stack are counted to show what is left alone.
"""
import argparse
import glob
import json
import os
import pickle
import sys
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstraction.betting import CHECK_CALL, FOLD  # noqa: E402
from chipzen.bridge import _contributions, legal_mask, parse_cards  # noqa: E402
from chipzen.player import ArenaPlayer, capped_call, fallback_choice, strength_class  # noqa: E402
from chipzen.pushfold import ShortStackRanges  # noqa: E402

#: The reads that take their bet's size as a tell; the flag leaves them on the full bet.
SIZE_READS = ("big bet believed", "small bet called", "shove call declined")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MATCHES = os.path.join(ROOT, "results", "chipzen", "matches")
_RANKS = "23456789TJQKA"
_SUITS = "hdcs"


def card_index(card):
    """'Kh' to the native deck index, suit * 13 + rank, the same as engine.cards.Card.index."""
    return _SUITS.index(card[1]) * 13 + _RANKS.index(card[0])


def matches(path):
    """(version, seat, hands) per match in one file; the reader audit_price_guard.py uses."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from audit_price_guard import matches as read
    return read(path)


def full_version(path):
    """The match_start version frames of a file, in order (audit_price_guard keeps only the label)."""
    out = []
    for line in open(path):
        if '"match_start"' not in line:
            continue
        try:
            out.append(json.loads(line).get("version") or {})
        except json.JSONDecodeError:
            out.append({})
    return out


class Rungs:
    """The abstraction of each rung by (ladder directory, depth label), from the flat pair's side file only."""

    def __init__(self, base):
        self.base = base
        self.cache = {}

    def get(self, version, label):
        ladder_dir, names = version.get("ladder_dir"), version.get("ladder") or []
        if not ladder_dir or not names:
            return None
        directory = os.path.normpath(os.path.join(self.base, ladder_dir))
        if directory not in self.cache:
            found = {}
            for name in names:
                side = os.path.join(directory, name[:-len(".pkl")] + ".flat.pkl")
                if not os.path.exists(side):
                    continue        # a full pickle is gigabytes resident; the row stays unknown instead
                with open(side, "rb") as handle:
                    saved = pickle.load(handle)
                args = saved.get("args") or {}
                args = args if isinstance(args, dict) else vars(args)
                depth = float(args.get("stack", 200)) / float(args.get("big_blind", 2))
                found[f"{depth:g}bb"] = saved["abstraction"]
            self.cache[directory] = found
        return self.cache[directory].get(label)


def spots(path, rungs, checks, table, ranges):
    import pokerbot_native as native
    versions = full_version(path)
    for number, match in enumerate(matches(path)):
        version = versions[number] if number < len(versions) else {}
        seat = match["seat"]
        for hand in match["hands"]:
            result, stacks = hand["result"], hand["start"].get("stacks")
            if not result or seat is None or not stacks:
                continue
            history = result.get("action_history") or []
            ours = [i for i, a in enumerate(history)
                    if a.get("seat") == seat and not str(a.get("action", "")).startswith("post")]
            shown = {s.get("seat"): s.get("hole_cards") for s in (result.get("showdown") or [])}
            theirs = shown.get(1 - seat)
            for k, d in enumerate(hand["decisions"]):
                if k >= len(ours) or history[ours[k]].get("phase") != d.get("phase"):
                    checks["unmatched to the action history"] += 1
                    continue
                put = _contributions(history[:ours[k]])
                mine = int(stacks[seat]) - put[seat]
                to_call, pot = int(d.get("to_call") or 0), int(d.get("pot") or 0)
                if to_call <= 0 or not 0 < mine <= to_call:
                    continue
                checks["facing a bet that covers our stack"] += 1
                read, choice = d.get("adjusted"), d.get("choice")
                pot_c, call = capped_call(pot, to_call, mine)
                hole, board = d.get("hole") or [], d.get("board") or []
                bb = float(d.get("effective_bb") or 0)
                why, cls, top = None, None, None
                if read in SIZE_READS:
                    checks[f"left on the full bet: {read}"] += 1
                if read == "short-stack solution":
                    raised = any(a.get("seat") == seat and a.get("action") == "raise"
                                 and a.get("phase") == "preflop" for a in history[:ours[k]])
                    cards = parse_cards(hole)
                    full = ranges.calls(cards, bb, to_call, pot, reraise=raised) if ranges else None
                    capped = ranges.calls(cards, bb, call, pot_c, reraise=raised) if ranges else None
                    table.append({"hole": "".join(hole), "price": to_call / float(pot + to_call),
                                  "capped": call / float(pot_c + call), "choice": choice, "effective_bb": bb})
                    if full is None or (CHECK_CALL if full else FOLD) != choice:
                        checks["table answers not reproduced uncapped"] += 1
                        continue
                    if capped and not full:
                        why = "short-stack table"
                elif read == "their re-raise is value":
                    checks["their re-raise is value, facing a bet that covers our stack"] += 1
                    if choice == FOLD and call / float(pot_c + call) <= ArenaPlayer.VALUE_RERAISE_PRICE:
                        why = "their re-raise is value"
                if choice != FOLD:
                    continue
                if why is None and read is None:
                    pre = [a for a in history[:ours[k]] if a.get("phase") == "preflop"
                           and not str(a.get("action", "")).startswith("post")]
                    if not board and len(pre) == 2 and pre[0].get("seat") == seat and pre[0].get("action") == "raise" \
                            and pre[1].get("seat") != seat and pre[1].get("action") == "raise":
                        checks["re-raise defended: eligible folds (flag duel-only, floor not logged)"] += 1
                    if len(board) == 5 and bb >= ArenaPlayer.SHOVE_RULE_MIN_BB:
                        checks["river bluff caught: eligible folds (flag duel-only, floor not logged)"] += 1
                checks["folds among them"] += 1
                if why is None and d.get("fallback") and read is None:
                    checks["rule folds"] += 1
                    abstraction = rungs.get(version, d.get("solver"))
                    mask = legal_mask(SimpleNamespace(to_call=to_call, raises_this_street=0, history=""),
                                      ["fold", "call"], tree=False)
                    checks["rule folds, rung known (class read)" if abstraction is not None
                           else "rule folds, rung unknown"] += 1
                    if abstraction is not None:
                        cls = strength_class(abstraction, parse_cards(hole), parse_cards(board))
                        top = int(getattr(abstraction, "postflop_buckets", 6)) - 1
                        if fallback_choice(cls, top, mask, pot, to_call) != FOLD:
                            checks["rule folds not reproduced uncapped"] += 1
                            continue
                        if fallback_choice(cls, top, mask, pot, to_call, stack=mine) == CHECK_CALL:
                            why = "fallback rule"
                    else:
                        # Any class below the top calls at a sixth of the pot or less once the bet is under it.
                        verdicts = {fallback_choice(c, 5, mask, pot, to_call, stack=mine) for c in range(5)}
                        if verdicts == {CHECK_CALL}:
                            why = "fallback rule (any class)"
                        elif CHECK_CALL in verdicts:
                            checks["rule folds, rung unknown, class decides"] += 1
                if why is None and call * ArenaPlayer.POT_ODDS_FLOOR <= pot_c - call:
                    # The rule's own test at the capped numbers; the logged fold was not its answer, as the call
                    # did not leave them all in or the uncapped call was too big.
                    why = "called for pot odds"
                if why is None:
                    continue
                value = equity = None
                if theirs:
                    edge = native.allin_edge([card_index(c) for c in hole], [card_index(c) for c in theirs],
                                             [card_index(c) for c in board], True)
                    equity = (1.0 + float(edge)) / 2.0
                    value = equity * (pot_c + call) - call
                yield {"match": match["match"][:8], "version": match["version"], "opponent": d.get("opponent"),
                       "hand": d.get("hand"), "phase": d.get("phase"), "hole": "".join(hole),
                       "board": "".join(board), "theirs": "".join(theirs) if theirs else None,
                       "effective_bb": d.get("effective_bb"), "solver": d.get("solver"), "class": cls, "top": top,
                       "pot": pot, "to_call": to_call, "stack": mine, "call": call, "capped_pot": pot_c,
                       "nominal_price": to_call / float(pot), "price": call / float(pot_c + call),
                       "equity": equity, "value": value, "why": why, "read": read}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--matches-dir", default=MATCHES)
    parser.add_argument("--ladder-base", default=None,
                        help="the tree the logged ladder_dir paths are relative to (default: the matches' repo)")
    parser.add_argument("--json", help="write the changed decisions here as well")
    args = parser.parse_args()
    directory = os.path.expanduser(args.matches_dir)
    base = args.ladder_base or os.path.abspath(os.path.join(directory, "..", "..", ".."))

    class Count(dict):
        def __missing__(self, key):
            return 0
    checks, table, changed = Count(), [], []
    rungs = Rungs(base)
    ranges = ShortStackRanges.load()
    if ranges is None:
        print("no push-fold table (results/cfr/chance/push_fold_ranges.npz): its answers are not re-run")
    files = sorted(glob.glob(os.path.join(directory, "*.jsonl")))
    for path in files:
        changed.extend(spots(path, rungs, checks, table, ranges))

    print(f"{len(files)} match files; ladders read relative to {base}")
    for key, value in checks.items():
        print(f"  {key}: {value}")
    known = [c for c in changed if c["value"] is not None]
    total = sum(c["value"] for c in known)
    by = {}
    for c in changed:
        by.setdefault(c["why"], []).append(c)
    print(f"changed by --capped-price: {len(changed)} (fold to call), with their cards shown: {len(known)}, "
          f"estimated chips from calling: {total:+,.0f}" + (f" ({total / len(known):+,.0f} each)" if known else ""))
    for why, rows in sorted(by.items()):
        shown = [r["value"] for r in rows if r["value"] is not None]
        print(f"  {why}: {len(rows)}, shown {len(shown)}, {sum(shown):+,.0f}")
    print("  (exact: the call is our last chip, so nothing is bet after it)")
    print()
    header = f"{'match':8} {'hand':>4} {'opponent':14} {'phase':7} {'ours':5} {'board':11} {'theirs':6} " \
             f"{'bb':>5} {'cls':>5} {'to call':>7} {'call':>6} {'pot':>7} {'nom':>5} {'real':>5} {'eq':>5} " \
             f"{'value':>8}  why"
    print(header)
    for c in changed:
        cls = f"{c['class']}/{c['top']}" if c["class"] is not None else "-"
        print(f"{c['match']:8} {c['hand']:>4} {str(c['opponent'])[:14]:14} {c['phase']:7} {c['hole']:5} "
              f"{c['board']:11} {c['theirs'] or '-':6} {c['effective_bb'] or 0:5.1f} {cls:>5} {c['to_call']:>7,} "
              f"{c['call']:>6,} {c['capped_pot']:>7,} {c['nominal_price']:5.2f} {c['price']:5.2f} "
              f"{('%.2f' % c['equity']) if c['equity'] is not None else '-':>5} "
              f"{('%+8.0f' % c['value']) if c['value'] is not None else '-':>8}  {c['why']}")
    if table:
        lower = sum(1 for t in table if t["capped"] < t["price"])
        print(f"\nshort-stack table answers facing a bet that covers our stack: {len(table)}, "
              f"{sum(1 for t in table if t['choice'] == FOLD)} of them folds; {lower} priced lower capped, "
              f"{len(by.get('short-stack table', []))} answered differently")
    if args.json:
        with open(args.json, "w") as handle:
            json.dump(changed, handle, indent=1)


if __name__ == "__main__":
    main()
