"""Create a compact synthesis of selected audited research-report findings."""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/studies_01_07/figures"
TEAL, RED, INK, MUTED = "#127e83", "#c95843", "#203540", "#586d78"


def main():
    with (OUT.parent / "condition_results.csv").open(encoding="utf-8", newline="") as stream:
        data = list(csv.DictReader(stream))

    def row(group, condition, model, variant):
        selected = [
            r
            for r in data
            if (r["group"], r["condition"], r["model"], r["variant"])
            == (group, condition, model, variant)
        ]
        assert len(selected) == 1 and selected[0]["n"] == "100"
        return selected[0]

    def value(record, metric):
        return float(record[metric + "_mean"])

    def point(ax, record, metric, y, color, offset=0):
        mean = value(record, metric)
        low, high = [float(record[metric + suffix]) for suffix in ("_low95", "_high95")]
        ax.errorbar(
            mean,
            y + offset,
            xerr=[[max(0, mean - low)], [max(0, high - mean)]],
            fmt="o",
            color=color,
            capsize=3,
            markersize=7,
            lw=1.7,
            zorder=4,
        )
        ax.annotate(
            f"{mean:.0%}",
            (mean, y + offset),
            xytext=(0, 11 if offset <= 0 else -19),
            textcoords="offset points",
            ha="center",
            color=color,
            fontsize=10,
            fontweight="bold",
        )

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
            "axes.edgecolor": "#cfdbdf",
        }
    )
    fig = plt.figure(figsize=(18, 13), facecolor="#f4f7f8")
    grid = fig.add_gridspec(
        2, 2, left=0.18, right=0.96, top=0.81, bottom=0.20, wspace=0.72, hspace=0.72
    )
    axes = [fig.add_subplot(grid[i, j], facecolor="white") for i in range(2) for j in range(2)]
    fig.text(
        0.055,
        0.956,
        "Funding without concentrated control requires layered safeguards",
        fontsize=24,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.917,
        "Selected findings from Studies 01–07 · 95 completed configurations · 100 presentation trials per condition",
        fontsize=13,
        color=MUTED,
    )
    fig.text(
        0.055,
        0.882,
        "Caps and identity checks address different threats. Waiting, quorum and capital offers each have limits.",
        fontsize=14,
        color=TEAL,
        fontweight="bold",
    )

    # A: means of eligible potential power, not a probability of capture.
    ax = axes[0]
    records = [
        row("01-baseline", "Wealth unequal / funding", model, "control")
        for model in ("proportional", "capped")
    ]
    y = np.arange(2)
    for offset, metric, label, color in [
        (-0.17, "top_1_share", "Most powerful 1%", RED),
        (0.17, "bottom50_power", "Bottom half by wealth", TEAL),
    ]:
        vals = [float(r[metric + "_mean"]) for r in records]
        ax.barh(y + offset, vals, height=0.28, color=color, label=label)
        for pos, val in zip(y + offset, vals, strict=True):
            ax.text(
                val + 0.012,
                pos,
                f"{val:.1%}",
                va="center",
                fontsize=11,
                color=color,
                fontweight="bold",
            )
    ax.set_yticks(y, ["Proportional", "Capped"])
    ax.invert_yaxis()
    ax.set(xlim=(0, 0.55), xlabel="Mean share of potential voting power")
    ax.set_title(
        "A  |  Caps reduce concentration", loc="left", fontsize=15, fontweight="bold", pad=42
    )
    ax.text(
        0,
        1.09,
        "Wealth-unequal profile · funding proposals · 10,000 supporters",
        transform=ax.transAxes,
        fontsize=10,
        color=MUTED,
    )
    ax.legend(loc="lower right", fontsize=9, frameon=False)

    # B: within-condition contrasts; each row has its own threat and rule.
    ax = axes[1]
    cases = [
        (
            row("02-wealthy", "Contribution 250,000", "proportional", "unprotected"),
            row("02-wealthy", "Contribution 250,000", "proportional", "defended"),
        ),
        (
            row("03-sybil-v1", "400 attempted aliases", "equal", "unprotected"),
            row("03-sybil-v1", "400 attempted aliases", "equal", "defended"),
        ),
        (
            row("04-infiltration-t0.2-h0.3", "Wait 0 days", "equal", "defended"),
            row("04-infiltration-t0.2-h0.3", "Wait 180 days", "equal", "defended"),
        ),
    ]
    for i, (reference, intervention) in enumerate(cases):
        ax.plot(
            [value(reference, "capture_success"), value(intervention, "capture_success")],
            [i, i],
            color="#c3ced3",
            lw=2,
        )
        point(ax, reference, "capture_success", i, RED, -0.12)
        point(ax, intervention, "capture_success", i, TEAL, 0.12)
    ax.set_yticks(
        range(3),
        [
            "Wealthy contributor\n250k; proportional\n→ verification + cap 5",
            "400 fraudulent aliases\nequal voting\n→ full verification",
            "Genuine entrants\nequal; turnout 20%; hostile 30%\n→ wait 0 to 180 days",
        ],
        fontsize=9,
    )
    ax.set(ylim=(2.6, -0.6), xlim=(-0.07, 1.07), xlabel="Any-election capture probability")
    ax.set_title(
        "B  |  Protection depends on the threat", loc="left", fontsize=15, fontweight="bold", pad=42
    )
    ax.text(0, 1.09, "Reference", color=RED, transform=ax.transAxes, fontweight="bold", fontsize=10)
    ax.text(
        0.28,
        1.09,
        "Configured intervention",
        color=TEAL,
        transform=ax.transAxes,
        fontweight="bold",
        fontsize=10,
    )
    ax.text(
        0,
        -0.30,
        "Waiting delayed first capture: day 90 → 181; annual capture stayed 100%.",
        transform=ax.transAxes,
        fontsize=9,
        color=MUTED,
    )

    # C: capture and passage are explicitly different endpoints.
    ax = axes[2]
    packages = [
        "Verify 1",
        "Verify 1 + Quorum 0.4",
        "Verify 1 + Incentive 0.2",
        "Verify 1 + Quorum 0.4 + Incentive 0.2",
    ]
    for i, package in enumerate(packages):
        record = row("05-turnout-h0.2-a1.0", package, "equal", "defended")
        point(ax, record, "capture_success", i, RED, -0.14)
        point(ax, record, "passed", i, TEAL, 0.14)
    ax.set_yticks(
        range(4),
        ["Verification only", "+ 40% quorum", "+ turnout incentive", "+ quorum + incentive"],
        fontsize=10,
    )
    ax.set(ylim=(3.6, -0.6), xlim=(-0.07, 1.07), xlabel="Trial fraction")
    ax.set_title(
        "C  |  Quorum can stop decisions, not capture",
        loc="left",
        fontsize=14,
        fontweight="bold",
        pad=50,
    )
    ax.text(
        0,
        1.15,
        "Equal voting · honest turnout 20% · hostile turnout 100%",
        transform=ax.transAxes,
        fontsize=10,
        color=MUTED,
    )
    ax.text(
        0,
        1.06,
        "Any-election capture",
        color=RED,
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
    )
    ax.text(
        0.52,
        1.06,
        "Final proposal passage",
        color=TEAL,
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
    )

    # D: acceptance probability, not the nominal amount of an offer.
    ax = axes[3]
    for i, severity in enumerate((0.3, 0.7)):
        record = row(
            "07-economics", f"N=100; fee=0; downturn={severity}; capital=30k", "equal", "defended"
        )
        point(ax, record, "outside_capital_received", i, TEAL)
    ax.set_yticks(
        [0, 1], ["Milder downturn\nseverity 0.3", "Harsher downturn\nseverity 0.7"], fontsize=10
    )
    ax.set(
        ylim=(1.55, -0.55),
        xlim=(-0.07, 1.07),
        xlabel="Probability the 30k capital offer is received",
    )
    ax.set_title(
        "D  |  Offered capital is not guaranteed cash",
        loc="left",
        fontsize=14,
        fontweight="bold",
        pad=50,
    )
    ax.text(
        0,
        1.15,
        "100 supporters · no fee · capital carries no voting rights",
        transform=ax.transAxes,
        fontsize=10,
        color=MUTED,
    )
    ax.text(
        0,
        -0.30,
        "All 16 economic cells stayed solvent; the grid did not reach a failure boundary.",
        transform=ax.transAxes,
        fontsize=9,
        color=MUTED,
    )

    for ax in axes:
        ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.grid(axis="x", color="#e4ecef", lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0, pad=10)
    fig.text(
        0.055,
        0.112,
        "CRISIS EXTENSION: a budget artifact, not proof of protection",
        fontsize=13,
        color="#945b20",
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.087,
        "The 100k-contribution attacker spent its entire budget and expired for unpaid fees on day 31, before voting. A maintained-attack follow-up is needed.",
        fontsize=11,
        color=INK,
    )
    fig.text(
        0.055,
        0.044,
        "Whiskers: pointwise 95% Wilson intervals, n=100 per condition (panels B–D). Panel A shows means. Zero observed capture still permits a 3.7% upper bound.",
        fontsize=9,
        color=MUTED,
    )
    fig.text(
        0.055,
        0.023,
        "Synthetic, uncalibrated assumptions; selected conditions are not pooled or a universal ranking. Pilots excluded. Source: audited Studies 01–07 report, 10 November 2026.",
        fontsize=9,
        color=MUTED,
    )
    for suffix in ("png", "svg"):
        fig.savefig(
            OUT / ("key_findings_synthesis." + suffix), dpi=200, facecolor=fig.get_facecolor()
        )
    plt.close(fig)
    print("Created key_findings_synthesis.png and .svg from audited 100-trial condition estimates")


if __name__ == "__main__":
    main()
