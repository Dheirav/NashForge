"""
The small-raise defence: facing a small preflop re-raise of our raise, a fold the price pays for becomes a call.
Traced LBR (8 Oct) found the exploiter folding 79% of its range to re-raises this small at 70bb, and the balanced set
67% at 35bb, against a limit near 20%. The solver's answer is forced to a fold here, so these test the rule.
"""
import os

import numpy as np
import pytest

from abstraction.betting import FOLD
from chipzen.opponents import Profiles
from chipzen.player import ArenaPlayer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHIPPED = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")


@pytest.fixture(scope="module")
def player():
    return ArenaPlayer([SHIPPED], np.random.default_rng(3))


def blinds():
    return [{"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop", "is_timeout": False},
            {"seat": 1, "action": "post_big_blind", "amount": 100, "phase": "preflop", "is_timeout": False}]


def entry(seat, action, amount):
    return {"seat": seat, "action": action, "amount": amount, "phase": "preflop", "is_timeout": False}


def spot(hole, lines, ours_in, theirs_in, stack=7000):
    """We are seat 0; `lines` are the preflop actions after the blinds, and the last is their raise."""
    return {"hand_number": 5, "phase": "preflop", "board": [], "your_hole_cards": hole,
            "pot": ours_in + theirs_in, "your_stack": stack - ours_in, "opponent_stacks": [stack - theirs_in],
            "to_call": theirs_in - ours_in, "min_raise": 2 * theirs_in, "max_raise": stack - ours_in,
            "action_history": blinds() + lines}


# 70bb: we open to 200, they re-raise to 400. The call is 200 into 600: a price of 0.25.
MIN_THREE_BET = ([entry(0, "raise", 200), entry(1, "raise", 400)], 200, 400)
# The same open re-raised to 1,000: 800 into 1,200, a price of 0.40, which is not a small raise.
BIG_THREE_BET = ([entry(0, "raise", 200), entry(1, "raise", 1000)], 200, 1000)


@pytest.fixture
def folding(player, monkeypatch, tmp_path):
    for solver in player.ladder:
        monkeypatch.setattr(solver, "agent", lambda *args, **kwargs: FOLD)
    player.small_raise_defence = True
    player.profiles = Profiles(str(tmp_path / "opp.json"), scout_reads=True)
    player.opponent = "villain"
    yield player
    player.small_raise_defence = False
    player.profiles, player.opponent = None, None


def decide(player, hole, case):
    lines, ours, theirs = case
    return player.decide(spot(hole, lines, ours, theirs), ["fold", "call", "raise"], 0)


def test_a_playable_hand_calls_a_small_re_raise_and_trash_still_folds(folding):
    out = decide(folding, ["7h", "6h"], MIN_THREE_BET)          # 0.36 against the top quarter, 0.29 realised
    assert out["action"] == "call" and out["record"]["adjusted"] == "small raise defended"
    assert decide(folding, ["7h", "2c"], MIN_THREE_BET)["action"] == "fold"     # 0.23 realised, under 0.25


def test_a_big_re_raise_is_left_alone(folding):
    # 99 has 0.58 against the top quarter, 0.46 realised, which would pay a price of 0.40: only the size limit stops it.
    out = decide(folding, ["9h", "9c"], BIG_THREE_BET)
    assert out["action"] == "fold" and out["record"]["adjusted"] != "small raise defended"


def test_a_second_re_raise_reads_a_tighter_range(folding):
    # They open to 200, we three-bet to 600, they four-bet to 1,200: 600 into 1,800, a price of 0.25, top tenth.
    four_bet = ([entry(1, "raise", 200), entry(0, "raise", 600), entry(1, "raise", 1200)], 600, 1200)
    assert decide(folding, ["Ah", "2c"], four_bet)["action"] == "fold"          # 0.30 against the top tenth: 0.24
    assert decide(folding, ["Qh", "Jh"], four_bet)["action"] == "call"          # 0.40: 0.32


def test_only_a_re_raise_of_our_raise_and_only_deep(folding):
    limped = ([entry(0, "call", 100), entry(1, "raise", 200)], 100, 200)        # we limped and they raised small (0.25)
    assert decide(folding, ["Kh", "9c"], limped)["action"] == "fold"
    lines, ours, theirs = MIN_THREE_BET
    short = folding.decide(spot(["Kh", "9c"], lines, ours, theirs, stack=1500), ["fold", "call", "raise"], 0)
    assert short["action"] == "fold"                                             # 15bb: the short rungs decide


def test_a_measured_re_raiser_s_range_is_used(folding):
    # A bot that re-raises 75% of opens has a wide range, so a hand that folds against the default top quarter calls.
    folding.profiles.rows["villain"] = {"hands": 400, "bets_faced": 0, "folds": 0, "calls": 0, "raises": 0,
                                        "by_history": {"preflop:Ur": {"call": 20, "fold": 30, "raise": 150}}}
    assert decide(folding, ["7h", "2c"], MIN_THREE_BET)["action"] == "call"


def test_off_by_default(player, monkeypatch):
    for solver in player.ladder:
        monkeypatch.setattr(solver, "agent", lambda *args, **kwargs: FOLD)
    assert player.small_raise_defence is False
    assert decide(player, ["7h", "6h"], MIN_THREE_BET)["action"] == "fold"
