"""
One panel every agent is measured against, whatever produced it.

The failure this exists to prevent is the one the audit found: agents evaluated
against other agents from the same lineage, so a population could improve
against itself for 89 runs while getting worse at poker, and nothing in the
numbers said so. A benchmark is only worth having if it does not share the
lineage of what it measures.

The panel is `random`, `always-call`, and **the CFR agent** — the last of which
was validated against Kuhn poker's analytic value of −1/18 and exact
exploitability on Leduc, and shares no ancestry with an evolutionary or
policy-gradient run.

Both games, one match
---------------------
The solver lives in :mod:`games.nolimit`, a traversable reimplementation; the
networks train against :class:`engine.PokerGame`. Matches are played in the
*engine*, so no agent is evaluated somewhere other than where it was trained —
a train/evaluate split is precisely how the previous feature bugs hid.

That works because both sides already share the same six abstract actions
(fold, check/call, half pot, pot, two pot, all-in). Since this harness drives
the loop, it knows which abstract action each agent chose and maintains the
solver's ``bucket|history`` key itself, so the CFR agent's lookup is exact
rather than translated. Two constraints are applied to make the engine's legal
set agree with the tree the solver was trained on:

* **A raise cap**, matching the solver's. The engine mask permits unlimited
  raises per street; the solver has never seen those histories.
* **No folding with nothing to call.** The engine offers it, the solver's tree
  excludes it as dominated. An agent that takes it is throwing away a free
  card, so removing it costs nothing and keeps the histories aligned.

Where the lookup misses anyway — an unreached information set — the CFR agent
plays uniformly over legal actions, and :attr:`BenchmarkResult.lookup_miss_rate`
reports how often. A benchmark quietly degrading to a random opponent is worse
than no benchmark, so the rate is measured rather than assumed small.

Duplicate play
--------------
Each hand is dealt twice from the same seed with the seats swapped, so both
agents hold the same cards against the same opposing cards and card luck
cancels rather than being averaged over. The engine reseeds per hand, so this
is exact rather than best-effort.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, Hashable, List, Optional, Sequence

import numpy as np

from abstraction.betting import ALL_IN, CHECK_CALL, FOLD
from engine import Action, PokerGame, get_abstract_action_mask
from training.fitness import abstract_action_to_engine_action

#: An agent is called with the game, its seat, the legality mask over the six
#: abstract actions, and the solver-format betting history so far. It returns an
#: index into the mask. Anything that does not need the history ignores it.
Agent = Callable[[PokerGame, int, np.ndarray, str], int]

NUM_ACTIONS = 6
RAISE_ACTIONS = (2, 3, 4, 5)


@dataclass
class BenchmarkResult:
    """One matchup, with the uncertainty attached rather than implied."""
    opponent: str
    hands: int
    chips_per_hand: float
    stderr: float
    big_blind: int
    lookup_miss_rate: float = 0.0

    @property
    def ci95(self) -> tuple:
        return (self.chips_per_hand - 1.96 * self.stderr,
                self.chips_per_hand + 1.96 * self.stderr)

    @property
    def bb_per_100(self) -> float:
        return self.chips_per_hand / self.big_blind * 100

    @property
    def separated_from_zero(self) -> bool:
        return abs(self.chips_per_hand) > 1.96 * self.stderr

    def summary(self) -> str:
        low, high = self.ci95
        verdict = "beats" if self.chips_per_hand > 0 else "loses to"
        if not self.separated_from_zero:
            verdict = "not separated from"
        return (f"vs {self.opponent:<14} {self.chips_per_hand:+7.3f} "
                f"+/- {self.stderr:.3f} chips/hand  [{low:+.3f}, {high:+.3f}]  "
                f"= {self.bb_per_100:+7.1f} BB/100   {verdict} it")


# ---------------------------------------------------------------------------
# The panel
# ---------------------------------------------------------------------------

def random_agent(rng: np.random.Generator) -> Agent:
    """Uniform over whatever is legal. The floor any agent must clear."""
    def act(game, player_id, mask, history):
        legal = np.flatnonzero(mask)
        return int(rng.choice(legal))
    return act


def always_call_agent() -> Agent:
    """
    Never folds, never raises. A weak opponent, but a *specific* one — beating
    it says the agent is not simply passive, and losing to it is diagnostic.
    """
    def act(game, player_id, mask, history):
        return CHECK_CALL if mask[CHECK_CALL] else int(np.flatnonzero(mask)[0])
    return act


def cfr_agent(strategy: Dict[Hashable, np.ndarray], abstraction,
              rng: np.random.Generator, misses: Optional[List[int]] = None) -> Agent:
    """
    A solved strategy, playing in the engine.

    The key is rebuilt here rather than read off the engine: the bucket comes
    from the cards, which are the same objects in both games, and the history
    is the one this harness has been maintaining. ``misses`` counts information
    sets the strategy has no entry for, so a benchmark that has quietly become
    a random opponent shows up as a number.
    """
    def act(game, player_id, mask, history):
        hole = game.players[player_id].hole_cards
        board = game.state.community_cards
        bucket = abstraction.bucket(hole, board, rng)

        probabilities = strategy.get(f"{bucket}|{history}")
        legal = np.flatnonzero(mask)

        if probabilities is None or probabilities.size != NUM_ACTIONS:
            if misses is not None:
                misses[0] += 1
            return int(rng.choice(legal))

        weights = np.asarray(probabilities, dtype=np.float64) * mask
        total = weights.sum()
        if total <= 0.0:
            if misses is not None:
                misses[0] += 1
            return int(rng.choice(legal))
        return int(rng.choice(NUM_ACTIONS, p=weights / total))
    return act


# ---------------------------------------------------------------------------
# Playing a hand
# ---------------------------------------------------------------------------

def _constrain(mask: np.ndarray, to_call: int, raises_this_street: int,
               raise_cap: int) -> np.ndarray:
    """
    Narrow the engine's legal set to the tree the solver was trained on.

    Both changes remove options rather than add them, so no agent is ever asked
    for something the engine would reject.
    """
    mask = mask.copy()
    if to_call <= 0:
        mask[FOLD] = 0.0                       # dominated, and off-tree
    if raises_this_street >= raise_cap:
        for action in RAISE_ACTIONS:
            mask[action] = 0.0
    if not mask.any():                         # never strand the actor
        mask[CHECK_CALL] = 1.0
    return mask


def _play_hand(agents: Sequence[Agent], seed: int, starting_stack: int,
               small_blind: int, big_blind: int, raise_cap: int) -> float:
    """
    One hand. Returns chips won by ``agents[0]``, who sits in seat 0.

    The seed fixes the deal, so calling this twice with the seats swapped gives
    both agents the same cards — duplicate play, exactly rather than
    approximately.
    """
    game = PokerGame([starting_stack] * 2, small_blind=small_blind,
                     big_blind=big_blind, seed=seed, enable_history=False)

    history = ""
    street = game.state.betting_round
    raises_this_street = 0
    guard = 0

    while not game.is_hand_over():
        guard += 1
        if guard > 200:
            raise RuntimeError(f"hand did not terminate: {history!r}")

        player = game.state.current_player
        if player is None:
            break

        if game.state.betting_round != street:
            street = game.state.betting_round
            history += "/"
            raises_this_street = 0

        actor = game.players[player]
        to_call = game.current_bet - actor.bet
        mask = _constrain(get_abstract_action_mask(game, player), to_call,
                          raises_this_street, raise_cap)

        choice = agents[player](game, player, mask, history)
        if not mask[choice]:
            choice = int(np.flatnonzero(mask)[0])

        history += str(choice)
        if choice in RAISE_ACTIONS:
            raises_this_street += 1

        game.apply_action(player, abstract_action_to_engine_action(choice, game, player))

    return game.players[0].stack - starting_stack


# ---------------------------------------------------------------------------
# The benchmark
# ---------------------------------------------------------------------------

def benchmark(agent: Agent, opponent: Agent, name: str, hands: int = 2000,
              seed: int = 0, starting_stack: int = 200, small_blind: int = 1,
              big_blind: int = 2, raise_cap: int = 1,
              misses: Optional[List[int]] = None) -> BenchmarkResult:
    """
    Play ``agent`` against ``opponent`` and report chips per hand to ``agent``.

    Every hand is played twice from one seed with the seats swapped, and the
    two results differenced. Position cancels because each agent sits in both
    seats; card luck cancels because both hold the same cards.
    """
    outcomes = np.empty(hands, dtype=np.float64)
    decisions = [0]
    if misses is None:
        misses = [0]

    for index in range(hands):
        deal = seed * 1_000_003 + index
        ours = _play_hand([agent, opponent], deal, starting_stack,
                          small_blind, big_blind, raise_cap)
        theirs = _play_hand([opponent, agent], deal, starting_stack,
                            small_blind, big_blind, raise_cap)
        outcomes[index] = (ours - theirs) / 2.0
        decisions[0] += 1

    stderr = (float(outcomes.std(ddof=1) / math.sqrt(hands)) if hands > 1
              else float("nan"))
    seen = max(1, decisions[0])
    return BenchmarkResult(opponent=name, hands=hands,
                           chips_per_hand=float(outcomes.mean()), stderr=stderr,
                           big_blind=big_blind,
                           lookup_miss_rate=misses[0] / seen)


def default_panel(rng: np.random.Generator,
                  cfr_strategy: Optional[Dict[Hashable, np.ndarray]] = None,
                  abstraction=None,
                  misses: Optional[List[int]] = None) -> List[tuple]:
    """
    The opponents every agent is measured against, weakest first.

    The solver is optional only so the panel still works before one has been
    trained. A run without it is measuring against two baselines that any
    competent agent beats, which is a floor check rather than a benchmark.
    """
    panel = [("random", random_agent(rng)), ("always-call", always_call_agent())]
    if cfr_strategy is not None and abstraction is not None:
        panel.append(("cfr", cfr_agent(cfr_strategy, abstraction, rng, misses)))
    return panel
