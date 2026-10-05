"""
The uploaded bot's limits, measured by playing: peak memory, start-up time and the slowest
decisions, over whole arena-style matches against a scripted opponent.

    .cvenv/bin/python container/selfcheck.py --matches 200 --opponent station

Run in the slim venv (numpy and the SDK only), so what is measured is what the image carries.
The limits it checks: 256 MB resident, about 15 s from launch to ready, 2,000 ms a decision.
"""
import argparse
import glob
import os
import resource
import sys
import time

T0 = time.time()
# --no-native: the compiled module is refused, as in the image, so card classes are computed in Python.
if "--no-native" in sys.argv:
    sys.modules["pokerbot_native"] = None
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from chipzen.player import ArenaPlayer  # noqa: E402


def rungs(ladder_dir):
    """Every rung in a compact ladder, named by its logical .pkl path (cfr/pure.py finds the files beside it)."""
    return sorted(p[:-len(".rung.json")] + ".pkl" for p in glob.glob(os.path.join(ladder_dir, "*.rung.json")))
import scripts.chipzen_duel as duel  # noqa: E402
from scripts.chipzen_duel import build, play_match  # noqa: E402

# The dealer's showdown is this harness's, not the bot's: on the arena the server scores hands.
# Without numba the Python evaluator's fallback overflows an int8, so score with the native one.
if sys.modules.get("pokerbot_native", 0) is not None:
    import pokerbot_native as native  # noqa: E402
    duel.score7 = lambda hole, board: int(native.score_hand_7([c % 13 for c in list(hole) + list(board)],
                                                              [c // 13 for c in list(hole) + list(board)]))


def peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ladder", default=os.path.join(ROOT, "container", "ladder"))
    parser.add_argument("--matches", type=int, default=200)
    parser.add_argument("--opponent", default="station")
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--no-native", action="store_true", help="refuse the compiled module (read before imports)")
    parser.add_argument("--shadow", help="a full ladder directory (flat tables) that sees every state the bot "
                                         "sees, purified at play time; its decisions are compared with the bot's")
    args = parser.parse_args()
    # Three generators: the bot's and the shadow's start equal and are drawn from alike, so their card
    # classes (a sampled equity) come out the same; the dealer's shuffles use their own.
    rng = np.random.default_rng(args.seed + 2)
    bot = ArenaPlayer(rungs(args.ladder), np.random.default_rng(args.seed), companions=[],
                      purify="all", stack_cap=True)
    bot.label = "NashForge"
    ready = time.time() - T0
    times = []
    decide = bot.decide

    def timed(*a, **k):
        t = time.perf_counter()
        out = decide(*a, **k)
        times.append(time.perf_counter() - t)
        return out
    bot.decide = timed
    same = [0, 0]
    diffs = []
    if args.shadow:
        import copy
        import importlib.util
        spec = importlib.util.spec_from_file_location("chipzen_run", os.path.join(ROOT, "scripts", "chipzen_run.py"))
        run = importlib.util.module_from_spec(spec)
        saved_argv, sys.argv = sys.argv, [sys.argv[0]]
        spec.loader.exec_module(run)
        sys.argv = saved_argv
        _, ladder, _ = run.ladder_paths(os.path.abspath(args.shadow), deep_primary=True) \
            if args.shadow != "self" else (None, rungs(args.ladder), None)
        full = ArenaPlayer(ladder, np.random.default_rng(args.seed), companions=[], purify="all", stack_cap=True)
        full.label = "NashForge"
        full_decide = full.decide

        last = {}

        def shadowed(*a, **k):
            if os.environ.get("RNG_TRACE") and not last.get("done"):
                sb = bot.rng.bit_generator.state["state"]["state"]; sf = full.rng.bit_generator.state["state"]["state"]
                if sb != sf:
                    strip = lambda d: {x: v for x, v in (d.get("record") or {}).items() if x not in ("ms",)}
                    print("GENERATORS PART after decision", same[1]); print("  bot   ", strip(last["m"])); print("  shadow", strip(last["t"]))
                    last["done"] = True
            pristine = copy.deepcopy((a, k))   # before the bot sees it, in case deciding changes the state
            mine = timed(*a, **k)
            theirs = full_decide(*pristine[0], **pristine[1])
            last["m"], last["t"] = mine, theirs
            same[1] += 1
            # What goes to the server; the record beside it carries each bot's own timing.
            sent = lambda d: (d.get("action"), (d.get("params") or {}).get("amount"))
            if sent(mine) == sent(theirs):
                same[0] += 1
            elif not diffs and os.environ.get("FIRST_DIFF"):
                strip = lambda d: {k: v for k, v in (d.get("record") or {}).items() if k != "ms"}
                print("FIRST DIFFERENCE at decision", same[1]); print("  bot   ", strip(mine)); print("  shadow", strip(theirs))
                diffs.append(None)
            elif len(diffs) < 5:
                r = mine.get("record") or {}
                diffs.append((r.get("phase"), r.get("hole"), r.get("board"), r.get("history"), sent(mine), sent(theirs),
                              r.get("adjusted"), (theirs.get("record") or {}).get("adjusted")))
            return mine
        bot.decide = shadowed
    if args.opponent == "hammer":
        # The overbet shover of ~/pokerbot-scratch/flush/probe.py: needs no native module, so it can play
        # against a bot run with --no-native, and its line forces a decision on every street.
        sys.path.insert(0, os.path.expanduser("~/pokerbot-scratch/flush"))
        from probe import Hammer
        other = Hammer()
    else:
        other = build(f"archetype:{args.opponent}", "", args.opponent, np.random.default_rng(args.seed + 1), None)
    won = hands = 0
    for m in range(args.matches):
        r = play_match([bot, other], rng, ("NashForge", args.opponent))
        won += r["winner"] == 0
        hands += r["hands"]
    ms = np.array(times) * 1000
    print(f"ready in {ready:.2f} s; peak resident {peak_mb():.0f} MB; numba loaded: {'numba' in sys.modules}")
    print(f"{args.matches} matches against {args.opponent}: won {won} ({100 * won / args.matches:.1f}%), {hands:,} hands")
    print(f"{len(ms):,} decisions: median {np.median(ms):.2f} ms, p99 {np.percentile(ms, 99):.1f} ms, max {ms.max():.1f} ms")
    if args.shadow:
        print(f"shadow ({args.shadow}): {same[0]:,} of {same[1]:,} decisions identical ({100 * same[0] / max(1, same[1]):.2f}%)")
        for d in diffs:
            print("  differs:", d)
        print("(peak memory includes the shadow's full tables; run without --shadow for the bot alone)")
    ok = peak_mb() < 256 and ready < 15 and ms.max() < 2000
    print("WITHIN the upload limits" if ok else "OUTSIDE the upload limits")


if __name__ == "__main__":
    main()
