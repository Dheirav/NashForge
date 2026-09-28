"""
Before a fixture: which of our reads fire on this opponent, and whether what
each one assumes is true of it.

    venv/bin/python scripts/opponent_brief.py PoetAndCoder --set results/cfr/ladder169l_v5x
    venv/bin/python scripts/opponent_brief.py Shadow

Twice this season the number that decided a match was in `opponents.json`
before we played, and it went wrong in opposite directions. wsp (23 Sept, lost)
re-raised our open 5 times in 392 and had bet the river 298 times without a
bluff; no read asked, and the solver four-bet ace-king into kings. Shadow (25
Sept, won from 2,200 of 20,000) had 30% air in its big bets; "shove call
declined" fired on it twelve times anyway, because it asks only how rarely a
bot calls, and folded TT to K9o. One was a statistic nothing read, the other a
read that assumed a statistic it never checked.

So the brief answers three questions, each of which would have flagged one of
the two:

1. **Which reads fire**, asked of the live `Profiles` predicates with the live
   flags, so the answer is the bot's and cannot drift from it.
2. **What each firing read assumes**, checked against the profile with a 95%
   Wilson bound: OK, CONFLICT (the profile contradicts the premise),
   UNMEASURED (the premise needs a number the profile does not hold) or
   ASSUMED (it cannot be checked from a profile at all). A read with a
   CONFLICT is doing the Shadow thing.
3. **Where the bot sits outside the field** on a statistic no firing read uses,
   which is the wsp thing.

With `--set`, it also says what the class cutoffs mean on that set's rungs: a
read written as "below the top two classes" folds 4 of 6 on a six-class rung
and 18 of 20 on a histogram rung.

It reads files and prints; it changes nothing. The registry below must name
every read in `chipzen/player.py`, and `tests/test_opponent_brief.py` fails
when a read is added without one, because a read the brief cannot see is a read
nobody checked.
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import math
import os
import sys
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import chipzen.opponents as op  # noqa: E402  (after the path, and after the private overrides load)
from chipzen.opponents import Profiles  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

OK, CONFLICT, UNMEASURED, ASSUMED = "OK", "CONFLICT", "UNMEASURED", "ASSUMED"

#: A premise statistic counts as "rare" when its upper bound is under this, as
#: "common" when its lower bound is over the matching equilibrium rate.
RARE = 0.10


def wilson(successes: int, trials: int, z: float = 1.96) -> Tuple[float, float]:
    """The 95% Wilson interval of a rate; (0, 1) with no trials."""
    if trials <= 0:
        return 0.0, 1.0
    p = successes / trials
    centre = (p + z * z / (2 * trials)) / (1 + z * z / trials)
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / (1 + z * z / trials)
    return max(0.0, centre - half), min(1.0, centre + half)


def _node(row: dict, key: str) -> Dict[str, int]:
    return (row.get("by_history") or {}).get(key, {})


def _rate(count: int, n: int) -> str:
    lo, hi = wilson(count, n)
    return f"{count} of {n} ({100 * count / n:.0f}%, 95% {100 * lo:.0f} to {100 * hi:.0f}%)" if n else "no data"


# ---------------------------------------------------------------------------
# Premise checks. Each takes a profile row and returns (status, what it found).
# ---------------------------------------------------------------------------

def big_bets_rarely_air(row: dict) -> Tuple[str, str]:
    """The premise of every read that treats a big bet as a made hand."""
    big = row.get("big_bets")
    if not big:
        return UNMEASURED, "the profile has no big-bet air count for this bot"
    air = row.get("big_bets_air", 0)
    _, hi = wilson(air, big)
    status = OK if hi < RARE else CONFLICT
    return status, f"big bets that were air: {_rate(air, big)}; needs the upper bound under {100 * RARE:.0f}%"


def raises_counted(row: dict) -> Tuple[str, str]:
    return UNMEASURED, ("the air count is of first bets only (`scripts/chipzen_scout.py`), "
                        "and the read also fires when it raises our bet")


def river_bets_rarely_bluffs(row: dict) -> Tuple[str, str]:
    bets = row.get("river_bets", 0)
    if not bets:
        return UNMEASURED, "no river bets counted"
    bluffs = row.get("river_bluffs", 0)
    _, hi = wilson(bluffs, bets)
    return (OK if hi < RARE else CONFLICT), f"river bets that were bluffs: {_rate(bluffs, bets)}"


def small_bets_often_air(row: dict) -> Tuple[str, str]:
    small = row.get("small_bets", 0)
    if not small:
        return UNMEASURED, "no small-bet count"
    air = row.get("small_bets_air", 0)
    lo, _ = wilson(air, small)
    return (OK if lo >= op.SMALL_BET_AIR_RATE else CONFLICT), f"small bets that were air: {_rate(air, small)}"


def folds_on_every_street_rarely(row: dict) -> Tuple[str, str]:
    """
    `never_folds` pools every bet we have made. A bot can be a non-folder on
    the flop and fold three times in four on the river (Fold-ver-3), and a
    bluff withheld on that river is the read working against us.
    """
    found, worst = [], OK
    for street in ("flop", "turn", "river"):
        node = _node(row, f"{street}:Ur")
        n = sum(node.values())
        if not n:
            continue
        lo, _ = wilson(node.get("fold", 0), n)
        flag = lo > op.EQUILIBRIUM_FOLD
        worst = CONFLICT if flag else worst
        found.append(f"{street} {_rate(node.get('fold', 0), n)}{' **folds**' if flag else ''}")
    if not found:
        return UNMEASURED, "no per-street counts"
    return worst, "fold to our bet by street: " + "; ".join(found)


def measured_at_node(key: str, action: str) -> Callable[[dict], Tuple[str, str]]:
    def check(row: dict) -> Tuple[str, str]:
        node = _node(row, key)
        n = sum(node.values())
        return (OK if n else UNMEASURED), f"`{key}` {action}: {_rate(node.get(action, 0), n)}, at the node the read acts on"
    return check


def assumed(text: str) -> Callable[[dict], Tuple[str, str]]:
    return lambda row: (ASSUMED, text)


#: Every read in `chipzen/player.py`, by the name it logs as `adjusted`: the
#: predicate that switches it on, where it acts, what its class cutoff is (as a
#: function of the rung's top class), and every premise it rests on.
READS: List[dict] = [
    dict(name="opened into a folding blind", predicate="folds_blind",
         acts="preflop, first to act, the solver folding: min-raise instead",
         premises=[measured_at_node("preflop:Ur", "fold"),
                   assumed("the fold rate holds at our minimum raise, whatever size it was counted at")]),
    dict(name="three-bet into a folder", predicate="folds_to_three_bet",
         acts="preflop facing an open, the solver folding: small three-bet instead",
         premises=[measured_at_node("preflop:TrUr", "fold"),
                   assumed("the fold rate holds at our small three-bet and at this depth")]),
    dict(name="river bet believed", predicate="never_bluffs",
         acts="river, facing a bet, the solver calling: fold below the top two classes",
         cutoff=lambda top: (top - 1, "folds classes below the top two"),
         premises=[river_bets_rarely_bluffs,
                   assumed("its river raises are as honest as its river bets; the profile counts bets")]),
    dict(name="big bet believed", predicate="big_bets_are_value",
         acts="postflop, facing 0.7 pot or more, the solver continuing: fold below the top two classes",
         cutoff=lambda top: (top - 1, "folds classes below the top two"),
         premises=[big_bets_rarely_air, raises_counted]),
    dict(name="small bet called", predicate="big_bets_are_value",
         acts="postflop, facing 0.6 pot or less, the solver folding: call from class 3 up",
         cutoff=lambda top: (3, "calls from class 3 up"),
         premises=[small_bets_often_air, raises_counted]),
    dict(name="their re-raise is value", predicate="never_three_bets",
         acts="preflop, they re-raised our open, the solver raising: call at a price or fold",
         premises=[measured_at_node("preflop:Ur", "raise"),
                   assumed("its re-raises are strong hands; the scout has the cards, the profile does not")]),
    dict(name="bluff withheld", predicate="never_folds",
         acts="any street, the solver raising a weak hand: check or call instead",
         premises=[folds_on_every_street_rarely]),
    dict(name="shove call declined", predicate="never_calls",
         acts="facing a bet of the pot or more, the solver calling: fold below the top class",
         cutoff=lambda top: (top, "folds classes below the top one"),
         premises=[big_bets_rarely_air]),
    dict(name="called for pot odds", predicate=None,
         acts="an opponent all in for a sliver: call at any strength", premises=[]),
    # Behind --aggro-reads and --reraise-defence, both off by default. Each fires
    # on a floor (a lower bound on a rate) rather than a yes/no predicate, so the
    # brief lists them without judging them; a set that turns one on needs the
    # floor read by hand.
    dict(name="river bluff caught", predicate=None,
         acts="river, facing a bet, the solver folding: call when the bluff floor pays for it (--aggro-reads)",
         premises=[assumed("its river bluff share from the profile is the share at this bet size")]),
    dict(name="bet into an over-folder", predicate=None,
         acts="flop or turn, checked to, below the top class: half-pot bet when the fold floor is high (--aggro-reads)",
         premises=[assumed("the fold rate holds at our half-pot bet")]),
    dict(name="re-raise defended", predicate=None,
         acts="preflop, our open re-raised, the solver folding: call when equity against its top share beats the price (--reraise-defence)",
         premises=[measured_at_node("preflop:Ur", "raise"),
                   assumed("it re-raises the top of its range, the tightest the rate allows")]),
]


#: `opponent_coverage.STATISTICS` consumers that are not `Profiles` predicates.
CONSUMER_PREDICATE = {"small_bets_called": "big_bets_are_value"}


def registered_names() -> set:
    return {r["name"] for r in READS}


def player_read_names(path: Optional[str] = None) -> set:
    """Every `adjusted = "..."` the player can log, read from its source."""
    import re
    source = open(path or os.path.join(ROOT, "chipzen", "player.py")).read()
    return set(re.findall(r'adjusted = "([^"]+)"', source))


def _coverage():
    spec = importlib.util.spec_from_file_location("opponent_coverage", os.path.join(ROOT, "scripts", "opponent_coverage.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def outliers(rows: Dict[str, dict], name: str, firing: set, tail: float = 10.0) -> List[tuple]:
    """
    Statistics on which this bot is beyond the field's `tail`th or
    (100 - tail)th percentile, with the read that consumes each and whether it
    fires. The same statistics and consumers as `opponent_coverage.py`.

    Not interquartile widths: the field is wide on every statistic, so Shadow's
    53% flop raises, above every other bot on file, came to 1.3 widths and
    wsp's 2.2% three-bet rate, the lowest on file, to 1.0. What made both of
    them a different kind of opponent was their rank, not the spread.
    """
    cov = _coverage()
    import numpy as np
    out = []
    for label, spec in cov.STATISTICS.items():
        mine, n = cov.value(rows.get(name, {}), spec)
        if mine is None:
            continue
        field = [v for bot, row in rows.items() if bot != name for v in [cov.value(row, spec)[0]] if v is not None]
        if len(field) < 5:
            continue
        low, median, high = np.percentile(field, [tail, 50, 100 - tail])
        if low <= mine <= high:
            continue
        above = sum(1 for v in field if v < mine)
        rank = f"above all {len(field)}" if above == len(field) else \
            (f"below all {len(field)}" if above == 0 else f"above {above} of {len(field)}")
        width = max(high - low, 1e-6)
        distance = (low - mine) / width if mine < low else (mine - high) / width
        consumer = spec[2]
        # The coverage table names some consumers by read rather than by the
        # predicate that switches them on.
        predicate = CONSUMER_PREDICATE.get(consumer, consumer)
        out.append((distance, label, mine, n, median, min(field), max(field), consumer,
                    predicate in firing if consumer else False, rank))
    return sorted(out, reverse=True)


def set_classes(ladder: str) -> List[Tuple[str, int]]:
    """(rung, postflop classes) for the cap-2 rungs of a set, from each rung's json."""
    out = []
    for path in sorted(glob.glob(os.path.join(ladder, "cap2_*bb.json"))):
        try:
            args = json.load(open(path)).get("args", {})
        except (OSError, ValueError):
            continue
        rung = os.path.basename(path)[5:-5]
        out.append((rung, int(args.get("buckets", 6))))
    return sorted(out, key=lambda t: int(t[0][:-2]))


