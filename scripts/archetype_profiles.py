"""
Profile rows for the archetypes, counted by the scout's own code, so a read can be tested against them.

    venv/bin/python scripts/archetype_profiles.py --out results/chipzen/archetype_profiles.json

A read fires from a row in `results/chipzen/opponents.json`, and an archetype has no row, so in a duel
against one every read is silent. This plays each archetype against v5i the way `chipzen_calibrate.py`
does, runs `chipzen_scout.profile` over the recorded hands, and writes the rows in the shape
`chipzen_scout.py --seed-profiles` writes them. Then a duel with `--profiles <out>` and
`--b-label <archetype>` reads the archetype the way a match reads a scouted bot.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chipzen.archetypes import ARCHETYPES, build_archetype  # noqa: E402
from scripts.chipzen_calibrate import play_recorded  # noqa: E402
from scripts.chipzen_duel import build  # noqa: E402
from scripts.chipzen_scout import profile  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kinds", nargs="+", default=list(ARCHETYPES))
    parser.add_argument("--matches", type=int, default=300)
    parser.add_argument("--ladder", default=os.path.expanduser("~/Code/PokerBot/results/cfr/ladder169l_v5i"))
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    opponent = build(args.ladder, "--deep-primary --stack-cap", "v5i", np.random.default_rng(args.seed), None)
    rows = {}
    for kind in args.kinds:
        arch = build_archetype(kind, np.random.default_rng(args.seed + 1))
        matches, hands = play_recorded([opponent, arch], np.random.default_rng(args.seed + 2), args.matches)
        row = profile(kind, matches, hands)
        rows[kind] = {"bets_faced": row["bets_faced"], "folds": row["folds"], "calls": row["calls"],
                      "raises": row["raises"], "hands": row["hands"], "net": 0,
                      "by_history": row["by_history"], "scouted": True,
                      "river_bets": row["river_bets"], "river_bluffs": row["river_bluffs"],
                      "big_bets": row["big_bets"], "big_bets_air": row["big_bets_air"],
                      "small_bets": row["small_bets"], "small_bets_air": row["small_bets_air"]}
        print(f"{kind}: {row['hands']} hands, river bluffs {row['river_bluffs']}/{row['river_bets']}, "
              f"folded to {row['folds']}/{row['bets_faced']} bets", flush=True)
    with open(args.out, "w") as handle:
        json.dump(rows, handle, indent=1, sort_keys=True)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
