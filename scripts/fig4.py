import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, sys

INK, SOFT, FAINT, RULE = "#16191c", "#33393e", "#8b9298", "#d8dcdf"
S1, S2 = "#2a78d6", "#eb6834"

def render(out, size, base, val, lab, ann):
    plt.rcParams.update({"font.family": base, "font.size": size,
        "axes.edgecolor": RULE, "axes.labelcolor": SOFT, "text.color": INK,
        "xtick.color": FAINT, "ytick.color": FAINT,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "axes.facecolor": "white"})
    names = ["vs random", "vs always-call", "vs CFR agent"]
    untr = np.array([-13.4, -8.1, -403.9]); tr = np.array([192.7, 0.5, -370.1])
    eu = np.array([14, 14, 13]); et = np.array([15, 4, 14])
    y = np.arange(len(names))[::-1]; h = 0.34

    fig, ax = plt.subplots(figsize=val)
    ax.barh(y + h/2, untr, height=h, color=S2, label="untrained", zorder=3)
    ax.barh(y - h/2, tr, height=h, color=S1, label="after 50 generations", zorder=3)
    ax.errorbar(untr, y + h/2, xerr=eu, fmt="none", ecolor=SOFT, elinewidth=1, capsize=2, zorder=4)
    ax.errorbar(tr, y - h/2, xerr=et, fmt="none", ecolor=SOFT, elinewidth=1, capsize=2, zorder=4)
    ax.axvline(0, color=FAINT, linewidth=1.3, zorder=2)
    for yi, v, e in list(zip(y + h/2, untr, eu)) + list(zip(y - h/2, tr, et)):
        tip = v + e if v > 0 else v - e
        ax.annotate(f"{v:+.0f}", (tip, yi), xytext=(4 if v > 0 else -4, 0),
                    textcoords="offset points", ha="left" if v > 0 else "right",
                    va="center", fontsize=ann, fontweight="bold", color=INK)
    ax.set_yticks(y); ax.set_yticklabels(names)
    ax.set_xlabel("BB/100 to the evolved agent"); ax.set_xlim(-560, 300)
    ax.grid(axis="x", color=RULE, linewidth=0.8, zorder=0)
    ax.legend(frameon=False, fontsize=lab, loc="upper left")
    fig.tight_layout(); fig.savefig(out, dpi=400 if "ieee" in out else 220, bbox_inches="tight")
    plt.close(fig)

render("/home/dheirav/pokerbot-scratch/fig4_evolution.png", 9, "DejaVu Sans", (6.6, 2.9), 8, 8.5)
render("/home/dheirav/pokerbot-scratch/ieee/fig4_evolution.png", 6.6, "DejaVu Serif", (3.35, 2.2), 5.8, 6.0)
print("rendered both sizes")
