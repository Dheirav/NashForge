"""
Freeze the AIVAT value function: fit g's coefficients on matches played before the bursts it will score.

    venv/bin/python scripts/aivat_fit.py --matches-dir ~/Code/PokerBot/results/chipzen/matches \
        --before 2026-10-03T00:00 --progress /tmp/aivat_fit.progress

Kim and Sandholm's rule: a value function chosen after seeing the data it scores can tune the variance away, and
then the error bars mean nothing. So the coefficients come from older matches only, the file records which ones and
when, and its digest is what a ledger entry should quote. Any coefficients give an unbiased estimate; fitting only
decides how much luck they cancel. A control variate's best coefficient is the regression of the result on it, so
that is what is fitted: the hand's all-in adjusted net on pot * (equity change) and effective stack * (equity
change), one pair per street, no intercept because every feature has mean zero by construction.
"""
import argparse
import datetime
import glob
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation.aivat import STREETS, VALUE_FILE, ValueFunction, hand_terms, preflop_table, trace_hand  # noqa: E402
from scripts.chipzen_decompose import MATCHES, _ist, allin_spot, expected_net, hand_nets  # noqa: E402

BURSTS = ("v5xRR3 purified", "balanced-next", "v5xRR3s10 purified")


def match_rows(paths, before, exclude):
    for path in paths:
        with open(path) as handle:
            rows = [json.loads(line) for line in handle]
        if not rows or rows[0].get("frame") != "match_start" or "version" not in rows[0]:
            continue
        label = rows[0]["version"]["label"]
        if rows[0].get("at", 0) >= before or any(label.startswith(x) for x in exclude):
            continue
        yield path, rows


def features_of(rows, vf):
    """(features, base) per decision hand, the same base and terms aivat_hands builds."""
    seat = rows[0]["seat"]
    decisions = defaultdict(list)
    for r in rows:
        if "history" in r:
            decisions[r["hand"]].append(r)
    nets = hand_nets(rows, seat)
    out, before, hole = [], None, None
    for r in rows:
        if r.get("frame") == "round_start":
            before = (r.get("state") or {}).get("stacks")
            hole = (r.get("state") or {}).get("your_hole_cards")
        elif r.get("frame") == "round_result":
            res = r["result"]
            hand = res["hand_number"]
            ds = decisions.get(hand, [])
            if before and hole and hand in nets and ds:
                base, last = nets[hand], None
                spot = allin_spot(res, before, ds, seat)
                if spot is not None:
                    base, last = expected_net(spot), spot["street"]
                terms = hand_terms(vf, trace_hand(res, before, ds, seat, hole), last)
                x = np.zeros(2 * len(STREETS))
                for i, street in enumerate(STREETS):
                    x[2 * i:2 * i + 2] = terms["features"].get(street, (0.0, 0.0))
                out.append((x, base))
            before, hole = None, None
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matches-dir", nargs="+", default=[MATCHES])
    parser.add_argument("--before", default="2026-10-03T00:00", help="IST; only matches that started earlier")
    parser.add_argument("--exclude", nargs="*", default=list(BURSTS), help="label prefixes never fitted on")
    parser.add_argument("--out", default=VALUE_FILE)
    parser.add_argument("--table", help="reuse the preflop table of an existing value file instead of sampling it")
    parser.add_argument("--progress", help="a file rewritten after every match: done, total, elapsed, ETA")
    args = parser.parse_args()

    if args.table:
        with open(args.table) as handle:
            table = json.load(handle)["preflop_equity"]
    else:
        t = time.time()
        table = preflop_table()
        print(f"preflop table: 169 classes in {time.time() - t:.0f} s", flush=True)
    vf = ValueFunction.checkdown(table)

    paths = sorted(p for d in args.matches_dir for p in glob.glob(os.path.join(d, "*.jsonl")))
    matches = list(match_rows(paths, _ist(args.before), args.exclude))
    X, y, start = [], [], time.time()
    for k, (path, rows) in enumerate(matches, 1):
        for x, base in features_of(rows, vf):
            X.append(x)
            y.append(base)
        if args.progress:
            elapsed = time.time() - start
            eta = elapsed / k * (len(matches) - k)
            with open(args.progress, "w") as handle:
                handle.write(f"{k} of {len(matches)} matches, {len(y)} hands, elapsed {elapsed / 60:.1f} min, "
                             f"ETA {eta / 60:.1f} min at the measured rate\n")
    X, y = np.array(X), np.array(y, dtype=float)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    fitted = X @ coef
    resid = y - fitted
    # Coefficient standard errors under the usual homoscedastic reading; rough, since the residuals are heavy tailed.
    cov = np.linalg.pinv(X.T @ X) * resid.var()
    se = np.sqrt(np.diag(cov))
    coefficients = {s: [float(coef[2 * i]), float(coef[2 * i + 1])] for i, s in enumerate(STREETS)}
    checkdown_resid = y - X @ np.tile([1.0, 0.0], len(STREETS))
    provenance = {
        "fitted": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).isoformat(
            timespec="minutes"),
        "matches_before_ist": args.before, "excluded_labels": args.exclude, "matches": len(matches),
        "hands": int(len(y)), "coefficient_se": {s: [float(se[2 * i]), float(se[2 * i + 1])]
                                                  for i, s in enumerate(STREETS)},
        "sd_per_hand": {"base": float(y.std()), "fitted_residual": float(resid.std()),
                        "checkdown_residual": float(checkdown_resid.std())},
    }
    data = {"name": "fitted g, matches before " + args.before + " IST",
            "form": "v = (a * pot + b * effective stack) * (equity vs random - 1/2); fold: -our contribution",
            "coefficients": coefficients, "preflop_equity": table, "provenance": provenance}
    with open(args.out, "w") as handle:
        json.dump(data, handle, indent=1, sort_keys=True)
    print(json.dumps({"coefficients": coefficients, **provenance}, indent=1))
    print(f"wrote {args.out}, digest {ValueFunction.load(args.out).digest}")


if __name__ == "__main__":
    main()
