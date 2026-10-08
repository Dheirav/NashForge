"""
E6, "their three-bet holds": against a bot whose re-raise of our open never folds to our re-raise, a four-bet
keeps only a hand that is ahead of its re-raising range. Blueprint, 7 Oct: 0 folds to 86 four-bets, and it called
all 8 of our light 35bb jams. The solver's answer is forced to a jam here, so these test the rule and not a rung.
"""
import os

import numpy as np
import pytest

from abstraction.betting import ALL_IN
from chipzen.opponents import Profiles, _wilson_upper
from chipzen.player import ArenaPlayer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHIPPED = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")

# Blueprint's two nodes as the profiles held them on 7 Oct: our opens answered, and its answers to our four-bet.
HOLDS = {"preflop:Ur": {"call": 1124, "fold": 1917, "raise": 525}, "preflop:UrTrUr": {"call": 73, "raise": 13}}
# hoops' shape on twice its sample: it folds to a four-bet about one time in nine (hoops itself, 3 of 28, is under
# FOUR_BET_MIN, so it would not show the fold bound working).
FOLDS_SOMETIMES = {"preflop:Ur": {"call": 1680, "fold": 693, "raise": 229},
                   "preflop:UrTrUr": {"call": 38, "fold": 6, "raise": 12}}


def profiles(tmp_path, by_history, scout_reads=True):
    p = Profiles(str(tmp_path / "opp.json"), scout_reads=scout_reads)
    p.rows["villain"] = {"bets_faced": 0, "hands": 3000, "folds": 0, "calls": 0, "raises": 0, "by_history": by_history}
    return p


def test_wilson_is_not_zero_at_zero_folds_and_shrinks_with_the_sample():
    assert 0.0 < _wilson_upper(0, 300) < _wilson_upper(0, 86) < _wilson_upper(0, 30)
    assert _wilson_upper(0, 86) == pytest.approx(0.043, abs=0.002)
    assert _wilson_upper(3, 28) > 0.25


def test_the_read_fires_on_a_three_bet_that_holds_and_returns_its_re_raise_floor(tmp_path):
    p = profiles(tmp_path, HOLDS)
    assert p.three_bets_hold("villain") == pytest.approx(p.reraise_floor("villain"))
    assert 0.12 < p.three_bets_hold("villain") < 0.15


def test_the_fold_bound_is_where_the_read_turns(tmp_path):
    ur = HOLDS["preflop:Ur"]
    assert profiles(tmp_path, {"preflop:Ur": ur, "preflop:UrTrUr": {"call": 99, "fold": 1}}).three_bets_hold("villain")
    assert profiles(tmp_path, {"preflop:Ur": ur, "preflop:UrTrUr": {"call": 95, "fold": 5}}) \
        .three_bets_hold("villain") is None


def test_the_read_stays_off_for_a_folder_a_small_sample_and_without_scout_reads(tmp_path):
    assert profiles(tmp_path, FOLDS_SOMETIMES).three_bets_hold("villain") is None
    # With no fold at all the bound itself needs about 35 answers (0 of 34 is 0.102), so a small sample is off.
    few = dict(HOLDS, **{"preflop:UrTrUr": {"call": 34}})
    assert profiles(tmp_path, few).three_bets_hold("villain") is None
    assert profiles(tmp_path, dict(HOLDS, **{"preflop:UrTrUr": {"call": 36}})).three_bets_hold("villain")
    assert profiles(tmp_path, HOLDS, scout_reads=False).three_bets_hold("villain") is None
    assert profiles(tmp_path, HOLDS).three_bets_hold("nobody") is None


@pytest.fixture(scope="module")
def player():
    return ArenaPlayer([SHIPPED], np.random.default_rng(3))


def blinds():
    return [{"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop", "is_timeout": False},
            {"seat": 1, "action": "post_big_blind", "amount": 100, "phase": "preflop", "is_timeout": False}]


def entry(seat, action, amount):
    return {"seat": seat, "action": action, "amount": amount, "phase": "preflop", "is_timeout": False}


def spot(hole, three_bet_to=400, stack=3500, opened_by_us=True):
    """35bb: we open to 200 from the button and they re-raise; we act."""
    lines = [entry(0, "raise", 200), entry(1, "raise", three_bet_to)] if opened_by_us else \
        [entry(0, "call", 50), entry(1, "raise", three_bet_to)]
    ours = 200 if opened_by_us else 100
    return {"hand_number": 7, "phase": "preflop", "board": [], "your_hole_cards": hole,
            "pot": ours + three_bet_to, "your_stack": stack - ours, "opponent_stacks": [stack - three_bet_to],
            "to_call": three_bet_to - ours, "min_raise": 2 * three_bet_to, "max_raise": stack - ours,
            "action_history": blinds() + lines}


@pytest.fixture
def jamming(player, tmp_path, monkeypatch):
    """The player with every rung forced to jam, a Blueprint-shaped profile, and the rule on."""
    for solver in player.ladder:
        monkeypatch.setattr(solver, "agent", lambda *args, **kwargs: ALL_IN)
    player.profiles, player.opponent, player.threebet_holds = profiles(tmp_path, HOLDS), "villain", True
    yield player
    player.profiles, player.opponent, player.threebet_holds = None, None, False


def test_a_weak_ace_does_not_jam_over_a_three_bet_that_holds_and_calls_at_a_good_price(jamming):
    # A5o has 0.36 against the top 13.6%; the call is 200 into 600, a price of 0.25.
    out = jamming.decide(spot(["Ah", "5c"]), ["fold", "call", "raise"], 0)
    assert out["action"] == "call"
    assert out["record"]["adjusted"] == "their three-bet holds"


def test_a_weak_ace_folds_when_the_price_is_beyond_its_equity(jamming):
    # A three-bet to 1,100: the call is 900 into 1,300, a price of 0.41 against 0.36.
    out = jamming.decide(spot(["Ah", "2c"], three_bet_to=1100), ["fold", "call", "raise"], 0)
    assert out["action"] == "fold"
    assert out["record"]["adjusted"] == "their three-bet holds"


def test_a_hand_ahead_of_the_range_keeps_its_jam(jamming):
    for hole in (["Qh", "Qc"], ["Ah", "Kc"], ["9h", "9c"]):
        out = jamming.decide(spot(hole), ["fold", "call", "raise"], 0)
        assert out["action"] == "raise", hole
        assert out["record"]["adjusted"] != "their three-bet holds"


def test_off_by_default_and_off_against_a_three_bettor_that_folds(jamming, tmp_path):
    jamming.threebet_holds = False
    assert jamming.decide(spot(["Ah", "5c"]), ["fold", "call", "raise"], 0)["action"] == "raise"
    jamming.threebet_holds = True
    jamming.profiles = profiles(tmp_path, FOLDS_SOMETIMES)
    assert jamming.decide(spot(["Ah", "5c"]), ["fold", "call", "raise"], 0)["action"] == "raise"


def test_only_our_open_re_raised_and_only_deep(jamming):
    # We limped and they raised: not a three-bet of our open.
    assert jamming.decide(spot(["Ah", "5c"], opened_by_us=False), ["fold", "call", "raise"], 0)["action"] == "raise"
    # 15bb: the short rungs know the ranges, as for every shove rule.
    assert jamming.decide(spot(["Ah", "5c"], three_bet_to=400, stack=1500), ["fold", "call", "raise"], 0)["action"] \
        == "raise"
