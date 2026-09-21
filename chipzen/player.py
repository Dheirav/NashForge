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

from abstraction.betting import ALL_IN, CHECK_CALL, FOLD, RAISE_ACTIONS, RAISE_HALF, RAISE_POT

ACTION_NAMES = {FOLD: "fold", CHECK_CALL: "check/call", RAISE_HALF: "raise ½", RAISE_POT: "raise pot",
                ALL_IN: "all-in"}       # for the log's `adjusted` field; other raises print as their index
from cfr.flat import load_strategy
from chipzen.bridge import Hand, cards, legal_mask, replay, to_chipzen
from cfr.river import decide_river
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
    river_shoves_to_companion: int = 0
    shoves_softened: int = 0
    bluffs_withheld: int = 0
    shove_calls_declined: int = 0
    river_solves: int = 0
    blinds_opened: int = 0
    three_bets_into_folders: int = 0
    river_bets_believed: int = 0
    big_bets_believed: int = 0
    small_bets_called: int = 0
    river_failures: int = 0
    fallbacks: int = 0
    collapsed_hits: int = 0            # answered on a re-read history after a pseudo all-in
    miss_depths: Dict[int, int] = field(default_factory=dict)
    depths_used: Dict[str, int] = field(default_factory=dict)
    actions_sent: Dict[str, int] = field(default_factory=dict)
    slowest_ms: float = 0.0

    @property
    def miss_rate(self) -> float:
        return self.misses / self.consulted if self.consulted else 0.0


def _shim(hole, board, to_call: int, stack: int = 0):
    """
    The five things `cfr_agent` reads. See `slumbot.player._shim` for why.

    `stack` matters only with `cfr_agent(stack_cap=True)`: the trees give a
    player who cannot cover the bet just fold and call, and both solvers store
    a two-wide entry there. Without the stack the lookup rebuilt the full
    list, rejected the entry as the wrong width, and the decision fell to the
    rule at exactly the all-in-facing nodes (19 September; 34% of a cap-2
    rung's keys are such nodes). The arena's `your_stack` is in the bridge's
    chip scale, which the bridge already uses for the shove ceiling.
    """
    actor = SimpleNamespace(hole_cards=hole, bet=0, stack=stack)
    return SimpleNamespace(
        players=[actor, SimpleNamespace(hole_cards=[], bet=0, stack=0)],
        state=SimpleNamespace(community_cards=board),
        current_bet=to_call)


def load_solver(path: str, rng: np.random.Generator, purify: str = "none",
                stack_cap: bool = False) -> Solver:
    # The flat pair beside the pickle when it exists (cfr/flat.py): the same
    # answers, a twentieth of the memory, which is what lets the whole ladder
    # sit beside a training run.
    saved = load_strategy(path)
    args = saved.get("args") or {}
    if not isinstance(args, dict):
        args = vars(args)
    cap = args.get("raise_cap", 1)
    schedule = tuple(cap) if isinstance(cap, (list, tuple)) else int(cap)
    depth = float(args.get("stack", 200)) / float(args.get("big_blind", 2))
    solver = Solver(path=path, depth_bb=depth, schedule=schedule,
                    strategy=saved["strategy"], abstraction=saved["abstraction"])
    solver.agent = cfr_agent(solver.strategy, solver.abstraction, rng,
                             misses=solver.misses, raise_cap=schedule, purify=purify,
                             stack_cap=stack_cap)
    return solver


def strength_class(abstraction, hole, board) -> int:
    """
    The hand's strength class, 0 to 5, as the solver reads it: the texture and
    the lossless preflop index stripped off. Seeded from the cards, as
    `cfr_agent` seeds, so the class is the one the lookup used.
    """
    key = (tuple(c.index for c in hole), tuple(c.index for c in board))
    bucket = abstraction.bucket(hole, board, np.random.default_rng(hash(key) % (2 ** 32)))
    if hasattr(abstraction, "strength_of"):
        street = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}[len(board)]
        return abstraction.strength_of(bucket, street)
    return bucket


