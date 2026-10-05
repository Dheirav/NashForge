"""
Independent review of the visit-counter branch: the gaps left by tests/test_visit_counter.py.

The branch's own tests pin Kuhn's forced counts, root sums in a small no-limit
game, on-equals-off for one plain run, the flat key order and the round trip.
What they leave out, and this file covers:

- the node layout and saturation, which only the compiler can see (a probe is
  compiled against the header in a temporary directory; the module itself is
  not rebuilt);
- on-equals-off under pruning, warm starts, a scripted opponent and the
  weighted rules, which are the paths the real rungs take;
- exact counts below the root and under heavier threading, where a lost
  increment would show;
- average_from across train() chunks, the frozen and proportional warm
  phases, pruning, and a scripted opponent;
- the trainer end to end: snapshot timing, naming, averaged iterations, and
  its argument checks;
- the report on empty and tiny inputs, and the stopping rule over every
  combination of missing legs.

Tests marked xfail(strict=True) with "REVIEW BUG" are behaviours judged wrong.
"""
import itertools
import os
import shutil
import subprocess
import sys
import textwrap

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

native = pytest.importorskip("pokerbot_native", reason="run native/build.sh to build the C++ core")

from cfr.flat import KEY_WIDTH, flat_paths, load_strategy  # noqa: E402
from cfr.visits import (Visits, classify, from_solver, load_visits, street_and_depth,  # noqa: E402
                        visits_path, write_visits)
from scripts.cfr import visit_report as report  # noqa: E402

PYTHON = os.path.join(ROOT, "venv", "bin", "python")


def _solver(seed=3, rule="vanilla"):
    # Every preflop hand in bucket 0, so a preflop history is one key: the
    # counts at "0|1" to "0|5" are then exact, not sums over buckets.
    return native.NoLimitSolver([0] * (52 * 52), [0.3, 0.6], [0.3, 0.6], [0.3, 0.6], 8, 200, 1, 2,
                                [4, 4], seed, rule=rule)


def _counts(solver):
    v = from_solver(solver)
    return {k.decode(): (int(a), int(r)) for k, a, r in zip(v.keys, v.avg, v.regret)}


def _flat(solver):
    keys, offsets, values = solver.average_strategy_flat(KEY_WIDTH)
    return np.asarray(keys).copy(), np.asarray(offsets).copy(), np.asarray(values).copy()


# --- layout and saturation, via a compiled probe ---------------------------

PROBE = textwrap.dedent("""
    #include <cstddef>
    #include <cstdio>
    #include "mccfr.hpp"
    using namespace pokerbot;
    int main() {
        InfoSetNode n(3);
        n.avg_visits = UINT32_MAX - 1;
        InfoSetNode::bump(n.avg_visits);
        const unsigned at_max = n.avg_visits;
        InfoSetNode::bump(n.avg_visits);
        n.regret_visits = UINT32_MAX;
        InfoSetNode::bump(n.regret_visits);
        InfoSetNode copy(n);
        std::printf("%zu %zu %zu %zu %zu %zu %zu %u %u %u %u %u\\n",
            sizeof(InfoSetNode), offsetof(InfoSetNode, avg_visits), offsetof(InfoSetNode, regret_sum),
            offsetof(InfoSetNode, strategy_sum), offsetof(InfoSetNode, last_discounted),
            offsetof(InfoSetNode, busy), offsetof(InfoSetNode, regret_visits),
            at_max, n.avg_visits, n.regret_visits, copy.avg_visits, copy.regret_visits);
    }
""")


@pytest.fixture(scope="module")
def probe(tmp_path_factory):
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("no g++ to compile the layout probe")
    where = tmp_path_factory.mktemp("probe")
    src, exe = where / "probe.cpp", where / "probe"
    src.write_text(PROBE)
    subprocess.run([compiler, "-std=c++17", "-w", "-I", os.path.join(ROOT, "native", "src"), str(src), "-o", str(exe)],
                   check=True, capture_output=True)
    return [int(x) for x in subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout.split()]


def test_the_node_is_120_bytes_and_the_old_fields_did_not_move(probe):
    size, avg_at, regret_sum_at, strategy_sum_at, last_at, busy_at, regret_visits_at = probe[:7]
    # Offsets of the pre-existing fields as main's header compiles them (8, 56, 104, 112).
    assert size == 120
    assert (regret_sum_at, strategy_sum_at, last_at, busy_at) == (8, 56, 104, 112)
    assert avg_at == 4 and regret_visits_at == 116     # both in what was padding


