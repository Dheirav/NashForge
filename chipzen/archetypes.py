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

Nine shapes. Five are calibrated to bots we have played, from the scout
table of the season 6 and 7 field: a **station** (Fold-ver-3, Maxwell, vpr: calls 84 to 92 percent
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

The other four come from the platform's published corpus of 247,946 hands
between eleven LLM-written bots (Kaggle, 23 August 2026), which is sixty
times what the scout can fetch per bot and carries hole cards. It covers
extremes nothing we have played reaches: a station that folds to a bet 5
percent of the time rather than 35, a bot that never folds to a three-bet
(nine of the eleven are at 0 or 1 percent, where every shape above folds
half the time), a bot that folds every hand, and one that three-bets 46
percent and then never folds after the flop. Those are the cases an
exploiter's value turns on, and the panel had none of them.

The interface is the duel's: `decide(state, valid, seat)` returning the arena's
action dict, and a `stats` object with the four counters the duel prints.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from chipzen.bridge import parse_cards

ARCHETYPES = ("station", "nit", "maniac", "foldraise", "hoops",
              "sticky", "nofold3bet", "folder", "wildpassive", "meek", "bully", "reraiser", "thirdraiser")

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
    # hoops: the queue's one bot with a better record than ours (+18 bb/100 in
    # the shared pool to our +16, 3 of 11 against us in September). Opens 42%
    # of hands at one to two times the pot, folds to a 3-bet half the time,
    # then calls 86% of the time postflop and rarely raises; showdown 13%,
    # won 42%. It takes pots before showdown.
    "hoops":    dict(open_eq=0.48, limp_eq=0.46, threebet_eq=0.58, fold_margin=0.09, raise_eq=0.80,
                     raise_p=0.4, bluff_p=0.05, call_p=0.80, defend_eq=0.45, defend3_eq=0.56, open_frac=1.0),

    # The four below come from the platform's published corpus (247,946 hands
    # between eleven LLM-written bots, Kaggle, 23 August 2026; the profiles are
    # in the private repo's corpus_profiles.md). The five above are calibrated
    # to bots we have actually played, and those stay the panel's core; these
    # cover shapes nothing we have played reaches, which is where an
    # exploiter's value is decided. Fitted to the corpus rows, not to a named
    # opponent, so the calibration target is the row rather than a scout file.

    # Agents 04, 08, 01, 05: enters 67 to 78% of hands, folds to a bet 0 to
    # 11% of the time, calls 94 to 97% of its answers, shows down 82 to 96%
    # of hands. Our "station" folds to a bet 35% of the time, which is three
    # times as willing; against a bot that never folds the right answer is to
    # stop bluffing and value bet much thinner, and that is the answer the
    # exploiter has never been asked for.
    "sticky":   dict(open_eq=0.52, limp_eq=0.20, threebet_eq=0.80, fold_margin=-0.30, raise_eq=0.85,
                     raise_p=0.3, bluff_p=0.0, call_p=0.98, defend_eq=0.18, defend3_eq=0.25),

    # Nine of the eleven fold to a three-bet 0 or 1% of the time, where every
    # shape above folds 46 to 62%. So a value three-bet is worth far more
    # against the real field than our panel says, and a three-bet bluff far
    # less; the read that three-bets a folder must never fire here.
    "nofold3bet": dict(open_eq=0.50, limp_eq=0.35, threebet_eq=0.62, fold_margin=-0.10, raise_eq=0.70,
                       raise_p=0.4, bluff_p=0.05, call_p=0.85, defend_eq=0.22, defend3_eq=0.20),

    # Agent 07: enters 0% of hands, folds 100% of blinds to an open, 3,188
    # hands in the corpus. Trivial to beat, and in the panel because a set
    # that fails to raise every hand against it is broken.
    "folder":   dict(open_eq=0.95, limp_eq=0.95, threebet_eq=0.95, fold_margin=0.45, raise_eq=0.95,
                     raise_p=0.1, bluff_p=0.0, call_p=0.9, defend_eq=0.90, defend3_eq=0.92),

    # Agent 06: three-bets 46% of hands and then folds to a bet 0% of the
    # time, calling 81% of its answers. Wild before the flop, immovable
    # after it; our "maniac" is aggressive throughout and never plays this.
    "wildpassive": dict(open_eq=0.36, limp_eq=0.20, threebet_eq=0.40, fold_margin=-0.25, raise_eq=0.82,
                        raise_p=0.3, bluff_p=0.02, call_p=0.95, defend_eq=0.20, defend3_eq=0.24, open_frac=1.0),

    # wsp, which beat us on 23 September and is the first opponent of its kind
    # the field has produced. It is not a rock: it opens 76% of hands. What
    # defines it is that it never re-raises anything, at any level, and folds
    # heavily once it is bet into. Its own record, by node:
    #
    #   first to act preflop   raises 76%, folds 24%        (n=1,113)
    #   facing our open        calls 55%, folds 43%, RAISES 1%   (n=392)
    #   facing our three-bet   calls 60%, folds 40%, RAISES 0%   (n=100)
    #   flop first to act      checks 76%, bets 24%         (n=634)
    #   facing a flop bet      folds 57%, calls 35%, raises 8%   (n=166)
    #   river bets             298, of which bluffs 0
    #
    # Every other shape in this table raises 9 to 30% of the time it faces a
    # bet and three-bets 4 to 40% of our opens. This one is at 3% and 1%, three
    # times outside the field's range on both, which is why nothing we had
    # could read it: the whole panel varied in how LOOSE a bot is and never in
    # how OFTEN it raises. The two-by-two of loose-or-tight against
    # passive-or-aggressive had an empty cell and this fills it.
    "meek":     dict(open_eq=0.44, limp_eq=0.40, threebet_eq=0.82, fold_margin=0.12, raise_eq=0.85,
                     raise_p=0.25, bluff_p=0.0, call_p=0.85, defend_eq=0.42, defend3_eq=0.46),

    # Shadow, which plays us on Friday and which we have never played: the
    # season 6 fixture was the walkover, so all 613 observations are scouted.
    # `scripts/opponent_coverage.py` found it on 24 September by asking which
    # statistics vary across the field and have no read, and it is the opposite
    # extreme from `meek`:
    #
    #   first to act    bets 74% of flops, 84% of turns, 86% of rivers
    #   facing a bet    RAISES 53% on the flop, against 2 to 36% for the field
    #   river bets      48, of which 23 were bluffs (48%)
    #   big bets        260, of which 79 were air (30%)
    #   but            folds 63% to our open, 58% to our three-bet, 51% overall
    #
    # It bets and raises constantly and folds to pressure, which is the one
    # shape where calling down light and re-raising both pay. Not one of our
    # seven reads fires on it: 63% is under folds_blind's 70%, 58% is under
    # folds_to_three_bet's 75%, it bluffs far too much for never_bluffs and
    # folds far too much for never_folds. Our "maniac" is aggressive AND
    # sticky (fold_margin 0.02); this one gives up.
    "bully":    dict(open_eq=0.47, limp_eq=0.60, threebet_eq=0.56, fold_margin=0.16, raise_eq=0.45,
                     raise_p=0.80, bluff_p=0.45, call_p=0.25, defend_eq=0.52, defend3_eq=0.60,
                     open_frac=1.0),
    # reraiser: the maniac's shape re-raising from 0.38 equity four times in five (call_p 0.2). v5x folds about
    # 80% of its opens to a re-raise, and against this shape it fell from 68.2% (maniac) to 64.1% (30 Sept,
    # 10,000 matches); the maniac re-raises only above 0.53, so training against it never reached the leak.
    "reraiser": dict(open_eq=0.50, limp_eq=0.45, threebet_eq=0.38, fold_margin=0.02, raise_eq=0.52,
                     raise_p=0.6, bluff_p=0.15, call_p=0.20, defend_eq=0.45, defend3_eq=0.78),
    # thirdraiser (6 Oct): the reraiser, except that its preflop third raise and beyond is sized (half the pot after
    # the call) instead of all-in. Every other shape jams there, so no duel ever reached the hole the (4,3,2,1) tree
    # and the price guard were built for: a (4,2,1) tree's third raise is all-in only, and the bridge reads a sized
    # one as all-in. 128 sized third raises in our logs, mr_hide and Blueprint four-betting to about a third to a
    # half of the pot with hands as wide as 33, 55, J9s and A6o.
    "thirdraiser": dict(open_eq=0.50, limp_eq=0.45, threebet_eq=0.38, fold_margin=0.02, raise_eq=0.52,
                        raise_p=0.6, bluff_p=0.15, call_p=0.20, defend_eq=0.45, defend3_eq=0.78,
                        third_raise_frac=0.5),
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
                    return self._raise_to(state, p.get("open_frac", 0.5))
                if e >= p["limp_eq"] or not facing:
                    return self._passive(valid)
                return self._fold(valid)
            # Facing a raise (or more).
            if can_raise and e >= p["threebet_eq"] and u > p["call_p"] * 0.5:
                if raises >= 2 and p.get("third_raise_frac") is not None and not self._short(state):
                    # A sized third raise, the one the (4,2,1) tree cannot express; jams only once short.
                    return self._raise_to(state, p["third_raise_frac"])
                if p.get("reraise_frac") is not None and not self._short(state):
                    # A sized re-raise, for the small ones traced LBR exploits (8 Oct): the shapes and copies all
                    # re-raise the pot, so the small-raise defence could not be measured on them. Unset in every shape.
                    return self._raise_to(state, p["reraise_frac"])
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


#: Columns of `action_probabilities`: the three things `decide` can do, by kind.
FOLD, PASSIVE, RAISE = 0, 1, 2


def action_probabilities(p: dict, equity: np.ndarray, facing: bool, price: float, preflop: bool,
                         can_raise: bool, raises: int) -> np.ndarray:
    """
    The chance `Archetype.decide` folds, checks or calls, or raises, for each
    of an array of equities, over its uniform draw `u`. It mirrors `decide`
    branch for branch; `tests/test_river_oracle.py` holds the two together by
    sampling `decide`, so a change to one that is not made to the other fails.

    The river oracle (`cfr/river_oracle.py`) needs the policy as a function
    of the hand rather than one sampled action, which `decide` cannot give.
    """
    e = np.asarray(equity, dtype=float)
    raise_ = np.zeros_like(e)
    if preflop:
        if raises == 0:
            if can_raise:
                raise_ = (e >= p["open_eq"]).astype(float)
            passive = (1.0 - raise_) * ((e >= p["limp_eq"]) | (not facing))
        else:
            if can_raise:
                raise_ = (e >= p["threebet_eq"]) * (1.0 - p["call_p"] * 0.5)
            defend = p["defend3_eq"] if raises >= 2 else p["defend_eq"]
            passive = (1.0 - raise_) * ((e >= defend) & (e >= price + p["fold_margin"]))
    elif facing:
        stays = (e >= price + p["fold_margin"]).astype(float)
        if can_raise:
            raise_ = stays * (e >= p["raise_eq"]) * (1.0 - p["call_p"])
        passive = stays - raise_
    else:
        if can_raise:
            # (e >= raise_eq and u < raise_p) or u < bluff_p
            raise_ = np.where(e >= p["raise_eq"], max(p["raise_p"], p["bluff_p"]), p["bluff_p"])
        passive = 1.0 - raise_
    fold = 1.0 - raise_ - passive
    return np.stack([fold, passive, raise_], axis=-1)


def build_archetype(kind: str, rng: np.random.Generator, params: dict = None) -> Archetype:
    return Archetype(kind, rng, params=params)
