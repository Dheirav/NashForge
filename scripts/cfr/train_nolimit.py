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
from abstraction.buckets import CardAbstraction, preflop_key
from abstraction.equity import FULL_DECK  # noqa: E402
from cfr import MCCFRSolver, VANILLA  # noqa: E402
from cfr.play import (always_call_policy, play_hands, strategy_policy,
                      uniform_policy)  # noqa: E402
from games.nolimit import NoLimitHoldem  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iterations", type=int, default=3000)
    parser.add_argument("--buckets", type=int, default=6)
    #: An int is the uniform schedule (N raises, all four sizes). Two or more
    #: values taper: `--raise-cap 4 1` allows four sizes for the opening bet and
    #: only all-in for the raise, which buys a re-raise for 347,136 information
    #: sets where carrying all four sizes to depth 2 costs 7,560,240.
    parser.add_argument("--raise-cap", type=int, nargs="+", default=[1],
                        help="uniform depth, or a tapered schedule of sizes "
                             "per raise depth (e.g. --raise-cap 4 1)")
    parser.add_argument("--stack", type=int, default=200)
    parser.add_argument("--big-blind", type=int, default=2)
    parser.add_argument("--abstraction-samples", type=int, default=800)
    parser.add_argument("--equity-samples", type=int, default=40)
    parser.add_argument("--texture", action="store_true",
                        help="fold the board's flush and straight texture into the "
                             "postflop bucket (abstraction.buckets.board_texture)")
    parser.add_argument("--eval-hands", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", help="write the strategy and summary here")
    #: The C++ core, roughly 32x faster and answer-changing: bucketing is seeded
    #: from the cards rather than from Python's tuple hash. Default, with
    #: --no-native to fall back to the Python solver, which stays as the
    #: reference `tests/test_native.py` pins the port against.
    parser.add_argument("--native", action=argparse.BooleanOptionalAction,
                        default=True, help="use the C++ solver core")
    return parser.parse_args()


def _resident_mb():
    """This process's resident size, or 0 where /proc is unavailable."""
    try:
        with open("/proc/self/status") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return 0.0


def _write(path, strategy, abstraction, args, results, iterations, seconds):
    """The strategy and its summary, written together so neither outlives the other."""
    with open(path, "wb") as handle:
        pickle.dump({"strategy": strategy, "abstraction": abstraction,
                     "args": vars(args), "results": results}, handle)
    with open(os.path.splitext(path)[0] + ".json", "w") as handle:
        json.dump({"args": vars(args), "results": results,
                   "information_sets_reached": len(strategy),
                   "iterations_completed": iterations,
                   "seconds": seconds}, handle, indent=2)


def _native_tables(abstraction):
    """
    The fitted abstraction as flat tables the C++ solver takes.

    Handed over rather than refitted on the other side: k-means over sampled
    equities happens once and is cheap, and refitting in C++ would be a second
    clustering that could silently disagree with this one.
    """
    preflop = [0] * (52 * 52)
    for first in range(52):
        for second in range(52):
            if first != second:
                preflop[first * 52 + second] = abstraction._preflop[
                    preflop_key([FULL_DECK[first], FULL_DECK[second]])]
    return (preflop,
            list(abstraction._centroid_list["flop"]),
            list(abstraction._centroid_list["turn"]),
            list(abstraction._centroid_list["river"]))


def _train_native(args, abstraction, projected):
    """
    Train with the C++ core, then write the same pickle the Python path writes.

    Everything downstream -- `evaluation.benchmark`, the Slumbot bridge, the GUI
    -- reads that file and must not be able to tell which solver produced it.

    The native path CHANGES ANSWERS: bucketing is seeded from the cards rather
    than from Python's tuple hash, so a hand near a boundary can fall either
    side. The two were measured playing indistinguishably, 16.2 and 23.1 BB/100
    apart against random and always-call, but strategies from the two paths are
    not comparable with each other. See docs/retrain-plan.md.
    """
    import pokerbot_native

    schedule = ([4] * args.raise_cap if isinstance(args.raise_cap, int)
                else list(args.raise_cap))
    preflop, flop, turn, river = _native_tables(abstraction)

    print(f"\nTraining MCCFR (native) for {args.iterations:,} iterations...")
    solver = pokerbot_native.NoLimitSolver(
        preflop, flop, turn, river, args.equity_samples, args.stack,
        args.big_blind // 2, args.big_blind, schedule, args.seed,
        texture=bool(getattr(abstraction, "texture", False)))
    start = time.perf_counter()

    # Trained in chunks so the run reports progress.
    #
    # The native path printed nothing until it finished, which cost a run: the
    # [4,2] taper on 11 September spent 66 minutes swapping at 50% CPU and there
    # was no way to see it was in trouble, or how far along it was. The Python
    # path has had a progress callback since the 500,000-iteration run that was
    # killed at six hours for the same reason.
    step = max(1, args.iterations // 50)
    done = 0
    while done < args.iterations:
        chunk = min(step, args.iterations - done)
        solver.train(chunk)
        done += chunk
        taken = time.perf_counter() - start
        rss = _resident_mb()
        # ETA from the measured rate, never estimated up front.
        eta = (args.iterations - done) * taken / done / 60
        print(f"  {done:>10,}/{args.iterations:,}  {taken / done * 1000:6.3f} ms/it  "
              f"{solver.information_sets():>9,} infosets  {rss:6.0f} MB  "
              f"eta {eta:6.1f} min", flush=True)
    elapsed = time.perf_counter() - start
    print(f"  {elapsed:.1f}s ({elapsed / args.iterations * 1000:.3f} ms/iteration)")
    print(f"  information sets reached: {solver.information_sets():,} "
          f"of {projected.information_sets:,} in the abstraction")

    strategy = {key: np.asarray(value, dtype=np.float64)
                for key, value in solver.average_strategy().items()}

    # Scored and written exactly as the Python path does, through the same
    # Python game, so the file is indistinguishable downstream and the printed
    # baselines are comparable with every previous run's.
    game = NoLimitHoldem(abstraction, starting_stack=args.stack,
                         big_blind=args.big_blind, raise_cap=args.raise_cap,
                         equity_samples=args.equity_samples)
    _report_and_write(args, game, abstraction, strategy,
                      solver.information_sets(), elapsed)


def main():
    args = parse_args()
    # One value is the int the rest of the codebase has always taken; more than
    # one is a taper. Normalised here so `vars(args)` in the output JSON records
    # which game produced the strategy.
    args.raise_cap = (args.raise_cap[0] if len(args.raise_cap) == 1
                      else tuple(args.raise_cap))
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
        texture=args.texture,
    ).fit(rng)
    print(f"  fitted in {time.perf_counter() - start:.1f}s")
    print(abstraction.describe())

    game = NoLimitHoldem(abstraction, starting_stack=args.stack,
                         big_blind=args.big_blind, raise_cap=args.raise_cap,
                         equity_samples=args.equity_samples)

    if args.native:
        return _train_native(args, abstraction, projected)

    print(f"\nTraining MCCFR for {args.iterations:,} iterations...")
    solver = MCCFRSolver(game, rule=VANILLA, seed=args.seed)
    start = time.perf_counter()

    def checkpoint(done, total, live):
        """
        Report, and save what exists so far.

        Both halves are here because their absence cost a run: a 500,000
        iteration attempt was killed at six hours having printed nothing to
        size it by and written nothing to keep. Memory is the ceiling rather
        than time -- the abstraction's table is 4.7 MB and the solver's
        bookkeeping reached 4.9 GB -- so the resident size is reported too,
        being the number that predicts the ending.
        """
        taken = time.perf_counter() - start
        rss = _resident_mb()
        eta = (total - done) * taken / done / 60
        print(f"  {done:>8,}/{total:,}  {taken / done * 1000:5.1f} ms/it  "
              f"{len(live.nodes):>7,} infosets  {rss:6.0f} MB  "
              f"eta {eta:5.1f} min", flush=True)
        if args.output:
            # `<base>.partial.pkl`, so its summary lands beside it as
            # `<base>.partial.json` rather than colliding with the final one.
            _write(os.path.splitext(args.output)[0] + ".partial.pkl",
                   live.average_strategy(), abstraction, args, {}, done, taken)

    solver.train(args.iterations, on_progress=checkpoint,
                 progress_every=max(1, args.iterations // 50))
    elapsed = time.perf_counter() - start
    print(f"  {elapsed:.1f}s ({elapsed / args.iterations * 1000:.1f} ms/iteration)")
    print(f"  information sets reached: {len(solver.nodes):,} "
          f"of {projected.information_sets:,} in the abstraction")

    strategy = solver.average_strategy()
    _report_and_write(args, game, abstraction, strategy, len(solver.nodes), elapsed)


def _report_and_write(args, game, abstraction, strategy, information_sets, elapsed):
    """Score against the baselines and write the pickle, for either solver."""
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
                       "information_sets_reached": information_sets,
                       "seconds": elapsed}, handle, indent=2)
        print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
