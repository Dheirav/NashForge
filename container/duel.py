"""
scripts/chipzen_duel.py with the uploaded bot as a player: `--a compact:<ladder dir>` builds it from the
rungs in that directory, all of them, as the image does. The duel's own `ladder_paths` cannot pick them:
it fills depths from the shipped defaults outside the directory, and on 28 Sept that played the old
one-raise solvers at 12 to 70bb (139 misses in 3,017 decisions) instead of the compact rungs.

    venv/bin/python container/duel.py --a compact:container/ladder "--a-flags=--purify all" \\
        --b ~/Code/PokerBot/results/cfr/ladder169l_v5x "--b-flags=--deep-primary --stack-cap" --arena-matches 5000
"""
import glob
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import scripts.chipzen_duel as duel  # noqa: E402
from chipzen.player import ArenaPlayer  # noqa: E402


def rungs(ladder_dir):
    """Every rung in a compact ladder, named by its logical .pkl path (cfr/pure.py finds the files beside it)."""
    return sorted(p[:-len(".rung.json")] + ".pkl" for p in glob.glob(os.path.join(ladder_dir, "*.rung.json")))

_build = duel.build


def build(ladder_dir, flags, label, rng, profiles_path):
    if not ladder_dir.startswith("compact:"):
        return _build(ladder_dir, flags, label, rng, profiles_path)
    tokens = flags.split()
    purify = tokens[tokens.index("--purify") + 1] if "--purify" in tokens else "none"
    paths = rungs(ladder_dir.split(":", 1)[1])
    player = ArenaPlayer(paths, rng, companions=[], purify=purify, stack_cap=True)
    player.label = label
    return player


duel.build = build

if __name__ == "__main__":
    duel.main()
