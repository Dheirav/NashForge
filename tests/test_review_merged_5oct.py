"""
Independent review of the three features merged on 5 October: the price guard (`--price-misread`), the
posterior reads (`--posterior-reads`, `--size-aware-bluffs`) and the profile double-count fix (`scout_base`).

Each test covers a behaviour or edge case the feature's own tests left out. A test marked
xfail(strict=True) with "REVIEW BUG" or "REVIEW FINDING" in its reason pins behaviour the review judged
wrong against the feature's own stated rule; it is kept failing on purpose, so a fix shows up as an XPASS.

The identity tests run the code from before the merges (37219c6 for the player and reads, c7dd020 for the
rebuild) out of `git show`/`git archive` into a temporary directory, never by checking out in the tree.
"""
import glob
import importlib.util
import json
import os
import subprocess
import sys
import types
from contextlib import contextmanager

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import chipzen.player as player_module  # noqa: E402
import pokerbot_native  # noqa: E402
from abstraction.betting import ALL_IN, CHECK_CALL, FOLD, RAISE_HALF, RAISE_POT  # noqa: E402
from chipzen import opponents as op  # noqa: E402
from chipzen.opponents import Profiles, fit_prior  # noqa: E402
from chipzen.player import ArenaPlayer  # noqa: E402

SHIPPED = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")
TAPER = os.path.join(ROOT, "results", "cfr", "nolimit_taper_42.pkl")
PROFILES = os.path.join(ROOT, "results", "chipzen", "opponents.json")
LADDER = os.path.join(ROOT, "results", "cfr", "ladder169l_v5xRR3")
MATCHES = os.path.join(ROOT, "results", "chipzen", "matches")
BEFORE_GUARD = "37219c6"      # main just before merge: price-guard (and so before the posterior merge)
BEFORE_BASE = "c7dd020"       # main just before merge: profile-base


def entry(seat, action, amount, phase="preflop"):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase, "is_timeout": False}


BLINDS = [entry(0, "post_small_blind", 50), entry(1, "post_big_blind", 100)]


@pytest.fixture(scope="module")
def player():
    return ArenaPlayer([SHIPPED], np.random.default_rng(3), companions=[TAPER])


@contextmanager
def forcing(player, action=FOLD, guard=True, stored=True):
    """Every strategy answers `action`; with `stored` no lookup runs, so no miss is counted (as test_price_guard)."""
    saved = [(s, s.agent) for s in player.ladder + player.companions]

    def forced(agent):
        def ask(*args, **kwargs):
            if not stored:
                agent(*args, **kwargs)
            return action
        return ask

    for solver, agent in saved:
        solver.agent = forced(agent)
    player.price_misread = guard
    try:
        yield
    finally:
        for solver, agent in saved:
            solver.agent = agent
        player.price_misread = False
        player.river = False
        player.profiles = None
        player.opponent = None


@pytest.fixture
def equity(monkeypatch):
    """Fix the guard's equity-against-random read (the 200-sample, seed-17 call) and leave every other call alone."""
    real = pokerbot_native.equity_vs_random

    def install(value):
        def fake(hole, board, samples, seed, *rest):
            if (samples, seed) == (200, 17):
                return value
            return real(hole, board, samples, seed, *rest)
        monkeypatch.setattr(pokerbot_native, "equity_vs_random", fake)
    return install


def decide(player, state, valid=("fold", "call", "raise"), seat=1):
    return player.decide(state, list(valid), seat)


def collapsed_flop(hole, bet, stack=8500):
    """test_price_guard's collapsed pattern: a preflop third raise read as all-in, called, then a flop bet."""
    return {"hand_number": 10, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": hole,
            "pot": 3000 + bet, "your_stack": stack, "opponent_stacks": [8500 - bet], "to_call": bet,
            "min_raise": 2 * bet, "max_raise": stack,
            "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "raise", 525),
                                        entry(0, "raise", 1500), entry(1, "call", 975),
                                        entry(1, "check", 0, "flop"), entry(0, "raise", bet, "flop")]}


def min_reraised_flop(hole, board=("Ah", "Tc", "4s")):
    """We bet 300 into 400 on the flop and they min-raise, keeping 9,200: the one-raise primary reads it as all-in."""
    return {"hand_number": 3, "phase": "flop", "board": list(board), "your_hole_cards": hole,
            "pot": 1300, "your_stack": 9500, "opponent_stacks": [9200], "to_call": 300,
            "min_raise": 900, "max_raise": 9500,
            "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 100),
                                        entry(1, "raise", 300, "flop"), entry(0, "raise", 600, "flop")]}


def min_reraised_river(hole, board=("Ah", "Tc", "4s", "2d", "8c")):
    """The same shape on the river after two checked streets."""
    return {"hand_number": 4, "phase": "river", "board": list(board), "your_hole_cards": hole,
            "pot": 1300, "your_stack": 9500, "opponent_stacks": [9200], "to_call": 300,
            "min_raise": 900, "max_raise": 9500,
            "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 100),
                                        entry(1, "check", 0, "flop"), entry(0, "check", 0, "flop"),
                                        entry(1, "check", 0, "turn"), entry(0, "check", 0, "turn"),
                                        entry(1, "raise", 300, "river"), entry(0, "raise", 600, "river")]}


