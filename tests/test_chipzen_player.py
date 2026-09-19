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


def test_the_companion_s_shove_with_a_middling_hand_becomes_a_call(player_with_companion):
    # 13 September, hand 3 against mr_hide: T9 on A-T-4 facing a bet after a
    # three-bet. The companion's only raises are huge; a shove here is taken as
    # "raise" and softened to a call unless the hand is in the top bucket.
    state = {"hand_number": 3, "phase": "flop", "board": ["Ah", "Tc", "4s"],
             "your_hole_cards": ["Ts", "9h"], "pot": 1627, "your_stack": 7175,
             "opponent_stacks": [11725], "to_call": 577, "min_raise": 1154, "max_raise": 7175,
             "action_history": blinds() + [entry(0, "raise", 200), entry(1, "raise", 525),
                                           entry(0, "call", 525), entry(1, "raise", 577, "flop")]}
    shoves = 0
    for _ in range(40):
        out = player_with_companion.decide(state, ["fold", "call", "raise"], 0)
        assert out["record"]["companion"] or out["record"]["fallback"]
        shoves += out["action"] == "raise" and out["params"]["amount"] == 7175
    assert shoves == 0


def test_a_station_is_only_believed_after_enough_bets(tmp_path):
    from chipzen.opponents import MIN_OBSERVED, Profiles
    profiles = Profiles(str(tmp_path / "opp.json"))
    hand = {"action_history": blinds() + [entry(0, "raise", 300), entry(1, "call", 300),
                                          entry(1, "check", 0, "flop"), entry(0, "raise", 600, "flop"),
                                          entry(1, "call", 600, "flop")]}
    for _ in range(MIN_OBSERVED // 2 - 1):
        profiles.observe(hand, 0, "station")
    assert profiles.fold_to_bet("station")[0] is None
    assert not profiles.never_folds("station")
    profiles.observe(hand, 0, "station")
    rate, n = profiles.fold_to_bet("station")
    assert n == MIN_OBSERVED and rate == 0.0
    assert profiles.never_folds("station")
    profiles.save()
    assert Profiles(str(tmp_path / "opp.json")).rows["station"]["bets_faced"] == MIN_OBSERVED


def test_only_the_opponent_s_answers_to_our_bets_are_counted():
    from chipzen.opponents import Profiles
    profiles = Profiles("/nonexistent/opp.json")
    # They raise, we call: nothing to count. Then we bet the flop and they fold.
    hand = {"action_history": blinds() + [entry(1, "raise", 300), entry(0, "call", 300),
                                          entry(0, "raise", 600, "flop"), entry(1, "fold", 0, "flop")]}
    profiles.observe(hand, 0, "x")
    counted = {k: v for k, v in profiles.rows["x"].items() if k not in ("net", "by_history")}
    assert counted == {"bets_faced": 1, "folds": 1, "calls": 0, "raises": 0, "hands": 1}


def test_a_bluff_is_withheld_against_a_station_but_a_value_bet_is_not(player):
    from chipzen.opponents import Profiles
    player.profiles = Profiles("/nonexistent/opp.json")
    player.profiles.rows["station"] = {"bets_faced": 500, "folds": 10, "calls": 490, "raises": 0, "hands": 300}
    player.opponent = "station"
    try:
        weak = {"hand_number": 1, "phase": "flop", "board": ["Qc", "9s", "Kd"], "your_hole_cards": ["3h", "2c"],
                "pot": 400, "your_stack": 9800, "opponent_stacks": [9800], "to_call": 0,
                "min_raise": 100, "max_raise": 9800,
                "action_history": blinds() + [entry(0, "raise", 200), entry(1, "call", 200),
                                              entry(1, "check", 0, "flop")]}
        strong = dict(weak, your_hole_cards=["Kc", "Kh"])
        weak_raises = sum(player.decide(weak, ["check", "raise"], 0)["action"] == "raise" for _ in range(60))
        strong_raises = sum(player.decide(strong, ["check", "raise"], 0)["action"] == "raise" for _ in range(60))
        assert weak_raises == 0
        assert strong_raises > 0
        assert player.stats.bluffs_withheld > 0
    finally:
        player.profiles = None
        player.opponent = None


def test_a_fold_or_raise_bot_s_shove_is_called_only_by_the_top_class(player_with_companion):
    from chipzen.opponents import Profiles
    player = player_with_companion
    player.profiles = Profiles("/nonexistent/opp.json")
    player.profiles.rows["jammer"] = {"bets_faced": 300, "folds": 200, "calls": 30, "raises": 70, "hands": 300}
    player.opponent = "jammer"
    try:
        # KQ facing a three-bet shove, the shape of hand 22 against Blueprint
        # on 14 September; on the companion's tree, so the solver answers.
        state = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["Kh", "Qd"],
                 "pot": 10175, "your_stack": 9275, "opponent_stacks": [0], "to_call": 9275,
                 "min_raise": 0, "max_raise": 0,
                 "action_history": blinds() + [entry(0, "raise", 450), entry(1, "raise", 10000)]}
        outs = [player.decide(state, ["fold", "call"], 0) for _ in range(40)]
        # Folded every time: by the solver itself or by the rule, either is the point.
        assert all(o["action"] == "fold" for o in outs)
        aces = dict(state, your_hole_cards=["As", "Ah"])
        assert player.decide(aces, ["fold", "call"], 0)["action"] == "call"
    finally:
        player.profiles = None
        player.opponent = None


