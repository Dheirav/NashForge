"""
Folds by the size of the bet, offline: the scout cache and our own match logs, read from the main tree.

    venv/bin/python scripts/fold_by_size_eval.py                     # the table, the bluff decisions, the ICCs
    venv/bin/python scripts/fold_by_size_eval.py --names hoops mr_hide

Three things, written up in docs/research/2026-10-05-fold-by-size.md:

1. Per bot, its fold rate to bets of each size from its scouted opponents (the scout's `by_size`, our matches left
   out so the two sources are independent), and the same from our side, counted by `Profiles.observe` on our logs.
2. A clean profile file built the way ~/pokerbot-scratch/profiles-clean/build.py builds one, but through
   `chipzen_scout.seed_row` so it carries the sized counts, and on it the bluff rule's verdict per size into a
   check: the overall bound (the rule as it was) against the bin's bound (the rule now).
3. The within-match correlation of each bin, the number the posterior's design effect needs.

No network: everything comes from the cache and the logs. Nothing is written into either tree.
"""
import argparse
import datetime as dt
import json
import os
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from chipzen import opponents as op  # noqa: E402
from chipzen.opponents import Profiles  # noqa: E402
import scripts.chipzen_scout as scout  # noqa: E402
from scripts.copy_validate import SCOUT, SINCE, load_matches, profile_since  # noqa: E402
from scripts.posterior_reads_eval import icc  # noqa: E402

MAIN = os.path.expanduser("~/Code/PokerBot")
PROFILE_FILE = os.path.join(MAIN, "results", "chipzen", "opponents.json")
LOGS = [os.path.join(MAIN, "results", "chipzen", "matches"), os.path.expanduser("~/pokerbot-scratch/chipzen/matches")]
SHOWN = ["hoops", "mr_hide", "PoetAndCoder", "Blueprint", "wsp", "Fold-ver-3", "r0ckGarden", "melly"]
#: As build.py: bots scouted on 5 Oct but never seeded, so their live rows came from our logs alone.
EXTRA = ["hoops", "mr_hide", "r0ckGarden"]
BINS = [name for name, _ in op.SIZE_BINS]
#: Into a check, the tree's three bet sizes and what each needs to fold.
SIZES = (("half", 0.5), ("pot", 1.0), ("2x", 2.0))


def cell(node, overall=None):
    n = sum(node.values()) if node else 0
    if not n:
        return "-"
    rate = node.get("fold", 0) / n
    flag = "*" if overall is not None and rate < overall and n >= op.SIZE_MIN else ""
    return f"{rate:.2f} ({n}){flag}"


def table(title, rows, names):
    print(f"\n## {title}\n")
    print("| bot | overall | " + " | ".join(f"post {b}" for b in BINS) + " | pre half | pre pot |")
    print("|---|---|" + "---|" * (len(BINS) + 2))
    for name in names:
        row = rows.get(name)
        if not row or not row.get("bets_faced"):
            print(f"| {name} | no bets on file |")
            continue
        overall = row["folds"] / row["bets_faced"]
        sized = row.get("by_size") or {}
        post = [cell(sized.get(f"post:{b}"), overall if b == "half" else None) for b in BINS]
        pre = [cell(sized.get(f"pre:{b}")) for b in ("half", "pot")]
        print(f"| {name} | {overall:.3f} ({row['bets_faced']}) | " + " | ".join(post + pre) + " |")
    print("\n`*`: a half-pot bin folding less than the bot's overall rate, from at least SIZE_MIN answers.")


def scouted(names, per_match=False):
    """{name: profile row} from the cache since each bot's cut-off, our matches left out; with per_match also the rows."""
    out, each = {}, {}
    plan = [(name, [m for m in load_matches(name, since=profile_since(name)) if "NashForge" not in m["vs"]])
            for name in names]
    total, done, started = sum(len(ms) for _, ms in plan), 0, time.time()
    print(f"scout cache: {len(plan)} bots, {total} matches", flush=True)
    for name, ms in plan:
        if not ms:
            continue
        rows = []
        for m in ms:
            rows.append(scout.profile(name, [m], {m["id"]: m["hands"]}) if per_match else None)
            done += 1
            if done % 250 == 0 or done == total:
                el = time.time() - started
                print(f"  {done}/{total} matches  {el:.0f}s  eta {(total - done) * el / done:.0f}s", flush=True)
        if per_match:
            each[name] = rows
            out[name] = _summed(rows, len(ms))
        else:
            out[name] = scout.profile(name, ms, {m["id"]: m["hands"] for m in ms})
    return out, each


def _summed(rows, matches):
    """Per-match scout rows summed into one, as `profile` over all of them would give."""
    total = {k: 0 for k in ("matches", "hands", "bets_faced", "folds", "calls", "raises", "river_bets", "river_bluffs",
                            "big_bets", "big_bets_air", "small_bets", "small_bets_air")}
    total["by_history"], total["by_size"] = {}, {}
    for r in rows:
        for k in list(total):
            if k in ("by_history", "by_size"):
                for key, node in r[k].items():
                    into = total[k].setdefault(key, {})
                    for a, n in node.items():
                        into[a] = into.get(a, 0) + n
            else:
                total[k] += r[k]
    total["matches"] = matches
    return total


def ours(names):
    p = Profiles(os.path.join(tempfile.mkdtemp(), "none.json"))
    p.SINCE_FILE = SINCE
    p.rebuild(*[d for d in LOGS if os.path.isdir(d)])
    return p.rows


def clean_file(rows_by_name, directory):
    """build.py's clean file, through seed_row, then our logs on top once."""
    path = os.path.join(directory, "opponents.clean.json")
    json.dump({n: scout.seed_row(r) for n, r in rows_by_name.items()}, open(path, "w"))
    p = Profiles(path, posteriors=True, scout_reads=True)
    p.SINCE_FILE = SINCE
    p.rebuild(*[d for d in LOGS if os.path.isdir(d)])
    return p


