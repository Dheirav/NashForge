"""
A duel opponent that plays the exact push-fold solution when it can.

    scripts/chipzen_duel.py --b pushfold

Below about twelve big blinds a heads-up hand is fold-or-shove, and that game
is solvable exactly (`scripts/push_fold.py`). This plays that solution: in the
small blind it shoves its solved range and folds the rest; in the big blind it
calls a shove with its solved range. Deeper than the solution's reach, and on
any street after the flop, it falls back to equity against the pot's price,
because the exact game no longer applies there.

It exists to settle one question. Our short rungs raise to about a third of
the stack where the solution shoves, and a first attempt to price that from
logged hands (22 September) charged every small raise as a fold and produced
half a big blind a decision for every bot alike. Playing the decisions one at
a time against the solution read within a twentieth of a blind of even at 5,
8 and 12 blinds. This is the same question asked the way every other claim in
this project is settled: whole matches, in the arena's own format, against an
opponent that cannot be accused of playing the short stage badly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RANKS = "23456789TJQKA"


@dataclass
class PushFoldStats:
    decisions: int = 0
    misses: int = 0
    companion_hits: int = 0
    fallbacks: int = 0


class PushFoldPlayer:
    """The exact short-stack solution, with an equity fallback where it does not apply."""

    def __init__(self, rng: np.random.Generator, samples: int = 200, max_bb: float = 14.0):
        import sys
        sys.path.insert(0, ROOT)
        from scripts.push_fold import combos_of, hand_labels, solve

        self.rng = rng
        self.samples = samples
        self.max_bb = max_bb
        self.stats = PushFoldStats()
        self.label = "pushfold"
        self.opponent = None
        self.profiles = None
        self._solve = solve
        edge = np.load(os.path.join(ROOT, "results", "cfr", "chance", "nolimit_12bb_preflop_allin.npy"))
        labels = hand_labels(os.path.join(ROOT, "results", "cfr", "ladder169l", "nolimit_12bb.pkl"))
        self._edge = edge
        self._combos = combos_of(labels)
        self._index = {label: i for i, label in enumerate(labels)}
        self._cache: dict[float, tuple] = {}

    # -- the solution, memoised by depth --------------------------------
    def _solution(self, depth: float):
        key = round(max(depth, 1.0) * 2) / 2
        if key not in self._cache:
            shove, call, _, _, _ = self._solve(self._edge, self._combos, key)
            self._cache[key] = (shove, call)
        return self._cache[key]

    def _class(self, cards: Sequence[str]) -> int:
        (r1, s1), (r2, s2) = (cards[0][0], cards[0][1]), (cards[1][0], cards[1][1])
        high, low = (r1, r2) if RANKS.index(r1) >= RANKS.index(r2) else (r2, r1)
        key = f"{high}{high}" if r1 == r2 else f"{high}{low}{'s' if s1 == s2 else 'o'}"
        return self._index[key]

    @staticmethod
    def _blind(state: dict) -> int:
        return max((int(a.get("amount") or 0) for a in state.get("action_history", [])
                    if a.get("action") == "post_big_blind"), default=100)

    def _equity(self, state: dict) -> float:
        import pokerbot_native as native
        from chipzen.bridge import parse_cards
        hole = [c.index for c in parse_cards(state["your_hole_cards"])]
        board = [c.index for c in parse_cards(state.get("board") or [])]
        return float(native.equity_vs_random(hole, board, self.samples, int(self.rng.integers(0, 2 ** 62))))

    def decide(self, state: dict, valid: Sequence[str], seat: int) -> dict:  # noqa: ARG002
        self.stats.decisions += 1
        big_blind = self._blind(state)
        to_call = int(state["to_call"])
        stack = int(state["your_stack"])
        depth = (stack + to_call) / max(big_blind, 1)
        preflop = not state.get("board")
        can_raise = "raise" in valid

        if preflop and depth <= self.max_bb:
            shove, call = self._solution(depth)
            klass = self._class(state["your_hole_cards"])
            if to_call <= big_blind:
                # First in, or the big blind facing a limp: shove the range.
                if can_raise and shove[klass]:
                    return {"action": "raise", "params": {"amount": int(state["max_raise"])}}
                if to_call == 0:
                    return {"action": "check" if "check" in valid else "call", "params": {}}
                return {"action": "fold" if "fold" in valid else "call", "params": {}}
            # Facing a raise: the solved calling range, which is the right
            # answer to a shove and the harshest sensible one to a small raise.
            if call[klass]:
                return {"action": "call", "params": {}}
            return {"action": "fold" if "fold" in valid else "call", "params": {}}

        # Outside the push-fold game: equity against the price, and value bets.
        equity = self._equity(state)
        pot = int(state["pot"])
        price = to_call / (pot + to_call) if to_call else 0.0
        if to_call:
            if equity < price:
                return {"action": "fold" if "fold" in valid else "call", "params": {}}
            if can_raise and equity > 0.80:
                return {"action": "raise", "params": {"amount": int(state["max_raise"])}}
            return {"action": "call", "params": {}}
        if can_raise and equity > 0.62:
            level = min(int(state["min_raise"]) + int(0.7 * pot), int(state["max_raise"]))
            return {"action": "raise", "params": {"amount": max(level, int(state["min_raise"]))}}
        return {"action": "check" if "check" in valid else "call", "params": {}}
