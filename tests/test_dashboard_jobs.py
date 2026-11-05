"""Process lifecycle tests use real subprocesses, including a tiny real engine run."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from fan_governance.api.jobs import JobManager
from fan_governance.scenarios.config import ScenarioConfig
from fan_governance.storage.filesystem import FileRepository


def small_configuration():
    config = ScenarioConfig().model_dump(mode="json")
    config["simulation"]["population"]["size"] = 8
    config["timeline"]["duration_months"] = 1
    config["elections"]["interval_months"] = 1
    config["experiment"]["trials"] = 1
    return config


def wait_for(manager, run_id, statuses, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = manager.get(run_id)
        if record["status"] in statuses:
            return record
        time.sleep(0.02)
    pytest.fail(f"run did not reach {statuses}: {manager.get(run_id)}")


def test_small_real_engine_job_persists_completed_artifacts(tmp_path):
    repository = FileRepository(tmp_path)
    manager = JobManager(repository)
    try:
        run = manager.submit(small_configuration(), name="Tiny real run")
        completed = wait_for(manager, run["id"], {"completed", "failed"})
        assert completed["status"] == "completed", completed
        assert completed["progress"] == {
            "completed_trials": 1,
            "total_trials": 1,
            "percentage": 100,
        }
        artifacts = repository.directory("runs", run["id"]) / "artifacts"
        rows = [json.loads(line) for line in (artifacts / "summary.jsonl").read_text().splitlines()]
        assert len(rows) == 3
        assert {row["variant"] for row in rows} == {"control", "unprotected", "defended"}
        assert json.loads((artifacts / "manifest.json").read_text())["row_counts"]["summary"] == 3
        assert repository.get("runs", run["id"])["status"] == "completed"
    finally:
        manager.shutdown()


def test_queue_bound_cancel_and_restart_recovery(tmp_path):
    repository = FileRepository(tmp_path)
    manager = JobManager(repository, autostart=False)
    jobs = [manager.submit(small_configuration()) for _ in range(20)]
    with pytest.raises(ValueError, match="queue"):
        manager.submit(small_configuration())
    cancelled = manager.cancel(jobs[0]["id"])
    assert cancelled["status"] == "cancelled"
    interrupted = jobs[1] | {"status": "running"}
    repository.save("runs", interrupted["id"], interrupted)
    manager.shutdown()
    recovered = JobManager(repository, autostart=False)
    try:
        assert recovered.get(interrupted["id"])["status"] == "failed"
        assert "restart" in recovered.get(interrupted["id"])["error"]
        assert recovered.get(jobs[2]["id"])["status"] == "queued"
        recovered.delete(jobs[0]["id"])
        with pytest.raises(KeyError):
            recovered.get(jobs[0]["id"])
    finally:
        recovered.shutdown()


@pytest.mark.parametrize("action", ["cancel", "timeout", "shutdown"])
def test_real_process_termination_and_controlled_concurrency(tmp_path, monkeypatch, action):
    repository = FileRepository(tmp_path)
    original_popen = subprocess.Popen
    spawned = []

    def slow_worker(*args, **kwargs):
        process = original_popen([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
        spawned.append(process)
        return process

    monkeypatch.setattr("fan_governance.api.jobs.subprocess.Popen", slow_worker)
    manager = JobManager(repository, timeout_seconds=0.25 if action == "timeout" else 30)
    try:
        first = manager.submit(small_configuration())
        wait_for(manager, first["id"], {"running"})
        second = manager.submit(small_configuration())
        assert manager.get(second["id"])["status"] == "queued"
        manager.cancel(second["id"])
        if action == "cancel":
            assert manager.cancel(first["id"])["status"] == "cancelled"
        elif action == "timeout":
            assert "timeout" in wait_for(manager, first["id"], {"failed"})["error"]
        else:
            manager.shutdown()
            assert manager.get(first["id"])["status"] == "cancelled"
        assert spawned[0].poll() is not None
        assert len(spawned) == 1
        assert manager.get(second["id"])["status"] == "cancelled"
    finally:
        manager.shutdown()


def test_failed_worker_cannot_report_completion_without_marker(tmp_path, monkeypatch):
    repository = FileRepository(tmp_path)
    original_popen = subprocess.Popen
    monkeypatch.setattr(
        "fan_governance.api.jobs.subprocess.Popen",
        lambda *args, **kwargs: original_popen([sys.executable, "-c", "pass"], **kwargs),
    )
    manager = JobManager(repository)
    try:
        run = manager.submit(small_configuration())
        failed = wait_for(manager, run["id"], {"failed"})
        assert "artifacts" in failed["error"]
        assert failed["progress"]["percentage"] is None
    finally:
        manager.shutdown()


def test_deleting_running_job_waits_for_process_and_log_file_release(tmp_path, monkeypatch):
    repository = FileRepository(tmp_path)
    original_popen = subprocess.Popen
    spawned = []

    def slow_worker(*args, **kwargs):
        process = original_popen(
            [sys.executable, "-u", "-c", "import time; print('started'); time.sleep(60)"],
            **kwargs,
        )
        spawned.append(process)
        return process

    monkeypatch.setattr("fan_governance.api.jobs.subprocess.Popen", slow_worker)
    manager = JobManager(repository)
    try:
        run = manager.submit(small_configuration())
        wait_for(manager, run["id"], {"running"})
        manager.delete(run["id"])
        assert spawned[0].poll() is not None
        assert not (tmp_path / "runs" / run["id"]).exists()
    finally:
        manager.shutdown()


def test_failed_worker_diagnostics_are_bounded_and_do_not_reach_public_record(
    tmp_path, monkeypatch
):
    repository = FileRepository(tmp_path)
    original_popen = subprocess.Popen
    monkeypatch.setattr(
        "fan_governance.api.jobs.subprocess.Popen",
        lambda *args, **kwargs: original_popen(
            [
                sys.executable,
                "-c",
                "import sys; print('private-path/' + 'x' * 2000000); sys.exit(2)",
            ],
            **kwargs,
        ),
    )
    manager = JobManager(repository)
    try:
        run = manager.submit(small_configuration())
        failed = wait_for(manager, run["id"], {"failed"})
        assert "private-path" not in failed["error"]
        log = repository.directory("runs", run["id"]) / "worker.log"
        assert log.stat().st_size <= 1024 * 1024
    finally:
        manager.shutdown()


def test_progress_counts_independent_trials_in_heterogeneous_grid(tmp_path):
    manager = JobManager(FileRepository(tmp_path), autostart=False)
    try:
        config = small_configuration()
        config["experiment"]["grid"] = {"experiment.trials": [1, 2]}
        run = manager.submit(config)
        assert run["progress"] == {
            "completed_trials": None,
            "total_trials": 3,
            "percentage": None,
        }
    finally:
        manager.shutdown()


def test_worker_terminates_when_api_parent_dies_abruptly(tmp_path):
    """A deliberately crashing API subprocess must not leave its engine running."""
    manager = JobManager(FileRepository(tmp_path), autostart=False)
    config = small_configuration()
    config["simulation"]["population"]["size"] = 100000
    config["experiment"]["trials"] = 10
    run = manager.submit(config)
    manager.shutdown()
    parent_code = """
