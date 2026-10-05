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

    venv/bin/python scripts/chipzen_decompose.py --label balanced-next --allin-adjust \
        --matches-dir ~/Code/PokerBot/results/chipzen/matches

`--allin-adjust` prints each row twice, raw and with every called all-in before
the river scored at its expectation over the runouts. Both estimate the same
thing, while the adjusted one drops the luck of a few large coin flips, which
is most of a burst's spread.

    venv/bin/python scripts/chipzen_decompose.py --label "v5xRR3 purified" --aivat \
        --between 2026-10-03T07:00 2026-10-03T09:00 --matches-dir ~/Code/PokerBot/results/chipzen/matches

`--aivat` prints three columns: raw, all-in adjusted and AIVAT (evaluation/aivat.py), which also takes out the
luck of our hole cards and of every board card the all-in adjustment cannot reach, against a value function frozen
in evaluation/aivat_value.json before these bursts were played. Only the all, deep and short rows are unbiased
under AIVAT; the rows chosen by what we did after the cards fell are marked, because selecting on our own later
actions is selecting on the very cards the terms correct for.
"""
import argparse
import datetime
import glob
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MATCHES = os.path.join(ROOT, "results", "chipzen", "matches")
DEEP = {"50bb", "70bb", "100bb", "200bb"}


def hand_nets(rows, seat):
    """
    Net chips per hand for our seat: our stack after the hand minus before it.

    Until 2 Oct this was payouts minus our puts, with a raise's amount taken as everything we had put in; it is the
    street's total, so a raise forgot what we had put in on earlier streets and the net read too high in 26 to 34% of
    hands, every printed row optimistic by about +100 to +190 chips a hand. The stack difference agrees with payouts
    minus true contributions on all 21,450 logged hands (~/pokerbot-scratch/offtree/report.md).
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


# The cheap half of AIVAT. A called all-in before the river is a coin we have already chosen to flip: once the money
# is in, the rest of the hand is chance alone, so its realised net can be replaced by the net's expectation over the
# cards still to come without biasing the mean. On 4 Oct three such hands moved about 22,800 chips against a burst
# total of about 10,900, which is variance the measurement does not need to carry. Every called all-in reaches
# showdown, so both hands are in the log.
BOARD_CARDS = {"preflop": 0, "flop": 3, "turn": 4}
_RANKS = "23456789TJQKA"
_SUITS = "hdcs"


def card_index(card):
    """'Kh' to the native deck index, suit * 13 + rank, the same as engine.cards.Card.index."""
    return _SUITS.index(card[1]) * 13 + _RANKS.index(card[0])


def contributions(action_history):
    """
    Chips each seat put in over the hand, and the street the last chip went in on.

    A raise's amount is the seat's total for the street while a call's is the increment; reading a raise as the
    hand's total is what made hand_nets optimistic until 2 Oct.
    """
    total, street_total, street, last = [0, 0], [0, 0], None, None
    for a in action_history:
        if a["phase"] != street:
            street, street_total = a["phase"], [0, 0]
        s = a["seat"]
        if a["action"] in ("raise", "bet", "all_in"):
            add = a["amount"] - street_total[s]
            street_total[s] = a["amount"]
        elif a["action"] in ("call", "post_small_blind", "post_big_blind"):
            add = a["amount"]
            street_total[s] += a["amount"]
        else:
            add = 0
        total[s] += add
        if add > 0:
            last = a["phase"]
    return total, last


def allin_spot(result, before, decisions, seat):
    """
    The all-in a hand reduces to, or None when the rest of it was not chance alone.

    The contested amount is the smaller contribution: whatever the covering seat put in beyond it went back uncalled,
    so it was never at risk. The board is the one we saw on the all-in street, from our own decision there. We always
    act on the street the last chip goes in, because that chip is either ours or a bet we answered; the exception is
    a preflop all-in forced by the blinds, which has no decision and an empty board anyway.
    """
    shown = {s["seat"]: s["hole_cards"] for s in (result.get("showdown") or [])}
    if not before or len(shown) != 2:
        return None
    total, street = contributions(result.get("action_history", []))
    at_risk = min(total)
    if street not in BOARD_CARDS or at_risk != min(before):
        return None
    on_street = [d for d in decisions if d["phase"] == street]
    board = on_street[-1]["board"] if on_street else []
    if len(board) != BOARD_CARDS[street]:
        return None
    return {"mine": shown[seat], "theirs": shown[1 - seat], "board": list(board), "at_risk": at_risk,
            "street": street}


