"""
The posterior reads (`Profiles(posteriors=True)`): the population prior, the bounds, the
within-match correction, each read on synthetic rows, and the size-aware bluff rule.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstraction.betting import ALL_IN, RAISE_HALF, RAISE_POT, RAISE_TWO  # noqa: E402
from chipzen import opponents as op  # noqa: E402
from chipzen.opponents import Profiles, _upper_bound, design_effect, fit_prior  # noqa: E402
from chipzen.player import ArenaPlayer  # noqa: E402

#: Fold-to-bet rates of a field like the real one (0.11 to 0.77 on 5 Oct), each over 2,000 bets.
FIELD_FOLDS = (0.12, 0.2, 0.25, 0.3, 0.35, 0.38, 0.4, 0.42, 0.45, 0.5, 0.55, 0.6, 0.7)


def bot(fold=0.4, bets=2000, call_share=0.75, hands=None, **extra):
    folds = int(round(fold * bets))
    calls = int(round(call_share * (bets - folds)))
    row = {"bets_faced": bets, "folds": folds, "calls": calls, "raises": bets - folds - calls,
           "hands": hands if hands is not None else 2 * bets, "net": 0, "by_history": {}}
    row.update(extra)
    return row


def field(posteriors=True, **flags):
    p = Profiles("/nonexistent/opponents.json", posteriors=posteriors, **flags)
    p.rows = {f"f{i}": bot(f, call_share=0.55 + 0.03 * i) for i, f in enumerate(FIELD_FOLDS)}
    return p


# ---------------------------------------------------------------------------------------------- prior

def test_the_prior_mean_is_the_field_s_and_its_strength_follows_the_spread():
    mean, strength = fit_prior(field().rows, "fold_to_bet")
    assert mean == pytest.approx(sum(FIELD_FOLDS) / len(FIELD_FOLDS), abs=0.01)
    # A spread this wide (sd about 0.16) is a weak prior, a few pseudo-trials, not hundreds.
    assert op.PRIOR_MIN_STRENGTH <= strength < 15


def test_a_field_that_looks_alike_is_a_strong_prior_but_capped():
    rows = {f"b{i}": bot(0.40, bets=5000) for i in range(10)}
    mean, strength = fit_prior(rows, "fold_to_bet")
    assert mean == pytest.approx(0.40, abs=0.005)
    assert strength == op.PRIOR_MAX_STRENGTH


def test_a_wildly_mixed_field_is_held_at_the_floor():
    rows = {f"b{i}": bot(f, bets=5000) for i, f in enumerate((0.02, 0.98, 0.03, 0.97, 0.05, 0.95))}
    assert fit_prior(rows, "fold_to_bet")[1] == op.PRIOR_MIN_STRENGTH


def test_too_few_bots_or_too_few_trials_leave_the_prior_uniform():
    rows = {"a": bot(0.1), "b": bot(0.9), "c": bot(0.5)}             # three bots, under PRIOR_MIN_BOTS
    assert fit_prior(rows, "fold_to_bet") == (0.5, op.PRIOR_MIN_STRENGTH)
    rows = {f"b{i}": bot(0.3, bets=10) for i in range(10)}           # ten bets each: no one qualifies
    assert fit_prior(rows, "fold_to_bet") == (0.5, op.PRIOR_MIN_STRENGTH)


# ---------------------------------------------------------------------------------------------- bounds

def test_with_no_row_the_posterior_is_the_prior_and_no_read_fires_on_it():
    p = field(scout_reads=True, sequential=True)
    mean, strength = p.prior("fold_to_bet")
    alpha, beta = p.posterior("stranger", "fold_to_bet")
    assert alpha == pytest.approx(mean * strength) and beta == pytest.approx((1 - mean) * strength)
    assert not any(getattr(p, read)("stranger") for read in
                   ("never_folds", "never_calls", "folds_blind", "never_three_bets", "folds_to_three_bet",
                    "never_bluffs", "big_bets_are_value"))
    assert p.fold_floor_upper("stranger") is None and p.river_bluff_floor("stranger") is None


def test_a_zero_count_has_a_bound_with_width_where_wald_has_none():
    p = field(scout_reads=True)
    p.rows["honest"] = bot(river_bets=40, river_bluffs=0)
    assert _upper_bound(0, 40) == 0.0                     # Wald: certain after 40 bets
    upper = p.upper("honest", "river_bluff")
    assert 0.0 < upper < 0.2


def test_the_bounds_move_the_right_way_with_each_observation():
    p = field()
    p.rows["x"] = bot(0.30, bets=200, hands=400)
    base_hi, base_lo = p.upper("x", "fold_to_bet"), p.lower("x", "fold_to_bet")
    p.rows["x"]["folds"] += 1                               # one more fold, one more bet
    p.rows["x"]["bets_faced"] += 1
    assert p.upper("x", "fold_to_bet") > base_hi and p.lower("x", "fold_to_bet") > base_lo
    p.rows["x"] = bot(0.30, bets=200, hands=400)
    p.rows["x"]["calls"] += 1                               # one more call, one more bet
    p.rows["x"]["bets_faced"] += 1
    assert p.upper("x", "fold_to_bet") < base_hi and p.lower("x", "fold_to_bet") < base_lo


def test_more_data_at_the_same_rate_narrows_the_interval():
    p = field()
    widths = []
    for bets in (50, 200, 1000, 5000):
        p.rows["x"] = bot(0.30, bets=bets, hands=2 * bets)
        widths.append(p.upper("x", "fold_to_bet") - p.lower("x", "fold_to_bet"))
    assert widths == sorted(widths, reverse=True)


def test_bets_clustered_in_few_matches_count_for_less():
    row = bot(0.30, bets=600, hands=600)                    # about 15 matches, 40 bets a match
    assert design_effect(row, 600, "fold_to_bet") == pytest.approx(
        1 + (600 / (600 / op.HANDS_PER_MATCH) - 1) * op.MATCH_CORRELATION["fold_to_bet"])
    spread = bot(0.30, bets=600, hands=60000)                # the same bets spread over 1,500 matches
    assert design_effect(spread, 600, "fold_to_bet") == 1.0
    p = field()
    p.rows["clustered"], p.rows["spread"] = row, spread
    assert p.upper("clustered", "fold_to_bet") > p.upper("spread", "fold_to_bet")


def test_a_scouted_match_count_is_used_when_the_row_has_one():
    row = bot(0.30, bets=600, hands=600)
    row["scout_base"] = {"hands": 600, "matches": 60}
    assert op.matches_of(row) == 60
    row["hands"] = 600 + int(op.HANDS_PER_MATCH) * 2       # two live matches on top of the scout
    assert op.matches_of(row) == pytest.approx(62)


# ---------------------------------------------------------------------------------------------- reads

def test_a_near_half_caller_with_105_bets_is_not_a_bot_that_never_calls():
    # Dronev4 on the clean file, 5 Oct: 38 folds, 31 calls, 36 raises from 150 hands in 7 matches.
    p = field()
    p.rows["Dronev4"] = {"bets_faced": 105, "folds": 38, "calls": 31, "raises": 36, "hands": 150}
    assert not p.never_calls("Dronev4")
    assert p.upper("Dronev4", "call_share") > 0.5           # not even separated from a half


def test_a_real_fold_or_raise_bot_still_reads_as_one():
    # Blueprint as the read was written for it, 14 Sept: 1,005 folds, 39 calls, 322 raises.
    p = field()
    p.rows["Blueprint"] = {"bets_faced": 1366, "folds": 1005, "calls": 39, "raises": 322, "hands": 1400}
    assert p.never_calls("Blueprint")


def test_a_23_percent_folder_over_5000_bets_never_folds_and_a_near_equilibrium_one_does_not():
    p = field()
    p.rows["PoetAndCoder"] = bot(0.23, bets=5000, hands=7000)
    assert p.never_folds("PoetAndCoder")
    p.rows["Maxwell"] = bot(0.366, bets=976, hands=1469)   # 0.366, its bound reaches past 0.40
    assert not p.never_folds("Maxwell")
    p.rows["short"] = bot(0.10, bets=op.SEQ_MIN_OBSERVED - 1)
    assert not p.never_folds("short")                       # under the minimum, whatever the rate


def test_hoops_is_still_a_station_but_its_bound_sits_between_a_half_pot_and_a_pot_bluff():
    p = field()
    p.rows["hoops"] = {"bets_faced": 6132, "folds": 2228, "calls": 3474, "raises": 430, "hands": 12399}
    upper = p.fold_floor_upper("hoops")
    assert p.never_folds("hoops")
    assert 2228 / 6132 < upper < op.EQUILIBRIUM_FOLD
    assert 1 / 3 < upper < 1 / 2


def _node_field(key, counts_by_bot, target):
    p = Profiles("/nonexistent/opponents.json", posteriors=True, scout_reads=True)
    p.rows = {f"f{i}": {"bets_faced": 0, "folds": 0, "calls": 0, "raises": 0, "hands": 4000,
                        "by_history": {key: c}} for i, c in enumerate(counts_by_bot)}
    p.rows["x"] = {"bets_faced": 0, "folds": 0, "calls": 0, "raises": 0, "hands": 4000,
                   "by_history": {key: target}}
    return p


OPEN_FIELD = [{"fold": f, "call": 400 - f - r, "raise": r} for f, r in
              ((40, 20), (80, 40), (120, 60), (160, 30), (200, 50), (240, 16), (100, 100), (60, 8))]


def test_folds_blind_needs_the_lower_bound_past_seventy_percent():
    assert _node_field("preflop:Ur", OPEN_FIELD, {"fold": 497, "call": 100, "raise": 34}).folds_blind("x")  # mellyy
    assert not _node_field("preflop:Ur", OPEN_FIELD, {"fold": 73, "call": 20, "raise": 7}).folds_blind("x")


def test_never_three_bets_holds_the_upper_bound_to_a_value_range():
    assert _node_field("preflop:Ur", OPEN_FIELD, {"fold": 731, "call": 1292, "raise": 22}).never_three_bets("x")  # wsp
    # r0ckGarden, 136 in 3,731 (3.6 percent): its bound (about 4.3) is over the point line of 4 but well inside a
    # 6 percent re-raise range, which is still the premium hands. Held against 4 the read was lost (5 Oct).
    assert _node_field("preflop:Ur", OPEN_FIELD, {"fold": 2957, "call": 638, "raise": 136}).never_three_bets("x")
    # mellyy on the clean file, 93 in 1,074 (8.7 percent), re-raises too often for its re-raise to be value.
    assert not _node_field("preflop:Ur", OPEN_FIELD, {"fold": 500, "call": 481, "raise": 93}).never_three_bets("x")


THREE_BET_FIELD = [{"fold": f, "call": 40 - f - 4, "raise": 4} for f in (5, 10, 15, 20, 25, 30, 12, 18)]


def test_folds_to_three_bet_holds_the_lower_bound_to_the_break_even_share():
    assert _node_field("preflop:TrUr", THREE_BET_FIELD, {"fold": 180, "call": 15, "raise": 5}).folds_to_three_bet("x")
    # melly, 143 of 182 (79 percent), the bot the read was written for: its bound (about 0.72) clears the 0.67 a
    # small three-bet needs. Held against 0.75 as well, the margin was counted twice and the read was lost.
    assert _node_field("preflop:TrUr", THREE_BET_FIELD, {"fold": 143, "call": 28, "raise": 11}).folds_to_three_bet("x")
    # Near the break-even on a thin sample (20 of 28, 71 percent): the bound falls below 0.67, so no read.
    assert not _node_field("preflop:TrUr", THREE_BET_FIELD, {"fold": 20, "call": 6, "raise": 2}).folds_to_three_bet("x")


def test_never_bluffs_on_the_bound():
    p = field(scout_reads=True)
    for i, name in enumerate(list(p.rows)):
        p.rows[name].update(river_bets=200, river_bluffs=10 + 8 * i)
    p.rows["runner1"] = bot(river_bets=106, river_bluffs=0, hands=914)
    p.rows["thin"] = bot(river_bets=40, river_bluffs=0, hands=239)       # Fold-ver-2: 0 of 40
    p.rows["one"] = bot(river_bets=143, river_bluffs=1, hands=4159)      # melly
    p.rows["often"] = bot(river_bets=200, river_bluffs=30, hands=3000)   # a 15 percent bluffer
    # The bound is held to a tenth, far inside the quarter to a third a bluff-catcher needs: Fold-ver-2's 0 of 40
    # (bound about 0.07) fires, where held against the point line of 0.05 it was lost (5 Oct).
    assert p.never_bluffs("runner1") and p.never_bluffs("one") and p.never_bluffs("thin")
    assert not p.never_bluffs("often")


def test_river_never_bluffs_on_the_bound_not_an_exact_zero():
    p = field(scout_reads=True)
    for i, name in enumerate(list(p.rows)):
        p.rows[name].update(river_bets=200, river_bluffs=10 + 8 * i)
    p.rows["runner1"] = bot(river_bets=106, river_bluffs=0, hands=914)   # bound about 0.028
    p.rows["wsp"] = bot(river_bets=500, river_bluffs=4, hands=6000)      # 0.8 percent, bound about 0.018
    p.rows["some"] = bot(river_bets=200, river_bluffs=10, hands=3000)    # 5 percent: honest enough for never_bluffs only
    assert p.river_never_bluffs("runner1") and p.river_never_bluffs("wsp")
    assert not p.river_never_bluffs("some")


def test_the_sizing_tell_on_the_bounds():
    p = field(scout_reads=True)
    for i, name in enumerate(list(p.rows)):
        p.rows[name].update(big_bets=200, big_bets_air=10 + 5 * i, small_bets=300, small_bets_air=40 + 10 * i)
    p.rows["poet"] = bot(big_bets=429, big_bets_air=0, small_bets=1080, small_bets_air=421, hands=7000)
    assert p.big_bets_are_value("poet")
    p.rows["poet"]["small_bets_air"] = 230                                # 21 percent: the bound is under 20
    assert not p.big_bets_are_value("poet")


def test_the_floors_are_posterior_bounds_and_keep_their_minimums():
    p = field(scout_reads=True)
    for name in list(p.rows):
        p.rows[name].update(river_bets=100, river_bluffs=20)
    p.rows["shadow"] = bot(river_bets=48, river_bluffs=23, hands=2344)
    floor = p.river_bluff_floor("shadow")
    assert floor == pytest.approx(p.lower("shadow", "river_bluff"))
    assert 0.2 < floor < 23 / 48
    p.rows["few"] = bot(river_bets=op.OVER_BLUFF_MIN - 1, river_bluffs=30)
    assert p.river_bluff_floor("few") is None


def test_posteriors_off_is_the_old_behaviour():
    on, off = field(sequential=True), field(posteriors=False, sequential=True)
    row = {"bets_faced": op.SEQ_MIN_OBSERVED, "folds": 10, "calls": 25, "raises": 5, "hands": 30}
    on.rows["x"], off.rows["x"] = dict(row), dict(row)
    assert off.never_folds("x")                    # the Wald bound, 0.38, under 0.40
    assert not on.never_folds("x")                 # forty bets from one match: not enough on the posterior


# ---------------------------------------------------------------------------------------------- bluff size

def checked_to(pot=400, stack=9800):
    return {"pot": pot, "to_call": 0, "your_stack": stack, "opponent_stacks": [stack]}


def test_the_break_even_of_a_bluff_is_its_share_of_the_pot_it_makes():
    state = checked_to()
    assert ArenaPlayer.bluff_break_even(RAISE_HALF, state) == pytest.approx(1 / 3)
    assert ArenaPlayer.bluff_break_even(RAISE_POT, state) == pytest.approx(1 / 2)
    assert ArenaPlayer.bluff_break_even(RAISE_TWO, state) == pytest.approx(2 / 3)
    assert ArenaPlayer.bluff_break_even(ALL_IN, state) == pytest.approx(9800 / 10200)
    # Facing 200 into 600 (the pot holds the bet): a half-pot raise puts in 200 + 400 = 600 to win 600.
    facing = {"pot": 600, "to_call": 200, "your_stack": 9400, "opponent_stacks": [9200]}
    assert ArenaPlayer.bluff_break_even(RAISE_HALF, facing) == pytest.approx(0.5)
    # Short: the bet cannot be more than the chips behind.
    assert ArenaPlayer.bluff_break_even(RAISE_TWO, checked_to(stack=300)) == pytest.approx(300 / 700)


def _player_against(row, name="hoops"):
    player = ArenaPlayer.__new__(ArenaPlayer)
    player.profiles = field()
    player.profiles.rows[name] = row
    player.opponent = name
    return player


def test_against_a_36_percent_folder_a_pot_bluff_is_withheld_and_a_half_pot_one_is_not():
    player = _player_against({"bets_faced": 6132, "folds": 2228, "calls": 3474, "raises": 430, "hands": 12399})
    state = checked_to()
    assert not player._bluff_folds_too_rarely(RAISE_HALF, state)
    assert player._bluff_folds_too_rarely(RAISE_POT, state)
    assert player._bluff_folds_too_rarely(ALL_IN, state)


def test_against_a_23_percent_folder_every_bluff_is_withheld():
    player = _player_against(bot(0.23, bets=5000, hands=7000), name="PoetAndCoder")
    for action in (RAISE_HALF, RAISE_POT, RAISE_TWO, ALL_IN):
        assert player._bluff_folds_too_rarely(action, checked_to())