def test_the_rule_folds_a_middling_hand_to_a_pot_sized_bet(player):
    # Queen high facing a shove at an off-tree node, no profile: the rule folds.
    state = {"hand_number": 5, "phase": "turn", "board": ["6s", "5h", "Js", "5s"], "your_hole_cards": ["Qd", "9h"],
             "pot": 10250, "your_stack": 9050, "opponent_stacks": [0], "to_call": 9050,
             "min_raise": 0, "max_raise": 0,
             "action_history": blinds() + [entry(0, "call", 100), entry(1, "check", 0),
                                           entry(1, "check", 0, "flop"), entry(0, "raise", 100, "flop"), entry(1, "call", 100, "flop"),
                                           entry(1, "raise", 100, "turn"), entry(0, "raise", 400, "turn"), entry(1, "raise", 9500, "turn")]}
    out = player.decide(state, ["fold", "call"], 0)
    assert out["record"]["fallback"] or out["record"]["companion"]
    if out["record"]["fallback"]:
        assert out["action"] == "fold"


def test_the_strength_read_is_a_class_of_six_even_with_a_lossless_preflop(player):
    """
    With 169 preflop classes the solver's bucket for AA is 168; the player's
    rules compare against `_top`, which is 5. The read has to be the coarse
    class or every preflop hand outranks the threshold.
    """
    from abstraction.buckets import CardAbstraction
    from chipzen.player import ArenaPlayer, Solver
    from slumbot.bridge import parse_cards
    abstraction = CardAbstraction(preflop_buckets=169, postflop_buckets=6,
                                  samples=60, equity_samples=8).fit(np.random.default_rng(0))
    solver = Solver(path="lossless", depth_bb=100, schedule=1, strategy={}, abstraction=abstraction)
    from chipzen.player import strength_class
    top = ArenaPlayer._top(solver)
    assert strength_class(solver.abstraction, parse_cards(["As", "Ah"]), []) == top
    assert strength_class(solver.abstraction, parse_cards(["Kh", "Qd"]), []) < top
    assert strength_class(solver.abstraction, parse_cards(["7h", "2d"]), []) == 0