def expected_net(spot):
    """
    Our net in expectation over the runouts: our share of the 2 * at_risk pot less our at_risk, ties split.

    That is at_risk * (P(win) - P(lose)), which native.allin_edge enumerates exactly: 990 runouts from the flop, 44
    from the turn, and all 1,712,304 preflop, which takes about 0.35 s in C++, so nothing needs sampling.
    """
    import pokerbot_native as native
    edge = native.allin_edge([card_index(c) for c in spot["mine"]], [card_index(c) for c in spot["theirs"]],
                             [card_index(c) for c in spot["board"]], True)
    return spot["at_risk"] * edge


def reachable_nets(spot, revealed):
    """
    The nets the hand could have produced on the runouts that agree with the board cards the log revealed.

    The log carries no final board, but each showdown's best_hand lists five cards, and the ones that are not hole
    cards are board cards, so at least three of the final five are known and at most 990 completions remain. A
    realised net outside this set means the spot was misread: wrong pot, wrong seat or wrong cards. Returns None
    when the revealed cards cannot belong to this board at all.
    """
    import itertools
    import pokerbot_native as native
    known = list(spot["board"]) + [c for c in revealed if c not in spot["board"]]
    if len(known) > 5:
        return None
    used = set(spot["mine"]) | set(spot["theirs"]) | set(known)
    deck = [r + s for s in _SUITS for r in _RANKS if r + s not in used]

    def split(cards):
        return [_RANKS.index(c[0]) for c in cards], [_SUITS.index(c[1]) for c in cards]
    nets = set()
    for extra in itertools.combinations(deck, 5 - len(known)):
        board = known + list(extra)
        a = native.score_hand_7(*split(spot["mine"] + board))
        b = native.score_hand_7(*split(spot["theirs"] + board))
        nets.add(spot["at_risk"] * ((a > b) - (a < b)))
    return nets


def allin_nets(rows, seat, decisions):
    """
    {hand: (expected net, spot, reachable nets or None)} for each called all-in before the river.

    `decisions` maps a hand number to our decision rows for it. A hand not in the result keeps its realised net.
    """
    out, before = {}, None
    for r in rows:
        if r.get("frame") == "round_start":
            before = (r.get("state") or {}).get("stacks")
        elif r.get("frame") == "round_result":
            res = r["result"]
            spot = allin_spot(res, before, decisions.get(res["hand_number"], []), seat)
            before = None
            if spot is None:
                continue
            holes = set(spot["mine"]) | set(spot["theirs"])
            revealed = sorted({c for s in res["showdown"] for c in (s.get("best_hand") or [])} - holes)
            out[res["hand_number"]] = (expected_net(spot), spot, reachable_nets(spot, revealed))
    return out


def aivat_hands(rows, seat, decisions, allins, vf):
    """
    {hand: (AIVAT value, terms)} for every hand with a result: the base value (the realised net, or a called
    all-in's expectation over the runouts) less the control terms of evaluation.aivat.hand_terms.

    For an all-in the chance terms stop at the all-in street, because the cards after it are already in the base.
    """
    from evaluation.aivat import hand_terms, trace_hand
    nets = hand_nets(rows, seat)
    out, before, hole = {}, None, None
    for r in rows:
        if r.get("frame") == "round_start":
            before = (r.get("state") or {}).get("stacks")
            hole = (r.get("state") or {}).get("your_hole_cards")
        elif r.get("frame") == "round_result":
            res = r["result"]
            hand = res["hand_number"]
            if before and hole and hand in nets:
                base, last = nets[hand], None
                if hand in allins:
                    base, last = allins[hand][0], allins[hand][1]["street"]
                trace = trace_hand(res, before, decisions.get(hand, []), seat, hole)
                terms = hand_terms(vf, trace, last)
                out[hand] = (base - terms["total"], terms)
            before, hole = None, None
    return out