def test_the_counters_saturate_rather_than_wrap_and_survive_a_copy(probe):
    """Training to 2^32 is impractical; the increment itself is the code path, and this pins it."""
    at_max, after_one_more, regret, copy_avg, copy_regret = probe[7:]
    assert at_max == after_one_more == regret == 2**32 - 1
    # The copy constructor is what a rehash or a table copy uses; it must carry both.
    assert copy_avg == copy_regret == 2**32 - 1


# --- counting on changes no strategy bit, on the paths rungs take -----------

def _configure(solver, case, prior):
    if case == "prune":
        solver.set_pruning(100, 0.0, 0.95)
    elif case == "frozen":
        solver.warm_start(prior, 150, 2.0, "frozen")
        solver.set_average_from(150)
    elif case == "proportional":
        solver.warm_start(prior, 150, 2.0, "proportional")
    elif case == "archetype":
        from chipzen.archetypes import PARAMS
        solver.set_opponent_archetype({k: float(v) for k, v in PARAMS["station"].items()}, 2, 0.5)
    elif case == "current_when_empty":
        solver.set_current_when_empty(True)
        solver.set_average_from(200)


@pytest.fixture(scope="module")
def prior():
    s = _solver(9)
    s.train(300)
    return [(k, list(v)) for k, v in s.average_strategy().items()]


@pytest.mark.parametrize("case,rule", [("prune", "vanilla"), ("frozen", "linear"), ("proportional", "vanilla"),
                                       ("archetype", "vanilla"), ("current_when_empty", "dcfr"),
                                       ("plain", "linear"), ("plain", "dcfr")])
def test_counting_changes_no_bit_on_the_rung_paths(case, rule, prior):
    off, on = _solver(4, rule), _solver(4, rule)
    on.set_count_visits(True)
    for s in (off, on):
        _configure(s, case, prior)
        s.train(250)
        s.train(250)   # two calls, as the trainer chunks
    for a, b in zip(_flat(off), _flat(on)):
        assert np.array_equal(a, b)
    assert off.iterations() == on.iterations() and off.pruned() == on.pruned()
    assert off.warm_hits() == on.warm_hits()
    if case == "prune":
        assert on.pruned() > 0, "the pruning case must actually prune to test anything"


def test_counting_can_be_switched_off_again():
    s = _solver()
    s.set_count_visits(True)
    s.train(100)
    before = _counts(s)
    s.set_count_visits(False)
    s.train(100)
    after = _counts(s)
    assert all(after[k] == before[k] for k in before)   # nothing counted while off
    assert all(after[k] == (0, 0) for k in set(after) - set(before))


# --- exact counts under threads and below the root -------------------------

@pytest.mark.parametrize("threads", [1, 4])
def test_counts_below_the_root_are_exact_under_threads(threads):
    T = 3000
    s = _solver(6)
    s.set_count_visits(True)
    s.train(T, threads)
    c = _counts(s)
    assert c["0|"] == (T, T)
    # In player 0's traversal every root action is walked and player 1 is the
    # sampled player at each non-terminal child: one average sample per
    # iteration at each of "0|1" to "0|5". Exact, whatever the thread count.
    for a in "12345":
        assert c[f"0|{a}"][0] == T, a
    # In player 1's traversal player 0 samples one root action; player 1
    # updates regret at that child unless it was the fold.
    assert sum(c[f"0|{a}"][1] for a in "12345") <= T


def test_kuhn_counts_survive_heavy_contention():
    T = 200_000
    v = native.solve_kuhn_visits(T, 17, 8)
    total = {h: [sum(v[f"{c}|{h}"][i] for c in "012") for i in (0, 1)] for h in ("", "p", "b", "pb")}
    assert total[""] == [T, T]
    assert total["p"][0] == T and total["b"][0] == T
    assert total["p"][1] + total["b"][1] == T
    assert total["pb"][0] == total["p"][1]


def test_average_from_is_respected_across_train_chunks():
    s = _solver()
    s.set_count_visits(True)
    s.set_average_from(150)
    for _ in range(3):
        s.train(100)
    c = _counts(s)
    assert c["0|"] == (150, 300)


# --- warm starts, pruning, scripted opponents ------------------------------