# ============================================================================================== price guard

def test_guard_fires_at_a_price_of_exactly_a_quarter_and_not_one_chip_above(player):
    # 1,500 into 4,500 is 1,500 / 6,000 = 0.25 exactly: the threshold is inclusive (price <= MISREAD_PRICE).
    with forcing(player, stored=False):
        at = decide(player, collapsed_flop(["Ts", "9h"], 1500))
        above = decide(player, collapsed_flop(["Ts", "9h"], 1501))
    assert str(at["record"]["companion"]).startswith("collapsed:"), at["record"]
    assert str(above["record"]["companion"]).startswith("collapsed:"), above["record"]
    assert at["action"] == "call" and at["record"]["adjusted"] == "priced a misread all-in"
    assert above["action"] == "fold" and above["record"]["adjusted"] is None


def test_guard_equity_line_is_inclusive_at_one_half(player, equity):
    state = collapsed_flop(["Ts", "9h"], 500)
    equity(ArenaPlayer.MISREAD_EQUITY)
    with forcing(player, stored=False):
        assert decide(player, state)["action"] == "call"
    equity(ArenaPlayer.MISREAD_EQUITY - 1e-6)
    with forcing(player, stored=False):
        out = decide(player, state)
    assert out["action"] == "fold" and out["record"]["adjusted"] is None


def covered_flop():
    """
    We started with 1,100 to their 10,000. 300 each preflop, we bet 300 on the flop, they raise to 3,000 and keep
    6,700: to call is 2,700, and the 500 we have left is all of it.
    """
    return {"hand_number": 7, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": ["Ad", "Qh"],
            "pot": 3900, "your_stack": 500, "opponent_stacks": [6700], "to_call": 2700,
            "min_raise": 0, "max_raise": 500,
            "action_history": BLINDS + [entry(0, "raise", 300), entry(1, "call", 200),
                                        entry(1, "raise", 300, "flop"), entry(0, "raise", 3000, "flop")]}


def test_guard_prices_only_the_chips_we_can_call_when_our_stack_is_shorter(player, monkeypatch):
    # The arithmetic alone, with the misread test held true: 2,700 into 3,900 is 0.41 at full size, but we call our
    # last 500 and their 2,200 beyond it comes back, so the price is 500 / (3,900 - 2,200 + 500) = 0.227. (A
    # collapsed re-read with a stack this short cannot be built from the shipped trees: below about 5,000 behind
    # the re-read misses too, and the price can only be under a quarter here with 1,500 or less behind.)
    monkeypatch.setattr(ArenaPlayer, "_misread", staticmethod(lambda *args: True))
    with forcing(player):
        out = decide(player, covered_flop(), ("fold", "call"))
    assert out["action"] == "call" and out["record"]["adjusted"] == "priced a misread all-in", out["record"]
    # And at a full-size price the same spot stays a fold: 2,700 / 6,600 with 9,000 behind.
    deep = dict(covered_flop(), your_stack=9000, max_raise=9000)
    with forcing(player):
        out = decide(player, deep, ("fold", "call"))
    assert out["action"] == "fold" and out["record"]["adjusted"] is None, out["record"]


def test_a_fold_made_by_a_read_is_left_alone_even_on_a_misread_history(player, equity):
    # "Bluff withheld" turns the strategy's raise into a fold against a station. The history ends in an all-in
    # read with chips behind and the equity is forced high, so only the guard's "no read changed it" test
    # (adjusted == river_shove or short_stack) keeps the read's fold.
    equity(0.9)
    state = min_reraised_flop(["3h", "2c"], board=("Qc", "9s", "Kd"))
    with forcing(player, action=RAISE_HALF):
        player.profiles = Profiles("/nonexistent/opp.json")
        player.profiles.rows["station"] = {"bets_faced": 500, "folds": 10, "calls": 490, "raises": 0, "hands": 300}
        player.opponent = "station"
        out = decide(player, state)
    assert out["record"]["history"].endswith(str(ALL_IN)), out["record"]
    assert out["action"] == "fold" and out["record"]["adjusted"] == "bluff withheld", out["record"]
    # The control: the same spot with the strategy's own fold is called, so the test above can tell the two apart.
    with forcing(player, action=FOLD):
        control = decide(player, state)
    assert control["action"] == "call" and control["record"]["adjusted"] == "priced a misread all-in"


