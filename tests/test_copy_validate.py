"""
The copy validator on synthetic bots, where the truth is known.

If the bot really is an archetype, a copy fitted to its earlier matches must predict its later ones to within
sampling error; if the later matches come from a different archetype, the same copy must miss by many
standard errors. Both are needed: the first says the scoring is unbiased, the second that it has power. The
replay's counts are also held to `chipzen_scout.profile`, since the fit's targets come from that code.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import chipzen.archetypes as arch  # noqa: E402
import scripts.copy_validate as cv  # noqa: E402

TRUTH = dict(arch.PARAMS["foldraise"], call_p=0.4, fold_margin=0.12)


@pytest.fixture(scope="module")
def own():
    return cv.simulate(TRUTH, "station", 40, seed=5, base="foldraise")


@pytest.fixture(scope="module")
def validated(own):
    return cv.validate("synthetic", own, draws=4, rounds=60)


def test_replay_counts_are_the_scouts(own):
    from scripts.chipzen_scout import profile
    matches = own[:6]
    row = profile("x", [{"id": m["id"], "vs": m["vs"], "seat": m["seat"]} for m in matches],
                  {m["id"]: m["hands"] for m in matches})
    real = {k: float(v.sum()) for k, v in cv.Replay(matches, draws=1).real.items()}
    pairs = {"hands": "hands", "vpip": "entered", "pfr": "raised", "three_bet": "tb", "three_bet_chances": "tb_n",
             "bets_faced": "bf_n", "folds": "bf_fold", "calls": "bf_call", "raises": "bf_raise",
             "showdowns": "sd", "river_bets": "rv_bet_p", "river_bluffs": "rv_bluff",
             "three_bets_faced": "tbf_n", "fold_to_three_bet": "tbf_fold"}
    for theirs, ours in pairs.items():
        assert real.get(ours, 0) == row[theirs], theirs
    assert real["bbo_n"] == sum(row["by_history"].get("preflop:Ur", {}).values())


def test_true_parameters_are_unbiased(own):
    # The copy's chances at the bot's own decisions are the compensator of its counts, so with the
    # generating row every statistic sits within sampling error, path statistics and sizes included.
    replay = cv.Replay(own[20:], draws=4, seed=1)
    rows = cv.compare(replay.real, replay.predicted(TRUTH))
    zs = [r["z"] for r in rows.values() if r["z"] is not None]
    assert len(zs) >= 12
    assert max(abs(z) for z in zs) < 3.5
    assert cv.rms(rows, [s[0] for s in cv.STATS])[0] < 1.6


def test_fitted_copy_predicts_its_own_bot(validated):
    assert validated["held_matches"] == 20
    assert validated["copy_fit_rms"] < 2.0
    assert validated["stability_fit_rms"] < 2.0
    assert validated["verdict"].startswith("copy holds")


def test_mismatched_bot_is_caught(validated):
    for kind in ("station", "maniac"):
        other = cv.simulate(dict(arch.PARAMS[kind]), "station", 20, seed=9, base=kind)
        replay = cv.Replay(other, draws=4, seed=1)
        score, n = cv.rms(cv.compare(replay.real, replay.predicted(validated["params"])), cv.FITTED)
        assert n >= 6
        assert score > 4, kind


def test_a_bot_that_changes_is_unstable(own):
    # Halfway through the held-out span the bot becomes a station: the halves must disagree.
    changed = own[20:30] + cv.simulate(dict(arch.PARAMS["station"]), "station", 10, seed=13, base="station")
    rows = cv.stability(cv.Replay(changed, draws=2, seed=2))
    assert cv.rms(rows, cv.FITTED)[0] > 3


def test_too_few_matches_is_reported(own):
    row = cv.validate("thin", own[:5], draws=1, rounds=1)
    assert row["verdict"] == "too few matches"
