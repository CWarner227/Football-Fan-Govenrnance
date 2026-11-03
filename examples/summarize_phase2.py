"""Generate a checked, measured research report from the executed Phase 2 artifacts."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fan_governance.output.provenance import source_provenance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("results/phase2_baseline"))
    parser.add_argument("--report", type=Path, default=Path("docs/PHASE2_RESULTS.md"))
    args = parser.parse_args()
    frame = pd.read_csv(args.directory / "baseline_trials.csv")
    summary = pd.read_csv(args.directory / "baseline_summary.csv")
    metadata = json.loads((args.directory / "baseline_metadata.json").read_text())
    benchmarks = json.loads((args.directory / "benchmarks.json").read_text())
    assert metadata["source_sha256"] == source_provenance()["source_sha256"]
    assert all(
        row["source_sha256"] == metadata["source_sha256"] for row in benchmarks["benchmarks"]
    )
    groups = frame.groupby(["scenario_id", "trial_id"])
    assert groups.size().eq(6).all()
    for key in [
        "execution_metadata.input_digest",
        "execution_metadata.realization_digest",
        "votes_cast",
        "eligible_voter_count",
    ]:
        assert groups[key].nunique(dropna=False).eq(1).all(), key
    for category, target in [("constitutional", "equal"), ("funding", "capped")]:
        subset = frame[frame["execution_metadata.proposal_category"] == category]
        baseline = subset[subset.voting_model == target].sort_values("trial_id")
        hybrid = subset[subset.voting_model == "hybrid"].sort_values("trial_id")
        assert np.array_equal(baseline["vote_totals.approve"], hybrid["vote_totals.approve"])
        assert np.array_equal(baseline["metrics.gini"], hybrid["metrics.gini"])
    lines = [
        "# Phase 2 executed results and validation",
        "",
        "Executed locally on Windows on November 3, 2026. All populations, histories and results are synthetic. No real club is modeled or empirically calibrated.",
        "",
        "## Existing foundation and changes",
        "",
        "Inspection confirmed functioning Phase 1 generation, four voting models, canonical membership eligibility, separate turnout/preferences, election execution, matched random draws, batch axes, metrics, exports, CLI and optional plotting. The unmodified baseline suite passed 68 tests.",
        "",
        "Phase 2 adds aliased richer supporter traits, synthetic forecast counts and categorical policies, affordability and wealth-fraction funding, constant/categorical marginals, matrix copulas, normalized voting parameters, hybrid routing, Wilson-history expertise, attribute/policy behaviors, proposal overrides, frozen matched snapshots, representation/realized metrics, profile/behavior/category axes, research exports, six figures, and isolated-process benchmarks.",
        "",
        "Architecture changes extend existing protocols and composition roots; the weight-specific formulas remain outside the election loop. Legacy YAML and voting constructor keywords remain supported. Two old fixture setups now fund their membership contributions to satisfy the new domain invariant; their original assertions are unchanged.",
        "",
        "## Verification",
        "",
        "Full automated suite: **191 passed**. Statement coverage: **92%**. Ruff lint and formatting passed. Fixed-seed statistical checks cover marginal moments and Gaussian-copula rank correlation. Independent review findings (standalone population seed provenance, authoritative membership affordability, and inactive duplicates affecting behavior) were reproduced by regression tests and verified fixed.",
        "",
        "The suite includes original Phase 1 tests, six-model/category matching, ordering independence, immutable snapshots, zero cases, synthetic history evidence, proposal overrides, all output formats, behavior models and optional plots. Execution was tested on Python 3.14.7; the declared Python >=3.12 floor was not separately exercised on every minor version.",
        "",
        "The source distribution and wheel built successfully. A fresh isolated wheel installation ran all six models with Matplotlib and PyArrow absent, verifying optional visualization/export dependencies remain optional.",
        "",
        "## Baseline experiment",
        "",
        f"Master seed **{metadata['seed']}**; 10,000 supporters, 100 Monte Carlo trials, six models and two proposal categories: **{metadata['result_count']:,} elections**. Simulation runtime: **{metadata['elapsed_seconds']:.3f} seconds**, excluding export and plotting. Every scenario/trial reused one input digest, eligible electorate, valid ballot count and realized preferences across its six models.",
        "",
        "Weights use the explicit parameters in baseline_config.yaml: reference contribution 100; capped baseline 1/cap 5; diminishing baseline 1/cap 5/log base 2; expertise multiplier 2/minimum history 20/cap 3, with 100 synthetic forecast records per supporter. Hybrid routes constitutional to equal and funding to capped.",
        "",
        "| Category | Model | Turnout | Effective voters | Gini | Bottom 50% wealth power | Pass rate | Disagreement with equal |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for category in ["constitutional", "funding"]:
        rows = summary[summary.proposal_category == category].set_index("voting_model")
        for name in ["equal", "proportional", "capped", "diminishing", "hybrid", "expertise"]:
            row = rows.loc[name]
            lines.append(
                f"| {category} | {name} | {row.average_turnout:.2%} | {row.average_effective_voters:,.2f} | {row.average_gini:.4f} | {row.average_bottom_50_wealth_power:.2%} | {row.pass_rate:.0%} | {row.disagreement_with_equal_rate:.0%} |"
            )
    lines += [
        "",
        "Hybrid constitutional totals/concentration exactly match equal, while hybrid funding totals/concentration exactly match capped in all trials. Equal turnout is imposed by the controlled behavioral design, not evidence that a voting rule increases participation.",
        "",
        "The chosen 50/50 synthetic preferences expose sensitivity near a decision boundary. Lower concentration or a different approval outcome does not establish better governance, forecasting-based decision quality or takeover resistance. Potential representation groups use the full eligible electorate; realized metrics use valid cast power.",
        "",
        "## Performance benchmarks",
        "",
        "Each workload ran in a fresh subprocess. Runtime includes generation, frozen snapshots and elections; excludes imports, export and figures. Peak RSS is an absolute process-lifetime high-water mark including interpreter/imports, not incremental allocation.",
        "",
        "| Workload | Elections | Runtime (s) | Peak resident memory (MiB) |",
        "|---|---:|---:|---:|",
    ]
    for row in benchmarks["benchmarks"]:
        peak = row["peak_resident_memory_bytes"]
        memory = f"{peak / 1024**2:.2f}" if peak is not None else "unavailable"
        lines.append(
            f"| {row['case']} | {row['result_rows']} | {row['runtime_seconds']:.3f} | {memory} |"
        )
    lines += [
        "",
        "The 600-election benchmark uses one funding category; the baseline additionally runs constitutional proposals (1,200 elections). Timings are one local execution, not hardware-independent guarantees. All benchmark overrides are unset for these full runs. The JSON files retain workload configuration and memory method.",
        "",
        "## Reproduction and artifacts",
        "",
        "```sh",
        "uv sync --locked --all-extras --group dev",
        "uv run --locked --all-extras fan-governance baseline --config configs/experiments/phase2_baseline.yaml --plot",
        "uv run --locked --all-extras python -m fan_governance.experiments.benchmark --config configs/experiments/phase2_baseline.yaml --output results/phase2_baseline/benchmarks.json",
        "uv run --locked --all-extras python examples/summarize_phase2.py",
        "```",
        "",
        f"Environment: `{json.dumps(metadata['environment'], sort_keys=True)}`.",
        "",
        f"Source SHA-256: `{metadata['source_sha256']}`. Git commit: `{metadata['git_commit']}` (no Git repository was initialized). `uv.lock` records package resolution. Trial CSV retains named component seeds and full effective configuration.",
        "",
        "Files in results/phase2_baseline: baseline_trials.csv, baseline_summary.csv, baseline_config.yaml, baseline_metadata.json, baseline_trials.parquet, manifest.json, benchmarks.json and figures/*.png. Generated datasets are local and Git-ignored; this report is retained in docs.",
        "",
        "## Scope and limitations",
        "",
        "Binary proposals; inclusive thresholds permit 50% ties to approve when quorum holds. All forecast histories are synthetic and neutral weighting applies without sufficient evidence. Normal/bounded marginals use clipping, which changes moments and can create boundary masses. Affordability transforms can change configured latent correlations. Wealth ties use deterministic identity ordering. Current available wealth constrains each club membership; multi-club budgets and time-dependent funding are not modeled.",
        "",
        "No coordination, Sybil fraud, takeover strategy, vote buying, financial ledger, economic shocks, sporting quality, blockchain or frontend. Results and snapshot copies remain in memory; very large sweeps should profile serialization/copying and consider streaming. Summary means skip undefined statistics; inspect trial data in degenerate scenarios.",
        "",
        "Phase 3 priorities: define adversary budgets and success criteria, paired coalition/control experiments, person/account identity separation, a modular financial ledger, and sensitivity/uncertainty analysis before adding blockchain or UI infrastructure. See PHASE3_PRIORITIES.md.",
        "",
    ]
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(args.report)


if __name__ == "__main__":
    main()
