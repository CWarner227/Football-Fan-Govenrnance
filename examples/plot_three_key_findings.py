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
            "1  Caps limited the wealthy attack",
            "Study 02 · proportional voting\n250,000 contribution; 300,000 actor budget",
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
    reference = get("02-wealthy", "Contribution 250,000", "proportional", "unprotected")
    defended = get("02-wealthy", "Contribution 250,000", "proportional", "defended")
    for y, row, color in [(0, reference, RED), (1, defended, TEAL)]:
        val = dot(ax, row, "capture_success", y, color)
        ax.barh(y, val, height=0.28, color=color, alpha=0.15)
    ax.set(ylim=(1.6, -0.6), xlim=(-0.08, 1.12), xlabel="Any-election capture probability")
    ax.set_yticks([0, 1], ["Unprotected", "Verification\n+ cap 5"])
    ax.set_xticks([0, 0.5, 1])
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    fig.text(0.055, 0.208, "100% → 0% capture", fontsize=17, fontweight="bold", color=TEAL)
    fig.text(
        0.055,
        0.15,
        "The tested package limited this single-contributor attack.\nVerification and the cap were applied together.",
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
            f"Day {day:.0f}",
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
    verification = get("05-turnout-h0.2-a1.0", "Verify 1", "equal", "defended")
    quorum = get("05-turnout-h0.2-a1.0", "Verify 1 + Quorum 0.4", "equal", "defended")
    for y, metric in [(0, "capture_success"), (1, "passed")]:
        ax.plot(
            [float(verification[metric + "_mean"]), float(quorum[metric + "_mean"])],
            [y, y],
            color="#c3ced3",
            lw=2,
        )
        dot(ax, verification, metric, y - 0.13, RED, 12)
        dot(ax, quorum, metric, y + 0.13, TEAL, -25)
    ax.set(ylim=(1.6, -0.6), xlim=(-0.08, 1.12), xlabel="Trial fraction")
    ax.set_yticks([0, 1], ["Any-election\ncapture", "Final proposal\npassage"])
    ax.set_xticks([0, 0.5, 1])
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    x = ax.get_position().x0
    fig.text(x, 0.69, "Verification only", fontsize=9, color=RED, fontweight="bold")
    fig.text(x + 0.115, 0.69, "+ 40% quorum", fontsize=9, color=TEAL, fontweight="bold")
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
        "Whiskers: pointwise 95% Wilson intervals (panels 1 and 3); n=100 per condition. Panel 2: observed mean first-capture day; all 100 trials captured.",
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
