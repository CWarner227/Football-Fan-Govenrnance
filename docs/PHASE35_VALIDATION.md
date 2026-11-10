# Phase 3.5 validation evidence

This file records observed checks. An unexecuted command or planned test is not
a passing result. Final integrated checks are recorded below.

## Foundation verification observed on 2026-11-03

Executed from the repository root:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_dashboard_foundation.py -q --basetemp=.pytest-dashboard-foundation-k
```

Observed result: **22 passed, 1 skipped in 0.71 seconds**. The skipped test creates
an actual symlink; this Windows session lacks the required symlink creation
privilege/developer mode. Production code still rejects symlinks and junctions.

Coverage includes dynamic discovery of six voting models, seven attacks, six
defenses and four shocks; metadata for a newly registered model; nested hybrid
schema and parameter validation; default normalization; every-cell grid
validation; population/trial/grid/workload limits; membership growth budgeting;
extra matched reference trajectories; incompatible quorum policies; unsupported
distribution rejection; atomic save failure retaining the previous record;
reopen/list/delete persistence; and malformed/path-traversal identifier rejection.
The comparison request envelope also rejects more than four run IDs, matching
the service's bounded comparison contract.

The new behavior was exercised tests-first: absent-module failure preceded the
foundation implementation; growth, malformed hybrid, incompatible quorum,
reference-trajectory, nested strict-type and unavailable-distribution regressions
were observed failing before fixes were applied.

Executed Ruff checks on the owned foundation modules and test file after
formatting: **All checks passed**. This is a scoped result, not an assertion that
the entire repository was linted.

Executed focused existing-engine regression checks:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_foundation.py tests/test_extensions.py tests/test_phase2_voting.py tests/test_phase3_quorum_registry.py -q --basetemp=.pytest-dashboard-foundation-regression
```

Observed result: **85 passed in 3.09 seconds**. This covers original foundation,
extension injection, Phase 2 voting and Phase 3 quorum/registry behavior after the
registry discovery accessor was added.

## Final integrated checks

Final verification on 2026-11-04:

- Complete Python suite: **387 passed, 1 skipped in 37.36 seconds**. The skip is
  the Windows symlink privilege check described above. This includes the original
  347-test baseline and the new dashboard tests.
- Whole repository Ruff lint passed; Ruff format check passed for **119 files**.
- Frontend: **20 Vitest tests passed**, including bounded comparison DOM rendering,
  saved-configuration/run pagination, authoritative trial controls, axes, cohort
  selection, population profiles and measured execution history.
- Frontend ESLint and TypeScript/production build passed. Plotly is lazy-loaded;
  Vite reports large chunks (Plotly 4.84 MB, 1.47 MB gzip; main client approximately
  570 KB, 177 KB gzip). Dependency comment annotation warnings are nonfatal.
- Source distribution and wheel built for **0.3.5**. Archive inspection verified
  dashboard Python modules, frontend source and its lockfile, with local run data,
  node_modules and tool caches excluded.
- Built single-server SPA root and `/builder` navigation returned HTML successfully;
  `/api/v1/health` returned 200 through the same API process.

Backend tests exercise real workers and results, configuration persistence across
repository reopen, source/profile discovery, schema validation, queue/restart
recovery, cancellation and timeout process termination, abrupt parent death,
bounded diagnostics, origin controls, pagination/filter/sort, facets beyond the
first chart window, CSV/JSON/ZIP export, compatibility checks, and comparison
response limits. Actual worker exit was checked rather than merely asserting a
cancelled status.

Browser checks use real Chromium and the real local Python service. The initial
complete workflow passed two tests, including configuration edit/validate/save,
real simulation, rendered Plotly chart, CSV download, history reopen/rerun,
matched comparison, and cancellation of actual computation.