def brief(name: str, profiles: Profiles, ladder: Optional[str] = None) -> str:
    rows = profiles.rows
    lines = [f"# Opponent brief: {name}", ""]
    row = rows.get(name)
    if not row:
        return "\n".join(lines + [f"No profile for {name!r}. Every read is off, so the solver plays it as anyone.", ""])
    lines.append(f"Profile: {row.get('hands', 0):,} hands, {row.get('bets_faced', 0):,} of our bets faced. "
                 f"Flags as the live bot runs them: sequential={profiles.sequential}, "
                 f"scout_reads={profiles.scout_reads}, bankroll={profiles.bankroll}.")
    lines.append("")

    unregistered = player_read_names() - registered_names()
    if unregistered:
        lines += [f"**UNREGISTERED READS in chipzen/player.py: {sorted(unregistered)}.** "
                  "The brief cannot say whether they fire or what they assume.", ""]

    firing_predicates = set()
    conflicts = 0
    lines += ["## Reads that fire", ""]
    for read in READS:
        predicate = read["predicate"]
        if predicate is None or not getattr(profiles, predicate)(name):
            continue
        firing_predicates.add(predicate)
        checks = [check(row) for check in read["premises"]]
        worst = CONFLICT if any(s == CONFLICT for s, _ in checks) else \
            (UNMEASURED if any(s == UNMEASURED for s, _ in checks) else OK)
        conflicts += worst == CONFLICT
        lines.append(f"### {read['name']}  ({worst})")
        lines.append(f"Switched on by `{predicate}`. Acts: {read['acts']}.")
        for status, text in checks:
            lines.append(f"- {status}: {text}")
        lines.append("")
    if not firing_predicates:
        lines += ["None. The solver plays this bot as it plays anyone.", ""]

    lines += ["## Where it sits outside the field", "",
              "Beyond the 10th or 90th percentile of the other profiled bots, on a sample of at least "
              f"{_coverage().MIN_SAMPLE}. A statistic no firing read uses is the wsp case.", ""]
    rows_out = outliers(rows, name, firing_predicates)
    if rows_out:
        lines += ["| statistic | this bot | field median | field range | read | fires |",
                  "|---|---|---|---|---|---|"]
        for distance, label, mine, n, median, lo, hi, consumer, fires, rank in rows_out:
            lines.append(f"| {label} | {100 * mine:.0f}% of {n} ({rank}) | {100 * median:.0f}% | "
                         f"{100 * lo:.0f} to {100 * hi:.0f}% | {consumer or '**none**'} | {'yes' if fires else '**no**'} |")
    else:
        lines.append("None.")
    lines.append("")

    if ladder:
        lines += [f"## Class cutoffs on `{ladder}`", ""]
        classes = set_classes(ladder)
        cut_reads = [r for r in READS if "cutoff" in r and r["predicate"] in firing_predicates]
        if not classes:
            lines.append("No cap-2 rung metadata found.")
        elif not cut_reads:
            lines.append("No firing read has a class cutoff.")
        else:
            for read in cut_reads:
                parts = []
                for rung, k in classes:
                    edge, what = read["cutoff"](k - 1)
                    share = edge / k if "folds" in what else (k - edge) / k
                    count = edge if "folds" in what else k - edge
                    parts.append(f"{rung} {count} of {k} ({100 * share:.0f}%)")
                lines.append(f"- {read['name']}: {what}: " + ", ".join(parts))
            lines.append("")
            lines.append("The cutoffs were written against six classes. Classes are not equal mass, so the "
                         "share is of classes, not of hands.")
        lines.append("")

    unmeasured = sum(1 for r in READS if r["predicate"] in firing_predicates
                     for s, _ in (c(row) for c in r["premises"]) if s == UNMEASURED)
    lines += ["## Verdict", "",
              f"{len(firing_predicates)} read predicate(s) fire; {conflicts} read(s) with a premise the profile "
              f"contradicts; {unmeasured} premise(s) the profile cannot check; "
              f"{sum(1 for o in rows_out if not o[8])} outlying statistic(s) no firing read uses.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("opponent")
    parser.add_argument("--profiles", default=os.path.join(ROOT, "results", "chipzen", "opponents.json"))
    parser.add_argument("--set", help="a ladder directory: say what the class cutoffs mean on its rungs")
    parser.add_argument("--no-sequential", action="store_true", help="the live bot runs --sequential-triggers")
    parser.add_argument("--no-scout-reads", action="store_true", help="the live bot runs --scout-reads")
    parser.add_argument("--bankroll", action="store_true")
    parser.add_argument("--out", help="also write the brief here")
    args = parser.parse_args()
    if not os.path.exists(args.profiles):
        raise SystemExit(f"{args.profiles}: no profiles (not tracked in git; pass --profiles from the main tree)")
    profiles = Profiles(args.profiles, sequential=not args.no_sequential, bankroll=args.bankroll,
                        scout_reads=not args.no_scout_reads)
    text = brief(args.opponent, profiles, args.set)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as handle:
            handle.write(text)


if __name__ == "__main__":
    main()