def test_a_fold_the_rule_made_after_a_miss_is_never_priced(player, equity):
    # The fallback rule prices the arena's own pot, so answered_history is None and the guard cannot fire, even
    # with a strong hand at a small price and the collapsed re-read unavailable. Forcing every lookup to miss is
    # done by giving the companion nothing and the primary a history it cannot hold: a fourth preflop raise.
    equity(0.9)
    state = {"hand_number": 5, "phase": "preflop", "board": [], "your_hole_cards": ["Ah", "Kd"],
             "pot": 2600, "your_stack": 8500, "opponent_stacks": [8100], "to_call": 400,
             "min_raise": 2400, "max_raise": 8500,
             "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "raise", 600), entry(0, "raise", 1400),
                                         entry(1, "raise", 1500), entry(0, "raise", 1900)]}
    with forcing(player, action=FOLD, stored=False):
        out = decide(player, state)
    if not out["record"]["fallback"]:
        pytest.skip(f"the shipped trees answered this history ({out['record']['companion']}); no fallback to test")
    assert out["record"]["adjusted"] != "priced a misread all-in", out["record"]


def test_guard_off_and_flag_untouched_records_carry_no_new_reason(player):
    with forcing(player, guard=False):
        out = decide(player, min_reraised_flop(["Ad", "Qh"]))
    assert out["action"] == "fold" and out["record"]["adjusted"] is None
    assert player.stats.misread_prices_called >= 0 and "withheld" not in out["record"]


def test_a_bet_that_puts_us_all_in_is_a_real_all_in_even_if_the_bettor_kept_chips(player):
    state = covered_flop()
    with forcing(player):
        out = decide(player, state, ("fold", "call"))
    if not out["record"]["history"].endswith(str(ALL_IN)):
        pytest.fail(f"precondition: the primary should read an all-in here: {out['record']}")
    assert out["action"] == "fold" and out["record"]["adjusted"] is None, out["record"]


def test_a_river_solve_fold_is_not_second_guessed(player, monkeypatch):
    def solved_fold(*args, **kwargs):
        return types.SimpleNamespace(choice=FOLD, iterations=1, ms=0.0, hands=1, range_source="blueprint",
                                     distribution={FOLD: 1.0})
    monkeypatch.setattr(player_module, "decide_river", solved_fold)
    state = min_reraised_river(["Ad", "Qh"], board=("Ah", "Tc", "4s", "2d", "8c"))
    with forcing(player):
        player.river = True
        out = decide(player, state)
    if not (out["record"]["river"] and "error" not in out["record"]["river"]
            and out["record"]["history"].endswith(str(ALL_IN))):
        pytest.fail(f"precondition: a river solve on an all-in read: {out['record']}")
    assert out["action"] == "fold" and out["record"]["adjusted"] is None, out["record"]


def test_price_guard_audit_reproduces_eight_firings_and_23404_chips():
    if not glob.glob(os.path.join(MATCHES, "*.jsonl")):
        pytest.skip("no match logs on this machine")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "audit_price_guard.py")],
                         capture_output=True, text=True, timeout=900, cwd=ROOT)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "firings: 8, with their cards shown: 8, estimated chips from calling instead: +23,404" in out.stdout


# ============================================================================================== posterior reads

def _field(rate_key, rows, posteriors=True, **flags):
    p = Profiles("/nonexistent/opponents.json", posteriors=posteriors, scout_reads=True, **flags)
    p.rows = rows
    return p


def _row(hands=4000, **extra):
    row = {"bets_faced": 0, "folds": 0, "calls": 0, "raises": 0, "hands": hands, "net": 0, "by_history": {}}
    row.update(extra)
    return row


def test_a_row_with_zero_trials_for_a_rate_is_the_prior_and_divides_by_nothing():
    rows = {f"b{i}": _row(river_bets=200, river_bluffs=20 + 10 * i) for i in range(6)}
    rows["blank"] = _row(river_bets=0, river_bluffs=0)
    p = _field("river_bluff", rows)
    mean, strength = p.prior("river_bluff")
    assert p.posterior("blank", "river_bluff") == pytest.approx((mean * strength, (1 - mean) * strength))
    assert 0.0 < p.lower("blank", "river_bluff") < p.upper("blank", "river_bluff") < 1.0
    assert not p.never_bluffs("blank") and p.river_bluff_floor("blank") is None


def test_a_file_with_one_bot_uses_the_uniform_prior_and_still_reads_it():
    p = _field("river_bluff", {"only": _row(river_bets=150, river_bluffs=0, hands=3000)})
    assert p.prior("river_bluff") == (0.5, op.PRIOR_MIN_STRENGTH)
    assert p.never_bluffs("only") and p.river_never_bluffs("only")


def test_a_bin_no_bot_has_gives_a_uniform_prior_and_no_read():
    rows = {f"b{i}": _row(bets_faced=500, folds=200, calls=250, raises=50) for i in range(6)}
    p = _field("open_fold", rows)
    assert p.prior("open_fold") == (0.5, op.PRIOR_MIN_STRENGTH)
    assert p.prior("three_bet_fold") == (0.5, op.PRIOR_MIN_STRENGTH)
    for read in ("folds_blind", "never_three_bets", "folds_to_three_bet"):
        assert not getattr(p, read)("b0")
    assert p.reraise_floor("b0") is None and p.postflop_fold_floor("b0") is None


