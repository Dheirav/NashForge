"""
The misread-price guard (`ArenaPlayer.price_misread`, 5 October).

On 5 October against mr_hide a third raise on the turn was read as all-in
although the bettor kept 2,174 chips; the river shove of those chips into
16,080 was answered on the collapsed re-read, and a jack-high flush folded at
11%. The guard calls such a fold at the real price when the hand is strong.

The shipped solvers do not fold a strong hand on these histories by
themselves, so every test forces the strategy's answer to a fold while leaving
the lookup itself in place: the miss counting, the companion and the collapsed
re-read all run exactly as in a match, and only the action that comes back is
fixed. What is tested is then the guard's conditions, one at a time.
"""
import os
from contextlib import contextmanager

import numpy as np
import pytest

from abstraction.betting import FOLD
from chipzen.player import ArenaPlayer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHIPPED = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")
TAPER = os.path.join(ROOT, "results", "cfr", "nolimit_taper_42.pkl")


def entry(seat, action, amount, phase="preflop"):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase, "is_timeout": False}


BLINDS = [entry(0, "post_small_blind", 50), entry(1, "post_big_blind", 100)]


@pytest.fixture(scope="module")
def player():
    return ArenaPlayer([SHIPPED], np.random.default_rng(3), companions=[TAPER])


@contextmanager
def folding(player, guard=True, stored=False):
    """
    Every strategy lookup still runs (so misses are counted), and then folds.

    With `stored` the lookup is skipped and no miss is counted, as if the
    primary held the node: the shipped trees have no all-in-only level, so a
    pseudo all-in they can answer cannot be built from them, while the v5
    ladder's cap-2 rungs answer one at every third raise (5 Oct, turn).
    """
    saved = [(s, s.agent) for s in player.ladder + player.companions]

    def forced(agent):
        def ask(*args, **kwargs):
            if not stored:
                agent(*args, **kwargs)
            return FOLD
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


def collapsed_flop(hole, bet):
    """
    The pattern of v5f's burst (and of the existing collapsed test): a preflop
    third raise read as all-in, called, then a flop. We are the big blind, check,
    and face a bet of `bet` with chips behind on both sides.
    """
    return {"hand_number": 10, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": hole,
            "pot": 3000 + bet, "your_stack": 8500, "opponent_stacks": [8500 - bet], "to_call": bet,
            "min_raise": 2 * bet, "max_raise": 8500,
            "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "raise", 525),
                                        entry(0, "raise", 1500), entry(1, "call", 975),
                                        entry(1, "check", 0, "flop"), entry(0, "raise", bet, "flop")]}


def decide(player, state, valid=("fold", "call", "raise")):
    return player.decide(state, list(valid), 1)


def test_a_fold_on_a_collapsed_history_is_called_at_a_low_price_with_a_strong_hand(player):
    # 500 into 3,500 is a price of 0.125, and T9 on A-T-4 beats a random hand 75% of the time.
    before = player.stats.misread_prices_called
    with folding(player):
        out = decide(player, collapsed_flop(["Ts", "9h"], 500))
    record = out["record"]
    assert str(record["companion"]).startswith("collapsed:"), record
    assert out["action"] == "call", record
    assert record["adjusted"] == "priced a misread all-in"
    assert player.stats.misread_prices_called == before + 1


def test_the_guard_is_off_unless_asked_for(player):
    assert not player.price_misread          # the default
    with folding(player, guard=False):
        out = decide(player, collapsed_flop(["Ts", "9h"], 500))
    assert str(out["record"]["companion"]).startswith("collapsed:")
    assert out["action"] == "fold" and out["record"]["adjusted"] is None


def test_the_guard_does_not_call_at_a_high_price(player):
    # 3,000 into 6,000 is a price of a third, beyond the 0.25 threshold.
    with folding(player):
        out = decide(player, collapsed_flop(["Ts", "9h"], 3000))
    assert str(out["record"]["companion"]).startswith("collapsed:")
    assert out["action"] == "fold" and out["record"]["adjusted"] is None


