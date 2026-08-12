"""
Milestone 5: abstracted heads-up no-limit Hold'em.

The betting logic here is reimplemented rather than borrowed, because the
engine's version mutates in place and a traverser must be able to back up. That
makes these tests the only thing standing between a plausible-looking solver and
a game that quietly misallocates chips — which is precisely the failure this
project spent a session recovering from.

So the properties asserted are the accounting ones: chips are conserved, every
terminal is zero-sum, a fold pays exactly what the folder committed, and no line
runs forever. Card abstraction is checked to affect only the information-set
key, never the payoff.

    python -m pytest tests/test_nolimit.py -q
"""
import numpy as np
import pytest

from abstraction.betting import ALL_IN, CHECK_CALL, FOLD, RAISE_POT
from abstraction.buckets import CardAbstraction
from cfr import MCCFRSolver, VANILLA
from cfr.play import always_call_policy, play_hands, strategy_policy, uniform_policy
from games.base import CHANCE
from games.nolimit import NoLimitHoldem, STREET_NAMES

STARTING_STACK = 200
SMALL_BLIND, BIG_BLIND = 1, 2
TOTAL_CHIPS = 2 * STARTING_STACK


@pytest.fixture(scope="module")
def abstraction():
    """A deliberately tiny abstraction; these tests are about betting, not cards."""
    return CardAbstraction(preflop_buckets=3, postflop_buckets=3,
                           samples=60, equity_samples=25).fit(np.random.default_rng(0))


@pytest.fixture(scope="module")
def game(abstraction):
    return NoLimitHoldem(abstraction, starting_stack=STARTING_STACK,
                         small_blind=SMALL_BLIND, big_blind=BIG_BLIND,
                         raise_cap=1, equity_samples=25)


def play_random_hand(game, rng):
    """Drive one hand with random legal actions; returns the terminal state."""
    state = game.initial_state()
    for _ in range(200):
        if game.is_terminal(state):
            return state
        if game.is_chance(state):
            state = game.next_state(state, game.sample_chance(state, rng))
            continue
        actions = game.legal_actions(state)
        assert actions, f"no legal actions at {state.history!r}"
        state = game.next_state(state, actions[rng.integers(len(actions))])
    raise AssertionError(f"hand did not terminate: {state.history!r}")


# ---------------------------------------------------------------------------
# Accounting
# ---------------------------------------------------------------------------

def test_chips_are_conserved(game):
    """Stacks plus contributions must always equal the chips brought to the table."""
    rng = np.random.default_rng(0)
    for _ in range(300):
        state = play_random_hand(game, rng)
        assert sum(state.stacks) + sum(state.contributions) == TOTAL_CHIPS, state


def test_every_terminal_is_zero_sum(game):
    rng = np.random.default_rng(1)
    for _ in range(300):
        state = play_random_hand(game, rng)
        assert game.utility(state, 0) + game.utility(state, 1) == pytest.approx(0.0), state


def test_nobody_can_bet_more_than_their_stack(game):
    rng = np.random.default_rng(2)
    for _ in range(300):
        state = play_random_hand(game, rng)
        assert min(state.stacks) >= 0, state
        assert max(state.contributions) <= STARTING_STACK, state


def test_blinds_are_posted_before_the_deal(game):
    state = game.initial_state()
    assert state.contributions == (SMALL_BLIND, BIG_BLIND)
    assert state.stacks == (STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND)
    assert game.current_player(state) == CHANCE


def test_folding_preflop_forfeits_only_the_blind(game):
    """The small blind folding loses 1, not the whole stack."""
    rng = np.random.default_rng(3)
    state = game.next_state(game.initial_state(),
                            game.sample_chance(game.initial_state(), rng))
    assert game.current_player(state) == 0            # small blind acts first
    folded = game.next_state(state, FOLD)

    assert game.is_terminal(folded)
    assert game.utility(folded, 0) == -SMALL_BLIND
    assert game.utility(folded, 1) == SMALL_BLIND


def test_a_fold_pays_the_folder_s_contribution(game):
    """Whoever folds loses exactly what they put in, whatever their cards."""
    rng = np.random.default_rng(4)
    for _ in range(200):
        state = play_random_hand(game, rng)
        if str(FOLD) not in state.history:
            continue
        losses = [game.utility(state, p) for p in (0, 1)]
        loser = 0 if losses[0] < 0 else 1
        assert losses[loser] == -state.contributions[loser], state.history


# ---------------------------------------------------------------------------
# Turn order and betting rules
# ---------------------------------------------------------------------------

def test_small_blind_acts_first_preflop_then_big_blind(game):
    rng = np.random.default_rng(5)
    state = game.next_state(game.initial_state(),
                            game.sample_chance(game.initial_state(), rng))
    assert game.current_player(state) == 0
    # The small blind completing does not end the street: the big blind has an option.
    called = game.next_state(state, CHECK_CALL)
    assert game.current_player(called) == 1
    assert not game.is_terminal(called)