def test_an_empty_file_reads_nothing_and_does_not_raise():
    p = _field("fold_to_bet", {})
    assert p.prior("fold_to_bet") == (0.5, op.PRIOR_MIN_STRENGTH)
    assert not p.never_folds("x") and not p.never_calls("x") and p.fold_floor_upper("x") is None


def test_the_prior_mean_is_clamped_off_zero_for_a_field_that_never_bluffs():
    rows = {f"b{i}": _row(river_bets=300, river_bluffs=0) for i in range(6)}
    mean, strength = fit_prior(rows, "river_bluff")
    assert mean == 0.01 and strength == op.PRIOR_MAX_STRENGTH
    p = _field("river_bluff", rows)
    assert 0.0 < p.upper("b0", "river_bluff") < op.HONEST_RIVER_BOUND


def test_bounds_are_monotone_in_the_bots_own_data_although_it_is_in_the_prior_fit():
    # Zero bluffs over more and more river bets: the upper bound must never rise, even though each step also
    # moves the fitted prior (the bot is one of five in the fit).
    uppers = []
    for bets in (40, 60, 100, 150, 250, 400, 800, 2000):
        rows = {f"b{i}": _row(river_bets=200, river_bluffs=30 + 15 * i) for i in range(4)}
        rows["z"] = _row(river_bets=bets, river_bluffs=0, hands=bets * 20)
        uppers.append(_field("river_bluff", rows).upper("z", "river_bluff"))
    assert uppers == sorted(uppers, reverse=True), uppers
    # More folds at the same number of trials: the lower bound only rises.
    lowers = []
    for folds in range(0, 41, 4):
        rows = {f"b{i}": _row(by_history={"preflop:TrUr": {"fold": 10 + 3 * i, "call": 20, "raise": 2}})
                for i in range(5)}
        rows["x"] = _row(by_history={"preflop:TrUr": {"fold": folds, "call": 40 - folds}})
        lowers.append(_field("three_bet_fold", rows).lower("x", "three_bet_fold"))
    assert lowers == sorted(lowers), lowers


def test_bots_below_the_trial_floor_do_not_enter_the_prior():
    rows = {f"b{i}": _row(river_bets=200, river_bluffs=20 + 10 * i) for i in range(5)}
    with_thin = dict(rows, thin=_row(river_bets=5, river_bluffs=5, hands=50))
    assert fit_prior(rows, "river_bluff") == fit_prior(with_thin, "river_bluff")


def test_observe_and_rebuild_refit_the_prior(tmp_path):
    p = Profiles(str(tmp_path / "none.json"), posteriors=True)
    p.rows = {f"b{i}": {"bets_faced": 400, "folds": 40 + 40 * i, "calls": 300, "raises": 60 - 40 * i + 40 * i,
                        "hands": 800, "net": 0, "by_history": {}} for i in range(5)}
    first = p.prior("fold_to_bet")
    hand = {"action_history": [entry(0, "post_small_blind", 50), entry(1, "post_big_blind", 100)] +
            [entry(0, "raise", 300), entry(1, "fold", 0)]}
    for _ in range(300):
        p.observe(hand, 0, "b0")
    assert p.prior("fold_to_bet") != first          # the cache was dropped and the field's spread moved
    p.rebuild(str(tmp_path))                        # no scouted rows, no logs: the file is empty
    assert p.prior("fold_to_bet") == (0.5, op.PRIOR_MIN_STRENGTH)


def _boundary(monkeypatch, which, value):
    monkeypatch.setattr(Profiles, which, lambda self, name, rate: value)


