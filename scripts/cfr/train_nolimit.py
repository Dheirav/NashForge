"""
Milestone 5 — train a CFR agent on abstracted heads-up no-limit Hold'em.

Fits a card abstraction, runs external-sampling MCCFR over the abstracted game,
and measures the resulting strategy against baselines by playing hands.

Two honest limits on what this can report, both stated rather than papered over:

* **Exploitability is not computable here.** Kuhn and Leduc allow an exact best
  response; no-limit does not. Local Best Response gives a lower bound and is
  the next piece of work. Until then the only measure available is head-to-head
  chips, which is a weaker claim: beating a passive baseline shows the strategy
  is not broken, not that it is near equilibrium.

* **Head-to-head results need error bars.** Poker results over a few thousand
  hands are dominated by variance. Every figure below carries a standard error
  and a 95% interval, and seats alternate so position is not a confound.

Usage
-----
    python scripts/cfr/train_nolimit.py
    python scripts/cfr/train_nolimit.py --iterations 20000 --buckets 8
    python scripts/cfr/train_nolimit.py --raise-cap 2 --output strategy.npz
"""
import argparse
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402

from abstraction.betting import STREETS, measure  # noqa: E402
from abstraction.buckets import CardAbstraction  # noqa: E402
from cfr import MCCFRSolver, VANILLA  # noqa: E402
from cfr.play import (always_call_policy, play_hands, strategy_policy,
                      uniform_policy)  # noqa: E402
from games.nolimit import NoLimitHoldem  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iterations", type=int, default=3000)
    parser.add_argument("--buckets", type=int, default=6)
    parser.add_argument("--raise-cap", type=int, default=1)
    parser.add_argument("--stack", type=int, default=200)
    parser.add_argument("--big-blind", type=int, default=2)
    parser.add_argument("--abstraction-samples", type=int, default=800)
    parser.add_argument("--equity-samples", type=int, default=40)
    parser.add_argument("--eval-hands", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", help="write the strategy and summary here")
    return parser.parse_args()


def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)

    projected = measure({street: args.buckets for street in STREETS},
                        raise_cap=args.raise_cap)
    print(f"Abstract game: {projected.summary()}")
    print(f"  (raise cap is the parameter that decides feasibility — see "
          f"measure_abstraction.py)\n")

    print(f"Fitting card abstraction ({args.abstraction_samples} situations/street)...")
    start = time.perf_counter()
    abstraction = CardAbstraction(
        preflop_buckets=args.buckets, postflop_buckets=args.buckets,
        samples=args.abstraction_samples, equity_samples=args.equity_samples,
    ).fit(rng)
    print(f"  fitted in {time.perf_counter() - start:.1f}s")
    print(abstraction.describe())

    game = NoLimitHoldem(abstraction, starting_stack=args.stack,
                         big_blind=args.big_blind, raise_cap=args.raise_cap,
                         equity_samples=args.equity_samples)

    print(f"\nTraining MCCFR for {args.iterations:,} iterations...")
    solver = MCCFRSolver(game, rule=VANILLA, seed=args.seed)
    start = time.perf_counter()
    solver.train(args.iterations)
    elapsed = time.perf_counter() - start
    print(f"  {elapsed:.1f}s ({elapsed / args.iterations * 1000:.1f} ms/iteration)")
    print(f"  information sets reached: {len(solver.nodes):,} "
          f"of {projected.information_sets:,} in the abstraction")

    strategy = solver.average_strategy()
    trained = strategy_policy(strategy)

    print(f"\nHead-to-head over {args.eval_hands:,} hands, seats alternating.")
    print("Positive means the trained strategy is winning.\n")

    results = {}
    for name, opponent in (("uniform random", uniform_policy()),
                           ("always call", always_call_policy())):
        outcome = play_hands(game, [trained, opponent], args.eval_hands,
                             np.random.default_rng(args.seed + 1))
        per_100_bb = outcome.mean / args.big_blind * 100
        print(f"  vs {name:<15} {outcome.summary()}")
        print(f"  {'':<18} = {per_100_bb:+.1f} BB/100")
        results[name] = {
            "chips_per_hand": outcome.mean,
            "stderr": outcome.stderr,
            "ci95": list(outcome.ci95),
            "bb_per_100": per_100_bb,
            "separated_from_zero": outcome.separated_from_zero,
        }

    print("\nNote: head-to-head chips is a weaker claim than exploitability.")
    print("Beating a passive baseline shows the strategy is not broken; it does")
    print("not show it is near equilibrium. LBR is the next piece of work.")

    if args.output:
        with open(args.output, "wb") as handle:
            pickle.dump({"strategy": strategy, "abstraction": abstraction,
                         "args": vars(args), "results": results}, handle)
        with open(os.path.splitext(args.output)[0] + ".json", "w") as handle:
            json.dump({"args": vars(args), "results": results,
                       "information_sets_reached": len(solver.nodes),
                       "seconds": elapsed}, handle, indent=2)
        print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
