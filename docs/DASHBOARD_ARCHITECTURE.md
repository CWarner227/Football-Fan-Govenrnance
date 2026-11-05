# Local research dashboard architecture

The Phase 3.5 dashboard exposes the existing synthetic governance engine through a
versioned FastAPI service and a separate React/TypeScript client. Voting weights,
participation, adversarial actions, economic transitions, scientific metrics and
uncertainty calculations remain in Python. The browser displays actual engine
outputs or explicitly saved runs.

```text
React / Vite browser client
  -> typed HTTP client /api/v1
  -> FastAPI validation, discovery, configuration and result services
  -> JobManager: persisted queue, one worker process at a time
  -> existing run_scenario / aggregate_trials / paired_defense_effectiveness
  -> confined filesystem repository and JSONL artifacts
```

## Module boundaries

| Module | Responsibility |
| --- | --- |
| `api/catalog.py` | Derive schemas/defaults from registry factory signatures, dataclasses and declared parameter models; publish scenario schema and local limits. |
| `api/validation.py` | Validate configuration, nested factories and every expanded grid cell before scheduling; estimate and bound local workload. |
| `api/schemas.py` | Typed request envelopes, independent of scientific configuration models. |
| `api/main.py` | Versioned HTTP endpoints and application lifespan. |
| `api/jobs.py` | Parent-owned queue, status transitions, process limits, cancellation and timeout handling. |
| `api/worker.py` | Invoke the existing scenario engine and atomically publish artifacts. |
| `api/results.py` | Bounded table/chart reads, exports and controlled comparisons. |
| `storage/interfaces.py` | Interchangeable repository protocol. |
| `storage/filesystem.py` | Atomic JSON metadata with opaque IDs and confined directories. |
| `integrations/interfaces.py` | Descriptive future integration boundary; blockchain is planned and disabled. |
| `frontend/src/components/SchemaForm.tsx` | Reusable schema controls; unsupported complex values retain a JSON editing path. |

The registry's public `factories()` accessor returns detached mappings for
discovery. Registering a typed voting/participation/preference factory or adding a
scenario attack/defense factory makes its metadata discoverable without copying
scientific rules into React. Hybrid routing includes nested model specifications.
Economic shock names and fields come from the existing `ShockSpec` schema.

## Configuration and execution

The authoritative input is `ScenarioConfig`, including its nested
`SimulationConfig`. Schema defaults use 100 supporters, one trial, 12 simulated
months, an election every 12 months and equal voting. Each scenario execution
includes the engine's control, unprotected and defended variants; additional
matched reference trajectories may be required for combined attacks, defenses and
economic shocks. The interface's simulation/experiment label does not replace
those scientific pairing requirements.

Validation workload metadata distinguishes independent Monte Carlo realizations
from engine trajectories: `total_trials` sums configured trials across grid
cells; `trajectory_runs` additionally counts voting models, paired variants and
extra matched references. One configured trial can therefore execute five
trajectories while still reporting one Monte Carlo trial. Neither value is an
intermediate progress measurement.

Validation constructs registered factories, validates routed hybrid parameters,
checks supported distributions through the existing sampler with a zero-sized
sample, and validates every Cartesian grid expansion. Limits published by
`/capabilities` are 100,000 initial supporters, 1,000 trials per cell, 256 grid
cells, 300,000,000 estimated work units, one concurrent worker and a 1,800-second
worker timeout. Work units are a conservative scheduling estimate, not a
scientific outcome. Operational budgets, potential membership growth and extra
matched references contribute to the estimate.

Submitting a run persists a normalized snapshot before queueing it. Only the
manager writes the run record. A worker produces separate progress and output
files. Exact intermediate trial callbacks are unavailable in the current engine;
running progress stays indeterminate until completed work can be established.
Cancellation terminates the process and waits for its exit. Timeout produces a
failed run after terminating computation. Queued records are reloaded at startup;
previously running records become failed rather than being reported as resumed.
Workers also watch a dedicated parent liveness pipe. Abrupt API process death
closes that pipe and the worker exits, so computation does not silently survive
the manager. Engine provenance subprocesses inherit a null stdin rather than
this private liveness pipe.

Run one API process against a repository. Multiple Uvicorn workers or independent
servers sharing the same storage directory are unsupported because the queue is
owned by one in-process manager.

## Persistence and results

The default root is `data/dashboard`, overridden by server environment variable
`FAN_GOVERNANCE_DATA`. Records are stored as:

```text
data/dashboard/
  configurations/<32-character lowercase hex ID>/record.json
  runs/<32-character lowercase hex ID>/
    record.json
    worker.log
    progress.json
    success.json
    artifacts/
      configuration.json
      manifest.json
      summary.jsonl
      elections.jsonl
      timeseries.jsonl
      events.jsonl
      aggregate.jsonl
      defense_effectiveness.jsonl
```

Metadata is limited to 16 MiB per record and committed by writing/flushing a
temporary file followed by atomic replacement. The repository accepts only the
`runs` and `configurations` collections and opaque IDs. It rejects path traversal,
symlinks and Windows junctions. Output paths supplied in scientific configuration
do not select worker destinations: both nested and scenario output directories
are set by the worker.

JSONL keeps result reads incremental. Table requests are paginated and charts
receive bounded subsets, with available totals retained so truncation can be
shown. Historical listings read metadata, not every historical result dataset.
HTTP record/table pages are limited to 500 rows, chart responses to 5,000 rows,
and facets to 500 values per dimension. Comparisons accept two to four completed
runs, read at most 500 summary rows per run and return at most 5,000 paired detail
rows, with explicit truncation warnings. Charts select one
grid/model/variant/metric group rather than pooling incompatible cells.
The engine still builds one run's results in worker memory; JSONL persistence
does not make the scientific runner itself streaming.

Aggregate uncertainty uses the engine's existing aggregation functions and
retains scenario/grid/model/variant grouping. Charts should select compatible
groups and preserve proportions and physical/financial units. Missing metrics
remain unavailable rather than being synthesized. Comparing uncontrolled runs
does not establish causation; matched differences require compatible seeds,
trial structure, definitions and experimental assumptions.

## Local trust boundary

This is an unauthenticated local research service. Bind both development servers
to loopback and use a trusted local storage directory and trusted scenario files.
It is not suitable for public exposure, shared untrusted hosts or multiple API
writers. There is no cloud service, wallet, contract deployment or real financial
transaction execution.

The optional `FAN_GOVERNANCE_CONFIGS` setting selects an absolute, server-owned
scenario directory. Browser requests cannot choose arbitrary filesystem paths or
shell commands. The API starts a fixed Python module with an argument list and
`shell=False`; engine/model extension code is trusted server code.

Future deployment to multiple users requires authentication, authorization,
cross-origin controls, shared queue ownership, durable leases and a database or
equivalent transactional repository. Those changes belong at these boundaries,
without moving scientific calculations into the browser.
