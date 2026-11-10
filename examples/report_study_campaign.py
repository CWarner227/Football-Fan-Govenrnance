"""Analyze completed frozen studies; refuse incomplete confirmatory datasets.

Writes CSV tables, publication figures and report source under reports/studies_01_07.
No dashboard comparison endpoints or pre-aggregated confidence bounds are pooled.
"""

import csv
import hashlib
import json
import math
import platform
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results/study_campaign"
OUT = ROOT / "reports/studies_01_07"
MODELS = ["equal", "proportional", "capped", "diminishing", "hybrid", "expertise"]
COLORS = ["#127e83", "#c95843", "#5274ae", "#9272a5", "#b18a32", "#576778"]


def table_path(folder, table):
    path = folder / (table + ".jsonl")
    return path if path.exists() else folder / (table + ".json")


def table_rows(folder, table):
    path = table_path(folder, table)
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)
    else:
        yield from json.loads(path.read_text(encoding="utf-8"))


def condition_identity(parameters):
    """Canonical numeric JSON spelling; preserve booleans and every grid setting."""

    def normalize(value):
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, (float, int)):
            return float(value)
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value

    payload = json.dumps(normalize(parameters), sort_keys=True, allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def wilson(k, n):
    if not 0 <= k <= n or n <= 0:
        raise ValueError("Invalid binomial counts")
    z = 1.959963984540054
    p = k / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def condition_label(group, row):
    if group.startswith("01"):
        pop = row["simulation.population"]
        profile = (
            "Low participation"
            if pop["participation_rate"].get("value") == 0.15
            else "Wealth unequal"
            if pop["wealth"]["sigma"] == 2
            else "Ordinary"
        )
        return profile + " / " + row["simulation.proposal.category"]
    if group.startswith("02"):
        return f"Contribution {row['attacks.0.parameters.contribution_budget']:,.0f}"
    if group.startswith("03"):
        return f"{row['attacks'][0]['parameters']['attempted_identities']} attempted aliases"
    if group.startswith("04"):
        return f"Wait {row['defenses.1.parameters.days']} days"
    if group.startswith(("05", "06")):
        labels = []
        for defense in row["defenses"]:
            name, p = defense["name"], defense["parameters"]
            labels.append(
                {
                    "identity_verification": f"Verify {p.get('strength', 1):g}",
                    "waiting_period": f"Wait {p.get('days', 0)}d",
                    "vote_cap": f"Cap {p.get('cap', 0):g}",
                    "quorum": f"Quorum {p.get('threshold', 0):g}",
                    "participation_incentive": f"Incentive {p.get('boost', 0):g}",
                    "suspicious_activity": p.get("review_policy", "Review"),
                }.get(name, name)
            )
        return " + ".join(labels)
    if group == "07-economics":
        return f"N={row['simulation.population.size']}; fee={row['economics.membership_fee']:g}; downturn={row['economics.shocks.0.severity']:g}; capital={'30k' if row['economics.investors'] else '0'}"
    return f"Revenue loss {row['economics.shocks.0.severity']:g}; attacker {row['attacks.0.parameters.contribution_budget']:g}"


def write_csv(name, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (OUT / name).open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_data(require_complete=True, groups=None, compact=False):
    ledger = json.loads((DATA / "ledger.json").read_text())
    if require_complete and (
        len(ledger) != 95 or any(r["status"] != "completed" for r in ledger.values())
    ):
        raise ValueError("All 95 configurations must complete before final analysis")
    summaries, elections, times = [], [], []
    provenance = []
    for key, entry in ledger.items():
        if entry["status"] != "completed":
            continue
        if groups is not None and entry["group"] not in groups:
            continue
        folder = DATA / key
        record = json.loads((folder / "record.json").read_text())
        config = record["configuration"]
        seed = config["experiment"]["seed"]
        provenance.append(
            dict(
                group=entry["group"],
                stage=entry["stage"],
                run_id=entry["run_id"],
                seed=seed,
                engine_version=record["engine_version"],
                seconds=record["elapsed_seconds"],
                summary_sha256=hashlib.sha256(
                    table_path(folder, "summary").read_bytes()
                ).hexdigest(),
            )
        )
        grid_metadata = {}
        for row in table_rows(folder, "summary"):
            grid_metadata[row["grid_id"]] = {key: row[key] for key in config["experiment"]["grid"]}
        for table, destination in (
            ("summary", summaries),
            ("elections", elections),
            ("timeseries", times),
        ):
            if compact and table == "elections" and entry["group"] != "04-infiltration-t0.2-h0.3":
                continue
            if compact and table == "timeseries" and entry["group"] != "07-economics":
                continue
            for row in table_rows(folder, table):
                if (
                    compact
                    and table != "summary"
                    and (row["voting_model"] != "equal" or row["variant"] != "defended")
                ):
                    continue
                row.update(grid_metadata[row["grid_id"]])
                parameters = grid_metadata[row["grid_id"]]
                row["original_grid_id"] = row["grid_id"]
                row["grid_id"] = condition_identity(parameters)
                if "capital_raised" in row:
                    row["outside_capital_received"] = row["capital_raised"] > 0
                row.update(
                    group=entry["group"], stage=entry["stage"], seed=seed, run_id=entry["run_id"]
                )
                destination.append(row)
    return summaries, elections, times, provenance


def aggregate(rows, expected_n):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["group"], row["grid_id"], row["voting_model"], row["variant"])].append(row)
    output = []
    metrics = [
        "capture_success",
        "passed",
        "quorum_achieved",
        "financially_survived",
        "outcome_differs_from_equal",
        "outcome_changed",
        "attacker_power_share",
        "attacker_vote_share",
        "gini",
        "effective_voters",
        "top_1_share",
        "top_10_share",
        "turnout",
        "cash_balance",
        "membership_retention",
        "financial_runway_months",
        "defense_administrative_cost",
        "legitimate_rejection_rate",
        "fraudulent_identities_accepted",
        "fraudulent_identities_detected",
        "time_to_capture",
        "financial_spent",
        "capital_raised",
        "investor_concentration",
        "outside_capital_received",
        "hostile_population_share",
        "hostile_membership_survival",
        "proposals_influenced",
        "legitimate_supporters_restricted",
        "false_positive_rate",
        "false_negative_rate",
        "recovery_time_after_shocks_days",
    ]
    binary = set(metrics[:6]) | {"outside_capital_received"}
    for (group, grid, model, variant), values in groups.items():
        identities = {(v["seed"], v["trial"]) for v in values}
        if len(values) != expected_n or len(identities) != expected_n:
            raise ValueError(
                f"Missing/duplicate observations: {group}/{grid}/{model}/{variant}: {len(values)}, {len(identities)}"
            )
        if expected_n == 100 and identities != {
            (seed, trial) for seed in (11001, 11002, 11003, 11004) for trial in range(25)
        }:
            raise ValueError("Presentation observations do not match the frozen four-batch design")
        if expected_n == 10 and identities != {(99001, trial) for trial in range(10)}:
            raise ValueError("Pilot observations do not match the frozen pilot design")
        result = dict(
            group=group,
            condition_id=grid,
            source_grid_ids=";".join(sorted({v.get("original_grid_id", grid) for v in values})),
            condition=condition_label(group, values[0]),
            model=model,
            variant=variant,
            n=len(values),
        )
        for metric in metrics:
            sample = [float(v[metric]) for v in values if v.get(metric) is not None]
            result[metric + "_n"] = len(sample)
            if not sample:
                continue
            result[metric + "_mean"] = float(np.mean(sample))
            if metric in binary:
                lo, hi = wilson(sum(sample), len(sample))
                result[metric + "_low95"], result[metric + "_high95"] = lo, hi
            else:
                for q, val in zip(
                    ("p025", "median", "p975"),
                    np.quantile(sample, [0.025, 0.5, 0.975]),
                    strict=True,
                ):
                    result[metric + "_" + q] = float(val)
        representation = [
            v["representation"]["potential"]["bottom_50_wealth_power_share"] for v in values
        ]
        result["bottom50_power_mean"] = float(np.mean(representation))
        output.append(result)
    return output


