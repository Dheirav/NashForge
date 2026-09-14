"""
Every figure for the phase-2 submission, from the repository's own results.

    venv/bin/python scripts/phase2/make_figures.py

Writes docs/figures/phase2/*.png. Numbers come from results/ where a file
exists and from NEXT.md's recorded tables where the measurement lives in a log
(the PPO ladder). Nothing here is typed in from memory: the source of each
figure is named next to its data.
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "docs", "figures", "phase2")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
INK, ACCENT, SOFT, RED, GREEN = "#2f3a44", "#2f4858", "#8fa3b0", "#b5453c", "#3c7d5a"


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print("wrote", os.path.relpath(path, ROOT))


# ---------------------------------------------------------------------------
# Diagrams
# ---------------------------------------------------------------------------

def box(ax, x, y, w, h, text, fc="#f4f6f7", ec=ACCENT, fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.02",
                                fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=INK,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, a, b, text=None, color=ACCENT):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, color=color, lw=1.1))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.018, text, ha="center", fontsize=7, color=SOFT)


def architecture():
    fig, ax = plt.subplots(figsize=(10, 6.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    # Foundation
    box(ax, 0.03, 0.79, 0.27, 0.13, "engine/\nrules, chips, hand evaluation\n(audited, unchanged)", bold=True)
    box(ax, 0.365, 0.79, 0.27, 0.13, "abstraction/\n6 strength buckets per street,\nboard texture, 3 bet sizes + all-in", bold=True)
    box(ax, 0.70, 0.79, 0.27, 0.13, "games/\nKuhn, Leduc (exact checks),\nno-limit hold'em", bold=True)
    # Families
    box(ax, 0.03, 0.53, 0.27, 0.16, "CFR family\nexternal-sampling MCCFR\nC++ core (native/), 32.5x\n250k iterations in 109 s", fc="#e8eef1")
    box(ax, 0.365, 0.53, 0.27, 0.16, "Evolutionary search\npopulation of policy networks,\nfitness by matches (training/)", fc="#e8eef1")
    box(ax, 0.70, 0.53, 0.27, 0.16, "PPO\nself-play reinforcement\nlearning, PyTorch (rl/)", fc="#e8eef1")
    for x in (0.165, 0.50, 0.835):
        arrow(ax, (x, 0.79), (x, 0.71))
    # Instrument
    box(ax, 0.03, 0.27, 0.605, 0.15, "evaluation/  one instrument for all three families\n40,000-hand matches against a fixed panel\n(random, always-call, the 250k solver); BB/100 with standard errors", fc="#fbf7ee", ec="#8a6d3b")
    arrow(ax, (0.165, 0.53), (0.165, 0.42))
    arrow(ax, (0.50, 0.53), (0.50, 0.42))
    arrow(ax, (0.73, 0.53), (0.60, 0.42))
    # External
    box(ax, 0.70, 0.27, 0.27, 0.15, "External instruments\nSlumbot (slumbot/): 200bb, 10k hands\nChipzen arena (chipzen/): rated, live\nopponents, every hand logged", fc="#fbf7ee", ec="#8a6d3b")
    ax.plot([0.165, 0.165, 0.675, 0.675], [0.53, 0.48, 0.48, 0.45], color=ACCENT, lw=1.1)
    arrow(ax, (0.675, 0.46), (0.74, 0.42))
    ax.text(0.42, 0.488, "the solver alone", ha="center", fontsize=7, color=SOFT, backgroundcolor="white")
    # Results
    box(ax, 0.03, 0.03, 0.94, 0.12, "results/  every figure in this paper with its provenance:\nresults/comparison, results/cfr, results/slumbot, results/chipzen", fc="#f4f6f7")
    arrow(ax, (0.33, 0.27), (0.33, 0.15))
    arrow(ax, (0.835, 0.27), (0.835, 0.15))
    ax.text(0.5, 0.955, "NashForge: overall architecture", ha="center", fontsize=11, fontweight="bold", color=INK)
    save(fig, "fig_architecture.png")


def arena_modules():
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    top, h = 0.64, 0.24
    cols = [(0.02, "Chipzen platform\nlobby and match\nWebSockets, JSON", "#e8eef1"),
            (0.275, "chipzen/client.py\nhandshake, heartbeat,\nreconnect, rated queue,\nstatus and logs", "#f4f6f7"),
            (0.53, "chipzen/bridge.py\nhistory to solver key:\npot fractions, translation,\nall-in vs the real stack", "#f4f6f7"),
            (0.785, "chipzen/player.py\nladder by effective stack,\ncap-2 or (4,2) companion,\nfallback rule, profile", "#f4f6f7")]
    for x, text, fc in cols:
        box(ax, x, top, 0.195, h, text, fc=fc, fs=8)
    for x0, label in ((0.215, "turn_request"), (0.47, "state"), (0.725, "node, mask")):
        arrow(ax, (x0, top + h / 2), (x0 + 0.06, top + h / 2))
        ax.text(x0 + 0.03, top + h / 2 + 0.035, label, ha="center", fontsize=7, color=SOFT)
    # the action goes back beneath the row
    ax.plot([0.88, 0.88, 0.115], [top, 0.54, 0.54], color="#8a6d3b", lw=1.1)
    arrow(ax, (0.115, 0.54), (0.115, top), color="#8a6d3b")
    ax.text(0.50, 0.555, "action: fold, check, call, or raise to an amount", ha="center", fontsize=7, color="#8a6d3b")
    bottom, hb = 0.06, 0.28
    rows = [(0.02, "chipzen/opponents.py\nfold-to-bet per opponent\nacross matches; bluffs\nwithheld under 25%", "#f4f6f7", ACCENT),
            (0.275, "evaluation.benchmark\ncfr_agent, the panel's own\nlookup: bucket|history\nto a policy over 6 actions", "#fbf7ee", "#8a6d3b"),
            (0.53, "results/cfr/ladder*/\nsolvers at 5 to 200bb;\n40 or 200 samples; texture;\ncap-2 at 100, 70, 50bb", "#fbf7ee", "#8a6d3b"),
            (0.785, "results/chipzen/\nmatches/*.jsonl: every\ndecision with its state;\nopponents.json; review.md", "#fbf7ee", "#8a6d3b")]
    for x, text, fc, ec in rows:
        box(ax, x, bottom, 0.195, hb, text, fc=fc, ec=ec, fs=8)
    arrow(ax, (0.215, bottom + hb / 2), (0.275, bottom + hb / 2))
    arrow(ax, (0.82, top), (0.42, bottom + hb), color=ACCENT)
    arrow(ax, (0.6275, bottom + hb), (0.6275, top))
    arrow(ax, (0.92, top), (0.92, bottom + hb))
    ax.text(0.655, 0.49, "loads", ha="center", fontsize=7, color=SOFT)
    ax.text(0.925, 0.47, "writes", ha="left", fontsize=7, color=SOFT)
    ax.text(0.56, 0.40, "asks", ha="center", fontsize=7, color=SOFT)
    ax.text(0.5, 0.96, "The arena path: module design", ha="center", fontsize=11, fontweight="bold", color=INK)
    save(fig, "fig_arena_modules.png")


# ---------------------------------------------------------------------------
# Charts from results/
# ---------------------------------------------------------------------------

def panel():
    d = json.load(open(os.path.join(ROOT, "results", "comparison", "phase4_native.json")))
    # PPO rows as recorded in NEXT.md from phase3_endpoint_native.json.
    rows = [("CFR solver\n(250k it.)", d["cfr"]["random"]["bb_per_100"], d["cfr"]["always-call"]["bb_per_100"], None),
            ("Evolution\n50 gen., 36M hands", d["evolution"]["random"]["trained"], d["evolution"]["always-call"]["trained"], d["evolution"]["cfr"]["trained"]),
            ("PPO\n0.5M hands", 191.2, 372.6, -84.6),
            ("PPO\n2M hands", 137.2, 373.2, -72.5),
            ("PPO\n8M hands", 226.8, 329.1, -74.9)]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    import numpy as np
    x = np.arange(len(rows))
    w = 0.26
    for i, (label, color) in enumerate((("vs random", SOFT), ("vs always-call", ACCENT), ("vs CFR solver", RED))):
        vals = [r[1 + i] if r[1 + i] is not None else 0 for r in rows]
        bars = ax.bar(x + (i - 1) * w, vals, w, label=label, color=color)
        for b, v in zip(bars, vals):
            if v:
                ax.text(b.get_x() + b.get_width() / 2, v + (12 if v >= 0 else -30), f"{v:+.0f}", ha="center", fontsize=7, color=INK)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([r[0] for r in rows])
    ax.set_ylabel("BB/100 (40,000 hands per matchup)")
    ax.set_title("Three families on one panel (results/comparison/phase4_native.json)", fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    save(fig, "fig_panel.png")


def bucket_sweep():
    d = json.load(open(os.path.join(ROOT, "results", "cfr", "bucket_sweep_long.json")))
    by_budget = defaultdict(list)
    for m in d["measurements"]:
        by_budget[m["budget"]].append(m["chips_per_hand_to_left"])
    import numpy as np
    budgets = sorted(by_budget)
    means = [np.mean(by_budget[b]) for b in budgets]
    ses = [np.std(by_budget[b], ddof=1) / len(by_budget[b]) ** 0.5 for b in budgets]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.errorbar(budgets, means, yerr=[1.96 * s for s in ses], fmt="o-", color=ACCENT, capsize=3)
    ax.axhline(0, color=INK, lw=0.8, ls="--")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("training budget, seconds (wall clock, equal for both)")
    ax.set_ylabel("chips/hand, 6 buckets minus 20")
    ax.set_title("Six buckets beat twenty at every budget (bucket_sweep_long.json, 3 seeds)", fontsize=9)
    save(fig, "fig_bucket_sweep.png")


def speed():
    native = json.load(open(os.path.join(ROOT, "results", "cfr", "nolimit_strategy.json")))["seconds"]
    py = json.load(open(os.path.join(ROOT, "results", "cfr", "nolimit_strategy_py.json")))["seconds"]
    steps = [("Python, 10 Sept", 32.4), ("Python optimised, 11 Sept", 7.47), ("C++ core, 11 Sept", native / 250000 * 1000)]
    fig, ax = plt.subplots(figsize=(6, 3.0))
    bars = ax.bar([s[0] for s in steps], [s[1] for s in steps], color=[SOFT, ACCENT, GREEN])
    for b, (_, v) in zip(bars, steps):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.15, f"{v:.2f} ms", ha="center", fontsize=8, color=INK)
    ax.set_yscale("log")
    ax.set_ylabel("ms per MCCFR iteration (100bb, log scale)")
    ax.set_title(f"Solver speed: a 250k-iteration solver went from {py / 3600:.1f} h to {native:.0f} s", fontsize=9)
    save(fig, "fig_speed.png")


def eq200():
    d = json.load(open(os.path.join(ROOT, "results", "cfr", "experiments", "eq200_vs_eq40.json")))
    fig, ax = plt.subplots(figsize=(5, 3.0))
    ax.bar([f"seed {s}" for s in d["seeds"]] + ["mean"], d["bb_per_100"] + [d["mean"]],
           color=[SOFT] * len(d["seeds"]) + [ACCENT], yerr=[0] * len(d["seeds"]) + [1.96 * d["stderr"]], capsize=4)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_ylabel("BB/100, 200 samples vs 40")
    ax.set_title(f"Bucketing at 200 equity samples: {d['mean']:+.1f} ± {d['stderr']:.1f} BB/100 (40,000 hands x 3)", fontsize=9)
    save(fig, "fig_eq200.png")


def slumbot():
    rows = [("4k iterations\n100bb", -1750.2, 524), ("150k\n100bb", -986.6, 374), ("250k\n200bb", -997.8, 396)]
    fig, ax = plt.subplots(figsize=(5, 3.0))
    ax.bar([r[0] for r in rows], [r[1] for r in rows], yerr=[r[2] for r in rows], color=[SOFT, ACCENT, ACCENT], capsize=4)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_ylabel("mbb/hand against Slumbot (9,999 hands)")
    ax.set_title("Slumbot: training halved the gap; depth did not move it (results/slumbot)", fontsize=9)
    save(fig, "fig_slumbot.png")


def arena():
    rows = []
    for p in glob.glob(os.path.join(ROOT, "results", "chipzen", "matches", "*.jsonl")):
        seat = opp = None
        cur = None
        for line in open(p):
            r = json.loads(line)
            f = r["frame"]
            if f == "match_start":
                seat = r["seat"]
                opp = next((s["display_name"] for s in r.get("seats") or [] if not s.get("is_self")), None)
            elif f == "round_start":
                cur = {"start": r["state"], "dec": [], "opp": opp, "seat": seat}
            elif f == "decision" and cur:
                cur["dec"].append(r)
            elif f == "round_result" and cur and seat is not None:
                cur["net"] = r["result"]["stacks"][seat] - cur["start"]["stacks"][seat]
                rows.append(cur)
                cur = None
    band = defaultdict(int)
    count = defaultdict(int)
    for h in rows:
        if h["dec"]:
            e = h["dec"][0]["effective_bb"]
            b = "under 15" if e < 15 else "15 to 35" if e < 35 else "35 to 70" if e < 70 else "70 and over"
            band[b] += h["net"]
            count[b] += 1
    order = ["70 and over", "35 to 70", "15 to 35", "under 15"]
    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    vals = [band[b] for b in order]
    ax.bar(order, vals, color=[RED if v < 0 else GREEN for v in vals])
    for i, b in enumerate(order):
        ax.text(i, vals[i] + (3000 if vals[i] >= 0 else -9000), f"{vals[i]:+,}\n{count[b]} hands", ha="center", fontsize=7.5, color=INK)
    ax.axhline(0, color=INK, lw=0.8)
    lo, hi = min(vals + [0]), max(vals + [0])
    ax.set_ylim(lo - 0.25 * (hi - lo), hi + 0.3 * (hi - lo))   # room for the labels under the title
    ax.set_ylabel("net chips")
    ax.set_xlabel("effective stack at the start of the hand, big blinds")
    ax.set_title(f"Arena, 13 Sept: where the chips went ({len(rows)} hands, results/chipzen/matches)", fontsize=9)
    save(fig, "fig_arena_depth.png")

    per = defaultdict(lambda: {"net": 0, "hands": 0})
    for h in rows:
        per[h["opp"] or "?"]["net"] += h["net"]
        per[h["opp"] or "?"]["hands"] += 1
    names = sorted(per, key=lambda k: -per[k]["hands"])
    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    vals = [per[n]["net"] for n in names]
    ax.bar(names, vals, color=[RED if v < 0 else GREEN for v in vals])
    for i, n in enumerate(names):
        ax.text(i, vals[i] + (4000 if vals[i] >= 0 else -12000), f"{vals[i]:+,}\n{per[n]['hands']} hands", ha="center", fontsize=7.5, color=INK)
    ax.axhline(0, color=INK, lw=0.8)
    lo, hi = min(vals + [0]), max(vals + [0])
    ax.set_ylim(lo - 0.3 * (hi - lo), hi + 0.3 * (hi - lo))
    ax.set_ylabel("net chips")
    ax.set_title("Arena, 13 Sept: net chips by opponent", fontsize=9)
    save(fig, "fig_arena_opponents.png")
    return rows


def text_snapshot(name, title, text):
    lines = text.rstrip("\n").split("\n")
    fig, ax = plt.subplots(figsize=(8, 0.22 * len(lines) + 0.6))
    ax.axis("off")
    ax.text(0.01, 0.98, text, family="DejaVu Sans Mono", fontsize=7.5, va="top", ha="left", color="#e6edf3",
            transform=ax.transAxes)
    fig.patch.set_facecolor("#0d1117")
    fig.suptitle(title, fontsize=8, color="#9fb3c8", x=0.01, ha="left")
    save(fig, name)


def snapshots():
    text_snapshot("snap_progress.png", "tools/chipzen-progress.sh, 13 September 20:51 IST",
                  "process: running (pid 1383838)\nlobby:    connected   (connected 7x, up 191 min)\n"
                  "last:     match lost   [188s ago]\nmatches:  45 finished, 0 active, 19 won / 16 lost   hands 1755\n"
                  "decides:  3344  misses 226  fallbacks 36  rejected 0  slowest 16.9 ms\n"
                  "  20:51  lost  vs mr_hide  10 hands  rated\n  20:49  lost  vs mr_hide  21 hands  rated\n"
                  "  20:40  lost  vs hoops  21 hands  rated")
    text_snapshot("snap_decision_log.png", "results/chipzen/matches/<id>.jsonl, one hand, as scripts/chipzen_review.py prints it",
                  "-- hand 3 dealer 0 stacks [9850, 10150] hole ['2c', '2h']\n"
                  "   preflop  hist ''           pot    150 call    50 eff  98.5 100bb      -> raise 300\n"
                  "   flop     hist '31/4'       pot   1500 call   900 eff  98.5 100bb      -> call\n"
                  "   turn     hist '31/41/3'    pot   6000 call  3600 eff  98.5 100bb      -> call\n"
                  "   river    hist '31/41/31/5' pot  14950 call  5350 eff  98.5 100bb      -> call\n"
                  "   result: winners [0] pot 19700 stacks [19700, 300] showdown [(0, 2c 2h), (1, Th 9h)]")
    text_snapshot("snap_training.png", "scripts/cfr/train_nolimit.py --native, the raise-cap-2 solver, 13 September",
                  "Training MCCFR (native) for 3,000,000 iterations...\n"
                  "   2,940,000/3,000,000   2.642 ms/it    390,440 infosets     263 MB  eta    2.6 min\n"
                  "   3,000,000/3,000,000   2.641 ms/it    390,456 infosets     263 MB  eta    0.0 min\n"
                  "  7921.9s (2.641 ms/iteration)\n"
                  "  vs uniform random  +4.811 +/- 0.786 chips/hand  95% CI [+3.271, +6.351]\n"
                  "  vs always call     +4.085 +/- 0.517 chips/hand  95% CI [+3.071, +5.099]\n"
                  "Wrote results/cfr/ladder200/cap2_100bb.pkl")


if __name__ == "__main__":
    architecture()
    arena_modules()
    panel()
    bucket_sweep()
    speed()
    eq200()
    slumbot()
    arena()
    snapshots()