def _ist(text):
    """
    '2026-10-03T07:00' read as IST, to a Unix time: the ledger and the fixture list both keep IST.

    An explicit offset wins, because a time copied from a log written under the machine's old +04 clock would
    otherwise be read 90 minutes off with nothing to say so.
    """
    moment = datetime.datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    return moment.timestamp()


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
    parser.add_argument("--matches-dir", nargs="+", default=[MATCHES],
                        help="one or more directories of match JSONL (a worktree has none of its own)")
    parser.add_argument("--allin-adjust", action="store_true",
                        help="also report each row with every called all-in before the river replaced by its "
                             "expected net over the runouts, side by side with the raw row")
    parser.add_argument("--aivat", action="store_true",
                        help="raw, all-in adjusted and AIVAT side by side (evaluation/aivat.py); implies the all-in "
                             "adjustment, whose exact runout expectation AIVAT keeps")
    parser.add_argument("--aivat-value", default=None,
                        help="the frozen value function (default evaluation/aivat_value.json), or 'checkdown' for "
                             "the unfitted g = pot")
    parser.add_argument("--between", nargs=2, metavar=("FROM", "TO"),
                        help="only matches that started in this window, IST, e.g. 2026-10-03T07:00 2026-10-03T09:00: "
                             "a label can also hold single fixtures that are not the burst")
    parser.add_argument("--progress", help="a file rewritten after every match file read: done of total, elapsed and "
                                           "an ETA from the measured rate (AIVAT costs about 0.1 s a hand)")
    args = parser.parse_args()
    if args.aivat:
        args.allin_adjust = True
        from evaluation.aivat import VALUE_FILE, ValueFunction
        vf = ValueFunction.load(args.aivat_value if args.aivat_value not in (None, "checkdown") else VALUE_FILE)
        if args.aivat_value == "checkdown":
            vf = ValueFunction.checkdown(vf.preflop)
    window = (_ist(args.between[0]), _ist(args.between[1])) if args.between else None

    aivat = defaultdict(lambda: defaultdict(list))        # the same rows under AIVAT
    terms_by = defaultdict(lambda: defaultdict(list))     # per label: each kind of term, per hand
    per_label = defaultdict(lambda: defaultdict(list))
    adjusted = defaultdict(lambda: defaultdict(list))     # the same rows, all-ins at their expectation
    touched = defaultdict(lambda: defaultdict(int))       # adjusted hands per row
    checks = defaultdict(lambda: defaultdict(int))        # per label: streets adjusted, validation outcomes
    paths = sorted(p for d in args.matches_dir for p in glob.glob(os.path.join(d, "*.jsonl")))
    started = time.time()
    for done, path in enumerate(paths):
        if args.progress:
            elapsed = time.time() - started
            eta = f"{elapsed / done * (len(paths) - done) / 60:.1f} min" if done else "not yet measured"
            with open(args.progress, "w") as handle:
                handle.write(f"{done} of {len(paths)} match files read, elapsed {elapsed / 60:.1f} min, ETA {eta}\n")
        with open(path) as handle:
            rows = [json.loads(line) for line in handle]
        if not rows or rows[0].get("frame") != "match_start" or "version" not in rows[0]:
            continue
        label = rows[0]["version"]["label"]
        tag = next((l for l in args.label if label.startswith(l + ":") or label == l), None)
        if tag is None:
            continue
        if window and not window[0] <= rows[0].get("at", 0) < window[1]:
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
        allins = allin_nets(rows, seat, decisions) if args.allin_adjust else {}
        scored = aivat_hands(rows, seat, decisions, allins, vf) if args.aivat else {}
        for hand, ds in decisions.items():
            if hand not in nets:
                continue
            if args.aivat and hand not in scored:
                # No hole cards logged, so no AIVAT value. The hand leaves all three columns, not only the AIVAT
                # one, because the paired AIVAT minus all-in check is only a bias check on the same hands.
                checks[tag]["hands without hole cards"] += 1
                continue
            value = nets[hand]
            if hand in allins:
                value, spot, reachable = allins[hand]
                checks[tag][spot["street"]] += 1
                if reachable is None:
                    checks[tag]["revealed cards do not fit the board"] += 1
                elif nets[hand] in reachable:
                    checks[tag]["realised net reachable"] += 1
                else:
                    checks[tag]["realised net NOT reachable"] += 1
                checks[tag]["raw chips"] += nets[hand]
                checks[tag]["expected chips"] += value
            if args.aivat:
                terms = scored[hand][1]
                for street in ("preflop", "flop", "turn", "river"):
                    terms_by[tag][street].append(terms["chance"].get(street, 0.0))
                terms_by[tag]["decisions"].append(terms["decision"])
                for k in ("decisions_with_term", "decisions_without", "decisions_unlogged", "board_missing"):
                    checks[tag][k] += terms[k]
            for cat in classify(ds):
                per_label[tag][cat].append(nets[hand])
                adjusted[tag][cat].append(value)
                touched[tag][cat] += hand in allins
                if args.aivat:
                    aivat[tag][cat].append(scored[hand][0])

    order = ["all", "deep", "short", "companion decided", "rule decided", "we jammed preflop",
             "called a preflop jam", "called a river shove", "a read fired"]
    labels = [l for l in args.label if l in per_label]
    print(f"chips per hand ± standard error (hands), on decision hands"
          + (f" against {args.opponent}" if args.opponent else "") + "\n")
    if args.aivat:
        print_aivat(order, labels, per_label, adjusted, aivat, terms_by, checks, vf)
        return
    if args.allin_adjust:
        print_adjusted(order, labels, per_label, adjusted, touched, checks)
        return
    print("| category | " + " | ".join(labels) + " |")
    print("|---|" + "---|" * len(labels))
    for cat in order:
        cells = [_cell(per_label[l].get(cat, [])) for l in labels]
        print(f"| {cat} | " + " | ".join(cells) + " |")