def decisions(p, names):
    print("\n## The bluff rule into a check, on the clean file under posteriors\n")
    print("Withheld (W) or released (r) for each size, by the overall bound (as it was) and the bin's bound (now).\n")
    print("| bot | never folds | overall upper | " + " | ".join(f"{s} bin upper" for s, _ in SIZES)
          + " | " + " | ".join(f"{s} was / now" for s, _ in SIZES) + " |")
    print("|---|---|---|" + "---|" * (2 * len(SIZES)))
    for name in names:
        if name not in p.rows:
            print(f"| {name} | not on file |")
            continue
        station = p.never_folds(name)
        overall = p.fold_floor_upper(name)
        uppers, verdicts = [], []
        for size, f in SIZES:
            need = f / (1 + f)
            key = f"fold_at:post:{op.size_bin(f)}"
            thin = p._trials(name, key) < op.SIZE_MIN
            bound = p.fold_upper_at(name, f)
            uppers.append("-" if bound is None else (f"{bound:.3f}" + (" (fallback)" if thin else "")))
            was = "W" if station and overall is not None and overall < need else "r"
            now = "W" if station and bound is not None and bound < need else "r"
            verdicts.append(f"{was} / {now}")
        ov = "-" if overall is None else f"{overall:.3f}"
        print(f"| {name} | {'yes' if station else 'no'} | {ov} | " + " | ".join(uppers + verdicts) + " |")
    print("\nA bluff needs b / (P + b) folds: a third for half the pot, a half for the pot, two thirds for 2x. "
          "Only a bot that `never_folds` has bluffs withheld at all.")


def preflop_decisions(p, names):
    """
    The same verdicts on an open from the small blind at 100bb, priced by the player's own break-even and size, since
    preflop the need depends on the call and the depth (a jam needs 0.985 folds there) rather than the size alone.
    """
    from abstraction.betting import ALL_IN, RAISE_HALF, RAISE_POT, RAISE_TWO
    from chipzen.player import ArenaPlayer
    state = {"phase": "preflop", "pot": 150, "to_call": 50, "your_stack": 9950, "opponent_stacks": [9900]}
    sizes = (("half", RAISE_HALF), ("pot", RAISE_POT), ("2x", RAISE_TWO), ("jam", ALL_IN))
    print("\n## The bluff rule on an open from the small blind at 100bb, same file\n")
    print("Each size's bin is read preflop; the need is `bluff_break_even` on that state. A bin's folds / answers "
          "are shown with its bound.\n")
    print("| bot | never folds | overall upper | " + " | ".join(f"{s} bin (folds/answers) upper, need" for s, _ in sizes)
          + " | " + " | ".join(f"{s} was / now" for s, _ in sizes) + " |")
    print("|---|---|---|" + "---|" * (2 * len(sizes)))
    for name in names:
        if name not in p.rows:
            print(f"| {name} | not on file |")
            continue
        station = p.never_folds(name)
        overall = p.fold_floor_upper(name)
        cells, verdicts = [], []
        for size, choice in sizes:
            f = ArenaPlayer.bluff_fraction(choice, state)
            need = ArenaPlayer.bluff_break_even(choice, state)
            key = op.size_key(f, True)
            node = (p.rows[name].get("by_size") or {}).get(key) or {}
            n = sum(node.values())
            thin = p._trials(name, f"fold_at:{key}") < op.SIZE_MIN
            bound = p.fold_upper_at(name, f, preflop=True)
            shown = "-" if bound is None else f"{bound:.3f}" + (" (fallback)" if thin else "")
            cells.append(f"{node.get('fold', 0)}/{n} {shown}, {need:.3f}")
            was = "W" if station and overall is not None and overall < need else "r"
            now = "W" if station and bound is not None and bound < need else "r"
            verdicts.append(f"{was} / {now}")
        ov = "-" if overall is None else f"{overall:.3f}"
        print(f"| {name} | {'yes' if station else 'no'} | {ov} | " + " | ".join(cells + verdicts) + " |")


def correlations(each):
    print("\n## Within-match correlation per bin (ANOVA ICC, pooled weighted by trials)\n")
    print("| bin | bots | pooled rho | median rho | answers per match |")
    print("|---|---|---|---|---|")
    found = {}
    for key in op.SIZE_KEYS:
        rate = f"fold_at:{key}"
        vals = [v for v in (icc(rows, rate) for rows in each.values()) if v is not None]
        if not vals:
            continue
        weight = sum(n for _, _, n in vals)
        pooled = sum(r * n for r, _, n in vals) / weight
        med = sorted(r for r, _, _ in vals)[len(vals) // 2]
        kbar = sum(k * n for _, k, n in vals) / weight
        found[key] = pooled
        print(f"| {key} | {len(vals)} | {pooled:.3f} | {med:.3f} | {kbar:.1f} |")
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--names", nargs="*", default=SHOWN)
    args = parser.parse_args()
    live = json.load(open(PROFILE_FILE))
    field = sorted({n for n, r in live.items() if r.get("scouted")} | set(EXTRA) | set(args.names))
    rows, each = scouted(field, per_match=True)
    table("Scout cache: the scouted bot facing its opponents' bets (our matches left out)", rows, args.names)
    logged = ours(args.names)
    table("Our logs: the opponent facing our bets", logged, args.names)
    correlations(each)
    p = clean_file(rows, tempfile.mkdtemp())
    decisions(p, args.names)
    preflop_decisions(p, args.names)


if __name__ == "__main__":
    main()
