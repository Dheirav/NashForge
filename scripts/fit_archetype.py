"""
Fit a scripted opponent to a real bot, then ask which of our sets plays it better.

    venv/bin/python scripts/fit_archetype.py v003 --base maniac --duel v5x v5i

`chipzen_calibrate.py` measures an archetype with the scout's own yardstick and
leaves the tuning to hand. The bully was tuned that way and `defend3_eq=0.60`
taught v5s60 to shove J7o into a fold rate real Shadow does not have. So this
does the tuning: start from the nearest shape, perturb its parameters, play each
candidate against v5i with every hand recorded, count it with
`chipzen_scout.profile`, and keep a candidate that is closer to the real bot's
counts over its matches since `--since`. Then the fitted shape plays each set in
`--duel` over the same seeds, and the report says which is ahead and by how much.

The fit is only as good as the columns it matches (`COLUMNS`), which are the
ones that decide a hand against us: how often it plays, raises, re-raises,
folds to a bet, calls rather than raises, and bluffs the river. A shape that
matches them can still differ elsewhere; say so beside any decision made on it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
MAIN = os.path.expanduser("~/Code/PokerBot")

import chipzen.archetypes as arch  # noqa: E402
from scripts.chipzen_calibrate import play_recorded  # noqa: E402
from scripts.chipzen_duel import build  # noqa: E402
from scripts.chipzen_scout import profile, summarise  # noqa: E402

#: The statistics fitted, and how much a miss on each counts.
COLUMNS = {"vpip": 1.0, "pfr": 1.0, "three_bet": 1.0, "fold_to_bet": 1.5, "call_share_of_answers": 1.0,
           "bb_fold_to_open": 0.5, "river_bluff_rate": 1.0, "showdown_rate": 0.5}
PROBABILITIES = {"raise_p", "bluff_p", "call_p", "open_frac"}


def target(name, since, scout_dir, bootstrap=None):
    """The real bot's counts over its matches since `since`, as the season scout counts them.

    With `bootstrap` (a seed), the matches are resampled with replacement first:
    one of the bots the scouted hands cannot tell apart from the real one."""
    cache = json.load(open(os.path.join(scout_dir, "season_matches.json"))).values()
    since = dt.datetime.fromisoformat(since).replace(tzinfo=dt.timezone.utc)
    items, hands = [], {}
    for m in cache:
        if name not in [p["name"] for p in m["participants"]]:
            continue
        if dt.datetime.fromisoformat(m["at"].replace("Z", "+00:00")) < since:
            continue
        path = os.path.join(scout_dir, "hands", f"{m['id']}.json")
        if not os.path.exists(path):
            continue
        seat = next(p["seat"] for p in m["participants"] if p["name"] == name)
        items.append({"id": m["id"], "seat": seat, "vs": [p["name"] for p in m["participants"] if p["name"] != name]})
        hands[m["id"]] = json.load(open(path))
    if bootstrap is not None:
        pick = np.random.default_rng(bootstrap).integers(0, len(items), len(items))
        items = [dict(items[i], id=f"{items[i]["id"]}#{k}") for k, i in enumerate(pick)]
        hands = {it["id"]: hands[it["id"].split("#")[0]] for it in items}
    return summarise(profile(name, items, hands), {}), sum(len(hands[it["id"]]) for it in items)


def measure(params, opponent, matches, seed):
    kind = "fit"
    arch.PARAMS[kind] = params
    if kind not in arch.ARCHETYPES:
        arch.ARCHETYPES = arch.ARCHETYPES + (kind,)
    bot = arch.Archetype(kind, np.random.default_rng(seed))
    rows, hands = play_recorded([opponent, bot], np.random.default_rng(seed + 1), matches)
    return summarise(profile(kind, rows, hands), {})


def distance(got, want):
    return sum(w * ((got.get(k) or 0) - (want.get(k) or 0)) ** 2 for k, w in COLUMNS.items())


def search(start, want, measure_fn, rounds, rng, label="start", log=True):
    """Hill-climb a parameter row towards `want`: perturb three parameters, keep the trial if it is closer.

    `measure_fn(params, r)` returns the summarised statistics of `params` at round `r` (0 for the start). It is
    a function so that a cheaper measurement than a duel against v5i can drive the same search: the copy
    validator (`scripts/copy_validate.py`) scores a row at the real bot's own decision points instead."""
    best = dict(start)
    got = measure_fn(best, 0)
    score = distance(got, want)
    if log:
        print(f"  start from {label}: distance {score:.4f}", flush=True)
    started = time.time()
    for r in range(1, rounds + 1):
        trial = dict(best)
        for key in rng.choice(list(trial), size=3, replace=False):
            step = rng.normal(0, 0.06)
            trial[key] = float(np.clip(trial[key] + step, 0.0 if key in PROBABILITIES else -0.3, 1.0))
        got_t = measure_fn(trial, r)
        d = distance(got_t, want)
        if d < score:
            best, score, got = trial, d, got_t
        if log:
            el = time.time() - started
            print(f"  round {r}/{rounds}: distance {score:.4f}  {el:.0f}s, eta {(rounds - r) * el / r:.0f}s", flush=True)
    return best, score, got


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name")
    parser.add_argument("--base", required=True, help="the archetype to start from")
    parser.add_argument("--since", default="2026-09-19")
    parser.add_argument("--rounds", type=int, default=24)
    parser.add_argument("--matches", type=int, default=30, help="matches a candidate is measured over")
    parser.add_argument("--duel", nargs="*", default=[], help="sets to play the fitted shape, e.g. v5x v5i")
    parser.add_argument("--duel-matches", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--bootstrap", type=int, help="resample the real bot's matches with this seed before fitting")
    parser.add_argument("--scout-dir", default=os.path.join(MAIN, "results", "chipzen", "scout"))
    parser.add_argument("--out")
    args = parser.parse_args()

    want, n = target(args.name, args.since, args.scout_dir, args.bootstrap)
    print(f"{args.name}: target from {n:,} scouted hands since {args.since}", flush=True)
    os.chdir(MAIN)
    opponent = build("results/cfr/ladder169l_v5i", "--deep-primary --stack-cap", "v5i",
                     np.random.default_rng(args.seed), None)
    best, score, got = search(arch.PARAMS[args.base], want,
                              lambda params, r: measure(params, opponent, args.matches, args.seed + r),
                              args.rounds, np.random.default_rng(args.seed + 7), label=args.base)
    # A final, larger measurement of the chosen shape, so the table is not the lucky sample that won the search.
    got = measure(best, opponent, 4 * args.matches, args.seed + 999)

    lines = [f"## {args.name}: fitted from `{args.base}`", "", f"Target: {n:,} scouted hands since {args.since}. "
             f"Fitted shape measured over {4 * args.matches} matches against v5i.", "",
             "| statistic | real bot | fitted shape |", "|---|---|---|"]
    lines += [f"| {k} | {100 * (want.get(k) or 0):.0f}% | {100 * (got.get(k) or 0):.0f}% |" for k in COLUMNS]
    lines += ["", "Parameters: `" + json.dumps({k: round(v, 3) for k, v in best.items()}) + "`", ""]

    if args.duel:
        import subprocess
        spec = json.dumps(best)
        lines += ["| our set | win rate against the fitted shape |", "|---|---|"]
        for label in args.duel:
            code = (
                "import sys, json, runpy; sys.argv = sys.argv[1:]\n"
                "sys.path.insert(0, %r)\n"
                "import chipzen.archetypes as a\n"
                "a.PARAMS['fit'] = json.loads(%r); a.ARCHETYPES = a.ARCHETYPES + ('fit',)\n"
                "runpy.run_path('scripts/chipzen_duel.py', run_name='__main__')\n" % (MAIN, spec))
            cmd = [os.path.join(MAIN, "venv", "bin", "python"), "-c", code, "chipzen_duel.py",
                   "--a", f"results/cfr/ladder169l_{label}", "--a-flags=--deep-primary --stack-cap", "--a-label", label,
                   "--b", "archetype:fit", "--b-label", f"fit {args.name}", "--arena-matches", str(args.duel_matches),
                   "--seed", "41", "--workers", str(args.workers)]
            out = subprocess.run(cmd, capture_output=True, text=True, cwd=MAIN).stdout
            line = next((l for l in out.splitlines() if "arena matches, " in l), out.strip()[-160:])
            lines.append(f"| {label} | {line.split(':', 1)[-1].strip()[:110]} |")
            print(f"  duel {label}: {line[:140]}", flush=True)
        lines.append("")
    text = "\n".join(lines)
    print("\n" + text)
    if args.out:
        open(args.out, "w").write(text)


if __name__ == "__main__":
    main()
