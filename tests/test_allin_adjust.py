"""
The all-in adjustment in chipzen_decompose must change the variance of a burst and nothing else.

It replaces a called all-in's realised net with its expectation over the runouts, which is only honest if the
expectation is right (checked against a brute force through the Python evaluator, a separate implementation from
the native one the script calls), if it touches no hand that was not chance alone from the all-in on, and if raw
and adjusted totals agree on average. The logs are synthetic but shaped like chipzen.client's.
"""
import itertools
import os
import random
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.hand_eval_fast import score_hand_7_fast  # noqa: E402
from scripts.chipzen_decompose import allin_nets, allin_spot, card_index, hand_nets  # noqa: E402

DECK = [r + s for s in "hdcs" for r in "23456789TJQKA"]


def score(cards):
    idx = [card_index(c) for c in cards]
    return score_hand_7_fast(np.array([i % 13 for i in idx]), np.array([i // 13 for i in idx]))


def outcome(mine, theirs, board):
    a, b = score(mine + board), score(theirs + board)
    return (a > b) - (a < b)


def brute_edge(mine, theirs, board):
    """P(win) - P(lose) over every runout, by the Python evaluator."""
    deck = [c for c in DECK if c not in set(mine) | set(theirs) | set(board)]
    runs = list(itertools.combinations(deck, 5 - len(board)))
    return sum(outcome(mine, theirs, board + list(r)) for r in runs) / len(runs)


def act(seat, action, amount, phase):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase, "is_timeout": False}


def decision(hand, phase, board, choice=1):
    return {"frame": "decision", "hand": hand, "phase": phase, "board": list(board), "history": "", "choice": choice,
            "solver": "100bb", "companion": None, "fallback": False, "adjusted": None}


def allin_hand(hand, mine, theirs, board, street, stacks=(10000, 10000), shown=None):
    """
    Rows for one hand where we (seat 0, the button) shove on `street` and get called, run out to `board`.

    The caller may cover us or not; whatever the bigger stack put in beyond the smaller goes back uncalled, so the
    stacks after move by the smaller stack only, as the server pays it.
    """
    a, b = stacks
    risk = min(stacks)
    flop, turn = board[:3], board[:4]
    history = [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop")]
    rows = [{"frame": "round_start", "state": {"hand_number": hand, "stacks": list(stacks)}}]
    if street == "preflop":
        rows.append(decision(hand, "preflop", [], 5))
        history += [act(0, "raise", a, "preflop"), act(1, "call", risk - 100, "preflop")]
    else:
        rows.append(decision(hand, "preflop", []))
        history += [act(0, "call", 50, "preflop"), act(1, "check", 0, "preflop")]
        streets = ["flop", "turn", "river"]
        cards = {"flop": flop, "turn": turn, "river": board}
        for s in streets[:streets.index(street) + 1]:
            rows.append(decision(hand, s, cards[s], 5 if s == street else 0))
            history.append(act(1, "check", 0, s))
            if s == street:
                history += [act(0, "raise", a - 100, s), act(1, "call", risk - 100, s)]
            else:
                history.append(act(0, "check", 0, s))
    sign = outcome(mine, theirs, list(board))
    after = [a + sign * risk, b - sign * risk]
    best = shown if shown is not None else {0: mine + list(board[:3]), 1: theirs + list(board[:3])}
    rows.append({"frame": "round_result", "result": {
        "hand_number": hand, "stacks": after, "action_history": history,
        "showdown": [{"seat": 0, "hole_cards": mine, "best_hand": best[0]},
                     {"seat": 1, "hole_cards": theirs, "best_hand": best[1]}]}})
    return rows


def decisions_of(rows):
    out = {}
    for r in rows:
        if r.get("frame") == "decision":
            out.setdefault(r["hand"], []).append(r)
    return out


def test_a_set_against_a_flush_draw_on_the_flop_scores_its_exact_equity():
    """
    Sevens full of nothing yet against a flush draw, with our shove covering them: the contested amount is their
    6,000, not our 10,000, and our expectation is 6,000 times the brute-force edge over all 990 runouts.
    """
    mine, theirs = ["7s", "7d"], ["Qc", "Jc"]
    board = ["7h", "2c", "9c", "3d", "4h"]
    rows = allin_hand(1, mine, theirs, board, "flop", stacks=(10000, 6000))
    realised = hand_nets(rows, 0)[1]
    assert realised == 6000                                 # the set held on this runout

    adjusted, spot, reachable = allin_nets(rows, 0, decisions_of(rows))[1]
    assert spot["at_risk"] == 6000 and spot["board"] == board[:3]
    edge = brute_edge(mine, theirs, board[:3])
    assert 0.3 < edge < 0.6                                 # a favourite, not a lock: the draw has ~25%
    assert adjusted == pytest.approx(6000 * edge, abs=1e-6)
    assert realised in reachable and reachable <= {6000, -6000, 0}


def test_the_turn_expectation_is_the_mean_over_all_44_rivers():
    """The identity that makes the adjustment unbiased, checked hand by hand rather than in aggregate."""
    mine, theirs, turn = ["Ah", "Kh"], ["Qs", "Qd"], ["Qh", "7h", "2s", "8c"]
    rivers = [c for c in DECK if c not in set(mine + theirs + turn)]
    assert len(rivers) == 44
    realised = []
    for i, river in enumerate(rivers):
        rows = allin_hand(i, mine, theirs, turn + [river], "turn", stacks=(8000, 8000))
        realised.append(hand_nets(rows, 0)[i])
        adjusted = allin_nets(rows, 0, decisions_of(rows))[i][0]
    assert np.mean(realised) == pytest.approx(adjusted, abs=1e-6)


def test_a_preflop_jam_uses_the_full_enumeration():
    """Aces against kings, about 82%: the native enumeration against a seeded Python sample of 20,000 boards."""
    mine, theirs = ["As", "Ah"], ["Kd", "Kc"]
    rows = allin_hand(1, mine, theirs, ["2c", "7d", "9s", "Jh", "3c"], "preflop", stacks=(5000, 9000))
    adjusted, spot, reachable = allin_nets(rows, 0, decisions_of(rows))[1]
    assert spot["at_risk"] == 5000 and spot["board"] == []
    rng = random.Random(11)
    deck = [c for c in DECK if c not in set(mine + theirs)]
    sampled = np.mean([outcome(mine, theirs, rng.sample(deck, 5)) for _ in range(20000)])
    assert adjusted / 5000 == pytest.approx(sampled, abs=0.015)
    assert hand_nets(rows, 0)[1] in reachable


def test_hands_that_were_not_chance_alone_keep_their_net():
    """A fold, a check-down that was never all in, and a river all-in all stay as they were."""
    fold = [{"frame": "round_start", "state": {"hand_number": 1, "stacks": [10000, 10000]}},
            decision(1, "preflop", [], 5),
            {"frame": "round_result", "result": {
                "hand_number": 1, "stacks": [10100, 9900], "showdown": [{"seat": 0, "hole_cards": ["As", "Ah"]}],
                "action_history": [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop"),
                                   act(0, "raise", 300, "preflop"), act(1, "fold", 0, "preflop")]}}]
    board = ["Ah", "Kd", "7c", "2s", "9h"]
    history = [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop"),
               act(0, "call", 50, "preflop"), act(1, "check", 0, "preflop")]
    for s in ("flop", "turn", "river"):
        history += [act(1, "check", 0, s), act(0, "check", 0, s)]
    checkdown = [{"frame": "round_start", "state": {"hand_number": 2, "stacks": [10000, 10000]}},
                 decision(2, "river", board),
                 {"frame": "round_result", "result": {
                     "hand_number": 2, "stacks": [10100, 9900], "action_history": history,
                     "showdown": [{"seat": 0, "hole_cards": ["Ac", "Qd"]}, {"seat": 1, "hole_cards": ["Js", "Jd"]}]}}]
    river = allin_hand(3, ["Ac", "Qd"], ["Js", "Jd"], board, "river")
    rows = fold + checkdown + river
    raw = hand_nets(rows, 0)
    assert raw == {1: 100, 2: 100, 3: 10000}
    assert allin_nets(rows, 0, decisions_of(rows)) == {}
    for hand, rs in ((1, fold), (2, checkdown), (3, river)):
        res = rs[-1]["result"]
        assert allin_spot(res, rs[0]["state"]["stacks"], decisions_of(rs).get(hand, []), 0) is None


def test_raw_and_adjusted_totals_agree_in_expectation():
    """
    Four hundred random flop and turn all-ins, each run out once with a seeded RNG: the adjusted total must sit
    within four standard errors of the raw one, and its spread must be smaller, which is the point of it.
    """
    rng = random.Random(5)
    raw, adjusted = [], []
    for hand in range(400):
        cards = rng.sample(DECK, 9)
        street = rng.choice(["flop", "turn"])
        stacks = (rng.randrange(2000, 20000, 100), rng.randrange(2000, 20000, 100))
        rows = allin_hand(hand, cards[:2], cards[2:4], cards[4:], street, stacks=stacks)
        raw.append(hand_nets(rows, 0)[hand])
        adjusted.append(allin_nets(rows, 0, decisions_of(rows))[hand][0])
    raw, adjusted = np.array(raw, float), np.array(adjusted, float)
    diff = raw - adjusted
    assert abs(diff.mean()) < 4 * diff.std() / np.sqrt(diff.size)
    assert adjusted.std() < raw.std()
