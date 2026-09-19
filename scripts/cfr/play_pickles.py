"""
Two solver pickles, head to head, in chips.

    venv/bin/python scripts/cfr/play_pickles.py A.pkl B.pkl --hands 40000 --seeds 0 1 2

Each agent buckets with its own abstraction and both walk the same betting
tree, so this is the clean comparison for a change to the *card* abstraction:
sample count, bucket count, centroids. It is not the comparison for a change
to the betting tree, where the coarser agent has no entries for the richer
one's histories and the result mostly measures its fallback.

Reported as BB/100 to the first pickle with the standard error across seeds,
because a chip count over a few thousand hands is variance, and 40,000 hands
against the same opponent gives roughly ±13 BB/100 here. Seats alternate
inside `benchmark`.
"""
import argparse
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402

from cfr.flat import load_strategy  # noqa: E402
from evaluation.benchmark import benchmark, cfr_agent  # noqa: E402


def load(path, seed, raise_cap, on_miss="random"):
    saved = load_strategy(path)
    args = saved.get("args") or {}
    cap = args.get("raise_cap", raise_cap) if isinstance(args, dict) else raise_cap
    cap = tuple(cap) if isinstance(cap, (list, tuple)) else int(cap)
    misses = [0, 0]
    return cfr_agent(saved["strategy"], saved["abstraction"], np.random.default_rng(seed),
                     misses=misses, raise_cap=cap, on_miss=on_miss), cap, len(saved["strategy"]), misses


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("first")
    parser.add_argument("second")
    parser.add_argument("--hands", type=int, default=40000)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--raise-cap", type=int, default=1, help="if the pickle does not say")
    parser.add_argument("--on-miss", default="random", choices=["random", "call"],
                        help="what a lookup miss plays; `call` for a cross-tree gate, where a "
                             "random shove on an unvisited line measures the fallback, not the solve")
    parser.add_argument("--output")
    args = parser.parse_args()

    scores = []
    miss_rates = []
    for seed in args.seeds:
        a, cap_a, n_a, miss_a = load(args.first, seed, args.raise_cap, args.on_miss)
        b, cap_b, n_b, miss_b = load(args.second, seed + 1000, args.raise_cap, args.on_miss)
        if seed == args.seeds[0]:
            print(f"{os.path.basename(args.first)}: {n_a:,} infosets, cap {cap_a}; "
                  f"{os.path.basename(args.second)}: {n_b:,} infosets, cap {cap_b}; on miss: {args.on_miss}", flush=True)
        started = time.perf_counter()
        result = benchmark(a, b, os.path.basename(args.second), hands=args.hands, seed=seed)
        scores.append(result.bb_per_100)
        miss_rates.append((miss_a[0] / max(1, miss_a[1]), miss_b[0] / max(1, miss_b[1])))
        print(f"  seed {seed}: {result.bb_per_100:+8.1f} BB/100 to the first, "
              f"{args.hands:,} hands in {(time.perf_counter() - started) / 60:.1f} min; "
              f"misses {100 * miss_rates[-1][0]:.2f}% / {100 * miss_rates[-1][1]:.2f}% of decisions", flush=True)

    mean = float(np.mean(scores))
    stderr = float(np.std(scores, ddof=1)) / len(scores) ** 0.5 if len(scores) > 1 else float("nan")
    print(f"\n{os.path.basename(args.first)} vs {os.path.basename(args.second)}: "
          f"{mean:+.1f} ± {stderr:.1f} BB/100 (SE across {len(scores)} seeds, {args.hands:,} hands each)")
    if args.output:
        with open(args.output, "w") as handle:
            json.dump({"first": args.first, "second": args.second, "hands": args.hands,
                       "seeds": args.seeds, "bb_per_100": scores, "mean": mean, "stderr": stderr,
                       "on_miss": args.on_miss,
                       "miss_rate": [float(np.mean([m[0] for m in miss_rates])),
                                     float(np.mean([m[1] for m in miss_rates]))],
                       "measured": time.strftime("%Y-%m-%d %H:%M")}, handle, indent=1)
        print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
