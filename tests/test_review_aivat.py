"""
Independent review of the AIVAT branch: the gaps tests/test_aivat.py leaves.

The existing tests check the identities one at a time (equity is a martingale on two spots, a decision term has zero
mean on one spot). These check the estimator as a whole through trace_hand and hand_terms: on a toy game where the
true value is known exactly, on every turn and river through one line, against the true card distribution with the
opponent's cards removed, and on the bookkeeping the write-up relies on (which streets get terms, the fit's
exclusions, the frozen digest, the window, the dagger, old logs). A test marked xfail(strict=True) is a real defect
found in review and left unfixed on purpose.
"""
import datetime
import glob
import itertools
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation.aivat import (STREETS, VALUE_FILE, ValueFunction, card_index, hand_class,  # noqa: E402
                              hand_terms, trace_hand)
from scripts.chipzen_decompose import _ist, aivat_hands, allin_nets, hand_nets  # noqa: E402
from tests.test_allin_adjust import act, allin_hand, decisions_of  # noqa: E402

DECK = [r + s for s in "hdcs" for r in "23456789TJQKA"]
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


@pytest.fixture(scope="module")
def frozen():
    return ValueFunction.load(VALUE_FILE)


def row(hand, phase, board, choice, pot, to_call, probs=None, legal=(1, 1, 1, 1, 1, 1)):
    d = {"frame": "decision", "hand": hand, "phase": phase, "board": list(board), "pot": pot, "to_call": to_call,
         "history": "", "choice": choice, "legal": list(legal), "solver": "100bb", "companion": None,
         "fallback": False, "adjusted": None}
    if probs is not None:
        d["probs"] = list(probs)
    return d


# ---------------------------------------------------------------------------------------------------------------
# A toy game with a known value: we are the button, we fold, pot-raise or jam, and the opponent folds to any raise.
# Our mix depends on our cards, so the deal and decision terms are both live, and the true EV is an exact sum.
# ---------------------------------------------------------------------------------------------------------------

def _toy_sigma(eq):
    p = np.zeros(6)
    p[0], p[3], p[5] = 1.0 - eq, 0.5 * eq, 0.5 * eq
    return p


