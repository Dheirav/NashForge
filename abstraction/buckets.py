"""
Card abstraction: collapsing hands into a bounded number of strength buckets.

No-limit Hold'em has on the order of 10^160 information sets; CFR needs
something it can hold in memory. Abstraction is the standard answer — group
hands a solver may treat identically, solve the smaller game, and play the
resulting strategy by mapping real hands into it.

Two streets, two methods:

* **Preflop** has only 169 strategically distinct starting hands, so nothing is
  sampled: all 169 are enumerated and grouped by strength directly. The existing
  Chen-formula score is used, as the project's proposal specifies.

* **Postflop** cannot be enumerated — the flop alone has around 26 million
  (hole, board) combinations — so equity is computed on a sample and clustered
  with k-means, following Johanson et al. (2013). New situations are then
  assigned to the nearest centroid.

Bucket 0 is always the weakest. That ordering is not cosmetic: it makes an
abstraction directly comparable across granularities, and it means a strategy
table can be read by a human.

**Abstraction is lossy, and finer is not automatically better.** Waugh et al.
(2009) showed refining an abstraction can make the resulting strategy *more*
exploitable. Granularity is therefore something to measure, which is what
``scripts/cfr/measure_abstraction.py`` does, rather than something to assume.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from engine.cards import RANKS, Card
from engine.features import chen_formula

from .equity import equity_vs_random, sample_situations

#: Board sizes for the streets that have one.
STREET_BOARD_SIZE = {"flop": 3, "turn": 4, "river": 5}
POSTFLOP_STREETS = ("flop", "turn", "river")


def canonical_preflop_hands() -> List[Tuple[str, str, bool]]:
    """
    The 169 strategically distinct starting hands.

    Suits carry no information preflop beyond whether the two cards match, so a
    hand is fully described by its two ranks and whether it is suited.
    """
    hands = []
    for i, high in enumerate(RANKS):
        for j, low in enumerate(RANKS):
            if j > i:
                continue
            if i == j:
                hands.append((high, low, False))       # a pair is never suited
            else:
                hands.append((high, low, True))
                hands.append((high, low, False))
    return hands


def preflop_key(hole: Sequence[Card]) -> Tuple[str, str, bool]:
    """Canonical key for a starting hand: (high rank, low rank, suited)."""
    first, second = hole
    high, low = first.rank, second.rank
    if RANKS.index(low) > RANKS.index(high):
        high, low = low, high
    return high, low, first.suit == second.suit


def _fit_kmeans_1d(values: np.ndarray, num_buckets: int,
                   iterations: int = 60) -> np.ndarray:
    """
    One-dimensional k-means over equities, returning sorted centroids.

    Initialised at quantiles rather than at random points: equity is
    one-dimensional and already ordered, so quantiles land near the final
    answer and remove the run-to-run variation random seeding would add to an
    abstraction that is supposed to be a fixed artifact.
    """
    if num_buckets >= values.size:
        return np.sort(np.unique(values))

    quantiles = (np.arange(num_buckets) + 0.5) / num_buckets
    centroids = np.quantile(values, quantiles)

    for _ in range(iterations):
        assignments = np.abs(values[:, None] - centroids[None, :]).argmin(axis=1)
        moved = False
        for index in range(num_buckets):
            members = values[assignments == index]
            if members.size:
                updated = members.mean()
                if updated != centroids[index]:
                    centroids[index] = updated
                    moved = True
        if not moved:
            break

    return np.sort(centroids)


@dataclass
class CardAbstraction:
    """
    A fitted abstraction: preflop groups plus per-street equity centroids.

    Attributes:
        preflop_buckets: Number of preflop groups.
        postflop_buckets: Number of buckets on each postflop street.
        samples: Situations sampled per postflop street when fitting.
        equity_samples: Monte Carlo samples per equity estimate.
    """
    preflop_buckets: int = 8
    postflop_buckets: int = 8
    samples: int = 3_000
    equity_samples: int = 120

    _preflop: Dict[Tuple[str, str, bool], int] = None
    _centroids: Dict[str, np.ndarray] = None

    # ------------------------------------------------------------------

    def fit(self, rng: Optional[np.random.Generator] = None) -> "CardAbstraction":
        """Build the abstraction. Deterministic given ``rng``."""
        rng = rng if rng is not None else np.random.default_rng(0)
        self._fit_preflop()
        self._fit_postflop(rng)
        return self

    def _fit_preflop(self) -> None:
        """
        Group all 169 starting hands by Chen score.

        Enumerated, not sampled — there are only 169, so the preflop abstraction
        is exact given the score it groups on.
        """
        hands = canonical_preflop_hands()
        scores = np.array([
            chen_formula([Card(high, "h"),
                          Card(low, "h" if suited else "d")])
            for high, low, suited in hands
        ])

        centroids = _fit_kmeans_1d(scores, self.preflop_buckets)
        assignments = np.abs(scores[:, None] - centroids[None, :]).argmin(axis=1)
        self._preflop = {hand: int(bucket) for hand, bucket in zip(hands, assignments)}

    def _fit_postflop(self, rng: np.random.Generator) -> None:
        """Cluster sampled equities into buckets, one clustering per street."""
        self._centroids = {}
        for street in POSTFLOP_STREETS:
            equities = np.array([
                equity_vs_random(hole, board, self.equity_samples, rng)
                for hole, board in sample_situations(
                    STREET_BOARD_SIZE[street], self.samples, rng)
            ])
            self._centroids[street] = _fit_kmeans_1d(equities, self.postflop_buckets)

    # ------------------------------------------------------------------

    def bucket(self, hole: Sequence[Card], board: Sequence[Card],
               rng: Optional[np.random.Generator] = None) -> int:
        """
        Bucket index for a situation. Lower means weaker.

        Preflop is a table lookup. Postflop costs one equity estimate, so a
        solver should cache it per hand rather than call this per decision.
        """
        if self._preflop is None:
            raise RuntimeError("call fit() before bucket()")

        if not board:
            return self._preflop[preflop_key(hole)]

        street = {3: "flop", 4: "turn", 5: "river"}[len(board)]
        equity = equity_vs_random(hole, board, self.equity_samples, rng)
        return int(np.abs(self._centroids[street] - equity).argmin())

    def num_buckets(self, street: str) -> int:
        """Buckets available on a street."""
        if street == "preflop":
            return len(set(self._preflop.values()))
        return int(self._centroids[street].size)

    def describe(self) -> str:
        """Human-readable summary, for reports."""
        lines = [f"preflop  {self.num_buckets('preflop')} buckets over 169 hands"]
        for street in POSTFLOP_STREETS:
            centroids = self._centroids[street]
            lines.append(
                f"{street:<8} {centroids.size} buckets, equity centroids "
                + " ".join(f"{c:.2f}" for c in centroids)
            )
        return "\n".join(lines)
