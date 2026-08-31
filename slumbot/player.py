"""
This project's solver, playing a hand dealt by Slumbot.

The bridge turns Slumbot's betting string into the solver's own history key and
chip accounting; this puts the two together and produces an action. It reuses
`evaluation.benchmark.cfr_agent` rather than reimplementing the lookup, through a
shim that presents the four things that agent actually reads. A second copy of
the lookup is exactly how the agent measured here would drift from the agent
measured on the panel, and then the two numbers would not be about the same
thing.

What this is honestly measuring
-------------------------------
A 100bb, one-raise-per-street strategy playing a 200bb unlimited-raise opponent.
That is not the solver's strength at Slumbot's game and should never be quoted as
though it were. It is the first number in this project that somebody else's agent
produced, which is the whole of what milestone M1 claims.

Two counters come back with every session for that reason: `misses`, the fraction
of decisions where the strategy had no entry and the agent chose among legal
actions at random, and `off_abstraction`, bets too large for the abstraction to
describe. A high miss rate means the result is largely a measurement of a random
agent wearing the solver's name -- the failure this project has already published
once, at a 74.3% miss rate.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Dict, List, Optional

import numpy as np

from evaluation.benchmark import cfr_agent
from slumbot.api import HandState
from slumbot.bridge import legal_mask, parse_cards, replay, to_slumbot


@dataclass
class SessionStats:
    """Protocol health, kept apart from anything about winning."""
    hands: int = 0
    decisions: int = 0
    misses: int = 0
    consulted: int = 0
    off_abstraction: int = 0
    actions_sent: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def miss_rate(self) -> float:
        return self.misses / self.consulted if self.consulted else 0.0


def _shim(hole, board, to_call: int):
    """
    The four things `cfr_agent` reads, and nothing else.

    Deliberately not a `PokerGame`: building one would mean dealing a deck to
    match cards Slumbot has already dealt, and a mismatch between the two would
    be a new and entirely self-inflicted class of bug.
    """
    actor = SimpleNamespace(hole_cards=hole, bet=0)
    return SimpleNamespace(
        players=[actor, SimpleNamespace(hole_cards=[], bet=0)],
        state=SimpleNamespace(community_cards=board),
        current_bet=to_call)


class SolverPlayer:
    """Answers Slumbot's hands with the strategy in `results/cfr/`."""

    def __init__(self, strategy_path: str, rng: Optional[np.random.Generator] = None,
                 raise_cap: int = 1):
        with open(strategy_path, "rb") as handle:
            saved = pickle.load(handle)
        self.abstraction = saved["abstraction"]
        self.rng = rng if rng is not None else np.random.default_rng(0)
        self.raise_cap = raise_cap
        self.stats = SessionStats()
        #: The miss counter is the agent's own, so what is reported is what the
        #: agent experienced rather than a second count taken alongside it.
        self._misses = [0, 0]
        self._agent = cfr_agent(saved["strategy"], self.abstraction, self.rng,
                                misses=self._misses, raise_cap=raise_cap)

    def __call__(self, state: HandState) -> str:
        node = replay(state, self.rng)
        self.stats.off_abstraction += node.misses

        hole = parse_cards(state.hole_cards)
        board = parse_cards(state.board)
        mask = legal_mask(node, self.raise_cap)

        choice = self._agent(_shim(hole, board, node.to_call), 0, mask,
                             node.history)
        if not mask[choice]:
            # The agent is asked only for legal actions, but a mask this layer
            # built and an agent the panel built could disagree; sending an
            # illegal action would be rejected by the server and lose the hand
            # to a protocol error rather than to poker.
            choice = int(np.flatnonzero(mask)[0])

        outgoing = to_slumbot(choice, node)
        self.stats.decisions += 1
        self.stats.actions_sent[outgoing[0]] = \
            self.stats.actions_sent.get(outgoing[0], 0) + 1
        self.stats.misses, self.stats.consulted = self._misses
        return outgoing