def paired_contrasts(rows):
    groups = defaultdict(dict)
    for row in rows:
        key = row["group"], row["grid_id"], row["voting_model"], row["seed"], row["trial"]
        groups[key][row["variant"]] = row
    contrasts = defaultdict(list)
    for (group, grid, model, _seed, _trial), variants in groups.items():
        if set(variants) != {"control", "unprotected", "defended"}:
            raise ValueError("Incomplete paired variants")
        for metric in (
            "capture_success",
            "passed",
            "quorum_achieved",
            "cash_balance",
            "membership_retention",
        ):
            u, d = variants["unprotected"].get(metric), variants["defended"].get(metric)
            if u is not None and d is not None:
                contrasts[(group, grid, model, metric)].append(float(d) - float(u))
    output = []
    for (group, grid, model, metric), sample in contrasts.items():
        mean = float(np.mean(sample))
        # Distribution-free Hoeffding bound for independent trial-level differences.
        # Binary differences lie in [-1,1]; avoids false zero-width intervals for
        # all-zero discordance. Conservative; no multiplicity adjustment.
        half = (
            math.sqrt(2 * math.log(40) / len(sample))
            if metric in ("capture_success", "passed", "quorum_achieved")
            else None
        )
        output.append(
            dict(
                group=group,
                condition_id=grid,
                model=model,
                metric=metric,
                n=len(sample),
                defended_minus_unprotected=mean,
                conservative_low95=max(-1, mean - half) if half is not None else "",
                conservative_high95=min(1, mean + half) if half is not None else "",
                defended_lower=sum(x < 0 for x in sample),
                defended_higher=sum(x > 0 for x in sample),
                tied=sum(x == 0 for x in sample),
            )
        )
    return output


