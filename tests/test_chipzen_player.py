"""
The arena player: solver ladder, fallback, and the client's result reading.

The ladder tests build `Solver` rows by hand so they do not depend on which
pickles exist; the decision tests load the shipped 100bb solver, which the
whole panel depends on anyway.
"""
import os

import numpy as np
import pytest

from abstraction.betting import FOLD
from chipzen.client import _outcome, _resolve
from chipzen.player import ArenaPlayer, Solver

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHIPPED = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")


def rung(depth):
    return Solver(path=f"{depth}bb", depth_bb=float(depth), schedule=1,
                  strategy={}, abstraction=None)


def _ladder(*depths):
    player = ArenaPlayer.__new__(ArenaPlayer)
    player.ladder = sorted((rung(d) for d in depths), key=lambda s: s.depth_bb)
    return player


def test_the_nearest_rung_is_chosen_in_ratio_not_in_difference():
    player = _ladder(100, 50, 25)
    # 70bb is 30 from 100 and 20 from 50 by difference, but closer to 100 in ratio
    # only above sqrt(50 * 100) = 70.7; at 70 it is the 50 rung.
    assert player.solver_for(75).depth_bb == 100
    assert player.solver_for(70).depth_bb == 50
    assert player.solver_for(3).depth_bb == 25
    assert player.solver_for(1000).depth_bb == 100


def test_an_unknown_depth_falls_to_the_shortest_rung():
    assert _ladder(100, 50).solver_for(0).depth_bb == 50


def blinds():
    return [{"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop", "is_timeout": False},
            {"seat": 1, "action": "post_big_blind", "amount": 100, "phase": "preflop", "is_timeout": False}]


def entry(seat, action, amount, phase="preflop"):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase, "is_timeout": False}


@pytest.fixture(scope="module")
def player():
    return ArenaPlayer([SHIPPED], np.random.default_rng(3))


def test_a_decision_is_always_one_the_arena_offered(player):
    state = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["9h", "3s"],
             "pot": 150, "your_stack": 9950, "opponent_stacks": [9900], "to_call": 50,
             "min_raise": 200, "max_raise": 9950, "action_history": blinds()}
    for _ in range(50):
        out = player.decide(state, ["fold", "call", "raise"], 0)
        assert out["action"] in ("fold", "call", "raise")
        if out["action"] == "raise":
            assert 200 <= out["params"]["amount"] <= 9950
        assert out["record"]["solver"] == "100bb"
        assert out["record"]["effective_bb"] == 100.0


def test_a_three_bet_is_off_tree_under_one_raise_and_the_fallback_answers(player):
    # The first exhibition hand on 13 September: we opened to 200 with 9h3s,
    # the opponent made it 400. One raise per street has no entry here.
    state = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["9h", "3s"],
             "pot": 600, "your_stack": 9800, "opponent_stacks": [9600], "to_call": 200,
             "min_raise": 600, "max_raise": 9800,
             "action_history": blinds() + [entry(0, "raise", 200), entry(1, "raise", 400)]}
    out = player.decide(state, ["fold", "call", "raise"], 0)
    assert out["record"]["miss"] and out["record"]["fallback"]
    assert out["action"] == "fold", "the weakest bucket folds to a bet of a third of the pot"
    assert player.stats.fallbacks >= 1


def test_the_fallback_does_not_fold_the_strongest_hand(player):
    state = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["As", "Ah"],
             "pot": 600, "your_stack": 9800, "opponent_stacks": [9600], "to_call": 200,
             "min_raise": 600, "max_raise": 9800,
             "action_history": blinds() + [entry(0, "raise", 200), entry(1, "raise", 400)]}
    out = player.decide(state, ["fold", "call", "raise"], 0)
    assert out["record"]["fallback"]
    assert out["action"] == "raise"


def test_the_fallback_never_picks_an_action_the_arena_did_not_offer(player):
    state = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["As", "Ah"],
             "pot": 600, "your_stack": 9800, "opponent_stacks": [0], "to_call": 200,
             "min_raise": 0, "max_raise": 0,
             "action_history": blinds() + [entry(0, "raise", 200), entry(1, "raise", 400)]}
    out = player.decide(state, ["fold", "call"], 0)
    assert out["action"] == "call"


def test_warm_up_runs_every_rung_and_leaves_the_counters_clean(player):
    assert player.warm_up() >= 0.0
    assert player.stats.decisions == 0


def test_the_arena_s_results_rows_give_the_outcome():
    end = {"results": [{"seat": 0, "name": "NashForge", "net_chips": 10000, "final_stack": 20000},
                       {"seat": 1, "name": "PluriBot", "net_chips": -10000, "final_stack": 0}]}
    assert _outcome(end, 0) == "won"
    assert _outcome(end, 1) == "lost"
    assert _outcome(end, None) is None
    assert _outcome({"results": [{"seat": 0, "rank": 2}]}, 0) == "lost"


def test_the_gateway_path_is_joined_to_the_lobby_s_origin():
    assert _resolve("wss://chipzen.ai", "/ws/external/match/m/p") == "wss://chipzen.ai/ws/external/match/m/p"
    assert _resolve("wss://chipzen.ai", "wss://other/x") == "wss://other/x"


TAPER = os.path.join(ROOT, "results", "cfr", "nolimit_taper_42.pkl")


@pytest.fixture(scope="module")
def player_with_companion():
    return ArenaPlayer([SHIPPED], np.random.default_rng(3), companions=[TAPER])


def test_a_three_bet_is_answered_by_the_companion_before_the_rule(player_with_companion):
    state = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["As", "Ah"],
             "pot": 600, "your_stack": 9800, "opponent_stacks": [9600], "to_call": 200,
             "min_raise": 600, "max_raise": 9800,
             "action_history": blinds() + [entry(0, "raise", 200), entry(1, "raise", 400)]}
    out = player_with_companion.decide(state, ["fold", "call", "raise"], 0)
    assert out["record"]["miss"]
    assert out["record"]["companion"] == "100bb(4, 2)"
    assert not out["record"]["fallback"]
    assert player_with_companion.stats.companion_hits >= 1


def test_a_companion_too_far_in_depth_is_not_asked():
    player = _ladder(100)
    player.companions = [rung(100)]
    assert player.companion_for(60).depth_bb == 100
    assert player.companion_for(40) is None
