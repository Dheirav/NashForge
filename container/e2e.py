"""
End to end: the zip's contents, alone, playing arena matches through the SDK's types.

    .cvenv/bin/python container/e2e.py --matches 60 --opponent station

Copies container/upload/ to a scratch directory and starts container/e2e_driver.py there in its own
process (slim venv, no repository on the path, no numba, no native module), so a module the package
forgot, a blocked import or a bad conversion between our state and the SDK's fails here. This process
deals (scripts/chipzen_duel.py), plays the scripted opponent and, with --shadow, asks the full v5x the
same question at every decision and counts how often the answers match.
"""
import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

import scripts.chipzen_duel as duel  # noqa: E402


class Upload:
    """A player whose every decision is made by the packaged bot in the other process."""

    def __init__(self, workdir, seed):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        self.proc = subprocess.Popen([sys.executable, "e2e_driver.py", str(seed)], cwd=workdir, env=env, text=True,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.label, self.times = "NashForge upload", []

    def decide(self, state, valid, seat):
        t = time.perf_counter()
        self.proc.stdin.write(json.dumps({"state": state, "valid": list(valid), "seat": seat}, default=int) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise SystemExit("the packaged bot exited; its error is above")
        reply = json.loads(line)
        self.times.append(time.perf_counter() - t)
        params = {"amount": reply["amount"]} if reply["action"] == "raise" else {}
        return {"action": reply["action"], "params": params}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matches", type=int, default=60)
    parser.add_argument("--opponent", default="station")
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--shadow", help="a full ladder directory to compare every decision with")
    args = parser.parse_args()
    work = tempfile.mkdtemp(prefix="nf_upload_")
    shutil.copytree(os.path.join(ROOT, "container", "upload"), work, dirs_exist_ok=True)
    shutil.copy(os.path.join(ROOT, "container", "e2e_driver.py"), work)
    bot = Upload(work, args.seed)
    same = [0, 0]
    if args.shadow:
        import importlib.util
        spec = importlib.util.spec_from_file_location("chipzen_run", os.path.join(ROOT, "scripts", "chipzen_run.py"))
        run = importlib.util.module_from_spec(spec)
        saved, sys.argv = sys.argv, [sys.argv[0]]
        spec.loader.exec_module(run)
        sys.argv = saved
        from chipzen.player import ArenaPlayer
        _, ladder, _ = run.ladder_paths(os.path.abspath(args.shadow), deep_primary=True)
        full = ArenaPlayer(ladder, np.random.default_rng(args.seed), companions=[], purify="all", stack_cap=True)
        full.label = "NashForge"
        ask = bot.decide

        def shadowed(state, valid, seat):
            pristine = copy.deepcopy(state)
            mine = ask(state, valid, seat)
            theirs = full.decide(pristine, valid, seat)
            same[1] += 1
            ok = (mine["action"], mine["params"].get("amount")) == (theirs["action"], (theirs["params"] or {}).get("amount"))
            same[0] += ok
            if not ok and os.environ.get("E2E_DIFFS") and same[1] - same[0] <= 3:
                r = theirs.get("record") or {}
                print("DIFF", same[1], {k: pristine.get(k) for k in ("hand_number", "phase", "your_hole_cards", "board", "pot",
                      "to_call", "min_raise", "max_raise", "your_stack", "opponent_stacks")},
                      "| upload", (mine["action"], mine["params"].get("amount")), "| full", (theirs["action"], (theirs["params"] or {}).get("amount")),
                      "| full's record:", {k: r.get(k) for k in ("history", "solver", "miss", "fallback", "adjusted", "choice")})
            return mine
        bot.decide = shadowed
    other = duel.build(f"archetype:{args.opponent}", "", args.opponent, np.random.default_rng(args.seed + 1), None)
    rng = np.random.default_rng(args.seed + 2)
    won = hands = 0
    for _ in range(args.matches):
        r = duel.play_match([bot, other], rng, ("NashForge", args.opponent))
        won += r["winner"] == 0
        hands += r["hands"]
    bot.proc.stdin.close()
    bot.proc.wait(timeout=30)
    ms = np.array(bot.times) * 1000
    print(f"packaged bot, {args.matches} matches against {args.opponent}: won {won} ({100 * won / args.matches:.1f}%), "
          f"{hands:,} hands, {len(ms):,} decisions; round trip median {np.median(ms):.2f} ms, max {ms.max():.1f} ms")
    if args.shadow:
        print(f"against the full bot: {same[0]:,} of {same[1]:,} decisions identical ({100 * same[0] / max(1, same[1]):.2f}%)")
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
