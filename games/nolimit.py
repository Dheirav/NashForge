"""
Heads-up no-limit Hold'em as a traversable, abstracted game.

This is where CFR meets the project's actual poker. Three things are borrowed
and one is rebuilt:

* **Borrowed:** the engine's card representation, its fast 7-card evaluator for
  showdowns, and the six-action abstraction the rest of the project uses.
* **Rebuilt:** the betting. ``engine.PokerGame`` mutates state in place and
  consumes a dealt deck, so a traverser cannot branch over an action and back
  up. The pot arithmetic here is small, immutable, and carried in the state.

**Abstraction applies to information sets, not to the game.** Cards are dealt
for real and showdowns are settled on real hands; only the key a player uses to
look up their strategy is bucketed. Abstracting the game itself would require
estimating bucket-to-bucket transition probabilities and would throw away the
correlation between the two players' holdings. This way the game stays exact and
only the solver's view is coarse — which is also what the exploitability of the
resulting strategy is measured against.

Chance here cannot be enumerated: the opening deal alone has about 1.6 million
outcomes. :meth:`chance_outcomes` therefore raises, and :meth:`sample_chance`
deals directly. Vanilla CFR cannot run on this game, which is a true statement
about no-limit Hold'em rather than a gap in the implementation.
"""
from __future__ import annotations

from typing import Hashable, List, NamedTuple, Optional, Sequence, Tuple

import numpy as np

from abstraction.betting import (ALL_IN, CHECK_CALL, FOLD, RAISE_HALF,
                                 RAISE_POT, RAISE_TWO, legal_actions)
from abstraction.buckets import CardAbstraction
from abstraction.equity import FULL_DECK
from engine.hand_eval_fast import evaluate_hand_fast

from .base import CHANCE, Game

#: Board cards revealed at the start of each street.
STREET_BOARD_SIZE = (0, 3, 4, 5)
STREET_NAMES = ("preflop", "flop", "turn", "river")

#: Pot fraction each raise action adds on top of calling.
RAISE_FRACTION = {RAISE_HALF: 0.5, RAISE_POT: 1.0, RAISE_TWO: 2.0}


class NoLimitState(NamedTuple):
    """
    Immutable state.

    ``contributions`` is chips put in this hand, ``committed`` chips put in on
    the current street — the difference between them is what a call must match.
    Both are carried rather than re-derived because a raise is sized from the
    pot at the moment it is made, so replaying the history to recover them would
    mean re-deriving the pot at every step.
    """
    hole: Tuple[Tuple[int, ...], ...]
    board: Tuple[int, ...]
    history: str
    contributions: Tuple[int, int]
    committed: Tuple[int, int]
    stacks: Tuple[int, int]
    street: int


def _street_actions(history: str) -> str:
    """Actions taken on the current street."""
    return history.split("/")[-1]