def test_frozen_phase_is_out_of_avg_only_when_average_from_says_so(prior):
    W, n = 120, 200
    kept_out = _solver()
    kept_out.set_count_visits(True)
    kept_out.warm_start(prior, W, 2.0, "frozen")
    kept_out.set_average_from(W)            # what the trainer does
    kept_out.train(W + n)
    assert _counts(kept_out)["0|"] == (n, W + n)
    # Without average_from the solver averages the frozen prior into
    # strategy_sum, and the counter follows strategy_sum, as it should.
    kept_in = _solver()
    kept_in.set_count_visits(True)
    kept_in.warm_start(prior, W, 2.0, "frozen")
    kept_in.train(W + n)
    assert _counts(kept_in)["0|"] == (W + n, W + n)


def test_proportional_warm_start_counts_only_played_iterations(prior):
    W, n = 500, 200
    s = _solver()
    s.set_count_visits(True)
    s.warm_start(prior, W, 2.0, "proportional")
    assert s.iterations() == W        # the counter starts at the prior's weight
    s.train(n)
    assert _counts(s)["0|"] == (n, n)
    assert from_solver(s, averaged_from=W).averaged_iterations == n


def test_pruning_skips_counts_below_pruned_actions_only():
    T = 2000
    s = _solver(8)
    s.set_count_visits(True)
    s.set_pruning(200, 0.0, 0.95)
    s.train(T)
    c = _counts(s)
    assert s.pruned() > 0
    # The root is never below a pruned action, and a pruned node still makes
    # its regret update, so both root counts stay exact.
    assert c["0|"] == (T, T)
    # A child of a pruned root action loses that iteration's average sample;
    # the shortfall is real (the counter counts samples, not iterations) and
    # bounded by the solver's own count of pruned visits.
    short = sum(T - c[f"0|{a}"][0] for a in "12345")
    assert 0 <= short <= s.pruned()


def test_with_a_scripted_opponent_both_counters_count_the_same_visits():
    """
    Against a script the learner's nodes are only entered as the traverser, so
    avg_visits and regret_visits are the same count, node for node. The report's
    reach proxy (avg x regret) is then the traverser's visits squared, not reach
    times chance: the definition in cfr/visits.py holds for self-play only.
    """
    from chipzen.archetypes import PARAMS
    s = _solver()
    s.set_count_visits(True)
    s.set_opponent_archetype({k: float(v) for k, v in PARAMS["station"].items()}, 2, 0.5)
    s.train(400)
    v = from_solver(s)
    assert len(v) and np.array_equal(v.avg, v.regret)
    assert _counts(s)["0|"] == (400, 400)


# --- the export -------------------------------------------------------------

def test_visits_flat_edges():
    empty = _solver()
    keys, avg, reg = empty.visits_flat(KEY_WIDTH)
    assert np.asarray(keys).shape == (0, KEY_WIDTH) and len(avg) == len(reg) == 0
    s = _solver()
    s.set_count_visits(True)
    s.train(200)
    with pytest.raises(ValueError):
        s.visits_flat(2)          # "0|25" and the like do not fit
    # Another width still lines up with the strategy export at that width.
    k20, _, _ = s.visits_flat(20)
    f20, _, _ = s.average_strategy_flat(20)
    assert np.array_equal(np.asarray(k20), np.asarray(f20))
    v = from_solver(s)
    assert v.avg.dtype == np.uint32 and v.regret.dtype == np.uint32
    assert (v.keys[:-1] < v.keys[1:]).all()   # sorted and unique, as ratios() assumes


def test_files_round_trip_when_empty_and_old_strategies_need_no_visits_file(tmp_path):
    empty = Visits(np.array([], dtype=f"S{KEY_WIDTH}"), np.array([], dtype=np.uint32),
                   np.array([], dtype=np.uint32), 0, 0, {"obj": object()})
    path = str(tmp_path / "e.visits.npz")
    write_visits(path, empty)
    back = load_visits(path)
    assert len(back) == 0 and back.avg.dtype == np.uint32 and isinstance(back.meta["obj"], str)
    with pytest.raises(FileNotFoundError):
        load_visits(str(tmp_path / "missing.visits.npz"))


def test_the_visits_file_sits_beside_the_flat_pair_for_any_output():
    for output in ("results/x/rung_12bb.pkl", "results/x/rung_0.5", "results/x/rung_0.7"):
        stem = flat_paths(output)[0][:-len(".flat.npz")]
        assert visits_path(output) == stem + ".visits.npz", output


# --- key parsing ------------------------------------------------------------

