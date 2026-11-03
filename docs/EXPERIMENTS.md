# Controlled experiments and reproduction

The default command-line workflows use the same scientific engine as library callers.
Use Python >=3.12 and the repository's uv lockfile. The Phase 2 baseline is explicitly
synthetic; these configurations have not been calibrated to actual football clubs.

## Run the baseline

```sh
uv sync --locked --all-extras --group dev
uv run --locked --all-extras fan-governance baseline --config configs/experiments/phase2_baseline.yaml --plot
```

This runs 10,000 supporters, 100 independent trials, six weight models, and two
categories (constitutional and funding): 1,200 elections. The categories share the
same generated supporter/membership conditions for each trial. They are separate
scenarios because proposal category is an input to hybrid routing. All six models in
each scenario/trial share a single immutable election input snapshot.

The configured wealth-fraction contribution process imposes an explicit financial
relationship. Other baseline numeric traits are independently sampled. There is no
assumed wealth/expertise/loyalty association. Forecast histories use 100 synthetic
binary records per supporter, with a Beta(5,4) generative accuracy distribution.
All history-derived expertise is simulated; it does not measure governance quality.

The default preference model is a 50/50 synthetic binary preference, chosen to expose
sensitivity to weighting near a decision boundary. Preferred policy categories are
generated but do not affect this particular experiment's random preference model.
No strategic behavior or change in turnout in response to the voting rule is modeled.

## Baseline files

The output directory defaults to `results/phase2_baseline`. It contains:

- `baseline_trials.csv`: one row per scenario/trial/model. Metrics are flattened with
  dotted names; full configuration and component seeds remain JSON-valued cells.
- `baseline_summary.csv`: means, pass/disagreement rates, and potential wealth-group
  influence by scenario/model. It retains proposal category; scenarios are not pooled.
- `baseline_config.yaml`: complete effective experiment configuration, including defaults.
- `baseline_metadata.json`: master seed, configuration, package versions, RNG scheme,
  execution time, OS/processor, Git commit when available, and source SHA-256.
- `baseline_trials.parquet`: same trial-level table, when the optional Parquet format
  is selected and PyArrow is installed.
- `manifest.json`: CLI timing and environment record.
- `figures/`: optional six Matplotlib figures, faceted by proposal category, for
  concentration, effective voters, wealth decile influence, approval shares, turnout,
  and outcome disagreement with the equal baseline.

CSV and JSON exports from the original `simulate` and `experiment` commands continue
to use their original `results.csv` / `results.json` filenames. The `baseline` command
adds the research artifact naming convention; it does not remove the other workflows.

## Matched inputs

`ElectionRunner.prepare(club, proposal, streams)`:

1. Validates club identities and membership affordability.
2. Copies supporters and membership records into frozen objects, with read-only
   extension attributes, and selects eligible records exactly once.
3. Generates potential behavior once per canonical supporter, using the chosen
   eligible membership for eligible people. Ineligible people still consume their
   component draws so changing eligibility does not shift unrelated people's draws.
4. Stores immutable turnout/preferences, eligible member IDs, proposal JSON, and an
   input SHA-256 digest. The proposal's weight strategy is neutralized for behavior.

Each injected weight model consumes the same snapshot. Mutating the original club
after preparation cannot change the snapshot. Behavior and eligibility plugins must
be pure functions of inputs and the supplied RNG, and must not use global random state.
`run(..., snapshot=snapshot)` uses the captured proposal and trial; regenerate a snapshot
to change any condition. It is an in-memory research input, not a production security
boundary, persistent ballot ledger or real-world identity proof.

Check `execution_metadata.input_digest` and `realization_digest` within a
`(scenario_id, trial_id)` group: each must have exactly one distinct value. Valid
ballot counts and unweighted shares must also agree across models. Category changes
produce different input digests even when random preferences happen to be identical.

The equal-counterfactual metrics are computed from the same valid ballots even if
`equal` is omitted from the selected strategies. They include first-option share,
proposal pass/fail, outcome disagreement and weighted-minus-equal approval share.

## Random streams

Population marginals, policy categories, forecast histories, contribution fractions,
adversarial labels, copula, participation, and preferences have named PCG64 streams.
Each seed is deterministically derived from the master seed, trial ID and stream name
using the versioned SHA-256 scheme. Population-specific seed overrides affect only
population streams; both standalone and batch outputs record their actual seeds.

Different trials have independent named streams. Scenarios within a trial share
streams as a common-random-number design. Changing strategy order/count does not
change a population or realization. Different population sizes or plugins that consume
different numbers of draws do not guarantee matching prefixes within that component.
Retain configuration, lockfile and versions; reproducibility across arbitrary NumPy
versions or different numerical implementations is not promised.

## Sweeps and proposal overrides

