"""
Scripted opponents shaped like the arena's field, for the duel.

Every duel this project runs is our solver against our solver, so a change
registers only if it wins chips against near-equilibrium play. The field is
not that. Three sets built on 22 September (a shared clustering, a third raise
at short stacks, and both together) each read even against v5i over 5,000
matches, while the same tapered trees had cut rule decisions by half: the
rule's answer in those spots is the solver's answer against a solver, and the
question was never whether it is the right answer against a bot that 4-bets
light. This module is the panel that asks that question.

Four shapes, taken from the scout table of the season 6 and 7 field rather
than invented: a **station** (Fold-ver-3, Maxwell, vpr: calls 84 to 92 percent
of the time it does not fold, never bluffs, folds to a bet about a third of
the time), a **nit** (Shadow, mellyy: folds to a bet three quarters of the
time, folds the blind to any open, wins its showdowns because it only gets
there with a hand), a **maniac** (v003: opens 58 percent, 3-bets 25 percent,
bets and raises on anything with equity), and a **fold-or-raise** bot
(Blueprint, LazerTank: calls only a third of the time it does not fold, raises
the rest). Each decides on Monte Carlo equity against a random hand (the
native sampler, 200 runouts) plus a few thresholds, sizes bets as a fraction
of the pot, and knows nothing about the opponent. They are crude by design:
the point is that they are wrong in the field's way, not that they are good.

The interface is the duel's: `decide(state, valid, seat)` returning the arena's
action dict, and a `stats` object with the four counters the duel prints.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from chipzen.bridge import parse_cards

ARCHETYPES = ("station", "nit", "maniac", "foldraise")

#: Each shape is a parameter row; `scripts/chipzen_calibrate.py` measures the
#: row with the scout's own statistics beside the bot it stands for, and the
#: numbers here are tuned by hand until the two columns agree. Equities are
#: against a random hand. `fold_margin` is how far below the pot's price the
#: hand's equity may fall before the shape folds (negative: it calls worse than
#: the price says); `call_p` is how often it calls rather than raises when it
#: could do either; `defend_eq` is the least equity it defends a raise with
#: preflop, and `defend3_eq` a re-raise, since a bot that opens light and
#: folds to 3-bets (v003) needs the two apart.
PARAMS = {
    "station":  dict(open_eq=0.56, limp_eq=0.30, threebet_eq=0.58, fold_margin=0.12, raise_eq=0.78,
                     raise_p=0.5, bluff_p=0.0, call_p=0.75, defend_eq=0.30, defend3_eq=0.48),
    "nit":      dict(open_eq=0.47, limp_eq=0.55, threebet_eq=0.60, fold_margin=0.04, raise_eq=0.58,
                     raise_p=0.6, bluff_p=0.05, call_p=0.05, defend_eq=0.55, defend3_eq=0.58),
    "maniac":   dict(open_eq=0.50, limp_eq=0.45, threebet_eq=0.53, fold_margin=0.02, raise_eq=0.52,
                     raise_p=0.6, bluff_p=0.15, call_p=0.50, defend_eq=0.45, defend3_eq=0.78),
    "foldraise": dict(open_eq=0.54, limp_eq=0.68, threebet_eq=0.58, fold_margin=0.20, raise_eq=0.55,
                      raise_p=0.7, bluff_p=0.05, call_p=0.30, defend_eq=0.62, defend3_eq=0.58),
}


@dataclass
class ArchetypeStats:
    decisions: int = 0
    misses: int = 0
    companion_hits: int = 0
    fallbacks: int = 0


class Archetype:
    """A scripted opponent; `kind` is one of ARCHETYPES, `params` a row of PARAMS."""

    def __init__(self, kind: str, rng: np.random.Generator, samples: int = 200, params: dict = None):
        if kind not in ARCHETYPES:
            raise ValueError(f"archetype must be one of {ARCHETYPES}, got {kind!r}")
        self.kind = kind
        self.p = dict(PARAMS[kind], **(params or {}))
        self.rng = rng
        self.samples = samples
        self.stats = ArchetypeStats()
        self.label = kind
        self.opponent = None
        self.profiles = None

    def _equity(self, state: dict) -> float:
        import pokerbot_native as native
        hole = [c.index for c in parse_cards(state["your_hole_cards"])]
        board = [c.index for c in parse_cards(state.get("board") or [])]
        return float(native.equity_vs_random(hole, board, self.samples, int(self.rng.integers(0, 2 ** 62))))

    @staticmethod
    def _raise_to(state: dict, fraction: float, allin: bool = False) -> dict:
        """A raise to about `fraction` of the pot after the call, clipped to the arena's bounds."""
        if allin:
            return {"action": "raise", "params": {"amount": int(state["max_raise"])}}
        pot_after_call = int(state["pot"]) + int(state["to_call"])
        level = int(state["min_raise"]) + int(fraction * pot_after_call)
        level = max(int(state["min_raise"]), min(level, int(state["max_raise"])))
        return {"action": "raise", "params": {"amount": level}}

    @staticmethod
    def _passive(valid: Sequence[str]) -> dict:
        return {"action": "check" if "check" in valid else "call", "params": {}}

    @staticmethod
    def _fold(valid: Sequence[str]) -> dict:
        return {"action": "fold" if "fold" in valid else "check", "params": {}}

    @staticmethod
    def _blind(state: dict) -> int:
        return max((int(a.get("amount") or 0) for a in state.get("action_history", [])
                    if a.get("action") == "post_big_blind"), default=100)

    def _short(self, state: dict) -> bool:
        return int(state["your_stack"]) + int(state["to_call"]) <= 12 * self._blind(state)

    @staticmethod
    def _raises_before(state: dict) -> int:
        """Raises so far on the current street, from the arena's history."""
        hist = state.get("action_history") or []
        phase = state.get("phase") or "preflop"
        return sum(1 for a in hist if a.get("phase") == phase and a.get("action") == "raise")

    def decide(self, state: dict, valid: Sequence[str], seat: int) -> dict:  # noqa: ARG002 (the duel passes it)
        self.stats.decisions += 1
        p = self.p
        e = self._equity(state)
        to_call = int(state["to_call"])
        pot = int(state["pot"])
        facing = to_call > 0
        price = to_call / (pot + to_call) if facing else 0.0
        preflop = not state.get("board")
        can_raise = "raise" in valid
        raises = self._raises_before(state)
        u = float(self.rng.random())

        if preflop:
            if raises == 0:
                # Unopened, or the big blind facing a limp: open, limp, or fold.
                if can_raise and e >= p["open_eq"]:
                    return self._raise_to(state, 0.5)
                if e >= p["limp_eq"] or not facing:
                    return self._passive(valid)
                return self._fold(valid)
            # Facing a raise (or more).
            if can_raise and e >= p["threebet_eq"] and u > p["call_p"] * 0.5:
                return self._raise_to(state, 1.0, allin=self._short(state) or raises >= 2)
            defend = p["defend3_eq"] if raises >= 2 else p["defend_eq"]
            if e >= defend and e >= price + p["fold_margin"]:
                return self._passive(valid)
            return self._fold(valid)

        # Postflop.
        if facing:
            if e < price + p["fold_margin"]:
                return self._fold(valid)
            if can_raise and e >= p["raise_eq"] and u > p["call_p"]:
                return self._raise_to(state, 1.0, allin=self._short(state))
            return self._passive(valid)
        if can_raise and ((e >= p["raise_eq"] and u < p["raise_p"]) or u < p["bluff_p"]):
            return self._raise_to(state, 0.66)
        return self._passive(valid)


def build_archetype(kind: str, rng: np.random.Generator, params: dict = None) -> Archetype:
    return Archetype(kind, rng, params=params)
