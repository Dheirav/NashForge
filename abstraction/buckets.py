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

import bisect
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from engine.cards import RANKS, Card
from engine.features import chen_formula, made_hand_strength

from .equity import equity_vs_random, sample_situations

#: Board sizes for the streets that have one.
STREET_BOARD_SIZE = {"flop": 3, "turn": 4, "river": 5}
POSTFLOP_STREETS = ("flop", "turn", "river")

#: Board size -> street, so a lookup does not rebuild a dict on every call.
_STREET_BY_BOARD = {3: "flop", 4: "turn", 5: "river"}


def _nearest_centroid(centroids: List[float], value: float) -> int:
    """
    Index of the centroid closest to ``value``, over a sorted list.

    A binary search rather than ``np.abs(centroids - value).argmin()``: the
    array holds six or eight numbers, and numpy's per-call overhead dwarfs the
    arithmetic at that size. This runs once per decision during training, so it
    is squarely on the hot path.
    """
    position = bisect.bisect_left(centroids, value)
    if position == 0:
        return 0
    if position == len(centroids):
        return len(centroids) - 1
    below, above = centroids[position - 1], centroids[position]
    return position if (above - value) < (value - below) else position - 1


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


#: Postflop strength signals a bucketing can be built on.
#:
#: ``equity`` is what the project's proposal specifies: Monte Carlo equity
#: against a random hand. It accounts for draws, and costs about 512 us per
#: situation at 40 samples — two hand evaluations per sample.
#:
#: ``made_hand`` scores only the hand made so far, deterministically, in a
#: single evaluation of about 6 us. It is roughly ninety times cheaper and free
#: of sampling noise, but it cannot see a draw: a flush draw scores as whatever
#: it has already made.
#:
#: Which to use is a real trade-off rather than an optimisation, so both are
#: available and measured — see ``scripts/cfr/compare_strength_signals.py``.
STRENGTH_SIGNALS = ("equity", "made_hand")


@dataclass
class CardAbstraction:
    """
    A fitted abstraction: preflop groups plus per-street strength centroids.

    Attributes:
        preflop_buckets: Number of preflop groups.
        postflop_buckets: Number of buckets on each postflop street.
        samples: Situations sampled per postflop street when fitting.
        equity_samples: Monte Carlo samples per estimate, when using ``equity``.
        strength: Which postflop signal to bucket on; see
            :data:`STRENGTH_SIGNALS`.
    """
    preflop_buckets: int = 8
    postflop_buckets: int = 8
    samples: int = 3_000
    equity_samples: int = 120
    strength: str = "equity"

    _preflop: Dict[Tuple[str, str, bool], int] = None
    _centroids: Dict[str, np.ndarray] = None
    #: The same centroids as plain sorted lists, for the binary-search lookup.
    _centroid_list: Dict[str, List[float]] = None

    def __post_init__(self):
        if self.strength not in STRENGTH_SIGNALS:
            raise ValueError(
                f"strength must be one of {STRENGTH_SIGNALS}, got {self.strength!r}")

    def __setstate__(self, state):
        """
        Restore, rebuilding any derived field the pickle predates.

        A fitted abstraction is pickled alongside the strategy it produced,
        precisely so a result outlives the code that produced it. That makes
        derived fields a hazard: ``_centroid_list`` was added later, as a plain
        mirror of ``_centroids`` for the binary-search lookup, and an older
        pickle arrives with it absent — whereupon the dataclass default supplies
        ``None`` and every postflop lookup raises. Rebuilding beats refitting,
        which would silently answer with a different clustering.
        """
        self.__dict__.update(state)
        if getattr(self, "_centroid_list", None) is None and self._centroids:
            self._centroid_list = {street: centroids.tolist()
                                   for street, centroids in self._centroids.items()}

    def _postflop_strength(self, hole, board,
                           rng: Optional[np.random.Generator] = None) -> float:
        """
        The signal this abstraction buckets postflop situations on.

        Fitting and lookup both go through here, so a clustering can never be
        fitted on one signal and queried with another.
        """
        if self.strength == "equity":
            return equity_vs_random(hole, board, self.equity_samples, rng)
        return made_hand_strength(hole, board)

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
        self._centroid_list = {}
        for street in POSTFLOP_STREETS:
            values = np.array([
                self._postflop_strength(hole, board, rng)
                for hole, board in sample_situations(
                    STREET_BOARD_SIZE[street], self.samples, rng)
            ])
            self._centroids[street] = _fit_kmeans_1d(values, self.postflop_buckets)
            self._centroid_list[street] = self._centroids[street].tolist()

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

        street = _STREET_BY_BOARD[len(board)]
        value = self._postflop_strength(hole, board, rng)
        return _nearest_centroid(self._centroid_list[street], value)

    def num_buckets(self, street: str) -> int:
        """Buckets available on a street."""
        if street == "preflop":
            return len(set(self._preflop.values()))
        return int(self._centroids[street].size)

    def describe(self) -> str:
        """Human-readable summary, for reports."""
        lines = [f"preflop  {self.num_buckets('preflop')} buckets over 169 hands",
                 f"postflop signal: {self.strength}"]
        for street in POSTFLOP_STREETS:
            centroids = self._centroids[street]
            lines.append(
                f"{street:<8} {centroids.size} buckets, centroids "
                + " ".join(f"{c:.2f}" for c in centroids)
            )
        return "\n".join(lines)