The existing `population_sizes`, `waiting_periods`, `participation_levels` and
`wealth_distributions` axes remain available. New axes are:

- `population_profiles`: mapping from profile name to a complete `PopulationConfig`.
  Omitted fields use normal population defaults. It is mutually exclusive with size/
  wealth-distribution axes to avoid ambiguous profile merging.
- `participation_models`: a list of model specifications, such as probabilistic,
  constant or attribute-based models. A simultaneous `participation_levels` axis
  adds the `probability` parameter and therefore is appropriate only for models that
  accept it; invalid combinations fail before the first trial.
- `proposal_categories`: distinct category names. They override the base proposal
  category while retaining other proposal fields.

See `configs/experiments/behavior_sweep.yaml` for a small illustrative grid. There are
six runnable standalone profile files under `configs/profiles` (2k/10k/100k supporters,
wealth-unequal, high-turnout and low-turnout). Profile names are synthetic labels.

Proposal-specific quorum, threshold, waiting period and eligibility override governance
defaults. An explicit waiting-period sweep takes precedence over the proposal's scalar
waiting period. A proposal's explicit `voting_strategy` selects a single strategy and
replaces the comparison list; use `hybrid` to route a strategy by category. The supplied
six-model baseline deliberately leaves that single-strategy override unset.

## Metrics and interpretation

Potential concentration includes every eligible member, including nonparticipants
and zero-weight members. Realized concentration uses valid cast ballots only. Wealth
groups in both views are defined on the full eligible electorate, ordered by wealth
with canonical identity as a deterministic tie-break. Equal wealth ties therefore have
an arbitrary, reproducible ordering; small groups should not be overinterpreted.

Representation includes bottom-50%, top-10%, top-1% influence, wealth-decile power
shares, financial contribution shares, and contribution-share / voting-power-share
ratios. Realized financial shares use only valid voters' contributions. Undefined
denominators export as null/blank. Do not replace them with zero inequality or zero
representation. Summary means skip missing values, so inspect degenerate trials.

All thresholds remain inclusive. An exact 50/50 weighted tie can approve at a 50%
threshold if quorum holds, although winning_option is null. Choose a threshold above
0.5 to require strictly more than half. Abstentions/invalid ballots are reported
separately and excluded from turnout, quorum and approval; zero-weight valid ballots
count toward turnout and count quorum, but supply no weighted approval power.

Report paired differences within scenario/trial. Do not treat six matched elections
as six independent population observations. Means and pass rates describe this
configured Monte Carlo process; they establish neither empirical facts nor better
governance decisions, increased participation, or takeover resistance.

## Benchmarks

```sh
uv run --locked --all-extras python -m fan_governance.experiments.benchmark --config configs/experiments/phase2_baseline.yaml --output results/phase2_baseline/benchmarks.json
```

This runs three fresh worker processes: 10,000 supporters/one equal election;
10,000 supporters/100 trials/six models for one funding category (600 elections);
100,000 supporters/one equal election. Runtime includes generation/snapshots/elections
and excludes imports/config loading/export/plotting. The standalone baseline is larger
because it additionally demonstrates a second category.

Memory is the absolute process-lifetime peak resident set, including interpreter and
imports, measured with Windows PeakWorkingSetSize or Unix ru_maxrss. It is not an
increment over an idle process. JSON records actual workloads, process IDs, environment,
source provenance and measurement methods. Timings are local measurements, not a
hardware-independent performance promise. `--size` / `--trials` are explicit smoke-test
overrides and are always recorded; omit them for the requested full workloads.

The current runner keeps result rows in memory, retaining no population across finished
trials. Frozen input copies and canonical JSON hashing cost memory, especially at 100k.
Thousands of trials may benefit from a streaming result API/exporter and optimized
snapshot serialization; benchmark first rather than adding distributed infrastructure.

## Phase 3 baseline suite

```sh
uv run --locked --all-extras fan-governance scenario-suite --config configs/phase3_experiments/suite.yaml --plot
uv run --locked python examples/benchmark_phase3.py
```

The suite contains A wealthy investor capture, B coordinated infiltration, C Sybil
resistance, D low-turnout capture, E individual and combined defenses, F economic
resilience, and G combined governance and financial crisis. YAML grids select dotted
paths, including list indices. Every expanded configuration is validated before its
trials begin. Defaults use three trials per cell and all six voting models; raise
`experiment.trials` for research beyond these smoke-sized demonstrations.

Outputs include trial summaries, election records, financial time series, complete
synthetic events, attack and defense histories, aggregate uncertainty, paired defense
effects, configuration snapshots, metadata, source hashes, and eight labeled figures.
CSV and JSON are core formats; Parquet and plots use optional dependencies.
See [Phase 3 results](PHASE3_RESULTS.md) for actual runs and limitations.
