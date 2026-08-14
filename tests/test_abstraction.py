"""
Milestone 4: card abstraction and the size of the abstract game.

Abstraction is where a solver stops being exact, so the properties worth
asserting are the ones that keep it *honest*: equity must order hands the way
poker does, buckets must be monotone in strength, and the information-set count
must be arithmetic rather than a guess.

Equity is checked against hands whose values are well known — aces beat a random
hand about 85% of the time — because a subtly wrong equity produces buckets that
look plausible and rank hands wrongly, which no downstream test would catch.

    python -m pytest tests/test_abstraction.py -q
"""
import numpy as np
import pytest

from abstraction.betting import (ALL_IN, CHECK_CALL, FOLD, RAISE_POT, STREETS,
                                 count_decision_points, enumerate_street_sequences,
                                 legal_actions, measure)
from abstraction.buckets import (CardAbstraction, canonical_preflop_hands,
                                 preflop_key, _fit_kmeans_1d)
from abstraction.equity import FULL_DECK, equity_vs_random, remaining_deck
from engine.cards import Card


def C(text):
    return Card(text[0], text[1])


# ---------------------------------------------------------------------------
# Equity
# ---------------------------------------------------------------------------

def test_deck_is_complete_and_distinct():
    assert len(FULL_DECK) == 52
    assert len({(c.rank, c.suit) for c in FULL_DECK}) == 52


def test_remaining_deck_excludes_known_cards():
    known = [C("Ah"), C("Kd"), C("2c")]
    remaining = remaining_deck(known)
    assert remaining.size == 49
    excluded = {FULL_DECK[i] for i in remaining}
    assert all(card not in excluded for card in known)


@pytest.mark.parametrize("hand,low,high", [
    (["Ah", "Ad"], 0.80, 0.90),      # pocket aces: about 85% against a random hand
    (["Kh", "Kd"], 0.75, 0.87),
    (["Ah", "Kh"], 0.60, 0.72),      # suited big cards
    (["7h", "2d"], 0.28, 0.40),      # the worst starting hand
])
def test_preflop_equity_matches_known_values(hand, low, high):
    """
    A wrong equity produces buckets that look entirely reasonable and rank hands
    incorrectly, so it is pinned against values that are independently known.
    """
    cards = [C(text) for text in hand]
    measured = np.mean([
        equity_vs_random(cards, [], 600, np.random.default_rng(seed))
        for seed in range(3)
    ])
    assert low <= measured <= high, f"{hand}: {measured:.3f}"


def test_equity_responds_to_the_board():
    """The same hole cards must be worth different amounts on different boards."""
    hole = [C("9h"), C("9c")]
    rng = lambda: np.random.default_rng(0)
    flopped_set = equity_vs_random(hole, [C("2c"), C("7s"), C("9d")], 600, rng())
    overcards = equity_vs_random(hole, [C("Ac"), C("Ks"), C("Qd")], 600, rng())
    assert flopped_set > overcards + 0.2


def test_equity_is_bounded():
    for hole, board in [(["Ah", "Ad"], []), (["7h", "2d"], ["Ac", "Kc", "Qc"])]:
        value = equity_vs_random([C(t) for t in hole], [C(t) for t in board],
                                 200, np.random.default_rng(0))
        assert 0.0 <= value <= 1.0


def test_equity_is_reproducible_given_a_seed():
    args = ([C("Ah"), C("Kh")], [C("2c"), C("7s"), C("9d")], 200)
    first = equity_vs_random(*args, np.random.default_rng(7))
    second = equity_vs_random(*args, np.random.default_rng(7))
    assert first == second


# ---------------------------------------------------------------------------
# Buckets
# ---------------------------------------------------------------------------

def test_there_are_169_distinct_starting_hands():
    hands = canonical_preflop_hands()
    assert len(hands) == 169
    assert len(set(hands)) == 169
    # 13 pairs, 78 suited, 78 offsuit
    assert sum(1 for _, _, suited in hands if suited) == 78


def test_preflop_key_is_order_and_suit_canonical():
    assert preflop_key([C("Kh"), C("Ah")]) == preflop_key([C("Ah"), C("Kh")])
    assert preflop_key([C("Ah"), C("Kh")]) != preflop_key([C("Ah"), C("Kd")])
    assert preflop_key([C("Ah"), C("Kd")]) == preflop_key([C("As"), C("Kc")])


