"""
This project's solver, answering a Chipzen turn request.

The lookup is `evaluation.benchmark.cfr_agent`, the same one the panel and the
Slumbot bridge use, through the same four-field shim `slumbot.player` uses.
What is new here is around it, and both additions exist because the arena's
game is not the one any single solver was fitted for.

**A ladder of solvers, chosen by effective stack.** Stacks carry over between
hands and the blinds rise, so the depth changes every hand. Each solver in the
ladder is a solution of the game at one depth; the hand is answered by the one
whose depth is nearest in ratio to the shorter stack in big blinds. A 100bb
strategy played at 15bb opens hands it should jam, so this is not a refinement
but the difference between playing the game and playing a different one.

**A fallback that is not uniform random.** When the strategy has no entry, the
panel's agent picks uniformly among legal actions, which is the right thing for
a measurement (it makes the miss visible as a number) and the wrong thing for a
match: one time in five it shoves with nothing. Here a miss is answered in two
stages. First a **companion** solver with a deeper betting tree, the `(4, 2)`
taper, is asked the same question with the history translated onto its own
schedule; a re-raise is on its tree, so it usually has an answer, and that
answer is an equilibrium's rather than a rule's. Only if the companion misses
too, or none is close enough in depth, does a bucket threshold decide: strong
hands raise, middling hands call at a price, weak hands fold. Misses are counted
and logged, by raise depth, exactly as they are against Slumbot.

Why not simply play the taper everywhere: it exploits a calling station far less
(+202 against +647 BB/100 on the panel), and an arena of amateur bots is where
exploitation pays. The one-raise solver leads, the taper covers what it lacks.
"""
from __future__ import annotations

import pickle
import time
from dataclasses import dataclass, field
from math import log
from types import SimpleNamespace
from typing import Dict, List, Optional, Sequence

import numpy as np

from abstraction.betting import ALL_IN, CHECK_CALL, FOLD, RAISE_ACTIONS, RAISE_POT
from chipzen.bridge import Hand, cards, legal_mask, replay, to_chipzen
from chipzen.opponents import Profiles
from evaluation.benchmark import cfr_agent


@dataclass
class Solver:
    """One rung of the ladder."""
    path: str
    depth_bb: float
    schedule: object
    strategy: dict
    abstraction: object
    misses: List[int] = field(default_factory=lambda: [0, 0])
    agent: object = None


@dataclass
class Stats:
    decisions: int = 0
    misses: int = 0
    consulted: int = 0
    off_abstraction: int = 0
    companion_hits: int = 0
    shoves_softened: int = 0
    bluffs_withheld: int = 0
    fallbacks: int = 0
    miss_depths: Dict[int, int] = field(default_factory=dict)
    depths_used: Dict[str, int] = field(default_factory=dict)
    actions_sent: Dict[str, int] = field(default_factory=dict)
    slowest_ms: float = 0.0

    @property
    def miss_rate(self) -> float:
        return self.misses / self.consulted if self.consulted else 0.0


def _shim(hole, board, to_call: int):
    """The four things `cfr_agent` reads. See `slumbot.player._shim` for why."""
    actor = SimpleNamespace(hole_cards=hole, bet=0)
    return SimpleNamespace(
        players=[actor, SimpleNamespace(hole_cards=[], bet=0)],
        state=SimpleNamespace(community_cards=board),
        current_bet=to_call)


def load_solver(path: str, rng: np.random.Generator) -> Solver:
    with open(path, "rb") as handle:
        saved = pickle.load(handle)
    args = saved.get("args") or {}
    if not isinstance(args, dict):
        args = vars(args)
    cap = args.get("raise_cap", 1)
    schedule = tuple(cap) if isinstance(cap, (list, tuple)) else int(cap)
    depth = float(args.get("stack", 200)) / float(args.get("big_blind", 2))
    solver = Solver(path=path, depth_bb=depth, schedule=schedule,
                    strategy=saved["strategy"], abstraction=saved["abstraction"])
    solver.agent = cfr_agent(solver.strategy, solver.abstraction, rng,
                             misses=solver.misses, raise_cap=schedule)
    return solver


