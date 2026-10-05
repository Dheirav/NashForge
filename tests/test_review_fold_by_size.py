"""
Independent review of the fold-by-size branch: the edge cases tests/test_fold_by_size.py leaves open.

The expected values here are worked out by hand from the definition the branch states (a bet's size is what it
raises by, over the pot after the call), not read back from the code. A test marked xfail(strict=True) is a real
disagreement between the code and that definition, kept failing on purpose so a fix shows up as an XPASS.
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstraction.betting import ALL_IN, RAISE_HALF, RAISE_POT, RAISE_TWO  # noqa: E402
from chipzen import opponents as op  # noqa: E402
from chipzen.opponents import Profiles, size_bin, size_fraction, size_key  # noqa: E402
from chipzen.player import ArenaPlayer  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHIPPED = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")


def a(seat, action, amount=0, phase="preflop"):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase}


BLINDS = [a(0, "post_small_blind", 50), a(1, "post_big_blind", 100)]


def observed(history, our_seat=0):
    p = Profiles("/nonexistent/opponents.json")
    p.observe({"action_history": history}, our_seat=our_seat, opponent="x")
    return p.rows["x"]


# ---------------------------------------------------------------------------------------------- bin edges

def test_every_bin_edge_belongs_to_the_bin_above_it():
    # The edges are half-open, [low, high): an exact 0.75 is a pot bet, and so on up.
    assert [size_bin(x) for x in (0.0, 0.3999, 0.4, 0.7499, 0.75, 1.2499, 1.25, 2.4999, 2.5, 1e9)] == \
        ["small", "small", "half", "half", "pot", "pot", "2x", "2x", "jam", "jam"]


def test_a_platform_two_and_a_half_blind_open_sits_exactly_on_the_half_pot_edge_and_reads_as_pot():
    # A 2.5bb open raises 150 over the call into a 200 pot: exactly 0.75. Pinned because the field opens this size
    # often, so pre:pot holds 2.5x and 3x opens while our 2x open (to 200) is pre:half.
    assert size_fraction(150, 200) == 0.75 and size_key(150 / 200, preflop=True) == "pre:pot"
    assert size_key(size_fraction(100, 200), preflop=True) == "pre:half"


def test_a_zero_pot_and_a_negative_raise_read_as_small_without_raising():
    assert size_fraction(100, 0) == 0.0 and size_bin(size_fraction(100, 0)) == "small"
    assert size_bin(size_fraction(-50, 200)) == "small"


# ---------------------------------------------------------------------------------------------- observe

def test_a_turn_bet_carries_the_pot_from_preflop_and_flop():
    # Preflop 200 each (400), flop bet 200 called (800), turn bet 400 into 800: half. A pot that forgot the flop
    # would read 400 / 400, a pot bet.
    rows = observed(BLINDS + [a(0, "raise", 200), a(1, "call", 100),
                              a(1, "check", 0, "flop"), a(0, "raise", 200, "flop"), a(1, "call", 200, "flop"),
                              a(1, "check", 0, "turn"), a(0, "raise", 400, "turn"), a(1, "fold", 0, "turn")])
    assert rows["by_size"] == {"pre:half": {"call": 1}, "post:half": {"call": 1, "fold": 1}}


def test_a_raise_over_a_limp_is_sized_against_the_pot_after_no_call():
    # They limp (call 50) to 100 each; our raise to 400 adds 300 over nothing to call, into 200: 1.5, a 2x bet.
    rows = observed([a(1, "post_small_blind", 50), a(0, "post_big_blind", 100), a(1, "call", 50),
                     a(0, "raise", 400), a(1, "fold")])
    assert rows["by_size"] == {"pre:2x": {"fold": 1}}


def test_limps_checks_and_their_bets_count_nothing():
    # We limp and check through; they bet and we call. No bet of ours is ever answered.
    rows = observed(BLINDS + [a(0, "call", 50), a(1, "check"),
                              a(1, "check", 0, "flop"), a(0, "check", 0, "flop"),
                              a(1, "raise", 200, "turn"), a(0, "call", 200, "turn")])
    assert rows["by_size"] == {} and rows["bets_faced"] == 0


def test_a_min_bet_postflop_is_small():
    # Flop pot 400, a 100 bet is 0.25.
    rows = observed(BLINDS + [a(0, "raise", 200), a(1, "call", 100),
                              a(1, "check", 0, "flop"), a(0, "raise", 100, "flop"), a(1, "call", 100, "flop")])
    assert rows["by_size"]["post:small"] == {"call": 1}


def test_our_short_all_in_is_binned_by_the_chips_it_actually_raises():
    # Flop pot 400; we have 300 left and shove it: 0.75, a pot bet, which is how bluff_break_even prices it.
    rows = observed(BLINDS + [a(0, "raise", 200), a(1, "call", 100),
                              a(1, "check", 0, "flop"), a(0, "raise", 300, "flop"), a(1, "fold", 0, "flop")])
    assert rows["by_size"]["post:pot"] == {"fold": 1}


def test_a_shove_over_a_short_opponent_is_binned_by_what_they_can_be_made_to_call():
    # They start the hand with 900. Preflop 200 each, flop pot 400. Our shove to 9,800 can only make them call their
    # last 700: 700 / 400 = 1.75, a 2x bet, and the player prices that ALL_IN as 2x (see the player test below).
    history = BLINDS + [a(0, "raise", 200), a(1, "call", 100),
                        a(1, "check", 0, "flop"), a(0, "raise", 9800, "flop"), a(1, "fold", 0, "flop")]
    p = Profiles("/nonexistent/opponents.json")
    p.observe({"action_history": history, "stacks": [10100, 700]}, our_seat=0, opponent="x")
    assert p.rows["x"]["by_size"].get("post:2x") == {"fold": 1}


def test_their_re_raise_then_our_call_counts_one_answer_to_our_bet():
    rows = observed(BLINDS + [a(0, "raise", 200), a(1, "call", 100),
                              a(1, "check", 0, "flop"), a(0, "raise", 400, "flop"),     # 400 into 400: pot
                              a(1, "raise", 1200, "flop"), a(0, "call", 800, "flop")])
    assert rows["by_size"] == {"pre:half": {"call": 1}, "post:pot": {"raise": 1}}
    assert rows["bets_faced"] == 2 and rows["raises"] == 1


def test_a_three_way_hand_sizes_our_raise_over_the_biggest_bet():
    # Seat 2 opens to 300; we (seat 1, big blind) make it 900: 600 over our 200 call, into 450 + 200 = 650: 0.92, pot.
    # Measured over seat 0's 50 instead of seat 2's 300 it would be 850 over 450, 1.89: 2x.
    history = [a(0, "post_small_blind", 50), a(1, "post_big_blind", 100), a(2, "raise", 300),
               a(0, "fold"), a(1, "raise", 900), a(2, "fold")]
    rows = observed(history, our_seat=1)
    assert rows["by_size"] == {"pre:pot": {"fold": 1}}


def test_a_row_written_before_the_branch_gains_by_size_on_its_first_hand():
    p = Profiles("/nonexistent/opponents.json")
    p.rows["x"] = {"bets_faced": 10, "folds": 2, "calls": 8, "raises": 0, "hands": 20, "net": 0, "by_history": {}}
    p.observe({"action_history": BLINDS + [a(0, "raise", 200), a(1, "fold")]}, our_seat=0, opponent="x")
    assert p.rows["x"]["by_size"] == {"pre:half": {"fold": 1}} and p.rows["x"]["bets_faced"] == 11


def test_a_raise_logged_without_an_amount_does_not_crash():
    # Not seen in the logs (every raise carries one), pinned so a malformed row costs a mis-binned count, not a start.
    rows = observed(BLINDS + [{"seat": 0, "action": "raise", "phase": "preflop"}, a(1, "fold")])
    assert rows["bets_faced"] == 1 and sum(sum(v.values()) for v in rows["by_size"].values()) == 1


# ---------------------------------------------------------------------------------------------- the scout

def test_the_scout_sizes_a_three_way_re_raise_over_the_biggest_bet():
    # Rewritten with the fix, which skips the match rather than sizing it: the scout's other counts (the U/T
    # letters, three-bet chances, showdowns) are heads-up shaped too, so a correct size alone would still leave
    # a three-way match misread. The finding stands as the case that must not be counted at the wrong size.
    from scripts.chipzen_scout import profile
    # Chips-added format. Scouted bot is seat 0 (small blind, 50 in). Seat 2 opens to 300 (adds 300); seat 1 (big
    # blind) re-raises to 900 (adds 800): 600 over its 200 call, into 450 + 200 = 650, 0.92, a pot bet. The scout
    # took the call from seat 0's 50 (none) and read 800 over 450, 1.78, a 2x bet.
    hand = {"winner_seats": [1], "actions": [
        a(0, "post_small_blind", 50), a(1, "post_big_blind", 100), a(2, "raise", 300),
        a(1, "raise", 800), a(0, "fold")]}
    heads_up = {"winner_seats": [1], "actions": BLINDS + [a(1, "raise", 100), a(0, "fold")]}   # 100 into 150: half
    row = profile("scouted", [{"id": "m", "vs": ["p", "q"], "seat": 0}, {"id": "h", "vs": ["p"], "seat": 0}],
                  {"m": [hand], "h": [heads_up]})
    # The three-way match is left out whole, as copy_validate.load_matches leaves it out; the heads-up one counts.
    assert row["matches"] == 1 and row["hands"] == 1
    assert "pre:2x" not in row["by_size"] and row["by_size"] == {"pre:half": {"fold": 1}}


def test_the_scout_and_observe_agree_on_a_turn_bet_with_two_streets_behind():
    from scripts.chipzen_scout import profile
    logged = BLINDS + [a(0, "raise", 200), a(1, "call", 100),
                       a(1, "check", 0, "flop"), a(0, "raise", 200, "flop"), a(1, "call", 200, "flop"),
                       a(1, "check", 0, "turn"), a(0, "raise", 400, "turn"), a(1, "fold", 0, "turn")]
    platform = BLINDS + [a(0, "raise", 150), a(1, "call", 100),        # the open adds 150 to the posted 50
                         a(1, "check", 0, "flop"), a(0, "raise", 200, "flop"), a(1, "call", 200, "flop"),
                         a(1, "check", 0, "turn"), a(0, "raise", 400, "turn"), a(1, "fold", 0, "turn")]
    row = profile("scouted", [{"id": "m", "vs": ["us"], "seat": 1}], {"m": [{"actions": platform, "winner_seats": [0]}]})
    assert row["by_size"] == observed(logged)["by_size"] == {"pre:half": {"call": 1}, "post:half": {"call": 1, "fold": 1}}


def test_seed_row_keeps_every_key_the_old_literal_wrote_plus_by_size():
    from scripts.chipzen_scout import profile, seed_row
    hand = {"actions": BLINDS + [a(0, "raise", 150), a(1, "fold")], "winner_seats": [0]}
    row = profile("s", [{"id": "m", "vs": ["us"], "seat": 1}], {"m": [hand]})
    old = {"bets_faced": row["bets_faced"], "folds": row["folds"], "calls": row["calls"],
           "raises": row["raises"], "hands": row["hands"], "matches": row["matches"], "net": 0,
           "by_history": row["by_history"], "scouted": True,
           "river_bets": row["river_bets"], "river_bluffs": row["river_bluffs"],
           "big_bets": row["big_bets"], "big_bets_air": row["big_bets_air"],
           "small_bets": row["small_bets"], "small_bets_air": row["small_bets_air"]}
    old["scout_base"] = {k: v for k, v in old.items()}
    new = seed_row(row)
    strip = lambda d: {k: v for k, v in d.items() if k != "by_size"}         # noqa: E731
    assert json.loads(json.dumps(strip(new) | {"scout_base": strip(new["scout_base"])})) == json.loads(json.dumps(old))
    assert new["by_size"] == new["scout_base"]["by_size"] == {"pre:half": {"fold": 1}}


# ---------------------------------------------------------------------------------------------- rebuild

def test_a_base_from_before_the_branch_takes_the_sized_live_answers_once_and_stays_unsized(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    rows = [{"frame": "match_start", "seat": 0, "at": 1_800_000_000,
             "seats": [{"display_name": "us", "is_self": True}, {"display_name": "old", "is_self": False}]}]
    for h in range(2):
        rows.append({"frame": "round_start", "state": {"stacks": [10000, 10000]}})
        rows.append({"frame": "round_result", "result": {"hand_number": h, "stacks": [10100, 9900],
                                                         "action_history": BLINDS + [a(0, "raise", 200),
                                                                                     a(1, "fold")]}})
    (logs / "m.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    base = {"bets_faced": 100, "folds": 30, "calls": 70, "raises": 0, "hands": 200, "net": 0, "by_history": {},
            "scouted": True}
    path = tmp_path / "opponents.json"
    path.write_text(json.dumps({"old": dict(base, scout_base=dict(base))}))
    for _ in range(3):
        p = Profiles(str(path)).rebuild(str(logs))
        p.save()
    row = Profiles(str(path)).rows["old"]
    assert row["by_size"] == {"pre:half": {"fold": 2}} and row["bets_faced"] == 102
    assert "by_size" not in row["scout_base"]


# ---------------------------------------------------------------------------------------------- the read

def row_with(fold=0.30, bets=4000, hands=8000, **bins):
    folds = int(round(fold * bets))
    row = {"bets_faced": bets, "folds": folds, "calls": bets - folds, "raises": 0, "hands": hands, "net": 0,
           "by_history": {}, "by_size": {}}
    for key, (f, n) in bins.items():
        row["by_size"][key.replace("_", ":")] = {"fold": f, "call": n - f}
    return row


def test_fold_upper_at_switches_from_the_overall_bound_at_exactly_size_min():
    p = Profiles("/nonexistent/opponents.json", posteriors=True)
    p.rows["x"] = row_with(post_pot=(30, op.SIZE_MIN - 1))
    assert p.fold_upper_at("x", 1.0) == p.fold_floor_upper("x")
    p.rows["x"] = row_with(post_pot=(30, op.SIZE_MIN))
    p._priors.clear()
    assert p.fold_upper_at("x", 1.0) == pytest.approx(p.upper("x", "fold_at:post:pot"))
    assert p.fold_upper_at("x", 1.0) != p.fold_floor_upper("x")


def test_a_bin_carried_by_too_few_bots_gets_the_uniform_prior_and_its_own_correlation():
    from scipy.special import betaincinv
    p = Profiles("/nonexistent/opponents.json", posteriors=True)
    for i in range(op.PRIOR_MIN_BOTS - 1):
        p.rows[f"b{i}"] = row_with(post_2x=(50, 100))
    assert p.prior("fold_at:post:2x") == (0.5, op.PRIOR_MIN_STRENGTH)
    p.rows["x"] = row_with(hands=3900, post_2x=(30, 60))             # 100 matches by the hands conversion
    p._priors.clear()
    assert p.prior("fold_at:post:2x") != (0.5, op.PRIOR_MIN_STRENGTH)  # the fourth bot fits a prior
    del p.rows["b0"]
    p._priors.clear()
    rho = op.MATCH_CORRELATION["fold_at:post:2x"]
    d = max(1.0, 1.0 + (60 / 100.0 - 1.0) * rho)
    want = betaincinv(1.0 + 30 / d, 1.0 + 30 / d, op.POSTERIOR_CONFIDENCE)
    assert p.fold_upper_at("x", 2.0) == pytest.approx(want)


def test_every_bin_has_a_correlation_and_a_rate():
    for key in op.SIZE_KEYS:
        assert f"fold_at:{key}" in op.RATES and f"fold_at:{key}" in op.MATCH_CORRELATION


def test_the_reads_tolerate_rows_with_no_or_null_by_size():
    p = Profiles("/nonexistent/opponents.json", posteriors=True)
    p.rows["none"] = {"bets_faced": 500, "folds": 100, "calls": 400, "raises": 0, "hands": 900}
    p.rows["null"] = dict(p.rows["none"], by_size=None)
    p.rows["nullbin"] = dict(p.rows["none"], by_size={"post:pot": None})
    for name in ("none", "null", "nullbin"):
        assert p.fold_at(name, 1.0) == pytest.approx(0.2)
        assert p.fold_upper_at(name, 1.0) == p.fold_floor_upper(name)


def test_fold_upper_at_respects_the_bankroll_gate():
    p = Profiles("/nonexistent/opponents.json", posteriors=True, bankroll=True)
    p.rows["x"] = dict(row_with(post_pot=(300, 400)), net=-1)
    assert p.fold_upper_at("x", 1.0) is None


# ---------------------------------------------------------------------------------------------- the player

def _player(row, name="b"):
    player = ArenaPlayer.__new__(ArenaPlayer)
    player.profiles = Profiles("/nonexistent/opponents.json", posteriors=True)
    player.profiles.rows[name] = row
    player.opponent = name
    player.size_aware_bluffs = True
    return player


def _main_break_even(choice, state):
    """bluff_break_even as main has it (fbeff2c), copied verbatim, to pin the refactor."""
    from slumbot.bridge import RAISE_FRACTIONS
    pot = int(state.get("pot") or 0)
    to_call = int(state.get("to_call") or 0)
    mine = int(state.get("your_stack") or 0)
    theirs = int((state.get("opponent_stacks") or [0])[0])
    behind = min(mine, to_call + theirs) if mine > 0 else to_call + theirs
    b = behind if choice == ALL_IN else to_call + (pot + to_call) * RAISE_FRACTIONS[choice - 2]
    b = min(b, behind) if behind > 0 else b
    return b / float(pot + b) if pot + b > 0 else 1.0


def test_bluff_break_even_is_unchanged_from_main():
    rng = np.random.default_rng(0)
    for _ in range(3000):
        state = {"pot": int(rng.integers(0, 4000)), "to_call": int(rng.integers(0, 2000)),
                 "your_stack": int(rng.integers(0, 12000)), "opponent_stacks": [int(rng.integers(0, 12000))]}
        if rng.random() < 0.05:
            state.pop("opponent_stacks")
        for choice in (RAISE_HALF, RAISE_POT, RAISE_TWO, ALL_IN):
            assert ArenaPlayer.bluff_break_even(choice, state) == _main_break_even(choice, state)


def test_the_bin_read_and_the_break_even_price_the_same_capped_chips():
    # Pot 400 into a check; they have 700 behind. Our 2x (800) and all-in are both 700: 1.75, the 2x bin.
    state = {"pot": 400, "to_call": 0, "your_stack": 9800, "opponent_stacks": [700], "phase": "river"}
    for choice in (RAISE_TWO, ALL_IN):
        f = ArenaPlayer.bluff_fraction(choice, state)
        assert f == pytest.approx(1.75) and size_bin(f) == "2x"
        assert ArenaPlayer.bluff_break_even(choice, state) == pytest.approx(700 / 1100)
    # Facing a bet, the half-pot raise over a check-raise: pot 1,000 with their 400 in, to_call 200 (our 200 in):
    # pot after the call 1,200, raise 600, 0.5.
    facing = {"pot": 1000, "to_call": 200, "your_stack": 9000, "opponent_stacks": [8800], "phase": "turn"}
    assert ArenaPlayer.bluff_fraction(RAISE_HALF, facing) == pytest.approx(0.5)


def test_a_facing_bet_bluff_reads_the_bin_of_its_raise_not_its_total_chips():
    # A half-pot raise facing a bet puts in 600 chips (call 200 + 400), which over the 800 pot after the call is
    # the 0.75 a pot bin starts at if measured by chips in. It must read the half bin: here a 20 percent half bin
    # withholds and a 90 percent pot bin would have released.
    player = _player(row_with(fold=0.30, post_half=(200, 1000), post_pot=(900, 1000)))
    facing = {"pot": 600, "to_call": 200, "your_stack": 9400, "opponent_stacks": [9200], "phase": "turn"}
    assert player._bluff_folds_too_rarely(RAISE_HALF, facing)
    assert not player._bluff_folds_too_rarely(RAISE_POT, facing)


def test_a_preflop_bluff_reads_the_jam_bin_for_a_shove():
    player = _player(row_with(fold=0.30, pre_jam=(980, 1000), pre_half=(50, 1000)))
    shove = {"pot": 150, "to_call": 50, "your_stack": 9950, "opponent_stacks": [9900], "phase": "preflop"}
    # A 66-pot shove needs 0.985 folds; the jam bin's bound (98 percent of 1,000) is about 0.987.
    assert player.profiles.fold_upper_at("b", ArenaPlayer.bluff_fraction(ALL_IN, shove), preflop=True) > \
        ArenaPlayer.bluff_break_even(ALL_IN, shove)
    assert not player._bluff_folds_too_rarely(ALL_IN, shove)
    assert player._bluff_folds_too_rarely(RAISE_HALF, shove)


# ---------------------------------------------------------------------------------------------- both flags only

@pytest.fixture(scope="module")
def shipped():
    if not os.path.exists(SHIPPED):
        pytest.skip("shipped solver not on this machine")
    return ArenaPlayer([SHIPPED], np.random.default_rng(3))


def _weak_flop():
    blinds = [{"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop", "is_timeout": False},
              {"seat": 1, "action": "post_big_blind", "amount": 100, "phase": "preflop", "is_timeout": False}]
    more = [{"seat": 0, "action": "raise", "amount": 200, "phase": "preflop", "is_timeout": False},
            {"seat": 1, "action": "call", "amount": 100, "phase": "preflop", "is_timeout": False},
            {"seat": 1, "action": "check", "amount": 0, "phase": "flop", "is_timeout": False}]
    return {"hand_number": 1, "phase": "flop", "board": ["Qc", "9s", "Kd"], "your_hole_cards": ["3h", "2c"],
            "pot": 400, "your_stack": 9800, "opponent_stacks": [9800], "to_call": 0,
            "min_raise": 100, "max_raise": 9800, "action_history": blinds + more}


@pytest.mark.parametrize("posteriors,size_aware,released", [(False, False, False), (False, True, False),
                                                             (True, False, False), (True, True, True)])
def test_the_bins_release_bluffs_only_under_both_flags(shipped, posteriors, size_aware, released):
    # A station overall (15 percent of 6,000) whose postflop bins fold 90 percent (99 to a jam, which needs 0.96): only the size rule with
    # posteriors reads the bins, and then nothing postflop is withheld; any other combination withholds as main.
    row = row_with(fold=0.15, bets=6000, hands=12000, post_small=(900, 1000), post_half=(900, 1000),
                   post_pot=(900, 1000), post_2x=(900, 1000), post_jam=(990, 1000))
    shipped.profiles = Profiles("/nonexistent/opp.json", posteriors=posteriors)
    shipped.profiles.rows["st"] = row
    shipped.opponent = "st"
    shipped.size_aware_bluffs = size_aware
    try:
        assert shipped.profiles.never_folds("st")
        outs = [shipped.decide(_weak_flop(), ["check", "raise"], 0) for _ in range(60)]
        withheld = [o for o in outs if o["record"]["adjusted"] == "bluff withheld"]
        if released:
            assert not withheld
            assert any(o["action"] == "raise" for o in outs)       # the solver's bluffs go out
        else:
            assert withheld and all(o["action"] == "check" for o in outs)
    finally:
        shipped.size_aware_bluffs = False
        shipped.profiles = None
        shipped.opponent = None