def save_figure(fig, name):
    fig.savefig(OUT / "figures" / (name + ".png"), dpi=180, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / "figures" / (name + ".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def heatmap(
    stats, prefix, metric, name, title, variants=("unprotected", "defended"), footer_note=None
):
    selected = [r for r in stats if r["group"].startswith(prefix)]
    conditions = list(
        dict.fromkeys((r["group"], r["condition_id"], r["condition"]) for r in selected)
    )
    fig, axes = plt.subplots(
        1, len(variants), figsize=(14, max(4, len(conditions) * 0.4)), squeeze=False
    )
    for axis_index, (ax, variant) in enumerate(zip(axes[0], variants, strict=True)):
        lookup = {
            (r["group"], r["condition_id"], r["model"]): r.get(metric + "_mean", np.nan)
            for r in selected
            if r["variant"] == variant
        }
        matrix = np.array(
            [[lookup.get((g, cell, m), np.nan) for m in MODELS] for g, cell, label in conditions]
        )
        image = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(6), MODELS, rotation=40, ha="right")
        labels = [
            g.replace(prefix, "")
            .replace("infiltration-", "")
            .replace("turnout-", "")
            .replace("defenses-", "")
            .replace("sybil-", "")
            .strip("-")
            + ": "
            + label
            for g, cell, label in conditions
        ]
        ax.set_yticks(
            range(len(conditions)),
            labels if axis_index == 0 else [""] * len(conditions),
            fontsize=9,
        )
        for (i, j), value in np.ndenumerate(matrix):
            ax.text(
                j,
                i,
                f"{value:.0%}",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if value > 0.65 else "#20313c",
            )
        ax.set_title(variant.title())
    fig.suptitle(
        title + "\n100 trials per displayed condition/model; cells are separate estimates",
        fontsize=13,
    )
    fig.subplots_adjust(
        left=0.4,
        right=0.88,
        top=1 - 0.9 / fig.get_size_inches()[1],
        bottom=0.25 if footer_note else 0.15,
        wspace=0.12,
    )
    if footer_note:
        fig.text(0.04, 0.01, footer_note, fontsize=9, color="#576778")
    color_axis = fig.add_axes((0.92, 0.22, 0.012, 0.5))
    fig.colorbar(image, cax=color_axis, label="Trial fraction")
    save_figure(fig, name)