@pytest.mark.parametrize("read,row,which,fires,misses", [
    # read, a row past every minimum, the bound it reads, a value that fires at the line, one just past it
    ("folds_blind", _row(by_history={"preflop:Ur": {"fold": op.POSTERIOR_BLIND_MIN}}), "lower",
     op.FOLD_BLIND_RATE, op.FOLD_BLIND_RATE - 1e-9),
    ("folds_to_three_bet", _row(by_history={"preflop:TrUr": {"fold": op.POSTERIOR_THREE_BET_MIN}}), "lower",
     op.THREE_BET_BREAK_EVEN, op.THREE_BET_BREAK_EVEN - 1e-9),
    ("never_bluffs", _row(river_bets=op.NEVER_BLUFF_MIN), "upper",
     op.NEVER_BLUFF_BOUND - 1e-9, op.NEVER_BLUFF_BOUND),
    ("never_three_bets", _row(by_history={"preflop:Ur": {"call": op.RARE_RAISE_MIN}}), "upper",
     op.RARE_RAISE_BOUND, op.RARE_RAISE_BOUND + 1e-9),
    ("river_never_bluffs", _row(river_bets=op.HONEST_RIVER_MIN, river_bluffs=1), "upper",
     op.HONEST_RIVER_BOUND, op.HONEST_RIVER_BOUND + 1e-9),
    ("never_folds", _row(bets_faced=op.SEQ_MIN_OBSERVED), "upper",
     op.EQUILIBRIUM_FOLD - 1e-9, op.EQUILIBRIUM_FOLD),
    ("never_calls", _row(calls=op.SEQ_MIN_OBSERVED // 2), "upper",
     op.NEVER_CALL_SHARE - 1e-9, op.NEVER_CALL_SHARE),
])
def test_each_read_at_its_line_and_its_minimum(monkeypatch, read, row, which, fires, misses):
    p = _field(None, {"x": json.loads(json.dumps(row))})
    _boundary(monkeypatch, which, fires)
    assert getattr(p, read)("x"), f"{read} at its line"
    _boundary(monkeypatch, which, misses)
    assert not getattr(p, read)("x"), f"{read} just past its line"
    # One trial short of the minimum, at a bound that would fire, the read stays off.
    _boundary(monkeypatch, which, fires)
    short = json.loads(json.dumps(row))
    if read == "folds_blind":
        short["by_history"]["preflop:Ur"]["fold"] -= 1
    elif read == "folds_to_three_bet":
        short["by_history"]["preflop:TrUr"]["fold"] -= 1
    elif read == "never_three_bets":
        short["by_history"]["preflop:Ur"]["call"] -= 1
    elif read in ("never_bluffs", "river_never_bluffs"):
        short["river_bets"] -= 1
    elif read == "never_folds":
        short["bets_faced"] -= 1
    elif read == "never_calls":
        short["calls"] -= 1
    p.rows["x"] = short
    assert not getattr(p, read)("x"), f"{read} one under its minimum"


def test_the_sizing_tell_at_its_two_lines(monkeypatch):
    p = _field(None, {"x": _row(big_bets=op.BIG_BET_MIN, small_bets=op.BIG_BET_MIN)})
    monkeypatch.setattr(Profiles, "upper", lambda self, n, r: op.BIG_BET_AIR_RATE - 1e-9)
    monkeypatch.setattr(Profiles, "lower", lambda self, n, r: op.SMALL_BET_AIR_RATE)
    assert p.big_bets_are_value("x")
    monkeypatch.setattr(Profiles, "upper", lambda self, n, r: op.BIG_BET_AIR_RATE)
    assert not p.big_bets_are_value("x")
    p.rows["x"]["small_bets"] -= 1
    monkeypatch.setattr(Profiles, "upper", lambda self, n, r: 0.0)
    assert not p.big_bets_are_value("x")


def test_river_exact_zero_stands_even_when_its_bound_is_over_the_line():
    # A field of heavy bluffers lifts a zero's bound: 0 of 100 here sits above HONEST_RIVER_BOUND, and the read
    # still fires, because under posteriors the exact zero is kept ("never stricter than the zero"). The existing
    # tests only reach the bound branch (runner1's bound is under the line), never this one.
    rows = {f"b{i}": _row(river_bets=300, river_bluffs=90 + 20 * i) for i in range(6)}
    rows["zero"] = _row(river_bets=op.HONEST_RIVER_MIN, river_bluffs=0, hands=800)
    p = _field("river_bluff", rows)
    assert p.upper("zero", "river_bluff") > op.HONEST_RIVER_BOUND
    assert p.river_never_bluffs("zero")
    rows["zero"]["river_bets"] = op.HONEST_RIVER_MIN - 1
    assert not p.river_never_bluffs("zero")


def test_an_exact_zero_over_many_river_bets_is_believed_under_posteriors_as_on_main():
    rows = {f"b{i}": _row(river_bets=2000, river_bluffs=800, hands=40000) for i in range(30)}
    rows["zero"] = _row(river_bets=150, river_bluffs=0, hands=3000)
    off, on = _field("river_bluff", rows, posteriors=False), _field("river_bluff", rows)
    if not (off.never_bluffs("zero") and off.river_never_bluffs("zero")):
        pytest.fail("precondition: main reads the zero as honest")
    assert on.never_bluffs("zero") and on.river_never_bluffs("zero")


def test_posteriors_off_never_loads_scipy():
    code = ("import sys; sys.path.insert(0, %r)\n"
            "from chipzen.opponents import Profiles\n"
            "p = Profiles(%r, sequential=True, scout_reads=True)\n"
            "[getattr(p, r)(n) for n in p.rows for r in ('never_folds', 'never_calls', 'folds_blind', 'never_bluffs',"
            " 'river_never_bluffs', 'folds_to_three_bet', 'never_three_bets', 'big_bets_are_value')]\n"
            "print('scipy' in sys.modules)") % (ROOT, PROFILES)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-1500:]
    assert out.stdout.strip() == "False"


