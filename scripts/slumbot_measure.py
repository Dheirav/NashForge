"""
M1 — the first number in this project that somebody else's agent produced.

Step 5 of `docs/EXTERNAL_BENCHMARK.md`. Every strength figure here was computed by
this project about itself, and item 1 closed with no usable bound, so no-limit has
no exploitability figure at all. This does not fix that. It produces one measured
result against a fixed, external, published opponent, which is the whole of what
M1 claims: *10,000 hands with a confidence interval, any result*.

Two estimators, and why the headline is the dull one
-----------------------------------------------------
Slumbot returns `baseline_winnings` beside the actual winnings on every hand. On
the 300-hand pilot the two correlate at 0.85, and differencing them cuts the
spread from 2169 chips to 1362 — a real variance reduction, worth about 1.6x in
hands.

It is not the headline, because **the two estimators disagree in sign**: the pilot
read +130.7 chips/hand raw and −80.5 differenced. What `baseline_winnings` means
is not documented anywhere this project can check, so treating the difference as
the answer is an unverified modelling choice that moves the result across zero.
Item 1's cap-2 row is the precedent — +2.783 one afternoon and −2.900 that
evening, same untouched strategy, only the exploiter's valuation changed.

So the raw win rate is reported as the result, the differenced one is reported
beside it as an alternative whose interpretation is unverified, and neither is
quietly preferred to the other.

What is being measured, stated plainly
---------------------------------------
A 100bb, one-raise-per-street solver playing a 200bb unlimited-raise opponent. It
is not this project's strength at Slumbot's game and must not be quoted as though
it were. The lookup miss rate comes back with the result for the same reason the
panel reports it.

Usage
-----
    venv/bin/python scripts/slumbot_measure.py --hands 10000
"""
import argparse
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

import numpy as np

from slumbot import SlumbotError, play_hand
from slumbot.api import BIG_BLIND
from slumbot.player import SolverPlayer

STRATEGY = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")
OUT = os.path.join(ROOT, "results", "slumbot")

#: M1's bar. Below it the interval is wide enough that the number says nothing.
M1_HANDS = 10_000


def interval(values):
    """Mean and 95% half-width in mbb/hand, from chips per hand."""
    series = np.asarray(values, dtype=float)
    mean = series.mean() / BIG_BLIND * 1000
    half = 1.96 * series.std(ddof=1) / np.sqrt(len(series)) / BIG_BLIND * 1000
    return mean, half


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hands", type=int, default=M1_HANDS)
    parser.add_argument("--seed", type=int, default=20260820)
    parser.add_argument("--out", default=os.path.join(OUT, "m1.json"))
    #: Which solver is playing. There are two now -- the 4,000-iteration one
    #: that shipped and a 150,000-iteration one that beats it head to head by
    #: 185 BB/100 -- and a result that does not say which produced it cannot be
    #: compared with the other.
    parser.add_argument("--strategy", default=STRATEGY)
    args = parser.parse_args()

    if args.hands < M1_HANDS:
        parser.error(f"M1 is {M1_HANDS:,} hands; fewer is a pilot, and "
                     "scripts/slumbot_pilot.py is the script that does not "
                     "report a result")

    player = SolverPlayer(args.strategy, np.random.default_rng(args.seed))
    winnings, baseline, positions = [], [], Counter()
    errors, token, started = [], None, time.time()

    print(f"M1 — {args.hands:,} hands against Slumbot, seed {args.seed}")
    print(f"strategy: {os.path.basename(args.strategy)}")
    print("100bb one-raise solver against a 200bb unlimited-raise opponent\n",
          flush=True)

    for index in range(args.hands):
        try:
            state = play_hand(player, token)
            token = state.token
            winnings.append(state.winnings)
            baseline.append(state.baseline_winnings)
            positions[state.client_pos] += 1
        except SlumbotError as error:
            errors.append(f"hand {index + 1}: {error}")
        if (index + 1) % 500 == 0:
            done = index + 1
            rate = done / (time.time() - started)
            mean, half = interval(winnings)
            print(f"  {done:>6,}/{args.hands:,}  {rate:4.1f} hands/s  "
                  f"eta {(args.hands - done) / rate / 60:5.1f} min  "
                  f"[{mean:+7.0f} ± {half:.0f} mbb/hand so far]", flush=True)

    report(player, winnings, baseline, positions, errors, args,
           time.time() - started)


def report(player, winnings, baseline, positions, errors, args, elapsed):
    stats = player.stats
    raw_mean, raw_half = interval(winnings)

    usable = [w - b for w, b in zip(winnings, baseline) if b is not None]
    adj_mean, adj_half = interval(usable) if len(usable) > 1 else (None, None)

    print(f"\n{'=' * 64}")
    print(f"M1 — {len(winnings):,} hands in {elapsed / 60:.0f} min\n")
    print(f"  win rate            {raw_mean:+8.1f} ± {raw_half:.0f} mbb/hand")
    print(f"                      95% interval "
          f"[{raw_mean - raw_half:+.0f}, {raw_mean + raw_half:+.0f}]")
    if adj_mean is not None:
        print(f"\n  differenced against Slumbot's baseline, interpretation")
        print(f"  unverified — NOT the result:")
        print(f"                      {adj_mean:+8.1f} ± {adj_half:.0f} mbb/hand")
        if (raw_mean > 0) != (adj_mean > 0):
            print("    The two estimators disagree in sign. Neither is quoted")
            print("    alone, and the raw figure above is the reported one.")

    print(f"\n  lookup miss rate    {stats.miss_rate:.1%} "
          f"({stats.misses}/{stats.consulted})")
    print(f"  off-abstraction     {stats.off_abstraction}")
    print(f"  seats               {dict(positions)}")
    print(f"  protocol errors     {len(errors)}")
    print(f"\n  Measures a 100bb one-raise-per-street solver against a 200bb")
    print(f"  unlimited-raise opponent. Not this project's strength at")
    print(f"  Slumbot's game.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as handle:
        json.dump({
            "milestone": "M1",
            "strategy": os.path.basename(args.strategy),
            "hands": len(winnings),
            "seed": args.seed,
            "units": "mbb/hand",
            "win_rate": raw_mean, "ci95": raw_half,
            "baseline_differenced": adj_mean,
            "baseline_differenced_ci95": adj_half,
            "baseline_note": "Slumbot's baseline_winnings differenced from "
                             "actual. Interpretation unverified; not the "
                             "reported result.",
            "lookup_miss_rate": stats.miss_rate,
            "off_abstraction": stats.off_abstraction,
            "seats": dict(positions),
            "protocol_errors": errors,
            "caveat": "100bb one-raise-per-street solver against a 200bb "
                      "unlimited-raise opponent; not this project's strength "
                      "at Slumbot's game.",
            "elapsed_seconds": elapsed,
        }, handle, indent=1)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
