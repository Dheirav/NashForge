"""
Preflop equity against a range that is the top share of hands, for the re-raise defence.

A bot that re-raises a share s of our opens is modelled as re-raising the top s of all 1,326 starting
hands, ranked by equity against a random hand. That is the tightest range consistent with the rate,
so it errs towards folding: a looser, bluffier re-raiser only makes a call better.
"""
from __future__ import annotations

from functools import lru_cache
from itertools import combinations
from typing import List, Sequence, Tuple

import numpy as np


@lru_cache(maxsize=1)
def ranked_combos() -> Tuple[Tuple[int, int], ...]:
    """All 1,326 two-card hands, strongest first by equity against a random hand (seeded, so stable)."""
    import pokerbot_native as native
    scored = [(float(native.equity_vs_random([a, b], [], 400, 5)), (a, b)) for a, b in combinations(range(52), 2)]
    scored.sort(key=lambda x: -x[0])
    return tuple(c for _, c in scored)


def equity_vs_top(hole: Sequence[int], share: float, samples: int = 400, seed: int = 11) -> float:
    """Our all-in equity against a random hand from the top `share` of combos, board run out at random."""
    import pokerbot_native as native
    mine = set(hole)
    combos: List[Tuple[int, int]] = [c for c in ranked_combos()[:max(1, int(round(share * 1326)))]
                                     if c[0] not in mine and c[1] not in mine]
    if not combos:
        return 0.0
    rng = np.random.default_rng(seed)
    win = tie = 0
    for _ in range(samples):
        a, b = combos[rng.integers(len(combos))]
        deck = [c for c in range(52) if c not in mine and c != a and c != b]
        board = [int(x) for x in rng.choice(deck, 5, replace=False)]
        us = native.score_hand_7([c % 13 for c in list(hole) + board], [c // 13 for c in list(hole) + board])
        them = native.score_hand_7([c % 13 for c in [a, b] + board], [c // 13 for c in [a, b] + board])
        win += us > them
        tie += us == them
    return (win + tie / 2) / samples