def test_bluff_break_even_corners():
    # An all-in facing a bet from a shorter opponent: we can only put in their stack plus the call.
    facing = {"pot": 1000, "to_call": 400, "your_stack": 9000, "opponent_stacks": [600]}
    assert ArenaPlayer.bluff_break_even(ALL_IN, facing) == pytest.approx(1000 / 2000)
    # Nothing in the pot and nothing to bet: no bluff can break even, and the rule does not divide by zero.
    assert ArenaPlayer.bluff_break_even(RAISE_POT, {"pot": 0, "to_call": 0, "your_stack": 0,
                                                    "opponent_stacks": [0]}) == 1.0


def test_size_aware_bluffs_without_posteriors_is_main_s_rule():
    # --size-aware-bluffs on its own must change nothing: the switch is read only under posteriors.
    def run(size_aware):
        p = ArenaPlayer([SHIPPED], np.random.default_rng(9))
        p.profiles = Profiles("/nonexistent/opp.json")
        p.profiles.rows["hoops"] = {"bets_faced": 6132, "folds": 1228, "calls": 4474, "raises": 430, "hands": 12399}
        p.opponent = "hoops"
        p.size_aware_bluffs = size_aware
        weak = {"hand_number": 1, "phase": "flop", "board": ["Qc", "9s", "Kd"], "your_hole_cards": ["3h", "2c"],
                "pot": 400, "your_stack": 9800, "opponent_stacks": [9800], "to_call": 0,
                "min_raise": 100, "max_raise": 9800,
                "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 200),
                                            entry(1, "check", 0, "flop")]}
        return [(o["action"], o["record"]["adjusted"]) for o in (p.decide(weak, ["check", "raise"], 0)
                                                                 for _ in range(40))]
    off, on = run(False), run(True)
    assert off == on
    assert any(adj == "bluff withheld" for _, adj in off)


# ============================================================================================== flags off = main

def _module_from(commit, path, name, tmp_path):
    source = subprocess.run(["git", "-C", ROOT, "show", f"{commit}:{path}"], capture_output=True, text=True,
                            check=True).stdout
    file = tmp_path / f"{name}.py"
    file.write_text(source)
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


READS = ("folds_blind", "never_bluffs", "never_three_bets", "river_never_bluffs", "folds_to_three_bet",
         "big_bets_are_value", "river_bluff_floor", "postflop_fold_floor", "reraise_floor", "never_folds",
         "never_calls", "fold_to_bet")


def test_with_posteriors_off_every_read_on_the_real_file_is_main_s(tmp_path):
    if not os.path.exists(PROFILES):
        pytest.skip("no profile file on this machine")
    old = _module_from(BEFORE_GUARD, "chipzen/opponents.py", "opponents_37219c6", tmp_path)
    compared = 0
    for sequential in (False, True):
        for bankroll in (False, True):
            for scout in (False, True):
                new_p = Profiles(PROFILES, sequential=sequential, bankroll=bankroll, scout_reads=scout)
                old_p = old.Profiles(PROFILES, sequential=sequential, bankroll=bankroll, scout_reads=scout)
                for name in list(new_p.rows) + ["stranger"]:
                    for read in READS:
                        assert getattr(new_p, read)(name) == getattr(old_p, read)(name), (name, read)
                        compared += 1
    assert compared > 1000


def test_the_first_rebuild_of_a_pre_fix_file_counts_as_main_did_and_the_second_no_longer_grows(tmp_path):
    old = _module_from(BEFORE_BASE, "chipzen/opponents.py", "opponents_c7dd020", tmp_path)
    logs = tmp_path / "logs"
    logs.mkdir()
    rows = [{"frame": "match_start", "seat": 0, "at": 1_800_000_000,
             "seats": [{"display_name": "us", "is_self": True}, {"display_name": "stranger", "is_self": False}]}]
    for h in range(1, 4):
        rows.append({"frame": "round_start", "state": {"stacks": [10000, 10000]}})
        rows.append({"frame": "round_result", "result": {"hand_number": h, "stacks": [10100, 9900], "action_history": [
            entry(0, "post_small_blind", 50), entry(1, "post_big_blind", 100),
            entry(0, "raise", 300), entry(1, "call", 200)]}})
    (logs / "m1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    saved = {"stranger": {"bets_faced": 500, "folds": 100, "calls": 350, "raises": 50, "hands": 600, "net": 0,
                          "by_history": {"preflop:Ur": {"call": 350}}, "scouted": True},
             "live_only": {"bets_faced": 77, "folds": 7, "calls": 70, "raises": 0, "hands": 99, "net": 5,
                           "by_history": {}}}
    for tag in ("old", "new"):
        (tmp_path / f"{tag}.json").write_text(json.dumps(saved))
    old_p = old.Profiles(str(tmp_path / "old.json")).rebuild(str(logs))
    new_p = Profiles(str(tmp_path / "new.json")).rebuild(str(logs))
    strip = lambda row: {k: v for k, v in row.items() if k != "scout_base"}  # noqa: E731
    assert strip(new_p.rows["stranger"]) == strip(old_p.rows["stranger"])
    assert "live_only" not in new_p.rows and "live_only" not in old_p.rows   # a row not scouted is recounted
    old_p.save(), new_p.save()
    old_again = old.Profiles(str(tmp_path / "old.json")).rebuild(str(logs))
    new_again = Profiles(str(tmp_path / "new.json")).rebuild(str(logs))
    assert old_again.rows["stranger"]["hands"] == 606                       # main's bug: the live hands twice
    assert new_again.rows["stranger"]["hands"] == 603


