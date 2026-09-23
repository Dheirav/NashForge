"""
Which opponent behaviours vary across the field, and which of them we read.

    venv/bin/python scripts/opponent_coverage.py

On 23 September wsp beat us on two hands. The number that decided the first
one, that it re-raises our open 5 times in 392 chances, was in
`results/chipzen/opponents.json` before the match and in memory during it:
`folds_blind` reads the fold count out of exactly that dictionary and nothing
read the raise count beside it. The loss was not missing information. It was
never having asked which of the information we hold is worth acting on.

This asks. For every profile we have, it computes a behavioural statistic,
reports its spread across the field, and marks whether any code path consumes
it. A statistic with a wide spread and no consumer is the next wsp: the field
varies in it, we cannot see it, and nothing will teach us until it costs a
match.

The spread that matters is not the range but the outlier distance: wsp's 1.3%
three-bet rate sits three times below the next lowest bot, which is what makes
it a different kind of opponent rather than a looser one. So each row reports
how far the furthest bot sits from the rest, in units of the interquartile
spread, and sorts by that.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

#: Every statistic we can compute, and the read that consumes it, if any. The
#: point of the table is the rows whose second column is empty.
STATISTICS = {
    "folds to a bet":            ("folds", "bets_faced", "never_folds"),
    "calls a bet":               ("calls", "bets_faced", "never_calls"),
    "raises a bet":              ("raises", "bets_faced", None),
    "three-bets our open":       ("preflop:Ur", "raise", "never_three_bets"),
    "folds its blind to an open": ("preflop:Ur", "fold", "folds_blind"),
    "calls our open":            ("preflop:Ur", "call", None),
    "folds to our three-bet":    ("preflop:TrUr", "fold", "folds_to_three_bet"),
    "opens when first to act":   ("preflop:", "raise", None),
    "checks the big blind back": ("preflop:Uc", "check", None),
    "bets the flop when checked to": ("flop:", "raise", None),
    "folds to a flop bet":       ("flop:Ur", "fold", None),
    "raises a flop bet":         ("flop:Ur", "raise", None),
    "folds to a turn bet":       ("turn:Ur", "fold", None),
    "raises a turn bet":         ("turn:Ur", "raise", None),
    "bets the river when checked to": ("river:", "raise", None),
    "folds to a river bet":      ("river:Ur", "fold", None),
    "raises a river bet":        ("river:Ur", "raise", None),
    "river bets that were bluffs": ("river_bluffs", "river_bets", "never_bluffs"),
    "big bets that were air":    ("big_bets_air", "big_bets", "big_bets_are_value"),
    "small bets that were air":  ("small_bets_air", "small_bets", "small_bets_called"),
}
MIN_SAMPLE = 60


def value(row: dict, spec) -> tuple:
    """The statistic as (rate, sample), or (None, 0) when the sample is too thin."""
    a, b, _ = spec
    if ":" in a:                                   # a by_history node
        node = (row.get("by_history") or {}).get(a, {})
        n = sum(node.values())
        return (node.get(b, 0) / n, n) if n >= MIN_SAMPLE else (None, n)
    n = row.get(b, 0)
    return (row.get(a, 0) / n, n) if n >= MIN_SAMPLE else (None, n)


def outlier_distance(values) -> float:
    """
    How far the furthest bot sits from the rest, in interquartile spreads.

    A range says the field is wide; this says one member is not in it, which is
    the shape of an opponent we have no machinery for.
    """
    v = np.asarray(sorted(values), dtype=float)
    if len(v) < 4:
        return 0.0
    q1, q3 = np.percentile(v, [25, 75])
    spread = max(q3 - q1, 1e-6)
    return float(max((q1 - v[0]) / spread, (v[-1] - q3) / spread))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profiles", default=os.path.join(ROOT, "results", "chipzen", "opponents.json"))
    parser.add_argument("--min-bots", type=int, default=5)
    args = parser.parse_args()

    rows = json.load(open(args.profiles))
    rows = rows.get("rows") or rows

    table = []
    for name, spec in STATISTICS.items():
        pairs = [(bot, value(row, spec)[0]) for bot, row in rows.items()]
        pairs = [(bot, v) for bot, v in pairs if v is not None]
        if len(pairs) < args.min_bots:
            continue
        values = [v for _, v in pairs]
        lo = min(pairs, key=lambda t: t[1])
        hi = max(pairs, key=lambda t: t[1])
        table.append((outlier_distance(values), name, spec[2], len(pairs), lo, hi))

    table.sort(reverse=True)
    print(f"{len(rows)} profiles, statistics with at least {args.min_bots} bots above a "
          f"{MIN_SAMPLE}-observation sample.\n")
    print("| outlier | statistic | read that consumes it | bots | lowest | highest |")
    print("|---|---|---|---|---|---|")
    for dist, name, read, n, lo, hi in table:
        mark = read or "**none**"
        print(f"| {dist:5.1f} | {name} | {mark} | {n} | {lo[0]} {100*lo[1]:.0f}% | {hi[0]} {100*hi[1]:.0f}% |")

    blind = [r for r in table if r[2] is None]
    print(f"\n{len(blind)} of {len(table)} statistics have no consumer. The ones to look at "
          f"are those with a large outlier distance: the field varies in them, one bot is "
          f"outside that variation, and nothing in the player can tell.")
    for dist, name, _, _, lo, hi in blind[:5]:
        print(f"  {dist:5.1f}  {name:32s} {lo[0]} at {100*lo[1]:.0f}%, {hi[0]} at {100*hi[1]:.0f}%")


if __name__ == "__main__":
    main()
