"""
Local Best Response — a computable lower bound on exploitability.

Exploitability is the measure that matters: how much a best-responding opponent
wins. On Kuhn and Leduc it is computed exactly by traversing the tree. No-limit
Hold'em cannot be traversed, so the only alternative has been head-to-head chip
counts — and beating a passive baseline says nothing about distance from
equilibrium.

LBR (Lisý & Bowling, 2017) closes that gap. Instead of a true best response it
plays a *greedy* one: track what the opponent's actions reveal about their hand,
then at each decision pick whichever action looks best under a one-step
lookahead. Because that is only a subset of the strategies a real best response
could play, whatever LBR wins is a **lower bound** on exploitability. A large
LBR value proves a strategy is exploitable; a small one proves nothing, which is
the direction of the guarantee and worth stating whenever the number is quoted.

Two design choices specific to this implementation:

* **The opponent's range is tracked over buckets, not over hands.** That is not
  an approximation here — the opponent's strategy is keyed on its bucket, so two
  hands in the same bucket are played identically by construction. Tracking six
  buckets instead of 1,225 hands is exact for the belief update and roughly two
  hundred times cheaper.

* **After the modelled action the hand is rolled out to showdown**, with no
  further betting. This is the standard LBR simplification and it is why the
  result is a bound rather than the true value: LBR never plans a second barrel.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Hashable, List, Optional, Sequence

import numpy as np

from abstraction.betting import ALL_IN, CHECK_CALL, FOLD
from abstraction.equity import FULL_DECK
from engine.hand_eval_fast import evaluate_hand_fast


@dataclass(frozen=True)
class LBRResult:
    """What LBR won, and how sure we are of it."""
    hands: int
    mean: float
    stderr: float

    @property
    def ci95(self) -> tuple:
        return (self.mean - 1.96 * self.stderr, self.mean + 1.96 * self.stderr)

    @property
    def proves_exploitable(self) -> bool:
        """True when the interval clears zero, so the bound is meaningful."""
        return self.mean - 1.96 * self.stderr > 0.0

    def summary(self) -> str:
        low, high = self.ci95
        verdict = ("exploitable by at least this much"
                   if self.proves_exploitable else "no exploitability proven")
        return (f"{self.mean:+.3f} +/- {self.stderr:.3f} chips/hand "
                f"[{low:+.3f}, {high:+.3f}] — {verdict}")


class LocalBestResponse:
    """
    A greedy exploiter of a fixed strategy in an abstracted no-limit game.

    Args:
        game: The :class:`~games.nolimit.NoLimitHoldem` being played.
        strategy: The strategy under test, keyed as the game keys its
            information sets.
        rollout_samples: Opponent hands sampled per decision to estimate the
            chance of winning a showdown.
    """

    def __init__(self, game, strategy: Dict[Hashable, np.ndarray],
                 rollout_samples: int = 60):
        self.game = game
        self.strategy = strategy
        self.rollout_samples = rollout_samples
        self.num_buckets = game.abstraction.postflop_buckets

    # ------------------------------------------------------------------

    def _opponent_probabilities(self, state, opponent: int,
                                bucket: int) -> Optional[np.ndarray]:
        """The opponent's action probabilities if they held ``bucket``."""
        key = f"{bucket}|{state.history}"
        probabilities = self.strategy.get(key)
        if probabilities is None:
            return None
        actions = self.game.legal_actions(state)
        if probabilities.size != len(actions):
            return None
        return probabilities

    def _update_belief(self, belief: np.ndarray, state, opponent: int,
                       action_index: int) -> np.ndarray:
        """
        Bayes: reweight each bucket by how likely it was to take the action.

        A bucket the opponent would never have played this way drops out, which
        is the entire source of LBR's leverage — it is exploiting the
        information their betting gives away.
        """
        updated = belief.copy()
        for bucket in range(self.num_buckets):
            probabilities = self._opponent_probabilities(state, opponent, bucket)
            likelihood = (probabilities[action_index] if probabilities is not None
                          else 1.0 / len(self.game.legal_actions(state)))
            updated[bucket] *= likelihood

        total = updated.sum()
        if total <= 0.0:                       # every bucket ruled out: reset
            return np.full(self.num_buckets, 1.0 / self.num_buckets)
        return updated / total

    def _win_probability(self, state, me: int, belief: np.ndarray,
                         rng: np.random.Generator) -> float:
        """
        Chance of winning a showdown against the believed range.

        Opponent hands are sampled from the remaining deck, weighted by how much
        belief sits on the bucket each one falls into, and the board is completed
        at random. Ties count half.
        """
        known = set(state.board) | set(state.hole[me]) | set(state.hole[1 - me])
        available = np.array([i for i in range(len(FULL_DECK)) if i not in known])
        runout = 5 - len(state.board)
        draw = 2 + runout

        mine = [FULL_DECK[c] for c in state.hole[me]]
        board = [FULL_DECK[c] for c in state.board]

        weighted_wins = 0.0
        total_weight = 0.0
        for _ in range(self.rollout_samples):
            picked = rng.choice(available, size=draw, replace=False)
            opponent_hand = [FULL_DECK[i] for i in picked[:2]]
            completed = board + [FULL_DECK[i] for i in picked[2:]]

            bucket = self.game.abstraction.bucket(opponent_hand, completed, rng)
            weight = belief[min(bucket, self.num_buckets - 1)]
            if weight <= 0.0:
                continue

            ours = evaluate_hand_fast(mine + completed)
            theirs = evaluate_hand_fast(opponent_hand + completed)
            outcome = 1.0 if ours > theirs else (0.5 if ours == theirs else 0.0)
            weighted_wins += weight * outcome
            total_weight += weight

        if total_weight <= 0.0:
            return 0.5
        return weighted_wins / total_weight

    def _fold_probability(self, state, opponent: int, belief: np.ndarray) -> float:
        """Chance the opponent folds to the action just taken, over the range."""
        actions = self.game.legal_actions(state)
        if FOLD not in actions:
            return 0.0
        index = list(actions).index(FOLD)

        total = 0.0
        for bucket in range(self.num_buckets):
            probabilities = self._opponent_probabilities(state, opponent, bucket)
            if probabilities is None:
                continue
            total += belief[bucket] * probabilities[index]
        return float(np.clip(total, 0.0, 1.0))

    def _choose(self, state, me: int, belief: np.ndarray,
                rng: np.random.Generator) -> int:
        """
        Index of the action with the highest one-step value.

        Folding is worth losing what we already put in. Any other action is
        valued by rolling the hand out to showdown, plus — for a raise — the
        chance the opponent simply folds.
        """
        actions = list(self.game.legal_actions(state))
        opponent = 1 - me
        win = self._win_probability(state, me, belief, rng)

        mine_in = state.contributions[me]
        theirs_in = state.contributions[opponent]
        to_call = max(state.committed[opponent] - state.committed[me], 0)

        values: List[float] = []
        for action in actions:
            if action == FOLD:
                values.append(-float(mine_in))
                continue

            after = self.game.next_state(state, action)
            my_total = after.contributions[me]
            their_total = after.contributions[opponent]

            showdown = win * their_total - (1.0 - win) * my_total

            if action == CHECK_CALL:
                values.append(showdown)
            else:
                # A raise also wins outright whenever they fold.
                folds = self._fold_probability(after, opponent, belief)
                values.append(folds * theirs_in + (1.0 - folds) * showdown)

        return int(np.argmax(values))

    # ------------------------------------------------------------------

    def play(self, hands: int, rng: Optional[np.random.Generator] = None,
             alternate_seats: bool = True) -> LBRResult:
        """Play ``hands`` hands as the exploiter and report the average won."""
        rng = rng if rng is not None else np.random.default_rng()
        outcomes = []
        for _ in range(hands):
            if alternate_seats:
                outcomes.append((self._one(0, rng) + self._one(1, rng)) / 2.0)
            else:
                outcomes.append(self._one(0, rng))

        values = np.asarray(outcomes, dtype=np.float64)
        stderr = (values.std(ddof=1) / np.sqrt(values.size)
                  if values.size > 1 else float("nan"))
        return LBRResult(values.size, float(values.mean()), float(stderr))

    def _one(self, me: int, rng: np.random.Generator) -> float:
        """One hand with LBR in seat ``me``; returns chips won by LBR."""
        game = self.game
        state = game.initial_state()
        belief = np.full(self.num_buckets, 1.0 / self.num_buckets)
        guard = 0

        while not game.is_terminal(state):
            guard += 1
            if guard > 200:
                raise RuntimeError(f"hand did not terminate: {state.history!r}")

            if game.is_chance(state):
                state = game.next_state(state, game.sample_chance(state, rng))
                continue

            player = game.current_player(state)
            actions = list(game.legal_actions(state))

            if player == me:
                index = self._choose(state, me, belief, rng)
            else:
                key = game.information_set(state, player)
                probabilities = self.strategy.get(key)
                if probabilities is None or probabilities.size != len(actions):
                    probabilities = np.full(len(actions), 1.0 / len(actions))
                index = int(rng.choice(len(actions), p=probabilities))
                belief = self._update_belief(belief, state, player, index)

            state = game.next_state(state, actions[index])

        return game.utility(state, me)


def lbr_value(game, strategy: Dict[Hashable, np.ndarray], hands: int = 2000,
              rng: Optional[np.random.Generator] = None,
              rollout_samples: int = 60) -> LBRResult:
    """
    Lower bound on the exploitability of ``strategy``, in chips per hand.

    Positive and clear of zero means the strategy is provably exploitable by at
    least this much. Near zero means only that LBR failed to exploit it — not
    that it is close to equilibrium.
    """
    return LocalBestResponse(game, strategy, rollout_samples).play(hands, rng)
