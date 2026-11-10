"""Bounded deterministic trial processes with parent-death cleanup."""

import multiprocessing as mp
import os
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from queue import Empty, Full

from fan_governance.core.engine import effective_voting_specs
from fan_governance.scenarios.runner import ScenarioResults, _run_scenario_serial, expanded_configs

_PROGRESS = None


def available_resources():
    cpus = (
        len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)
    )
    memory = 4 * 1024**3
    try:
        values = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
        memory = int(values["MemAvailable"].split()[0]) * 1024
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if quota != "max":
            cpus = min(cpus, max(1, int(quota) // int(period)))
        limit = Path("/sys/fs/cgroup/memory.max").read_text().strip()
        if limit != "max":
            used = int(Path("/sys/fs/cgroup/memory.current").read_text())
            memory = min(memory, max(0, int(limit) - used))
    except (OSError, ValueError, KeyError):
        pass
    return cpus, memory


def recommended_workers(population, *, cpus=None, memory_bytes=None, requested=0):
    detected_cpu, detected_memory = available_resources()
    cpus = detected_cpu if cpus is None else cpus
    memory_bytes = detected_memory if memory_bytes is None else memory_bytes
    # Reserve half the available memory for merged artifacts and the UI/OS.
    # This is a conservative sizing heuristic, not an enforced memory quota.
    memory_workers = max(1, int(memory_bytes * 0.5) // (128 * 1024**2 + population * 65536))
    desired = requested if requested > 0 else min(8, max(1, cpus - 2))
    return max(1, min(desired, cpus, memory_workers, 32))


def _initialize(progress, parent_liveness):
    global _PROGRESS
    _PROGRESS = progress
    progress.cancel_join_thread()

    def watch_parent():
        try:
            parent_liveness.recv_bytes()
        except (EOFError, OSError):
            os._exit(1)

    # spawn passes only the read endpoint: no child can keep the parent's
    # write endpoint alive. EOF stops descendants even after a forced kill.
    threading.Thread(target=watch_parent, daemon=True).start()


def _execute(configuration, index, task, emit):
    from fan_governance.scenarios.config import ScenarioConfig

    last = float("-inf")

    def report(event):
        nonlocal last
        now = time.monotonic()
        if now - last >= 0.2 or event["completed_trials"] == event["total_trials"]:
            fraction = event["completed_trajectories"] / event["total_trajectories"]
            try:
                _PROGRESS.put_nowait((index, fraction, os.getpid()))
            except Full:
                pass
            last = now

    result = _run_scenario_serial(
        ScenarioConfig.model_validate(configuration),
        task=task,
        progress_callback=report if emit else None,
    )
    return result, os.getpid()


def run_parallel(config, workers, progress_callback=None):
    started = time.perf_counter()
    expanded = list(expanded_configs(config))
    tasks, weights = [], []
    for grid_index, (_, candidate, _) in enumerate(expanded):
        weight = len(effective_voting_specs(candidate.simulation)) * (
            3
            + bool(candidate.attacks and candidate.economics.shocks)
            + bool(candidate.attacks and candidate.defenses)
        )
        for trial in range(candidate.experiment.trials):
            tasks.append((grid_index, trial))
            weights.append(weight)
    workers = min(
        workers,
        len(tasks),
        recommended_workers(
            max(c.simulation.population.size for _, c, _ in expanded), requested=workers
        ),
    )
    context = mp.get_context("spawn")
    queue = context.Queue(maxsize=workers * 4)
    receive, liveness = context.Pipe(duplex=False)
    pool = ProcessPoolExecutor(
        max_workers=workers, mp_context=context, initializer=_initialize, initargs=(queue, receive)
    )
    output = ScenarioResults()
    pending, buffered, fractions = {}, {}, {}
    next_submit = next_merge = completed_trials = 0
    completed_work = 0.0
    total_work = sum(weights)
    process_ids = set()
    successful = False
    configuration = config.model_dump(mode="json")

    def report(index=None, fraction=0):
        nonlocal completed_work
        if index is not None:
            previous = fractions.get(index, 0)
            fraction = max(previous, min(1, fraction))
            completed_work += (fraction - previous) * weights[index]
            fractions[index] = fraction
        if progress_callback:
            progress_callback(
                {
                    "completed_trials": completed_trials,
                    "total_trials": len(tasks),
                    "completed_trajectories": min(total_work, completed_work),
                    "total_trajectories": total_work,
                    "worker_process_ids": sorted(process_ids),
                }
            )

    try:
        report()
        while next_merge < len(tasks):
            # Bound both in-flight tasks and out-of-order results to one worker window.
            while next_submit < min(len(tasks), next_merge + workers):
                future = pool.submit(
                    _execute,
                    configuration,
                    next_submit,
                    tasks[next_submit],
                    progress_callback is not None,
                )
                pending[future] = next_submit
                next_submit += 1
            done, _ = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)
            while True:
                try:
                    index, fraction, pid = queue.get_nowait()
                except Empty:
                    break
                process_ids.add(pid)
                report(index, fraction)
            for future in done:
                index = pending.pop(future)
                result, pid = future.result()
                process_ids.add(pid)
                buffered[index] = result
                completed_trials += 1
                report(index, 1)
            while next_merge in buffered:
                result = buffered.pop(next_merge)
                for name in ("summary", "elections", "timeseries", "events"):
                    getattr(output, name).extend(getattr(result, name))
                if not output.metadata:
                    output.metadata = result.metadata
                next_merge += 1
        successful = True
    finally:
        if not successful:
            liveness.close()  # Stop expensive unfinished tasks before waiting for the pool.
        pool.shutdown(wait=True, cancel_futures=True)
        liveness.close()
        receive.close()
        queue.close()
        queue.join_thread()
    output.metadata.update(
        grid_cells=len(expanded),
        elapsed_seconds=time.perf_counter() - started,
        execution={
            "workers": workers,
            "tasks": len(tasks),
            "process_ids": sorted(process_ids),
            "mode": "parallel_trials",
            "merge_order": "grid_then_trial",
        },
    )
    return output
