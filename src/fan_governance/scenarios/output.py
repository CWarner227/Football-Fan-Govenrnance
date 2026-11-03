"""Portable synthetic scenario results and trial-level uncertainty summaries.

Intervals use independent trials within each scenario/grid/model/variant. Wilson
intervals describe binary synthetic outcomes; continuous quantiles describe the
trial distribution, not confidence intervals on a real-world population mean.
Plotting and Parquet dependencies are imported only when explicitly requested.
"""

import json
import math
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

GROUP_COLUMNS = ("scenario", "grid_id", "voting_model", "variant")
BINARY_METRICS = {
    "capture_success",
    "captured",
    "attack_success",
    "insolvent",
    "passed",
    "quorum_achieved",
    "outcome_changed",
    "proposal_influenced",
}


def _clean(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, Mapping):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _rows(values):
    if isinstance(values, pd.DataFrame):
        values = values.to_dict(orient="records")
    return [_clean(dict(row)) for row in values]


def aggregate_trials(summary_rows) -> list[dict]:
    """Return one metric row per independent trial group, preserving nulls."""
    rows = _rows(summary_rows)
    columns = [name for name in GROUP_COLUMNS if any(name in row for row in rows)]
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(name) for name in columns)].append(row)
    results = []
    for key, group in groups.items():
        trial_ids = [row.get("trial") for row in group if "trial" in row]
        if len(trial_ids) != len(set(trial_ids)):
            raise ValueError("Summary must contain one row per trial/grid/model/variant")
        for metric in sorted(
            set().union(*(row.keys() for row in group)) - set(columns) - {"trial", "seed"}
        ):
            values = [row.get(metric) for row in group]
            values = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
            if not values:
                continue
            array = np.asarray(values, dtype=float)
            binary = metric in BINARY_METRICS or all(isinstance(v, bool) for v in values)
            result = dict(zip(columns, key, strict=True)) | {
                "metric": metric,
                "n": len(array),
                "missing": len(group) - len(array),
                "mean": float(np.mean(array)),
                "uncertainty_kind": "trial_quantiles",
                "q025": float(np.quantile(array, 0.025)),
                "q50": float(np.quantile(array, 0.5)),
                "q975": float(np.quantile(array, 0.975)),
                "wilson_lower": None,
                "wilson_upper": None,
            }
            if binary:
                if not np.isin(array, [0, 1]).all():
                    raise ValueError(f"Binary metric {metric} must contain booleans or zero/one")
                z = 1.959963984540054
                n, rate = len(array), float(np.mean(array))
                denominator = 1 + z * z / n
                center = (rate + z * z / (2 * n)) / denominator
                width = z * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n)) / denominator
                result.update(
                    uncertainty_kind="wilson_95",
                    wilson_lower=max(0.0, center - width),
                    wilson_upper=min(1.0, center + width),
                )
            results.append(result)
    return results


def paired_defense_effectiveness(summary_rows) -> list[dict]:
    """Risk differences use matched trial IDs; zero baseline risk is undefined."""
    groups = defaultdict(lambda: defaultdict(dict))
    columns = ("scenario", "grid_id", "voting_model")
    for row in _rows(summary_rows):
        if row.get("variant") not in {"unprotected", "defended"} or "capture_success" not in row:
            continue
        key = tuple(row.get(name) for name in columns)
        groups[key][row["variant"]][row["trial"]] = bool(row["capture_success"])
    results = []
    for key, variants in groups.items():
        shared = sorted(set(variants["unprotected"]) & set(variants["defended"]))
        if not shared:
            continue
        baseline = np.array([variants["unprotected"][trial] for trial in shared], dtype=float)
        defended = np.array([variants["defended"][trial] for trial in shared], dtype=float)
        base_rate, defended_rate = float(baseline.mean()), float(defended.mean())
        results.append(
            dict(zip(columns, key, strict=True))
            | {
                "paired_trials": len(shared),
                "unprotected_capture_rate": base_rate,
                "defended_capture_rate": defended_rate,
                "absolute_capture_reduction": base_rate - defended_rate,
                "relative_capture_reduction": (base_rate - defended_rate) / base_rate
                if base_rate
                else None,
                "capture_prevented_rate": float(np.mean((baseline == 1) & (defended == 0))),
                "capture_introduced_rate": float(np.mean((baseline == 0) & (defended == 1))),
            }
        )
    return results