def test_kmeans_returns_sorted_centroids():
    values = np.array([0.1, 0.12, 0.5, 0.52, 0.9, 0.95])
    centroids = _fit_kmeans_1d(values, 3)
    assert centroids.size == 3
    assert (np.diff(centroids) > 0).all(), "buckets must be ordered by strength"


def test_kmeans_handles_more_buckets_than_values():
    centroids = _fit_kmeans_1d(np.array([0.2, 0.8]), 10)
    assert centroids.size <= 2


@pytest.fixture(scope="module")
def fitted():
    """A small abstraction; sampling is kept low so the suite stays quick."""
    return CardAbstraction(preflop_buckets=5, postflop_buckets=5,
                           samples=150, equity_samples=60).fit(np.random.default_rng(0))


def test_a_pickle_predating_the_lookup_table_still_buckets(fitted):
    """
    An abstraction is pickled so a result outlives the code that produced it,
    which makes every derived field a compatibility hazard. `_centroid_list` was
    added after `results/cfr/nolimit_strategy.pkl` was written, and that file now
    unpickles with it set to None — so every postflop lookup raises rather than
    answering. Restoring must rebuild it, and rebuild it to the *same* clustering
    rather than refitting to a plausible different one.
    """
    aged = fitted.__dict__.copy()
    aged.pop("_centroid_list", None)          # as an older pickle carries it

    revived = CardAbstraction.__new__(CardAbstraction)
    revived.__setstate__(aged)

    hole, board = [C("Ah"), C("Kh")], [C("Qh"), C("7d"), C("2s")]
    assert revived.bucket(hole, board, np.random.default_rng(0)) == \
        fitted.bucket(hole, board, np.random.default_rng(0))


def test_pickling_an_abstraction_round_trips(fitted):
    """The ordinary path must keep working, not just the aged one."""
    import pickle

    revived = pickle.loads(pickle.dumps(fitted))
    hole, board = [C("Ah"), C("Kh")], [C("Qh"), C("7d"), C("2s")]
    assert revived.bucket(hole, board, np.random.default_rng(0)) == \
        fitted.bucket(hole, board, np.random.default_rng(0))
    assert revived.describe() == fitted.describe()


def test_preflop_buckets_order_hands_by_strength(fitted):
    """Aces must not land in a weaker bucket than seven-deuce."""
    aces = fitted.bucket([C("Ah"), C("Ad")], [])
    kings = fitted.bucket([C("Kh"), C("Kd")], [])
    junk = fitted.bucket([C("7h"), C("2d")], [])
    assert aces >= kings > junk


def test_every_starting_hand_gets_a_bucket(fitted):
    for high, low, suited in canonical_preflop_hands():
        hand = [Card(high, "h"), Card(low, "h" if suited else "d")]
        bucket = fitted.bucket(hand, [])
        assert 0 <= bucket < fitted.preflop_buckets


def test_postflop_buckets_order_by_strength(fitted):
    board = [C("2c"), C("7s"), C("9d")]
    rng = lambda: np.random.default_rng(1)
    strong = fitted.bucket([C("9h"), C("9c")], board, rng())   # a set
    weak = fitted.bucket([C("3h"), C("4d")], board, rng())     # nothing
    assert strong > weak


def test_fitting_is_deterministic_given_a_seed():
    """An abstraction is a fixed artifact; it must not vary between builds."""
    def build():
        return CardAbstraction(preflop_buckets=4, postflop_buckets=4,
                               samples=80, equity_samples=40).fit(
                                   np.random.default_rng(3))

    first, second = build(), build()
    for street in ("flop", "turn", "river"):
        assert first._centroids[street].tolist() == second._centroids[street].tolist()


def test_bucket_before_fit_is_an_error():
    with pytest.raises(RuntimeError):
        CardAbstraction().bucket([C("Ah"), C("Ad")], [])


# ---------------------------------------------------------------------------
# The betting tree
# ---------------------------------------------------------------------------

def test_folding_is_not_offered_with_nothing_to_call():
    assert FOLD not in legal_actions(raises_so_far=0, facing_bet=False, raise_cap=2)
    assert FOLD in legal_actions(raises_so_far=1, facing_bet=True, raise_cap=2)


def test_raises_stop_at_the_cap():
    assert RAISE_POT in legal_actions(1, True, raise_cap=2)
    assert set(legal_actions(2, True, raise_cap=2)) == {FOLD, CHECK_CALL}


