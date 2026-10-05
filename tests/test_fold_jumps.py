"""Leg (d) of the stopping rule: scripts/fold_jumps.py on small hand-built strategies."""
import os
import pickle
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.fold_jumps import (RANKS, actions_at, all_in_histories, check, combo_weights,  # noqa: E402
                                line_probability, neighbour_pairs, own_reach, parse_label, report, verdict)

CAP = 2                    # two raises: the small blind's raise can be re-raised all-in
LABELS = ["AA", "KK", "QQ", "AKs", "AQs", "KQs", "AKo", "AQo"]
AA, KK, QQ, AKS, AQS, KQS, AKO, AQO = range(len(LABELS))


def all_labels():
    out = []
    for high in range(12, -1, -1):
        for low in range(high, -1, -1):
            if high == low:
                out.append(RANKS[high] * 2)
            else:
                out += [f"{RANKS[high]}{RANKS[low]}s", f"{RANKS[high]}{RANKS[low]}o"]
    return out


def one_hot(actions, action, p=1.0):
    row = np.zeros(len(actions))
    row[actions.index(action)] = p
    if p < 1.0:                                     # the rest on the first other action
        row[[i for i in range(len(actions)) if actions[i] != action][0]] = 1.0 - p
    return row


def line(fold_at_shove, shove_share=0.5, root_raise=None):
    """
    Every class opens a half-pot raise ('2'), the big blind re-raises all-in
    ('25') with `shove_share` of every class, and the small blind folds there
    with `fold_at_shove[class]`.
    """
    strategy = {}
    root, after_raise, facing = actions_at("", CAP), actions_at("2", CAP), actions_at("25", CAP)
    for klass in range(len(LABELS)):
        strategy[f"{klass}|"] = one_hot(root, 2, (root_raise or {}).get(klass, 1.0))
        strategy[f"{klass}|2"] = one_hot(after_raise, 5, shove_share) if shove_share > 0 else one_hot(after_raise, 1)
        fold = fold_at_shove[klass]
        strategy[f"{klass}|25"] = np.array([fold, 1.0 - fold])
    assert facing == (0, 1)
    return strategy


MONOTONE = {AA: 0.0, KK: 0.0, QQ: 0.1, AKS: 0.0, AQS: 0.2, KQS: 0.6, AKO: 0.1, AQO: 0.7}


def test_labels_parse_both_ways():
    assert parse_label("AKs") == (12, 11, True)
    assert parse_label("72o") == (5, 0, False)
    assert parse_label("TT") == (8, 8, None)


def test_neighbours_on_the_full_grid():
    labels = all_labels()
    pairs = neighbour_pairs(labels)
    # 12 pair steps, then for each suitedness 66 steps of the high card and 66 of the low one.
    assert len(pairs) == 12 + 2 * (66 + 66)
    assert len(set(pairs)) == len(pairs)
    for strong, weak in pairs:
        s, w = parse_label(labels[strong]), parse_label(labels[weak])
        assert s[2] == w[2]                                       # same suitedness, pairs with pairs
        assert s[0] >= w[0] and s[1] >= w[1]                      # card for card at least as high
        assert (s[0] - w[0]) + (s[1] - w[1]) == (2 if s[2] is None else 1)
    names = {(labels[a], labels[b]) for a, b in pairs}
    assert ("AKs", "AQs") in names and ("AQs", "KQs") in names and ("KK", "QQ") in names
    assert ("AKs", "KQs") not in names                            # two steps, not a neighbour
    assert not any(b == "KK" and a.endswith("s") for a, b in names)   # KQs one up is not KK


def test_neighbours_of_a_partial_list():
    pairs = {(LABELS[a], LABELS[b]) for a, b in neighbour_pairs(LABELS)}
    assert pairs == {("AA", "KK"), ("KK", "QQ"), ("AKs", "AQs"), ("AQs", "KQs"), ("AKo", "AQo")}


def test_combo_weights():
    w = combo_weights(LABELS)
    assert w.sum() == pytest.approx(1.0)
    assert w[AA] / w[AKS] == pytest.approx(6 / 4) and w[AKO] / w[AKS] == pytest.approx(3)


def test_all_in_histories_are_preflop_and_facing_a_shove():
    strategy = {"0|": [1], "0|5": [1, 0], "0|25": [1, 0], "0|2": [1], "0|25/1": [1], "0|1/5": [1, 0]}
    assert all_in_histories(strategy) == ["5", "25"]


