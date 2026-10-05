"""
AIVAT on the arena logs must leave the mean alone: every control term has to average zero given what came before.

The chance terms rest on one identity, that equity against a random hand is a martingale over the next card, so it
is checked exactly by enumeration rather than in aggregate. The decision terms rest on the logged distribution
being the one sampled, so the term's expectation under that distribution is checked to be zero for every choice.
The rest pins the bookkeeping: pots and stacks read from the arena's history, an all-in's later cards left to the
exact runout expectation, and nothing at all where our play was purified.
"""
import itertools
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.hand_eval_fast import score_hand_7_fast  # noqa: E402
from evaluation.aivat import (STREETS, ValueFunction, action_values, card_index, hand_class,  # noqa: E402
                              hand_terms, trace_hand)
from scripts.chipzen_decompose import aivat_hands, allin_nets, hand_nets  # noqa: E402
from tests.test_allin_adjust import act, allin_hand, decisions_of  # noqa: E402

DECK = [r + s for s in "hdcs" for r in "23456789TJQKA"]
# A coarse table is enough wherever the preflop number only has to be the same on both sides of an identity.
TABLE = {hand_class(h): 0.5 for h in itertools.combinations(range(52), 2)}
TABLE.update({"AA": 0.852, "KK": 0.824, "72o": 0.346, "AKs": 0.67, "QJs": 0.6})


def vf(a=1.0, b=0.0):
    return ValueFunction({s: (a, b) for s in STREETS}, TABLE, "test")


def idx(cards):
    return [card_index(c) for c in cards]