def test_an_all_in_cannot_be_raised():
    """
    There are no chips left to raise with. Treating all-in as an ordinary raise
    inflates the tree with lines that cannot occur — it cut the sequence count
    by a fifth at cap 2.
    """
    assert set(legal_actions(1, True, raise_cap=3, last_action=ALL_IN)) == {FOLD, CHECK_CALL}


def test_every_street_sequence_ends_properly():
    """A street must close on a call, a check-through, or a fold."""
    for sequence, folded in enumerate_street_sequences(2):
        assert sequence, "empty sequence"
        if folded:
            assert sequence[-1] == FOLD
        else:
            assert sequence[-1] == CHECK_CALL
            assert FOLD not in sequence


def test_deeper_caps_give_strictly_larger_trees():
    sizes = [len(enumerate_street_sequences(cap)) for cap in (1, 2, 3)]
    assert sizes[0] < sizes[1] < sizes[2]


def test_decision_points_are_shared_between_players():
    counts = count_decision_points(2)
    assert counts[0] > 0 and counts[1] > 0


# ---------------------------------------------------------------------------
# Sizing arithmetic
# ---------------------------------------------------------------------------

def test_information_sets_scale_linearly_in_buckets():
    small = measure({s: 4 for s in STREETS}, raise_cap=1)
    large = measure({s: 8 for s in STREETS}, raise_cap=1)
    assert large.information_sets == 2 * small.information_sets


def test_information_sets_explode_with_the_raise_cap():
    """
    Betting lines multiply across all four streets, so the cap compounds while
    buckets only scale. This is why the bet abstraction, not the card
    abstraction, decides whether the game fits in memory.
    """
    shallow = measure({s: 8 for s in STREETS}, raise_cap=1)
    deep = measure({s: 8 for s in STREETS}, raise_cap=2)
    assert deep.information_sets > 100 * shallow.information_sets


def test_memory_accounts_for_regret_and_strategy():
    size = measure({s: 8 for s in STREETS}, raise_cap=1, num_actions=6,
                   bytes_per_entry=8)
    assert size.table_bytes == size.information_sets * 6 * 2 * 8


def test_reaching_sequences_compound_by_street():
    size = measure({s: 4 for s in STREETS}, raise_cap=1)
    reaching = size.reaching_sequences
    assert reaching["preflop"] == 1
    assert reaching["flop"] < reaching["turn"] < reaching["river"]


# ---------------------------------------------------------------------------
# The pluggable postflop strength signal
# ---------------------------------------------------------------------------

def test_both_strength_signals_produce_ordered_buckets():
    """
    Whichever signal a bucketing is fitted on, a set must land above nothing.
    made_hand cannot see draws, but it must still rank made hands correctly.
    """
    from abstraction.buckets import STRENGTH_SIGNALS

    board = [C("2c"), C("7s"), C("9d")]
    for signal in STRENGTH_SIGNALS:
        fitted = CardAbstraction(preflop_buckets=4, postflop_buckets=4, samples=120,
                                 equity_samples=30, strength=signal).fit(
                                     np.random.default_rng(0))
        strong = fitted.bucket([C("9h"), C("9c")], board, np.random.default_rng(1))
        weak = fitted.bucket([C("3h"), C("4d")], board, np.random.default_rng(1))
        assert strong > weak, signal


def test_fit_and_lookup_share_one_signal():
    """
    A clustering fitted on one signal and queried with another would assign
    every situation to whichever bucket happened to sit near the wrong scale —
    plausible output, meaningless buckets. Both routes go through one method.
    """
    fitted = CardAbstraction(preflop_buckets=4, postflop_buckets=4, samples=80,
                             equity_samples=25, strength="made_hand").fit(
                                 np.random.default_rng(0))
    hole, board = [C("Ah"), C("Kh")], [C("2c"), C("7s"), C("9d")]
    direct = fitted._postflop_strength(hole, board, np.random.default_rng(0))
    from engine.features import made_hand_strength
    assert direct == made_hand_strength(hole, board)


def test_unknown_strength_signal_is_rejected():
    with pytest.raises(ValueError):
        CardAbstraction(strength="vibes")


def test_nearest_centroid_matches_exhaustive_search():
    """The binary search must agree with the argmin it replaced."""
    from abstraction.buckets import _nearest_centroid

    rng = np.random.default_rng(0)
    for _ in range(500):
        centroids = np.sort(rng.random(rng.integers(2, 10)))
        value = float(rng.random())
        expected = int(np.abs(centroids - value).argmin())
        assert _nearest_centroid(centroids.tolist(), value) == expected
