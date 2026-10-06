"""cfr_agent(covering_call=True): facing a bet that leaves only fold and call, a raise or a jam is played as the call."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chipzen.player import _shim  # noqa: E402
from evaluation.benchmark import CHECK_CALL, FOLD, cfr_agent  # noqa: E402


class OneBucket:
    def bucket(self, hole, board, rng=None):
        return 0


# The root, facing the big blind, on a (4,2,1) tree: fold, call, half, pot, 2x, all-in.
SHADOW_STRAIGHT = np.array([0.17, 0.17, 0.0, 0.33, 0.0, 0.33])   # the hand 41 row: continue 0.83, fold 0.17
COVERED = [1, 1, 0, 0, 0, 0]                                       # their bet covers us: fold or call only
OPEN = [1, 1, 1, 1, 1, 1]


def decide(row, mask, flag, purify="all", to_call=50, probe=None, misses=None, on_miss="random", seed=0):
    agent = cfr_agent({"0|": np.asarray(row, float)}, OneBucket(), np.random.default_rng(seed), raise_cap=(4, 2, 1),
                      purify=purify, covering_call=flag, probe=probe, misses=misses, on_miss=on_miss)
    return agent(_shim([], [], to_call), 0, np.asarray(mask, float), "")


def test_the_straight_is_called_with_the_flag_and_folded_without():
    assert decide(SHADOW_STRAIGHT, COVERED, flag=False) == FOLD          # the bug: 0.5 / 0.5, the tie goes to fold
    assert decide(SHADOW_STRAIGHT, COVERED, flag=True) == CHECK_CALL


def test_the_raise_mass_goes_to_the_call_and_the_fold_keeps_its_own():
    probe = []
    decide(SHADOW_STRAIGHT, COVERED, flag=True, purify="none", probe=probe)
    p = probe[0]
    assert np.isclose(p[FOLD], 0.17) and np.isclose(p[CHECK_CALL], 0.83) and np.isclose(p.sum(), 1.0)
    decide(SHADOW_STRAIGHT, COVERED, flag=False, purify="none", probe=probe)
    assert np.isclose(probe[0][FOLD], 0.5) and np.isclose(probe[0][CHECK_CALL], 0.5)


def test_nothing_changes_while_a_raise_is_legal():
    for mask in (OPEN, [1, 1, 0, 0, 0, 1], [1, 1, 1, 0, 0, 0]):
        for purify in ("all", "none"):
            assert decide(SHADOW_STRAIGHT, mask, True, purify) == decide(SHADOW_STRAIGHT, mask, False, purify)


def test_nothing_changes_when_not_facing_a_bet_or_when_the_call_is_illegal():
    assert decide(SHADOW_STRAIGHT, COVERED, True, to_call=0) == decide(SHADOW_STRAIGHT, COVERED, False, to_call=0)
    assert decide(SHADOW_STRAIGHT, [1, 0, 0, 0, 0, 0], True) == FOLD


def test_an_all_raise_row_is_a_call_not_a_miss():
    # fold 0, call 0, everything on raises: masked away it left nothing, so the lookup fell to the miss policy.
    row = [0.0, 0.0, 0.0, 0.5, 0.0, 0.5]
    misses = [0, 0]
    assert decide(row, COVERED, flag=True, misses=misses) == CHECK_CALL
    assert misses == [0, 1]
    misses = [0, 0]
    decide(row, COVERED, flag=False, misses=misses)
    assert misses == [1, 1]


def test_off_by_default():
    agent = cfr_agent({"0|": SHADOW_STRAIGHT}, OneBucket(), np.random.default_rng(0), raise_cap=(4, 2, 1), purify="all")
    assert agent(_shim([], [], 50), 0, np.asarray(COVERED, float), "") == FOLD