def test_the_shove_rule_leaves_short_stacks_to_the_solver(player_with_companion):
    """
    Against Blueprint's revealed cards on 15 September, every one of the
    rule's 70 folds that cost chips was under 20bb effective, where that bot
    shoves any two cards and the short rungs' calling ranges are right. Deep,
    the rule stays.
    """
    from chipzen.opponents import Profiles
    player = player_with_companion
    player.profiles = Profiles("/nonexistent/opp.json")
    player.profiles.rows["jammer"] = {"bets_faced": 300, "folds": 200, "calls": 30, "raises": 70, "hands": 300}
    player.opponent = "jammer"
    try:
        # 15bb effective: a shove for 1,400 more over our 100 blind. The rule must not fire.
        short = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["Kh", "Qd"],
                 "pot": 1650, "your_stack": 1400, "opponent_stacks": [0], "to_call": 1400,
                 "min_raise": 0, "max_raise": 0,
                 "action_history": blinds() + [entry(0, "raise", 1500)]}
        outs = [player.decide(short, ["fold", "call"], 1) for _ in range(20)]
        assert all(o["record"]["adjusted"] is None for o in outs)
        assert all(o["record"]["effective_bb"] < 20 for o in outs)
        # 92bb effective, the situation the rule was written for: it still fires.
        deep = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["Kh", "Qd"],
                "pot": 10175, "your_stack": 9275, "opponent_stacks": [0], "to_call": 9275,
                "min_raise": 0, "max_raise": 0,
                "action_history": blinds() + [entry(0, "raise", 450), entry(1, "raise", 10000)]}
        outs = [player.decide(deep, ["fold", "call"], 0) for _ in range(20)]
        assert all(o["action"] == "fold" for o in outs)
    finally:
        player.profiles = None
        player.opponent = None



def test_an_opponent_all_in_for_a_fraction_of_a_blind_is_called(player):
    """
    14 September, blinds 100/200: villain shoved to 212 over our 200 blind, 12
    into 412, and the 5bb blueprint folded T5o. Any two cards call at 33 to 1.
    """
    st = {"hand_number": 58, "phase": "preflop", "board": [], "your_hole_cards": ["Th", "5d"],
          "pot": 412, "your_stack": 19588, "opponent_stacks": [0], "to_call": 12,
          "min_raise": 0, "max_raise": 0,
          "action_history": [{"seat": 1, "action": "post_small_blind", "amount": 100, "phase": "preflop"},
                             {"seat": 0, "action": "post_big_blind", "amount": 200, "phase": "preflop"},
                             {"seat": 1, "action": "raise", "amount": 212, "phase": "preflop"}]}
    outs = [player.decide(st, ["fold", "call"], 0) for _ in range(20)]
    assert all(o["action"] == "call" for o in outs)


def test_the_last_resort_guard_prefers_the_passive_action(player):
    from chipzen.bridge import legal_mask, replay
    import numpy as np
    # If the chosen action is illegal and check is available, the guard must not fold.
    st = {"hand_number": 1, "phase": "flop", "board": ["Qs", "7h", "3d"], "your_hole_cards": ["As", "Kh"],
          "pot": 400, "your_stack": 9800, "opponent_stacks": [9800], "to_call": 0,
          "min_raise": 200, "max_raise": 9800,
          "action_history": blinds() + [entry(0, "raise", 200), entry(1, "call", 100)]}
    outs = [player.decide(st, ["check", "raise"], 1) for _ in range(20)]
    assert all(o["action"] in ("check", "raise") for o in outs)


def test_the_bluff_rule_folds_rather_than_calls_when_facing_a_bet(player):
    from chipzen.opponents import Profiles
    player.profiles = Profiles("/nonexistent/opp.json")
    player.profiles.rows["station"] = {"bets_faced": 500, "folds": 10, "calls": 490, "raises": 0, "hands": 300}
    player.opponent = "station"
    try:
        st = {"hand_number": 1, "phase": "river", "board": ["Qs", "7h", "3d", "2c", "9s"], "your_hole_cards": ["6h", "4h"],
              "pot": 600, "your_stack": 9400, "opponent_stacks": [9200], "to_call": 200,
              "min_raise": 400, "max_raise": 9400,
              "action_history": blinds() + [entry(0, "call", 50), entry(1, "check", 0),
                                            entry(1, "check", 0, "flop"), entry(0, "check", 0, "flop"),
                                            entry(1, "check", 0, "turn"), entry(0, "check", 0, "turn"),
                                            entry(1, "raise", 200, "river")]}
        outs = [player.decide(st, ["fold", "call", "raise"], 0) for _ in range(40)]
        withheld = [o for o in outs if o["record"]["adjusted"] == "bluff withheld"]
        assert all(o["action"] == "fold" for o in withheld)
    finally:
        player.profiles = None
        player.opponent = None



