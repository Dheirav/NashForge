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

* **The opponent's range is a weighted set of candidate hands**, resampled once
  per hand and reweighted by Bayes as the opponent acts. The obvious cheaper
  alternative — carrying a distribution over bucket indices — does not work
  here, because :class:`~abstraction.buckets.CardAbstraction` fits a *separate*
  clustering per street. Bucket 3 on the flop and bucket 3 on the turn are
  unrelated categories, so a belief accumulated over one street's indices cannot
  be carried into the next. Tracking hands and re-bucketing them against
  whatever board is actually out keeps every lookup on the street it belongs to.

* **After the modelled action the hand is rolled out to showdown**, with no
  further betting. This is the standard LBR simplification and it is why the
  result is a bound rather than the true value: LBR never plans a second barrel.

LBR sees only what a real opponent would: its own cards, the board, and the
betting. It never reads ``state.hole`` for the player it is exploiting.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Hashable, List, Optional, Sequence, Tuple

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


class Range:
    """
    What LBR believes about the opponent's hand: candidate hands and weights.

    The buckets are cached against the board they were computed for, so a new
    street invalidates them and they are recomputed lazily — a hand that ends on
    the flop never pays for turn and river bucketing.
    """

    __slots__ = ("hands", "weights", "buckets", "board")

    def __init__(self, hands: List[Tuple[int, int]], weights: np.ndarray):
        self.hands = hands
        self.weights = weights
        self.buckets: List[int] = []
        self.board: Optional[Tuple[int, ...]] = None

    def live(self) -> np.ndarray:
        """Indices of candidates still carrying weight."""
        return np.flatnonzero(self.weights > 0.0)


