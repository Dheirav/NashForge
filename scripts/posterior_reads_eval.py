"""
Offline check of the posterior reads (`Profiles(posteriors=True)`) against the rules they replace.

    venv/bin/python scripts/posterior_reads_eval.py cache        # per-match counts from the scout cache (~7 min)
    venv/bin/python scripts/posterior_reads_eval.py icc          # within-match correlation of each rate
    venv/bin/python scripts/posterior_reads_eval.py predict      # early half against later half, per bot
    venv/bin/python scripts/posterior_reads_eval.py audit        # reads per opponent, old rules against posteriors
    venv/bin/python scripts/posterior_reads_eval.py decisions    # logged adjustments that would change (loads rungs)

Everything is read from the main tree (scout cache, clean profile file, match logs) and nothing is
written there. The per-match counts come from `chipzen_scout.profile` run on one match at a time, so
they are the same counts the profile file holds, only kept apart by match: the file sums them, and
the summing is exactly what hides the clustering this checks for.
"""
import argparse
import glob
import json
import math
import os
import sys
import tempfile
import time
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from chipzen import opponents as op  # noqa: E402

MAIN = os.path.expanduser("~/Code/PokerBot")
PROFILE_FILE = os.path.join(MAIN, "results", "chipzen", "opponents.json")
MATCH_LOGS = os.path.join(MAIN, "results", "chipzen", "matches")
#: Derived and rebuilt in minutes, so it lives outside the tree unless asked otherwise.
CACHE = os.environ.get("POSTERIOR_EVAL_CACHE",
                       os.path.join(tempfile.gettempdir(), "posterior_eval_per_match.json"))

#: The count keys a row carries (chipzen_scout.profile's numeric fields the reads use).
COUNT_KEYS = ("hands", "bets_faced", "folds", "calls", "raises", "river_bets", "river_bluffs",
              "big_bets", "big_bets_air", "small_bets", "small_bets_air")


# ---------------------------------------------------------------------------------------------- cache

def build_cache(names=None):
    import scripts.chipzen_scout as scout
    from scripts.copy_validate import load_matches, profile_since
    rows = json.load(open(PROFILE_FILE))
    names = names or sorted(n for n, r in rows.items() if r.get("scouted"))
    out = {}
    plan = []
    for name in names:
        matches = load_matches(name, since=profile_since(name))
        plan.append((name, matches))
    total = sum(len(m) for _, m in plan)
    done, started = 0, time.time()
    for name, matches in plan:
        per = []
        for m in matches:
            row = scout.profile(name, [m], {m["id"]: m["hands"]})
            per.append({"id": m["id"], "at": m["at"].isoformat(),
                        **{k: row[k] for k in COUNT_KEYS}, "by_history": row["by_history"]})
            done += 1
            if done % 100 == 0 or done == total:
                elapsed = time.time() - started
                print(f"  {done}/{total} matches  {elapsed:.0f}s  eta {(total - done) * elapsed / done:.0f}s",
                      flush=True)
        out[name] = per
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w") as handle:
        json.dump(out, handle)
    print(f"wrote {CACHE}: {len(out)} bots, {total} matches")


def load_cache():
    return json.load(open(CACHE))


def summed(per_match):
    """Per-match rows summed into one profile row, shaped as a seeded scout row (with its match count)."""
    row = {k: 0 for k in COUNT_KEYS}
    row["by_history"] = {}
    for m in per_match:
        for k in COUNT_KEYS:
            row[k] += m[k]
        for key, node in m["by_history"].items():
            into = row["by_history"].setdefault(key, {})
            for action, n in node.items():
                into[action] = into.get(action, 0) + n
    row["scouted"] = True
    row["net"] = 0
    row["scout_base"] = dict(row, matches=len(per_match))
    return row


# ---------------------------------------------------------------------------------------------- icc

