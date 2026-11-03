"""Build the measured demonstration report and figure from exported trial records."""

import argparse
import json
from pathlib import Path

import pandas as pd

from fan_governance.elections.models import SimulationResult
from fan_governance.output.plotting import plot_results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("results/voting_comparison"))
    parser.add_argument("--report", type=Path, default=Path("docs/DEMONSTRATION.md"))
    args = parser.parse_args()
    frame = pd.read_csv(args.directory / "results.csv")
    summary = pd.read_csv(args.directory / "summary.csv").set_index("voting_model")
    manifest = json.loads((args.directory / "manifest.json").read_text(encoding="utf-8"))
    paired = frame.pivot(index=["scenario_id", "trial_id"], columns="voting_model", values="passed")
    disagreements = {name: int((paired[name] != paired["equal"]).sum()) for name in paired.columns}
    comparison = pd.DataFrame(
        [
            {"model": name, "disagreements_with_equal": count}
            for name, count in disagreements.items()
        ]
    )
    comparison.to_csv(args.directory / "outcome_disagreements.csv", index=False)
    results = [
        SimulationResult.model_validate(r)
        for r in json.loads((args.directory / "results.json").read_text(encoding="utf-8"))
    ]
    plot_results(results, args.directory / "comparison.png")
    lines = [
        "# Executed Phase 1 demonstration",
        "",
        "Executed locally on Windows on October 27, 2026. These are synthetic simulation outputs, not empirical club findings.",
        "",
        "Command: `uv run fan-governance experiment --config configs/experiments/voting_comparison.yaml`.",
        "",
        f"Master seed {manifest['configuration']['experiment']['seed']}; 100 independent trials, 10,000 supporters per trial, four strategies, 400 elections. Membership waiting period 180 days; count quorum 20%; inclusive weighted approval threshold 50%.",
        "",
        f"Measured simulation time: **{manifest['simulation_seconds']:.3f} seconds**. Total through CSV/JSON/summary export and before manifest writing: **{manifest['total_seconds_before_manifest']:.3f} seconds**. Plot/report generation is additional. Timing is one local run, not a hardware-independent benchmark.",
        "",
        f"Environment: `{json.dumps(manifest['versions'], sort_keys=True)}`. Dependency resolution is recorded in `uv.lock`.",
        "",
        "| Model | Average turnout | Effective voters | Gini | Top 1% power | Passed / 100 | Outcomes differing from equal |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ["equal", "proportional", "capped", "diminishing"]:
        row = summary.loc[name]
        passes = int(frame.loc[frame.voting_model == name, "passed"].sum())
        lines.append(
            f"| {name} | {row.average_turnout:.2%} | {row.average_effective_voters:,.2f} | {row.average_gini:.4f} | {row.average_top_1_share:.2%} | {passes} | {disagreements[name]} |"
        )
    eligible = frame.groupby("trial_id").eligible_voter_count.first().mean()
    paired_counts = frame.groupby(["scenario_id", "trial_id"]).votes_cast.nunique()
    paired_digests = frame.groupby(["scenario_id", "trial_id"])[
        "execution_metadata.realization_digest"
    ].nunique()
    assert paired_counts.eq(1).all() and paired_digests.eq(1).all()
    lines += [
        "",
        f"Average eligible electorate: {eligible:,.2f}. Each trial uses one shared population and ballot realization across all four strategies; every trial had identical valid ballot counts and realization digests across models.",
        "",
        "Equal voting spreads potential power evenly across eligible members. Proportional contribution weighting concentrates power under this configured contribution distribution. Capping and logarithmic weighting reduce that concentration. Wealth is independently generated and does not directly enter these voting formulas.",
        "",
        "The default 50/50 synthetic preferences deliberately place proposals near the decision boundary. Outcome differences demonstrate sensitivity to weighting; they do not identify better decisions, measure hostile capture, or establish a causal effect on participation. Equal turnout is built into the paired behavioral design.",
        "",
        "Artifacts: `results/voting_comparison/results.csv`, `results.json`, `summary.csv`, `manifest.json`, `outcome_disagreements.csv`, and `comparison.png`. Raw artifacts are local generated files ignored by Git. This report is retained under docs.",
        "",
        "Regenerate the report and figure with `uv run --extra plots python examples/summarize_demo.py` after running the demonstration.",
        "",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(args.report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