@pytest.mark.parametrize("key,expected", [
    ("0|5", (0, 1)),            # an open shove
    ("0|25", (0, 2)),           # raise, shove over
    (b"168|21/5\0\0", (1, 1)),  # a three-digit bucket, a flop shove
    ("4|1/", (1, 0)),           # first to act on the flop
    ("4|21/1/", (2, 0)),
    ("4|21/1/24/", (3, 0)),     # raises on the turn do not carry to the river
    ("1|pb", (0, 0)),           # a Kuhn key: no raise symbols, no streets
    ("|", (0, 0)),
])
def test_street_and_depth_edge_keys(key, expected):
    assert street_and_depth(key) == expected


def test_parsed_depth_matches_the_tree_on_real_keys():
    s = _solver()
    s.set_count_visits(True)
    s.train(400)
    v = from_solver(s)
    streets, depths = classify(v.keys)
    assert set(streets.tolist()) == {0, 1, 2, 3}
    assert depths.min() == 0 and depths.max() == 2   # the [4, 4] schedule is two raises a street
    for k, st in zip(v.keys, streets):
        assert k.decode().count("/") == st


# --- the report ---------------------------------------------------------------

class _Args:
    def __init__(self, bar=100, h2h_delta=None, h2h_se=None, lbr_delta=None, lbr_se=None):
        self.bar, self.h2h_delta, self.h2h_se, self.lbr_delta, self.lbr_se = bar, h2h_delta, h2h_se, lbr_delta, lbr_se


def _visits(keys, avg, reg, iterations=1000):
    return Visits(np.array(keys, dtype=f"S{KEY_WIDTH}"), np.array(avg, dtype=np.uint32),
                  np.array(reg, dtype=np.uint32), iterations, iterations)


def test_summary_on_empty_tiny_and_unreached_inputs():
    assert report.summarise(np.array([], dtype=np.uint32), np.array([], dtype=np.uint32)) == {"nodes": 0}
    one = report.summarise(np.array([7], dtype=np.uint32), np.array([3], dtype=np.uint32))
    assert one["p1"] == one["p90"] == one["rw_p10"] == 7 and one["under_10"] == 1.0
    zero = report.summarise(np.array([0, 0], dtype=np.uint32), np.array([5, 9], dtype=np.uint32))
    assert np.isnan(zero["rw_p10"]) and np.isnan(zero["rw_under_100"]) and zero["zero"] == 1.0
    # uint32 counts near the top must not overflow the avg x regret product.
    big = report.summarise(np.array([2**32 - 1, 1], dtype=np.uint32), np.array([2**32 - 1, 1], dtype=np.uint32))
    assert big["rw_p10"] == 2**32 - 1


def test_weighted_percentile_definition():
    w = np.ones(4)
    v = np.array([1.0, 2.0, 3.0, 4.0])
    assert report.weighted_percentile(v, w, 10) == 1 and report.weighted_percentile(v, w, 50) == 2
    assert report.weighted_percentile(v, w, 100) == 4
    # Zero-weight values never become the percentile.
    assert report.weighted_percentile(np.array([0.0, 5.0, 9.0]), np.array([0.0, 1.0, 1.0]), 10) == 5
    assert np.isnan(report.weighted_percentile(np.array([]), np.array([]), 10))


def test_breakdown_and_ratios_on_empty_and_disjoint_snapshots():
    empty = _visits([], [], [], 0)
    rows = report.breakdown(empty)
    assert rows == {"all": {"nodes": 0}}
    legs, verdict = report.rule(rows, _Args(h2h_delta=0.1, h2h_se=0.5, lbr_delta=0.1, lbr_se=1.0))
    assert verdict != "done" and legs["a_visits"]["pass"] is False
    r = report.ratios(empty, empty)
    assert r["common"] == 0 and np.isnan(r["iteration_ratio"])
    a = _visits([b"0|", b"0|1"], [10, 4], [10, 4])
    b = _visits([b"0|2", b"0|3"], [20, 8], [20, 8], 2000)
    r = report.ratios(a, b)
    assert r["common"] == 0 and r["only_in_a"] == 2 and r["only_in_b"] == 2 and "all" not in r


def test_ratios_on_shared_nodes():
    a = _visits([b"0|", b"0|1", b"0|1/"], [10, 0, 4], [10, 3, 4], 1000)
    b = _visits([b"0|", b"0|1", b"0|1/", b"0|2"], [20, 5, 12], [20, 3, 12], 2000)
    r = report.ratios(a, b)
    assert r["common"] == 3 and r["only_in_b"] == 1 and r["iteration_ratio"] == 2.0
    # The node with no samples in A is left out of the ratio rather than dividing by zero.
    assert r["all"]["nodes"] == 2 and r["all"]["median"] == pytest.approx(2.5)
    assert r["preflop"]["nodes"] == 1 and r["flop"]["median"] == 3.0


