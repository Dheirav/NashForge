"""
Where the off-tree preflop answer (`ArenaPlayer.offtree_preflop`) would have fired, and what it would have been worth.

    venv/bin/python scripts/audit_offtree_preflop.py
    venv/bin/python scripts/audit_offtree_preflop.py --ladder-dir ~/Code/PokerBot/results/cfr/ladder169l_v5xRR3 --json out.json

Read-only over the per-match JSONL. Two passes over every preflop decision that faced a bet while the bettor kept chips.

**As logged.** The decisions the bot that played folded to a raise read as all-in. The history it answered is the
record's `answered_history` where the record has one (from 5 Oct); before that it is the primary's `history`, or, when
a companion answered, its own translation rebuilt by `audit_price_guard.answered_history`.

**Replayed.** The same decisions put through `ArenaPlayer.decide` on one set (by default the main set, v5xRR3, as it
plays: deep primary, stack cap, purified), with the flag on and no profiles, so nothing but the strategy and this
rule acts. A firing is a fold the rule turned into a call. Only the first divergence in a hand is real, and this is it.

The value of a call is scored as `audit_price_guard.py` scores it: our exact equity against their shown hand, times the
pot after the call, less the call. **The call is not the last chip in.** About ninety blinds stay behind at 100bb, the
hand goes on to a flop played on the collapsed history, and that is ignored in both directions. The logged hands where
the bot called such a raise are scored the same way and against what they actually won, which is the one check on how
much that assumption is worth.
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np  # noqa: E402

from chipzen.player import ArenaPlayer  # noqa: E402
from scripts.audit_price_guard import UNTOUCHED, answered_history, card_index, contributions, matches  # noqa: E402
from scripts.chipzen_run import ladder_paths  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAIN = os.path.join(os.path.expanduser("~"), "Code", "PokerBot")
MATCHES = os.path.join(MAIN, "results", "chipzen", "matches")
LADDER = os.path.join(MAIN, "results", "cfr", "ladder169l_v5xRR3")
MARGINS = (0.0, 0.03, 0.05, 0.08, 0.10)


def situations(match):
    """(hand, decision, state, opponent stack, our stack) for every preflop decision facing a bet."""
    seat = match["seat"]
    for hand in match["hands"]:
        result = hand["result"]
        stacks = hand["start"].get("stacks")
        if not result or seat is None or not stacks:
            continue
        history = result.get("action_history") or []
        ours = [i for i, a in enumerate(history) if a.get("seat") == seat and not str(a.get("action", "")).startswith("post")]
        for k, d in enumerate(hand["decisions"]):
            if d.get("phase") != "preflop" or int(d.get("to_call") or 0) <= 0:
                continue
            if k >= len(ours) or history[ours[k]].get("phase") != "preflop":
                continue
            before = history[:ours[k]]
            put = contributions(before)
            theirs, mine = int(stacks[1 - seat]) - put[1 - seat], int(stacks[seat]) - put[seat]
            to_call = int(d.get("to_call") or 0)
            state = {"hand_number": d.get("hand"), "phase": "preflop", "board": [], "your_hole_cards": d.get("hole"),
                     "pot": int(d.get("pot") or 0), "to_call": to_call, "your_stack": mine, "opponent_stacks": [theirs],
                     "min_raise": min(mine, 2 * to_call), "max_raise": mine, "action_history": before}
            yield hand, d, state, theirs, mine


def value_of(hole, theirs, pot, call):
    """Equity against their hand times the pot after the call, less the call; see the module note."""
    import pokerbot_native as native
    edge = native.allin_edge([card_index(c) for c in hole], [card_index(c) for c in theirs], [], True)
    equity = (1.0 + float(edge)) / 2.0
    return equity, equity * (pot + call) - call


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--matches-dir", default=MATCHES)
    parser.add_argument("--ladder-dir", default=LADDER, help="the set the replay pass plays (default the main set)")
    parser.add_argument("--no-deep-primary", action="store_true")
    parser.add_argument("--purify", default="all")
    parser.add_argument("--json", help="write every evaluated spot here as well")
    args = parser.parse_args()

    _, ladder, companions = ladder_paths(os.path.expanduser(args.ladder_dir), not args.no_deep_primary)
    player = ArenaPlayer(ladder, np.random.default_rng(0), companions=companions, purify=args.purify, stack_cap=True)
    player.offtree_preflop = True

    files = sorted(glob.glob(os.path.join(os.path.expanduser(args.matches_dir), "*.jsonl")))
    logged, replayed, called_logged = [], [], []
    counts = {"preflop decisions facing a bet, bettor kept chips": 0}
    for path in files:
        for match in matches(path):
            seat = match["seat"]
            for hand, d, state, theirs, mine in situations(match):
                if theirs <= 0:
                    continue
                counts["preflop decisions facing a bet, bettor kept chips"] += 1
                result = hand["result"]
                shown = {s.get("seat"): s.get("hole_cards") for s in (result.get("showdown") or [])}.get(1 - seat)
                called = min(state["to_call"], mine) if mine > 0 else state["to_call"]
                pot = state["pot"] - (state["to_call"] - called)
                base = {"match": match["match"][:8], "version": match["version"], "opponent": d.get("opponent"),
                        "hand": d.get("hand"), "hole": "".join(d.get("hole") or []),
                        "theirs": "".join(shown) if shown else None, "pot": pot, "call": called,
                        "effective_bb": d.get("effective_bb"), "logged_history": d.get("history"),
                        "companion": d.get("companion")}

                valid = ["fold", "call"] + (["raise"] if mine > state["to_call"] else [])
                out = player.decide(state, valid, seat)
                record = out["record"]
                answered, source = answered_history(d, state["action_history"], mine, theirs, seat)
                untouched = d.get("adjusted") in UNTOUCHED and not d.get("fallback")
                if answered and str(answered).endswith("5") and untouched and d.get("choice") in (0, 1):
                    row = dict(base, answered=answered, source=source, replay_choice=record["choice"],
                               replay_adjusted=record["adjusted"], replay_offtree=record.get("offtree"))
                    if shown:
                        row["equity"], row["value"] = value_of(d["hole"], shown, pot, called)
                    if d.get("choice") == 0:
                        logged.append(row)
                    elif shown:
                        # Realised from this decision on: what the stack ended at against what it was here.
                        row["realised"] = int(result["stacks"][seat]) - mine
                        called_logged.append(row)

                if record.get("offtree") is not None:
                    row = dict(base, **record["offtree"], fired=record["adjusted"] == "priced an off-tree raise",
                               replay_history=record["history"], logged_choice=d.get("choice"))
                    if shown:
                        row["shown_equity"], row["value"] = value_of(d["hole"], shown, pot, called)
                    replayed.append(row)

    print(f"{len(files)} match files; replay set {os.path.basename(os.path.expanduser(args.ladder_dir))} "
          f"(purify {args.purify}, stack cap, deep primary {not args.no_deep_primary}); margin {player.OFFTREE_MARGIN:g}")
    for key, value in counts.items():
        print(f"  {key}: {value}")
    print()
    print(f"As logged: {len(logged)} folds to a preflop raise read as all-in with the bettor holding chips")
    for source in sorted({r['source'] for r in logged}):
        print(f"  answered on {source}: {sum(r['source'] == source for r in logged)}")
    rule = sum(r["replay_adjusted"] == "priced an off-tree raise" for r in logged)
    print(f"  the replay set there: {sum(r['replay_choice'] == 0 for r in logged) + rule} strategy folds, of which "
          f"the rule called {rule}; {sum(r['replay_choice'] == 1 for r in logged) - rule} strategy calls; "
          f"{sum(r['replay_choice'] not in (0, 1) for r in logged)} raises")
    known = [r for r in called_logged if r.get("value") is not None]
    if known:
        print(f"The logged calls of such a raise, cards shown: {len(known)}; scored as the last chip in "
              f"{sum(r['value'] for r in known):+,.0f}, realised {sum(r['realised'] for r in known):+,.0f}")
    print()
    print(f"Replayed: {len(replayed)} folds priced by the rule, {sum(r['fired'] for r in replayed)} fired")
    print(f"{'margin':>6} {'fired':>5} {'shown':>5} {'chips':>9} {'a firing':>9} {'worst':>7}")
    for margin in MARGINS + ((player.OFFTREE_MARGIN,) if player.OFFTREE_MARGIN not in MARGINS else ()):
        fired = [r for r in replayed if r["equity"] >= r["price"] + margin]
        scored = [r["value"] for r in fired if r.get("value") is not None]
        print(f"{margin:6.2f} {len(fired):5d} {len(scored):5d} {sum(scored):+9,.0f} "
              f"{(sum(scored) / len(scored)) if scored else 0:+9,.0f} {min(scored) if scored else 0:+7,.0f}")
    print()
    print(f"{'match':8} {'hand':>4} {'opponent':12} {'bb':>5} {'line':6} {'ours':5} {'theirs':6} {'pot':>6} {'call':>5} "
          f"{'price':>5} {'eqR':>5} {'share':>6} {'eqS':>5} {'value':>7} fired  logged")
    for r in sorted(replayed, key=lambda r: (not r["fired"], r["match"], r["hand"] or 0)):
        print(f"{r['match']:8} {r['hand'] or 0:>4} {str(r['opponent'])[:12]:12} {r['effective_bb'] or 0:5.1f} "
              f"{r['line']:6} {r['hole']:5} {r['theirs'] or '-':6} {r['pot']:>6,} {r['call']:>5,} {r['price']:5.2f} "
              f"{r['equity']:5.2f} {r['range_share']:6.3f} "
              f"{('%.2f' % r['shown_equity']) if r.get('shown_equity') is not None else '-':>5} "
              f"{('%+7.0f' % r['value']) if r.get('value') is not None else '-':>7} {'yes' if r['fired'] else 'no':5}  "
              f"{r['logged_history']}->{['fold', 'call'][r['logged_choice']] if r['logged_choice'] in (0, 1) else r['logged_choice']}")
    if args.json:
        with open(args.json, "w") as handle:
            json.dump({"logged": logged, "called_logged": called_logged, "replayed": replayed}, handle, indent=1)


if __name__ == "__main__":
    main()