def test_big_blind_acts_first_after_the_flop(game):
    rng = np.random.default_rng(6)
    state = game.next_state(game.initial_state(),
                            game.sample_chance(game.initial_state(), rng))
    state = game.next_state(state, CHECK_CALL)      # small blind completes
    state = game.next_state(state, CHECK_CALL)      # big blind checks: street closes
    assert game.current_player(state) == CHANCE     # deal the flop
    state = game.next_state(state, game.sample_chance(state, rng))
    assert game.current_player(state) == 1, "big blind is first to act postflop"


def test_a_single_check_does_not_close_a_street(game):
    """Postflop, one check leaves the other player to act."""
    rng = np.random.default_rng(7)
    state = game.next_state(game.initial_state(),
                            game.sample_chance(game.initial_state(), rng))
    state = game.next_state(state, CHECK_CALL)
    state = game.next_state(state, CHECK_CALL)
    state = game.next_state(state, game.sample_chance(state, rng))   # flop

    checked = game.next_state(state, CHECK_CALL)
    assert game.current_player(checked) == 0, "street closed after a single check"


def test_raises_are_capped(game):
    rng = np.random.default_rng(8)
    state = game.next_state(game.initial_state(),
                            game.sample_chance(game.initial_state(), rng))
    raised = game.next_state(state, RAISE_POT)
    # With cap 1 the opponent may only fold or call.
    assert set(game.legal_actions(raised)) <= {FOLD, CHECK_CALL}


def test_a_player_who_cannot_cover_may_only_fold_or_call(game):
    rng = np.random.default_rng(9)
    state = game.next_state(game.initial_state(),
                            game.sample_chance(game.initial_state(), rng))
    shoved = game.next_state(state, ALL_IN)
    assert set(game.legal_actions(shoved)) <= {FOLD, CHECK_CALL}


def test_hands_reach_every_street(game):
    """If the river is never reached, the street machinery is broken."""
    rng = np.random.default_rng(10)
    reached = set()
    for _ in range(400):
        state = play_random_hand(game, rng)
        reached.add(min(state.street, len(STREET_NAMES) - 1))
    assert reached == {0, 1, 2, 3}, reached


# ---------------------------------------------------------------------------
# Abstraction affects only what the solver sees
# ---------------------------------------------------------------------------

def test_information_sets_hide_the_opponent(game):
    """The key must contain a bucket and the public history, nothing else."""
    rng = np.random.default_rng(11)
    state = game.next_state(game.initial_state(),
                            game.sample_chance(game.initial_state(), rng))
    key = game.information_set(state, 0)
    bucket, _, history = key.partition("|")
    assert bucket.isdigit()
    assert history == state.history


def test_chance_cannot_be_enumerated(game):
    """
    No-limit chance is far too large to list. Raising is the honest answer, and
    is what forces a sampling solver rather than vanilla CFR.
    """
    with pytest.raises(NotImplementedError):
        game.chance_outcomes(game.initial_state())


def test_payoffs_do_not_depend_on_the_abstraction(abstraction):
    """
    Cards are dealt and settled for real; only the solver's view is bucketed.
    Two games differing only in granularity must agree on every payoff.
    """
    coarse = NoLimitHoldem(abstraction, raise_cap=1, equity_samples=25)
    fine = NoLimitHoldem(
        CardAbstraction(preflop_buckets=8, postflop_buckets=8, samples=60,
                        equity_samples=25).fit(np.random.default_rng(1)),
        raise_cap=1, equity_samples=25)

    rng = np.random.default_rng(12)
    for _ in range(60):
        state = play_random_hand(coarse, rng)
        assert coarse.utility(state, 0) == fine.utility(state, 0), state.history


# ---------------------------------------------------------------------------
# The solver runs on it
# ---------------------------------------------------------------------------

def test_mccfr_trains_and_finds_information_sets(game):
    solver = MCCFRSolver(game, rule=VANILLA, seed=0)
    solver.train(120)
    assert len(solver.nodes) > 50

    for key, probabilities in solver.average_strategy().items():
        assert probabilities.sum() == pytest.approx(1.0), key
        assert (probabilities >= 0.0).all(), key


def test_head_to_head_reports_uncertainty(game):
    """A chip count without a standard error cannot be compared to anything."""
    result = play_hands(game, [uniform_policy(), always_call_policy()], 200,
                        np.random.default_rng(0))
    assert result.hands == 200
    assert result.stderr > 0.0
    low, high = result.ci95
    assert low < result.mean < high


def test_alternating_seats_cancels_position(game):
    """
    Two identical policies must break even. Without alternating seats the small
    blind's positional disadvantage would show up as a spurious edge.
    """
    result = play_hands(game, [uniform_policy(), uniform_policy()], 400,
                        np.random.default_rng(0), alternate_seats=True)
    assert abs(result.mean) < 4 * max(result.stderr, 1e-9)
