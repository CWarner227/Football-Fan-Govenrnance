# Phase 3 implementation and measured results

Executed locally on Windows with Python 3.14.7, package 0.3.0, seed 42 for the seven baselines. All results are synthetic assumptions, without empirical calibration.

## Existing functionality and changes

The starting Phase 2 engine provided validated supporter populations, six voting models, eligibility, frozen paired ballots, concentration/representation metrics, research exports, and 191 passing tests. Phase 3 preserves those commands and interfaces.

New packages are `adversarial` (seven bounded strategies and objectives), `defenses` (verification, waiting, caps, quorum, incentives, safeguarded review), `lifecycle` (calendar, scheduler, aging/recovery), `economics` (supporters, club ledger, investors, sporting outcomes, four shocks), and `scenarios` (state, central transitions, registry, paired runner, exports/figures). Existing election/config/metric modules gain weighted quorum; CLI gains scenario and scenario-suite; package/lock version is 0.3.0. Eleven scenario YAMLs and seven experiment grids are included.

True people, identity claims, memberships, and credentials are separate. Weak verification projects mistaken identities into the unchanged canonical election engine. Strategies propose actions; the transition executor validates them before debiting finite resources. Economic ownership and voting rights are explicit and separate.

## Verification

347 automated tests passed; Ruff lint and format checks passed. The wheel builds and its unpacked package runs a combined scenario independently of the editable source. All 11 library scenarios execute in end-to-end tests. CSV, JSON, and six Parquet tables passed an export smoke check. Financial continuity and cash/profit/financing identities were independently checked across every exported baseline economic row.

The Windows sandbox rejected executable-resource rewriting during a target-directory uv installation. Package files were available for the wheel import smoke test; standard wheel creation succeeded. No system installation was needed for the project environment.

## Seven baseline experiments

Each cell uses three trials and six voting models with control, unprotected, and defended variants. The fractions below average the explicitly configured cases; shared trials and heterogeneous grid settings are not independent pooled observations. Per-cell/model Wilson intervals and continuous trial quantiles are in each aggregate table.

| Experiment | Cells | Elections | Unprotected case fraction captured | Defended case fraction captured | Simulation seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| A — wealthy_investor_capture | 3 | 324 | 0.111 | 0.000 | 19.48 |
| B — coordinated_rival_infiltration | 8 | 1296 | 0.125 | 0.125 | 93.34 |
| C — sybil_resistance | 6 | 648 | 0.000 | 0.000 | 67.13 |
| D — low_turnout_capture | 8 | 864 | 0.111 | 0.097 | 83.67 |
| E — defensive_policy_comparison | 10 | 1080 | 0.000 | 0.000 | 92.74 |
| F — economic_resilience | 16 | 1728 | 0.000 | 0.000 | 91.68 |
| G — combined_crisis | 4 | 432 | 0.000 | 0.000 | 40.31 |

Total: 6,372 elections, 2,970 trial summaries, 56 scenario figures and eight suite figures. Exports: `results/phase3_experiments/`; machine-readable audit: `suite_report.json`.

## Research observations

These observations describe the configured grids rather than ranking governance systems universally. Capture is the configured majority of cast voting weight; a quorum can prevent a proposal passing while that cast-weight majority still exists.

Experiment A, averaged across its three attacker contribution levels:

| Voting model | Unprotected case fraction captured | Defended case fraction captured | Unprotected mean hostile potential share | Defended mean hostile potential share |
| --- | ---: | ---: | ---: | ---: |
| capped | 0.000 | 0.000 | 0.0082 | 0.0082 |
| diminishing | 0.000 | 0.000 | 0.0096 | 0.0096 |
| equal | 0.000 | 0.000 | 0.0052 | 0.0052 |
| expertise | 0.000 | 0.000 | 0.0043 | 0.0043 |
| hybrid | 0.000 | 0.000 | 0.0082 | 0.0082 |
| proportional | 0.667 | 0.000 | 0.4290 | 0.0108 |

In experiment C, full verification accepted 0 fraudulent claims across its defended cases. Genuine hostile people remain distinct from fraudulent aliases; identity verification does not remove genuine hostile voting rights.

In experiment B, a 180-day wait is already satisfied for day-zero joins by the first six-month election. Its limited effect in this grid illustrates why joining and election dates matter; it does not establish that waiting periods are ineffective generally.

Outside capital in experiment F has no voting rights. The integration tests separately verify that an explicit investor offer uses actual weights and caps, and that a cap can make an investor reject funding when its requested voting share is unmet.

## Benchmarks

Fresh worker processes measure run_scenario only, excluding imports, export, and plotting. Peak working set includes interpreter/imports and retained events. Other verification work overlapped these runs, so timings are local measurements rather than hardware-independent guarantees.

| Workload | Exported elections | Seconds | Peak working set MiB | Event rows |
| --- | ---: | ---: | ---: | ---: |
| 10000_supporters_36_months | 9 | 60.514 | 352.94 | 140,451 |
| 100_trials_100_supporters | 300 | 19.093 | 128.45 | 79,588 |

A demonstrated event-retention bottleneck led to optional individual ordinary receipts. Reconciled totals and random draws are identical with detailed logging enabled or disabled. The pre-compaction benchmark is preserved in `results/phase3_benchmarks/benchmarks_before_event_compaction.json`. Set `economics.record_individual_transactions: true` when individual ordinary receipts are required.

## Limits and Phase 4 priorities

Three trials per baseline cell are exploratory: even zero successes out of three leaves a wide Wilson interval. Financial relationships, risk signals, verification accuracy, turnout, and attacker behavior are synthetic. No board-seat elections, legal control transfer, real authentication, transactions, or empirically calibrated football forecasts are implemented.

Execution is sequential within each experiment and retains rows/events in memory. 100,000 supporters are a design target rather than a verified Phase 3 workload. Detailed individual transaction logs can greatly increase memory and export time. Simultaneous investor offers conservatively assume all due eligible grants enter their denominator. Revenue recovery is not recovery of cumulative lost cash.

Phase 4 should prioritize streaming event exports/checkpointing, empirical calibration and sensitivity studies, richer repeated strategic responses, explicit policy-choice effects on budgets, multi-seat elections, and a measured 100,000-supporter benchmark.

## Reproduction

```sh
uv run --locked --all-extras fan-governance scenario-suite --config configs/phase3_experiments/suite.yaml --plot
uv run --locked python examples/benchmark_phase3.py
uv run --locked python examples/report_phase3.py
uv run --locked pytest
```

Source provenance and configurations are stored per experiment. The report reads actual outputs and checks financial reconciliation; it does not synthesize missing experiment observations.