def test_the_rejection_fallback_never_calls_a_stack_off_by_accident():
    from chipzen.client import _rejection_fallback
    assert _rejection_fallback(["check", "fold"], 1) == "check"
    assert _rejection_fallback(["fold", "call", "raise"], 1) == "fold"     # fold before call
    assert _rejection_fallback(["call", "raise"], 1) == "call"
    assert _rejection_fallback(None, 1) == "check"
    assert _rejection_fallback(["fold", "call"], 2) == "fold"              # the second rejection stops the loop


def test_a_folding_blind_is_opened_with_the_minimum_raise(player):
    from chipzen.opponents import Profiles
    player.profiles = Profiles("/nonexistent/opp.json", scout_reads=True)
    player.profiles.rows["nit"] = {"bets_faced": 908, "folds": 688, "calls": 141, "raises": 79, "hands": 2053,
                                   "by_history": {"preflop:Ur": {"fold": 497, "call": 100, "raise": 34}},
                                   "river_bets": 63, "river_bluffs": 5}
    player.opponent = "nit"
    try:
        # Seven-deuce on the button: the solver folds it; the read opens it for the minimum.
        st = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["7h", "2d"],
              "pot": 150, "your_stack": 9950, "opponent_stacks": [9900], "to_call": 50,
              "min_raise": 200, "max_raise": 9950, "action_history": blinds()}
        outs = [player.decide(st, ["fold", "call", "raise"], 0) for _ in range(30)]
        assert all(o["action"] != "fold" for o in outs)
        opened = [o for o in outs if o["record"]["adjusted"] == "opened into a folding blind"]
        assert opened and all(o["params"]["amount"] == 200 for o in opened)
    finally:
        player.profiles = None
        player.opponent = None


def test_a_never_bluffer_s_river_bet_is_believed_below_the_top_two_classes(player):
    from chipzen.opponents import Profiles
    player.profiles = Profiles("/nonexistent/opp.json", scout_reads=True)
    player.profiles.rows["honest"] = {"bets_faced": 470, "folds": 125, "calls": 306, "raises": 39, "hands": 574,
                                      "by_history": {}, "river_bets": 63, "river_bluffs": 0}
    player.opponent = "honest"
    try:
        st = {"hand_number": 1, "phase": "river", "board": ["Qs", "7h", "3d", "2c", "9s"], "your_hole_cards": ["Ah", "4h"],
              "pot": 1200, "your_stack": 9000, "opponent_stacks": [8600], "to_call": 400,
              "min_raise": 800, "max_raise": 9000,
              "action_history": blinds() + [entry(0, "call", 50), entry(1, "check", 0),
                                            entry(1, "check", 0, "flop"), entry(0, "check", 0, "flop"),
                                            entry(1, "check", 0, "turn"), entry(0, "check", 0, "turn"),
                                            entry(1, "raise", 400, "river")]}
        outs = [player.decide(st, ["fold", "call", "raise"], 0) for _ in range(30)]
        believed = [o for o in outs if o["record"]["adjusted"] == "river bet believed"]
        assert believed and all(o["action"] == "fold" for o in believed)
        # With the read off, nothing is believed.
        player.profiles.scout_reads = False
        assert all(o["record"]["adjusted"] != "river bet believed" for o in [player.decide(st, ["fold", "call", "raise"], 0) for _ in range(10)])
    finally:
        player.profiles = None
        player.opponent = None


def test_a_sizing_tell_folds_to_the_big_bet_and_calls_the_small_one(player):
    from chipzen.opponents import Profiles
    player.profiles = Profiles("/nonexistent/opp.json", scout_reads=True)
    player.profiles.rows["poet"] = {"bets_faced": 966, "folds": 234, "calls": 581, "raises": 151, "hands": 1362,
                                    "by_history": {}, "big_bets": 429, "big_bets_air": 0,
                                    "small_bets": 1080, "small_bets_air": 421}
    player.opponent = "poet"
    try:
        base = {"hand_number": 1, "phase": "flop", "board": ["Qs", "7h", "3d"], "your_hole_cards": ["9h", "8h"],
                "your_stack": 9600, "opponent_stacks": [9200], "min_raise": 1200, "max_raise": 9600,
                "action_history": blinds() + [entry(0, "call", 50), entry(1, "check", 0),
                                              entry(1, "raise", 200, "flop")]}
        # Their pot-sized bet (200 into 200): nine-high folds every time.
        big = dict(base, pot=400, to_call=200)
        outs = [player.decide(big, ["fold", "call", "raise"], 0) for _ in range(20)]
        assert all(o["action"] == "fold" for o in outs)
        assert any(o["record"]["adjusted"] == "big bet believed" for o in outs)
        # Their half-pot bet (100 into 200): a middling hand does not fold.
        small = dict(base, pot=300, to_call=100,
                     action_history=base["action_history"][:-1] + [entry(1, "raise", 100, "flop")],
                     your_hole_cards=["Qd", "9c"])
        outs = [player.decide(small, ["fold", "call", "raise"], 0) for _ in range(20)]
        assert all(o["action"] != "fold" for o in outs)
    finally:
        player.profiles = None
        player.opponent = None