class ArenaPlayer:
    """A ladder of solvers behind the Chipzen bridge."""

    #: A companion further than this from the hand's depth, in ratio, is not
    #: asked: a 100bb taper's answer to a 12bb re-raise is the wrong game.
    COMPANION_REACH = 2.0

    def __init__(self, paths: Sequence[str], rng: Optional[np.random.Generator] = None,
                 companions: Sequence[str] = ()):
        self.rng = rng if rng is not None else np.random.default_rng()
        self.ladder = sorted((load_solver(p, self.rng) for p in paths),
                             key=lambda s: s.depth_bb)
        if not self.ladder:
            raise ValueError("an empty ladder cannot play")
        self.companions = sorted((load_solver(p, self.rng) for p in companions),
                                 key=lambda s: s.depth_bb)
        self.stats = Stats()
        self.probe: List = []
        #: Set by the client at match start; read by the one adjustment below.
        self.opponent: Optional[str] = None
        self.profiles: Optional[Profiles] = None

    #: A raise with a hand this weak or weaker is a bluff for the purpose of
    #: withholding it: the bottom two of six strength classes.
    BLUFF_STRENGTH = 1

    def solver_for(self, effective_bb: float) -> Solver:
        """Nearest rung in ratio, so 70bb goes to 100 rather than to 50 by a hair."""
        if effective_bb <= 0:
            return self.ladder[0]
        return min(self.ladder,
                   key=lambda s: abs(log(s.depth_bb) - log(effective_bb)))

    def companion_for(self, effective_bb: float) -> Optional[Solver]:
        """The deeper-tree solver nearest in depth, if one is within reach."""
        if not self.companions or effective_bb <= 0:
            return None
        best = min(self.companions,
                   key=lambda s: abs(log(s.depth_bb) - log(effective_bb)))
        if abs(log(best.depth_bb) - log(effective_bb)) > log(self.COMPANION_REACH):
            return None
        return best

    def decide(self, state: dict, valid_actions: Sequence[str], seat: int) -> dict:
        """
        The arena's `{action, params}` for this turn, plus a record of how.

        The record is what gets logged: enough to replay the decision offline
        and compare it with what the arena's own replay shows.
        """
        started = time.perf_counter()
        # Depth first, because the schedule the history is translated onto is
        # the chosen solver's. The stacks are known before any translation.
        probe_hand = replay(state, seat, self.rng)
        solver = self.solver_for(probe_hand.effective_bb)
        hand = replay(state, seat, self.rng, schedule=solver.schedule) \
            if solver.schedule != 1 else probe_hand
        node = hand.node
        self.stats.off_abstraction += node.misses
        for depth in hand.miss_depths:
            self.stats.miss_depths[depth] = self.stats.miss_depths.get(depth, 0) + 1

        hole, board = cards(state)
        mask = legal_mask(node, valid_actions, solver.schedule)
        arena = legal_mask(node, valid_actions, tree=False)
        to_call = int(state.get("to_call") or 0)

        before = list(solver.misses)
        self.probe[:] = []
        choice = solver.agent(_shim(hole, board, to_call), 0, mask, node.history)
        missed = solver.misses[0] > before[0]
        fell_back = False
        companion_used = None
        if missed:
            deep = self.companion_for(hand.effective_bb)
            if deep is not None:
                deep_hand = replay(state, seat, self.rng, schedule=deep.schedule)
                deep_mask = legal_mask(deep_hand.node, valid_actions, deep.schedule)
                deep_before = deep.misses[0]
                choice = deep.agent(_shim(hole, board, to_call), 0, deep_mask,
                                    deep_hand.node.history)
                if deep.misses[0] == deep_before:
                    companion_used = f"{deep.depth_bb:g}bb{deep.schedule}"
                    self.stats.companion_hits += 1
                    # The (4, 2) taper keeps only two-times-pot and all-in for
                    # a re-raise, so whenever it wants to raise it shoves. On
                    # 13 September that was 7,175 chips with middle pair into
                    # jacks. A shove from the companion is taken as "raise",
                    # and only the top bucket gets to make it a shove.
                    if choice == ALL_IN and arena[CHECK_CALL] and \
                            self._bucket(deep, hole, board) < self._top(deep):
                        choice = CHECK_CALL
                        self.stats.shoves_softened += 1
            if companion_used is None:
                fell_back = True
                choice = self._fallback(solver, hole, board, arena, state)
        adjusted = None
        if choice in RAISE_ACTIONS and arena[CHECK_CALL] and self.profiles is not None \
                and self.profiles.never_folds(self.opponent) \
                and self._bucket(solver, hole, board) <= self.BLUFF_STRENGTH:
            # A measured station: bluffing it only builds a pot we are behind in.
            choice = CHECK_CALL
            adjusted = "bluff withheld"
            self.stats.bluffs_withheld += 1
        if not arena[choice]:
            choice = int(np.flatnonzero(arena)[0])

        outgoing = to_chipzen(choice, node, state)
        elapsed = (time.perf_counter() - started) * 1000.0

        self.stats.decisions += 1
        self.stats.misses += solver.misses[0] - before[0]
        self.stats.consulted += solver.misses[1] - before[1]
        self.stats.fallbacks += int(fell_back)
        key = f"{solver.depth_bb:g}bb"
        self.stats.depths_used[key] = self.stats.depths_used.get(key, 0) + 1
        self.stats.actions_sent[outgoing["action"]] = \
            self.stats.actions_sent.get(outgoing["action"], 0) + 1
        self.stats.slowest_ms = max(self.stats.slowest_ms, elapsed)

        record = {
            "hand": state.get("hand_number"), "phase": state.get("phase"),
            "seat": seat, "hole": state.get("your_hole_cards"),
            "board": state.get("board"), "pot": state.get("pot"),
            "to_call": to_call, "history": node.history,
            "effective_bb": round(hand.effective_bb, 1), "solver": key,
            "miss": missed, "companion": companion_used, "fallback": fell_back,
            "adjusted": adjusted, "opponent": self.opponent,
            "legal": [int(m) for m in mask], "choice": int(choice),
            "sent": outgoing, "ms": round(elapsed, 2),
        }
        return {"action": outgoing["action"], "params": outgoing["params"],
                "record": record}

    @staticmethod
    def _bucket(solver: Solver, hole, board) -> int:
        """
        The hand's strength class, 0 to 5, as the solver itself would read it.

        With a texture-aware abstraction the stored bucket also carries the
        board's class; only the strength part is wanted for a threshold.
        """
        key = (tuple(c.index for c in hole), tuple(c.index for c in board))
        bucket = solver.abstraction.bucket(
            hole, board, np.random.default_rng(hash(key) % (2 ** 32)))
        if board and hasattr(solver.abstraction, "strength_of"):
            street = {3: "flop", 4: "turn", 5: "river"}[len(board)]
            return solver.abstraction.strength_of(bucket, street)
        return bucket

    @staticmethod
    def _top(solver: Solver) -> int:
        return int(getattr(solver.abstraction, "postflop_buckets", 6)) - 1

    def _fallback(self, solver: Solver, hole, board, mask, state) -> int:
        """
        A policy for a node the strategy never stored. Crude on purpose.

        Buckets run from 0 (weakest) to 5 (strongest). The price of a call is
        measured against the pot as the arena reports it, bet included.
        """
        bucket = self._bucket(solver, hole, board)
        top = self._top(solver)
        to_call = int(state.get("to_call") or 0)
        pot = int(state.get("pot") or 0)

        def first_legal(*preferred):
            for action in preferred:
                if mask[action]:
                    return int(action)
            return int(np.flatnonzero(mask)[0])

        if bucket >= top:
            return first_legal(RAISE_POT, ALL_IN, CHECK_CALL)
        if bucket >= top - 1:
            return first_legal(CHECK_CALL, FOLD)
        if bucket >= top - 2:
            return first_legal(CHECK_CALL, FOLD) if to_call <= pot * 0.5 \
                else first_legal(FOLD, CHECK_CALL)
        return first_legal(CHECK_CALL, FOLD) if to_call <= pot * 0.15 \
            else first_legal(FOLD, CHECK_CALL)

    def warm_up(self) -> float:
        """
        Pay the compile cost before the clock is running.

        The equity estimator is numba-compiled on first use, and on a cold cache
        that is seconds, which is the whole decision budget. One decision on a
        made-up hand at every rung moves that cost to start-up.
        """
        started = time.perf_counter()
        for solver in self.ladder + self.companions:
            for phase, board in (("preflop", []), ("flop", ["Qs", "7h", "3d"]),
                                 ("river", ["Qs", "7h", "3d", "2c", "9s"])):
                bb = int(solver.depth_bb)
                state = {
                    "hand_number": 0, "phase": phase, "board": board,
                    "your_hole_cards": ["As", "Kh"], "pot": 300,
                    "your_stack": bb * 100 - 100, "opponent_stacks": [bb * 100 - 200],
                    "to_call": 100, "min_raise": 400, "max_raise": bb * 100 - 100,
                    "action_history": [
                        {"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop", "is_timeout": False},
                        {"seat": 1, "action": "post_big_blind", "amount": 100, "phase": "preflop", "is_timeout": False},
                        {"seat": 0, "action": "raise", "amount": 200, "phase": "preflop", "is_timeout": False},
                    ] + ([{"seat": 1, "action": "call", "amount": 200, "phase": "preflop", "is_timeout": False},
                          {"seat": 1, "action": "raise", "amount": 100, "phase": phase, "is_timeout": False}]
                         if phase != "preflop" else []),
                }
                self.decide(state, ["fold", "call", "raise"], 1 if phase == "preflop" else 0)
        self.stats = Stats()
        return time.perf_counter() - started
