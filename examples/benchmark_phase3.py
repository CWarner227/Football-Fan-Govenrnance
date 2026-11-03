"""Reproduce synthetic Phase 3 benchmarks in isolated processes.

Run with the project environment: python examples/benchmark_phase3.py.
Wall time excludes imports and export; peak working set includes the whole worker
process and is measured without tracemalloc overhead. Each workload evaluates
control/unprotected/defended variants of one equal-vote governance model.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "results" / "phase3_benchmarks"


def peak_working_set():
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "PeakWorkingSetSize",
                    "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage",
                    "PagefileUsage",
                    "PeakPagefileUsage",
                )
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        if not psapi.GetProcessMemoryInfo(
            kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def run_case(case):
    from fan_governance.scenarios.config import ScenarioConfig
    from fan_governance.scenarios.runner import run_scenario

    large = case == "10000_supporters_36_months"
    population, duration, trials = (10000, 36, 1) if large else (100, 12, 100)
    config = ScenarioConfig.model_validate(
        {
            "name": case,
            "timeline": {"duration_months": duration},
            "elections": {"interval_months": 12},
            "simulation": {"population": {"size": population}, "voting": {"strategies": ["equal"]}},
            "experiment": {"trials": trials, "seed": 20261103},
            "honest_turnout": 0.4,
            "attacks": [
                {
                    "attacker_id": "wealthy",
                    "name": "wealthy_takeover",
                    "financial_budget": 1000000,
                    "parameters": {"contribution_budget": 20000},
                },
                {
                    "attacker_id": "minority",
                    "name": "low_turnout",
                    "financial_budget": 1000000,
                    "parameters": {"hostile_population_share": 0.05},
                },
            ],
            "defenses": [
                {"name": "identity_verification", "parameters": {"strength": 0.95}},
                {"name": "waiting_period", "parameters": {"days": 180}},
                {"name": "quorum", "parameters": {"threshold": 0.3}},
            ],
            "economics": {
                "membership_fee": 5,
                "contribution_willingness": 0.01,
                "starting_cash": 100000,
                "operating_revenue": 20000,
                "operating_expenses": 15000,
                "wages": 10000,
                "shocks": [
                    {
                        "name": "economic_downturn",
                        "start_month": 6,
                        "duration_months": 6,
                        "severity": 0.3,
                        "recovery_months": 6,
                    }
                ],
            },
            "output": {"directory": str(DESTINATION / case)},
        }
    )
    started = perf_counter()
    result = run_scenario(config)
    seconds = perf_counter() - started
    peak = peak_working_set()
    report = {
        "label": "Synthetic simulation benchmark",
        "case": case,
        "population": population,
        "duration_months": duration,
        "trials": trials,
        "models": 1,
        "variants": 3,
        "wall_seconds": seconds,
        "peak_working_set_bytes": peak,
        "peak_working_set_mib": peak / 1024**2,
        "elections": len(result.elections),
        "economic_rows": len(result.timeseries),
        "event_rows": len(result.events),
        "summary_rows": len(result.summary),
        "metadata": result.metadata,
        "configuration": config.model_dump(mode="json"),
        "trial_summary": result.summary,
        "measurement": "Isolated worker; perf_counter run_scenario only; process peak working set without allocation tracing.",
    }
    DESTINATION.mkdir(parents=True, exist_ok=True)
    (DESTINATION / f"{case}.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key not in {"configuration", "metadata", "trial_summary"}
            },
            indent=2,
        ),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", choices=["10000_supporters_36_months", "100_trials_100_supporters"]
    )
    args = parser.parse_args()
    if args.case:
        run_case(args.case)
        return
    for case in ("10000_supporters_36_months", "100_trials_100_supporters"):
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--case", case], cwd=ROOT, check=True
        )
    reports = [
        json.loads((DESTINATION / f"{case}.json").read_text(encoding="utf-8"))
        for case in ("10000_supporters_36_months", "100_trials_100_supporters")
    ]
    (DESTINATION / "benchmarks.json").write_text(
        json.dumps(reports, indent=2, allow_nan=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