def figures(stats, rows, times):
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    # Baseline potential concentration versus bottom-half representation.
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for profile, marker in (("Ordinary", "o"), ("Wealth unequal", "s"), ("Low participation", "^")):
        items = [
            next(
                r
                for r in stats
                if r["group"] == "01-baseline"
                and r["variant"] == "control"
                and r["model"] == model
                and r["condition"] == profile + " / funding"
            )
            for model in MODELS
        ]
        for ax, metric in zip(axes, ("top_1_share_mean", "bottom50_power_mean"), strict=True):
            ax.plot(MODELS, [r[metric] for r in items], marker=marker, label=profile)
            ax.tick_params(axis="x", rotation=40)
            ax.set_ylim(0, 1)
            ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    axes[0].set_title("Most powerful 1%: potential power share")
    axes[1].set_title("Bottom 50% by wealth: potential power share")
    axes[0].legend(fontsize=8)
    fig.suptitle("Study 01 · Funding decisions · means of 100 trials per condition")
    fig.tight_layout()
    save_figure(fig, "01_baseline_representation")
    heatmap(
        stats,
        "02-",
        "capture_success",
        "02_wealth_capture",
        "Study 02 · Any-election hostile cast-weight capture",
    )
    heatmap(
        stats,
        "03-",
        "capture_success",
        "03_sybil_capture",
        "Study 03 · Verification strength and attempted aliases",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    strengths = [0, 0.8, 1]
    selected = [
        next(
            r
            for r in stats
            if r["group"] == f"03-sybil-v{strength}"
            and r["condition"] == "200 attempted aliases"
            and r["model"] == "equal"
            and r["variant"] == "defended"
        )
        for strength in strengths
    ]
    for ax, metric, divisor, title in zip(
        axes,
        ("fraudulent_identities_accepted", "legitimate_rejection_rate"),
        (200, 1),
        ("Fraudulent aliases accepted / 200 attempts", "Legitimate verification rejection rate"),
        strict=True,
    ):
        mean = np.array([r[metric + "_mean"] / divisor for r in selected])
        lower = np.array([r[metric + "_p025"] / divisor for r in selected])
        upper = np.array([r[metric + "_p975"] / divisor for r in selected])
        ax.plot(strengths, mean, marker="o", color=COLORS[0])
        ax.fill_between(strengths, lower, upper, color=COLORS[0], alpha=0.15)
        ax.set(xlabel="Configured verification strength", ylabel="Fraction", title=title)
        ax.set_xticks(strengths)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
        ax.set_ylim(bottom=0)
    fig.suptitle(
        "Study 03 · Equal / defended · 100 trials per condition\nMean and central 95% trial range; error rates are synthetic assumptions"
    )
    fig.tight_layout()
    save_figure(fig, "03_verification_errors")
    heatmap(
        stats,
        "04-",
        "capture_success",
        "04_infiltration_capture",
        "Study 04 · Genuine hostile entrants and waiting periods",
    )
    heatmap(stats, "05-", "capture_success", "05_turnout_capture", "Study 05 · Low-turnout capture")
    heatmap(
        stats,
        "05-",
        "passed",
        "05_turnout_passage",
        "Study 05 · Final-election proposal passage (not capture)",
    )
    heatmap(
        stats,
        "05-",
        "quorum_achieved",
        "05_turnout_quorum",
        "Study 05 · Final-election quorum achieved",
    )
    heatmap(
        stats,
        "06-",
        "capture_success",
        "06_defense_capture",
        "Study 06 · Ten configured defense packages",
    )
    heatmap(
        stats,
        "07-combined",
        "capture_success",
        "07_combined_capture",
        "Study 07 extension · Funding and fee-budget exhaustion",
        footer_note="100k contribution exhausts the actor budget; fee-driven expiry precedes voting. Zero capture does not establish defense efficacy.",
    )
    # Calendar capture: genuine entrants may pass verification and age into eligibility.
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    chosen = [
        r
        for r in rows
        if r["group"] == "04-infiltration-t0.2-h0.3"
        and r["variant"] == "defended"
        and r["voting_model"] == "equal"
    ]
    for wait in (0, 90, 180):
        sample = [r for r in chosen if r["defenses.1.parameters.days"] == wait]
        for ax, metric in zip(axes, ("attacker_vote_share", "capture_success"), strict=True):
            days = sorted({r["day"] for r in sample})
            means = [np.mean([r[metric] for r in sample if r["day"] == day]) for day in days]
            ax.plot(days, means, marker="o", label=f"Wait {wait} days")
            ax.set_xlabel("Days from start")
            ax.set_ylim(0, 1)
            ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    axes[0].set_title("Mean hostile share of votes cast")
    axes[1].set_title("Capture at each election")
    axes[0].legend()
    fig.suptitle("Study 04 · Equal voting · honest turnout 0.2, target hostile share 0.3")
    fig.tight_layout()
    save_figure(fig, "04_waiting_calendar")
    # Economics uses equal voting as a representative bookkeeping trajectory,
    # avoiding six copies of the same financial path as independent observations.
    selected = [
        r
        for r in stats
        if r["group"] == "07-economics" and r["model"] == "equal" and r["variant"] == "defended"
    ]
    selected.sort(key=lambda r: r["condition"])
    fig, axes = plt.subplots(1, 2, figsize=(13, 7))
    labels = [
        r["condition"]
        .replace("N=", "")
        .replace("fee=", "")
        .replace("downturn=", "")
        .replace("capital=", "")
        .replace("; ", " | ")
        for r in selected
    ]
    y = np.arange(len(selected))
    for ax, metric, title in zip(
        axes,
        ("cash_balance", "membership_retention"),
        ("Final cash (arbitrary monetary units)", "Final membership retention"),
        strict=True,
    ):
        med = np.array([r[metric + "_median"] for r in selected])
        low = np.array([r[metric + "_p025"] for r in selected])
        high = np.array([r[metric + "_p975"] for r in selected])
        ax.errorbar(
            med, y, xerr=np.array([med - low, high - med]), fmt="o", color=COLORS[0], capsize=2
        )
        ax.set_yticks(y, labels, fontsize=7)
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.2)
    axes[1].xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    axes[0].set_ylabel("Population | fee | downturn | capital offered")
    fig.suptitle("Study 07 · Equal / defended · median and central 95% trial range (not mean CI)")
    fig.tight_layout()
    save_figure(fig, "07_economic_outcomes")
    fig, ax = plt.subplots(figsize=(10, 5))
    chosen_times = [
        r
        for r in times
        if r["group"] == "07-economics"
        and r["voting_model"] == "equal"
        and r["variant"] == "defended"
        and r["economics.membership_fee"] == 0
        and r["simulation.population.size"] == 100
    ]
    for severity in (0.3, 0.7):
        for capital in (False, True):
            sample = [
                r
                for r in chosen_times
                if r["economics.shocks.0.severity"] == severity
                and bool(r["economics.investors"]) == capital
            ]
            months = sorted({r["month"] for r in sample})
            arrays = [
                np.array([r["cash_balance"] for r in sample if r["month"] == month])
                for month in months
            ]
            (line,) = ax.plot(
                months,
                [np.median(a) for a in arrays],
                label=f"Downturn {severity}; capital {'30k' if capital else '0'}",
            )
            ax.fill_between(
                months,
                [np.quantile(a, 0.025) for a in arrays],
                [np.quantile(a, 0.975) for a in arrays],
                color=line.get_color(),
                alpha=0.1,
            )
    ax.axhline(0, color="black", lw=0.8)
    ax.set(
        xlabel="Month",
        ylabel="Cash (arbitrary monetary units)",
        title="Study 07 · N=100, fee=0 · equal / defended\nMedian and central 95% trial range; 100 trials per line",
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    save_figure(fig, "07_cash_trajectories")
    # Conceptual model diagram, explicitly separating rights from ownership.
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axis("off")
    boxes = [
        ("Supporters + funding", 0.04, 0.7),
        ("Identity + membership\nverification / waiting", 0.35, 0.7),
        ("Eligibility + turnout\nballots + voting weights", 0.68, 0.7),
        ("Hostile actor\nfinite money / operations", 0.04, 0.25),
        ("Club cash + membership\nfees / shocks / outside capital", 0.35, 0.25),
        ("Separate outcomes\ncapture / passage / solvency", 0.68, 0.25),
    ]
    for label, x, y in boxes:
        ax.text(
            x,
            y,
            label,
            transform=ax.transAxes,
            ha="left",
            va="center",
            bbox=dict(boxstyle="round,pad=.7", facecolor="#e7f2f2", edgecolor=COLORS[0]),
            fontsize=11,
        )
    for start, end in [
        ((0.25, 0.7), (0.34, 0.7)),
        ((0.59, 0.7), (0.67, 0.7)),
        ((0.82, 0.59), (0.82, 0.36)),
        ((0.25, 0.25), (0.34, 0.62)),
        ((0.59, 0.25), (0.67, 0.25)),
        ((0.48, 0.36), (0.48, 0.59)),
    ]:
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            xycoords="axes fraction",
            arrowprops=dict(arrowstyle="->", color="#576778", lw=1.5),
        )
    ax.set_title(
        "Research mechanism: broad funding, bounded voting power, and layered defenses\nOwnership capital creates voting rights only under an explicit policy",
        fontsize=13,
    )
    save_figure(fig, "00_research_mechanism")
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.axis("off")
    for text, x, y, color in [
        ("19 study groups\n76 design cells", 0.13, 0.73, "#e7f2f2"),
        ("4 seeds x 25 trials\n100 trial draws per cell", 0.48, 0.73, "#e7f2f2"),
        ("6 models x 3 variants\n18 related trajectories per draw", 0.83, 0.73, "#e7f2f2"),
        (
            "19 pilots: 10 trials per cell\nSeparate checks; excluded from final estimates",
            0.30,
            0.23,
            "#fff2da",
        ),
        (
            "Condition-level estimates + paired contrasts\n7,600 trial/cell draws; 136,800 summaries",
            0.75,
            0.23,
            "#e7f2f2",
        ),
    ]:
        ax.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=11,
            bbox=dict(boxstyle="round,pad=.8", facecolor=color, edgecolor="#576778"),
        )
    for start, end in [
        ((0.26, 0.73), (0.34, 0.73)),
        ((0.62, 0.73), (0.69, 0.73)),
        ((0.83, 0.59), (0.79, 0.38)),
    ]:
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            xycoords="axes fraction",
            arrowprops=dict(arrowstyle="->", lw=1.5, color="#127e83"),
        )
    ax.set_title(
        "Sampling design: models, variants and calendar elections are not extra independent trials",
        fontsize=13,
    )
    save_figure(fig, "00_study_design")