import os, subprocess, sys, time
from pathlib import Path
p = subprocess.Popen(
    [sys.executable, '-m', 'fan_governance.api.worker', '--root', sys.argv[1],
     '--run-id', sys.argv[2], '--watch-parent'],
    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
print(p.pid, flush=True)
progress = Path(sys.argv[1]) / 'runs' / sys.argv[2] / 'progress.json'
deadline = time.monotonic() + 15
while not progress.exists() and time.monotonic() < deadline and p.poll() is None:
    time.sleep(0.02)
os._exit(0)
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    parent = subprocess.Popen(
        [sys.executable, "-c", parent_code, str(tmp_path), run["id"]],
        stdout=subprocess.PIPE,
        text=True,
        env=environment,
    )
    child_pid = int(parent.stdout.readline().strip())
    parent.wait(timeout=20)
    parent.stdout.close()
    assert (tmp_path / "runs" / run["id"] / "progress.json").exists(), (
        "Worker never began execution"
    )
    if sys.platform == "win32":
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x00100000, False, child_pid)
        if handle:
            try:
                assert ctypes.windll.kernel32.WaitForSingleObject(handle, 10000) == 0
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
    else:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.02)
        else:
            pytest.fail("Worker survived abrupt API parent termination")
    assert not (tmp_path / "runs" / run["id"] / "success.json").exists()
