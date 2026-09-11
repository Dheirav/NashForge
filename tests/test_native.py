"""
The C++ core against the Python it replaces.

A port that quietly disagrees is worse than no port: it would not fail, it would
shift every equity estimate, every bucket and every strategy trained afterwards.
So the deterministic half is pinned hand-for-hand and the sampled half is
checked for bias.

Skipped when the module is not built, because `native/build.sh` needs cmake,
ninja and nanobind, and the rest of the suite must not depend on them.
"""
import random

import numpy as np
import pytest

from abstraction.equity import FULL_DECK, equity_vs_random
from engine.hand_eval_fast import score_hand_7_fast

native = pytest.importorskip("pokerbot_native",
                             reason="run native/build.sh to build the C++ core")


def test_the_cpp_evaluator_is_identical_on_every_hand_class():
    """
    Exact, not approximate. Restricted decks are included because random
    seven-card hands almost never make quads or straight flushes, and those are
    the branches most likely to be wrong.
    """
    decks = [
        list(range(52)),
        [s * 13 + r for s in range(4) for r in range(6)],     # forces quads, boats
        [s * 13 + r for s in range(2) for r in range(13)],    # forces flushes
    ]
    rng = random.Random(2026)
    classes = set()
    for deck in decks:
        for _ in range(2000):
            cards = rng.sample(deck, 7)
            ranks = np.array([c % 13 for c in cards], dtype=np.int32)
            suits = np.array([c // 13 for c in cards], dtype=np.int32)
            expected = int(score_hand_7_fast(ranks, suits))
            assert native.score_hand_7([c % 13 for c in cards],
                                       [c // 13 for c in cards]) == expected, (
                f"C++ evaluator differs on {cards}")
            classes.add(expected >> 20)
    assert len(classes) >= 8, f"only saw hand classes {sorted(classes)}"


def test_the_cpp_rollout_is_unbiased_against_the_python_one():
    """
    Not identical: the two draw from different generators on purpose. What must
    hold is that neither systematically favours a hand, which a mean difference
    indistinguishable from zero is what shows.
    """
    rng = random.Random(99)
    differences = []
    for _ in range(400):
        board_size = rng.choice([3, 4, 5])
        cards = rng.sample(range(52), 2 + board_size)
        hole, board = cards[:2], cards[2:]
        mine = equity_vs_random([FULL_DECK[c] for c in hole],
                                [FULL_DECK[c] for c in board], 2000,
                                np.random.default_rng(rng.randrange(10 ** 6)))
        theirs = native.equity_vs_random(hole, board, 2000, rng.randrange(10 ** 9))
        differences.append(mine - theirs)

    values = np.array(differences)
    interval = 1.96 * values.std(ddof=1) / np.sqrt(values.size)
    assert abs(values.mean()) < interval, (
        f"C++ rollout is biased by {values.mean():+.5f} +/- {interval:.5f}")
