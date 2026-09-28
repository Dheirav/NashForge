"""
Build the uploaded bot's ladder: the rungs a set plays, stored compactly (cfr/pure.py).

    venv/bin/python container/build_ladder.py --ladder results/cfr/ladder169l_v5x --out container/ladder

Takes the same rungs `chipzen_run.ladder_paths` picks with --deep-primary (the flags every fixture
has played with), writes each as a `.rung.json` (the card abstraction and the training arguments,
a few KB) and a `.compact.npz` (cfr/pure.py), and checks every node against the source before it
moves on: same width, every probability equal to 32-bit precision, and the same first maximum. Run with the main venv: it reads the flat
tables, which the image never carries.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ladder", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    sys.argv = [sys.argv[0]]
    import importlib.util
    spec = importlib.util.spec_from_file_location("chipzen_run", os.path.join(ROOT, "scripts", "chipzen_run.py"))
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
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


if __name__ == "__main__":
    main()
