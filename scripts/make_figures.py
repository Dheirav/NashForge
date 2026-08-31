"""
Render every figure used by the reports, at both sizes.

Two widths, because the same chart cannot serve both: 6.6 inches for the Word
and web documents, and 3.35 inches at 400 dpi for an IEEE column, where a chart
scaled down rather than redrawn arrives with unreadable labels.

Everything is written under ``docs/figures/`` relative to the repository, so the
documents can be regenerated from a fresh clone. An earlier version of these
scripts wrote to an absolute scratch path, which meant the submitted documents
were reproducible only on one machine — the figures were in the repository but
the means of producing them were not.

    python scripts/make_figures.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WIDE = os.path.join(ROOT, "docs", "figures")
COLUMN = os.path.join(WIDE, "ieee")
os.makedirs(COLUMN, exist_ok=True)

INK, SOFT, FAINT, RULE = "#16191c", "#33393e", "#8b9298", "#d8dcdf"
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
POS, NEG, NONE = "#2a78d6", "#e34948", "#a7adb1"

#: (directory, figure size, base font, label font, annotation font, dpi)
WIDE_STYLE = (WIDE, (6.6, 3.0), "DejaVu Sans", 9, 8, 8.5, 220)
COLUMN_STYLE = (COLUMN, (3.35, 2.3), "DejaVu Serif", 6.6, 5.8, 6.2, 400)


def styled(base, size):
    plt.rcParams.update({
        "font.family": base, "font.size": size,
        "axes.edgecolor": RULE, "axes.labelcolor": SOFT, "text.color": INK,
        "xtick.color": FAINT, "ytick.color": FAINT,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "axes.facecolor": "white",
    })


def leduc(out, figsize, base, size, label, annot, dpi):
    styled(base, size)
    it = np.array([1000, 4000, 16000, 64000])
    runs = [("linear", [0.7213, 0.2621, 0.1072, 0.0559], S1),
            ("vanilla", [0.7769, 0.2831, 0.1313, 0.0615], S2),
            ("CFR+", [0.6843, 0.3173, 0.1542, 0.0819], S3),
            ("DCFR", [0.6926, 0.3500, 0.1673, 0.0930], S4)]

    fig, ax = plt.subplots(figsize=figsize)
    for name, values, colour in runs:
        ax.plot(it, values, color=colour, linewidth=1.4 if dpi > 300 else 2,
                marker="o", markersize=3 if dpi > 300 else 4.5,
                markeredgecolor="white", markeredgewidth=1.1, zorder=3)
        ax.annotate(name, (it[-1], values[-1]), xytext=(4, 0),
                    textcoords="offset points", color=colour,
                    fontsize=annot, fontweight="bold", va="center")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(it); ax.set_xticklabels(["1k", "4k", "16k", "64k"])
    ax.set_yticks([0.05, 0.1, 0.2, 0.4, 0.8])
    ax.set_yticklabels(["0.05", "0.10", "0.20", "0.40", "0.80"])
    ax.set_xlabel("training iterations")
    ax.set_ylabel("exploitability (lower is better)")
    ax.grid(axis="y", color=RULE, linewidth=0.8, zorder=0)
    ax.set_xlim(850, 110000)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig1_leduc.png"), dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def crossover(out, figsize, base, size, label, annot, dpi):
    styled(base, size)
    labels = ["40 s", "160 s", "640 s", "2560 s"]
    values = np.array([-3.136, -1.531, 0.273, 0.916])
    errors = np.array([0.729, 0.164, 0.203, 0.118])
    y = np.arange(len(labels))[::-1]

    fig, ax = plt.subplots(figsize=(figsize[0], figsize[1] * 0.93))
    ax.barh(y, values, height=0.58, color=[NEG, NEG, NONE, POS], zorder=3)
    ax.errorbar(values, y, xerr=errors, fmt="none", ecolor=SOFT,
                elinewidth=1.1, capsize=2.5, zorder=4)
    ax.axvline(0, color=FAINT, linewidth=1.3, zorder=2)
    # Anchor labels past the whisker, not the bar: at 40s the interval reaches
    # further left than the bar does, and anchoring on the bar put the number on
    # top of the error bar.
    for yi, v, e in zip(y, values, errors):
        tip = v + e if v > 0 else v - e
        ax.annotate(f"{v:+.3f}", (tip, yi), xytext=(5 if v > 0 else -5, 0),
                    textcoords="offset points", ha="left" if v > 0 else "right",
                    va="center", fontsize=annot, fontweight="bold", color=INK)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.set_xlabel("chips per hand to the equity agent")
    ax.set_xlim(-5.6, 2.4)
    ax.grid(axis="x", color=RULE, linewidth=0.8, zorder=0)
    ax.text(-5.4, len(labels) - 0.25, "← made-hand ahead", fontsize=label, color=FAINT)
    ax.text(2.3, len(labels) - 0.25, "equity ahead →", fontsize=label,
            color=FAINT, ha="right")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig2_crossover.png"), dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def features(out, figsize, base, size, label, annot, dpi):
    styled(base, size)
    labels = ["all 17 features", "hand strength only", "without hand strength",
              "postflop, as built", "postflop, + draw features"]
    values = [0.421, 0.238, 0.013, 0.475, 0.637]
    y = np.arange(len(labels))[::-1]

    fig, ax = plt.subplots(figsize=(figsize[0], figsize[1] * 0.93))
    ax.barh(y, values, height=0.62, color=[S1, S1, S1, S2, S2], zorder=3)
    for yi, v in zip(y, values):
        ax.annotate(f"{v:.3f}", (v, yi), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=annot, fontweight="bold", color=INK)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.set_xlabel("R² against true (Monte Carlo) equity")
    ax.set_xlim(0, 0.86)
    ax.grid(axis="x", color=RULE, linewidth=0.8, zorder=0)
    handles = [plt.Rectangle((0, 0), 1, 1, color=S1),
               plt.Rectangle((0, 0), 1, 1, color=S2)]
    ax.legend(handles, ["all decision states", "postflop only"],
              frameon=False, fontsize=label, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig3_features.png"), dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def evolution(out, figsize, base, size, label, annot, dpi):
    styled(base, size)
    names = ["vs random", "vs always-call", "vs CFR agent"]
    untrained = np.array([-13.4, -8.1, -403.9])
    trained = np.array([192.7, 0.5, -370.1])
    eu, et = np.array([14, 14, 13]), np.array([15, 4, 14])
    y = np.arange(len(names))[::-1]
    height = 0.34

    fig, ax = plt.subplots(figsize=(figsize[0], figsize[1] * 0.93))
    ax.barh(y + height / 2, untrained, height=height, color=S2,
            label="untrained", zorder=3)
    ax.barh(y - height / 2, trained, height=height, color=S1,
            label="after 50 generations", zorder=3)
    ax.errorbar(untrained, y + height / 2, xerr=eu, fmt="none", ecolor=SOFT,
                elinewidth=1, capsize=2, zorder=4)
    ax.errorbar(trained, y - height / 2, xerr=et, fmt="none", ecolor=SOFT,
                elinewidth=1, capsize=2, zorder=4)
    ax.axvline(0, color=FAINT, linewidth=1.3, zorder=2)
    for yi, v, e in list(zip(y + height / 2, untrained, eu)) + \
                    list(zip(y - height / 2, trained, et)):
        tip = v + e if v > 0 else v - e
        ax.annotate(f"{v:+.0f}", (tip, yi), xytext=(4 if v > 0 else -4, 0),
                    textcoords="offset points", ha="left" if v > 0 else "right",
                    va="center", fontsize=annot, fontweight="bold", color=INK)
    ax.set_yticks(y); ax.set_yticklabels(names)
    ax.set_xlabel("BB/100 to the evolved agent")
    ax.set_xlim(-560, 300)
    ax.grid(axis="x", color=RULE, linewidth=0.8, zorder=0)
    # Upper left is the only empty quadrant; anywhere lower overlaps the CFR bars.
    ax.legend(frameon=False, fontsize=label, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig4_evolution.png"), dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def comparison(out, figsize, base, size, label, annot, dpi):
    """
    Phase 4 on its budget axis: what each family is worth per hour of training.

    Read from `results/` rather than transcribed. The numbers moved once already
    when the instrument was fixed, and a figure with its own copy of them is a
    figure that goes stale without saying so.

    The y axis is the score against the CFR agent, because that is the opponent
    from outside both families' lineage and the only column whose seed spread is
    tight enough to plot. Zero is parity with the solver, so the line is the
    thing to look at rather than a gridline.
    """
    import json
    styled(base, size)
    root = os.path.join(ROOT, "results")
    with open(os.path.join(root, "comparison", "phase4.json")) as handle:
        phase4 = json.load(handle)
    with open(os.path.join(root, "ppo", "phase3_endpoint.json")) as handle:
        ppo = json.load(handle)

    seconds = phase4["wall_clock_seconds"]
    rungs = sorted(int(k) for k in seconds["ppo"])
    hours, scores, spread = [], [], []
    for rung in rungs:
        hours.append(seconds["ppo"][str(rung)] / 3600
                     if str(rung) in seconds["ppo"] else seconds["ppo"][rung] / 3600)
        vals = [row["trained"] for rec in ppo["records"]
                if rec["hands_trained"] == rung
                for row in rec["rows"] if row["opponent"] == "cfr"]
        scores.append(float(np.mean(vals)))
        spread.append((max(vals) - min(vals)) / 2)

    evo_hours = seconds["evolution"] / 3600
    evo = phase4["evolution"]["cfr"]

    fig, ax = plt.subplots(figsize=(figsize[0], figsize[1] * 0.95))
    ax.axhline(0, color=FAINT, linewidth=1.3, zorder=2)
    ax.annotate("parity with the solver", (0.55, 0), xytext=(0, -14),
                textcoords="offset points", fontsize=annot, color=SOFT,
                ha="center", va="top")

    ax.errorbar(hours, scores, yerr=spread, fmt="o-", color=S1, ecolor=SOFT,
                elinewidth=1, capsize=3, markersize=5, linewidth=1.8,
                label="PPO, self-play", zorder=4)
    for h, v, r in zip(hours, scores, rungs):
        ax.annotate(f"{r/1e6:g}M", (h, v), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=annot,
                    color=INK)

    ax.errorbar([evo_hours], [evo["trained"]], yerr=[evo["trained_ci95"]],
                fmt="s", color=S2, ecolor=SOFT, elinewidth=1, capsize=3,
                markersize=6, label="evolutionary search, 50 generations",
                zorder=4)
    ax.annotate(f"{evo['trained']:+.0f}", (evo_hours, evo["trained"]),
                xytext=(0, -14), textcoords="offset points", ha="center",
                fontsize=annot, fontweight="bold", color=INK)

    ax.set_xscale("log")
    # Explicit ticks: a log axis over half a decade otherwise labels 10^0 and
    # nothing else, which hides the very quantity the figure is about.
    ticks = [0.25, 0.5, 1, 2, 4]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{t:g}" for t in ticks])
    ax.tick_params(axis="x", which="minor", length=0)
    ax.set_xlabel("training wall-clock (hours, log scale)")
    ax.set_ylabel("BB/100 against the CFR agent")
    ax.set_xlim(0.18, 7.5)
    ax.set_ylim(-460, 120)
    ax.grid(color=RULE, linewidth=0.8, zorder=0)
    ax.legend(frameon=False, fontsize=label, loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig5_comparison.png"), dpi=dpi,
                bbox_inches="tight")
    plt.close(fig)


def main():
    for style in (WIDE_STYLE, COLUMN_STYLE):
        for draw in (leduc, crossover, features, evolution, comparison):
            draw(*style)
    print(f"wrote 5 figures at two sizes under {os.path.relpath(WIDE, ROOT)}/")


if __name__ == "__main__":
    main()
