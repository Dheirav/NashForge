"""
Fit the data-driven copies the duels play as `datacopy:<table.json>` (chipzen/datacopy.py) from the scout cache.

    venv/bin/python scripts/fit_data_copy.py --names Shadow Blueprint --out ~/pokerbot-scratch/datacopies
    venv/bin/python scripts/fit_data_copy.py --names Shadow --until 2026-10-01T00:00 --out DIR    # train on the earlier matches

A table is the bot's action counts by situation and hand strength, its raise-size counts, and the field's counts for
the back-off; see chipzen/datacopy.py for why this replaces the archetype copies for anything but a station.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from chipzen.datacopy import build_table  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--names", nargs="+", required=True)
    parser.add_argument("--scout-dir", default=os.path.join(ROOT, "results", "chipzen", "scout"))
    parser.add_argument("--until", help="only matches up to this ISO time (the training half of a validation)")
    parser.add_argument("--since", help="only matches from this ISO time (a bot that changed: Blueprint since 2026-10-01)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for name in args.names:
        table = build_table(name, args.scout_dir, until=args.until, since=args.since)
        path = os.path.join(args.out, f"{name}.json")
        with open(path, "w") as handle:
            json.dump(table, handle)
        print(f"{name}: {table['decisions']:,} decisions -> {path}")


if __name__ == "__main__":
    main()