def fallback_choice(bucket: int, top: int, mask, pot: int, to_call: int) -> int:
    """
    A policy for a node the strategy never stored. Crude on purpose.

    Buckets run from 0 (weakest) to `top` (strongest). The price of a call is
    measured against the pot with the bet included. Shared by the arena player
    and the Slumbot player: until 15 September the Slumbot player guessed
    uniformly at random on a miss, a shove one time in six, and at 3,000 hands
    the 135 hands with a miss carried 68 percent of the loss while the hands
    without one were not separated from zero.
    """
    def first_legal(*preferred):
        for action in preferred:
            if mask[action]:
                return int(action)
        return int(np.flatnonzero(mask)[0])

    if bucket >= top:
        return first_legal(RAISE_POT, ALL_IN, CHECK_CALL)
    if to_call > 0 and to_call >= pot - to_call:
        # A bet of the pot or more, and the rule has no read on the bettor:
        # 14 September's T-5 calling a shove with a pair of fives is what
        # this line prevents.
        return first_legal(FOLD, CHECK_CALL)
    if bucket >= top - 1:
        return first_legal(CHECK_CALL, FOLD)
    if bucket >= top - 2:
        return first_legal(CHECK_CALL, FOLD) if to_call <= pot * 0.5 \
            else first_legal(FOLD, CHECK_CALL)
    return first_legal(CHECK_CALL, FOLD) if to_call <= pot * 0.15 \
        else first_legal(FOLD, CHECK_CALL)


