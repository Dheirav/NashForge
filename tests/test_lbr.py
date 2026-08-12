"""
Local Best Response: a computable lower bound on exploitability.

LBR is the only exploitability measure available in no-limit, so it needs
checking as carefully as anything it will be used to judge. The difficulty is
that there is no exact answer to compare against — that is the whole reason LBR
exists — so these tests pin it in three other ways:

* **A known answer.** Against an opponent who always folds, the exploiter's
  winnings are arithmetic, not opinion.
* **Ordering.** A strategy trained for longer must not be *more* exploitable
  than an untrained one. LBR that cannot tell those apart is measuring noise.
* **Mechanism.** The belief update must actually rule buckets out; without that
  LBR has no leverage and degenerates into a fixed heuristic.

    python -m pytest tests/test_lbr.py -q
"""
import numpy as np
import pytest

from abstraction.betting import CHECK_CALL, FOLD
from abstraction.buckets import CardAbstraction
from cfr import MCCFRSolver, VANILLA, lbr_value
from cfr.lbr import LocalBestResponse
from games.nolimit import NoLimitHoldem


@pytest.fixture(scope="module")
def game():
    abstraction = CardAbstraction(preflop_buckets=4, postflop_buckets=4,
                                  samples=300, equity_samples=30,
                                  strength="made_hand").fit(np.random.default_rng(0))
    return NoLimitHoldem(abstraction, raise_cap=1, equity_samples=30)


@pytest.fixture(scope="module")
def trained(game):
    solver = MCCFRSolver(game, rule=VANILLA, seed=0)
    solver.train(4000)
    return solver.average_strategy()


def constant_strategy(game, action, buckets=4):
    """A strategy that always takes ``action`` wherever it is legal."""
    from abstraction.betting import enumerate_street_sequences  # noqa: F401

    strategy = {}
    rng = np.random.default_rng(0)
    seen = set()

    def walk(state, depth=0):
        if game.is_terminal(state) or depth > 30:
            return
        if game.is_chance(state):
            walk(game.next_state(state, game.sample_chance(state, rng)), depth + 1)
            return
        player = game.current_player(state)
        actions = list(game.legal_actions(state))
        for bucket in range(buckets):
            key = f"{bucket}|{state.history}"
            if key not in seen:
                seen.add(key)
                probabilities = np.zeros(len(actions))
                index = actions.index(action) if action in actions else \
                    actions.index(CHECK_CALL)
                probabilities[index] = 1.0
                strategy[key] = probabilities
        for candidate in actions:
            walk(game.next_state(state, candidate), depth + 1)

    for _ in range(40):
        walk(game.initial_state())
    return strategy


# ---------------------------------------------------------------------------
# A known answer
# ---------------------------------------------------------------------------

def test_an_always_folding_opponent_is_maximally_exploitable(game):
    """
    If the opponent folds every time, the exploiter collects their blind every
    hand. That is arithmetic, so LBR must find close to it — and a bound that
    cannot exploit a player who never plays is broken.
    """
    always_fold = constant_strategy(game, FOLD)
    result = lbr_value(game, always_fold, hands=400,
                       rng=np.random.default_rng(0), rollout_samples=20)

    assert result.proves_exploitable, result.summary()
    # Seats alternate, so the win is the average of taking the big blind and
    # taking the small blind: (2 + 1) / 2 = 1.5 chips a hand.
    assert result.mean == pytest.approx(1.5, abs=0.6), result.summary()


def test_the_bound_is_never_wildly_beyond_the_stack(game, trained):
    """A hand cannot win more than the opponent brought to the table."""
    result = lbr_value(game, trained, hands=200,
                       rng=np.random.default_rng(1), rollout_samples=20)
    assert abs(result.mean) < game.starting_stack


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------

def test_training_reduces_exploitability(game, trained):
    """
    An untrained strategy plays uniformly at random and should be far more
    exploitable than a trained one. LBR that cannot separate these is measuring
    noise rather than exploitability.
    """
    untrained = lbr_value(game, {}, hands=500,
                          rng=np.random.default_rng(2), rollout_samples=25)
    learned = lbr_value(game, trained, hands=500,
                        rng=np.random.default_rng(2), rollout_samples=25)

    assert untrained.mean > learned.mean, \
        f"untrained {untrained.mean:.2f} vs trained {learned.mean:.2f}"
    assert untrained.proves_exploitable


def test_result_reports_its_own_uncertainty(game, trained):
    result = lbr_value(game, trained, hands=200,
                       rng=np.random.default_rng(3), rollout_samples=20)
    assert result.hands == 200
    assert result.stderr > 0.0
    low, high = result.ci95
    assert low < result.mean < high
    # The guarantee is one-directional and the summary must say so.
    assert "exploitab" in result.summary()


# ---------------------------------------------------------------------------
# Mechanism
# ---------------------------------------------------------------------------

def test_belief_rules_out_buckets_that_would_not_have_acted(game):
    """
    The whole leverage of LBR is that betting gives information away. If a
    bucket would never take the observed action, its weight must go to zero.
    """
    strategy = {}
    for bucket in range(4):
        # Only bucket 3 ever raises; everything else always calls.
        strategy[f"{bucket}|"] = (np.array([0.0, 1.0, 0.0, 0.0, 0.0, 0.0])
                                  if bucket < 3 else
                                  np.array([0.0, 0.0, 0.0, 1.0, 0.0, 0.0]))

    lbr = LocalBestResponse(game, strategy, rollout_samples=10)
    rng = np.random.default_rng(0)
    state = game.next_state(game.initial_state(),
                            game.sample_chance(game.initial_state(), rng))

    actions = list(game.legal_actions(state))
    raise_index = 3 if len(actions) > 3 else len(actions) - 1

    belief = np.full(4, 0.25)
    updated = lbr._update_belief(belief, state, 0, raise_index)

    assert updated[3] > 0.9, updated
    assert updated[:3].sum() < 0.1, updated


def test_belief_survives_an_impossible_observation(game):
    """
    If every bucket is ruled out — the strategy assigns the observed action zero
    probability everywhere — the belief must reset rather than become NaN.
    """
    strategy = {f"{b}|": np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0]) for b in range(4)}
    lbr = LocalBestResponse(game, strategy, rollout_samples=10)
    rng = np.random.default_rng(0)
    state = game.next_state(game.initial_state(),
                            game.sample_chance(game.initial_state(), rng))

    updated = lbr._update_belief(np.full(4, 0.25), state, 0, 1)
    assert np.isfinite(updated).all()
    assert updated.sum() == pytest.approx(1.0)


def test_fold_probability_reflects_the_range(game):
    """An opponent who always folds must read as folding with probability 1."""
    lbr = LocalBestResponse(game, constant_strategy(game, FOLD), rollout_samples=10)
    rng = np.random.default_rng(0)
    state = game.next_state(game.initial_state(),
                            game.sample_chance(game.initial_state(), rng))
    raised = game.next_state(state, 3)          # a pot-sized raise

    if FOLD in game.legal_actions(raised):
        probability = lbr._fold_probability(raised, 1, np.full(4, 0.25))
        assert probability == pytest.approx(1.0, abs=0.05)