def test_own_reach_counts_only_the_players_own_actions():
    strategy = line(MONOTONE, shove_share=0.3, root_raise={AKS: 0.4})
    # The small blind at '25' acted once ('2' at the root); the big blind's 0.3 is not its reach.
    assert own_reach(strategy, CAP, AKS, "25") == pytest.approx(0.4)
    assert own_reach(strategy, CAP, AA, "25") == pytest.approx(1.0)
    # The big blind's own reach to '25' is its shove share.
    assert own_reach(strategy, CAP, AA, "25", player=1) == pytest.approx(0.3)
    assert own_reach(strategy, CAP, 99, "25") == 0.0                    # no entry for the class


def test_line_probability_is_the_opponents_range_weighted_reach():
    strategy = line(MONOTONE, shove_share=0.3)
    assert line_probability(strategy, CAP, "25", combo_weights(LABELS)) == pytest.approx(0.3)


def test_monotone_folds_flag_nothing():
    result = check(line(MONOTONE), CAP, LABELS)
    assert result["nodes"] == 1 and result["pairs_compared"] == 5
    assert result["flagged"] == [] and result["excess"] == 0.0 and result["weighted_excess"] == 0.0


def test_a_stronger_hand_folding_more_is_flagged_and_weighted():
    folds = {**MONOTONE, AKS: 0.9, AQS: 0.1}
    result = check(line(folds, shove_share=0.5), CAP, LABELS)
    assert [(r["stronger"], r["weaker"]) for r in result["flagged"]] == [("AKs", "AQs")]
    row = result["flagged"][0]
    assert row["excess"] == pytest.approx(0.8)
    assert row["line"] == pytest.approx(0.5) and row["reach_stronger"] == pytest.approx(1.0)
    assert result["weighted_excess"] == pytest.approx(0.8 * 0.5)


def test_threshold_is_inclusive_and_small_gaps_pass():
    folds = {**MONOTONE, AKS: 0.35, AQS: 0.2}          # a 0.15 gap, under the 0.2 default
    assert check(line(folds), CAP, LABELS)["flagged"] == []
    folds = {**MONOTONE, AKS: 0.45, AQS: 0.2}
    assert len(check(line(folds), CAP, LABELS, threshold=0.25)["flagged"]) == 1


def test_a_class_that_does_not_reach_the_node_is_not_compared():
    folds = {**MONOTONE, AKS: 0.9, AQS: 0.1}
    result = check(line(folds, root_raise={AKS: 0.01}), CAP, LABELS)
    assert result["flagged"] == [] and result["pairs_compared"] == 4


def test_an_untouched_uniform_entry_is_counted_not_compared():
    strategy = line(MONOTONE)
    strategy[f"{AKS}|25"] = np.array([0.5, 0.5])
    result = check(strategy, CAP, LABELS)
    assert result["uniform_entries"] == 1 and result["pairs_compared"] == 4


def test_a_line_the_opponent_never_takes_carries_no_weight():
    folds = {**MONOTONE, AKS: 0.9, AQS: 0.1}
    strategy = line(folds, shove_share=0.0)
    # Nobody shoves at '2', so '25' is never trained: still listed, weighted to nothing.
    for klass in range(len(LABELS)):
        strategy[f"{klass}|25"] = np.array([folds[klass], 1.0 - folds[klass]])
    result = check(strategy, CAP, LABELS)
    assert len(result["flagged"]) == 1 and result["weighted_excess"] == 0.0


def test_verdict():
    good, bad = {**MONOTONE, AKS: 0.5, AQS: 0.2}, {**MONOTONE, AKS: 0.9, AQS: 0.1}
    at_good, at_bad = check(line(good), CAP, LABELS), check(line(bad), CAP, LABELS)
    assert verdict(at_bad, at_good) == "pass"                 # 2T better
    assert verdict(at_good, at_good) == "pass"                # level is not worse
    assert verdict(at_good, at_bad) == "FAIL"                 # 2T worse
    assert verdict(at_good, check({}, CAP, LABELS)) == "not measured"


class _Abstraction:
    def __init__(self, labels):
        self._preflop = {}
        for index, label in enumerate(labels):
            high, low = label[0], label[1]
            self._preflop[(high, low, label.endswith("s"))] = index


def test_report_reads_a_saved_solve(tmp_path):
    path = tmp_path / "rung.pkl"
    folds = {**MONOTONE, AKS: 0.9, AQS: 0.1}
    with open(path, "wb") as handle:
        pickle.dump({"strategy": line(folds), "args": {"raise_cap": CAP, "stack": 140, "big_blind": 2},
                     "abstraction": _Abstraction(LABELS)}, handle)
    result = report(str(path), 0.2, 0.05)
    assert result["depth_bb"] == 70
    assert [(r["stronger"], r["weaker"]) for r in result["flagged"]] == [("AKs", "AQs")]
