# Simulation performance investigation — 2026-11-10

## Why the pilot timed out

Failed run `93907b28abb442cd833b3b5314795e00` was the unmodified Study 01 pilot:
10,000 supporters, three population profiles, two proposal categories, ten trials
per cell, six voting models and three paired variants. It expands to **60
trial/cell combinations and 1,080 labeled trajectories**. It timed out at
1,800.57 seconds with 52/60 trial/cell combinations completed. The timeout was
enforced correctly; the workload was too slow.

Docker had access to **18 CPUs and 23.22 GiB RAM**, with no additional CPU quota.
The host has 18 logical processors and approximately 47.6 GiB RAM. The engine
executed trials sequentially, leaving most CPU capacity unused.

A profile of one real ordinary-population cell/trial found 1.62 million Pydantic
`model_copy` calls, heavy recursive copying, investor projection with no
investors, and unused per-person hostile RNG construction. The three variants
were also identical when there were no attacks, defenses or shocks.

Profiled timings include profiler overhead: the profile took 116 seconds,
whereas the corresponding unprofiled trial took 29.44 seconds. Profile cumulative
times overlap and should not be added together or treated as wall-clock savings.

## Changes

- Run independent grid/trial tasks in spawned CPU processes. All models, variants
  and matched references for one trial remain together. Trial indices, master
  seeds and grid labels retain their original identities.
- Merge full results in original grid/trial order, regardless of completion order.
  Bound in-flight tasks and buffered out-of-order results to the worker window.
- Automatically select up to eight processes using available CPUs, Linux CPU
  quota and memory estimates. One dashboard job can use multiple CPU cores while
  the job queue still permits one active research job at a time.
- Limit BLAS/OpenMP libraries to one thread per process in Compose, avoiding
  nested thread oversubscription.
- Reuse identical no-attack/no-defense/no-shock variant trajectories, retaining
  separately labeled output rows. Custom injected registries disable this reuse.
- Isolate mutable supporter attributes with a dictionary copy; do not recursively
  copy every scalar model field. Membership fields are scalar and copied normally.
- Skip investor projection when no investors exist. Construct hostile RNG streams
  only for hostile behavior. The actual named RNG streams and draws are unchanged.
- Use native scalar cleanup fast paths and C-backed JSON encoding for event
  exports. Null handling, nonfinite normalization, NumPy values, paths, dates,
  ordering and JSON contents are preserved.
- Child processes watch a private parent-death pipe. Cancellation, timeout or
  abrupt owner failure stops descendants instead of leaving computation behind.
- Progress combines actual work from all processes, including reference runs and
  reused completed results. It remains monotonic and only reaches 100% on success.

## Measured results on this computer

| Measurement | Before | After |
| --- | ---: | ---: |
| One ordinary-population cell/trial, sequential | 29.44 s | 6.72 s |
| Complete pilot, before the export optimization | Timed out at 1,800.57 s | 307.7 s, completed |
| Complete pilot, final engine and exporter | Timed out at 1,800.57 s | **143.3 s, completed** |

The isolated sequential improvement is **4.38×**. The original full run never
completed, so its complete-runtime speedup is not known; comparing a completed
run to a timeout is not a matched full-runtime benchmark.

The final full pilot used **eight distinct trial processes**. A Docker sample
during parallel computation showed **647% CPU** (approximately 6.5 logical cores
at that instant), and observed memory was approximately **6.1 GiB**. It completed
all 60 trial/cell combinations and exported:

- 1,080 trial summary rows and 1,080 election rows;
- 2,160 time-series rows;
- **10,800,000 event rows**, approximately **4.0 GB** of JSONL;
- 5,256 aggregate rows and 36 defense-effectiveness rows.

The event log explains the long finalization phase after CPU simulation finishes.
A 10,000-row sample of actual events showed a 3.08× serialization improvement
with identical bytes. The original serialized writer occupied most of the first
optimized run's remaining time.

These are local observed timings, not performance guarantees. Final verification
overlapped other regression checks. Seeds, population sizes, trial counts and the
30-minute timeout were not changed to obtain these results.

## Result integrity and available runs

The one-trial scientific-table SHA-256 fingerprints matched the pre-optimization
engine exactly. Tests compare serial/parallel summaries, elections, timelines
and events, including adversarial cases and extra matched references.

All six exported scientific tables were also **byte-for-byte identical** between
the two complete optimized pilot runs, including the entire 4 GB event file.
Manifests include execution metadata (workers, task count, process IDs and merge
order); timing and process metadata naturally differ between runs.

- Original failed run: `93907b28abb442cd833b3b5314795e00` (preserved).
- Intermediate performance verification: `77557b12a8594b689263627e1b83e5cf`.
- Final optimized pilot: **`a202915544c249b786ee41a418a03e54`**.

Both successful verifications use the same pilot seed, 99001. They are repeat
executions of the same samples, **not** twenty independent trials per condition.
Use the final run when inspecting this pilot. The 100-trial presentation batches
still require their separate B01–B04 seeds.

Detailed profile and fingerprint records are stored in the local Docker volume
under `/app/data/dashboard/performance/`; generated results remain outside Git.

## Resource control

The current Docker setup uses automatic selection by default. To override it,
copy `.env.example` to `.env` and set:

```dotenv
FAN_GOVERNANCE_TRIAL_WORKERS=0
```

`0` selects automatically, `1` forces serial execution, and a larger positive
value requests that many processes. Explicit counts are still bounded by CPU,
estimated memory availability, task count and a hard maximum of 32. Automatic
selection leaves two logical CPUs available where possible and caps at eight.
The public library also accepts `run_scenario(config, workers=4)`; its default
remains serial for compatibility. Parallel execution uses the default installed
registry; injected custom registries retain serial behavior.

After existing runs finish, restart with Start-Dashboard.cmd to apply environment
changes. The existing frontend presets automatically use the optimized worker;
there is no need to regenerate or change their scientific settings.

Memory sizing is a conservative heuristic, not an enforced OS memory quota.
The engine still retains final result rows in its owner process before writing
artifacts. Larger campaigns can therefore require more memory and disk than a
single pilot; the provided batching remains useful.

## Verification

- Complete Python suite: **420 passed, 1 skipped in 165.46 seconds**. The skip
  remains Windows symlink creation privileges.
- Whole-repository Ruff lint and formatting passed for **124 Python files**.
- Real process tests verify deterministic merging, progress, automatic sizing,
  cancellation and exit of child workers after abrupt owner death.
- JSON export tests cover nested mappings, NumPy scalars, Unicode, nulls,
  infinities/NaN, dates, paths and negative zero.
- Both real Chromium dashboard workflows passed against the final Docker app in
  **18.2 seconds**, including progress/ETA, execution, exports, comparison and
  UI cancellation of an actual parallel job.