def _write_table(destination: Path, name: str, rows: list[dict], parquet: bool):
    (destination / f"{name}.json").write_text(
        json.dumps(rows, indent=2, allow_nan=False), encoding="utf-8"
    )
    flat = pd.json_normalize(rows)
    for column in flat.columns:
        if flat[column].map(lambda v: isinstance(v, (list, dict))).any():
            flat[column] = flat[column].map(
                lambda v: (
                    json.dumps(v, sort_keys=True, allow_nan=False)
                    if isinstance(v, (list, dict))
                    else v
                )
            )
    if flat.empty and not len(flat.columns):
        # Empty event tables still have a parseable CSV header.
        flat = pd.DataFrame(columns=["scenario", "grid_id", "trial", "voting_model", "variant"])
    flat.to_csv(destination / f"{name}.csv", index=False)
    if parquet:
        try:
            flat.to_parquet(destination / f"{name}.parquet", index=False, engine="pyarrow")
        except ImportError as error:
            raise ValueError("Parquet export requires the optional parquet extra") from error


def export_scenario(config, summary_rows, election_rows, time_rows, event_rows, metadata) -> Path:
    """Write lossless JSON, flat CSV, optional Parquet, config and provenance."""
    destination = Path(config.output.directory)
    destination.mkdir(parents=True, exist_ok=True)
    summary = _rows(summary_rows)
    tables = {
        "summary": summary,
        "elections": _rows(election_rows),
        "timeseries": _rows(time_rows),
        "events": _rows(event_rows),
        "aggregate": aggregate_trials(summary),
        "defense_effectiveness": paired_defense_effectiveness(summary),
    }
    parquet = "parquet" in config.output.formats
    for name, rows in tables.items():
        _write_table(destination, name, rows, parquet)
    configuration = config.model_dump(mode="json")
    (destination / "configuration.json").write_text(
        json.dumps(configuration, indent=2, allow_nan=False), encoding="utf-8"
    )
    (destination / "configuration.yaml").write_text(
        yaml.safe_dump(configuration, sort_keys=False), encoding="utf-8"
    )
    manifest = {
        "label": "Synthetic simulation results",
        "configuration": configuration,
        "metadata": _clean(metadata),
        "row_counts": {name: len(rows) for name, rows in tables.items()},
        "uncertainty": "Wilson 95% intervals for binary trial outcomes; 2.5/50/97.5% trial quantiles for continuous metrics; groups preserve scenario/grid/model/variant. These are synthetic model outputs, not empirical real-world probabilities.",
    }
    (destination / "metadata.json").write_text(
        json.dumps(_clean(metadata), indent=2, allow_nan=False), encoding="utf-8"
    )
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8"
    )
    return destination


