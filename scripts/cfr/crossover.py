"""
Does the finer card abstraction ever repay its cost?

A made-hand bucketing is 5.4x cheaper per iteration than Monte Carlo equity and
provably blind to draws: on a two-heart board the nut flush draw and the same
overcards without it land in the same bucket. At small budgets that blindness
has never shown up — three separate measurements failed to find it, because the
extra iterations bought more than the lost information cost.

The obvious explanation is that the equity agent has a better map and no time to
read it. If so, its exploitability curve should fall faster and eventually cross
below the cheap signal's. This measures whether it does.

**The budget axis is wall-clock, not iterations.** "Given N seconds, which
should I use" is the question a practitioner faces. Measuring per iteration
would compare maps while ignoring that one takes five times longer to read, and
would favour equity by construction.

Exploitability is measured by Local Best Response, which is a lower bound: a
larger value proves more exploitable, a smaller one proves less about how close
to optimal a strategy is. Comparing two LBR figures under the same configuration
is the intended use.

Usage
-----
    python scripts/cfr/crossover.py
    python scripts/cfr/crossover.py --budgets 40 160 640 --seeds 3
"""
import argparse
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402

from abstraction.buckets import STRENGTH_SIGNALS, CardAbstraction  # noqa: E402
from cfr import MCCFRSolver, VANILLA, lbr_value  # noqa: E402
from games.nolimit import NoLimitHoldem  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--budgets", type=float, nargs="+", default=[40, 160, 640],
                        help="cumulative training seconds at which to measure")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--buckets", type=int, default=6)
    parser.add_argument("--raise-cap", type=int, default=1)
    parser.add_argument("--equity-samples", type=int, default=40)
    parser.add_argument("--lbr-hands", type=int, default=1000)
    parser.add_argument("--rollout-samples", type=int, default=20)
    parser.add_argument("--signals", nargs="+", default=list(STRENGTH_SIGNALS),
                        choices=list(STRENGTH_SIGNALS),
                        help="run only these signals; results merge into --output")
    parser.add_argument("--output", default="results/cfr/crossover.json")
    return parser.parse_args()


def save(path, payload):
    """Write results after every measurement.

    A long run that only writes at the end loses everything to an interruption —
    which is precisely what happened to the first attempt at this experiment.
    """
    tmp = path + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(tmp, path)


def load(path):
    """Any measurements already on disk, so a rerun resumes rather than repeats."""
    if os.path.exists(path):
        with open(path) as handle:
            return json.load(handle)
    return {}


def run_one(signal, seed, budgets, args, on_measurement=None):
    """Train to each budget in turn, measuring exploitability at each."""
    rng = np.random.default_rng(seed)
    abstraction = CardAbstraction(
        preflop_buckets=args.buckets, postflop_buckets=args.buckets,
        samples=800, equity_samples=args.equity_samples, strength=signal).fit(rng)
    game = NoLimitHoldem(abstraction, raise_cap=args.raise_cap,
                         equity_samples=args.equity_samples)
    solver = MCCFRSolver(game, rule=VANILLA, seed=seed)

    measurements = []
    spent = 0.0
    for budget in budgets:
        deadline = time.perf_counter() + (budget - spent)
        while time.perf_counter() < deadline:
            solver.train(25)
        spent = budget

        bound = lbr_value(game, solver.average_strategy(), hands=args.lbr_hands,
                          rng=np.random.default_rng(7000 + seed),
                          rollout_samples=args.rollout_samples)
        measurements.append({"budget": budget, "iterations": solver.iterations,
                             "lbr": bound.mean, "stderr": bound.stderr})
        print(f"      {signal:<10} seed {seed}  {budget:>6.0f}s  "
              f"{solver.iterations:>7,} iters  LBR {bound.mean:+.3f} "
              f"+/- {bound.stderr:.3f}", flush=True)
        if on_measurement is not None:
            on_measurement(signal, seed, measurements)
    return measurements


def main():
    args = parse_args()
    budgets = sorted(args.budgets)

    print("Exploitability against training budget, both bucketing signals.")
    print(f"{args.seeds} seeds, {args.lbr_hands} LBR hands per measurement.")
    print("Lower LBR is better. LBR is a lower bound on exploitability.\n")

    stored = load(args.output)
    raw = {k: v for k, v in stored.get("per_seed", {}).items()}

    def checkpoint(signal, seed, measurements):
        raw.setdefault(signal, {})
        raw[signal][str(seed)] = measurements
        save(args.output, {"args": vars(args), "per_seed": raw})

    for signal in args.signals:
        existing = raw.get(signal, {})
        for seed in range(args.seeds):
            if str(seed) in existing and len(existing[str(seed)]) == len(budgets):
                print(f"      {signal:<10} seed {seed}  already on disk, skipping",
                      flush=True)
                continue
            run_one(signal, seed, budgets, args, on_measurement=checkpoint)
        print()

    print(f"\n{'budget':>8}{'equity LBR':>22}{'made_hand LBR':>22}{'difference':>16}")
    print("-" * 68)

    summary = []
    for index, budget in enumerate(budgets):
        row = {"budget": budget}
        for signal in STRENGTH_SIGNALS:
            runs = list(raw.get(signal, {}).values())
            if not runs:
                row[signal] = {"mean": float("nan"), "stderr": float("nan"),
                               "iterations": 0}
                continue
            values = [run[index]["lbr"] for run in runs]
            errors = [run[index]["stderr"] for run in runs]
            row[signal] = {"mean": statistics.fmean(values),
                           "stderr": statistics.fmean(errors),
                           "iterations": statistics.fmean(
                               run[index]["iterations"] for run in runs)}

        gap = row["equity"]["mean"] - row["made_hand"]["mean"]
        noise = row["equity"]["stderr"] + row["made_hand"]["stderr"]
        row["gap"] = gap
        row["separated"] = abs(gap) > noise
        marker = ("equity ahead" if gap < 0 else "made_hand ahead") if row["separated"] \
            else "not separated"

        print(f"{budget:>7.0f}s{row['equity']['mean']:>14.3f} "
              f"+/-{row['equity']['stderr']:<6.3f}"
              f"{row['made_hand']['mean']:>14.3f} +/-{row['made_hand']['stderr']:<6.3f}"
              f"{marker:>16}")
        summary.append(row)

    print()
    crossed = [r for r in summary if r["gap"] < 0 and r["separated"]]
    if crossed:
        print(f"Crossover found: the equity abstraction is ahead from "
              f"{crossed[0]['budget']:.0f}s onward.")
    else:
        trend = [r["gap"] for r in summary]
        direction = ("narrowing" if len(trend) > 1 and trend[-1] < trend[0]
                     else "not narrowing")
        print(f"No crossover within {budgets[-1]:.0f}s. The gap is {direction} "
              f"({trend[0]:+.2f} -> {trend[-1]:+.2f}); a crossover, if it exists, "
              f"lies beyond the budgets tested.")

    save(args.output, {"args": vars(args), "per_seed": raw, "summary": summary})
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
