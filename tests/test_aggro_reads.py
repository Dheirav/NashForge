"""The two aggressive-side reads: an over-bluffer on the river and an over-folder after the flop."""
import json

import pytest

from chipzen.opponents import OVER_BLUFF_MIN, OVER_FOLD_MIN, Profiles, _lower_bound


def profiles(tmp_path, rows, scout_reads=True):
    path = tmp_path / "opponents.json"
    path.write_text(json.dumps(rows))
    return Profiles(str(path), scout_reads=scout_reads)


def test_lower_bound_is_below_the_rate_and_never_negative_in_use():
    assert _lower_bound(23, 48) < 23 / 48
    assert _lower_bound(0, 0) == 0.0


def test_river_bluff_floor_needs_a_sample(tmp_path):
    p = profiles(tmp_path, {"few": {"river_bets": OVER_BLUFF_MIN - 1, "river_bluffs": 30},
                            "shadow": {"river_bets": 48, "river_bluffs": 23}})
    assert p.river_bluff_floor("few") is None
    assert p.river_bluff_floor("shadow") == pytest.approx(_lower_bound(23, 48))
    assert p.river_bluff_floor("nobody") is None


def test_river_bluff_floor_is_off_without_scout_reads(tmp_path):
    p = profiles(tmp_path, {"shadow": {"river_bets": 48, "river_bluffs": 23}}, scout_reads=False)
    assert p.river_bluff_floor("shadow") is None


def test_an_honest_bettor_has_a_floor_of_zero(tmp_path):
    p = profiles(tmp_path, {"runner1": {"river_bets": 63, "river_bluffs": 0}})
    assert p.river_bluff_floor("runner1") == 0.0


def by_history(fold, call, raise_):
    half = lambda x: x // 2
    return {"flop:Ur": {"fold": half(fold), "call": half(call), "raise": half(raise_)},
            "turn:TcUr": {"fold": fold - half(fold), "call": call - half(call), "raise": raise_ - half(raise_)}}


def test_postflop_fold_floor_pools_flop_and_turn(tmp_path):
    p = profiles(tmp_path, {"folder": {"by_history": by_history(80, 15, 5)}})
    assert p.postflop_fold_floor("folder") == pytest.approx(_lower_bound(80, 100))


def test_postflop_fold_floor_refuses_a_raiser_and_a_small_sample(tmp_path):
    p = profiles(tmp_path, {"raiser": {"by_history": by_history(60, 20, 20)},
                            "few": {"by_history": by_history(OVER_FOLD_MIN // 2, 10, 0)}})
    assert p.postflop_fold_floor("raiser") is None
    assert p.postflop_fold_floor("few") is None


def test_preflop_and_river_answers_do_not_count(tmp_path):
    rows = {"x": {"by_history": {"preflop:Ur": {"fold": 500}, "river:Ur": {"fold": 500},
                                 "flop:Ur": {"call": 50}}}}
    assert profiles(tmp_path, rows).postflop_fold_floor("x") is None


def test_reraise_floor_reads_the_answers_to_our_opens(tmp_path):
    from chipzen.opponents import RERAISE_MIN
    rows = {"v003": {"by_history": {"preflop:Ur": {"raise": 44, "call": 30, "fold": 26}}},
            "few": {"by_history": {"preflop:Ur": {"raise": RERAISE_MIN - 1}}}}
    p = profiles(tmp_path, rows)
    assert p.reraise_floor("v003") == pytest.approx(_lower_bound(44, 100))
    assert p.reraise_floor("few") is None
    assert profiles(tmp_path, rows, scout_reads=False).reraise_floor("v003") is None


def test_range_equity_orders_hands_sensibly():
    from chipzen.ranges import equity_vs_top
    aces, trash = [12, 38], [5, 13]            # Ac Ad against 7c 2d, by index
    assert equity_vs_top(aces, 0.4) > 0.8
    assert equity_vs_top(trash, 0.4) < 0.36
    assert equity_vs_top([11, 24], 0.4) > equity_vs_top([11, 24], 0.1)   # a looser range is easier to call
