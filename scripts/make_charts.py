"""Render the three analysis figures as PNGs for the Word document."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = "/home/dheirav/pokerbot-scratch"

INK, SOFT, FAINT, RULE = "#16191c", "#33393e", "#8b9298", "#d8dcdf"
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
POS, NEG, NONE = "#2a78d6", "#e34948", "#a7adb1"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.edgecolor": RULE, "axes.labelcolor": SOFT, "text.color": INK,
    "xtick.color": FAINT, "ytick.color": FAINT,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def leduc():
    it = np.array([1000, 4000, 16000, 64000])
    runs = [("linear", [0.7213, 0.2621, 0.1072, 0.0559], S1),
            ("vanilla", [0.7769, 0.2831, 0.1313, 0.0615], S2),
            ("CFR+", [0.6843, 0.3173, 0.1542, 0.0819], S3),
            ("DCFR", [0.6926, 0.3500, 0.1673, 0.0930], S4)]

    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    for name, values, colour in runs:
        ax.plot(it, values, color=colour, linewidth=2, marker="o",
                markersize=4.5, markeredgecolor="white", markeredgewidth=1.2,
                label=name, zorder=3)
        ax.annotate(name, (it[-1], values[-1]), xytext=(8, 0),
                    textcoords="offset points", color=colour,
                    fontsize=8.5, fontweight="bold", va="center")

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(it); ax.set_xticklabels(["1k", "4k", "16k", "64k"])
    ax.set_yticks([0.05, 0.1, 0.2, 0.4, 0.8])
    ax.set_yticklabels(["0.05", "0.10", "0.20", "0.40", "0.80"])
    ax.set_xlabel("training iterations"); ax.set_ylabel("exploitability (lower is better)")
    ax.grid(axis="y", color=RULE, linewidth=0.8, zorder=0)
    ax.set_xlim(850, 110000)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig1_leduc.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def crossover():
    labels = ["40 s", "160 s", "640 s", "2560 s"]
    values = np.array([-3.136, -1.531, 0.273, 0.916])
    errors = np.array([0.729, 0.164, 0.203, 0.118])
    colours = [NEG, NEG, NONE, POS]
    y = np.arange(len(labels))[::-1]

    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    ax.barh(y, values, height=0.55, color=colours, zorder=3)
    ax.errorbar(values, y, xerr=errors, fmt="none", ecolor=SOFT,
                elinewidth=1.3, capsize=3.5, zorder=4)
    ax.axvline(0, color=FAINT, linewidth=1.4, zorder=2)

    # Anchor the label beyond the whisker, not beyond the bar: at 40s the
    # interval reaches further left than the bar does, and anchoring on the bar
    # put the number on top of the error bar.
    for yi, v, e in zip(y, values, errors):
        tip = v + e if v > 0 else v - e
        ax.annotate(f"{v:+.3f}", (tip, yi), xytext=(9 if v > 0 else -9, 0),
                    textcoords="offset points", ha="left" if v > 0 else "right",
                    va="center", fontsize=8.5, fontweight="bold", color=INK)

    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.set_xlabel("chips per hand to the equity agent")
    ax.set_xlim(-5.1, 2.1)
    ax.grid(axis="x", color=RULE, linewidth=0.8, zorder=0)
    ax.text(-4.4, len(labels) - 0.25, "← made-hand ahead", fontsize=8, color=FAINT)
    ax.text(1.9, len(labels) - 0.25, "equity ahead →", fontsize=8, color=FAINT, ha="right")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig2_crossover.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def features():
    labels = ["all 17 features", "hand strength only", "without hand strength",
              "postflop, as built", "postflop, + draw features"]
    values = [0.421, 0.238, 0.013, 0.475, 0.637]
    colours = [S1, S1, S1, S2, S2]
    y = np.arange(len(labels))[::-1]

    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    ax.barh(y, values, height=0.58, color=colours, zorder=3)
    for yi, v in zip(y, values):
        ax.annotate(f"{v:.3f}", (v, yi), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8.5, fontweight="bold", color=INK)

    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.set_xlabel("R² against true (Monte Carlo) equity")
    ax.set_xlim(0, 0.78)
    ax.grid(axis="x", color=RULE, linewidth=0.8, zorder=0)
    handles = [plt.Rectangle((0, 0), 1, 1, color=S1),
               plt.Rectangle((0, 0), 1, 1, color=S2)]
    ax.legend(handles, ["all decision states", "postflop only"],
              frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig3_features.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


leduc(); crossover(); features()
print("wrote fig1_leduc.png, fig2_crossover.png, fig3_features.png")
