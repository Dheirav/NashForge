"""
Monte Carlo hand equity, fast enough to build a card abstraction with.

Bucketing needs equity for tens of thousands of situations. The engine already
ships ``hand_strength_vs_random``, but it spends about 265 microseconds per
simulation — roughly twenty times the cost of the two hand evaluations a
simulation actually requires, the rest going on rebuilding a deck and sampling
through Python objects. At that rate a single abstraction would take hours.

This does the same job by drawing the opponent's cards and the remaining board
in one numpy call per simulation and evaluating through the fast 7-card
evaluator, which brings a 200-simulation estimate to a few milliseconds.

Equity here is the probability of winning against ONE uniformly random opponent
hand with the board completed at random, counting ties as half. That is the
standard signal for card abstraction: it is not the same as equity against a
range, but it orders hands sensibly and is what the clustering consumes.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np

from engine.cards import RANKS, SUITS, Card
from engine.hand_eval_fast import evaluate_hand_fast

#: The 52 distinct cards, in a fixed order, built once.
FULL_DECK: List[Card] = [Card(rank, suit) for suit in SUITS for rank in RANKS]

#: Index lookup so a Card can be removed from the deck without a linear scan.
_CARD_INDEX = {(card.rank, card.suit): i for i, card in enumerate(FULL_DECK)}

BOARD_SIZE = 5
HOLE_SIZE = 2


def card_index(card: Card) -> int:
    """Position of ``card`` in :data:`FULL_DECK`."""
    return _CARD_INDEX[(card.rank, card.suit)]


def remaining_deck(known: Sequence[Card]) -> np.ndarray:
    """Indices of the cards not among ``known``."""
    seen = {card_index(card) for card in known}
    return np.array([i for i in range(len(FULL_DECK)) if i not in seen], dtype=np.int64)


def equity_vs_random(
    hole: Sequence[Card],
    board: Sequence[Card],
    num_samples: int = 200,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """
    Probability that ``hole`` beats one random opponent hand, ties counted half.

    Args:
        hole: The player's two cards.
        board: Community cards so far — 0, 3, 4 or 5 of them.
        num_samples: Simulations. 200 gives a standard error near 0.035, which
            is finer than any sensible bucket boundary.
        rng: Generator, for reproducibility.

    Returns:
        Equity in [0, 1].
    """
    rng = rng if rng is not None else np.random.default_rng()
    board = list(board)
    available = remaining_deck(list(hole) + board)
    runout = BOARD_SIZE - len(board)
    draw = HOLE_SIZE + runout

    # Draw every sample in one vectorised step. Calling rng.choice per sample
    # with replace=False permutes the whole remaining deck each time, which cost
    # more than the two hand evaluations the sample exists for. Partitioning a
    # matrix of random keys gives the same uniform draw without replacement for
    # all samples at once.
    keys = rng.random((num_samples, available.size))
    picks = available[np.argpartition(keys, draw - 1, axis=1)[:, :draw]]

    hole = list(hole)
    wins = ties = 0
    for row in picks:
        opponent = [FULL_DECK[i] for i in row[:HOLE_SIZE]]
        completed = board + [FULL_DECK[i] for i in row[HOLE_SIZE:]]

        mine = evaluate_hand_fast(hole + completed)
        theirs = evaluate_hand_fast(opponent + completed)
        if mine > theirs:
            wins += 1
        elif mine == theirs:
            ties += 1

    return (wins + 0.5 * ties) / num_samples


def sample_situations(
    street_board_size: int,
    count: int,
    rng: Optional[np.random.Generator] = None,
):
    """
    Random (hole, board) situations for a street, for fitting an abstraction.

    The flop alone has about 26 million distinct situations, so a clustering is
    fitted on a sample rather than on the whole space. Yields
    ``(hole, board)`` tuples of :class:`Card`.
    """
    rng = rng if rng is not None else np.random.default_rng()
    total = HOLE_SIZE + street_board_size
    for _ in range(count):
        picked = rng.choice(len(FULL_DECK), size=total, replace=False)
        cards = [FULL_DECK[i] for i in picked]
        yield cards[:HOLE_SIZE], cards[HOLE_SIZE:]
