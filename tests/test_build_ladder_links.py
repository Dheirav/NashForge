"""container/build_ladder.py writes the links the runner needs to play its cap2 rungs, and checks the set."""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = _load("container/build_ladder.py", "build_ladder")
package = _load("container/package.py", "package")
run = build._runner()


def touch(folder, *names):
    for name in names:
        with open(os.path.join(folder, name), "w") as handle:
            handle.write(name)


@pytest.fixture
def ladders(tmp_path):
    """A source ladder as the trainer leaves one, and a compact folder as the builder writes it."""
    source, out = tmp_path / "ladder169l_x", tmp_path / "ladder169l_x_compact"
    source.mkdir(); out.mkdir()
    touch(source, "nolimit_5bb.pkl", "nolimit_12bb.pkl", "nolimit_12bb.flat.npz", "nolimit_12bb.flat.pkl",
          "nolimit_70bb.pkl", "cap2_12bb.pkl", "cap2_70bb.pkl", "taper42_12bb.pkl")
    touch(out, "nolimit_5bb.rung.json", "nolimit_5bb.compact.npz", "cap2_12bb.rung.json", "cap2_12bb.compact.npz",
          "cap2_70bb.rung.json", "cap2_70bb.compact.npz")
    _, built, _ = run.ladder_paths(str(source), deep_primary=True)
    return str(source), str(out), built


def test_without_the_links_the_runner_plays_a_different_set(ladders):
    source, out, _ = ladders
    # The bug of 5 October, reproduced: the cap2 rungs are dropped and nothing says so.
    _, ladder, _ = run.ladder_paths(out, deep_primary=True)
    assert not any(os.path.basename(p).startswith("cap2_") for p in ladder)
    with pytest.raises(SystemExit, match="different set"):
        build.same_set(run, source, out)


def test_the_links_make_the_runner_pick_the_source_set(ladders):
    source, out, built = ladders
    assert sorted(os.path.basename(p) for p in built if "cap2" in p) == ["cap2_12bb.pkl", "cap2_70bb.pkl"]
    links = build.write_runner_links(source, out, built)
    names = sorted(os.path.basename(p) for p in links)
    # The flat pair is linked only where the source has one.
    assert names == ["nolimit_12bb.flat.npz", "nolimit_12bb.flat.pkl", "nolimit_12bb.pkl", "nolimit_70bb.pkl"]
    for path in links:
        assert os.path.islink(path) and not os.path.isabs(os.readlink(path))
        assert os.path.realpath(path) == os.path.realpath(os.path.join(source, os.path.basename(path)))
    picked = build.same_set(run, source, out)
    assert "cap2_12bb.pkl" in picked[0] and "cap2_70bb.pkl" in picked[0] and "nolimit_5bb.pkl" in picked[0]
    # A one-raise rung that a cap2 rung replaced is a link only, not a rung the image would read.
    assert not os.path.exists(os.path.join(out, "nolimit_12bb.rung.json"))


def test_a_rebuild_replaces_its_own_links(ladders):
    source, out, built = ladders
    build.write_runner_links(source, out, built)
    os.remove(os.path.join(out, "nolimit_70bb.pkl"))
    os.symlink("elsewhere.pkl", os.path.join(out, "nolimit_70bb.pkl"))       # a stale link
    build.write_runner_links(source, out, built)
    assert os.readlink(os.path.join(out, "nolimit_70bb.pkl")) == os.path.relpath(
        os.path.join(source, "nolimit_70bb.pkl"), out)
    build.same_set(run, source, out)


def test_a_real_file_where_a_link_goes_stops_the_build(ladders):
    source, out, built = ladders
    touch(out, "nolimit_70bb.pkl")
    with pytest.raises(SystemExit, match="real file"):
        build.write_runner_links(source, out, built)
    with open(os.path.join(out, "nolimit_70bb.pkl")) as handle:
        assert handle.read() == "nolimit_70bb.pkl"                        # untouched


def test_a_cap2_rung_with_no_one_raise_rung_in_the_source_stops_the_build(ladders, tmp_path):
    source, out, _ = ladders
    stray = os.path.join(str(tmp_path), "cap2_35bb.pkl")
    with pytest.raises(SystemExit, match="no nolimit_35bb"):
        build.write_runner_links(source, out, [stray])


def test_a_rung_missing_from_the_build_is_caught(ladders):
    source, out, built = ladders
    build.write_runner_links(source, out, built)
    for suffix in (".rung.json", ".compact.npz"):
        os.remove(os.path.join(out, "cap2_70bb" + suffix))
    with pytest.raises(SystemExit, match="different set"):
        build.same_set(run, source, out)


def test_the_upload_leaves_the_links_out(ladders, tmp_path):
    source, out, built = ladders
    build.write_runner_links(source, out, built)
    target = str(tmp_path / "upload_ladder")
    package.copy_ladder(out, target)
    real = [n for n in os.listdir(out) if not os.path.islink(os.path.join(out, n))]
    assert sorted(os.listdir(target)) == sorted(real)                     # every file the builder wrote
    assert len(real) == 6 and not any(n.endswith(".pkl") for n in real)
    assert not any(n.startswith("nolimit_12bb") or n.startswith("nolimit_70bb") for n in os.listdir(target))