def audit_exports(manifests):
    """Stream full artifact counts and all cash transitions without retaining paths."""
    ledger = json.loads((DATA / "ledger.json").read_text())
    source_hashes = set()
    economic_rows = transitions = presentation_elections = presentation_times = hashes_verified = 0
    for key, entry in ledger.items():
        manifest = manifests[entry["run_id"]]["manifest"]
        source_hashes.add(manifest["metadata"]["source"]["source_sha256"])
        previous_cash = {}
        for table in ("summary", "elections", "timeseries", "aggregate", "defense_effectiveness"):
            path = table_path(DATA / key, table)
            original_hash = manifests[entry["run_id"]].get("artifact_sha256", {}).get(table)
            if original_hash and path.suffix == ".jsonl":
                with path.open("rb") as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != original_hash:
                        raise ValueError(f"Copied artifact hash differs from source: {key}/{table}")
                hashes_verified += 1
            if table != "timeseries" and path.suffix == ".jsonl":
                with path.open("rb") as stream:
                    count = sum(bool(line.strip()) for line in stream)
            else:
                count = 0
                for row in table_rows(DATA / key, table):
                    count += 1
                    if table != "timeseries" or "opening_cash" not in row:
                        continue
                    economic_rows += 1
                    expected = (
                        row["opening_cash"]
                        + row["operating_surplus"]
                        + row["financing_cashflow"]
                        + row["investing_cashflow"]
                    )
                    if not math.isclose(expected, row["cash_balance"], rel_tol=1e-9, abs_tol=1e-6):
                        raise ValueError(f"Financial reconciliation failure: {key}")
                    identity = row["grid_id"], row["trial"], row["voting_model"], row["variant"]
                    if identity in previous_cash:
                        month, closing = previous_cash[identity]
                        transitions += 1
                        if row["month"] <= month or not math.isclose(
                            closing, row["opening_cash"], rel_tol=1e-9, abs_tol=1e-6
                        ):
                            raise ValueError(f"Financial period continuity failure: {key}")
                    previous_cash[identity] = row["month"], row["cash_balance"]
            if count != manifest["row_counts"][table]:
                raise ValueError(
                    f"Export row count differs from scientific manifest: {key}/{table}"
                )
            if entry["stage"] != "pilot":
                if table == "elections":
                    presentation_elections += count
                elif table == "timeseries":
                    presentation_times += count
    if len(source_hashes) != 1:
        raise ValueError("Campaign contains different engine source hashes; review before pooling")
    return dict(
        economic_period_rows_reconciled=economic_rows,
        financial_reconciliation_failures=0,
        cash_transitions_checked=transitions,
        presentation_elections=presentation_elections,
        presentation_timeseries_rows=presentation_times,
        source_sha256=next(iter(source_hashes)),
        manifest_row_counts_verified=True,
        copied_artifact_hashes_verified=hashes_verified,
    )


