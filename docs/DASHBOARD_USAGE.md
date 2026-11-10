# Running the research dashboard

Use Python 3.12 or later, `uv`, and a Node.js version supported by the installed
Vite release. Run commands from the repository root unless a different directory
is shown. No database, Redis, Docker, cloud account or blockchain node is needed.

## Start the application

Install Python dependencies:

```powershell
uv sync --all-extras --group dev
```

Start one API process on loopback:

```powershell
uv run uvicorn fan_governance.api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open the local Vite address printed in that terminal, normally
<http://127.0.0.1:5173>. Vite proxies `/api` requests to the Python service on port
8000. Open <http://127.0.0.1:8000/docs> for interactive API documentation.

Do not add `--workers` or run two API servers against the same data directory.
Keep these unauthenticated development services bound to loopback.

Optional server settings, set before starting the API:

```powershell
$env:FAN_GOVERNANCE_DATA = 'C:\research\governance-dashboard'
$env:FAN_GOVERNANCE_CONFIGS = 'C:\research\scenario-library'
```

The first setting changes the storage root; the second selects a trusted absolute
scenario library directory. Without overrides the repository scenario library
and `data/dashboard` are used. These paths are administrator settings, not form
fields or API request parameters. Preserve the data directory to retain history.

## Run a small study

1. Open **Scenarios**, inspect an existing scenario, and load it into the builder;
   or open **Simulation Builder** to start from the backend's small defaults.
2. Set the study name and seed. For the first run, use 100 supporters and one
   trial. Keep the election interval within the simulated duration.
3. Choose voting models and edit their generated controls. Add attacks, defenses
   or economic shocks only when needed for the research question.
4. Expand population, governance, economics and advanced sections as needed.
   Distribution parameters and correlations remain backend-validated.
5. Use the advanced JSON/YAML editor to inspect or import a complete scenario.
   Validate it and resolve the displayed errors before submission.
6. Save a reusable configuration, or submit the run. The server validates every
   grid cell and estimates workload before adding it to the queue.
7. Follow its queued/running/completed status. Intermediate percentages are
   intentionally absent when the engine cannot measure them. **Cancel** stops
   queued work or terminates the active worker.
8. Open **Results Explorer** after completion. Select a grid cell, voting model
   and variant, then inspect metrics, charts, timeline and raw tables.
9. Download a table as CSV/JSON or export the full run. Reopen it later from
   **Run History**.

The engine executes paired control, unprotected and defended trajectories even
for a study labeled a simulation. A one-trial study is useful for checking the
workflow; it does not provide a reliable Monte Carlo estimate of capture risk.
Use more trials when estimating uncertainty, within the published local limits.

Validation reports `total_trials` as independent Monte Carlo trials summed over
grid cells. Its separate `trajectory_runs` includes voting models, the three
paired variants and additional matched references. For example, one configured
trial can require five trajectories without becoming five independent trials.

The population profile selector loads one of six existing YAML profiles through
`/api/v1/profiles`; it does not maintain another browser-only profile library.

While a run executes, its Results page shows measured completion and an
approximate time remaining, refreshed about every 1.5 seconds. Timing starts
after the job leaves the queue. The estimate appears after the first complete
model/variant trajectory, then updates as work completes; changing population
sizes, attacks and grid settings can make it rise or fall. It is not a deadline.
The bar reserves its last portion for **Finalizing results** and reaches 100%
only on successful completion. Cancelled or failed jobs never show a live ETA.

## Pages and research interpretation

| Page | Purpose |
| --- | --- |
| Overview | Inventory, recent activity and links into real persisted runs. |
| Simulation Builder | Schema-driven setup, authoritative validation, saved configurations and submission. |
| Scenarios | Search the existing YAML library, inspect or load a scenario. |
| Experiments | Configure repeated trials and scenario grid studies. |
| Results Explorer | Summary, governance, adversarial, economics, timeline and raw output views. |
| Run History | Reopen, rerun, duplicate or delete saved work where the action is available. |
| Integrations | Discover installed capabilities; blockchain remains planned and disabled. |
| Settings | Inspect engine defaults, limits and local UI settings. |

Charts show engine-produced fields. A proportion such as turnout `0.6` means 60%;
the raw field retains its original scale. Gini measures concentration, while
effective voters describes concentration-adjusted voting influence rather than
the head count. Capture success depends on the configured attacker objective.
Financial runway is a model output under the scenario assumptions, not a forecast
or financial recommendation.

Use the comparison page to inspect completed runs side by side. Review
configuration differences and compatibility warnings before interpreting outcome
differences. Matched-trial comparisons need compatible populations, seeds,
trial identifiers and outcome definitions. The application does not pool
unrelated experiments into a single causal estimate.

Charts use bounded server subsets and tables are paginated. Export the complete
table for analysis beyond the displayed subset. A missing metric means the engine
did not produce it for that selection. It is not a measured zero.

## Errors, stopping and recovery

Validation errors identify unsupported fields, model parameters, grid paths or
resource limits. Reduce population/trials/grid size or split a study when the
workload estimate exceeds the local budget. Membership growth and attacker
operational budgets can make a small initial population expensive.

A failed run exposes a stable error; detailed worker diagnostics remain in its
local `worker.log`, which is bounded. Cancellation and timeout terminate actual
computation. Stop both development servers with Ctrl+C. On restart, queued runs
are restored and previously running records become failed; rerun them explicitly.
Partial artifacts are not presented as completed results.

Deleting a run removes its local record and artifacts. Export it first if those
results must be retained. Saved configurations and completed runs persist across
normal application restarts.

## API routes

The API is versioned under `/api/v1`; typed request/response documentation is
available at `/docs` and `/openapi.json` on the backend.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health`, `/capabilities`, `/models` | Health, engine/schema defaults, limits and registered model metadata. |
| GET | `/profiles` | Six installed YAML population profiles. |
| GET | `/scenarios`, `/scenarios/{id}` | Installed YAML scenario discovery and full configuration. |
| POST | `/configurations/validate` | Normalized configuration and bounded workload estimate. |
| POST | `/configurations/save` | Save a reusable validated configuration. |
| GET | `/configurations`, `/configurations/{id}` | List/load saved configurations. |
| DELETE | `/configurations/{id}` | Delete a saved configuration. |
| POST | `/runs` | Validate, persist and queue real engine execution. |
| GET | `/runs`, `/runs/{id}`, `/overview` | Run history/status and activity counts. |
| POST | `/runs/{id}/cancel` | Cancel queued work or terminate an active worker. |
| DELETE | `/runs/{id}` | Stop if necessary, then delete local run data. |
| GET | `/runs/{id}/results`, `/runs/{id}/events` | Paginated, searchable output rows. |
| GET | `/runs/{id}/charts`, `/runs/{id}/facets` | Bounded chart rows and available selection values. |
| GET | `/runs/{id}/export` | Full ZIP or selected-table CSV/JSON export. |
| POST | `/comparisons` | Compare two to four completed runs with compatibility warnings. |

Record/table pages have a maximum of 500 rows, chart requests 5,000 rows and
facets 500 values per dimension. Comparisons inspect at most 500 summary rows per
run and return at most 5,000 paired detail rows, with truncation warnings. Use
exports when conducting broader analysis.

## Developer checks

```powershell
uv run pytest
uv run ruff check src tests
cd frontend
npm test
npm run lint
npm run build
npm run test:e2e
```

Playwright requires its configured browser installation. Consult
[PHASE35_VALIDATION.md](PHASE35_VALIDATION.md) for checks actually executed and
any environment-specific limitations; the command list above is not test
execution evidence.
