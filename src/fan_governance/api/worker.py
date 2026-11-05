"""Trusted process entrypoint: execute the existing engine and publish artifacts."""

import argparse
import json
import os
import sys
import tempfile
import threading
import traceback
from pathlib import Path

from fan_governance.api.jobs import engine_version
from fan_governance.api.validation import validate_configuration
from fan_governance.scenarios.output import _clean, aggregate_trials, paired_defense_effectiveness
from fan_governance.scenarios.runner import run_scenario
from fan_governance.storage.filesystem import FileRepository


def atomic_json(destination: Path, value):
    atomic_rows(destination, [_clean(value)], lines=False)


def atomic_rows(destination: Path, rows, *, lines=True):
    """Publish only complete files; JSONL supports bounded downstream reads."""
    descriptor, temporary = tempfile.mkstemp(prefix=".worker-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            for row in rows:
                json.dump(_clean(row), stream, allow_nan=False, separators=(",", ":"))
                if lines:
                    stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def execute(root: Path, run_id: str):
    repository = FileRepository(root)
    record = repository.get("runs", run_id)
    config, _ = validate_configuration(record["configuration"])
    directory = repository.directory("runs", run_id)
    artifacts = directory / "artifacts"
    artifacts.mkdir(exist_ok=True)
    if artifacts.is_symlink() or artifacts.resolve().parent != directory.resolve():
        raise ValueError("Unsafe artifact directory")
    # All file destinations derive from repository IDs. Caller output paths
    # never control a worker destination, including nested simulation output.
    config.output.directory = artifacts
    config.simulation.output.directory = artifacts
    total = record["progress"]["total_trials"]
    atomic_json(
        directory / "progress.json",
        {
            "completed_trials": None,
            "total_trials": total,
            "percentage": None,
        },
    )
    results = run_scenario(config)
    tables = {
        "summary": results.summary,
        "elections": results.elections,
        "timeseries": results.timeseries,
        "events": results.events,
        "aggregate": aggregate_trials(results.summary),
        "defense_effectiveness": paired_defense_effectiveness(results.summary),
    }
    for name, rows in tables.items():
        atomic_rows(artifacts / f"{name}.jsonl", rows)
    configuration = record["configuration"]
    atomic_json(artifacts / "configuration.json", configuration)
    manifest = {
        "label": "Synthetic simulation results",
        "configuration": configuration,
        "metadata": results.metadata | {"engine_version": engine_version()},
        "row_counts": {name: len(rows) for name, rows in tables.items()},
        "columns": {
            name: sorted({key for row in rows for key in row}) for name, rows in tables.items()
        },
        "uncertainty": "Wilson 95% intervals for binary trial outcomes; continuous trial quantiles. Groups preserve scenario/grid/model/variant.",
    }
    atomic_json(artifacts / "manifest.json", manifest)
    atomic_json(
        directory / "progress.json",
        {
            "completed_trials": total,
            "total_trials": total,
            "percentage": 100,
        },
    )
    atomic_json(directory / "success.json", {"run_id": run_id, "status": "completed"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--watch-parent", action="store_true")
    args = parser.parse_args()
    if args.watch_parent:
        # The manager keeps this pipe open without writing to it. The OS closes
        # it even after a crash or force kill; EOF then stops engine computation
        # without relying on PID identity, polling, or platform-specific signals.
        parent_descriptor = os.dup(sys.stdin.fileno())
        null_descriptor = os.open(os.devnull, os.O_RDONLY)
        os.dup2(null_descriptor, sys.stdin.fileno())
        os.close(null_descriptor)
        if sys.platform == "win32":
            import ctypes
            import msvcrt

            # Engine provenance runs Git. Its subprocess stdin must inherit
            # DEVNULL rather than the manager's private liveness pipe.
            ctypes.windll.kernel32.SetStdHandle(
                -10, ctypes.c_void_p(msvcrt.get_osfhandle(sys.stdin.fileno()))
            )

        def stop_on_parent_exit():
            # Read the raw descriptor: a daemon holding BufferedReader's lock
            # can otherwise block normal Python interpreter shutdown.
            while os.read(parent_descriptor, 1):
                pass
            os._exit(1)

        threading.Thread(target=stop_on_parent_exit, name="parent-liveness", daemon=True).start()
    try:
        execute(args.root, args.run_id)
    except Exception:
        # Tracebacks go only to the bounded local log. The API exposes a stable
        # diagnostic without reflecting configuration values or local paths.
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