def _toy_hand(hole, choice, sigma):
    before = [10000, 10000]
    history = [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop")]
    if choice == 0:
        history.append(act(0, "fold", 0, "preflop"))
        after = [9950, 10050]
    else:
        history += [act(0, "raise" if choice == 3 else "all_in", 300 if choice == 3 else 10000, "preflop"),
                    act(1, "fold", 0, "preflop")]
        after = [10100, 9900]
    result = {"hand_number": 1, "action_history": history, "stacks": after, "showdown": []}
    d = row(1, "preflop", [], choice, 150, 50, sigma)
    return result, before, [d], after[0] - before[0]


def test_toy_game_aivat_mean_equals_the_true_ev_exactly(frozen):
    """
    Every holding and every choice, weighted by its true probability: E[AIVAT] must equal the true EV, less only
    the deal term's known offset g * (table mean - 1/2), which is the preflop table's own sampling error.
    """
    true_ev, aivat_mean, n = 0.0, 0.0, 0
    for h in itertools.combinations(range(52), 2):
        eq = frozen.equity(list(h), [])
        sigma = _toy_sigma(eq)
        hole = [DECK[c] for c in h]
        for c in (0, 3, 5):
            result, before, ds, net = _toy_hand(hole, c, sigma)
            terms = hand_terms(frozen, trace_hand(result, before, ds, 0, hole))
            assert terms["decisions_with_term"] == 1
            true_ev += sigma[c] * net
            aivat_mean += sigma[c] * (net - terms["total"])
        n += 1
    true_ev, aivat_mean = true_ev / n, aivat_mean / n
    table_mean = np.mean([frozen.equity(list(h), []) for h in itertools.combinations(range(52), 2)])
    offset = frozen.scale("preflop", 150, 10000) * (table_mean - 0.5)
    assert aivat_mean == pytest.approx(true_ev - offset, abs=1e-6)
    assert abs(offset) < 1.0                     # under a chip a hand, which is what the write-up implies


def test_toy_game_monte_carlo_over_seeds_agrees_with_the_true_ev(frozen):
    """The same toy sampled the way a burst is: 20 seeds of 2,000 hands, the pooled mean within 4 standard errors."""
    combos = list(itertools.combinations(range(52), 2))
    eqs = np.array([frozen.equity(list(h), []) for h in combos])
    true_ev = float(np.mean((1 - eqs) * -50 + eqs * 100))
    values, raws = [], []
    for seed in range(20):
        rng = np.random.default_rng(seed)
        for _ in range(2000):
            k = int(rng.integers(len(combos)))
            sigma = _toy_sigma(eqs[k])
            c = int(rng.choice(6, p=sigma))
            hole = [DECK[x] for x in combos[k]]
            result, before, ds, net = _toy_hand(hole, c, sigma)
            values.append(net - hand_terms(frozen, trace_hand(result, before, ds, 0, hole))["total"])
            raws.append(net)
    values = np.array(values)
    se = values.std() / np.sqrt(values.size)
    assert abs(values.mean() - true_ev) < 4 * se + 1.0
    # No variance claim here: the frozen g is fitted to real pots, so on a toy whose nets are only -50 or +100 the
    # deal term (about 940 * (equity - 1/2)) adds spread. Unbiased is not the same as useful on every game.
    assert values.std() > np.std(raws)


# ---------------------------------------------------------------------------------------------------------------
# Every turn and river through one line, read through trace_hand: the chance terms' mean is zero exactly.
# ---------------------------------------------------------------------------------------------------------------

HOLE = ["Ah", "Kh"]
FLOP = ["Qh", "7h", "2s"]


def _line(turn, river):
    """Limp, check the flop, bet the turn only when it is a heart (so the river's pot depends on the turn), check
    the river. Seat 0 is the button: on later streets seat 1 acts first."""
    hist = [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop"),
            act(0, "call", 50, "preflop"), act(1, "check", 0, "preflop"),
            act(1, "check", 0, "flop"), act(0, "check", 0, "flop"), act(1, "check", 0, "turn")]
    ds = [row(1, "preflop", [], 1, 150, 50), row(1, "flop", FLOP, 1, 200, 0)]
    pot_turn = 200
    ds.append(row(1, "turn", FLOP + [turn], 3 if turn[1] == "h" else 1, pot_turn, 0))
    if turn[1] == "h":
        hist += [act(0, "bet", 200, "turn"), act(1, "call", 200, "turn")]
    else:
        hist.append(act(0, "check", 0, "turn"))
    hist += [act(1, "check", 0, "river"), act(0, "check", 0, "river")]
    ds.append(row(1, "river", FLOP + [turn, river], 1, 600 if turn[1] == "h" else 200, 0))
    result = {"hand_number": 1, "action_history": hist, "stacks": [10000, 10000], "showdown": []}
    return result, ds


def test_turn_and_river_terms_average_zero_over_every_runout_through_the_trace(frozen):
    seen = set(HOLE + FLOP)
    sums, n = 0.0, 0
    for turn in [c for c in DECK if c not in seen]:
        for river in [c for c in DECK if c not in seen | {turn}]:
            result, ds = _line(turn, river)
            terms = hand_terms(frozen, trace_hand(result, [10000, 10000], ds, 0, HOLE))
            assert set(terms["chance"]) == set(STREETS)
            sums += terms["chance"]["turn"] + terms["chance"]["river"]
            n += 1
    assert n == 47 * 46
    assert sums / n == pytest.approx(0.0, abs=1e-9)


def test_the_removal_formula_is_the_true_mean_of_a_river_term(frozen, tmp_path):
    """
    With the opponent's cards known, the true river distribution excludes them. The mean of the river term under
    it, enumerated, must equal what scripts/aivat_sim.removal_bias reports for that hand.
    """
    from scripts.aivat_sim import removal_bias
    opp = ["Qs", "Qd"]
    turn = "8c"
    seen = set(HOLE + FLOP + [turn])
    rivers = [c for c in DECK if c not in seen | set(opp)]
    assert len(rivers) == 44
    vals = []
    for river in rivers:
        result, ds = _line(turn, river)
        vals.append(hand_terms(frozen, trace_hand(result, [10000, 10000], ds, 0, HOLE))["chance"]["river"])
    true_mean = float(np.mean(vals))
    result, ds = _line(turn, rivers[0])
    log = [{"frame": "match_start", "seat": 0, "at": 0.0, "version": {"label": "sim"}},
           {"frame": "round_start", "state": {"hand_number": 1, "your_hole_cards": HOLE, "stacks": [10000, 10000],
                                               "sim_opponent_hole": opp}}] + ds + \
          [{"frame": "round_result", "result": result}]
    path = tmp_path / "one.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in log) + "\n")
    out = removal_bias([str(path)], frozen)
    assert out["river"] == [pytest.approx(true_mean, abs=1e-9)]
    assert true_mean != pytest.approx(0.0, abs=1e-6)     # the bias is real, if small


# ---------------------------------------------------------------------------------------------------------------
# Which streets get a term
# ---------------------------------------------------------------------------------------------------------------

def _with_hole(rows, hole):
    rows[0]["state"]["your_hole_cards"] = hole
    return rows


@pytest.mark.parametrize("street, expected", [("preflop", {"preflop"}), ("turn", {"preflop", "flop", "turn"})])
def test_a_called_allin_stops_the_chance_terms_at_its_street(frozen, street, expected):
    mine, theirs, board = ["Ac", "Qd"], ["Js", "Jd"], ["Ah", "Kd", "7c", "2s", "9h"]
    rows = _with_hole(allin_hand(1, mine, theirs, board, street, stacks=(4000, 9000)), mine)
    ds = decisions_of(rows)
    allins = allin_nets(rows, 0, ds)
    assert allins[1][1]["street"] == street
    value, terms = aivat_hands(rows, 0, ds, allins, frozen)[1]
    assert set(terms["chance"]) == expected
    assert value == pytest.approx(allins[1][0] - terms["total"])


def test_a_river_allin_keeps_its_realised_net_and_every_street_term(frozen):
    mine, theirs, board = ["Ac", "Qd"], ["Js", "Jd"], ["Ah", "Kd", "7c", "2s", "9h"]
    rows = _with_hole(allin_hand(1, mine, theirs, board, "river"), mine)
    ds = decisions_of(rows)
    allins = allin_nets(rows, 0, ds)
    assert allins == {}
    value, terms = aivat_hands(rows, 0, ds, allins, frozen)[1]
    assert set(terms["chance"]) == set(STREETS)
    assert value == pytest.approx(hand_nets(rows, 0)[1] - terms["total"])


def test_a_preflop_fold_gets_only_the_deal_term(frozen):
    result, before, ds, net = _toy_hand(["7c", "2d"], 0, None)
    terms = hand_terms(frozen, trace_hand(result, before, ds, 0, ["7c", "2d"]))
    assert set(terms["chance"]) == {"preflop"} and net == -50
    assert terms["chance"]["preflop"] < 0         # a bad deal is credited back to us


def test_an_opponent_fold_on_the_turn_gets_terms_up_to_the_turn(frozen):
    hist = [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop"),
            act(0, "call", 50, "preflop"), act(1, "check", 0, "preflop"),
            act(1, "check", 0, "flop"), act(0, "check", 0, "flop"),
            act(1, "check", 0, "turn"), act(0, "bet", 200, "turn"), act(1, "fold", 0, "turn")]
    ds = [row(1, "preflop", [], 1, 150, 50), row(1, "flop", FLOP, 1, 200, 0), row(1, "turn", FLOP + ["8c"], 3, 200, 0)]
    result = {"hand_number": 1, "action_history": hist, "stacks": [10100, 9900], "showdown": []}
    terms = hand_terms(frozen, trace_hand(result, [10000, 10000], ds, 0, HOLE))
    assert set(terms["chance"]) == {"preflop", "flop", "turn"}


def test_a_split_pot_scores_zero_less_its_terms(frozen):
    """Both play the board: net 0, all four streets get a term, nothing special-cased."""
    board = ["As", "Ks", "Qs", "Js", "Ts"]
    hist = [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop"),
            act(0, "call", 50, "preflop"), act(1, "check", 0, "preflop")]
    ds = [row(1, "preflop", [], 1, 150, 50)]
    for s, k in (("flop", 3), ("turn", 4), ("river", 5)):
        hist += [act(1, "check", 0, s), act(0, "check", 0, s)]
        ds.append(row(1, s, board[:k], 1, 200, 0))
    rows = [{"frame": "round_start", "state": {"hand_number": 1, "stacks": [10000, 10000],
                                               "your_hole_cards": ["2c", "3d"]}}] + ds + \
           [{"frame": "round_result", "result": {"hand_number": 1, "action_history": hist, "stacks": [10000, 10000],
                                                 "showdown": [{"seat": 0, "hole_cards": ["2c", "3d"]},
                                                              {"seat": 1, "hole_cards": ["4c", "5d"]}]}}]
    value, terms = aivat_hands(rows, 0, decisions_of(rows), {}, frozen)[1]
    assert set(terms["chance"]) == set(STREETS)
    assert value == pytest.approx(-terms["total"])
    assert frozen.equity([card_index("2c"), card_index("3d")], [card_index(c) for c in board]) == 0.5


# ---------------------------------------------------------------------------------------------------------------
# The decision term
# ---------------------------------------------------------------------------------------------------------------

def test_a_decision_term_stays_unbiased_when_the_logged_probs_put_mass_on_an_illegal_slot(frozen):
    """
    If the client sampled from an unmasked distribution and an illegal draw was logged as such, the code masks,
    renormalises and skips the illegal draw. Conditional on a legal draw the masked distribution is the right one,
    so the expected term over every draw is still zero.
    """
    raw = np.array([0.2, 0.2, 0.1, 0.2, 0.1, 0.2])
    legal = (1, 1, 1, 1, 0, 0)
    hist = [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop"),
            act(0, "call", 50, "preflop"), act(1, "check", 0, "preflop"), act(1, "raise", 150, "flop"),
            act(0, "call", 150, "flop")]
    total = 0.0
    for c in range(6):
        ds = [row(1, "preflop", [], 1, 150, 50), row(1, "flop", FLOP, c, 350, 150, raw, legal)]
        result = {"hand_number": 1, "action_history": hist, "stacks": [10000, 10000], "showdown": []}
        total += raw[c] * hand_terms(frozen, trace_hand(result, [10000, 10000], ds, 0, HOLE))["decision"]
    assert total == pytest.approx(0.0, abs=1e-9)


@pytest.mark.xfail(strict=True, reason="REVIEW BUG (minor, latent): trace_hand pairs our history actions with our "
                                       "decision rows by an iterator and drops a row whose phase does not match, so "
                                       "one missing preflop row silently loses every later row's term without "
                                       "counting it in decisions_without. No real log has a missing row today.")
def test_a_missing_decision_row_does_not_swallow_the_next_streets_term(frozen):
    sigma = [0.1, 0.5, 0.1, 0.2, 0.05, 0.05]
    hist = [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop"),
            act(0, "call", 50, "preflop"), act(1, "check", 0, "preflop"),
            act(1, "check", 0, "flop"), act(0, "check", 0, "flop")]
    ds = [row(1, "flop", FLOP, 1, 200, 0, sigma)]          # the preflop row is missing
    result = {"hand_number": 1, "action_history": hist, "stacks": [10000, 10000], "showdown": []}
    terms = hand_terms(frozen, trace_hand(result, [10000, 10000], ds, 0, HOLE))
    assert terms["decisions_with_term"] + terms["decisions_without"] == 1


# ---------------------------------------------------------------------------------------------------------------
# Freezing: the value file and the fit's exclusions
# ---------------------------------------------------------------------------------------------------------------

def test_the_frozen_file_is_the_digest_the_write_up_quotes_and_records_its_cutoff(frozen):
    assert frozen.digest == "5e8aa4ce68af"
    prov = frozen.provenance
    assert prov["matches_before_ist"] == "2026-10-03T00:00"
    assert set(prov["excluded_labels"]) == {"v5xRR3 purified", "balanced-next", "v5xRR3s10 purified"}


def test_the_fit_skips_burst_labels_and_matches_at_or_after_the_cutoff(tmp_path):
    from scripts.aivat_fit import BURSTS, match_rows
    cut = _ist("2026-10-03T00:00")
    cases = {"old": ("v5x: something", cut - 3600), "edge": ("v5x: something", cut),
             "late": ("v5x: something", cut + 60), "burst": ("v5xRR3 purified: x", cut - 60),
             "bn": ("balanced-next: x", cut - 60), "s10": ("v5xRR3s10 purified: x", cut - 60)}
    for name, (label, at) in cases.items():
        (tmp_path / f"{name}.jsonl").write_text(json.dumps({"frame": "match_start", "seat": 0, "at": at,
                                                            "version": {"label": label}}) + "\n")
    kept = [os.path.basename(p) for p, _ in match_rows(sorted(glob.glob(str(tmp_path / "*.jsonl"))), cut,
                                                         list(BURSTS))]
    assert kept == ["old.jsonl"]


def test_hand_class_partitions_the_1326_deals_into_169_classes():
    from collections import Counter
    counts = Counter(hand_class(h) for h in itertools.combinations(range(52), 2))
    assert len(counts) == 169
    assert Counter(counts.values()) == {6: 13, 4: 78, 12: 78}
    assert hand_class((card_index("Ah"), card_index("Kh"))) == "AKs"
    assert hand_class((card_index("2c"), card_index("7d"))) == "72o"


# ---------------------------------------------------------------------------------------------------------------
# The window, the dagger and old logs, through the script's main
# ---------------------------------------------------------------------------------------------------------------

def test_between_reads_a_naive_time_as_ist():
    """The logs carry `at` as a Unix time, so the machine's clock change on 5 Oct cannot move it; only the parse can."""
    assert _ist("2026-10-05T00:09") == datetime.datetime(2026, 10, 4, 18, 39, tzinfo=datetime.timezone.utc).timestamp()


@pytest.mark.xfail(strict=True, reason="REVIEW BUG (minor): _ist replaces any explicit offset with +05:30, so "
                                       "--between 2026-10-03T07:00+04:00 is silently read as 07:00 IST, 90 minutes "
                                       "off, the exact confusion the machine's old +04 clock invites.")
def test_between_respects_an_explicit_offset():
    assert _ist("2026-10-03T07:00+04:00") == datetime.datetime(2026, 10, 3, 3, 0,
                                                               tzinfo=datetime.timezone.utc).timestamp()


def _match_file(path, at, hole=True, label="t: test"):
    rows = [{"frame": "match_start", "seat": 0, "at": at, "version": {"label": label}}]
    state = {"hand_number": 1, "stacks": [10000, 10000]}
    if hole:
        state["your_hole_cards"] = ["7c", "2d"]
    rows.append({"frame": "round_start", "state": state})
    rows.append(row(1, "preflop", [], 0, 150, 50))
    rows.append({"frame": "round_result", "result": {
        "hand_number": 1, "stacks": [9950, 10050], "showdown": [],
        "action_history": [act(0, "post_small_blind", 50, "preflop"), act(1, "post_big_blind", 100, "preflop"),
                           act(0, "fold", 0, "preflop")]}})
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def _run_main(monkeypatch, capsys, argv):
    from scripts import chipzen_decompose
    monkeypatch.setattr(sys, "argv", ["chipzen_decompose.py"] + argv)
    chipzen_decompose.main()
    return capsys.readouterr().out


def test_between_keeps_the_start_and_drops_the_end(tmp_path, monkeypatch, capsys):
    start, end = _ist("2026-10-03T07:00"), _ist("2026-10-03T09:00")
    for name, at in (("a", start - 1), ("b", start), ("c", end - 1), ("d", end)):
        _match_file(tmp_path / f"{name}.jsonl", at)
    out = _run_main(monkeypatch, capsys, ["--label", "t", "--matches-dir", str(tmp_path),
                                          "--between", "2026-10-03T07:00", "2026-10-03T09:00"])
    assert "-50 ± 0 (2)" in out


def test_only_the_all_deep_and_short_rows_go_unmarked(tmp_path, monkeypatch, capsys):
    _match_file(tmp_path / "a.jsonl", 0.0)
    out = _run_main(monkeypatch, capsys, ["--label", "t", "--matches-dir", str(tmp_path), "--aivat"])
    lines = {l.split("|")[1].strip(): l for l in out.splitlines() if l.startswith("| ") and "category" not in l}
    for cat, line in lines.items():
        assert ("†" in line) == (cat not in ("all", "deep", "short")), cat
    assert "5e8aa4ce68af" in out


@pytest.mark.xfail(strict=True, reason="REVIEW BUG (minor, latent): a round_start without your_hole_cards is left "
                                       "out of aivat_hands but main still indexes scored[hand], so --aivat dies with "
                                       "a KeyError instead of skipping or counting the hand. Every current log has "
                                       "the field.")
def test_aivat_survives_a_hand_without_hole_cards(tmp_path, monkeypatch, capsys):
    _match_file(tmp_path / "a.jsonl", 0.0, hole=False)
    _run_main(monkeypatch, capsys, ["--label", "t", "--matches-dir", str(tmp_path), "--aivat"])