@pytest.mark.skipif(not os.path.isdir(LADDER) or not glob.glob(os.path.join(MATCHES, "*.jsonl")),
                    reason="needs the v5xRR3 ladder and the match logs")
def test_with_all_three_flags_off_decisions_are_main_s_on_logged_states(tmp_path):
    """
    About 2,000 turn states rebuilt from logged matches (the mr_hide matches of the guard's firings among them),
    played by the production ladder with the burst's flags (--stack-cap --purify all --sequential-triggers
    --scout-reads, deep primary), once by 37219c6's chipzen package and once by this tree's.
    """
    from chipzen.bridge import _contributions
    files = sorted(glob.glob(os.path.join(MATCHES, "*.jsonl")))
    pick = [f for f in files if os.path.basename(f)[:8] in ("f1a0b755", "f1dd11ec", "b5b90d8e", "ba45b472")] \
        + files[::40]
    states = []
    for path in pick:
        seat, start, decisions = None, None, []
        for line in open(path):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            frame = r.get("frame")
            if frame == "match_start":
                seat = r.get("seat")
            elif frame == "round_start":
                start, decisions = r.get("state") or {}, []
            elif frame == "decision":
                decisions.append(r)
            elif frame == "round_result" and start and seat is not None:
                hist = (r.get("result") or {}).get("action_history") or []
                ours = [i for i, a in enumerate(hist) if a.get("seat") == seat
                        and not str(a.get("action", "")).startswith("post")]
                for k, d in enumerate(decisions):
                    if k >= len(ours) or not start.get("stacks") or hist[ours[k]].get("phase") != d.get("phase"):
                        continue
                    put = _contributions(hist[:ours[k]])
                    mine = int(start["stacks"][seat]) - put[seat]
                    theirs = int(start["stacks"][1 - seat]) - put[1 - seat]
                    to_call = int(d.get("to_call") or 0)
                    valid = (["fold", "call"] + (["raise"] if mine > to_call and theirs > 0 else [])) \
                        if to_call > 0 else ["check", "raise"]
                    states.append({"seat": seat, "opponent": d.get("opponent"), "valid": valid, "state": {
                        "hand_number": d.get("hand"), "phase": d.get("phase"), "board": d.get("board") or [],
                        "your_hole_cards": d.get("hole"), "pot": int(d.get("pot") or 0), "your_stack": mine,
                        "opponent_stacks": [theirs], "to_call": to_call, "min_raise": min(mine, max(2 * to_call, 200)),
                        "max_raise": mine, "action_history": hist[:ours[k]]}})
                start = None
    assert len(states) > 500
    (tmp_path / "states.json").write_text(json.dumps(states))
    old_root = tmp_path / "old"
    old_root.mkdir()
    archive = subprocess.run(["git", "-C", ROOT, "archive", BEFORE_GUARD, "chipzen"], capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(old_root)], input=archive.stdout, check=True)
    # The push-fold table is found relative to the package, so the old copy needs the same results directory.
    os.symlink(os.path.join(ROOT, "results"), old_root / "results")
    driver = tmp_path / "drive.py"
    driver.write_text(
        "import json, sys\n"
        "root, out = sys.argv[1], sys.argv[2]\n"
        f"sys.path[:0] = [root, {ROOT!r}]\n"
        "import numpy as np\n"
        "import chipzen.player as P\n"
        "from chipzen.opponents import Profiles\n"
        "assert P.__file__.startswith(root), P.__file__\n"
        "from scripts.chipzen_run import ladder_paths\n"
        f"_, ladder, companions = ladder_paths({LADDER!r}, True)\n"
        "player = P.ArenaPlayer(ladder, np.random.default_rng(11), companions=companions, purify='all', stack_cap=True)\n"
        f"player.profiles = Profiles({PROFILES!r}, sequential=True, scout_reads=True)\n"
        f"states = json.load(open({str(tmp_path / 'states.json')!r}))\n"
        "rows = []\n"
        "for s in states:\n"
        "    player.opponent = s['opponent']\n"
        "    d = player.decide(s['state'], s['valid'], s['seat'])\n"
        "    r = d['record']\n"
        "    rows.append([r['choice'], d['action'], d['params'].get('amount'), r['adjusted'], r['companion']])\n"
        "json.dump(rows, open(out, 'w'))\n")
    results = {}
    for tag, root in (("old", str(old_root)), ("new", ROOT)):
        out = tmp_path / f"{tag}.json"
        run = subprocess.run([sys.executable, str(driver), root, str(out)], capture_output=True, text=True,
                             timeout=900)
        assert run.returncode == 0, run.stderr[-2000:]
        results[tag] = json.loads(out.read_text())
    differ = [i for i, (a, b) in enumerate(zip(results["old"], results["new"])) if a != b]
    assert len(results["old"]) == len(states) and not differ, [(i, results["old"][i], results["new"][i])
                                                               for i in differ[:5]]


