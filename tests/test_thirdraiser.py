"""The thirdraiser archetype: a sized preflop third raise where every other shape jams."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chipzen.archetypes import ARCHETYPES, PARAMS, action_probabilities, build_archetype  # noqa: E402


def facing_four_bet(stack=9000, short=False):
    """We are the small blind, opened, they three-bet; we face it with two raises on the street."""
    big = 100
    stack = 1000 if short else stack
    history = [{"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop"},
               {"seat": 1, "action": "post_big_blind", "amount": big, "phase": "preflop"},
               {"seat": 0, "action": "raise", "amount": 250, "phase": "preflop"},
               {"seat": 1, "action": "raise", "amount": 750, "phase": "preflop"}]
    return {"your_hole_cards": ["As", "Ah"], "board": [], "to_call": 500, "pot": 1000, "min_raise": 1250,
            "max_raise": stack + 250, "your_stack": stack, "action_history": history, "phase": "preflop"}


def facing_open():
    state = facing_four_bet()
    state["action_history"] = state["action_history"][:3]
    state.update(to_call=150, pot=350, min_raise=400)
    return state


def bot(kind, equity=0.9, seed=3):
    b = build_archetype(kind, np.random.default_rng(seed))
    b._equity = lambda state: equity                  # the decision under test, not the equity sampler
    return b


def test_it_is_registered_and_only_the_size_differs_from_the_reraiser():
    assert "thirdraiser" in ARCHETYPES
    a, b = dict(PARAMS["thirdraiser"]), dict(PARAMS["reraiser"])
    assert a.pop("third_raise_frac") == 0.5 and a == b
    assert all("third_raise_frac" not in PARAMS[k] for k in ARCHETYPES if k != "thirdraiser")


def raising_seeds(state, n=40):
    """Seeds whose draw takes the raise branch (it raises when the draw beats call_p / 2), the same for both shapes."""
    seeds = [s for s in range(n) if bot("reraiser", seed=s).decide(dict(state), ["fold", "call", "raise"], 0)["action"] == "raise"]
    assert len(seeds) >= 10
    return seeds


def test_its_third_raise_is_sized_and_the_reraiser_still_jams():
    state = facing_four_bet()
    expected = state["min_raise"] + int(0.5 * (state["pot"] + state["to_call"]))
    for seed in raising_seeds(state):
        jam = bot("reraiser", seed=seed).decide(dict(state), ["fold", "call", "raise"], 0)
        sized = bot("thirdraiser", seed=seed).decide(dict(state), ["fold", "call", "raise"], 0)
        assert jam == {"action": "raise", "params": {"amount": state["max_raise"]}}
        assert sized == {"action": "raise", "params": {"amount": expected}} and expected < state["max_raise"]


def test_short_it_jams_like_every_other_shape():
    # Not a test of the short check itself: at 12bb or less facing a four-bet, a half-pot third raise is already
    # clipped to the stack, so with or without the check the raise is all-in. This holds the outcome.
    state = facing_four_bet(short=True)
    for seed in raising_seeds(state):
        assert bot("thirdraiser", seed=seed).decide(dict(state), ["fold", "call", "raise"], 0) == \
            {"action": "raise", "params": {"amount": state["max_raise"]}}


@pytest.mark.parametrize("make", [facing_open, lambda: dict(facing_four_bet(), board=["2c", "7d", "Ks"])])
def test_everything_but_the_preflop_third_raise_is_the_reraisers(make):
    for seed in range(20):
        for equity in (0.2, 0.45, 0.6, 0.9):
            state = make()
            a = bot("thirdraiser", equity, seed).decide(dict(state), ["fold", "call", "raise"], 0)
            b = bot("reraiser", equity, seed).decide(dict(state), ["fold", "call", "raise"], 0)
            assert a == b


def test_when_it_raises_is_unchanged():
    e = np.linspace(0, 1, 21)
    for raises in (0, 1, 2, 3):
        for facing in (True, False):
            for preflop in (True, False):
                a = action_probabilities(PARAMS["thirdraiser"], e, facing, 0.3, preflop, True, raises)
                b = action_probabilities(PARAMS["reraiser"], e, facing, 0.3, preflop, True, raises)
                assert np.array_equal(a, b)