def main():
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    manifests = json.loads((OUT / "source_manifests.json").read_text())
    verified = audit_exports(manifests)
    summaries, elections, times, provenance = load_data(compact=True)
    confirmatory = [r for r in summaries if r["stage"] != "pilot"]
    pilots = [r for r in summaries if r["stage"] == "pilot"]
    stats = aggregate(confirmatory, 100)
    pilot_stats = aggregate(pilots, 10)
    write_csv("condition_results.csv", stats)
    write_csv("pilot_results.csv", pilot_stats)
    write_csv("paired_defense_contrasts.csv", paired_contrasts(confirmatory))
    write_csv("run_provenance.csv", provenance)
    figures(
        stats,
        [r for r in elections if r["stage"] != "pilot"],
        [r for r in times if r["stage"] != "pilot"],
    )
    audit = dict(
        configurations=len(provenance),
        presentation_configurations=sum(p["stage"] != "pilot" for p in provenance),
        pilot_configurations=sum(p["stage"] == "pilot" for p in provenance),
        presentation_trial_cells=len(confirmatory) // 18,
        presentation_summaries=len(confirmatory),
        pilot_summaries=len(pilots),
        condition_model_variant_estimates=len(stats),
        **verified,
        analysis_environment={
            "python": platform.python_version(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
        },
    )
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
