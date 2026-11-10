# Fan Governance Simulator

A standalone Python research framework for comparing synthetic supporter governance
rules. Phase 3 adds seven synthetic attack strategies, composable defenses,
calendar-based membership lifecycles, supporter and club finances, investor rights,
and economic shocks. It preserves the six voting models, matched election inputs,
and Phase 1/2 commands. Results
are synthetic assumptions, not evidence that a rule is effective in real clubs.

Phase 3.5 adds a local **Research Dashboard** with a schema-driven simulation
builder, scenario and population-profile libraries, background execution,
interactive results, matched comparisons, persistent history and exports.

## Research dashboard

With Docker Desktop running, double-click **Start-Dashboard.cmd** to build and
start the frontend and backend together, then open the dashboard automatically.
Double-click **Stop-Dashboard.cmd** to stop it. No local Python or Node install
is needed. The first build downloads dependencies and takes longer.

Or run from the repository root:

```sh
docker compose up --build -d --wait
```

Open [the Docker dashboard](http://localhost:8000). Run history and saved
configurations persist in the `football-governance_dashboard-data` Docker volume
across rebuilds and stops. Existing host `data/dashboard/` is separate. Use
`docker compose logs -f` for logs and `docker compose stop` to stop. Port 8000 must
be free. This publishes only to your computer's loopback interface.

From this source checkout, start the API:

```sh
uv sync --all-extras --group dev
uv run uvicorn fan_governance.api.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open [the local dashboard](http://localhost:5173) or
[API documentation](http://127.0.0.1:8000/docs). The dashboard is a trusted,
unauthenticated local research tool; keep a single API process bound to loopback.
Configuration and history persist under ignored `data/dashboard/`.

Presentation studies: double-click **Import-Study-Configurations.cmd** to add
the seven studies and combined-crisis extension to Saved configurations. Open
**Experiments**, search `Study 01` through `Study 07`, then load a pilot or named
25-trial batch. See [the study run guide](docs/PRESENTATION_STUDIES.md) for the
95 presets, run order, seed rules and how to reach 100 trials per condition.

For one-server use, run `npm run build` in `frontend/` before starting the API;
the API then serves the built dashboard at [localhost:8000](http://localhost:8000).
See [dashboard usage](docs/DASHBOARD_USAGE.md),
[architecture](docs/DASHBOARD_ARCHITECTURE.md),
[integration guide](docs/INTEGRATION_GUIDE.md), and
[verification evidence](docs/PHASE35_VALIDATION.md).

Dashboard checks:

```sh
uv run --all-extras pytest
cd frontend
npm test
npm run lint
npm run build
npm run test:e2e
```

The Playwright tests require both local servers and its Chromium browser
(`npx playwright install chromium`). They execute actual small simulations.

## Installation and execution

Python 3.12 or newer is required. Using uv:

```sh
uv sync --group dev
uv run fan-governance models
uv run fan-governance simulate --config configs/default.yaml
uv run fan-governance experiment --config configs/experiments/voting_comparison.yaml
uv run --all-extras fan-governance baseline --config configs/experiments/phase2_baseline.yaml --plot
uv run --all-extras fan-governance scenario --config configs/scenarios/combined_crisis.yaml --plot
uv run --all-extras fan-governance scenario-suite --config configs/phase3_experiments/suite.yaml --plot
uv run python examples/benchmark_phase3.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Alternatively, `python -m pip install -e .` installs the core package. Install
`.[plots,parquet]` for optional Matplotlib and PyArrow support. Output paths are
relative to the working directory; `--output PATH` overrides the configured directory.
`simulate` requires one strategy, one trial and no experiment axes. `experiment`
runs the configured comparison grid. `baseline` additionally writes the research
artifact bundle. See `examples/basic_simulation.py` for library use.

`scenario` runs paired control, unprotected, and defended multi-period trials.
`scenario-suite` runs the seven Phase 3 experiment grids. Configuration selects
attack resources, identity verification, waiting periods, caps, quorum, incentives,
membership fees, investor offers, and composable shocks. The library API is
`run_scenario(ScenarioConfig)` in `fan_governance.scenarios.runner`.

See [Scenario guide](docs/SCENARIO_GUIDE.md),
[adversarial architecture](docs/ADVERSARIAL_ARCHITECTURE.md),
[threat model](docs/THREAT_MODEL.md), [economic model](docs/ECONOMIC_MODEL.md),
and [Phase 3 measured results](docs/PHASE3_RESULTS.md).

Run isolated performance workloads separately:

```sh
uv run python -m fan_governance.experiments.benchmark --config configs/experiments/phase2_baseline.yaml --output results/phase2_baseline/benchmarks.json
```

The benchmark measures 10,000 supporters with one equal election; 10,000 supporters
with 100 trials and six models; and 100,000 supporters with one equal election.
Each uses a fresh worker and one funding category. Memory is the absolute process
resident high-water mark, including interpreter/imports, not incremental allocation.

## Configuration and compatibility

Old `*_distribution` configuration and public supporter names remain supported.
Compact population YAML is also accepted:

```yaml
population:
  size: 10000
  seed: 42
  wealth: {distribution: lognormal, mean: 10.0, sigma: 1.0}
  loyalty: {distribution: beta, alpha: 4.0, beta: 2.0}
  participation_rate: {distribution: beta, alpha: 3.0, beta: 4.0}
  knowledge_score: {distribution: beta, alpha: 2.0, beta: 3.0}
  contribution: {model: wealth_fraction, min_fraction: 0.001, max_fraction: 0.05}
  forecast_accuracy: {distribution: beta, alpha: 5.0, beta: 4.0}
  forecast_sample_count: {distribution: constant, value: 100}
  preferred_policy:
    distribution: categorical
    categories: [community, investment, neutral]
    probabilities: [0.4, 0.4, 0.2]
```

`fan_id`, `participation_rate` and `knowledge_score` alias the existing
`supporter_id`, `participation_probability` and `knowledge` fields without storing
extra copies. Independent contributions are clipped to wealth by default. Explicit
wealth-fraction and unfunded alternatives are documented in the assumptions guide.
The six files in `configs/profiles/` describe small (2,000), medium (10,000), large
(100,000), wealth-unequal, high-participation and low-participation synthetic populations.
These are research scenarios, not estimates of real supporter populations.

Voting names are `equal`, `proportional`, `capped`, `diminishing`, `hybrid` and
`expertise`. Existing capped and diminishing defaults retain their Phase 1 formulas.
Use explicit parameters for the Phase 2 formulas, for example:

```yaml
voting:
  strategies:
    - equal
    - name: proportional
      parameters: {reference_contribution: 100}
    - name: capped
      parameters: {base_weight: 1, reference_contribution: 100, max_weight: 5}
    - name: diminishing
      parameters: {base_weight: 1, reference_contribution: 100, max_weight: 5}
    - name: hybrid
      parameters:
        default_strategy: equal
        proposal_rules:
          constitutional: equal
          funding:
            name: capped
            parameters: {base_weight: 1, reference_contribution: 100, max_weight: 5}
    - name: expertise
      parameters: {minimum_samples: 20, expertise_multiplier: 2, max_weight: 3}
```

Forecast histories are explicitly synthetic. Expertise weighting uses correct/total
counts with a conservative Wilson-bound reliability score; latent knowledge and
raw forecast accuracy do not substitute for history or measure governance quality.

## Interpreting results

Every result row represents one model, scenario and trial. JSON retains configuration,
component seeds, source/version metadata and metrics. CSV/Parquet flatten metrics and
retain nested configuration and seeds as JSON cells. Standard runs write
`results.*`, `summary.csv` and `manifest.json`. Baseline runs write
`baseline_trials.csv`, `baseline_summary.csv`, `baseline_config.yaml` and
`baseline_metadata.json`, with optional Parquet and research figures.

Within each scenario/trial, models reuse one frozen snapshot: supporters, memberships,
eligibility, proposal, turnout and preferences. Only voting weights change. Compare
paired differences; do not treat those elections as independent observations.

Turnout and quorum count eligible members casting valid option ballots, including
zero-weight ballots. Abstentions and invalid ballots are excluded. Approval requires
positive cast weight and an inclusive first-option share threshold. At threshold
0.5 an exact tie can pass if quorum holds, while the winning option is null.

Top-level concentration metrics describe all eligible potential power; separate
realized metrics describe valid participating power. Wealth representation groups
are ranked within the eligible electorate, with deterministic identity tie-breaks.
Undefined ratios and empty/all-zero concentration are JSON `null` and blank CSV cells.
Effective voters is inverse concentration, not an actual participant headcount.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Extending models](docs/EXTENDING_MODELS.md)
- [Simulation assumptions and formulas](docs/SIMULATION_ASSUMPTIONS.md)
- [Controlled experiments and reproduction](docs/EXPERIMENTS.md)
- [Phase 2 verification and measured results](docs/PHASE2_RESULTS.md)
- [Historical Phase 1 demonstration](docs/DEMONSTRATION.md)
- [Phase 2 requirements](docs/PHASE2_REQUEST.md)

The dashboard runs locally without a database server or blockchain. Real
transactions and a calibrated football model are outside this research tool.
Canonical identity is assumed; this is not an identity-fraud defense.