def _cell(values, note=""):
    x = np.array(values, dtype=float)
    if x.size == 0:
        return "—"
    se = x.std() / np.sqrt(x.size) if x.size > 1 else float("nan")
    return f"{x.mean():+.0f} ± {se:.0f} ({x.size}{note})"


def _mean_se(values):
    x = np.asarray(values, dtype=float)
    return f"{x.mean():+.1f} ± {x.std() / np.sqrt(x.size):.1f}"


def print_adjusted(order, labels, per_label, adjusted, touched, checks):
    """Raw and all-in adjusted side by side; the adjusted cell says how many of its hands were replaced."""
    print("| category | " + " | ".join(f"{l} raw | {l} adjusted" for l in labels) + " |")
    print("|---|" + "---|---|" * len(labels))
    for cat in order:
        cells = []
        for l in labels:
            cells.append(_cell(per_label[l].get(cat, [])))
            cells.append(_cell(adjusted[l].get(cat, []), f", {touched[l][cat]} adjusted"))
        print(f"| {cat} | " + " | ".join(cells) + " |")
    print()
    for l in labels:
        c = checks[l]
        streets = ", ".join(f"{c[s]} {s}" for s in BOARD_CARDS if c[s])
        n = sum(c[s] for s in BOARD_CARDS)
        print(f"{l}: {n} hands adjusted ({streets or 'none'}); on them raw {c['raw chips']:+,} chips against "
              f"expected {c['expected chips']:+,.0f}. Realised net reachable on the revealed board: "
              f"{c['realised net reachable']} of {n}, not reachable {c['realised net NOT reachable']}, "
              f"revealed cards inconsistent {c['revealed cards do not fit the board']}.")


#: The rows a hand enters by its stack depth alone, which is fixed before any card is dealt; every other row is
#: entered by what we or the opponent did after seeing cards, and conditioning on that makes the chance terms'
#: mean nonzero inside the row.
UNBIASED_ROWS = {"all", "deep", "short"}


def print_aivat(order, labels, per_label, adjusted, aivat, terms_by, checks, vf):
    """Raw, all-in adjusted and AIVAT side by side, then what each kind of term did per label."""
    print(f"value function {vf.name} ({vf.digest})\n")
    print("| category | " + " | ".join(f"{l} raw | {l} all-in | {l} AIVAT" for l in labels) + " |")
    print("|---|" + "---|---|---|" * len(labels))
    for cat in order:
        cells = []
        for l in labels:
            cells.append(_cell(per_label[l].get(cat, [])))
            cells.append(_cell(adjusted[l].get(cat, [])))
            cells.append(_cell(aivat[l].get(cat, [])) + ("" if cat in UNBIASED_ROWS else " †"))
        print(f"| {cat} | " + " | ".join(cells) + " |")
    print("\n† selected after the cards were seen, so the AIVAT cell is the row's result relative to its cards, "
          "not an estimate of the raw cell.\n")
    for l in labels:
        raw = np.array(per_label[l]["all"], dtype=float)
        adj = np.array(adjusted[l]["all"], dtype=float)
        av = np.array(aivat[l]["all"], dtype=float)
        kinds = ", ".join(f"{k} {_mean_se(v)} (sd {np.std(v):.0f})" for k, v in terms_by[l].items())
        c = checks[l]
        # The paired difference is the bias check: it is minus the sum of the terms, whose mean must be zero.
        print(f"{l}: sd per hand raw {raw.std():.0f}, all-in {adj.std():.0f}, AIVAT {av.std():.0f}; "
              f"AIVAT is worth {(raw.var() / av.var()):.2f}x the hands of raw and {(adj.var() / av.var()):.2f}x "
              f"the all-in adjusted. AIVAT minus all-in, paired: {_mean_se(av - adj)}. "
              f"Terms, mean ± se per hand: {kinds}. Decisions with a term {c['decisions_with_term']}, "
              f"without (purified or distribution unknown) {c['decisions_without']}, our actions with no logged "
              f"row {c['decisions_unlogged']}; streets without a logged board {c['board_missing']}; hands left "
              f"out of every column for want of our hole cards {c['hands without hole cards']}.")
    for l, c in checks.items():
        if l not in labels and c["hands without hole cards"]:
            print(f"{l}: every hand left out, {c['hands without hole cards']} without our hole cards in the log.")


if __name__ == "__main__":
    main()
