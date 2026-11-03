# Executed Phase 1 demonstration

Executed locally on Windows on October 27, 2026. These are synthetic simulation outputs, not empirical club findings.

Command: `uv run fan-governance experiment --config configs/experiments/voting_comparison.yaml`.

Master seed 42; 100 independent trials, 10,000 supporters per trial, four strategies, 400 elections. Membership waiting period 180 days; count quorum 20%; inclusive weighted approval threshold 50%.

Measured simulation time: **24.441 seconds**. Total through CSV/JSON/summary export and before manifest writing: **24.596 seconds**. Plot/report generation is additional. Timing is one local run, not a hardware-independent benchmark.

Environment: `{"fan_governance": "0.1.0", "numpy": "2.5.4", "pandas": "3.1.0", "pydantic": "2.14.1", "python": "3.14.7", "rng": "PCG64", "stream_scheme": "sha256-v1"}`. Dependency resolution is recorded in `uv.lock`.

| Model | Average turnout | Effective voters | Gini | Top 1% power | Passed / 100 | Outcomes differing from equal |
|---|---:|---:|---:|---:|---:|---:|
| equal | 60.01% | 9,015.08 | 0.0000 | 1.01% | 51 | 0 |
| proportional | 60.01% | 1,063.82 | 0.7105 | 20.33% | 53 | 42 |
| capped | 60.01% | 6,298.59 | 0.3674 | 1.76% | 54 | 21 |
| diminishing | 60.01% | 6,718.66 | 0.3281 | 2.84% | 53 | 18 |

Average eligible electorate: 9,015.08. Each trial uses one shared population and ballot realization across all four strategies; every trial had identical valid ballot counts and realization digests across models.

Equal voting spreads potential power evenly across eligible members. Proportional contribution weighting concentrates power under this configured contribution distribution. Capping and logarithmic weighting reduce that concentration. Wealth is independently generated and does not directly enter these voting formulas.

The default 50/50 synthetic preferences deliberately place proposals near the decision boundary. Outcome differences demonstrate sensitivity to weighting; they do not identify better decisions, measure hostile capture, or establish a causal effect on participation. Equal turnout is built into the paired behavioral design.

Artifacts: `results/voting_comparison/results.csv`, `results.json`, `summary.csv`, `manifest.json`, `outcome_disagreements.csv`, and `comparison.png`. Raw artifacts are local generated files ignored by Git. This report is retained under docs.

Regenerate the report and figure with `uv run --extra plots python examples/summarize_demo.py` after running the demonstration.
