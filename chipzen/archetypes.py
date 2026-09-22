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


@dataclass
class ArchetypeStats:
    decisions: int = 0
    misses: int = 0
    companion_hits: int = 0
    fallbacks: int = 0


class Archetype:
    """A scripted opponent; `kind` is one of ARCHETYPES."""

    def __init__(self, kind: str, rng: np.random.Generator, samples: int = 200):
        if kind not in ARCHETYPES:
            raise ValueError(f"archetype must be one of {ARCHETYPES}, got {kind!r}")
        self.kind = kind
        self.rng = rng
        self.samples = samples
        self.stats = ArchetypeStats()
        self.label = kind
        self.opponent = None
        self.profiles = None

    # -- the hand's strength, as the bot sees it --------------------------
    def _equity(self, state: dict) -> float:
        import pokerbot_native as native
        hole = [c.index for c in parse_cards(state["your_hole_cards"])]
        board = [c.index for c in parse_cards(state.get("board") or [])]
        return float(native.equity_vs_random(hole, board, self.samples, int(self.rng.integers(0, 2 ** 62))))

    # -- sizing ----------------------------------------------------------
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

    def _short(self, state: dict) -> bool:
        """Under about twelve big blinds, judged from the blinds in the history."""
        bb = max((int(a.get("amount") or 0) for a in state.get("action_history", [])
                  if a.get("action") == "post_big_blind"), default=100)
        return int(state["your_stack"]) + int(state["to_call"]) <= 12 * bb

    # -- the shapes --------------------------------------------------------
    def decide(self, state: dict, valid: Sequence[str], seat: int) -> dict:  # noqa: ARG002 (the duel passes it)
        self.stats.decisions += 1
        e = self._equity(state)
        to_call = int(state["to_call"])
        pot = int(state["pot"])
        facing = to_call > 0
        price = to_call / (pot + to_call) if facing else 0.0      # pot odds as a fraction
        preflop = not state.get("board")
        can_raise = "raise" in valid
        u = float(self.rng.random())

        if self.kind == "station":
            # Calls with any equity near the price, folds only far below it,
            # raises only a made hand, never bluffs.
            if facing and e < price - 0.15:
                return self._fold(valid)
            if can_raise and e > 0.80 and u < 0.7:
                return self._raise_to(state, 0.75)
            if can_raise and preflop and not facing and e > 0.55 and u < 0.4:
                return self._raise_to(state, 0.5)
            return self._passive(valid)

        if self.kind == "nit":
            # Folds to pressure unless strong, opens only good hands, and
            # shoves short with a premium.
            if facing:
                if e >= 0.72 and can_raise and u < 0.5:
                    return self._raise_to(state, 1.0, allin=self._short(state))
                return self._passive(valid) if e >= 0.62 else self._fold(valid)
            if can_raise and e >= 0.62:
                return self._raise_to(state, 0.66)
            return self._passive(valid)

        if self.kind == "maniac":
            # Raises anything with equity, 3-bets and 4-bets light, shoves
            # short, and still calls rather than folds when raising is off.
            if can_raise and (e > 0.40 or u < 0.25):
                allin = self._short(state) or (facing and e > 0.6 and u < 0.5)
                return self._raise_to(state, 1.0, allin=allin)
            if facing and e < price - 0.10 and u < 0.7:
                return self._fold(valid)
            return self._passive(valid)

        # fold-or-raise: calling is the rare action.
        if facing:
            if e >= 0.55 and can_raise:
                return self._raise_to(state, 1.0, allin=self._short(state) and e > 0.6)
            if e >= 0.50 and u < 0.35:
                return self._passive(valid)
            return self._fold(valid)
        if can_raise and e >= 0.50:
            return self._raise_to(state, 0.66)
        return self._passive(valid)


def build_archetype(kind: str, rng: np.random.Generator) -> Archetype:
    return Archetype(kind, rng)