def plot_scenario(summary_rows, election_rows, time_rows, directory) -> dict[str, Path]:
    """Generate eight required synthetic research figures without pooling models.

    Missing axes are explicitly annotated. Raw trial scatters preserve uncertainty;
    time lines show the within-model/variant mean, never a pooled governance model.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise ValueError("Scenario plotting requires the optional plots extra") from error
    frames = {
        "summary": pd.json_normalize(_rows(summary_rows)),
        "elections": pd.json_normalize(_rows(election_rows)),
        "timeseries": pd.json_normalize(_rows(time_rows)),
    }
    specs = {
        "capture_vs_hostile_share": (
            "summary",
            (
                "hostile_population_share",
                "hostile_share",
                "grid.hostile_share",
                "grid.hostile_population_share",
            ),
            ("capture_success",),
            "Hostile population share",
            "Capture outcome",
        ),
        "capture_vs_turnout": (
            "summary",
            ("honest_turnout", "turnout", "grid.honest_turnout"),
            ("capture_success",),
            "Honest turnout",
            "Capture outcome",
        ),
        "voting_concentration_vs_investor_contribution": (
            "summary",
            ("capital_raised", "investor_capital", "total_capital_raised"),
            ("attacker_power_share", "voting_concentration", "gini"),
            "Investor capital",
            "Voting power concentration",
        ),
        "defense_effectiveness": (
            "summary",
            ("variant",),
            ("capture_success",),
            "Policy variant",
            "Capture outcome",
        ),
        "false_positive_vs_detection": (
            "summary",
            ("false_positive_rate", "legitimate_rejection_rate", "legitimate_restriction_rate"),
            ("detection_rate", "fraudulent_identity_detection_rate", "fraud_detection_rate"),
            "False positive rate",
            "Detection rate",
        ),
        "financial_runway": (
            "timeseries",
            ("month", "day"),
            ("financial_runway_months",),
            "Month",
            "Financial runway (months)",
        ),
        "membership_revenue_vs_affordability": (
            "timeseries",
            ("membership_affordability",),
            ("membership_revenue",),
            "Membership affordability",
            "Membership revenue",
        ),
        "governance_resilience_vs_funding": (
            "summary",
            ("capital_raised", "total_capital_raised", "contribution_inflow", "total_funding"),
            ("capture_success", "attacker_power_share"),
            "Funding",
            "Capture outcome or hostile power share",
        ),
    }
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, (table, x_options, y_options, xlabel, ylabel) in specs.items():
        frame = frames[table]
        x = next((col for col in x_options if col in frame and frame[col].notna().any()), None)
        y = next((col for col in y_options if col in frame and frame[col].notna().any()), None)
        figure, axis = plt.subplots(figsize=(8, 5), constrained_layout=True)
        try:
            usable = frame.dropna(subset=[x, y]) if x and y else pd.DataFrame()
            if usable.empty:
                axis.text(
                    0.5,
                    0.5,
                    "No finite observations for these axes in this scenario",
                    ha="center",
                    va="center",
                    transform=axis.transAxes,
                )
            else:
                grouping = [col for col in ("voting_model", "variant") if col in usable]
                if y == "capture_success" and "grid_id" in usable:
                    grouping.insert(0, "grid_id")
                groups = (
                    usable.groupby(grouping, dropna=False, sort=False)
                    if grouping
                    else [("all trials", usable)]
                )
                for key, group in groups:
                    label = " / ".join(map(str, key)) if isinstance(key, tuple) else str(key)
                    if name == "financial_runway":
                        series = group.groupby(x, dropna=False)[y].mean()
                        axis.plot(series.index, series.values, label=label)
                    elif y == "capture_success":
                        for value, observations in group.groupby(x, dropna=False, sort=False):
                            n = len(observations)
                            rate = float(observations[y].mean())
                            z = 1.959963984540054
                            denominator = 1 + z * z / n
                            center = (rate + z * z / (2 * n)) / denominator
                            width = (
                                z
                                * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n))
                                / denominator
                            )
                            lower, upper = max(0, center - width), min(1, center + width)
                            axis.errorbar(
                                [value],
                                [rate],
                                yerr=[[max(0.0, rate - lower)], [max(0.0, upper - rate)]],
                                marker="o",
                                capsize=3,
                                label=label,
                            )
                            label = "_nolegend_"
                    else:
                        axis.scatter(group[x], group[y], alpha=0.65, s=25, label=label)
                handles, labels = axis.get_legend_handles_labels()
                unique = dict(zip(labels, handles, strict=True))
                if len(unique) > 12:
                    axis.text(
                        0.01,
                        0.01,
                        f"{len(unique)} series; first 12 shown in legend",
                        transform=axis.transAxes,
                        fontsize=7,
                    )
                axis.legend(list(unique.values())[:12], list(unique)[:12], fontsize=6, loc="best")
            axis.set_xlabel(xlabel)
            axis.set_ylabel(ylabel)
            if y == "capture_success":
                axis.set_ylabel("Synthetic capture rate (Wilson 95% interval)")
                axis.set_ylim(-0.05, 1.05)
            axis.set_title("Synthetic simulation results — " + name.replace("_", " "))
            axis.grid(alpha=0.2)
            path = destination / f"{name}.png"
            figure.savefig(path, dpi=150)
            paths[name] = path
        finally:
            plt.close(figure)
    return paths