def test_the_guard_does_not_call_with_a_weak_hand(player):
    # Seven-six with no pair and no draw on A-T-4: 28% against a random hand.
    with folding(player):
        out = decide(player, collapsed_flop(["7c", "6c"], 500))
    assert str(out["record"]["companion"]).startswith("collapsed:")
    assert out["action"] == "fold" and out["record"]["adjusted"] is None


def test_a_real_all_in_on_a_true_history_is_left_to_the_pot_odds_rule(player):
    # The river shove is for everything they have, and nothing earlier was
    # read as all-in, so the history the strategy answered is the hand.
    # 1,500 into 11,050 (0.12) is not the pot-odds rule's 10 to 1 either.
    state = {"hand_number": 9, "phase": "river", "board": ["3s", "Jc", "8s", "8h", "Qd"],
             "your_hole_cards": ["Js", "Jd"], "pot": 9550, "your_stack": 7950,
             "opponent_stacks": [0], "to_call": 1500, "min_raise": 0, "max_raise": 0,
             "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 100),
                                         entry(1, "check", 0, "flop"), entry(0, "check", 0, "flop"),
                                         entry(1, "raise", 800, "turn"), entry(0, "call", 800, "turn"),
                                         entry(1, "check", 0, "river"), entry(0, "raise", 1500, "river")]}
    # Their stack before the hand was 2,500, so the 1,500 is all of it.
    with folding(player):
        out = decide(player, state, ("fold", "call"))
    record = out["record"]
    assert not str(record["companion"]).startswith("collapsed:"), record
    assert out["action"] == "fold" and record["adjusted"] is None, record


def test_a_fold_on_a_true_history_is_left_alone(player):
    # A plain flop bet after a called open: nothing was misread, so a fold the
    # strategy makes is its own and the guard does not second-guess it.
    state = {"hand_number": 2, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": ["Ts", "9h"],
             "pot": 500, "your_stack": 9800, "opponent_stacks": [9700], "to_call": 100,
             "min_raise": 200, "max_raise": 9800,
             "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 100),
                                         entry(1, "check", 0, "flop"), entry(0, "raise", 100, "flop")]}
    with folding(player):
        out = decide(player, state)
    record = out["record"]
    assert record["companion"] is None and not record["history"].endswith("5"), record
    assert out["action"] == "fold" and record["adjusted"] is None, record


def test_a_raise_read_as_all_in_while_the_bettor_kept_chips_is_priced_too(player):
    # The one-raise primary has no sized re-raise, so their min-raise of our
    # flop bet is read as all-in although they keep 9,200 behind: 300 to call
    # into 1,300 is a price of 0.19, and the guard calls with top pair when
    # the strategy that folded was answering that history.
    state = {"hand_number": 3, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": ["Ad", "Qh"],
             "pot": 1300, "your_stack": 9500, "opponent_stacks": [9200], "to_call": 300,
             "min_raise": 900, "max_raise": 9500,
             "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 100),
                                         entry(1, "raise", 300, "flop"), entry(0, "raise", 600, "flop")]}
    with folding(player, stored=True):
        out = decide(player, state)
    record = out["record"]
    assert record["history"].endswith("5") and not record["miss"], record
    assert out["action"] == "call" and record["adjusted"] == "priced a misread all-in", record
    with folding(player, guard=False, stored=True):
        assert decide(player, state)["action"] == "fold"
    # Asked for real, the primary misses and the taper answers on its own
    # translation, where the min-raise is a sized re-raise and not an all-in:
    # that history is the hand, so its fold stands.
    with folding(player):
        out = decide(player, state)
    assert out["record"]["companion"] == "100bb(4, 2)", out["record"]
    assert out["action"] == "fold" and out["record"]["adjusted"] is None


def test_the_misread_test_itself():
    misread = ArenaPlayer._misread
    assert misread("collapsed:1321/11/1221/15", "1321/11/1221/15", 0)    # 5 Oct: a real shove, on a re-read
    assert misread(None, "21/25", 9200)                                 # all-in read, chips behind
    assert not misread(None, "21/25", 0)                                # a real all-in on the true history
    assert not misread("100bb(4, 2)", "21/24", 9200)                    # the companion read it as sized
    assert not misread(None, None, 9200)                                # the rule answered, at the real pot
