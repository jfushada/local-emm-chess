# Figure for the paper: how well the planted subgroups are found, per quality
# measure and subgroup size, with the fix (min rho = 40) and without (min rho = 5).

# Run from the repo root, after src.synthetic_recovery:  python -m src.plot_synthetic
# Reads  results/synthetic_recovery_min_rho_40.csv  (and _5 if it exists) and plots
# the Dice similarity between the planted group and the best-matching subgroup
# Writes results/synthetic_recovery.png  (one column of the ACM layout, 3.4 in wide)

import matplotlib.pyplot as plt
import pandas as pd

from src import config
from src.synthetic_recovery import dice_from_jaccard

# categorical slots 1-3 of the shared palette (same blue/orange as the network figure),
# each with its own marker so the lines can be told apart without colour
MEASURES = {
    "mean":  ("mean (numerical)", "#2a78d6", "o"),
    "ks":    ("KS (numerical)", "#eb6834", "s"),
    "wracc": ("WRAcc (binary)", "#1baf7a", "^"),
}
BASELINE_COLOR = "#8a8984"   # grey: the original method
TEXT_COLOR = "#0b0b0b"
GRID_COLOR = "#e4e3df"


# mean Dice similarity per shift x size x measure, from the per-group results
def load_dice(min_rho):
    path = config.RESULTS_DIR / f"synthetic_recovery_min_rho_{min_rho}.csv"
    if not path.exists():
        return None
    out = pd.read_csv(path)
    out["sigma_dice"] = dice_from_jaccard(out["sigma_jaccard"])
    return out.groupby(["shift_sd", "size", "measure"], as_index=False)["sigma_dice"].mean()


def main():
    after = load_dice(40)
    before = load_dice(5)
    sizes = sorted(after["size"].unique())
    shifts = sorted(after["shift_sd"].unique())

    plt.rcParams.update({"font.size": 7, "axes.edgecolor": GRID_COLOR,
                         "xtick.color": TEXT_COLOR, "ytick.color": TEXT_COLOR})
    fig, axes = plt.subplots(1, len(sizes), figsize=(3.4, 1.9), sharey=True)

    for ax, size in zip(axes, sizes):
        for measure, (label, color, marker) in MEASURES.items():
            rows = after[(after["size"] == size) & (after["measure"] == measure)].sort_values("shift_sd")
            ax.plot(range(len(rows)), rows["sigma_dice"], color=color, marker=marker,
                    markersize=3.5, linewidth=1.2, label=label)
        if before is not None:
            rows = before[(before["size"] == size) & (before["measure"] == "mean")].sort_values("shift_sd")
            ax.plot(range(len(rows)), rows["sigma_dice"], color=BASELINE_COLOR,
                    linestyle="--", linewidth=1, label=r"mean, original ($\rho \geq 5$)")
        ax.set_title(f"size {size}", fontsize=7, color=TEXT_COLOR, pad=3)
        # the shifts as evenly spaced categories, so 0.5 and 1 don't overlap
        ax.set_xticks(range(len(shifts)))
        ax.set_xticklabels([f"{s:g}" for s in shifts])
        ax.set_xlim(-0.3, len(shifts) - 0.7)
        ax.set_ylim(0, 1.02)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
        ax.set_yticklabels(["0", "", "0.5", "", "1"])
        ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5)
        ax.tick_params(length=2, pad=1.5)
        for side in ["top", "right"]:
            ax.spines[side].set_visible(False)

    axes[0].set_ylabel("Dice with planted", color=TEXT_COLOR, labelpad=2)
    fig.supxlabel("planted shift (sd)", fontsize=7, color=TEXT_COLOR, y=0.02)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, fontsize=6.5,
               handlelength=1.8, columnspacing=1.2, bbox_to_anchor=(0.53, 1.02))
    fig.tight_layout(pad=0.3, rect=(0, 0.04, 1, 0.8))
    fig.subplots_adjust(wspace=0.12)

    out_file = config.RESULTS_DIR / "synthetic_recovery.pdf"
    fig.savefig(out_file, dpi=300, facecolor="white")
    print(f"Saved {out_file}")


if __name__ == "__main__":
    main()