class ArenaPlayer:
    """A ladder of solvers behind the Chipzen bridge."""

    #: A companion further than this from the hand's depth, in ratio, is not
    #: asked: a 100bb taper's answer to a 12bb re-raise is the wrong game.
    COMPANION_REACH = 2.0

    def __init__(self, paths: Sequence[str], rng: Optional[np.random.Generator] = None,
                 companions: Sequence[str] = (), purify: str = "none",
                 river: bool = False, river_budget_s: float = 8.0,
                 river_shove_companion: bool = False, stack_cap: bool = False):
        self.rng = rng if rng is not None else np.random.default_rng()
        self.purify = purify
        #: Honour the trees' stack cap in every lookup (see `_shim`). Off by
        #: default until a burst has gated it; the duel gates it first.
        self.stack_cap = stack_cap
        #: Facing an all-in on the river, ask the cap-2 companion even though
        #: the one-raise primary has a node. The primary's river node was solved
        #: in a game where nobody can re-raise, so a shove there is bluff-heavy
        #: and its calling range is wide: K3 called 6,350 with a pair of threes
        #: and K8 5,168 into jacks in v7b's burst (19 Sept), J7 with jack-high
        #: in v7's. The companion's range comes from the game with re-raises.
        #: Off by default; gated on the replay and a burst before it plays.
        self.river_shove_companion = river_shove_companion
        #: River endgame solving (cfr/river.py), off by default: the river is
        #: re-solved on the exact hand from the blueprint's ranges, and the
        #: blueprint's own answer is kept only if the solve fails or overruns.
        self.river = river
        self.river_budget_s = river_budget_s
        self.ladder = sorted((load_solver(p, self.rng, purify, stack_cap) for p in paths),
                             key=lambda s: s.depth_bb)
        if not self.ladder:
            raise ValueError("an empty ladder cannot play")
        self.companions = sorted((load_solver(p, self.rng, purify, stack_cap) for p in companions),
                                 key=lambda s: s.depth_bb)
        self.stats = Stats()
        self.probe: List = []
        #: Set by the client at match start; read by the one adjustment below.
        self.opponent: Optional[str] = None
        self.profiles: Optional[Profiles] = None

    #: A raise with a hand this weak or weaker is a bluff for the purpose of
    #: withholding it: the bottom two of six strength classes.
    BLUFF_STRENGTH = 1
    #: The shove-call rule fires only at this effective stack or deeper. It
    #: was written for 100bb three-bet shoves, and on 15 September v4's burst
    #: showed it firing 70 times against Blueprint, 60 of them preflop at short
    #: stacks where that bot shoves any two cards: against the revealed hands
    #: calling was better in 48 of the 70, worth about 184,000 chips over the
    #: burst, and every one of those below 20bb. At 20bb and deeper the rule
    #: was neutral. The solver's short rungs know the calling ranges; the rule
    #: does not.
    SHOVE_RULE_MIN_BB = 20.0
    #: Pot odds beyond which a fold to an all-in opponent is never sent: the
    #: outstanding call is at most a tenth of what is already in the pot.
    POT_ODDS_FLOOR = 10
    #: The three-bet-into-a-folder read fires only this deep, so a four-bet
    #: can be folded to without having committed the stack.
    THREE_BET_MIN_BB = 30.0

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
        # The strength class is read by up to four rules per decision, each of
        # which built a fresh generator to seed the bucket the way the lookup
        # does; one memo per decision answers them all from a single call.
        classes: Dict[int, int] = {}

        def strength(of_solver) -> int:
            key = id(of_solver)
            if key not in classes:
                classes[key] = self._bucket(of_solver, hole, board)
            return classes[key]

        mask = legal_mask(node, valid_actions, solver.schedule)
        arena = legal_mask(node, valid_actions, tree=False)
        to_call = int(state.get("to_call") or 0)

        before = list(solver.misses)
        self.probe[:] = []
        choice = solver.agent(_shim(hole, board, to_call, int(state.get("your_stack") or 0)), 0, mask, node.history)
        missed = solver.misses[0] > before[0]
        fell_back = False
        companion_used = None
        river_shove = None
        if self.river_shove_companion and not missed and len(board) == 5 and to_call > 0 \
                and node.history.endswith("5"):
            deep = self.companion_for(hand.effective_bb)
            if deep is not None:
                deep_hand = replay(state, seat, self.rng, schedule=deep.schedule)
                deep_mask = legal_mask(deep_hand.node, valid_actions, deep.schedule)
                deep_before = deep.misses[0]
                answer = deep.agent(_shim(hole, board, to_call, int(state.get("your_stack") or 0)), 0, deep_mask, deep_hand.node.history)
                if deep.misses[0] == deep_before:
                    river_shove = f"river shove: {ACTION_NAMES.get(choice, choice)} -> companion "
                    river_shove += f"{ACTION_NAMES.get(answer, answer)}"
                    choice = answer
                    companion_used = f"{deep.depth_bb:g}bb{deep.schedule}"
                    self.stats.river_shoves_to_companion += 1
        if missed:
            deep = self.companion_for(hand.effective_bb)
            if deep is not None:
                deep_hand = replay(state, seat, self.rng, schedule=deep.schedule)
                deep_mask = legal_mask(deep_hand.node, valid_actions, deep.schedule)
                deep_before = deep.misses[0]
                choice = deep.agent(_shim(hole, board, to_call, int(state.get("your_stack") or 0)), 0, deep_mask,
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
                            strength(deep) < self._top(deep):
                        choice = CHECK_CALL
                        self.stats.shoves_softened += 1
            if companion_used is None:
                # A pseudo all-in closed an earlier street and the hand went
                # on (chipzen.bridge._close_street). Last resort before the
                # rule: the same solvers on their own re-read histories.
                candidates = [(solver, hand)]
                if deep is not None:
                    candidates.append((deep, deep_hand))
                for candidate, c_hand in candidates:
                    if c_hand.alt_history is None:
                        continue
                    c_before = candidate.misses[0]
                    alt_mask = legal_mask(c_hand.node, valid_actions, candidate.schedule)
                    answer = candidate.agent(_shim(hole, board, to_call, int(state.get("your_stack") or 0)), 0,
                                             alt_mask, c_hand.alt_history)
                    if candidate.misses[0] == c_before:
                        choice = answer
                        companion_used = f"collapsed:{c_hand.alt_history}"
                        self.stats.collapsed_hits += 1
                        break
            if companion_used is None:
                fell_back = True
                choice = self._fallback(solver, hole, board, arena, state)
        river = None
        if self.river and len(board) == 5:
            try:
                posted = next((a.get("seat") for a in state.get("action_history") or []
                               if a.get("action") == "post_small_blind"), None)
                decision = decide_river(
                    state, hole, board, node.history, solver.strategy, solver.abstraction,
                    solver.schedule, we_are_small_blind=(posted == seat), rng=self.rng,
                    legal=arena, budget_s=self.river_budget_s, purify=(self.purify != "none"))
                choice, missed, fell_back, companion_used = decision.choice, False, False, None
                river = {"iterations": decision.iterations, "ms": round(decision.ms, 1),
                         "hands": decision.hands,
                         "strategy": {str(a): round(p, 3) for a, p in decision.distribution.items()}}
                self.stats.river_solves += 1
            except Exception as error:          # the blueprint's answer stands
                river = {"error": f"{type(error).__name__}: {error}"[:200]}
                self.stats.river_failures += 1
        adjusted = river_shove
        if self.profiles is not None and choice == FOLD and not board and node.history == "" \
                and arena[RAISE_HALF] and self.profiles.folds_blind(self.opponent):
            # First to act preflop against a big blind that folds to most
            # opens: the minimum raise (half the pot after the call is the
            # 2x open) wins the blind outright far more often than it costs.
            choice = RAISE_HALF
            adjusted = "opened into a folding blind"
            self.stats.blinds_opened += 1
        if self.profiles is not None and choice == FOLD and not board and len(node.history) == 1 \
                and node.history in "2345" and arena[RAISE_HALF] \
                and hand.effective_bb >= self.THREE_BET_MIN_BB \
                and self.profiles.folds_to_three_bet(self.opponent):
            # Facing an open from a bot that folds to most three-bets, and the
            # solver was folding: the small three-bet replaces an action worth
            # nothing with one that shows a profit at any fold rate above two
            # thirds. Deep only, so a four-bet is folded to at a bearable price.
            choice = RAISE_HALF
            adjusted = "three-bet into a folder"
            self.stats.three_bets_into_folders += 1
        if self.profiles is not None and choice == CHECK_CALL and to_call > 0 and len(board) == 5 \
                and arena[FOLD] and hand.effective_bb >= self.SHOVE_RULE_MIN_BB \
                and self.profiles.never_bluffs(self.opponent) \
                and strength(solver) < self._top(solver) - 1:
            # A river bet from a bot whose river bets are never bluffs is paid
            # off only by the top two strength classes. Deep only, and river
            # only: the same shape of rule folded good hands short in v4.
            choice = FOLD
            adjusted = "river bet believed"
            self.stats.river_bets_believed += 1
        pot_before = int(state.get("pot") or 0) - to_call
        if self.profiles is not None and to_call > 0 and board and pot_before > 0 \
                and hand.effective_bb >= self.SHOVE_RULE_MIN_BB \
                and self.profiles.big_bets_are_value(self.opponent):
            size = to_call / pot_before
            cls = strength(solver)
            if size >= 0.7 and choice != FOLD and arena[FOLD] and cls < self._top(solver) - 1:
                # Its big bets were never air: below the top two classes, fold.
                choice = FOLD
                adjusted = "big bet believed"
                self.stats.big_bets_believed += 1
            elif size <= 0.6 and choice == FOLD and arena[CHECK_CALL] and cls >= 3:
                # Its small bets were air two times in five: a middling hand calls.
                choice = CHECK_CALL
                adjusted = "small bet called"
                self.stats.small_bets_called += 1
        if choice in RAISE_ACTIONS and arena[CHECK_CALL] and self.profiles is not None \
                and self.profiles.never_folds(self.opponent) \
                and strength(solver) <= self.BLUFF_STRENGTH:
            # A measured station: bluffing it only builds a pot we are behind
            # in. Facing a bet, the alternative to the bluff-raise is the fold,
            # not a call with the bottom class: 114 of 286 firings had turned a
            # bluff into a call before 15 September.
            choice = FOLD if to_call > 0 and arena[FOLD] else CHECK_CALL
            adjusted = "bluff withheld"
            self.stats.bluffs_withheld += 1
        big_bet = to_call > 0 and to_call >= int(state.get("pot") or 0) - to_call
        if choice == CHECK_CALL and big_bet and arena[FOLD] and self.profiles is not None \
                and hand.effective_bb >= self.SHOVE_RULE_MIN_BB \
                and self.profiles.never_calls(self.opponent) \
                and strength(solver) < self._top(solver):
            # A fold-or-raise bot's bet of the pot or more is a made hand.
            choice = FOLD
            adjusted = "shove call declined"
            self.stats.shove_calls_declined += 1
        opponent_stack = int((state.get("opponent_stacks") or [0])[0])
        if to_call > 0 and opponent_stack <= 0 and arena[CHECK_CALL] and choice == FOLD \
                and to_call * self.POT_ODDS_FLOOR <= int(state.get("pot") or 0) - to_call:
            # An opponent all in for a fraction of a blind: the 5bb blueprint
            # prices "all-in" at several blinds and folded T5o at 33 to 1 on
            # 14 September. Any two cards call at these odds.
            choice = CHECK_CALL
            adjusted = "called for pot odds"
        if not arena[choice]:
            # The last-resort legality guard keeps the passive action, not the
            # fold that happens to sit at index 0.
            choice = CHECK_CALL if arena[CHECK_CALL] else int(np.flatnonzero(arena)[0])

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
            "adjusted": adjusted, "opponent": self.opponent, "river": river,
            "legal": [int(m) for m in mask], "choice": int(choice),
            "sent": outgoing, "ms": round(elapsed, 2),
        }
        return {"action": outgoing["action"], "params": outgoing["params"],
                "record": record}

    #: Strength classes by (solver, hole, board) across decisions: a hand's
    #: cards come back on every street, and each read cost a generator (9 µs)
    #: plus a 200-sample rollout. Seeded per key exactly as the lookup seeds,
    #: so the memo changes nothing but the time. Cleared at the cap.
    _CLASS_MEMO_CAP = 20_000

    def _bucket(self, solver: Solver, hole, board) -> int:
        """
        The hand's strength class, 0 to 5, as the solver itself would read it.

        With a texture-aware abstraction the stored bucket also carries the
        board's class, and with a lossless preflop it is the hand's own index
        out of 169; only the strength part, one of six classes, is wanted for
        a threshold.
        """
        key = (id(solver), tuple(c.index for c in hole), tuple(c.index for c in board))
        memo = self.__dict__.setdefault("_class_memo", {})
        found = memo.get(key)
        if found is not None:
            return found
        found = strength_class(solver.abstraction, hole, board)
        if len(memo) >= self._CLASS_MEMO_CAP:
            memo.clear()
        memo[key] = found
        return found

    @staticmethod
    def _top(solver: Solver) -> int:
        return int(getattr(solver.abstraction, "postflop_buckets", 6)) - 1

    def _fallback(self, solver: Solver, hole, board, mask, state) -> int:
        """A policy for a node the strategy never stored; see `fallback_choice`."""
        return fallback_choice(self._bucket(solver, hole, board), self._top(solver), mask,
                               int(state.get("pot") or 0), int(state.get("to_call") or 0))

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
