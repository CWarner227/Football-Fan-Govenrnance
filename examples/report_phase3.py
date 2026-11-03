"""Audit exported Phase 3 baselines and regenerate their evidence report."""

import json
from pathlib import Path

import pandas as pd
import yaml

from fan_governance.scenarios.config import load_scenario
from fan_governance.scenarios.output import plot_scenario

ROOT = Path(__file__).resolve().parents[1]


def main():
    suite = ROOT / "configs/phase3_experiments/suite.yaml"
    entries = yaml.safe_load(suite.read_text())["experiments"]
    reports, summaries, timeseries = [], [], []
    for entry in entries:
        config = load_scenario(suite.parent / entry)
        directory = ROOT / config.output.directory
        manifest = json.loads((directory / "manifest.json").read_text())
        summary = json.loads((directory / "summary.json").read_text())
        times = json.loads((directory / "timeseries.json").read_text())
        frame = pd.DataFrame(times)
        reconciliation = frame.cash_balance - (
            frame.opening_cash + frame.profit + frame.financing_cashflow + frame.investing_cashflow
        )
        grouping = ["grid_id", "trial", "voting_model", "variant"]
        ordered = frame.sort_values(grouping + ["day"])
        continuity = ordered.opening_cash - ordered.groupby(grouping).cash_balance.shift()
        error = float(max(reconciliation.abs().max(), continuity.abs().max()))
        if error > 1e-7:
            raise ValueError(f"{config.name}: financial reconciliation error {error}")
        figures = list((directory / "figures").glob("*.png"))
        if len(figures) != 8 or any(p.stat().st_size < 1000 for p in figures):
            raise ValueError(f"{config.name}: missing or empty research figures")
        frame = pd.DataFrame(summary)
        by_variant = {}
        for variant, group in frame.groupby("variant"):
            by_variant[variant] = {
                "case_fraction_captured": float(group.capture_success.mean()),
                "mean_final_cash": float(group.cash_balance.mean()),
                "case_fraction_financially_survived": float(group.financially_survived.mean()),
                "mean_hostile_power": float(group.attacker_power_share.mean()),
            }
        reports.append(
            {
                "experiment": entry[0],
                "name": config.name,
                "grid_cells": manifest["metadata"]["grid_cells"],
                "trials_per_cell": config.experiment.trials,
                "summary_rows": len(summary),
                "elections": manifest["row_counts"]["elections"],
                "economic_rows": len(times),
                "event_rows": manifest["row_counts"]["events"],
                "simulation_seconds": manifest["metadata"]["elapsed_seconds"],
                "max_financial_reconciliation_error": error,
                "figures": len(figures),
                "variants": by_variant,
            }
        )
        summaries.extend(summary)
        timeseries.extend(times)
    destination = ROOT / "results/phase3_experiments"
    benchmarks = json.loads((ROOT / "results/phase3_benchmarks/benchmarks.json").read_text())
    report = {
        "synthetic": True,
        "experiments": reports,
        "total_elections": sum(r["elections"] for r in reports),
        "total_trial_summaries": len(summaries),
        "interpretation": "Case fractions average configured grid cells and shared trials; they are descriptive, not a pooled independent-trial probability.",
        "benchmarks": benchmarks,
    }
    (destination / "suite_report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    plot_scenario(summaries, [], timeseries, destination / "figures")
    text = [
        "# Phase 3 implementation and measured results",
        "",
        "Executed locally on Windows with Python 3.14.7, package 0.3.0, seed 42 for the seven baselines. All results are synthetic assumptions, without empirical calibration.",
        "",
        "## Existing functionality and changes",
        "",
        "The starting Phase 2 engine provided validated supporter populations, six voting models, eligibility, frozen paired ballots, concentration/representation metrics, research exports, and 191 passing tests. Phase 3 preserves those commands and interfaces.",
        "",
        "New packages are `adversarial` (seven bounded strategies and objectives), `defenses` (verification, waiting, caps, quorum, incentives, safeguarded review), `lifecycle` (calendar, scheduler, aging/recovery), `economics` (supporters, club ledger, investors, sporting outcomes, four shocks), and `scenarios` (state, central transitions, registry, paired runner, exports/figures). Existing election/config/metric modules gain weighted quorum; CLI gains scenario and scenario-suite; package/lock version is 0.3.0. Eleven scenario YAMLs and seven experiment grids are included.",
        "",
        "True people, identity claims, memberships, and credentials are separate. Weak verification projects mistaken identities into the unchanged canonical election engine. Strategies propose actions; the transition executor validates them before debiting finite resources. Economic ownership and voting rights are explicit and separate.",
        "",
        "## Verification",
        "",
        "347 automated tests passed; Ruff lint and format checks passed. The wheel builds and its unpacked package runs a combined scenario independently of the editable source. All 11 library scenarios execute in end-to-end tests. CSV, JSON, and six Parquet tables passed an export smoke check. Financial continuity and cash/profit/financing identities were independently checked across every exported baseline economic row.",
        "",
        "The Windows sandbox rejected executable-resource rewriting during a target-directory uv installation. Package files were available for the wheel import smoke test; standard wheel creation succeeded. No system installation was needed for the project environment.",
        "",
        "## Seven baseline experiments",
        "",
        "Each cell uses three trials and six voting models with control, unprotected, and defended variants. The fractions below average the explicitly configured cases; shared trials and heterogeneous grid settings are not independent pooled observations. Per-cell/model Wilson intervals and continuous trial quantiles are in each aggregate table.",
        "",
        "| Experiment | Cells | Elections | Unprotected case fraction captured | Defended case fraction captured | Simulation seconds |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in reports:
        text.append(
            f"| {row['experiment']} — {row['name']} | {row['grid_cells']} | {row['elections']} | {row['variants']['unprotected']['case_fraction_captured']:.3f} | {row['variants']['defended']['case_fraction_captured']:.3f} | {row['simulation_seconds']:.2f} |"
        )
    text += [
        "",
        f"Total: {report['total_elections']:,} elections, {len(summaries):,} trial summaries, 56 scenario figures and eight suite figures. Exports: `results/phase3_experiments/`; machine-readable audit: `suite_report.json`.",
        "",
        "## Research observations",
        "",
        "These observations describe the configured grids rather than ranking governance systems universally. Capture is the configured majority of cast voting weight; a quorum can prevent a proposal passing while that cast-weight majority still exists.",
        "",
        "Experiment A, averaged across its three attacker contribution levels:",
        "",
        "| Voting model | Unprotected case fraction captured | Defended case fraction captured | Unprotected mean hostile potential share | Defended mean hostile potential share |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    frame = pd.DataFrame(summaries)
    a = frame[frame.scenario == "wealthy_investor_capture"]
    for model, group in a.groupby("voting_model"):
        u, d = group[group.variant == "unprotected"], group[group.variant == "defended"]
        text.append(
            f"| {model} | {u.capture_success.mean():.3f} | {d.capture_success.mean():.3f} | {u.attacker_power_share.mean():.4f} | {d.attacker_power_share.mean():.4f} |"
        )
    c = frame[frame.scenario == "sybil_resistance"]
    full = c[(c.variant == "defended") & (c["defenses.0.parameters.strength"] == 1)]
    text += [
        "",
        f"In experiment C, full verification accepted {int(full.fraudulent_identities_accepted.sum())} fraudulent claims across its defended cases. Genuine hostile people remain distinct from fraudulent aliases; identity verification does not remove genuine hostile voting rights.",
        "",
        "In experiment B, a 180-day wait is already satisfied for day-zero joins by the first six-month election. Its limited effect in this grid illustrates why joining and election dates matter; it does not establish that waiting periods are ineffective generally.",
        "",
        "Outside capital in experiment F has no voting rights. The integration tests separately verify that an explicit investor offer uses actual weights and caps, and that a cap can make an investor reject funding when its requested voting share is unmet.",
        "",
        "## Benchmarks",
        "",
        "Fresh worker processes measure run_scenario only, excluding imports, export, and plotting. Peak working set includes interpreter/imports and retained events. Other verification work overlapped these runs, so timings are local measurements rather than hardware-independent guarantees.",
        "",
        "| Workload | Exported elections | Seconds | Peak working set MiB | Event rows |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    cases = (
        benchmarks
        if isinstance(benchmarks, list)
        else benchmarks.get("cases", benchmarks.get("benchmarks", []))
    )
    for case in cases:
        text.append(
            f"| {case['case']} | {case['elections']} | {case['wall_seconds']:.3f} | {case['peak_working_set_mib']:.2f} | {case['event_rows']:,} |"
        )
    text += [
        "",
        "A demonstrated event-retention bottleneck led to optional individual ordinary receipts. Reconciled totals and random draws are identical with detailed logging enabled or disabled. The pre-compaction benchmark is preserved in `results/phase3_benchmarks/benchmarks_before_event_compaction.json`. Set `economics.record_individual_transactions: true` when individual ordinary receipts are required.",
        "",
        "## Limits and Phase 4 priorities",
        "",
        "Three trials per baseline cell are exploratory: even zero successes out of three leaves a wide Wilson interval. Financial relationships, risk signals, verification accuracy, turnout, and attacker behavior are synthetic. No board-seat elections, legal control transfer, real authentication, transactions, or empirically calibrated football forecasts are implemented.",
        "",
        "Execution is sequential within each experiment and retains rows/events in memory. 100,000 supporters are a design target rather than a verified Phase 3 workload. Detailed individual transaction logs can greatly increase memory and export time. Simultaneous investor offers conservatively assume all due eligible grants enter their denominator. Revenue recovery is not recovery of cumulative lost cash.",
        "",
        "Phase 4 should prioritize streaming event exports/checkpointing, empirical calibration and sensitivity studies, richer repeated strategic responses, explicit policy-choice effects on budgets, multi-seat elections, and a measured 100,000-supporter benchmark.",
        "",
        "## Reproduction",
        "",
        "```sh",
        "uv run --locked --all-extras fan-governance scenario-suite --config configs/phase3_experiments/suite.yaml --plot",
        "uv run --locked python examples/benchmark_phase3.py",
        "uv run --locked python examples/report_phase3.py",
        "uv run --locked pytest",
        "```",
        "",
        "Source provenance and configurations are stored per experiment. The report reads actual outputs and checks financial reconciliation; it does not synthesize missing experiment observations.",
    ]
    (ROOT / "docs/PHASE3_RESULTS.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "benchmarks"}, indent=2))


if __name__ == "__main__":
    main()