def test_the_worst_line_ignores_unplayed_lines_but_takes_the_rarest_played_one():
    keys = [b"0|", b"0|2", b"0|1/", b"0|1/2"]
    rows = report.breakdown(_visits(keys, [5000, 4000, 3000, 150], [5000, 4000, 3000, 2]))
    legs, _ = report.rule(rows, _Args(bar=200))
    assert legs["a_visits"]["line"] == "flop d1" and legs["a_visits"]["pass"] is False


ARG_VALUES = {"h2h_delta": (None, 0.3), "h2h_se": (None, 0.5, 2.0), "lbr_delta": (None, 0.5), "lbr_se": (None, 3.0)}


def test_the_rule_never_says_done_with_a_leg_unmeasured():
    rows = report.breakdown(_visits([b"0|", b"0|2"], [5000, 4000], [5000, 4000]))
    seen_done = False
    for combo in itertools.product(*ARG_VALUES.values()):
        args = _Args(**dict(zip(ARG_VALUES, combo)))
        legs, verdict = report.rule(rows, args)
        if args.lbr_delta is None or args.lbr_se is None:
            assert verdict != "done"
        if args.h2h_delta is None:
            assert verdict != "done"
        seen_done |= verdict == "done"
    assert seen_done      # and with every leg measured and passing, it can say done


def test_leg_b_needs_its_standard_error():
    rows = report.breakdown(_visits([b"0|", b"0|2"], [5000, 4000], [5000, 4000]))
    legs, verdict = report.rule(rows, _Args(h2h_delta=0.3, h2h_se=None, lbr_delta=0.5, lbr_se=3.0))
    assert legs["b_h2h"]["pass"] is None and verdict != "done"


def test_nan_measurements_do_not_pass():
    rows = report.breakdown(_visits([b"0|", b"0|2"], [5000, 4000], [5000, 4000]))
    nan = float("nan")
    for args in (_Args(h2h_delta=nan, h2h_se=0.5, lbr_delta=0.5, lbr_se=3.0),
                 _Args(h2h_delta=0.3, h2h_se=0.5, lbr_delta=nan, lbr_se=3.0),
                 _Args(h2h_delta=0.3, h2h_se=0.5, lbr_delta=0.5, lbr_se=nan),
                 _Args(h2h_delta=0.3, h2h_se=nan, lbr_delta=0.5, lbr_se=3.0),
                 _Args(bar=nan, h2h_delta=0.3, h2h_se=0.5, lbr_delta=0.5, lbr_se=3.0)):
        assert report.rule(rows, args)[1] != "done"


def test_the_report_script_runs_on_empty_and_single_node_files(tmp_path):
    empty = str(tmp_path / "empty.visits.npz")
    write_visits(empty, _visits([], [], [], 0))
    one = str(tmp_path / "one.visits.npz")
    write_visits(one, _visits([b"3|21/1"], [40], [9]))
    for files in ([empty], [one], [empty, one], [one, one]):
        out = subprocess.run([PYTHON, os.path.join(ROOT, "scripts", "cfr", "visit_report.py"), *files,
                              "--json", str(tmp_path / "r.json")], capture_output=True, text=True, timeout=60)
        assert out.returncode == 0, out.stderr
        assert "verdict: not measured" in out.stdout or "verdict: not done" in out.stdout


# --- the trainer, end to end --------------------------------------------------

TRAIN = [PYTHON, os.path.join(ROOT, "scripts", "cfr", "train_nolimit.py"), "--buckets", "2",
         "--abstraction-samples", "50", "--equity-samples", "10", "--eval-hands", "20", "--stack", "20",
         "--seed", "0"]


def _train(*extra, check=True):
    out = subprocess.run(TRAIN + list(extra), capture_output=True, text=True, timeout=110, cwd=ROOT)
    if check:
        assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    return out


def _root(v):
    roots = np.array([k.split(b"|", 1)[1] == b"" for k in v.keys])
    return int(v.avg[roots].sum()), int(v.regret[roots].sum())


@pytest.fixture(scope="module")
def plain_run(tmp_path_factory):
    where = tmp_path_factory.mktemp("plain")
    out = str(where / "run.pkl")
    _train("--iterations", "300", "--count-visits", "--visit-snapshots", "200", "100", "100", "300", "0", "-5",
           "--output", out)
    return out


