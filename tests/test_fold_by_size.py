"""
Folds by the size of our bet: the bins, the counting in `observe` (street totals) and in the scout (chips added),
the fallback to the overall rate where a bin is thin, and the bluff rule reading the bin of the bet it considers.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstraction.betting import ALL_IN, RAISE_HALF, RAISE_POT, RAISE_TWO  # noqa: E402
from chipzen import opponents as op  # noqa: E402
from chipzen.opponents import Profiles, size_bin, size_key  # noqa: E402
from chipzen.player import ArenaPlayer  # noqa: E402


def test_the_tree_s_sizes_land_inside_their_own_bins():
    assert [size_bin(f) for f in (0.25, 0.5, 1.0, 2.0, 5.0)] == ["small", "half", "pot", "2x", "jam"]
    # The edges are between the sizes, so the arena's clamps (min_raise lifting a small half-pot bet) stay put.
    assert size_bin(0.66) == "half" and size_bin(1.2) == "pot" and size_bin(2.4) == "2x"
    assert size_key(0.5, preflop=True) == "pre:half" and size_key(0.5, preflop=False) == "post:half"


# A hand with a three-bet, a four-bet, a bet and a re-raise over a check-raise, as our logs record it: a raise's
# amount is the seat's total for the street, a call's the chips it adds. Seat 0 is us, seat 1 the opponent.
#   open to 200: raises 100 over the 200 a call makes, half; four-bet to 1,800 over their 600: raises 1,200 over
#   1,200, pot; flop bet 1,800 into 3,600, half; re-raise to 19,800 over their 5,400: 14,400 over the 14,400 the
#   pot is after the call, which counts the 3,600 from preflop. Forgetting it would read 1.33, a 2x bet.
LOGGED = [
    {"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop"},
    {"seat": 1, "action": "post_big_blind", "amount": 100, "phase": "preflop"},
    {"seat": 0, "action": "raise", "amount": 200, "phase": "preflop"},
    {"seat": 1, "action": "raise", "amount": 600, "phase": "preflop"},
    {"seat": 0, "action": "raise", "amount": 1800, "phase": "preflop"},
    {"seat": 1, "action": "call", "amount": 1200, "phase": "preflop"},
    {"seat": 1, "action": "check", "amount": 0, "phase": "flop"},
    {"seat": 0, "action": "raise", "amount": 1800, "phase": "flop"},
    {"seat": 1, "action": "raise", "amount": 5400, "phase": "flop"},
    {"seat": 0, "action": "raise", "amount": 19800, "phase": "flop"},
    {"seat": 1, "action": "fold", "amount": 0, "phase": "flop"},
]
EXPECTED = {"pre:half": {"raise": 1}, "pre:pot": {"call": 1}, "post:half": {"raise": 1}, "post:pot": {"fold": 1}}


def as_platform_record(logged):
    """The same hand as the platform's hand records give it: every amount is the chips that action adds."""
    out, street, totals = [], None, {}
    for a in logged:
        if a["phase"] != street:
            street, totals = a["phase"], {}
        amount = a["amount"]
        if a["action"] == "raise":
            amount = a["amount"] - totals.get(a["seat"], 0)
            totals[a["seat"]] = a["amount"]
        else:
            totals[a["seat"]] = totals.get(a["seat"], 0) + amount
        out.append(dict(a, amount=amount))
    return out


def test_observe_bins_our_bets_by_the_pot_after_the_call_including_earlier_streets():
    p = Profiles("/nonexistent/opponents.json")
    p.observe({"action_history": LOGGED}, our_seat=0, opponent="x")
    row = p.rows["x"]
    assert row["by_size"] == EXPECTED
    # The sized answers are the same answers the overall count holds, split.
    assert sum(sum(v.values()) for v in row["by_size"].values()) == row["bets_faced"] == 4


def test_the_scout_bins_the_same_hand_the_same_way_from_the_other_seat():
    from scripts.chipzen_scout import profile, seed_row
    hand = {"actions": as_platform_record(LOGGED), "winner_seats": [0]}
    row = profile("scouted", [{"id": "m", "vs": ["us"], "seat": 1}], {"m": [hand]})
    assert row["by_size"] == EXPECTED
    assert row["bets_faced"] == 4 and row["folds"] == 1 and row["raises"] == 2
    seeded = seed_row(row)
    assert seeded["by_size"] == EXPECTED and seeded["scout_base"]["by_size"] == EXPECTED
    seeded["by_size"]["post:pot"]["fold"] += 1          # live counts must not move the base
    assert seeded["scout_base"]["by_size"]["post:pot"]["fold"] == 1


