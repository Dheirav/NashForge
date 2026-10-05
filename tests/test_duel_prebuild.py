"""chipzen_duel.py builds the histogram rungs' native tables once, in the parent, before it forks its workers."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import scripts.chipzen_duel as duel  # noqa: E402


class FakeAbstraction:
    """Counts its builds; the real one caches the native tables on itself the same way."""

    def __init__(self, tables=True):
        self._hist_tables = {"flop": ("keys", "buckets")} if tables else None
        self.builds = 0

    def native_tables(self):
        cached = getattr(self, "_native_tables", None)
        if cached is not None:
            return cached
        self.builds += 1
        self._native_tables = {"flop": object()}
        return self._native_tables


class FakeSolver:
    def __init__(self, abstraction):
        self.abstraction = abstraction


class FakePlayer:
    def __init__(self, ladder, companions=()):
        self.ladder = list(ladder)
        self.companions = None if companions is None else list(companions)


class Scripted:
    """An archetype or push/fold player: no ladder at all."""


def test_prebuild_builds_each_histogram_rung_once_and_skips_the_rest():
    hist, hist_companion, plain = FakeAbstraction(), FakeAbstraction(), FakeAbstraction(tables=False)
    a = FakePlayer([FakeSolver(hist), FakeSolver(plain)], [FakeSolver(hist_companion)])
    assert duel.prebuild_tables(a, Scripted()) == 2
    assert (hist.builds, hist_companion.builds, plain.builds) == (1, 1, 0)
    assert not hasattr(plain, "_native_tables")
    # A second call, or a worker's first decision, finds them cached.
    duel.prebuild_tables(a)
    assert hist.builds == 1


def test_prebuild_takes_a_player_with_no_companions_or_an_empty_ladder():
    assert duel.prebuild_tables(FakePlayer([], None), FakePlayer([FakeSolver(None)])) == 0


def _child_view(_):
    # Inside a forked worker: what the parent built before the fork, then what a lookup costs here.
    abstraction = duel._PLAYERS[0].ladder[0].abstraction
    inherited = abstraction.builds
    abstraction.native_tables()
    return inherited, abstraction.builds


def test_forked_workers_inherit_the_built_tables():
    hist = FakeAbstraction()
    players = (FakePlayer([FakeSolver(hist)]), Scripted())
    with duel._fork_pool(players, 2) as pool:
        views = pool.map(_child_view, range(4))
    assert hist.builds == 1                                   # built once, in the parent
    assert views == [(1, 1)] * 4                              # every worker saw it built and built nothing
    assert duel._PLAYERS == players


def _record(monkeypatch):
    seen = []
    real = duel.prebuild_tables
    monkeypatch.setattr(duel, "prebuild_tables", lambda *players: seen.append(players) or real(*players))
    return seen


def test_both_forking_paths_prebuild_before_the_pool(monkeypatch, tmp_path, capsys):
    seen = _record(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["chipzen_duel.py", "--a", "archetype:station", "--b", "archetype:nit",
                                      "--arena-matches", "4", "--workers", "2", "--seed", "3",
                                      "--output", str(tmp_path / "m.json")])
    duel.main()
    monkeypatch.setattr(sys, "argv", ["chipzen_duel.py", "--a", "archetype:station", "--b", "archetype:nit",
                                      "--hands", "6", "--stack-bb", "20", "--workers", "2", "--seed", "3",
                                      "--output", str(tmp_path / "d.json")])
    duel.main()
    assert len(seen) == 2 and all(len(players) == 2 for players in seen)
    assert (tmp_path / "m.json").exists() and (tmp_path / "d.json").exists()


def test_one_worker_does_not_fork_or_prebuild(monkeypatch, tmp_path):
    seen = _record(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["chipzen_duel.py", "--a", "archetype:station", "--b", "archetype:nit",
                                      "--arena-matches", "2", "--seed", "3", "--output", str(tmp_path / "m.json")])
    duel.main()
    assert seen == []
