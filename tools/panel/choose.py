"""
Choose a set for an opponent: fit a scripted copy of it, then play each candidate set against the copy.

    ~/Code/PokerBot/venv/bin/python tools/panel/choose.py --opponent Shadow --sets fixture_set_final burst_set_t2

The fit (scripts/fit_archetype.py) reads matches from the season scout's index; bots scouted by chipzen_scout.py are
in another index (29 Sept: fermat1 was fitted to zero hands until the two were merged), so both are merged into a
scratch copy first. The fit starts from several shapes and keeps the closest. Each set then plays the copy as a
fixture plays: the set file's flags plus the two read flags fixture2.sh adds, with the opponent's real profile.

A copy is a scripted bot, which flatters an exploiter against a strong opponent (fermat1: v5x beat every copy while
losing both real matches); the report says so beside the numbers.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
MAIN = f"{HOME}/Code/PokerBot"
PY = f"{MAIN}/venv/bin/python"
CHIPZEN = f"{HOME}/pokerbot-scratch/chipzen"
SCOUT = f"{MAIN}/results/chipzen/scout"
BASES = ("nit", "maniac", "foldraise", "station", "bully")
FIXTURE_READS = "--sequential-triggers --scout-reads"


def write_result(path, obj):
    """Atomically: the panel reads result.json while jobs run, and a half-written file must never be seen."""
    tmp = path + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(obj, handle, indent=1)
    os.replace(tmp, path)


def step(i, n, text):
    print(f"STEP {i}/{n} {time.strftime('%H:%M:%S')} {text}", flush=True)


def merged_index(opponent, out):
    """The season index plus the other scout's matches for `opponent` that have their hands on disk."""
    os.makedirs(out, exist_ok=True)
    season = json.load(open(f"{SCOUT}/season_matches.json"))
    added = 0
    try:
        by_name = json.load(open(f"{SCOUT}/index.json"))["by_name"].get(opponent) or []
    except (OSError, KeyError, ValueError):
        by_name = []
    for m in by_name:
        if m["id"] in season or not os.path.exists(f"{SCOUT}/hands/{m['id']}.json"):
            continue
        season[m["id"]] = {"id": m["id"], "at": m["at"], "rated": m.get("rated"), "type": m.get("type"),
                           "participants": [{"name": opponent, "seat": m["seat"]}] +
                                           [{"name": v, "seat": 1 - m["seat"]} for v in m["vs"]]}
        added += 1
    json.dump(season, open(f"{out}/season_matches.json", "w"))
    if not os.path.exists(f"{out}/hands"):
        os.symlink(f"{SCOUT}/hands", f"{out}/hands")
    return added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--sets", nargs="+", required=True, help="set files in ~/pokerbot-scratch/chipzen")
    parser.add_argument("--matches", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=41)
    args = parser.parse_args()
    out = f"{HOME}/pokerbot-scratch/panel/choose/{time.strftime('%Y%m%d-%H%M%S')}-{args.opponent}"
    os.makedirs(out, exist_ok=True)
    n = 1 + len(BASES) + len(args.sets)
    k = 1
    step(k, n, f"merging the scout indexes for {args.opponent}")
    added = merged_index(args.opponent, f"{out}/scout")
    fits = []
    for base in BASES:
        k += 1
        step(k, n, f"fitting {args.opponent} from {base}")
        log = f"{out}/fit_{base}.log"
        with open(log, "w") as handle:
            subprocess.run([PY, "scripts/fit_archetype.py", args.opponent, "--base", base, "--scout-dir", f"{out}/scout",
                            "--out", f"{out}/fit_{base}.md"], cwd=MAIN, stdout=handle, stderr=subprocess.STDOUT)
        text = open(log).read()
        hands = re.search(r"target from ([\d,]+) scouted hands", text)
        dist = re.findall(r"distance ([0-9.]+)", text)
        if dist and os.path.exists(f"{out}/fit_{base}.md"):
            fits.append({"base": base, "distance": float(dist[-1]), "hands": hands.group(1) if hands else "?"})
    if not fits or fits[0]["hands"] == "0":
        print("no fit: the opponent has no scouted hands; scout it first", flush=True)
        write_result(f"{out}/result.json", {"opponent": args.opponent, "error": "no scouted hands", "at": time.time()})
        return
    best = min(fits, key=lambda f: f["distance"])
    md = open(f"{out}/fit_{best['base']}.md").read()
    params = md.split("Parameters: `")[1].split("`")[0]
    table = md[md.index("| statistic"):md.index("Parameters:")].strip()
    results = []
    for setfile in args.sets:
        k += 1
        lines = open(f"{CHIPZEN}/{setfile}").read().splitlines()
        ladder = lines[0] if lines[0].startswith("/") else f"{MAIN}/{lines[0]}"
        flags = re.sub(r"--matches-dir \S+", "", lines[2] if len(lines) > 2 else "").strip() + " " + FIXTURE_READS
        step(k, n, f"{setfile} against the {args.opponent} copy, {args.matches:,} matches")
        log = f"{out}/duel_{setfile}.log"
        with open(log, "w") as handle:
            subprocess.run([PY, f"{HOME}/pokerbot-scratch/aggro/run_fit.py", "--a", ladder, f"--a-flags={flags}",
                            "--a-label", setfile, "--b", "archetype:fit", "--b-label", args.opponent,
                            "--profiles", f"{MAIN}/results/chipzen/opponents.json", "--arena-matches", str(args.matches),
                            "--seed", str(args.seed), "--workers", "2", "--output", f"{out}/duel_{setfile}.json"],
                           cwd=MAIN, env=dict(os.environ, WT=MAIN, FIT_PARAMS=params), stdout=handle,
                           stderr=subprocess.STDOUT)
        win = re.search(r"wins ([0-9.]+)% ± ([0-9.]+)", open(log).read())
        results.append({"set": setfile, "label": lines[1], "win": float(win.group(1)) if win else None,
                        "stderr": float(win.group(2)) if win else None})
    result = {"opponent": args.opponent, "at": time.time(), "matches": args.matches, "fit": best, "fits": fits,
              "fit_table": table, "added_from_other_index": added, "results": results,
              "caveat": "a copy is a scripted bot: it flatters an exploiter against a strong real opponent"}
    write_result(f"{out}/result.json", result)
    print("DONE " + "; ".join(f"{r['set']}: {r['win']}%" for r in results), flush=True)


if __name__ == "__main__":
    main()