# ============================================================================================== scout_base

def _log(directory, opponent="stranger", hands=3, name="m1.jsonl", at=1_800_000_000):
    rows = [{"frame": "match_start", "seat": 0, "at": at,
             "seats": [{"display_name": "us", "is_self": True}, {"display_name": opponent, "is_self": False}]}]
    for h in range(1, hands + 1):
        rows.append({"frame": "round_start", "state": {"stacks": [10000, 10000]}})
        rows.append({"frame": "round_result", "result": {"hand_number": h, "stacks": [10100, 9900], "action_history": [
            entry(0, "post_small_blind", 50), entry(1, "post_big_blind", 100),
            entry(0, "raise", 300), entry(1, "call", 200)]}})
    (directory / name).write_text("\n".join(json.dumps(r) for r in rows) + "\n")


BASE = {"bets_faced": 500, "folds": 100, "calls": 350, "raises": 50, "hands": 600, "matches": 15, "net": 0,
        "by_history": {"preflop:Ur": {"call": 350}}, "scouted": True}


def test_live_hands_never_reach_the_scout_base_nested_counts(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    _log(logs, hands=4)
    path = tmp_path / "opponents.json"
    path.write_text(json.dumps({"stranger": dict(json.loads(json.dumps(BASE)), scout_base=json.loads(json.dumps(BASE)))}))
    for _ in range(3):
        p = Profiles(str(path)).rebuild(str(logs))
        p.save()
    row = Profiles(str(path)).rows["stranger"]
    assert row["by_history"]["preflop:Ur"]["call"] == 354
    assert row["scout_base"]["by_history"]["preflop:Ur"]["call"] == 350          # the base is never aliased
    assert row["scout_base"]["hands"] == 600 and row["matches"] == 15          # live hands do not touch matches
    assert op.matches_of(row) == pytest.approx(15 + 4 / op.HANDS_PER_MATCH)


def test_a_reseeded_base_replaces_the_old_one_on_the_next_start(tmp_path):
    # --reseed writes a fresh, smaller scout row with its own scout_base; the next start must count from it.
    logs = tmp_path / "logs"
    logs.mkdir()
    _log(logs, hands=2)
    path = tmp_path / "opponents.json"
    inflated = dict(BASE, hands=9000, bets_faced=7000)
    path.write_text(json.dumps({"stranger": inflated}))                         # a pre-fix row, frozen as its base
    Profiles(str(path)).rebuild(str(logs)).save()
    assert Profiles(str(path)).rows["stranger"]["scout_base"]["hands"] == 9000
    fresh = dict(BASE)
    rows = json.loads(path.read_text())
    rows["stranger"] = dict(fresh, scout_base=dict(fresh))                      # what the scout script writes
    path.write_text(json.dumps(rows))
    again = Profiles(str(path)).rebuild(str(logs))
    assert again.rows["stranger"]["hands"] == 602 and again.rows["stranger"]["scout_base"]["hands"] == 600


def test_rows_that_are_not_scouted_are_live_counts_only_and_carry_no_base(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    _log(logs, opponent="newbot", hands=3)
    path = tmp_path / "opponents.json"
    path.write_text(json.dumps({"newbot": {"bets_faced": 900, "folds": 9, "calls": 891, "raises": 0, "hands": 999,
                                           "net": 0, "by_history": {}},
                                "gone": {"bets_faced": 9, "folds": 1, "calls": 8, "raises": 0, "hands": 9}}))
    for _ in range(2):
        p = Profiles(str(path)).rebuild(str(logs))
        p.save()
    rows = Profiles(str(path)).rows
    assert set(rows) == {"newbot"}
    assert rows["newbot"]["hands"] == 3 and rows["newbot"]["bets_faced"] == 3 and "scout_base" not in rows["newbot"]


def test_a_scouted_row_with_no_live_hands_is_its_base_exactly(tmp_path):
    path = tmp_path / "opponents.json"
    path.write_text(json.dumps({"stranger": dict(BASE, scout_base=dict(BASE))}))
    p = Profiles(str(path)).rebuild(str(tmp_path / "no_logs"))
    assert {k: v for k, v in p.rows["stranger"].items() if k != "scout_base"} == BASE


def test_the_same_log_in_two_directories_counts_once(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    _log(a, hands=3)
    _log(b, hands=3)                                                            # the copy under the log dir
    path = tmp_path / "opponents.json"
    path.write_text(json.dumps({"stranger": dict(BASE, scout_base=dict(BASE))}))
    p = Profiles(str(path)).rebuild(str(a), str(b))
    assert p.rows["stranger"]["hands"] == 603