def test_board_equity_matches_a_brute_force_through_the_python_evaluator():
    hole, board = idx(["Ah", "Kh"]), idx(["Qh", "7h", "2s", "8c", "Td"])
    dead = set(hole + board)
    score = lambda cards: score_hand_7_fast(np.array([c % 13 for c in cards]), np.array([c // 13 for c in cards]))
    mine = score(hole + board)
    results = []
    for o in itertools.combinations([c for c in range(52) if c not in dead], 2):
        theirs = score(list(o) + board)
        results.append(1.0 if mine > theirs else 0.5 if mine == theirs else 0.0)
    assert vf().equity(hole, board) == pytest.approx(np.mean(results), abs=1e-12)


@pytest.mark.parametrize("hole, board", [(["Ah", "Kh"], ["Qh", "7h", "2s", "8c"]),
                                         (["7s", "7d"], ["7h", "2c", "9c"])])
def test_equity_is_a_martingale_over_the_next_card(hole, board):
    """E over the next card of the equity is the equity now, exactly: the chance term's mean is zero."""
    hole, board = idx(hole), idx(board)
    v = vf()
    nxt = [c for c in range(52) if c not in set(hole + board)]
    assert np.mean([v.equity(hole, board + [c]) for c in nxt]) == pytest.approx(v.equity(hole, board), abs=1e-12)


def test_the_frozen_preflop_table_averages_one_half_over_all_deals():
    path = os.path.join(os.path.dirname(__file__), "..", "evaluation", "aivat_value.json")
    if not os.path.exists(path):
        pytest.skip("no frozen value file")
    frozen = ValueFunction.load(path)
    mean = np.mean([frozen.equity(list(h), []) for h in itertools.combinations(range(52), 2)])
    assert mean == pytest.approx(0.5, abs=5e-4)
    assert frozen.preflop["AA"] == pytest.approx(0.852, abs=2e-3)


def _flop_hand(choice_probs=None, choice=3):
    """We (seat 0, the button) limp, face a flop bet and raise it, and the opponent folds: known pots throughout."""
    history = [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop"),
               act(0, "call", 50, "preflop"), act(1, "check", 0, "preflop"),
               act(1, "raise", 150, "flop"), act(0, "raise", 600, "flop"), act(1, "fold", 0, "flop")]
    d0 = {"frame": "decision", "hand": 1, "phase": "preflop", "board": [], "pot": 150, "to_call": 50,
          "history": "", "choice": 1, "legal": [1, 1, 1, 1, 1, 1], "solver": "100bb"}
    d1 = {"frame": "decision", "hand": 1, "phase": "flop", "board": ["Qh", "7h", "2s"], "pot": 350, "to_call": 150,
          "history": "", "choice": choice, "legal": [1, 1, 1, 1, 1, 1], "solver": "100bb"}
    if choice_probs is not None:
        d1["probs"] = choice_probs
    result = {"hand_number": 1, "action_history": history, "stacks": [10350, 9650],
              "showdown": [{"seat": 0, "hole_cards": ["Ah", "Kh"]}]}
    return result, [d0, d1]


def test_the_trace_reads_pots_and_stacks_from_the_arenas_history():
    result, ds = _flop_hand()
    t = trace_hand(result, [10000, 8000], ds, 0, ["Ah", "Kh"])
    assert [(n["street"], n["pot"], n["eff"]) for n in t["chance"]] == [("preflop", 150, 8000), ("flop", 200, 7900)]
    flop = t["ours"][1]
    assert (flop["our"], flop["opp"], flop["our_stack"], flop["opp_stack"]) == (100, 250, 9900, 7750)
    v = action_values(vf(), "flop", 0.7, flop)
    assert v[0] == -100                                  # a fold loses what we put in
    assert v[1] == pytest.approx(500 * 0.7 - 250)          # a call: 250 each, checked down at 70%
    # A pot raise: 150 to call plus the pot after the call (500), so 650 more and 750 each if matched.
    assert v[3] == pytest.approx(1500 * 0.7 - 750)


def test_a_decision_term_has_zero_mean_under_the_logged_distribution():
    sigma = [0.1, 0.3, 0.05, 0.4, 0.05, 0.1]
    total = 0.0
    for choice in range(6):
        result, ds = _flop_hand(sigma, choice)
        terms = hand_terms(vf(), trace_hand(result, [10000, 8000], ds, 0, ["Ah", "Kh"]))
        assert terms["decisions_with_term"] == 1 and terms["decisions_without"] == 1   # the preflop row has no probs
        total += sigma[choice] * terms["decision"]
    assert total == pytest.approx(0.0, abs=1e-9)


def test_a_purified_row_gets_no_decision_term_and_zero_coefficients_change_nothing():
    result, ds = _flop_hand()
    terms = hand_terms(vf(), trace_hand(result, [10000, 8000], ds, 0, ["Ah", "Kh"]))
    assert terms["decision"] == 0.0 and terms["decisions_with_term"] == 0
    assert set(terms["chance"]) == {"preflop", "flop"}
    zero = hand_terms(vf(0.0, 0.0), trace_hand(result, [10000, 8000], ds, 0, ["Ah", "Kh"]))
    assert zero["total"] == 0.0


def test_an_allin_keeps_its_exact_runout_and_gets_terms_only_up_to_its_street():
    mine, theirs, board = ["7s", "7d"], ["Qc", "Jc"], ["7h", "2c", "9c", "3d", "4h"]
    rows = [r for r in allin_hand(1, mine, theirs, board, "flop", stacks=(10000, 6000))]
    rows[0]["state"]["your_hole_cards"] = mine
    decisions = decisions_of(rows)
    allins = allin_nets(rows, 0, decisions)
    value, terms = aivat_hands(rows, 0, decisions, allins, vf())[1]
    assert set(terms["chance"]) == {"preflop", "flop"}
    assert value == pytest.approx(allins[1][0] - terms["total"])
    # With no value function the estimate is the all-in adjustment exactly.
    assert aivat_hands(rows, 0, decisions, allins, vf(0.0, 0.0))[1][0] == pytest.approx(allins[1][0])


def test_simulated_matches_parse_and_every_decision_gets_its_term(tmp_path):
    """Two short matches from the simulator, read back the way the decomposition reads a burst."""
    from scripts.aivat_sim import play_logged_match
    rng = np.random.default_rng(3)
    for k, kind in enumerate(("maniac", "foldraise")):
        rows = play_logged_match(f"t{k}", kind, rng, hero_seat=k % 2)
        seat = rows[0]["seat"]
        decisions = {}
        for r in rows:
            if r.get("frame") == "decision":
                decisions.setdefault(r["hand"], []).append(r)
        nets = hand_nets(rows, seat)
        assert abs(sum(nets.values())) == 10000           # played to a bust
        scored = aivat_hands(rows, seat, decisions, allin_nets(rows, seat, decisions), vf())
        n_rows = sum(len(v) for v in decisions.values())
        assert sum(t["decisions_with_term"] for _, t in scored.values()) == n_rows
        assert sum(t["board_missing"] for _, t in scored.values()) == 0
