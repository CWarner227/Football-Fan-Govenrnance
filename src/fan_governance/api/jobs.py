"""Local bounded process queue. Only the manager changes persisted run statuses."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import uuid4

from fan_governance import __version__
from fan_governance.api.responses import ProgressResponse
from fan_governance.api.validation import validate_configuration
from fan_governance.scenarios.runner import expanded_configs

TERMINAL = frozenset({"completed", "failed", "cancelled"})


def now() -> str:
    return datetime.now(UTC).isoformat()


def engine_version() -> str:
    try:
        return version("fan-governance-simulator")
    except PackageNotFoundError:
        return f"{__version__} (source checkout)"


class JobManager:
    """Run trusted worker commands with a finite queue and cancellable processes.

    A single manager owns a repository at a time. Queued jobs survive a clean
    shutdown; formerly running records fail on startup because their execution
    cannot safely be resumed or inferred from partially written artifacts.
    """

    max_queued = 20

    def __init__(self, repository, *, max_concurrent=1, timeout_seconds=1800, autostart=True):
        if max_concurrent < 1 or timeout_seconds <= 0:
            raise ValueError("Concurrency and timeout must be positive")
        self.repository = repository
        self.max_concurrent = max_concurrent
        self.timeout_seconds = timeout_seconds
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stopped = False
        self._pending: deque[str] = deque()
        self._active: dict[str, tuple[subprocess.Popen, float]] = {}
        self._logs: dict[str, threading.Thread] = {}
        self._thread: threading.Thread | None = None
        for record in sorted(repository.list("runs"), key=lambda r: (r["created_at"], r["id"])):
            if record["status"] == "running":
                self._finish(record, "failed", "Server restart interrupted this run; rerun it.")
            elif record["status"] == "queued":
                self._pending.append(record["id"])
        if autostart:
            self.start()

    def start(self):
        with self._lock:
            if self._stopped:
                raise RuntimeError("Job manager is shut down")
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._schedule, name="simulation-queue", daemon=True
                )
                self._thread.start()

    def submit(self, configuration: dict, name="", description="", kind="simulation") -> dict:
        config, _ = validate_configuration(configuration)
        if kind not in {"simulation", "experiment"}:
            raise ValueError("Unknown run kind")
        with self._lock:
            if self._stopped:
                raise RuntimeError("Job manager is shut down")
            if len(self._pending) >= self.max_queued:
                raise ValueError("Run queue is full (20 queued runs maximum)")
            # Count independent trial realizations per grid cell, not the three
            # paired variants or separate voting-model output rows.
            total = sum(candidate.experiment.trials for _, candidate, _ in expanded_configs(config))
            record: dict[str, Any] = {
                "id": uuid4().hex,
                "name": name or config.name,
                "description": description,
                "kind": kind,
                "status": "queued",
                "created_at": now(),
                "started_at": None,
                "completed_at": None,
                "elapsed_seconds": 0.0,
                "configuration": config.model_dump(mode="json"),
                "seed": config.experiment.seed,
                "engine_version": engine_version(),
                "error": None,
                "progress": {"completed_trials": None, "total_trials": total, "percentage": None},
            }
            self.repository.save("runs", record["id"], record)
            self._pending.append(record["id"])
            self._wake.set()
            return record

    def get(self, run_id) -> dict:
        with self._lock:
            record = self.repository.get("runs", run_id)
            if record["status"] == "running" and run_id in self._active:
                record["elapsed_seconds"] = max(0.0, time.monotonic() - self._active[run_id][1])
                self._read_progress(record)
            return record

    def _read_progress(self, record):
        path = self.repository.directory("runs", record["id"]) / "progress.json"
        try:
            if path.is_symlink() or path.is_junction() or path.stat().st_size > 16384:
                return
            progress = ProgressResponse.model_validate_json(path.read_text(encoding="utf-8"))
            if (
                progress.phase in {"simulating", "finalizing"}
                and progress.total_trials == record["progress"]["total_trials"]
                and progress.completed_trials is not None
                and 0 <= progress.completed_trials <= progress.total_trials
                and progress.percentage is not None
                and progress.percentage < 100
            ):
                record["progress"] = progress.model_dump()
        except (OSError, ValueError):
            pass  # Missing/partial legacy progress never implies execution failure.

    def list(self) -> list[dict]:
        with self._lock:
            return sorted(
                (self.get(r["id"]) for r in self.repository.list("runs")),
                key=lambda r: (r["created_at"], r["id"]),
                reverse=True,
            )

    @staticmethod
    def _terminate(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        else:
            process.wait()

    def _finish(self, record, status, error=None):
        if record["status"] == "running":
            self._read_progress(record)
        record["status"] = status
        record["error"] = error
        record["completed_at"] = now()
        active = self._active.pop(record["id"], None)
        if active and active[0].stdin:
            active[0].stdin.close()
        log_thread = self._logs.pop(record["id"], None)
        if log_thread:
            log_thread.join(timeout=3)
        if active:
            record["elapsed_seconds"] = max(0.0, time.monotonic() - active[1])
        elif record.get("started_at"):
            record["elapsed_seconds"] = max(
                0.0,
                (datetime.now(UTC) - datetime.fromisoformat(record["started_at"])).total_seconds(),
            )
        if status == "completed":
            total = record["progress"]["total_trials"]
            record["progress"] = {
                "completed_trials": total,
                "total_trials": total,
                "percentage": 100,
                "estimated_remaining_seconds": 0,
                "phase": "completed",
            }
        else:
            record["progress"].update(estimated_remaining_seconds=None, phase=status)
        self.repository.save("runs", record["id"], record)

    def cancel(self, run_id) -> dict:
        with self._lock:
            record = self.repository.get("runs", run_id)
            if record["status"] in TERMINAL:
                return record
            if run_id in self._active:
                self._terminate(self._active[run_id][0])
            self._pending = deque(item for item in self._pending if item != run_id)
            self._finish(record, "cancelled")
            self._wake.set()
            return self.get(run_id)

    def delete(self, run_id):
        with self._lock:
            self.cancel(run_id)
            self.repository.delete("runs", run_id)

    def shutdown(self):
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            for run_id in list(self._active):
                self.cancel(run_id)
            self._wake.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=10)

    def _launch(self, run_id):
        record = self.repository.get("runs", run_id)
        directory = self.repository.directory("runs", run_id)
        # A bounded diagnostic reader drains stdout continuously; a full pipe
        # must never block a running simulation or consume unbounded disk space.
        environment = os.environ.copy()
        source = str(Path(__file__).resolve().parents[2])
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(None, [source, environment.get("PYTHONPATH")])
        )
        # Exclusive creation also rejects a pre-existing symlink log destination.
        log_stream = (directory / "worker.log").open("xb")
        try:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "fan_governance.api.worker",
                    "--root",
                    str(self.repository.root),
                    "--run-id",
                    run_id,
                    "--watch-parent",
                ],
                cwd=Path(__file__).resolve().parents[3],
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        except Exception:
            log_stream.close()
            raise
        self._active[run_id] = (process, time.monotonic())
        record.update(status="running", started_at=now())
        self.repository.save("runs", run_id, record)
        log_thread = threading.Thread(
            target=self._drain_log, args=(process, log_stream), daemon=True
        )
        self._logs[run_id] = log_thread
        log_thread.start()

    @staticmethod
    def _drain_log(process, log_stream):
        limit = 1024 * 1024
        written = 0
        try:
            with log_stream as stream:
                while chunk := process.stdout.read(8192):
                    if written < limit:
                        piece = chunk[: limit - written]
                        stream.write(piece)
                        written += len(piece)
        finally:
            process.stdout.close()

    def _poll(self):
        for run_id, (process, started) in list(self._active.items()):
            record = self.repository.get("runs", run_id)
            code = process.poll()
            if code is None and time.monotonic() - started > self.timeout_seconds:
                self._terminate(process)
                self._finish(record, "failed", "Run timeout exceeded; computation was terminated.")
            elif code is not None:
                directory = self.repository.directory("runs", run_id)
                try:
                    marker = json.loads((directory / "success.json").read_text(encoding="utf-8"))
                    complete = (
                        marker.get("run_id") == run_id and marker.get("status") == "completed"
                    )
                except (OSError, ValueError, AttributeError):
                    complete = False
                if code == 0 and complete:
                    self._finish(record, "completed")
                else:
                    self._finish(
                        record,
                        "failed",
                        "Worker failed to produce complete artifacts. Review the local worker log for details.",
                    )
        while self._pending and len(self._active) < self.max_concurrent:
            run_id = self._pending.popleft()
            try:
                self._launch(run_id)
            except Exception:
                record = self.repository.get("runs", run_id)
                if run_id in self._active:
                    self._terminate(self._active[run_id][0])
                self._finish(record, "failed", "Unable to start the simulation worker.")

    def _schedule(self):
        while True:
            with self._lock:
                if self._stopped:
                    return
                self._poll()
                self._wake.clear()
            self._wake.wait(0.05)
