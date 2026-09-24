"""
Local Best Response against the rungs we actually play.

    venv/bin/python scripts/lbr_ladder.py --rungs 70bb 100bb --hands 2000

Exploitability is the measure that matters and we have never had one for the
arena ladder. `cfr/lbr.py` has implemented LBR (Lisy and Bowling 2017) since
early September and the only run on record, `results/cfr/lbr_valuation_remeasure.json`,
was against solvers with 25,089 information sets. v5i's 70bb rung has 1,170,732.
So every improvement argued about this week was argued without knowing where
the blueprint leaks.

Read the sign carefully, because it is asymmetric. A clearly positive number
proves the rung is exploitable by at least that much, and the bet sizes that
produced it say where. A number near zero proves nothing at all: it means this
particular greedy exploiter failed, not that the rung is near equilibrium. A
negative number means the bound is slack and the run was wasted.

The opponent bets sizes that sit between ours on purpose, which is the attack
our pseudo-harmonic translation is supposed to absorb and which nothing has
ever pointed at us.
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cfr.flat import load_strategy  # noqa: E402
from cfr.lbr import lbr_value  # noqa: E402
from games.nolimit import NoLimitHoldem  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
#: Sizes that fall between the abstraction's, the way Modicum's LBR opponent
#: bet 0.33 x 2^x of the pot to sit inside the gaps.
BETWEEN = (0.33, 0.66, 1.33, 2.66, 5.33)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ladder", default=os.path.join(ROOT, "results", "cfr", "ladder169l_v5i"))
    parser.add_argument("--rungs", nargs="+", default=["70bb"])
    parser.add_argument("--hands", type=int, default=2000)
    parser.add_argument("--rollout-samples", type=int, default=60)
    parser.add_argument("--candidates", type=int, default=32)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--between-sizes", action="store_true",
                        help="give the exploiter sizes that sit between ours, the translation attack")
    parser.add_argument("--out", default=os.path.join(ROOT, "results", "cfr", "lbr_ladder.json"))
    args = parser.parse_args()

    rows = {}
    for rung in args.rungs:
        matches = [p for p in glob.glob(os.path.join(args.ladder, f"*_{rung}.pkl")) if ".flat." not in p]
        if not matches:
            print(f"{rung}: not in {args.ladder}")
            continue
        # A ladder directory holds both the cap-2 rungs the bot plays under
        # --deep-primary and the older one-raise `nolimit_*` solves beside them.
        # Taking the first match measured nolimit_70bb.pkl, 131,693 information
        # sets, when v5i's 70bb rung has 1,170,732: an exploitability number for
        # a solver we retired. Prefer what the bot actually plays, and say so.
        matches.sort(key=lambda q: (not os.path.basename(q).startswith("cap2_"), q))
        path = matches[0]
        if len(matches) > 1:
            others = ", ".join(os.path.basename(q) for q in matches[1:])
            print(f"{rung}: using {os.path.basename(path)} (also present: {others})")
        saved = load_strategy(path)
        saved_args = saved["args"]
        cap = saved_args["raise_cap"]
        cap = tuple(cap) if isinstance(cap, (list, tuple)) else cap
        game = NoLimitHoldem(saved["abstraction"], starting_stack=int(saved_args["stack"]),
                             small_blind=int(saved_args["big_blind"]) // 2,
                             big_blind=int(saved_args["big_blind"]), raise_cap=cap,
                             equity_samples=int(saved_args.get("equity_samples", 200)))
        started = time.perf_counter()
        kwargs = {}
        if args.between_sizes:
            kwargs["bet_sizes"] = BETWEEN
        result = lbr_value(game, saved["strategy"], hands=args.hands,
                           rng=np.random.default_rng(args.seed),
                           rollout_samples=args.rollout_samples,
                           candidates=args.candidates, **kwargs)
        elapsed = time.perf_counter() - started
        big_blind = int(saved_args["big_blind"])
        rows[rung] = {"path": os.path.basename(path), "mean": result.mean, "stderr": result.stderr,
                      "ci95": list(result.ci95), "proves_exploitable": bool(result.proves_exploitable),
                      "hands": args.hands, "bb_per_100": 100.0 * result.mean / big_blind,
                      "between_sizes": bool(args.between_sizes), "seconds": round(elapsed, 1),
                      "information_sets": len(saved["strategy"])}
        print(f"{rung}: {result.summary()}")
        print(f"   {100.0 * result.mean / big_blind:+.1f} BB/100, {len(saved['strategy']):,} information sets, "
              f"{elapsed / 60:.1f} min")
        if not result.proves_exploitable:
            print("   the bound is slack: this says LBR failed, not that the rung is sound")

    if rows:
        with open(args.out, "w") as handle:
            json.dump(rows, handle, indent=1)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
