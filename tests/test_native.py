"""
The C++ core against the Python it replaces.

A port that quietly disagrees is worse than no port: it would not fail, it would
shift every equity estimate, every bucket and every strategy trained afterwards.
So the deterministic half is pinned hand-for-hand and the sampled half is
checked for bias.

Skipped when the module is not built, because `native/build.sh` needs cmake,
ninja and nanobind, and the rest of the suite must not depend on them.
"""
import random

import numpy as np
import pytest

from abstraction.equity import FULL_DECK, equity_vs_random
from engine.hand_eval_fast import score_hand_7_fast

native = pytest.importorskip("pokerbot_native",
                             reason="run native/build.sh to build the C++ core")


def test_the_cpp_evaluator_is_identical_on_every_hand_class():
    """
    Exact, not approximate. Restricted decks are included because random
    seven-card hands almost never make quads or straight flushes, and those are
    the branches most likely to be wrong.
    """
    decks = [
        list(range(52)),
        [s * 13 + r for s in range(4) for r in range(6)],     # forces quads, boats
        [s * 13 + r for s in range(2) for r in range(13)],    # forces flushes
    ]
    rng = random.Random(2026)
    classes = set()
    for deck in decks:
        for _ in range(2000):
            cards = rng.sample(deck, 7)
            ranks = np.array([c % 13 for c in cards], dtype=np.int32)
            suits = np.array([c // 13 for c in cards], dtype=np.int32)
            expected = int(score_hand_7_fast(ranks, suits))
            assert native.score_hand_7([c % 13 for c in cards],
                                       [c // 13 for c in cards]) == expected, (
                f"C++ evaluator differs on {cards}")
            classes.add(expected >> 20)
    assert len(classes) >= 8, f"only saw hand classes {sorted(classes)}"


def test_the_cpp_rollout_is_unbiased_against_the_python_one():
    """
    Not identical: the two draw from different generators on purpose. What must
    hold is that neither systematically favours a hand, which a mean difference
    indistinguishable from zero is what shows.
    """
    rng = random.Random(99)
    differences = []
    for _ in range(400):
        board_size = rng.choice([3, 4, 5])
        cards = rng.sample(range(52), 2 + board_size)
        hole, board = cards[:2], cards[2:]
        mine = equity_vs_random([FULL_DECK[c] for c in hole],
                                [FULL_DECK[c] for c in board], 2000,
                                np.random.default_rng(rng.randrange(10 ** 6)))
        theirs = native.equity_vs_random(hole, board, 2000, rng.randrange(10 ** 9))
        differences.append(mine - theirs)

    values = np.array(differences)
    interval = 1.96 * values.std(ddof=1) / np.sqrt(values.size)
    assert abs(values.mean()) < interval, (
        f"C++ rollout is biased by {values.mean():+.5f} +/- {interval:.5f}")


def test_the_cpp_betting_game_agrees_over_the_enumerated_tree():
    """
    The same check `test_betting_equivalence.py` makes, against a third
    implementation.

    Betting is written twice in this project and has diverged twice: a
    pot-fraction raise once sized off the pot before the call instead of after,
    making every engine raise about 20% too small, and the traversal game once
    failed to end a hand at an all-in, keying 19.7% of decision nodes
    differently. Neither failed; both returned plausible wrong numbers. A C++
    port makes it three implementations, so it gets the same treatment.

    Compared at every node: pot, both stacks, the history string (which is the
    information-set key's public half), and the legal-action list itself. All
    four raise schedules are covered, including the tapered ones, since a taper
    is exactly the kind of change that splits two implementations apart.
    """
    import itertools

    from abstraction.buckets import CardAbstraction
    from games.nolimit import NoLimitHoldem

    stack, small_blind, big_blind = 200, 1, 2
    abstraction = CardAbstraction(preflop_buckets=2, postflop_buckets=2,
                                  samples=20, equity_samples=4)
    abstraction.fit(np.random.default_rng(0))

    def python_replay(actions, schedule):
        game = NoLimitHoldem(abstraction, starting_stack=stack,
                             small_blind=small_blind, big_blind=big_blind,
                             raise_cap=schedule, equity_samples=4)
        state = game.initial_state()._replace(hole=((0, 1), (2, 3)))
        legal_each = []
        for action in actions:
            if game.is_terminal(state):
                return -1, None, None, legal_each
            if game.current_player(state) < 0:
                return -2, None, None, legal_each
            legal = list(game.legal_actions(state))
            legal_each.append(legal)
            if action not in legal:
                return -3, None, None, legal_each
            state = game.next_state(state, action)
        return sum(state.contributions), list(state.stacks), state.history, legal_each

    schedules = [(1, [4]), (2, [4, 4]), ((4, 1), [4, 1]), ((4, 2), [4, 2])]
    compared = 0
    for python_schedule, cpp_schedule in schedules:
        for depth in (1, 2, 3):
            for actions in itertools.product(range(6), repeat=depth):
                expected = python_replay(list(actions), python_schedule)
                got = native.replay(list(actions), stack, small_blind, big_blind,
                                    cpp_schedule)
                compared += 1
                assert expected[0] == got[0], (
                    f"schedule={python_schedule} actions={actions}: "
                    f"pot {expected[0]} vs {got[0]}")
                if expected[0] >= 0:
                    assert expected[1] == list(got[1]), (
                        f"schedule={python_schedule} actions={actions}: stacks differ")
                    assert expected[2] == got[2], (
                        f"schedule={python_schedule} actions={actions}: history differs")
                assert expected[3] == [list(step) for step in got[3]], (
                    f"schedule={python_schedule} actions={actions}: legal actions differ")
    assert compared > 1000, f"only compared {compared} sequences"


def test_the_cpp_solver_converges_to_kuhns_analytic_value():
    """
    Kuhn poker's value to the first player is exactly -1/18 under optimal play.

    This is the acceptance test for the ported MCCFR, and it is stronger than
    comparing against our own Python: that would show the translation was
    faithful, while this shows regret matching, external sampling and strategy
    averaging are each correct. It is the same anchor `tests/test_mccfr.py`
    uses for the Python solver.
    """
    import itertools

    def game_value(strategy):
        def probability(key, action):
            entry = strategy.get(key)
            return entry[action] if entry else 0.5

        total = 0.0
        for mine, theirs in itertools.permutations(range(3), 2):
            showdown = 1.0 if mine > theirs else -1.0
            value = probability(f"{mine}|", 0) * (
                probability(f"{theirs}|p", 0) * showdown
                + probability(f"{theirs}|p", 1) * (
                    probability(f"{mine}|pb", 0) * -1.0
                    + probability(f"{mine}|pb", 1) * 2.0 * showdown))
            value += probability(f"{mine}|", 1) * (
                probability(f"{theirs}|b", 0) * 1.0
                + probability(f"{theirs}|b", 1) * 2.0 * showdown)
            total += value / 6.0
        return total

    values = [game_value(native.solve_kuhn(200_000, seed)) for seed in range(3)]
    mean = sum(values) / len(values)
    assert abs(mean - (-1 / 18)) < 0.002, (
        f"converged to {mean:+.5f}, expected {-1/18:+.5f}; seeds {values}")


def test_the_cpp_no_limit_solver_produces_a_usable_strategy():
    """
    The solver runs end to end and returns something the Python can play.

    Deliberately small: the acceptance test that matters is the one run by hand
    on 11 September, where C++ and Python solvers at 40,000 iterations were
    scored by the same harness and agreed to 16 and 23 BB/100 against random and
    always-call, well inside the measurement interval. That takes six minutes
    because of the Python arm, so it does not belong in the suite. This checks
    the wiring: keys are well formed, distributions are distributions.
    """
    from abstraction.buckets import CardAbstraction, preflop_key
    from abstraction.equity import FULL_DECK

    abstraction = CardAbstraction(preflop_buckets=4, postflop_buckets=4,
                                  samples=60, equity_samples=8)
    abstraction.fit(np.random.default_rng(0))

    preflop = [0] * (52 * 52)
    for first in range(52):
        for second in range(52):
            if first != second:
                preflop[first * 52 + second] = abstraction._preflop[
                    preflop_key([FULL_DECK[first], FULL_DECK[second]])]

    solver = native.NoLimitSolver(
        preflop,
        list(abstraction._centroid_list["flop"]),
        list(abstraction._centroid_list["turn"]),
        list(abstraction._centroid_list["river"]),
        8, 200, 1, 2, [4], 0)
    solver.train(300)

    strategy = solver.average_strategy()
    assert strategy, "solver produced no information sets"
    assert solver.iterations() == 300

    for key, probabilities in strategy.items():
        assert "|" in key, f"malformed information-set key {key!r}"
        bucket, history = key.split("|", 1)
        assert bucket.isdigit(), f"bucket is not a number in {key!r}"
        assert set(history) <= set("012345/"), f"unexpected history in {key!r}"
        assert 2 <= len(probabilities) <= 6, f"{key!r} has {len(probabilities)} actions"
        assert abs(sum(probabilities) - 1.0) < 1e-9, f"{key!r} is not a distribution"
        assert all(p >= 0.0 for p in probabilities), f"{key!r} has a negative probability"


def test_board_texture_agrees_between_python_and_the_native_core():
    """Every class of board the C++ solver could bucket, read the same way."""
    import numpy as np
    from abstraction.buckets import board_texture
    from abstraction.equity import FULL_DECK
    import pokerbot_native
    rng = np.random.default_rng(13)
    for _ in range(3000):
        n = int(rng.choice([3, 4, 5]))
        picked = [int(i) for i in rng.choice(52, size=n, replace=False)]
        cards = [FULL_DECK[i] for i in picked]
        assert board_texture(cards) == pokerbot_native.board_texture([c.index for c in cards])
