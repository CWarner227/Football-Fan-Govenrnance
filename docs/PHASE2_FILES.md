# Phase 2 file inventory

The existing repository structure was retained. There was no Git repository/commit
to diff; this inventory records the implementation scope.

## Created source modules

- `core/behavior.py`: validated numeric traits and stable logistic probabilities.
- `participation/attribute_based.py`: attribute-based turnout.
- `preferences/policy.py`, `preferences/attribute_based.py`: policy/attribute choices.
- `voting/hybrid.py`, `voting/expertise.py`: delegation and forecast-history reliability.
- `elections/snapshot.py`: frozen supporters/memberships/realizations and matched inputs.
- `metrics/representation.py`: wealth-group potential and realized power.
- `output/baseline.py`, `output/provenance.py`, `output/research_plotting.py`:
  research artifacts, offline code provenance and six optional figures.
- `experiments/benchmark.py`: fresh-process runtime and absolute peak-RSS measurements.

Source paths above are relative to `src/fan_governance/`.

## Modified source and project configuration

- `agents/models.py`, `agents/generator.py`: aliases, constraints, distributions/history.
- `core/config.py`, `core/context.py`, `core/engine.py`, `core/registry.py`: compatible
  configuration, expanded context, correct actual stream provenance and composition.
- `clubs/models.py`, `membership/eligibility.py`: affordability and proposal filters.
- `voting/strategies.py`: normalized/capped Phase 2 parameters, legacy compatibility.
- `participation/probabilistic.py`: distinct constant common-probability implementation.
- `elections/models.py`, `elections/runner.py`: richer proposal/metric inputs and snapshots.
- `metrics/results.py`: participation, equal-counterfactual, representation/realized metrics.
- `experiments/runner.py`, `experiments/comparison.py`: scenario axes and paired summaries.
- `cli.py`, `__init__.py`: baseline workflow/progress and version 0.2.0.
- `pyproject.toml`, `uv.lock`: package version; dependency choices retained.

## Configurations, examples and tests

- `configs/experiments/phase2_baseline.yaml`, `behavior_sweep.yaml`.
- Six `configs/profiles/*.yaml` files: small/medium/large, wealth-unequal, high/low turnout.
- `examples/summarize_phase2.py`: checked artifact-to-report reproduction.
- Eleven `tests/test_phase2_*.py` files cover population, formulas, behavior, snapshots,
  metrics, experiments, plotting, benchmarks, statistics, provenance and review regressions.
- Two original fixture setups (`tests/test_elections.py`, `tests/test_membership.py`)
  now fund authoritative membership contributions; original voting assertions retained.

## Documentation and generated artifacts

Updated README, architecture, extension guide and assumptions. Added the Phase 2
request/plan, EXPERIMENTS.md, PHASE2_RESULTS.md, this inventory and PHASE3_PRIORITIES.md.
Historical Phase 1 evidence/roadmap files link to the current evidence and phase labels.

The executed trial datasets, summaries, copied configuration, metadata, Parquet,
benchmark JSON and six figures are in `results/phase2_baseline/` and remain Git-ignored.
The preliminary full-run outputs in `results/phase2_smoke/` are not the final evidence.
