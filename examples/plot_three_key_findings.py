"""Plot the three requested findings directly from audited condition estimates."""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/studies_01_07/figures"
TEAL, RED, INK, MUTED = "#127e83", "#c95843", "#203540", "#586d78"


def main():
    with (OUT.parent / "condition_results.csv").open(encoding="utf-8", newline="") as stream:
        data = list(csv.DictReader(stream))

    def get(group, condition, model, variant):
        rows = [
            r
            for r in data
            if (r["group"], r["condition"], r["model"], r["variant"])
            == (group, condition, model, variant)
        ]
        assert len(rows) == 1 and rows[0]["n"] == "100"
        return rows[0]

    def dot(ax, row, metric, y, color, dy=12):
        mean, low, high = [float(row[metric + suffix]) for suffix in ("_mean", "_low95", "_high95")]
        ax.errorbar(
            mean,
            y,
            xerr=[[max(0, mean - low)], [max(0, high - mean)]],
            fmt="o",
            color=color,
            markersize=9,
            capsize=4,
            lw=2,
            zorder=3,
        )
        ax.annotate(
            f"{mean:.0%}",
            (mean, y),
            xytext=(0, dy),
            textcoords="offset points",
            ha="center",
            fontsize=14,
            fontweight="bold",
            color=color,
        )
        return mean

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": MUTED,
            "ytick.color": INK,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.edgecolor": "#ccd9df",
        }
    )
    fig, axes = plt.subplots(1, 3, figsize=(19, 9), facecolor="#f4f7f8")
    fig.subplots_adjust(left=0.09, right=0.96, bottom=0.29, top=0.67, wspace=0.77)
    fig.text(
        0.045,
        0.945,
        "Three key findings from the governance simulations",
        fontsize=27,
        fontweight="bold",
    )
    fig.text(
        0.045,
        0.892,
        "Audited research results · 100 presentation trials per condition · selected synthetic scenarios",
        fontsize=14,
        color=MUTED,
    )
    headings = [
        (
            "1  Caps reduce concentration",
            "Study 01 · wealth-unequal profile\nFunding proposals; 10,000 supporters",
        ),
        (
            "2  Waiting delayed genuine infiltration",
            "Study 04 · equal voting\n20% honest turnout; 30% hostile target",
        ),
        (
            "3  Quorum could block decisions",
            "Study 05 · equal voting\n20% honest turnout; 100% hostile turnout",
        ),
    ]
    for ax, (title, context) in zip(axes, headings, strict=True):
        x = ax.get_position().x0
        fig.text(x - 0.035, 0.81, title, fontsize=15, fontweight="bold")
        fig.text(x - 0.035, 0.735, context, fontsize=11, color=MUTED, linespacing=1.5)
        ax.set_facecolor("white")
        ax.grid(axis="x", color="#e4ecef")
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0, pad=10)

    ax = axes[0]
    for y, model in enumerate(("proportional", "capped")):
        record = get("01-baseline", "Wealth unequal / funding", model, "control")
        for offset, metric, color in [(-0.17, "top_1_share", RED), (0.17, "bottom50_power", TEAL)]:
            val = float(record[metric + "_mean"])
            ax.barh(y + offset, val, height=0.28, color=color)
            ax.text(
                val + 0.012,
                y + offset,
                f"{val:.1%}",
                va="center",
                color=color,
                fontsize=13,
                fontweight="bold",
            )
    ax.set(ylim=(1.6, -0.6), xlim=(0, 0.55), xlabel="Mean share of potential voting power")
    ax.set_yticks([0, 1], ["Proportional", "Capped"])
    ax.set_xticks([0, 0.1, 0.2, 0.3, 0.4, 0.5])
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    x = ax.get_position().x0
    fig.text(x - 0.035, 0.69, "Most powerful 1%", fontsize=9, color=RED, fontweight="bold")
    fig.text(x + 0.105, 0.69, "Bottom half by wealth", fontsize=9, color=TEAL, fontweight="bold")
    fig.text(0.055, 0.208, "Top 1% power: 38.7% → 1.6%", fontsize=16, fontweight="bold", color=TEAL)
    fig.text(
        0.055,
        0.15,
        "The bottom half by wealth gained power: 2.3% → 28.2%.\nGroups are defined by voting power and wealth, respectively.",
        fontsize=10,
        color=MUTED,
        linespacing=1.45,
    )

    ax = axes[1]
    waits = [
        get("04-infiltration-t0.2-h0.3", f"Wait {days} days", "equal", "defended")
        for days in (0, 180)
    ]
    for y, row, color in [(0, waits[0], RED), (1, waits[1], TEAL)]:
        assert float(row["capture_success_mean"]) == 1 and row["time_to_capture_n"] == "100"
        day = float(row["time_to_capture_mean"])
        ax.hlines(y, 0, day, color=color, lw=6, alpha=0.22)
        ax.scatter(day, y, color=color, s=90, zorder=3)
        ax.annotate(
            f"{float(row['capture_success_mean']):.0%} captured",
            (day, y),
            xytext=(0, 14),
            textcoords="offset points",
            ha="center",
            fontsize=14,
            fontweight="bold",
            color=color,
        )
    ax.set(ylim=(1.6, -0.6), xlim=(-15, 365), xlabel="First capture: days from simulation start")
    ax.set_xticks([0, 90, 181, 365])
    ax.set_yticks([0, 1], ["No wait", "180-day wait"])
    fig.text(
        0.371,
        0.208,
        "91-day delay; capture stayed 100%",
        fontsize=16,
        fontweight="bold",
        color=TEAL,
    )
    fig.text(
        0.371,
        0.15,
        "Genuine entrants became eligible later.\nThe waiting period did not prevent capture within the year.",
        fontsize=10,
        color=MUTED,
        linespacing=1.45,
    )

    ax = axes[2]
    packages = [
        "Verify 1",
        "Verify 1 + Quorum 0.4",
        "Verify 1 + Incentive 0.2",
        "Verify 1 + Quorum 0.4 + Incentive 0.2",
    ]
    for y, package in enumerate(packages):
        record = get("05-turnout-h0.2-a1.0", package, "equal", "defended")
        dot(ax, record, "capture_success", y - 0.14, RED, 10)
        dot(ax, record, "passed", y + 0.14, TEAL, -22)
    ax.set(ylim=(3.6, -0.6), xlim=(-0.08, 1.12), xlabel="Trial fraction")
    ax.set_yticks(
        [0, 1, 2, 3],
        ["Verification only", "+ 40% quorum", "+ turnout incentive", "+ quorum + incentive"],
        fontsize=10,
    )
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1])
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    x = ax.get_position().x0
    fig.text(x - 0.035, 0.69, "Any-election capture", fontsize=9, color=RED, fontweight="bold")
    fig.text(x + 0.115, 0.69, "Final proposal passage", fontsize=9, color=TEAL, fontweight="bold")
    fig.text(
        0.695, 0.208, "42% capture; passage 100% → 0%", fontsize=16, fontweight="bold", color=TEAL
    )
    fig.text(
        0.695,
        0.15,
        "Quorum was never met at the final election.\nBlocking passage did not remove hostile cast-weight dominance.",
        fontsize=10,
        color=MUTED,
        linespacing=1.45,
    )

    fig.text(
        0.045,
        0.092,
        "Takeaway: contribution limits, membership timing and decision-validity rules address different governance risks.",
        fontsize=15,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.045,
        0.047,
        "Panel 1: mean potential power shares. Panel 2: endpoint labels show trials captured within the year; x-axis shows mean first-capture day. Panel 3: 95% Wilson intervals.",
        fontsize=10,
        color=MUTED,
    )
    fig.text(
        0.045,
        0.022,
        "Capture = hostile majority of cast voting weight at any election; passage = approval at the final election with quorum. Synthetic assumptions; no universal ranking or real-club forecast.",
        fontsize=9,
        color=MUTED,
    )
    for extension in ("png", "svg"):
        fig.savefig(
            OUT / ("three_key_findings." + extension), dpi=200, facecolor=fig.get_facecolor()
        )
    plt.close(fig)
    print("Created three_key_findings.png and .svg")


if __name__ == "__main__":
    main()
