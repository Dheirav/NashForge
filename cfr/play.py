"""
Playing strategies against each other, for games too large to evaluate exactly.

On Kuhn and Leduc a strategy is measured by traversing the whole tree, which is
exact. No-limit Hold'em cannot be traversed, so the only available measure is to
play hands and count chips — and a chip count over a few thousand hands of poker
is dominated by variance, not by skill.

Two things follow, and both are applied here.

**Every result carries a standard error.** A number without one cannot be
compared to another number. This project has a history of ranking configurations
on differences far inside their own noise; see CODEBASE_AUDIT.md.

**Seats alternate.** In heads-up play position is worth a great deal, so a
strategy measured only in the small blind is measured against a confound. Each
hand is played from both seats.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Hashable, Optional, Sequence

import numpy as np

from games.base import Game

#: A policy is called with the game, the state, the player to act and the
#: number of legal actions, and returns action probabilities. Returning None
#: means "no opinion", and uniform is used.
#:
#: It receives the STATE rather than just the information-set key so that two
#: agents trained on different abstractions can play each other: each must be
#: able to compute the key its own abstraction would produce. Passing only the
#: game's key would silently feed one agent another's bucketing, and it would
#: look like it was playing badly rather than being asked the wrong question.
Policy = Callable[[Any, Any, int, int], Optional[np.ndarray]]


def strategy_policy(strategy: Dict[Hashable, np.ndarray],
                    abstraction: Any = None) -> Policy:
    """
    Wrap a solved strategy table as a policy.

    With ``abstraction``, keys are computed through that abstraction rather than
    the game's — which is what lets an agent play in a game whose abstraction is
    not its own.
    """
    def policy(game, state, player: int, num_actions: int) -> Optional[np.ndarray]:
        if abstraction is None:
            key = game.information_set(state, player)
        else:
            key = game.information_set_with(state, player, abstraction)
        probabilities = strategy.get(key)
        if probabilities is None or probabilities.size != num_actions:
            return None
        return probabilities
    return policy


def uniform_policy() -> Policy:
    """Plays every legal action equally often."""
    return lambda game, state, player, num_actions: None


def always_call_policy(call_action: int = 1) -> Policy:
    """
    Never folds, never raises — the classic passive baseline.

    A strategy that cannot beat this is not playing poker. Note it also cannot
    be bluffed, so it does not test semi-bluffing or draw play at all.
    """
    def policy(game, state, player: int, num_actions: int) -> Optional[np.ndarray]:
        probabilities = np.zeros(num_actions)
        probabilities[min(call_action, num_actions - 1)] = 1.0
        return probabilities
    return policy


@dataclass(frozen=True)
class MatchResult:
    """Chips per hand to the first strategy, with its uncertainty."""
    hands: int
    mean: float
    stderr: float

    @property
    def ci95(self) -> tuple:
        return (self.mean - 1.96 * self.stderr, self.mean + 1.96 * self.stderr)

    @property
    def separated_from_zero(self) -> bool:
        """Whether this many hands can tell the result apart from break-even."""
        low, high = self.ci95
        return low > 0.0 or high < 0.0

    def summary(self, per_hand: str = "chips/hand") -> str:
        low, high = self.ci95
        verdict = "" if self.separated_from_zero else "  (not separated from zero)"
        return (f"{self.mean:+.3f} +/- {self.stderr:.3f} {per_hand}"
                f"  95% CI [{low:+.3f}, {high:+.3f}]{verdict}")


def play_hands(game: Game, policies: Sequence[Policy], hands: int,
               rng: Optional[np.random.Generator] = None,
               alternate_seats: bool = True) -> MatchResult:
    """
    Play ``hands`` hands and report the result to ``policies[0]``.

    With ``alternate_seats``, each hand is played twice — once from each seat —
    and the two results averaged, so position cancels rather than being
    absorbed into the estimate.
    """
    rng = rng if rng is not None else np.random.default_rng()
    outcomes = []

    for _ in range(hands):
        if alternate_seats:
            first = _play_one(game, [policies[0], policies[1]], rng)
            second = _play_one(game, [policies[1], policies[0]], rng)
            outcomes.append((first - second) / 2.0)
        else:
            outcomes.append(_play_one(game, policies, rng))

    values = np.asarray(outcomes, dtype=np.float64)
    stderr = values.std(ddof=1) / np.sqrt(values.size) if values.size > 1 else float("nan")
    return MatchResult(hands=values.size, mean=float(values.mean()), stderr=float(stderr))


def _play_one(game: Game, policies: Sequence[Policy],
              rng: np.random.Generator) -> float:
    """One hand; returns chips to the policy seated at index 0."""
    state = game.initial_state()
    guard = 0

    while not game.is_terminal(state):
        guard += 1
        if guard > 200:
            raise RuntimeError(f"hand did not terminate: {state}")

        if game.is_chance(state):
            state = game.next_state(state, game.sample_chance(state, rng))
            continue

        player = game.current_player(state)
        actions = game.legal_actions(state)

        probabilities = policies[player](game, state, player, len(actions))
        if probabilities is None:
            probabilities = np.full(len(actions), 1.0 / len(actions))

        index = int(rng.choice(len(actions), p=probabilities))
        state = game.next_state(state, actions[index])

    return game.utility(state, 0)