def icc(per_match, rate):
    """
    The ANOVA estimate of the intraclass correlation of a binary outcome clustered by match
    (Fleiss), and the mean trials per match. None when too few matches carry the rate.
    """
    groups = [op.RATES[rate](m) for m in per_match]
    groups = [(s, n) for s, n in groups if n > 0]
    if len(groups) < 8:
        return None
    total_n = sum(n for _, n in groups)
    total_s = sum(s for s, _ in groups)
    g = len(groups)
    if total_n <= g:
        return None
    p = total_s / total_n
    msb = sum(n * (s / n - p) ** 2 for s, n in groups) / (g - 1)
    msw = sum(s - s * s / n for s, n in groups) / (total_n - g)
    n0 = (total_n - sum(n * n for _, n in groups) / total_n) / (g - 1)
    if msb + (n0 - 1) * msw <= 0:
        return None
    return (msb - msw) / (msb + (n0 - 1) * msw), total_n / g, total_n


def run_icc(cache):
    print(f"{'rate':16} {'bots':>4} {'pooled rho':>10} {'median rho':>10} {'trials/match':>12}")
    result = {}
    for rate in op.RATES:
        vals = [(r, k, n) for r, k, n in (icc(per, rate) or (None, None, None) for per in cache.values())
                if r is not None]
        if not vals:
            continue
        weight = sum(n for _, _, n in vals)
        pooled = sum(r * n for r, _, n in vals) / weight
        med = sorted(r for r, _, _ in vals)[len(vals) // 2]
        kbar = sum(k * n for _, k, n in vals) / weight
        result[rate] = {"bots": len(vals), "pooled": pooled, "median": med, "per_match": kbar}
        print(f"{rate:16} {len(vals):4d} {pooled:10.3f} {med:10.3f} {kbar:12.1f}")
    hpm = [sum(m["hands"] for m in per) / len(per) for per in cache.values() if per]
    print(f"hands per match: median over bots {sorted(hpm)[len(hpm) // 2]:.1f}, "
          f"pooled {sum(sum(m['hands'] for m in p) for p in cache.values()) / sum(len(p) for p in cache.values()):.1f}")
    return result


# ---------------------------------------------------------------------------------------------- predict

#: Each boolean read: the rate it reads, its threshold, which side fires, and its minimum count. The
#: later half's verdict is its own raw rate past the threshold, believed only with LATER_MIN trials.
READS = {
    "never_folds": ("fold_to_bet", op.EQUILIBRIUM_FOLD, "below"),
    "never_calls": ("call_share", op.NEVER_CALL_SHARE, "below"),
    "folds_blind": ("open_fold", op.FOLD_BLIND_RATE, "above"),
    "never_three_bets": ("open_reraise", op.RARE_RAISE_RATE, "below"),
    "folds_to_three_bet": ("three_bet_fold", op.THREE_BET_FOLD_RATE, "above"),
    "never_bluffs": ("river_bluff", op.NEVER_BLUFF_RATE, "below"),
}
LATER_MIN = 30


def split_half(per):
    k = len(per) // 2
    return per[:k], per[k:]


def log_loss(p, s, n):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return -(s * math.log(p) + (n - s) * math.log(1 - p))


def brier(p, s, n):
    return s * (1 - p) ** 2 + (n - s) * p ** 2


def run_predict(cache, min_matches=6):
    early_rows, late_rows = {}, {}
    for name, per in cache.items():
        if len(per) < min_matches:
            continue
        early, late = split_half(per)
        early_rows[name], late_rows[name] = summed(early), summed(late)
    post = op.Profiles("/nonexistent/opponents.json", posteriors=True, scout_reads=True, sequential=True)
    post.rows = early_rows
    print(f"bots with at least {min_matches} cached matches: {len(early_rows)}\n")

    # Point predictions: the raw early rate against the posterior mean, scored on every later trial.
    scores = defaultdict(lambda: defaultdict(float))
    per_bot = defaultdict(dict)
    for rate in op.RATES:
        for name in early_rows:
            s0, n0 = op.RATES[rate](early_rows[name])
            s1, n1 = op.RATES[rate](late_rows[name])
            if n0 == 0 or n1 == 0:
                continue
            raw = s0 / n0
            mean = post.posterior_mean(name, rate)
            flat = post.posterior_mean(name, rate, correct=False)
            for label, p in (("raw", raw), ("posterior", mean), ("posterior, no deff", flat)):
                scores[rate][label + ":ll"] += log_loss(p, s1, n1)
                scores[rate][label + ":brier"] += brier(p, s1, n1)
            scores[rate]["n"] += n1
            scores[rate]["bots"] += 1
            per_bot[name][rate] = (log_loss(raw, s1, n1) / n1, log_loss(mean, s1, n1) / n1, n0, n1)
    print("Per bot: log loss per later trial over all its rates, raw against posterior:")
    print(f"  {'bot':18} {'matches':>7} {'trials':>7} {'raw':>7} {'post':>7}  better")
    for name in sorted(per_bot, key=lambda n: -len(cache[n])):
        rates = per_bot[name]
        n = sum(r[3] for r in rates.values())
        lr = sum(r[0] * r[3] for r in rates.values()) / n
        lp = sum(r[1] * r[3] for r in rates.values()) / n
        print(f"  {name:18} {len(cache[name]):7d} {n:7d} {lr:7.4f} {lp:7.4f}  "
              f"{'posterior' if lp < lr - 1e-4 else ('raw' if lr < lp - 1e-4 else 'tie')}")
    print()
    print("Log loss and Brier per later trial (lower is better), summed over bots:")
    print(f"{'rate':16} {'bots':>4} {'trials':>7} {'raw LL':>8} {'post LL':>8} {'noDE LL':>8} "
          f"{'raw Br':>7} {'post Br':>7}")
    totals = defaultdict(float)
    table = {}
    for rate, sc in scores.items():
        n = sc["n"]
        row = {k: sc[k] / n for k in sc if ":" in k}
        table[rate] = dict(row, bots=int(sc["bots"]), trials=int(n))
        for k in sc:
            totals[k] += sc[k]
        print(f"{rate:16} {int(sc['bots']):4d} {int(n):7d} {row['raw:ll']:8.4f} {row['posterior:ll']:8.4f} "
              f"{row['posterior, no deff:ll']:8.4f} {row['raw:brier']:7.4f} {row['posterior:brier']:7.4f}")

    # Bot-level average: each bot counts once, which is the view that matters for the small ones.
    print("\nMean over bots of per-trial log loss (each bot weighted equally), by early sample size:")
    buckets = defaultdict(lambda: [0, 0.0, 0.0])
    for name, rates in per_bot.items():
        for rate, (lr, lp, n0, n1) in rates.items():
            b = "<50" if n0 < 50 else ("50-300" if n0 < 300 else "300+")
            buckets[b][0] += 1
            buckets[b][1] += lr
            buckets[b][2] += lp
    for b in ("<50", "50-300", "300+"):
        c, lr, lp = buckets[b]
        if c:
            print(f"  early trials {b:7}: {c:3d} bot-rates  raw {lr / c:.4f}  posterior {lp / c:.4f}")

    # Read decisions: fire on the early half under each rule, judged by the later half's own rate.
    old = op.Profiles("/nonexistent/opponents.json", posteriors=False, scout_reads=True, sequential=True)
    fixed = op.Profiles("/nonexistent/opponents.json", posteriors=False, scout_reads=True, sequential=False)
    old.rows = fixed.rows = early_rows
    # The second judge: the later half's own posterior (its prior refitted on the later rows), which
    # calls a read confirmed when its bound is past the threshold, refuted when the opposite bound is
    # on the wrong side, and leaves the rest open. The raw judge counts 0 of 40 as "never", which is
    # the zero-width mistake under test, so it flatters the raw and Wald rules on the never-reads.
    late = op.Profiles("/nonexistent/opponents.json", posteriors=True)
    late.rows = late_rows
    print("\nRead verdicts on the early half, judged on the later half two ways: its raw rate past the "
          f"threshold (needs {LATER_MIN} trials), and its posterior (confirmed / refuted / open):")
    print(f"{'read':20} {'rule':11} {'fired':>5} {'held':>4} {'fail':>4} {'n/a':>3} {'miss':>4} | "
          f"{'conf':>4} {'refu':>4} {'open':>4} {'miss':>4}   fired on; refuted ones starred")
    decisions = {}
    for read, (rate, threshold, side) in READS.items():
        for label, prof in (("fixed", fixed), ("sequential", old), ("posterior", post)):
            c = Counter()
            names_fired = []
            for name in early_rows:
                s1, n1 = op.RATES[rate](late_rows[name])
                verdict = getattr(prof, read)(name)
                truth = None
                if n1 >= LATER_MIN:
                    truth = (s1 / n1 < threshold) if side == "below" else (s1 / n1 >= threshold)
                if n1 > 0:
                    lo, hi = late.lower(name, rate), late.upper(name, rate)
                    confirmed = hi < threshold if side == "below" else lo >= threshold
                    refuted = lo >= threshold if side == "below" else hi < threshold
                else:
                    confirmed = refuted = False
                if verdict:
                    c["fired"] += 1
                    c["held" if truth else ("n/a" if truth is None else "fail")] += 1
                    c["conf" if confirmed else ("refu" if refuted else "open")] += 1
                    names_fired.append(name + ("*" if refuted else ""))
                else:
                    c["miss"] += int(bool(truth))
                    c["pmiss"] += int(confirmed)
            decisions[f"{read}/{label}"] = dict(c, names=names_fired)
            print(f"{read:20} {label:11} {c['fired']:5d} {c['held']:4d} {c['fail']:4d} {c['n/a']:3d} {c['miss']:4d} | "
                  f"{c['conf']:4d} {c['refu']:4d} {c['open']:4d} {c['pmiss']:4d}   {', '.join(names_fired)}")
    return table, decisions, per_bot


# ---------------------------------------------------------------------------------------------- audit

BOOL_READS = ("never_folds", "never_calls", "folds_blind", "never_three_bets", "folds_to_three_bet",
              "never_bluffs", "river_never_bluffs", "big_bets_are_value")
FLOORS = ("river_bluff_floor", "postflop_fold_floor", "reraise_floor")


def reads_of(prof, name):
    on = [r for r in BOOL_READS if getattr(prof, r)(name)]
    floors = {f: getattr(prof, f)(name) for f in FLOORS}
    return on, floors


def run_audit():
    rows = json.load(open(PROFILE_FILE))
    old = op.Profiles("/nonexistent/opponents.json", sequential=True, scout_reads=True)
    new = op.Profiles("/nonexistent/opponents.json", sequential=True, scout_reads=True, posteriors=True)
    old.rows = new.rows = rows
    print("Priors fitted on the clean profile file:")
    for rate in op.RATES:
        mean, strength = new.prior(rate)
        print(f"  {rate:16} mean {mean:.3f}  strength {strength:6.1f}")
    print("\nReads per opponent (live flags: --sequential-triggers --scout-reads):")
    changed = {}
    for name in sorted(rows, key=lambda n: -rows[n].get("bets_faced", 0)):
        a, fa = reads_of(old, name)
        b, fb = reads_of(new, name)
        fold_up = new.fold_floor_upper(name)
        line = f"  {name:18} old: {', '.join(a) or '-':40} post: {', '.join(b) or '-'}"
        floor_txt = "; ".join(f"{k.split('_floor')[0]} {fa[k] if fa[k] is None else round(fa[k], 3)}"
                              f"->{fb[k] if fb[k] is None else round(fb[k], 3)}"
                              for k in FLOORS if fa[k] is not None or fb[k] is not None)
        print(line + (f"   [{floor_txt}]" if floor_txt else "") +
              (f"   fold upper {fold_up:.3f}" if fold_up is not None else ""))
        if set(a) != set(b):
            changed[name] = (sorted(set(a) - set(b)), sorted(set(b) - set(a)))
    return rows, old, new, changed


def logged_decisions():
    """Every logged decision with an adjustment, by opponent: (adjusted, record)."""
    out = defaultdict(list)
    for path in sorted(glob.glob(os.path.join(MATCH_LOGS, "*.jsonl"))):
        opponent = None
        with open(path) as handle:
            for line in handle:
                try:
                    frame = json.loads(line)
                except ValueError:
                    continue
                if frame.get("frame") == "match_start":
                    opponent = next((s.get("display_name") for s in frame.get("seats") or []
                                     if not s.get("is_self")), None)
                rec = frame.get("record") if isinstance(frame.get("record"), dict) else None
                if rec is None and "adjusted" in frame:
                    rec = frame
                if rec is not None and "adjusted" in rec:
                    out[rec.get("opponent") or opponent].append((rec.get("adjusted"), rec, frame))
    return out


#: Each logged adjustment, by the read that made it.
ADJUSTMENT_READ = {
    "opened into a folding blind": "folds_blind", "three-bet into a folder": "folds_to_three_bet",
    "river bet believed": "never_bluffs", "big bet believed": "big_bets_are_value",
    "small bet called": "big_bets_are_value", "their re-raise is value": "never_three_bets",
    "bluff withheld": "never_folds", "shove call declined": "never_calls",
}


def _rung_file(ladder_dir, deep_primary, solver):
    """The pickle a logged decision's `solver` field names, preferring the cap-2 rung under --deep-primary."""
    base = os.path.join(MAIN, ladder_dir)
    depth = str(solver).split("bb")[0] + "bb"
    order = ("cap2_", "nolimit_") if deep_primary else ("nolimit_", "cap2_")
    for prefix in order:
        path = os.path.join(base, f"{prefix}{depth}.pkl")
        if os.path.exists(path):
            return path
    return None


def withheld_sizes():
    """
    The raise each logged "bluff withheld" decision took back, as the solver's distribution over the
    raise sizes at that node, looked up in the rung that played it (as `chipzen_replay.lookup` does).
    Rungs are loaded one at a time; each is about 400 MB.
    """
    import numpy as np
    from abstraction.betting import RAISE_ACTIONS
    from chipzen.player import load_solver
    from scripts.chipzen_replay import lookup
    rows = []
    for path in sorted(glob.glob(os.path.join(MATCH_LOGS, "*.jsonl"))):
        version = {}
        with open(path) as handle:
            for line in handle:
                if line.startswith('{"frame": "match_start"'):
                    version = json.loads(line).get("version") or {}
                elif '"bluff withheld"' in line:
                    rec = json.loads(line)
                    rec["_rung"] = _rung_file(version["ladder_dir"], version.get("deep_primary"), rec["solver"]) \
                        if version.get("ladder_dir") else None
                    rows.append(rec)
    by_rung = defaultdict(list)
    for rec in rows:
        by_rung[rec["_rung"]].append(rec)
    started = time.time()
    for k, (rung, recs) in enumerate(sorted(by_rung.items(), key=lambda kv: str(kv[0])), 1):
        if rung is None:
            for rec in recs:
                rec["_sizes"] = None
            continue
        solver = load_solver(rung, np.random.default_rng(0))
        for rec in recs:
            weights = lookup(solver, rec)
            raise_mass = None if weights is None else {a: float(weights[a]) for a in RAISE_ACTIONS if weights[a] > 0}
            total = sum(raise_mass.values()) if raise_mass else 0.0
            rec["_sizes"] = {a: w / total for a, w in raise_mass.items()} if total > 0 else None
        del solver
        if k % 10 == 0 or k == len(by_rung):
            print(f"  rung {k}/{len(by_rung)}  {time.time() - started:.0f}s", flush=True)
    return rows


def break_even(action, rec):
    """b / (pot + b) for the chips a raise of this size puts in, with the arena's pot (their bet in it)."""
    from abstraction.betting import ALL_IN
    from slumbot.bridge import RAISE_FRACTIONS
    pot, to_call = rec["pot"], rec["to_call"]
    stack = rec["effective_bb"] * 100
    b = stack if action == ALL_IN else to_call + (pot + to_call) * RAISE_FRACTIONS[action - 2]
    b = min(b, stack) if stack > 0 else b
    return b / (pot + b)


def run_decision_audit():
    rows, old, new, _ = run_audit()
    decisions = logged_decisions()
    print("\nLogged adjustments, by opponent, against today's clean file:")
    print(f"  {'opponent':18} {'adjustment':28} {'logged':>6}  old today  post today")
    totals = Counter()
    for opponent, recs in sorted(decisions.items(), key=lambda kv: -len(kv[1])):
        tally = Counter(adj for adj, _, _ in recs if adj in ADJUSTMENT_READ)
        for adj, n in tally.most_common():
            read = ADJUSTMENT_READ[adj]
            a, b = getattr(old, read)(opponent), getattr(new, read)(opponent)
            totals[("logged", adj)] += n
            totals[("old", adj)] += n * a
            totals[("post", adj)] += n * b
            print(f"  {str(opponent):18} {adj:28} {n:6d}  {'fires' if a else '-':9}  {'fires' if b else '-'}")
    print("\n  totals: adjustment, logged, still made under today's old rules, under posteriors")
    for adj in ADJUSTMENT_READ:
        if totals[("logged", adj)]:
            print(f"    {adj:28} {totals[('logged', adj)]:6d} {totals[('old', adj)]:6d} {totals[('post', adj)]:6d}")

    print("\nBluff withheld, size-aware: the solver's raise sizes at each logged withholding, and the share")
    print("the posterior rule would release (fold upper bound at or above that size's break-even):")
    recs = withheld_sizes()
    per = defaultdict(Counter)
    for rec in recs:
        name = rec["opponent"]
        # The rule plays on the overall rate; the first-bet rate is shown beside it because it is the
        # obvious refinement and the audit is where it was found wanting (see `fold_floor_upper`).
        upper = new.fold_floor_upper(name)
        first = new.upper(name, "first_bet_fold") if bool(rec["board"]) and rec["to_call"] == 0 and \
            new._trials(name, "first_bet_fold") >= op.SEQ_MIN_OBSERVED else upper
        c = per[name]
        c["logged"] += 1
        if not new.never_folds(name):
            c["released, read off"] += 1
            continue
        if rec["_sizes"] is None:
            c["size unknown"] += 1
            continue
        c["sized"] += 1
        released = sum(w for a, w in rec["_sizes"].items() if upper >= break_even(a, rec))
        c["released"] += released
        c["released on the first-bet rate"] += sum(w for a, w in rec["_sizes"].items()
                                                   if first >= break_even(a, rec))
        c["released postflop, checked to"] += released if rec["phase"] != "preflop" and rec["to_call"] == 0 else 0
        for a, w in rec["_sizes"].items():
            c[f"size {a}"] += w
    print(f"  {'opponent':16} {'upper':>6} {'1st bet':>7} {'logged':>6} {'sized':>5} {'unknown':>7} {'released':>8} "
          f"{'1st-bet rule':>12}  postflop checked-to   size mix (half / pot / 2x / all-in)")
    for name, c in sorted(per.items(), key=lambda kv: -kv[1]["logged"]):
        up = new.fold_floor_upper(name)
        fb = new.upper(name, "first_bet_fold") if new._trials(name, "first_bet_fold") >= op.SEQ_MIN_OBSERVED else None
        mix = " / ".join(f"{c[f'size {a}']:.0f}" for a in (2, 3, 4, 5))
        print(f"  {name:16} {up if up is None else round(up, 3)!s:>6} {fb if fb is None else round(fb, 3)!s:>7} "
              f"{c['logged']:6d} {c['sized']:5d} "
              f"{c['size unknown']:7d} {c['released'] + c['released, read off']:8.1f} "
              f"{c['released on the first-bet rate'] + c['released, read off']:12.1f}  "
              f"{c['released postflop, checked to']:6.1f}   {mix}")
    return per


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", choices=("cache", "icc", "predict", "audit", "decisions"))
    parser.add_argument("--names", nargs="*")
    args = parser.parse_args()
    if args.stage == "cache":
        build_cache(args.names)
    elif args.stage == "icc":
        run_icc(load_cache())
    elif args.stage == "predict":
        run_predict(load_cache())
    elif args.stage == "audit":
        run_audit()
    else:
        run_decision_audit()


if __name__ == "__main__":
    main()
