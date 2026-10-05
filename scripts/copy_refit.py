"""
Refit the copies the duels play, by the replay method `copy_validate.py` measured.

The division copies of 2 Oct were fitted by playing each candidate against v5i and matching the bot's
frequencies, and on 5 Oct `copy_validate.py` showed every one of them off its bot at the bot's own decisions
(RMS z 2.3 to 6.7) while a copy fitted by replay held (1.0 to 1.7 for Blueprint, PoetAndCoder, Shadow and
melly). So this fits each copy the second way, on the bot's most recent cached matches (from its
`profile_since.json` cutoff, if it has one), and writes it where the duels read a copy from: a markdown file
with a `Parameters: {...}` line, as `scripts/fit_archetype.py` writes.

It fits on all the matches, so it carries no held-out score of its own; `copy_validate.py` is the check that a
fit made this way predicts later matches. What no fit can fix is the archetype family itself: its first bet is
always about two thirds of the pot, and its postflop raise share and fold-to-three-bet are not free
parameters, so a copy is still to be trusted only for preflop play and the response to a bet.

    venv/bin/python scripts/copy_refit.py                                  # the named bots, into ~/pokerbot-scratch/copies
    venv/bin/python scripts/copy_refit.py --names hoops mr_hide r0ckGarden
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import copy_validate as cv  # noqa: E402

OUT = os.path.expanduser("~/pokerbot-scratch/copies")
NAMES = cv.NAMED + ("hoops", "mr_hide", "r0ckGarden", "Fold5", "Mimaima699-Pro")


def refit(name, max_matches=120, draws=8, rounds=150, seed=11):
    matches = cv.load_matches(name, since=cv.profile_since(name))[-max_matches:]
    if len(matches) < 6:
        return {"name": name, "matches": len(matches), "verdict": "too few matches"}
    replay = cv.Replay(matches, draws, seed)
    params, score, base = cv.fit(replay, rounds, seed)
    in_sample, _ = cv.rms(cv.compare(replay.real, replay.predicted(params)), cv.FITTED)
    return {"name": name, "matches": len(matches), "hands": sum(len(m["hands"]) for m in matches),
            "from": matches[0]["at"].isoformat(), "to": matches[-1]["at"].isoformat(), "base": base,
            "distance": score, "in_sample_rms": in_sample, "params": {k: round(v, 3) for k, v in params.items()}}


def write(row, out=OUT):
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"refit_{row['name']}.md")
    with open(path, "w") as handle:
        handle.write(f"# Copy of {row['name']}, refitted by replay {dt.date.today():%d %b %Y}\n\n"
                     f"{row['matches']} cached matches, {row['hands']} hands, {row['from'][:10]} to {row['to'][:10]}. "
                     f"Base shape {row['base']}, search distance {row['distance']:.4f}, in-sample RMS z "
                     f"{row['in_sample_rms']:.2f} over the fitted statistics.\n\n"
                     f"Parameters: `{json.dumps(row['params'])}`\n")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--names", nargs="*", default=list(NAMES))
    parser.add_argument("--max-matches", type=int, default=120)
    parser.add_argument("--rounds", type=int, default=150)
    parser.add_argument("--out", default=OUT)
    args = parser.parse_args()
    rows = []
    for i, name in enumerate(args.names, 1):
        row = refit(name, args.max_matches, rounds=args.rounds)
        if "params" in row:
            row["path"] = write(row, args.out)
            print(f"[{i}/{len(args.names)}] {name}: {row['matches']} matches, base {row['base']}, "
                  f"in-sample RMS z {row['in_sample_rms']:.2f} -> {row['path']}", flush=True)
        else:
            print(f"[{i}/{len(args.names)}] {name}: {row['verdict']} ({row['matches']})", flush=True)
        rows.append(row)
    with open(os.path.join(args.out, "refit_index.json"), "w") as handle:
        json.dump(rows, handle, indent=1)


if __name__ == "__main__":
    main()
