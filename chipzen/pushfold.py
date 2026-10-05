"""
The exact short-stack answer, for the one spot where the rule was worst.

Below about fourteen big blinds a preflop all-in is the whole hand, and that
game is small enough to solve exactly rather than approximately: 169 classes a
side, one matrix of all-in equities, fictitious play to a fixed point
(`scripts/push_fold.py`, precomputed by `scripts/push_fold_table.py`).

The bot reaches these depths every match, because the blinds climb until one
stack is short. What it did there until now, whenever the betting tree had no
entry for the node, was `fallback_choice`: a bet of the pot or more with no
read on the bettor is folded. That guard was written for a deep stack, where a
pot-sized bet really is a commitment. Short, after we have already raised, a
third of the stack is in and the price is nothing like that. Priced on 23
September at the node the 8bb rung misses most, our own half-pot raise shoved
over: the rule agreed with the exact answer on 88 of the 169 classes, called
none of them where the solution calls 45%, and each of the 81 disagreements
cost 0.69 big blinds. Over a duel against exact play that was -13.6 chips a
hand.

This is deliberately narrow. It answers preflop all-ins at short depths and
nothing else: no postflop, no sized bets, no depth the solution does not
cover. Everywhere else the rule stands, because everywhere else the rule is
not provably wrong.
"""
from __future__ import annotations

import os
from typing import Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PATH = os.path.join(ROOT, "results", "cfr", "chance", "push_fold_ranges.npz")
RANKS = "23456789TJQKA"


class ShortStackRanges:
    """The solved shoving and calling ranges, by depth, with the equity matrix."""

    def __init__(self, labels, depths, shove, call, combos, edge):
        self.labels = [str(l) for l in labels]
        self.depths = np.asarray(depths, dtype=float)
        self.shove = np.asarray(shove, dtype=bool)
        self.call = np.asarray(call, dtype=bool)
        self.weights = np.asarray(combos, dtype=float) / float(np.sum(combos))
        self.edge = np.asarray(edge, dtype=np.float64)
        self.index = {label: i for i, label in enumerate(self.labels)}

    @classmethod
    def load(cls, path: str = DEFAULT_PATH) -> Optional["ShortStackRanges"]:
        """The table, or None if it has not been built; a missing file is not a match-day error."""
        try:
            with np.load(path, allow_pickle=False) as data:
                return cls(data["labels"], data["depths"], data["shove"],
                           data["call"], data["combos"], data["edge"])
        except Exception:
            return None

    def class_of(self, hole: Sequence) -> Optional[int]:
        """The hand's index among the 169 classes, from `engine.cards.Card`s."""
        if len(hole) != 2:
            return None
        first, second = int(hole[0].index), int(hole[1].index)
        high, low = sorted((first % 13, second % 13), reverse=True)
        if high == low:
            key = f"{RANKS[high]}{RANKS[low]}"
        else:
            key = f"{RANKS[high]}{RANKS[low]}{'s' if first // 13 == second // 13 else 'o'}"
        return self.index.get(key)

    def _row(self, depth_bb: float) -> Optional[int]:
        """The nearest solved depth, or None if the hand is deeper than the table reaches."""
        if depth_bb <= 0 or depth_bb > self.depths[-1] + 0.5:
            return None
        return int(np.argmin(np.abs(self.depths - depth_bb)))

    def equity(self, klass: int, opponent: np.ndarray) -> Optional[float]:
        """Our share of the pot all in against a range, as the solver's matrix scores it."""
        w = self.weights * opponent
        total = float(w.sum())
        if total <= 0:
            return None
        return 0.5 * (1.0 + float(self.edge[klass] @ (w / total)))

    def combos_left(self, hole: Sequence) -> np.ndarray:
        """
        Each class's combos that do not share a card with `hole`. Against a narrow range the
        blockers move the answer: ace-king leaves three combos of aces and nine of ace-king, not
        six and sixteen, and the range a four-bet is priced against is exactly that narrow.
        """
        held = {int(c.index) for c in hole}
        left = np.zeros(len(self.labels))
        for first in range(52):
            for second in range(first + 1, 52):
                if first in held or second in held:
                    continue
                high, low = sorted((first % 13, second % 13), reverse=True)
                key = f"{RANKS[high]}{RANKS[low]}" if high == low else \
                    f"{RANKS[high]}{RANKS[low]}{'s' if first // 13 == second // 13 else 'o'}"
                left[self.index[key]] += 1
        return left

    def equity_against(self, hole: Sequence, reach: np.ndarray) -> Optional[float]:
        """
        Our all-in share against a range given as each class's reach (a probability per class,
        not yet weighted by combos), with our own cards removed from it. None for an empty range.
        """
        klass = self.class_of(hole)
        if klass is None:
            return None
        w = self.combos_left(hole) * np.asarray(reach, dtype=float)
        total = float(w.sum())
        if total <= 0:
            return None
        return 0.5 * (1.0 + float(self.edge[klass] @ (w / total)))

    def calls(self, hole: Sequence, depth_bb: float, to_call: int, pot: int,
              reraise: bool) -> Optional[bool]:
        """
        Whether to call this all-in: the price against the range that shoved it.

        `pot` is the arena's, which already holds the shove; calling `to_call`
        more plays for `pot + to_call`. Under the arena player's --capped-price
        both come in capped (`chipzen.player.capped_call`): a shove that covers
        our stack is priced at our stack, with their excess out of the pot,
        which is the effective-stack all-in the table was solved for. `reraise` says the all-in came over a
        raise of ours, in which case the range that shoved is the solution's
        calling range, which is much the tighter of the two; an open shove is
        priced against its shoving range. None means the table cannot answer
        and the caller should keep whatever it had.
        """
        row = self._row(depth_bb)
        klass = self.class_of(hole)
        if row is None or klass is None or to_call <= 0 or pot <= 0:
            return None
        equity = self.equity(klass, self.call[row] if reraise else self.shove[row])
        if equity is None:
            return None
        return equity >= to_call / float(pot + to_call)