def test_the_scout_sizes_an_overbet_and_a_jam_into_a_check():
    from scripts.chipzen_scout import profile
    hand = {"winner_seats": [0], "actions": [
        {"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop"},
        {"seat": 1, "action": "post_big_blind", "amount": 100, "phase": "preflop"},
        {"seat": 0, "action": "call", "amount": 50, "phase": "preflop"},
        {"seat": 1, "action": "check", "amount": 0, "phase": "preflop"},
        {"seat": 1, "action": "check", "amount": 0, "phase": "flop"},
        {"seat": 0, "action": "raise", "amount": 400, "phase": "flop"},       # 2x the 200 pot
        {"seat": 1, "action": "call", "amount": 400, "phase": "flop"},
        {"seat": 1, "action": "check", "amount": 0, "phase": "turn"},
        {"seat": 0, "action": "raise", "amount": 9500, "phase": "turn"},      # a shove into 1,000
        {"seat": 1, "action": "fold", "amount": 0, "phase": "turn"},
    ]}
    row = profile("scouted", [{"id": "m", "vs": ["us"], "seat": 1}], {"m": [hand]})
    assert row["by_size"] == {"post:2x": {"call": 1}, "post:jam": {"fold": 1}}


def _match_log(directory, opponent="stranger", hands=3):
    import json
    rows = [{"frame": "match_start", "seat": 0, "at": 1_800_000_000,
             "seats": [{"display_name": "us", "is_self": True}, {"display_name": opponent, "is_self": False}]}]
    # Stacks that agree with LOGGED: the flop shove to 19,800 needs both seats about 30,000 deep, and they lose
    # 7,200 (our payout is the 14,400 pot and our uncalled 14,400), so `observe`, which rebuilds each start from the
    # closing stacks, leaves the shove uncapped.
    for h in range(1, hands + 1):
        rows.append({"frame": "round_start", "state": {"stacks": [30000, 30000]}})
        rows.append({"frame": "round_result", "result": {"hand_number": h, "stacks": [37200, 22800],
                                                         "payouts": [{"seat": 0, "amount": 28800}],
                                                         "winner_seats": [0], "action_history": LOGGED}})
    (directory / "m1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_every_start_counts_the_sized_live_answers_once(tmp_path):
    """The 4 Oct double count, for the sized counts: they live in the scout base and are added to once per start."""
    import json
    logs = tmp_path / "logs"; logs.mkdir()
    _match_log(logs, hands=3)
    path = tmp_path / "opponents.json"
    base = {"bets_faced": 500, "folds": 100, "calls": 350, "raises": 50, "hands": 600, "net": 0, "by_history": {},
            "by_size": {"post:pot": {"fold": 40, "call": 60}, "pre:half": {"call": 200}}, "scouted": True}
    path.write_text(json.dumps({"stranger": dict(base, scout_base=json.loads(json.dumps(base)))}))
    seen = []
    for _ in range(3):
        p = Profiles(str(path)).rebuild(str(logs))
        p.save()
        seen.append(json.dumps(p.rows["stranger"]["by_size"], sort_keys=True))
    assert seen[0] == seen[1] == seen[2]
    row = Profiles(str(path)).rows["stranger"]
    assert row["by_size"]["post:pot"] == {"fold": 43, "call": 60}
    assert row["by_size"]["pre:half"] == {"call": 200, "raise": 3}
    assert row["by_size"]["pre:pot"] == {"call": 3} and row["by_size"]["post:half"] == {"raise": 3}
    assert row["scout_base"]["by_size"] == base["by_size"]


# ---------------------------------------------------------------------------------------------- fold_at

def sized_row(fold=0.36, bets=6000, hands=12000, **bins):
    """A row with an overall fold rate and, per bin key, (fold rate, answers)."""
    folds = int(round(fold * bets))
    row = {"bets_faced": bets, "folds": folds, "calls": bets - folds, "raises": 0, "hands": hands, "net": 0,
           "by_history": {}, "by_size": {}}
    for key, (rate, n) in bins.items():
        f = int(round(rate * n))
        row["by_size"][key.replace("_", ":")] = {"fold": f, "call": n - f}
    return row


def field():
    """A field whose bots fold more to bigger bets, so each bin's prior is fitted rather than uniform."""
    p = Profiles("/nonexistent/opponents.json", posteriors=True)
    for i, f in enumerate((0.15, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6)):
        p.rows[f"f{i}"] = sized_row(f, bets=2000, hands=4000, post_half=(f, 500), post_pot=(f + 0.12, 300),
                                    pre_half=(f - 0.05, 600))
    return p


def test_fold_at_reads_the_bin_and_falls_back_to_the_overall_rate_when_it_is_thin():
    p = Profiles("/nonexistent/opponents.json")
    p.rows["x"] = sized_row(0.36, post_pot=(0.57, op.SIZE_MIN), post_half=(0.44, op.SIZE_MIN - 1))
    assert p.fold_at("x", 1.0) == pytest.approx(0.575, abs=0.01)
    assert p.fold_at("x", 0.5) == pytest.approx(0.36, abs=0.001)          # 39 answers: the overall rate
    assert p.fold_at("x", 0.5, preflop=True) == pytest.approx(0.36, abs=0.001)   # no preflop bins at all
    assert p.fold_at("nobody", 0.5) is None


def test_fold_upper_at_is_the_bin_s_posterior_bound_or_the_overall_one():
    p = field()
    p.rows["x"] = sized_row(0.36, post_pot=(0.57, 800), post_half=(0.44, 10))
    overall = p.fold_floor_upper("x")
    assert p.fold_upper_at("x", 0.5) == overall                            # thin bin
    pot = p.fold_upper_at("x", 1.0)
    assert 0.57 < pot < 0.62 and pot != overall
    p.rows["y"] = sized_row(0.36, bets=op.SEQ_MIN_OBSERVED - 1, post_pot=(0.57, 800))
    assert p.fold_upper_at("y", 1.0) is None                               # the overall gate still holds


def test_each_bin_has_its_own_prior():
    p = field()
    half, _ = p.prior("fold_at:post:half")
    pot, _ = p.prior("fold_at:post:pot")
    assert pot == pytest.approx(half + 0.12, abs=0.01)


# ---------------------------------------------------------------------------------------------- the bluff rule

def checked_to(pot=400, stack=9800, phase="flop"):
    return {"pot": pot, "to_call": 0, "your_stack": stack, "opponent_stacks": [stack], "phase": phase}


def _player_against(row, name="hoops"):
    player = ArenaPlayer.__new__(ArenaPlayer)
    player.profiles = field()
    player.profiles.rows[name] = row
    player.opponent = name
    return player


def test_the_raise_s_size_is_measured_as_observe_bins_it():
    assert ArenaPlayer.bluff_fraction(RAISE_HALF, checked_to()) == pytest.approx(0.5)
    assert ArenaPlayer.bluff_fraction(RAISE_POT, checked_to()) == pytest.approx(1.0)
    facing = {"pot": 600, "to_call": 200, "your_stack": 9400, "opponent_stacks": [9200]}
    assert ArenaPlayer.bluff_fraction(RAISE_HALF, facing) == pytest.approx(0.5)
    assert size_bin(ArenaPlayer.bluff_fraction(ALL_IN, checked_to())) == "jam"


def test_hoops_by_size_releases_the_pot_bluff_the_overall_rate_withheld():
    """
    hoops on the scout cache: 36 percent overall, 44 to half-pot bets, 57 to pot-sized ones. On the overall rate a
    half-pot bluff (needs a third) goes and a pot bluff (needs a half) is withheld; on the bins both go.
    """
    overall_only = _player_against(sized_row(0.363, bets=6132, hands=12399))
    assert not overall_only._bluff_folds_too_rarely(RAISE_HALF, checked_to())
    assert overall_only._bluff_folds_too_rarely(RAISE_POT, checked_to())
    sized = _player_against(sized_row(0.363, bets=6132, hands=12399, post_half=(0.44, 1500), post_pot=(0.57, 800)))
    assert not sized._bluff_folds_too_rarely(RAISE_HALF, checked_to())
    assert not sized._bluff_folds_too_rarely(RAISE_POT, checked_to())
    # A 2x bluff needs two thirds, and with no 2x bin on file it is read on the overall rate.
    assert sized._bluff_folds_too_rarely(RAISE_TWO, checked_to())


def test_a_half_pot_bin_under_a_third_withholds_the_half_pot_bluff():
    """Where the half-pot bin folds 30 percent the old rule (36 overall) was wrong to release that bluff."""
    player = _player_against(sized_row(0.363, bets=6132, hands=12399, post_half=(0.30, 1500), post_pot=(0.45, 800)))
    assert player._bluff_folds_too_rarely(RAISE_HALF, checked_to())
    assert player._bluff_folds_too_rarely(RAISE_POT, checked_to())
    # The pot bin alone decides the pot bluff: at 57 percent it would go even though the half-pot one does not.
    player.profiles.rows["hoops"]["by_size"]["post:pot"] = {"fold": 456, "call": 344}
    assert player._bluff_folds_too_rarely(RAISE_HALF, checked_to())
    assert not player._bluff_folds_too_rarely(RAISE_POT, checked_to())


def test_preflop_bluffs_read_the_preflop_bin_not_the_postflop_one():
    """A bot that calls opens and folds after the flop (Fold-ver-3's shape)."""
    player = _player_against(sized_row(0.366, bets=3000, hands=6000, pre_half=(0.20, 900), post_half=(0.60, 900)))
    open_state = {"pot": 150, "to_call": 50, "your_stack": 9950, "opponent_stacks": [9900], "phase": "preflop"}
    assert player._bluff_folds_too_rarely(RAISE_HALF, open_state)
    assert not player._bluff_folds_too_rarely(RAISE_HALF, checked_to())
