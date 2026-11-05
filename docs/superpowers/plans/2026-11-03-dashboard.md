# Phase 3.5 Research Dashboard Implementation Plan

> **For agentic workers:** Use focused parallel implementation followed by integrated review and real end-to-end verification.

**Goal:** Operate the existing governance research engine entirely through a local web dashboard.

**Architecture:** React/TypeScript/Vite consumes a versioned FastAPI API. Registry-derived JSON schemas drive model forms. Managed subprocesses execute existing scenario experiments. Interchangeable filesystem repositories persist immutable configurations, run records, progress and paginated artifacts. No scientific formulas move into JavaScript.

**Tech Stack:** FastAPI/Pydantic, React/TypeScript/Vite/Tailwind, React Router, TanStack Query, React Hook Form/Zod, Plotly, pytest/Vitest/Playwright.

**Spec:** [Phase 3.5 request](../../PHASE35_REQUEST.md). Its explicit implementation instructions authorize the complete application; routine design choices below are implementation decisions.

## Global constraints

- Local-only, loopback defaults, no cloud, database server, blockchain, wallet or fabricated results.
- Preserve the Phase 1â€“3 package and CLI, optional dashboard dependencies.
- Authoritative validation includes all expanded grids and registry factories, bounded workload, enforced run output paths.
- Process-based queue with controlled concurrency, real termination on cancellation/timeout, explicit restart recovery.
- Atomic persistence and opaque IDs; no API-supplied filesystem paths or shell commands.
- Paginated output reads and bounded plot queries; never aggregate incompatible grid/model/variant populations into a single scientific estimate.

## Interfaces and file ownership

1. Foundation: `api/catalog.py`, `api/validation.py`, `api/schemas.py`, `storage/{interfaces,filesystem}.py`, `integrations/interfaces.py`; tests for discovery, validation, traversal, atomic persistence. Model catalog shape `{models:[{id,name,category,description,schema,defaults}]}`. Capabilities `{version,schema,defaults,limits,integrations}`. Validation returns normalized ScenarioConfig and workload metadata.
2. Execution: `api/jobs.py`, `api/worker.py`; manager methods submit/config, list/get, cancel/delete/shutdown. Parent owns run statuses; worker writes separate progress/output files. File repository uses UUID IDs and records JSON dictionaries.
3. Results/API integration: `api/results.py`, `api/main.py`, routes; existing scenario runner produces real JSONL tables and aggregate uncertainty. GET tables paginated/filterable/sortable, chart subsets bounded, export ZIP/CSV/JSON, comparisons preserve cells and warn about mismatched assumptions.
4. Frontend: modular shell, eight pages, schema forms plus model selector widgets, advanced YAML/JSON, scenarios/config persistence, real run polling, categorized results, comparisons, history/settings/integration discovery. Typed API client and forms never contain governance formulas.
5. Verification/docs: baseline tests, backend lifecycle/integration tests, frontend tests, real Playwright full flow, package build, instructions, threat boundaries/known limits.

## Review focus

- Invalid nested strategy parameters and excessive Cartesian grids rejected before spawning.
- Cancelling queued/running jobs never leaves computation behind; restart recovery never reports orphan jobs as running.
- Traversal/symlink tricks and output-path injection cannot escape the storage root.
- Sparse/undefined metrics and failed jobs show explicit states; paired comparisons validate seeds and definitions.
- Form edits and YAML imports retain normalized backend values; missing schemas remain editable through JSON rather than dropping parameters.

## Execution checklist

- [x] Record current test baseline and repository findings.
- [x] Build and test schema discovery, storage and authoritative validation.
- [x] Build and test managed jobs, restart recovery, termination and bounded artifact APIs.
- [x] Build frontend and verify form/scenario/run/result/history workflows.
- [x] Run real simulations, unit and end-to-end tests; inspect the rendered UI.
- [x] Complete architecture, usage, integration and verification documentation.

## Implementation choices

The requested React/FastAPI approach fits the existing Pydantic Python engine. A static browser-only application cannot execute that engine; a Python-only UI would not provide the requested modular React client. PostgreSQL/Redis are deferred through storage interfaces. A single local scheduler with bounded subprocess concurrency is sufficient for the initial application. Phase 3 has no exact per-trial callback, so its job progress starts indeterminate and only reports completed work when the worker can actually measure it.