class LocalBestResponse:
    """
    A greedy exploiter of a fixed strategy in an abstracted no-limit game.

    Args:
        game: The :class:`~games.nolimit.NoLimitHoldem` being played.
        strategy: The strategy under test, keyed as the game keys its
            information sets.
        rollout_samples: Showdowns sampled per decision to estimate the chance of
            winning.
        candidates: Opponent hands carried as the range. More is a finer read on
            what the betting revealed; the cost is one bucket lookup each per
            street actually reached.
    """

    def __init__(self, game, strategy: Dict[Hashable, np.ndarray],
                 rollout_samples: int = 60, candidates: int = 32):
        self.game = game
        self.strategy = strategy
        self.rollout_samples = rollout_samples
        self.candidates = candidates

    # ------------------------------------------------------------------

    def _deal_range(self, state, me: int, rng: np.random.Generator) -> Range:
        """
        A fresh uniform range over hands the opponent could hold.

        Sampled from the deck less LBR's own cards. The board is *not* excluded
        here — it is empty at this point — so candidates that later collide with
        a board card are dropped as it comes out, which is the same conditioning
        applied at the right time.
        """
        blocked = set(int(c) for c in state.hole[me])
        available = [c for c in range(len(FULL_DECK)) if c not in blocked]

        hands: List[Tuple[int, int]] = []
        for _ in range(self.candidates):
            picked = rng.choice(len(available), size=2, replace=False)
            hands.append((available[int(picked[0])], available[int(picked[1])]))

        return Range(hands, np.full(len(hands), 1.0 / len(hands)))

    def _sync(self, candidate_range: Range, board: Tuple[int, ...]) -> None:
        """
        Bring the range up to date with the board.

        Two things happen when a street lands: candidates holding a card that
        just appeared on the board become impossible and lose their weight, and
        every survivor must be re-bucketed against the new board, because the
        bucket it had on the previous street was drawn from a different
        clustering entirely.
        """
        board = tuple(int(c) for c in board)
        if candidate_range.board == board:
            return

        on_board = set(board)
        possible = np.array([0.0 if (a in on_board or b in on_board) else 1.0
                             for a, b in candidate_range.hands])

        weights = candidate_range.weights * possible
        total = weights.sum()
        if total > 0.0:
            candidate_range.weights = weights / total
        elif possible.sum() > 0.0:
            # Everything that survived the board had already been ruled out by
            # the betting. Keep the survivors, drop the read.
            candidate_range.weights = possible / possible.sum()
        else:
            # Every candidate collides with the board. Vanishingly rare, but it
            # must not produce NaNs: fall back to a flat read over all of them.
            candidate_range.weights = np.full(len(candidate_range.hands),
                                              1.0 / len(candidate_range.hands))

        candidate_range.buckets = [
            self.game.bucket_for(hand, board) if weight > 0.0 else -1
            for hand, weight in zip(candidate_range.hands, candidate_range.weights)
        ]
        candidate_range.board = board

    # ------------------------------------------------------------------

    def _action_probabilities(self, candidate_range: Range, index: int,
                              state, num_actions: int) -> Optional[np.ndarray]:
        """How a given candidate hand would act here, or None if unmodelled."""
        probabilities = self.strategy.get(
            f"{candidate_range.buckets[index]}|{state.history}")
        if probabilities is None or probabilities.size != num_actions:
            return None
        return probabilities

    def _update_belief(self, candidate_range: Range, state,
                       action_index: int) -> None:
        """
        Bayes: reweight each candidate by how likely it was to act this way.

        A hand that would never have played like this drops out, which is the
        entire source of LBR's leverage — it is exploiting the information the
        betting gives away. Hands the strategy has no entry for are left alone
        rather than guessed at, so an unmodelled line neither confirms nor
        eliminates anything.
        """
        self._sync(candidate_range, state.board)
        num_actions = len(self.game.legal_actions(state))
        uniform = 1.0 / num_actions

        updated = candidate_range.weights.copy()
        for index in candidate_range.live():
            probabilities = self._action_probabilities(candidate_range, index,
                                                       state, num_actions)
            likelihood = (uniform if probabilities is None
                          else probabilities[action_index])
            updated[index] *= likelihood

        total = updated.sum()
        if total <= 0.0:
            # The observed action was impossible for every candidate, so the
            # strategy is not the one being modelled here. Keep the previous
            # read rather than inventing a new one.
            return
        candidate_range.weights = updated / total

    def _win_probability(self, state, me: int, candidate_range: Range,
                         rng: np.random.Generator) -> float:
        """
        Chance of winning a showdown against the believed range.

        A candidate is drawn in proportion to its weight, the board is completed
        around it, and the two hands are compared. Ties count half.
        """
        self._sync(candidate_range, state.board)
        live = candidate_range.live()
        if live.size == 0:
            return 0.5

        probabilities = candidate_range.weights[live]
        probabilities = probabilities / probabilities.sum()

        known = set(int(c) for c in state.board) | set(int(c) for c in state.hole[me])
        runout = 5 - len(state.board)
        mine = [FULL_DECK[c] for c in state.hole[me]]
        board = [FULL_DECK[c] for c in state.board]

        wins = 0.0
        for _ in range(self.rollout_samples):
            index = int(live[rng.choice(live.size, p=probabilities)])
            first, second = candidate_range.hands[index]

            blocked = known | {first, second}
            available = [c for c in range(len(FULL_DECK)) if c not in blocked]
            drawn = (rng.choice(len(available), size=runout, replace=False)
                     if runout else ())
            completed = board + [FULL_DECK[available[int(c)]] for c in drawn]

            ours = evaluate_hand_fast(mine + completed)
            theirs = evaluate_hand_fast(
                [FULL_DECK[first], FULL_DECK[second]] + completed)
            wins += 1.0 if ours > theirs else (0.5 if ours == theirs else 0.0)

        return wins / self.rollout_samples

    def _fold_probability(self, state, candidate_range: Range) -> float:
        """Chance the opponent folds to the action just taken, over the range."""
        actions = self.game.legal_actions(state)
        if FOLD not in actions:
            return 0.0
        index = list(actions).index(FOLD)

        self._sync(candidate_range, state.board)
        total = 0.0
        for candidate in candidate_range.live():
            probabilities = self._action_probabilities(candidate_range, candidate,
                                                       state, len(actions))
            if probabilities is None:
                continue
            total += candidate_range.weights[candidate] * probabilities[index]
        return float(np.clip(total, 0.0, 1.0))

    def _choose(self, state, me: int, candidate_range: Range,
                rng: np.random.Generator) -> int:
        """
        Index of the action with the highest one-step value.

        Folding is worth losing what we already put in. Any other action is
        valued by rolling the hand out to showdown, plus — for a raise — the
        chance the opponent simply folds.
        """
        actions = list(self.game.legal_actions(state))
        opponent = 1 - me
        win = self._win_probability(state, me, candidate_range, rng)

        mine_in = state.contributions[me]
        theirs_in = state.contributions[opponent]

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
                folds = self._fold_probability(after, candidate_range)
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
        candidate_range = None
        guard = 0

        while not game.is_terminal(state):
            guard += 1
            if guard > 200:
                raise RuntimeError(f"hand did not terminate: {state.history!r}")

            if game.is_chance(state):
                state = game.next_state(state, game.sample_chance(state, rng))
                if candidate_range is None and state.hole:
                    candidate_range = self._deal_range(state, me, rng)
                continue

            player = game.current_player(state)
            actions = list(game.legal_actions(state))

            if player == me:
                index = self._choose(state, me, candidate_range, rng)
            else:
                key = game.information_set(state, player)
                probabilities = self.strategy.get(key)
                if probabilities is None or probabilities.size != len(actions):
                    probabilities = np.full(len(actions), 1.0 / len(actions))
                index = int(rng.choice(len(actions), p=probabilities))
                self._update_belief(candidate_range, state, index)

            state = game.next_state(state, actions[index])

        return game.utility(state, me)


def lbr_value(game, strategy: Dict[Hashable, np.ndarray], hands: int = 2000,
              rng: Optional[np.random.Generator] = None,
              rollout_samples: int = 60, candidates: int = 32) -> LBRResult:
    """
    Lower bound on the exploitability of ``strategy``, in chips per hand.

    Positive and clear of zero means the strategy is provably exploitable by at
    least this much. Near zero means only that LBR failed to exploit it — not
    that it is close to equilibrium. A negative value is not negative
    exploitability, which cannot exist: it means this particular greedy
    exploiter lost money, so the bound is slack and says nothing at all.
    """
    return LocalBestResponse(game, strategy, rollout_samples,
                             candidates).play(hands, rng)