def test_trainer_snapshot_names_and_timing(plain_run):
    where = os.path.dirname(plain_run)
    names = sorted(n for n in os.listdir(where) if ".visits." in n)
    # 0, -5 and 300 (the end, which the final file covers) write nothing; a repeat writes once.
    assert names == ["run.visits.100.npz", "run.visits.200.npz", "run.visits.npz"]
    for label in (100, 200):
        v = load_visits(os.path.join(where, f"run.visits.{label}.npz"))
        assert v.iterations == v.averaged_iterations == label and v.meta["run_iterations"] == label
        assert _root(v) == (label, label)
    final = load_visits(os.path.join(where, "run.visits.npz"))
    assert final.iterations == 300 and _root(final) == (300, 300)
    flat = np.load(flat_paths(plain_run)[0])
    assert np.array_equal(final.keys, flat["keys"])


def test_trainer_average_from_in_snapshots(tmp_path):
    out = str(tmp_path / "af.pkl")
    _train("--iterations", "300", "--average-from", "0.5", "--count-visits", "--visit-snapshots", "100", "200",
           "--output", out)
    early = load_visits(visits_path(out, 100))
    mid = load_visits(visits_path(out, 200))
    final = load_visits(visits_path(out))
    assert (early.averaged_iterations, _root(early)) == (0, (0, 100))
    assert (mid.averaged_iterations, _root(mid)) == (50, (50, 200))
    assert (final.averaged_iterations, _root(final)) == (150, (150, 300))


def test_trainer_frozen_warm_start_snapshots(plain_run, tmp_path):
    out = str(tmp_path / "frozen.pkl")
    _train("--iterations", "200", "--warm-start", plain_run, "--warm-mode", "frozen", "--warm-weight", "100",
           "--count-visits", "--visit-snapshots", "100", "--output", out)
    snap = load_visits(visits_path(out, 100))
    # Labelled in played iterations; taken after 100 frozen and 100 played.
    assert (snap.iterations, snap.averaged_iterations, snap.meta["run_iterations"]) == (200, 100, 100)
    assert _root(snap) == (100, 200)         # regret updates run through the frozen phase
    final = load_visits(visits_path(out))
    assert (final.iterations, final.averaged_iterations, final.meta["run_iterations"]) == (300, 200, 200)
    assert _root(final) == (200, 300)


def test_trainer_proportional_warm_start_snapshots(plain_run, tmp_path):
    out = str(tmp_path / "prop.pkl")
    _train("--iterations", "200", "--warm-start", plain_run, "--warm-mode", "proportional", "--warm-weight", "100",
           "--count-visits", "--visit-snapshots", "100", "--output", out)
    snap = load_visits(visits_path(out, 100))
    assert (snap.iterations, snap.averaged_iterations) == (200, 100) and _root(snap) == (100, 100)
    final = load_visits(visits_path(out))
    assert (final.iterations, final.averaged_iterations) == (300, 200) and _root(final) == (200, 200)


def test_trainer_with_pruning_and_threads(tmp_path):
    out = str(tmp_path / "pruned.pkl")
    _train("--iterations", "600", "--prune-after", "0.2", "--prune-stacks", "0", "--threads", "3",
           "--count-visits", "--visit-snapshots", "300", "--output", out)
    assert _root(load_visits(visits_path(out, 300))) == (300, 300)
    assert _root(load_visits(visits_path(out))) == (600, 600)


@pytest.mark.parametrize("extra,message", [
    (["--visit-snapshots", "100", "--output", "x.pkl"], "--visit-snapshots needs --count-visits"),
    (["--count-visits"], "--count-visits writes beside --output"),
    (["--count-visits", "--no-native", "--output", "x.pkl"], "--count-visits is a native solver feature"),
])
def test_trainer_refuses_inconsistent_flags(extra, message, tmp_path):
    out = _train("--iterations", "50", *[str(tmp_path / e) if e == "x.pkl" else e for e in extra], check=False)
    assert out.returncode != 0 and message in out.stderr


def test_an_old_strategy_without_visits_still_loads(plain_run, tmp_path):
    copy = str(tmp_path / "old.pkl")
    shutil.copy(plain_run, copy)
    for src, dst in zip(flat_paths(plain_run), flat_paths(copy)):
        shutil.copy(src, dst)
    assert not any(".visits." in n for n in os.listdir(tmp_path))
    loaded = load_strategy(copy)
    assert len(loaded["strategy"]) == len(load_visits(visits_path(plain_run)))
