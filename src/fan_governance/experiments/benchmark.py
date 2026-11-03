"""Reproducible workloads measured in fresh processes, without export overhead.

Run ``python -m fan_governance.experiments.benchmark --config CONFIG --output FILE``.
Timing includes population generation and elections. Memory is the absolute process
lifetime resident high-water mark, including interpreter/imports, not an increment
over pre-run memory. Workers isolate high-water marks between benchmark cases.
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from fan_governance.core.config import ModelSpec, SimulationConfig, load_config
from fan_governance.experiments.runner import ExperimentRunner

SIX_MODELS = ("equal", "proportional", "capped", "diminishing", "hybrid", "expertise")
CASES = {
    "10k_equal": (10_000, 1, ("equal",)),
    "10k_100_trials_six_models": (10_000, 100, SIX_MODELS),
    "100k_equal": (100_000, 1, ("equal",)),
}


def workload_config(
    config: SimulationConfig,
    *,
    size: int,
    trials: int,
    strategies: list[str | ModelSpec] | None = None,
) -> SimulationConfig:
    """Copy and validate a single funding workload, retaining configured model parameters."""
    workload = config.model_copy(deep=True).model_dump()
    workload["population"]["size"] = size
    workload["experiment"].update(
        trials=trials,
        population_sizes=None,
        population_profiles=None,
        waiting_periods=None,
        participation_levels=None,
        wealth_distributions=None,
        participation_models=None,
        proposal_categories=["funding"],
    )
    workload["proposal"].update(category="funding", voting_strategy=None)
    if strategies is not None:
        configured = {spec.name: spec for spec in config.voting.specs()}
        workload["voting"]["strategies"] = [
            (
                configured.get(spec, ModelSpec(name=spec)) if isinstance(spec, str) else spec
            ).model_dump()
            for spec in strategies
        ]
    return SimulationConfig.model_validate(workload)


def peak_resident_memory() -> tuple[int | None, str]:
    """Return the process-lifetime resident high-water mark in bytes where available."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if psapi.GetProcessMemoryInfo(
            kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            return int(counters.PeakWorkingSetSize), "windows.PeakWorkingSetSize"
        return None, "unavailable: GetProcessMemoryInfo failed"
    try:
        import resource
    except ImportError:
        return None, "unavailable: resource module missing"
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak * (1 if sys.platform == "darwin" else 1024)), "resource.ru_maxrss"


def measured_run(config: SimulationConfig) -> dict:
    """Measure ExperimentRunner.run only; return actual row count and complete provenance."""
    runner = ExperimentRunner()
    started = perf_counter()
    results = runner.run(config)
    elapsed = perf_counter() - started
    memory, method = peak_resident_memory()
    from fan_governance import __version__
    from fan_governance.output.provenance import source_provenance

    return {
        **source_provenance(),
        "fan_governance": __version__,
        "population_size": config.population.size,
        "trials": config.experiment.trials,
        "strategies": [spec.name for spec in config.voting.specs()],
        "proposal_category": config.proposal.category,
        "runtime_seconds": elapsed,
        "result_rows": len(results),
        "peak_resident_memory_bytes": memory,
        "memory_method": method,
        "memory_scope": "absolute process lifetime peak; includes interpreter/imports; not incremental",
        "timing_scope": "ExperimentRunner.run; includes population generation; excludes imports/config/output",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "process_id": os.getpid(),
        "configuration": config.model_dump(mode="json"),
    }


def run_case(
    config: SimulationConfig,
    *,
    size: int,
    trials: int,
    strategies: list[str | ModelSpec] | None = None,
) -> dict:
    return measured_run(workload_config(config, size=size, trials=trials, strategies=strategies))


def run_benchmarks(
    config_path: str | Path, *, size: int | None = None, trials: int | None = None
) -> dict:
    """Launch one fresh worker per workload. Overrides support small reproducible smoke runs."""
    rows = []
    for name in CASES:
        command = [
            sys.executable,
            "-m",
            "fan_governance.experiments.benchmark",
            "--config",
            str(Path(config_path).resolve()),
            "--worker",
            name,
        ]
        if size is not None:
            command.extend(["--size", str(size)])
        if trials is not None:
            command.extend(["--trials", str(trials)])
        completed = subprocess.run(command, capture_output=True, text=True, check=True)
        rows.append(json.loads(completed.stdout))
    return {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "config_path": str(Path(config_path).resolve()),
        "fresh_process_per_case": True,
        "benchmark_overrides": {"size": size, "trials": trials},
        "benchmarks": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", choices=CASES)
    parser.add_argument("--size", type=int, help="Override supporters per case (for smoke runs)")
    parser.add_argument("--trials", type=int, help="Override trials per case (for smoke runs)")
    args = parser.parse_args()
    if args.worker:
        size, trials, strategies = CASES[args.worker]
        report = run_case(
            load_config(args.config),
            size=size if args.size is None else args.size,
            trials=trials if args.trials is None else args.trials,
            strategies=list(strategies),
        )
        report["case"] = args.worker
        print(json.dumps(report, allow_nan=False))
    else:
        if args.output is None:
            parser.error("--output is required when running the benchmark suite")
        report = run_benchmarks(args.config, size=args.size, trials=args.trials)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
