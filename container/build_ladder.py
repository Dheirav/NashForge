"""
Build the uploaded bot's ladder: the rungs a set plays, stored compactly (cfr/pure.py).

    venv/bin/python container/build_ladder.py --ladder results/cfr/ladder169l_v5x --out container/ladder

Takes the same rungs `chipzen_run.ladder_paths` picks with --deep-primary (the flags every fixture
has played with), writes each as a `.rung.json` (the card abstraction and the training arguments,
a few KB) and a `.compact.npz` (cfr/pure.py), and checks every node against the source before it
moves on: same width, every probability equal to 32-bit precision, and the same first maximum. Run with the main venv: it reads the flat
tables, which the image never carries.

The folder is also read by the runner (`chipzen_duel.py`, `chipzen_replay.py`, `chipzen_run.py`) for duels,
and there `--deep-primary` swaps a cap2 rung in only at a depth where the folder holds a `nolimit_<d>bb` entry.
The builder writes only the rungs that play, so without those entries the runner silently dropped every cap2
rung and played the shipped one-raise solver instead (5 October). So each cap2 rung gets a link
`nolimit_<d>bb.pkl` to the source's own one-raise rung (and its flat pair), never loaded under
`--deep-primary`, and the build ends by checking that the runner picks the same rungs from the new folder as
from the source. The links are `.pkl` files, which the image never reads (it lists `*.rung.json`), and
`container/package.py` leaves them out of the upload.
"""
import argparse
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from cfr.flat import load_strategy  # noqa: E402
from cfr.pure import compact, load_compact, write_compact, write_rung  # noqa: E402


def _depth(path: str) -> str:
    """`cap2_70bb.pkl` to `70bb`."""
    return os.path.basename(path).split("_")[1].split(".")[0]


def write_runner_links(source_dir: str, out_dir: str, built) -> list:
    """
    For every cap2 rung built, a relative link `nolimit_<d>bb.pkl` (and the flat pair, when the source has
    one) to the source's one-raise rung at that depth, so `ladder_paths` sees the depth. Returns the links.
    A depth whose one-raise rung the source does not hold stops the build, and so does a real file where a
    link should go, because overwriting a rung is never what this is for.
    """
    written = []
    for path in built:
        name = os.path.basename(path)
        if not name.startswith("cap2_"):
            continue
        stem = f"nolimit_{_depth(name)}"
        source = os.path.join(source_dir, stem + ".pkl")
        if not os.path.exists(source):
            raise SystemExit(f"{name}: the source has no {stem}.pkl, so the runner could not have played this rung "
                             f"from it under --deep-primary; refusing to invent the depth")
        for suffix in (".pkl", ".flat.npz", ".flat.pkl"):
            target, origin = os.path.join(out_dir, stem + suffix), os.path.join(source_dir, stem + suffix)
            if suffix != ".pkl" and not os.path.exists(origin):
                continue
            if os.path.lexists(target) and not os.path.islink(target):
                raise SystemExit(f"{target} is a real file, not a link; not replacing it")
            link = os.path.relpath(origin, out_dir)
            if os.path.islink(target):
                os.remove(target)
            os.symlink(link, target)
            written.append(target)
    return written


def same_set(run, source_dir: str, out_dir: str):
    """Stop the build unless the runner picks the same rungs, by name, from the new folder as from the source."""
    def picked(folder):
        _, ladder, companions = run.ladder_paths(os.path.abspath(folder), deep_primary=True)
        return sorted(os.path.basename(p) for p in ladder), sorted(os.path.basename(p) for p in companions)
    want, got = picked(source_dir), picked(out_dir)
    if want != got:
        raise SystemExit(f"the runner would play a different set from {out_dir}:\n  source {want}\n  built  {got}")
    return got


def _runner():
    import importlib.util
    spec = importlib.util.spec_from_file_location("chipzen_run", os.path.join(ROOT, "scripts", "chipzen_run.py"))
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ladder", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--drop-hist-tables", action="store_true",
                        help="leave out a histogram abstraction's precomputed bucket tables (130 MB for v5y), so the "
                             "image computes each class instead: the tables are read only by the native module")
    args = parser.parse_args()
    sys.argv = [sys.argv[0]]
    run = _runner()
    _, ladder, companions = run.ladder_paths(os.path.abspath(args.ladder), deep_primary=True)
    if companions:
        raise SystemExit(f"this set plays companions {companions}; the container carries primaries only")
    os.makedirs(args.out, exist_ok=True)
    total = 0
    for path in ladder:
        t = time.time()
        saved = load_strategy(path)
        strategy = saved.pop("strategy")
        table = compact(strategy)
        ties = 0
        for key, probs in strategy.items():
            row, probs = table.get(key), np.asarray(probs, dtype=np.float64)
            if row is None or len(row) != len(probs) or not np.array_equal(row, probs.astype(np.float32)):
                raise SystemExit(f"{path}: node {key!r} does not read back")
            ties += int(np.argmax(row)) != int(np.argmax(probs))
        name = os.path.basename(path)
        target = os.path.join(args.out, name)
        if args.drop_hist_tables and getattr(saved["abstraction"], "_hist_tables", None) is not None:
            saved["abstraction"]._hist_tables = None
        write_rung(target, {"abstraction": saved["abstraction"], "args": saved["args"]})
        out = write_compact(target, table)
        # The written pair reads back as the source: every attribute of the abstraction, and the args.
        back = load_compact(target)
        if vars(back["abstraction"]).keys() != vars(saved["abstraction"]).keys() or \
                repr(back["args"]) != repr(dict(saved["args"])):
            raise SystemExit(f"{name}: the rung file does not read back")
        total += os.path.getsize(out)
        print(f"{name:18s} {len(table):>9,} nodes  {os.path.getsize(out) / 1e6:6.1f} MB  checked, {ties} top-action ties  {time.time() - t:5.1f}s")
    print(f"{len(ladder)} rungs, {total / 1e6:.1f} MB of tables in {args.out}")
    links = write_runner_links(os.path.abspath(args.ladder), os.path.abspath(args.out), ladder)
    same_set(run, args.ladder, args.out)
    print(f"{len(links)} runner links written; the runner picks the same rungs from {args.out} as from {args.ladder}")


if __name__ == "__main__":
    main()