class NoLimitHoldem(Game):
    """
    Heads-up no-limit Hold'em over a card abstraction.

    Args:
        abstraction: Fitted :class:`~abstraction.buckets.CardAbstraction`
            supplying the bucket used in information-set keys.
        starting_stack: Chips each player begins with.
        small_blind / big_blind: Blind sizes.
        raise_cap: Bets or raises allowed per street. This is the parameter that
            decides whether the game fits in memory — see
            ``scripts/cfr/measure_abstraction.py``.
        equity_samples: Monte Carlo samples per postflop bucket lookup.
    """

    num_players = 2

    def __init__(self, abstraction: CardAbstraction, starting_stack: int = 200,
                 small_blind: int = 1, big_blind: int = 2, raise_cap: int = 1,
                 equity_samples: int = 60):
        self.abstraction = abstraction
        self.starting_stack = starting_stack
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.raise_cap = raise_cap
        self.equity_samples = equity_samples
        self._bucket_cache: dict = {}

    # ---- structure -------------------------------------------------------

    def initial_state(self) -> NoLimitState:
        """Blinds are posted before the deal, so the root is a chance node."""
        return NoLimitState(
            hole=(), board=(), history="",
            contributions=(self.small_blind, self.big_blind),
            committed=(self.small_blind, self.big_blind),
            stacks=(self.starting_stack - self.small_blind,
                    self.starting_stack - self.big_blind),
            street=0,
        )

    def is_terminal(self, state: NoLimitState) -> bool:
        if not state.hole:
            return False
        if str(FOLD) in state.history:
            return True
        if state.street >= len(STREET_NAMES):
            return True
        return False

    def _street_closed(self, state: NoLimitState) -> bool:
        """
        True when betting on the current street is complete.

        Both players must have acted and the last action must be a check or
        call: preflop, the small blind calling the big blind still leaves the
        big blind its option, and postflop a single check leaves the other
        player to act.
        """
        actions = _street_actions(state.history)
        if len(actions) < 2 or actions[-1] != str(CHECK_CALL):
            return False
        if state.committed[0] == state.committed[1]:
            return True
        # A call that could not cover the bet still closes the street — the
        # caller is all-in and the uncalled excess is returned at showdown.
        return min(state.stacks) == 0

    def current_player(self, state: NoLimitState) -> int:
        if not state.hole:
            return CHANCE
        if self._street_closed(state):
            return CHANCE                      # deal the next street
        actions = _street_actions(state.history)
        # Preflop the small blind (seat 0) acts first; afterwards the big blind.
        first = 0 if state.street == 0 else 1
        return (first + len(actions)) % 2

    def legal_actions(self, state: NoLimitState) -> Sequence[int]:
        actions = _street_actions(state.history)
        raises = sum(1 for a in actions if int(a) in RAISE_FRACTION or int(a) == ALL_IN)
        facing = state.committed[0] != state.committed[1]
        last = int(actions[-1]) if actions else None

        available = list(legal_actions(raises, facing, self.raise_cap, last))

        player = self.current_player(state)
        to_call = abs(state.committed[0] - state.committed[1])
        if state.stacks[player] <= to_call:
            # Cannot raise what one cannot cover; calling is capped at the stack.
            available = [a for a in available if a in (FOLD, CHECK_CALL)]
        return tuple(available)

    def next_state(self, state: NoLimitState, action) -> NoLimitState:
        if not state.hole:
            hole, board = action
            return state._replace(hole=hole, board=board)

        if self.current_player(state) == CHANCE:
            # Reveal the next street and reset per-street commitments.
            street = state.street + 1
            return state._replace(board=action, history=state.history + "/",
                                  committed=(0, 0), street=street)

        return self._apply(state, int(action))

    def _apply(self, state: NoLimitState, action: int) -> NoLimitState:
        player = self.current_player(state)
        opponent = 1 - player
        to_call = state.committed[opponent] - state.committed[player]

        contributions = list(state.contributions)
        committed = list(state.committed)
        stacks = list(state.stacks)

        if action == FOLD:
            pay = 0
        elif action == CHECK_CALL:
            pay = min(max(to_call, 0), stacks[player])
        elif action == ALL_IN:
            pay = stacks[player]
        else:
            pot = sum(contributions) + to_call
            raise_by = int(round(RAISE_FRACTION[action] * pot))
            pay = min(max(to_call, 0) + max(raise_by, self.big_blind), stacks[player])

        contributions[player] += pay
        committed[player] += pay
        stacks[player] -= pay

        updated = state._replace(
            history=state.history + str(action),
            contributions=tuple(contributions),
            committed=tuple(committed),
            stacks=tuple(stacks),
        )

        # If the street just closed on the river, the hand is over.
        if updated.street == len(STREET_NAMES) - 1 and self._street_closed(updated):
            return updated._replace(street=len(STREET_NAMES))
        return updated

    # ---- chance ----------------------------------------------------------

    def chance_outcomes(self, state: NoLimitState):
        raise NotImplementedError(
            "no-limit chance cannot be enumerated (about 1.6 million opening "
            "deals); use sample_chance, and a sampling solver such as MCCFRSolver"
        )

    def sample_chance(self, state: NoLimitState, rng) -> object:
        """Deal the hole cards, or reveal the next street."""
        if not state.hole:
            picked = rng.choice(len(FULL_DECK), size=4, replace=False)
            return ((tuple(picked[:2]), tuple(picked[2:])), ())

        needed = STREET_BOARD_SIZE[state.street + 1] - len(state.board)
        seen = set(state.board) | set(state.hole[0]) | set(state.hole[1])
        available = np.array([i for i in range(len(FULL_DECK)) if i not in seen])
        drawn = rng.choice(available, size=needed, replace=False)
        return state.board + tuple(int(c) for c in drawn)

    # ---- payoffs and knowledge -------------------------------------------

    def utility(self, state: NoLimitState, player: int) -> float:
        opponent = 1 - player

        if str(FOLD) in state.history:
            folded = self._who_folded(state)
            if folded == player:
                return -float(state.contributions[player])
            return float(state.contributions[opponent])

        mine = evaluate_hand_fast([FULL_DECK[c] for c in
                                   tuple(state.hole[player]) + state.board])
        theirs = evaluate_hand_fast([FULL_DECK[c] for c in
                                     tuple(state.hole[opponent]) + state.board])

        # Only the matched portion is at risk; anything a player put in beyond
        # what the opponent could cover is returned, so it nets to nothing.
        at_risk = min(state.contributions)
        if mine > theirs:
            return float(at_risk)
        if mine < theirs:
            return -float(at_risk)
        return 0.0

    def _who_folded(self, state: NoLimitState) -> int:
        """Index of the player whose action was the fold."""
        position = state.history.index(str(FOLD))
        prefix = state.history[:position]
        street = prefix.count("/")
        actions_before = len(prefix.split("/")[-1])
        first = 0 if street == 0 else 1
        return (first + actions_before) % 2

    def information_set(self, state: NoLimitState, player: int) -> Hashable:
        """
        Bucketed hand strength plus the public betting history.

        The bucket is the entire card abstraction: two situations sharing a
        bucket and a history are indistinguishable to the solver. The
        opponent's cards never appear.
        """
        return f"{self._bucket(state, player)}|{state.history}"

    def information_set_with(self, state: NoLimitState, player: int,
                             abstraction: CardAbstraction) -> Hashable:
        """
        The key this state would have under a DIFFERENT card abstraction.

        Needed to play two agents trained on different abstractions against each
        other: each must be asked the question its own bucketing poses. Handing
        an agent the other's key would look like bad play rather than a
        mismatched lookup.
        """
        hole = [FULL_DECK[c] for c in state.hole[player]]
        board = [FULL_DECK[c] for c in state.board]
        seed = hash((state.hole[player], state.board)) % (2 ** 32)
        bucket = abstraction.bucket(hole, board, np.random.default_rng(seed))
        return f"{bucket}|{state.history}"

    def _bucket(self, state: NoLimitState, player: int) -> int:
        key = (state.hole[player], state.board)
        cached = self._bucket_cache.get(key)
        if cached is None:
            hole = [FULL_DECK[c] for c in state.hole[player]]
            board = [FULL_DECK[c] for c in state.board]
            cached = self.abstraction.bucket(hole, board,
                                             np.random.default_rng(hash(key) % (2 ** 32)))
            self._bucket_cache[key] = cached
        return cached
