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

import time
from dataclasses import dataclass, field
from math import log
from types import SimpleNamespace
from typing import Dict, List, Optional, Sequence

import numpy as np

from abstraction.betting import ALL_IN, CHECK_CALL, FOLD, RAISE_ACTIONS, RAISE_HALF, RAISE_POT, schedule_from_args

ACTION_NAMES = {FOLD: "fold", CHECK_CALL: "check/call", RAISE_HALF: "raise ½", RAISE_POT: "raise pot",
                ALL_IN: "all-in"}       # for the log's `adjusted` field; other raises print as their index
from cfr.flat import load_strategy
from chipzen.bridge import Hand, cards, legal_mask, replay, to_chipzen
from cfr.river import decide_river
from chipzen.opponents import Profiles, size_fraction
from chipzen.pushfold import ShortStackRanges
from evaluation.benchmark import cfr_agent
from slumbot.bridge import RAISE_FRACTIONS


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
    river_oracle_ranges: int = 0   # river solves given the opponent's true range
    fallbacks: int = 0
    short_stack_answers: int = 0   # a preflop all-in answered by the exact solution
    reraises_believed: int = 0     # a re-raise from a bot that never re-raises
    collapsed_hits: int = 0            # answered on a re-read history after a pseudo all-in
    river_bluffs_caught: int = 0   # a river fold turned into a call against an over-bluffer
    overfolders_bet: int = 0       # a flop or turn check turned into a half-pot bet
    reraises_defended: int = 0     # a fold of our open to a re-raise turned into a call
    misread_prices_called: int = 0  # a fold on a misread all-in turned into a call at the real price
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
    schedule = schedule_from_args(cap)
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
                 river_shove_companion: bool = False, stack_cap: bool = False,
                 short_solution: bool = True):
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
        #: The river test's oracle arm (cfr/river_oracle.py): the scripted
        #: opponent's parameter row and sample count, set by the duel only.
        #: The solve then takes the script's true range instead of the
        #: blueprint's. No real opponent's policy is known, so nothing that
        #: plays the arena may set this.
        self.river_oracle = None
        #: The river solve's opponent range, mixed with "any two cards" at this weight (cfr/river.py, 30 Sept).
        #: 0 is the blueprint's range, as every river solve so far; off until measured.
        self.river_blend = 0.0
        #: The river solve's iteration count; None keeps the solver's default (2,000 native).
        self.river_iterations = None
        self.ladder = sorted((load_solver(p, self.rng, purify, stack_cap) for p in paths),
                             key=lambda s: s.depth_bb)
        if not self.ladder:
            raise ValueError("an empty ladder cannot play")
        self.companions = sorted((load_solver(p, self.rng, purify, stack_cap) for p in companions),
                                 key=lambda s: s.depth_bb)
        #: The exact shove-or-fold solution, for preflop all-ins at short
        #: depths where the rule was provably wrong (chipzen/pushfold.py).
        #: None if the table has not been built or the caller turned it off,
        #: and then the rule stands: that is the arm the change is measured
        #: against, and the switch back if it ever misbehaves in a match.
        self.short_ranges = ShortStackRanges.load() if short_solution else None
        self.stats = Stats()
        self.probe: List = []
        #: Set by the client at match start; read by the one adjustment below.
        self.opponent: Optional[str] = None
        self.profiles: Optional[Profiles] = None
        #: The two aggressive-side reads (branch aggro-reads, 26 Sept). Off
        #: unless asked for, like every read before it was measured.
        self.aggro_reads = False
        #: Defend our opens against a frequent re-raiser (27 Sept). Off unless asked for.
        self.reraise_defence = False
        #: Call a fold the strategy made on a misread all-in when the real price is small (5 Oct). Off unless asked for.
        self.price_misread = False
        #: Under --posterior-reads, withhold a bluff only when the station's fold bound is under that bet's break-even.
        #: Off on its own: on 5 Oct it cost 1.2 points on the hoops copy (52,181 withheld bluffs down to 35,121) while
        #: one overall fold rate stood in for the fold rate at each size. It now reads the bin of the bet being
        #: considered (`Profiles.fold_upper_at`), falling back to the overall rate where a bin is thin.
        self.size_aware_bluffs = False
        #: "Bluff withheld" before the flop. Against a station it turns the small blind's open into a fold, which
        #: gives up the blind a station would often have folded to: turning it off gained 1.6 (hoops) and 0.8
        #: (PoetAndCoder copy) points at 20,000 matches, 30 Sept, and lost nowhere. On until gated and burst.
        self.withhold_preflop = True

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
    #: Against a bot with a large river sample and not one bluff, the river read
    #: extends to hands this far up the strength scale. A FRACTION of the top
    #: class, not an absolute step: v5i's deep rungs carry 20 classes and its
    #: short rungs 6, so "one below the top" is two very different hands
    #: depending on which rung answered. An absolute step folded the nut flush
    #: on a 20-class rung in the audit of 23 September.
    HONEST_RIVER_CLASS = 0.85
    #: Facing a re-raise from a bot that never re-raises, continue at this price
    #: or better and give up beyond it. A range of queens, kings, aces and
    #: ace-king leaves the hands that wanted to raise about a third of the pot,
    #: so a third is the break-even and 0.30 keeps a margin. On 23 September the
    #: price was 0.27, which is a call for 510 chips; the jam cost 7,935.
    VALUE_RERAISE_PRICE = 0.30
    #: The exact push-fold solution answers a preflop all-in at this effective
    #: stack or shorter. Fourteen blinds is where the solved game stops being
    #: the whole hand: deeper than that a shove is a real decision with a flop
    #: behind it, and the solution's assumption that the hand ends preflop is
    #: the wrong model. The table itself is solved to 20bb so the boundary can
    #: move on a measurement rather than on a rebuild.
    SHORT_STACK_MAX_BB = 14.0
    #: The three-bet-into-a-folder read fires only this deep, so a four-bet
    #: can be folded to without having committed the stack.
    THREE_BET_MIN_BB = 30.0
    #: Bet into an over-folder only when the lower bound of its fold share to
    #: our flop and turn bets is at least this. A half-pot bet with no equity
    #: breaks even at a third; the margin covers the hands that call and win.
    OVER_FOLD_RATE = 0.45
    #: A river call against an over-bluffer only with a hand that beats its
    #: bluffs: at least this equity against a random hand, the scout's own line
    #: between a bluff and a value bet.
    BLUFF_CATCH_EQUITY = 0.5
    #: The re-raise defence reads an opponent as a frequent re-raiser from
    #: this lower bound of its re-raise share. Blueprint (18%, value) and wsp
    #: (2%) stay out; v003 (44%), RockyPoker and Sleight-of-Hand (26%) come in.
    RERAISE_OFTEN = 0.20
    #: Equity against the re-raising range needed beyond the price, for the
    #: equity a call does not realise after the flop.
    RERAISE_MARGIN = 0.03
    #: The misread-price guard calls at this price or better, the call over the
    #: pot after it. 5 October, mr_hide: a third raise on the turn was read as
    #: all-in although they kept 2,174, so the river shove of those 2,174 into
    #: 16,080 was answered on the collapsed history, where the tree prices a
    #: shove of a full stack, and the jack-high flush folded at 11%. A quarter
    #: is far above that and still below the third where a pot-sized bet sits.
    MISREAD_PRICE = 0.25
    #: And only with a hand that beats a random hand this often, the same line
    #: the river bluff-catch uses: a misread is no reason to call with air.
    MISREAD_EQUITY = 0.5

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
        short_stack = None
        companion_used = None
        river_shove = None
        #: The history the strategy that chose was actually asked about; the
        #: misread-price guard reads its last action.
        answered_history = node.history
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
                    answered_history = deep_hand.node.history
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
                    answered_history = deep_hand.node.history
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
                        answered_history = c_hand.alt_history
                        self.stats.collapsed_hits += 1
                        break
            if companion_used is None:
                fell_back = True
                # The rule and the short-stack table price the arena's own pot,
                # so no history of theirs can be misread.
                answered_history = None
                answer = self._short_stack_answer(hole, board, hand.effective_bb, arena, state, seat)
                if answer is None:
                    choice = self._fallback(solver, hole, board, arena, state)
                else:
                    choice = answer
                    short_stack = "short-stack solution"
                    self.stats.short_stack_answers += 1
        river = None
        if self.river and len(board) == 5:
            try:
                posted = next((a.get("seat") for a in state.get("action_history") or []
                               if a.get("action") == "post_small_blind"), None)
                opponent_range = None
                if self.river_oracle is not None:
                    from cfr.river_oracle import script_reach
                    params, samples = self.river_oracle
                    opponent_range = lambda pairs: script_reach(pairs, board, params, state, 1 - seat, samples)  # noqa: E731
                decision = decide_river(
                    state, hole, board, node.history, solver.strategy, solver.abstraction,
                    solver.schedule, we_are_small_blind=(posted == seat), rng=self.rng,
                    legal=arena, budget_s=self.river_budget_s, purify=(self.purify != "none"),
                    opponent_range=opponent_range, blend=self.river_blend,
                    **({"iterations": self.river_iterations} if self.river_iterations else {}))
                choice, missed, fell_back, companion_used = decision.choice, False, False, None
                answered_history = node.history
                river = {"iterations": decision.iterations, "ms": round(decision.ms, 1),
                         "hands": decision.hands, "range": decision.range_source,
                         "strategy": {str(a): round(p, 3) for a, p in decision.distribution.items()}}
                self.stats.river_solves += 1
                if decision.range_source == "oracle":
                    self.stats.river_oracle_ranges += 1
            except Exception as error:          # the blueprint's answer stands
                river = {"error": f"{type(error).__name__}: {error}"[:200]}
                self.stats.river_failures += 1
        adjusted = river_shove or short_stack
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
                and (strength(solver) < self._top(solver) - 1
                     or (self.profiles.river_never_bluffs(self.opponent)
                         and strength(solver) <= self.HONEST_RIVER_CLASS * self._top(solver))):
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
        if choice in RAISE_ACTIONS and not board and to_call > 0 and self.profiles is not None \
                and self.profiles.never_three_bets(self.opponent) \
                and any(a.get("seat") == seat and a.get("action") == "raise"
                        and a.get("phase") == "preflop"
                        for a in state.get("action_history") or []):
            # They re-raised our open, and they do that once in eighty hands.
            # There is no bluff in a range that narrow, so the stack does not
            # go in: we continue at the price or we give up. 23 September, wsp:
            # ace-king four-bet all in for 53bb into kings, which was the
            # fixture. Calling there was 510 into 1,920 and correct. No hand is
            # exempt: a six-class abstraction cannot tell aces from ace-king,
            # and ace-king is precisely the hand this is here to stop, so the
            # first version of this rule excluded the only case it was written
            # for. Aces lose nothing by calling a range they are ahead of.
            price = to_call / float(int(state.get("pot") or 0) + to_call)
            choice = CHECK_CALL if arena[CHECK_CALL] and price <= self.VALUE_RERAISE_PRICE else \
                (FOLD if arena[FOLD] else CHECK_CALL)
            adjusted = "their re-raise is value"
            self.stats.reraises_believed += 1
        withheld = None
        if choice in RAISE_ACTIONS and arena[CHECK_CALL] and self.profiles is not None \
                and (self.withhold_preflop or board) \
                and self.profiles.never_folds(self.opponent) \
                and strength(solver) <= self.BLUFF_STRENGTH \
                and (not (self.profiles.posteriors and self.size_aware_bluffs)
                     or self._bluff_folds_too_rarely(choice, state)):
            # A measured station: bluffing it only builds a pot we are behind
            # in. Facing a bet, the alternative to the bluff-raise is the fold,
            # not a call with the bottom class: 114 of 286 firings had turned a
            # bluff into a call before 15 September. With posteriors and
            # --size-aware-bluffs on, only a bluff that needs more folds than the
            # station gives is withheld.
            withheld = int(choice)
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
        if self.aggro_reads and self.profiles is not None and choice == FOLD and to_call > 0 \
                and len(board) == 5 and arena[CHECK_CALL] and hand.effective_bb >= self.SHOVE_RULE_MIN_BB:
            # A river bet from a bot that bluffs its rivers often: call when the
            # lower bound of its bluff share pays for the call (b * pot against
            # (1 - b) * price, the pot already holding its bet) and our hand
            # beats a bluff. The mirror of "river bet believed".
            import pokerbot_native as native    # loaded lazily, as cfr/river.py does
            floor = self.profiles.river_bluff_floor(self.opponent)
            pot = int(state.get("pot") or 0)
            if floor is not None and floor * pot >= (1.0 - floor) * to_call \
                    and float(native.equity_vs_random([c.index for c in hole], [c.index for c in board],
                                                      200, 17)) >= self.BLUFF_CATCH_EQUITY:
                choice = CHECK_CALL
                adjusted = "river bluff caught"
                self.stats.river_bluffs_caught += 1
        if self.aggro_reads and self.profiles is not None and choice == CHECK_CALL and to_call == 0 \
                and len(board) in (3, 4) and arena[RAISE_HALF] and hand.effective_bb >= self.SHOVE_RULE_MIN_BB \
                and strength(solver) < self._top(solver):
            # Checked to, or first to act, on the flop or turn against a bot that
            # folds to most of our bets there and rarely raises them: half the
            # pot wins it outright often enough to show a profit with any hand.
            # The top class keeps its check, which may be a trap.
            floor = self.profiles.postflop_fold_floor(self.opponent)
            if floor is not None and floor >= self.OVER_FOLD_RATE:
                choice = RAISE_HALF
                adjusted = "bet into an over-folder"
                self.stats.overfolders_bet += 1
        if self.reraise_defence and self.profiles is not None and choice == FOLD and not board \
                and to_call > 0 and arena[CHECK_CALL]:
            # We opened and they re-raised. A bot that re-raises a large share
            # of opens is modelled as re-raising the top of all hands at that
            # rate (the tightest range the rate allows), and we call whenever
            # our equity against it beats the price. v5x folded 79% of its opens
            # to a 3x re-raise; any two cards re-raise at a profit above 62%.
            pre = [a for a in state.get("action_history") or []
                   if a.get("phase") == "preflop" and not str(a.get("action", "")).startswith("post")]
            if len(pre) == 2 and pre[0].get("seat") == seat and pre[0].get("action") == "raise" \
                    and pre[1].get("seat") != seat and pre[1].get("action") == "raise":
                floor = self.profiles.reraise_floor(self.opponent)
                if floor is not None and floor >= self.RERAISE_OFTEN:
                    from chipzen.ranges import equity_vs_top
                    pot = int(state.get("pot") or 0)
                    price = to_call / float(pot + to_call)
                    if equity_vs_top([c.index for c in hole], floor) >= price + self.RERAISE_MARGIN:
                        choice = CHECK_CALL
                        adjusted = "re-raise defended"
                        self.stats.reraises_defended += 1
        opponent_stack = int((state.get("opponent_stacks") or [0])[0])
        if to_call > 0 and opponent_stack <= 0 and arena[CHECK_CALL] and choice == FOLD \
                and to_call * self.POT_ODDS_FLOOR <= int(state.get("pot") or 0) - to_call:
            # An opponent all in for a fraction of a blind: the 5bb blueprint
            # prices "all-in" at several blinds and folded T5o at 33 to 1 on
            # 14 September. Any two cards call at these odds.
            choice = CHECK_CALL
            adjusted = "called for pot odds"
        if self.price_misread and choice == FOLD and to_call > 0 and arena[CHECK_CALL] \
                and adjusted == (river_shove or short_stack) \
                and self._misread(companion_used, answered_history, opponent_stack):
            # The strategy folded on a history that is not the hand: either a
            # street re-read after a pseudo all-in (the tree's pot is then far
            # smaller than the arena's, so any bet reads as a big one) or a
            # raise read as all-in although the bettor kept chips. Its price is
            # not the real one, so the real one decides with a strong hand. A
            # read that folded on purpose is left alone; it priced the real bet.
            import pokerbot_native as native    # loaded lazily, as cfr/river.py does
            mine = int(state.get("your_stack") or 0)
            called = min(to_call, mine) if mine > 0 else to_call
            # Their chips beyond our stack come back uncalled, so they are not in the pot we win.
            price = called / float(int(state.get("pot") or 0) - (to_call - called) + called)
            if price <= self.MISREAD_PRICE and float(native.equity_vs_random(
                    [c.index for c in hole], [c.index for c in board], 200, 17)) >= self.MISREAD_EQUITY:
                choice = CHECK_CALL
                adjusted = "priced a misread all-in"
                self.stats.misread_prices_called += 1
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
        if withheld is not None:
            # The raise taken back. Without it, which bluffs a size-aware rule would have let through
            # could be answered only by reloading the rung that played (5 Oct audit).
            record["withheld"] = withheld
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
    def _bluff_chips(choice: int, state: dict) -> int:
        """Chips a raise of `choice` puts in: the call plus the fraction of the pot after it, capped by the chips behind."""
        pot = int(state.get("pot") or 0)
        to_call = int(state.get("to_call") or 0)
        mine = int(state.get("your_stack") or 0)
        theirs = int((state.get("opponent_stacks") or [0])[0])
        behind = min(mine, to_call + theirs) if mine > 0 else to_call + theirs
        b = behind if choice == ALL_IN else to_call + (pot + to_call) * RAISE_FRACTIONS[choice - 2]
        return min(b, behind) if behind > 0 else b

    @staticmethod
    def bluff_break_even(choice: int, state: dict) -> float:
        """
        The fold share at which a raise of `choice` with no equity breaks even: it puts in b chips
        to win the pot P already there (their bet in it), so it needs b / (P + b). Half the pot
        checked to is a third, the pot a half. b is the call plus the fraction of the pot after the
        call, as `to_chipzen` sizes it, and never more than the chips either of us has behind.
        Zero equity is the pessimistic case: a bluff that sometimes wins called breaks even lower.
        """
        pot = int(state.get("pot") or 0)
        b = ArenaPlayer._bluff_chips(choice, state)
        return b / float(pot + b) if pot + b > 0 else 1.0

    @staticmethod
    def bluff_fraction(choice: int, state: dict) -> float:
        """What the raise adds over the call, as a share of the pot after the call: the size `observe` bins by."""
        to_call = int(state.get("to_call") or 0)
        return size_fraction(ArenaPlayer._bluff_chips(choice, state) - to_call, int(state.get("pot") or 0) + to_call)

    def _bluff_folds_too_rarely(self, choice: int, state: dict) -> bool:
        """
        Withhold this bluff: the posterior upper bound of their fold rate to a bet of this size is below
        what the size needs. hoops folds 36 percent overall but 44 to half-pot bets and 57 to pot-sized
        ones on the scout cache, so one overall rate withheld its pot bluffs that pay; the bin's own
        bound releases them. A bin too thin to read falls back to the overall bound (`fold_upper_at`).
        """
        upper = self.profiles.fold_upper_at(self.opponent, self.bluff_fraction(choice, state),
                                            preflop=state.get("phase") == "preflop")
        return upper is not None and upper < self.bluff_break_even(choice, state)

    @staticmethod
    def _misread(companion_used, answered_history: str, opponent_stack: int) -> bool:
        """
        Whether the answer came from a history whose price is not the arena's.

        A collapsed re-read always is, even facing a real all-in: on 5 October
        the river shove was a real one, but the turn under it had been
        collapsed, so the tree priced it as a whole stack into a small pot. A
        history ending in all-in is a misread only while the bettor still has
        chips; a real all-in on a true history is the pot-odds rule's job.
        """
        if str(companion_used or "").startswith("collapsed:"):
            return True
        return opponent_stack > 0 and str(answered_history or "").endswith(str(ALL_IN))

    @staticmethod
    def _top(solver: Solver) -> int:
        return int(getattr(solver.abstraction, "postflop_buckets", 6)) - 1

    def _short_stack_answer(self, hole, board, effective_bb: float, mask, state, seat: int):
        """
        A preflop all-in at a short stack, answered exactly rather than by the rule.

        Only this spot, because only here is the rule provably wrong: it folds
        to any bet of the pot or more it has no read on, which after our own
        raise at eight blinds folded 45% of the hands that should call, 0.69
        big blinds each (23 September, `scripts/push_fold_cost.py` and the duel
        against exact play). Returns None whenever the solution does not apply,
        and then `fallback_choice` answers as before.

        The range that shoved is read from our own history: over a raise of
        ours it is the solution's calling range, which is the tighter of the
        two, and an open shove is priced against its shoving range.
        """
        if self.short_ranges is None or board or effective_bb > self.SHORT_STACK_MAX_BB:
            return None
        to_call = int(state.get("to_call") or 0)
        opponent_stack = int((state.get("opponent_stacks") or [0])[0])
        all_in = to_call > 0 and (opponent_stack <= 0 or to_call >= int(state.get("your_stack") or 0))
        if not all_in or not mask[FOLD] or not mask[CHECK_CALL]:
            return None
        raised = any(a.get("seat") == seat and a.get("action") == "raise"
                     and a.get("phase") == "preflop"
                     for a in state.get("action_history") or [])
        calls = self.short_ranges.calls(hole, effective_bb, to_call,
                                        int(state.get("pot") or 0), reraise=raised)
        if calls is None:
            return None
        return CHECK_CALL if calls else FOLD

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