def test_a_fold_to_an_open_becomes_a_small_three_bet_against_a_bot_that_folds_to_them(player):
    from chipzen.opponents import Profiles
    player.profiles = Profiles("/nonexistent/opp.json", scout_reads=True)
    player.profiles.rows["nit"] = {"bets_faced": 908, "folds": 688, "calls": 141, "raises": 79, "hands": 2053,
                                   "by_history": {"preflop:TrUr": {"fold": 25, "call": 3, "raise": 1}},
                                   "river_bets": 63, "river_bluffs": 5}
    player.opponent = "nit"
    try:
        # Seven-deuce in the big blind facing a 2.5x open at 100bb: the solver folds; the read three-bets small.
        st = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["7h", "2d"],
              "pot": 350, "your_stack": 9900, "opponent_stacks": [9750], "to_call": 150,
              "min_raise": 400, "max_raise": 9900,
              "action_history": blinds() + [entry(0, "raise", 250)]}
        outs = [player.decide(st, ["fold", "call", "raise"], 1) for _ in range(30)]
        assert all(o["action"] != "fold" for o in outs)
        assert any(o["record"]["adjusted"] == "three-bet into a folder" for o in outs)
        # Short, the read stays off: a three-bet there commits the stack.
        short = dict(st, your_stack=2400, opponent_stacks=[2250], max_raise=2400)
        outs = [player.decide(short, ["fold", "call", "raise"], 1) for _ in range(20)]
        assert all(o["record"]["adjusted"] != "three-bet into a folder" for o in outs)
    finally:
        player.profiles = None
        player.opponent = None


def test_a_river_shove_is_handed_to_the_companion_only_when_asked():
    # v7b's burst, 19 September: K3 called 6,350 on the river with a pair of
    # threes, K8 5,168 into jacks. The one-raise primary's river node was solved
    # in a game where nobody can re-raise, so a shove there reads bluff-heavy
    # and its calling range is wide. With the flag the companion answers a
    # river all-in even though the primary has a node; without it nothing
    # changes, and the record says which happened.
    state = {"hand_number": 9, "phase": "river", "board": ["3s", "Jc", "8s", "8h", "Qd"],
             "your_hole_cards": ["Kd", "3d"], "pot": 9550, "your_stack": 7950,
             "opponent_stacks": [0], "to_call": 6350, "min_raise": 7950, "max_raise": 7950,
             "action_history": blinds() + [entry(1, "raise", 200), entry(0, "call", 200),
                                           entry(0, "check", 0, "flop"), entry(1, "check", 0, "flop"),
                                           entry(0, "raise", 800, "turn"), entry(1, "call", 800, "turn"),
                                           entry(0, "check", 0, "river"), entry(1, "raise", 6350, "river")]}
    plain = ArenaPlayer([SHIPPED], np.random.default_rng(3), companions=[TAPER])
    out = plain.decide(state, ["fold", "call"], 0)
    assert out["record"]["adjusted"] is None and out["record"]["companion"] is None
    handed = ArenaPlayer([SHIPPED], np.random.default_rng(3), companions=[TAPER],
                         river_shove_companion=True)
    seen = set()
    for _ in range(20):
        out = handed.decide(state, ["fold", "call"], 0)
        assert out["action"] in ("fold", "call")
        if out["record"]["companion"]:
            assert out["record"]["adjusted"].startswith("river shove:")
            seen.add(out["action"])
    assert handed.stats.river_shoves_to_companion > 0, "the companion was never asked"