Final production-mode rerun: **2 Playwright tests passed in 10.2 seconds** against
`http://127.0.0.1:8000`, after the final UI corrections. A repeated-history selector
was tightened after it could match the rerun and original as the same checkbox;
this was a test ambiguity rather than a simulated engine result. The final run
used the completed build without concurrent asset changes.

Rendered overview and governance-results screenshots were inspected. Real local
history counts, execution duration bars, completed engine metadata, selected
cohort, actual Gini data and paginated result rows were visible. Screenshots and
browser traces remain ignored local test artifacts.

A Windows Vite native-module file lock prevented the first dependency restore.
After stopping that owned preview process, `npm ci --no-audit --no-fund --offline`
restored the lockfile packages successfully. Frontend tests, lint, type checking,
build and Chromium were rerun with those packages.

## Scope and limitations

The current engine builds each run's result objects in worker memory before
persisting JSONL. API result readers can be bounded without claiming that the
scientific engine is itself streaming. Workload is an estimate, supplemented by
process concurrency and timeouts; it is not an operating-system memory quota.

The application is an unauthenticated trusted local research tool. Only one API
process may own its data directory. Blockchain is a disabled extension boundary,
not an implemented integration. Intermediate trial progress remains indeterminate
where the engine exposes no reliable callback.

## Docker delivery verification (2026-11-04)

The `Chris` branch adds a multi-stage Dockerfile, Compose configuration,
`.dockerignore`, and Windows start/stop launchers. FastAPI serves the production
React build and `/api/v1` from one non-root container on loopback port 8000.

Observed checks:

- `docker compose config --quiet` passed.
- Native Linux ARM64 image build and health-checked startup passed on Docker Desktop.
- Runtime identity verified as UID/GID 10001; built frontend assets present;
  host `node_modules` and Git metadata absent.
- Both real Chromium end-to-end tests passed against the container in **9.7 seconds**.
- Forced container recreation preserved a saved configuration, a completed run,
  and all three summary rows from its real engine execution.
- `Start-Dashboard.cmd` completed successfully, waited for health, reused cached
  build layers and launched the dashboard URL. PowerShell parser checks passed.

The Compose volume is separate from host `data/dashboard/`. Stop/rebuild preserves
it; explicitly deleting the volume removes its stored configurations and runs.
Docker Desktop must be running in Linux-container mode and host port 8000 must
be available. The container remains running for the requested local handoff.

## Presentation preset verification (2026-11-10)

Added 95 configurations across 19 study groups: one 10-trial pilot and four
25-trial presentation batches per group. All 76 configured cells are validated
through the dashboard's actual schema, factories and resource checks; the
largest preset has a 274,500,000 work-unit estimate (below 300,000,000).

Observed checks:

- Complete Python suite: **410 passed, 1 skipped in 185.52 seconds**. The skip
  remains the Windows symlink privilege test. All 121 Python files pass Ruff
  lint and formatting checks.
- New tests cover matched seed blocks, six voting models, baseline profile and
  proposal axes, waiting-period timing, alias budgets, defense packages,
  cross-platform idempotent import, conflict preservation, and read-only
  container import mode.
- **19 actual single-trial smoke executions** passed, one per study group using
  its first grid cell and all six models/three variants. These are execution
  checks, not completed 10-trial pilots or the presentation campaign.
- Imported all **95 presets** into the running dashboard's Saved configurations.
  Reimport from the rebuilt Linux container reported **0 created, 95 existing**.
- Real Chromium loaded and validated B01 presets for Studies 01–07 through the
  frontend, checking 25 trials and seed 11001. No study was submitted by this
  browser verification.
- `Import-Study-Configurations.cmd` successfully rebuilt/started the healthy
  Docker app, skipped existing presets, and opened Experiments. Import and
  generation do not queue simulations.

The source YAMLs, workload manifest, reproducible generator/importer and
`PRESENTATION_STUDIES.md` explain batch identity, pilot exclusion, model/variant
matching, redundant controls, and export-based cross-seed uncertainty analysis.
