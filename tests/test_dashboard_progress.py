"""Measured engine progress, approximate timing, and lifecycle truthfulness."""

import json
import time

import pytest

from fan_governance.api.jobs import JobManager
from fan_governance.scenarios.config import ScenarioConfig
from fan_governance.scenarios.runner import run_scenario
from fan_governance.storage.filesystem import FileRepository


def test_engine_progress_counts_references_grids_models_and_preserves_outputs():
    config = ScenarioConfig.model_validate(
        {
            "simulation": {
                "population": {"size": 8},
                "voting": {"strategies": ["equal", "capped"]},
            },
            "timeline": {"duration_months": 1},
            "elections": {"interval_months": 1},
            "attacks": [{"name": "wealthy_takeover", "operational_budget": 1}],
            "defenses": [{"name": "vote_cap", "parameters": {"cap": 5}}],
            "economics": {"shocks": [{"name": "revenue_loss"}]},
            "experiment": {"trials": 1, "grid": {"experiment.trials": [1, 2]}},
        }
    )
    updates = []
    measured = run_scenario(config, progress_callback=updates.append)
    original = run_scenario(config)
    assert measured.summary == original.summary
    assert measured.elections == original.elections
    assert measured.events == original.events
    assert updates[0]["completed_trajectories"] == 0
    assert updates[-1]["completed_trajectories"] == updates[-1]["total_trajectories"] == 30
    assert updates[-1]["completed_trials"] == updates[-1]["total_trials"] == 3
    assert [x["completed_trajectories"] for x in updates] == sorted(
        x["completed_trajectories"] for x in updates
    )
    assert any(0 < x["completed_trajectories"] < 1 for x in updates)


def test_worker_estimates_wait_for_measurement_throttles_and_reserves_completion(tmp_path):
    from fan_governance.api.worker import ProgressReporter

    elapsed = [0.0]
    reporter = ProgressReporter(tmp_path, 4, clock=lambda: elapsed[0])

    def sample(completed):
        reporter(
            {
                "completed_trajectories": completed,
                "total_trajectories": 12,
                "completed_trials": int(completed // 3),
                "total_trials": 4,
            }
        )
        return json.loads((tmp_path / "progress.json").read_text())

    assert sample(0)["estimated_remaining_seconds"] is None
    elapsed[0] = 10
    progress = sample(3)
    assert progress["percentage"] == pytest.approx(23.75)
    assert progress["estimated_remaining_seconds"] == pytest.approx(30)
    elapsed[0] = 10.01
    assert sample(4) == progress  # bounded file-write rate
    elapsed[0] = 40
    assert sample(12)["percentage"] == 95
    reporter.finalizing(0, 8)
    progress = json.loads((tmp_path / "progress.json").read_text())
    assert progress["phase"] == "finalizing"
    assert progress["estimated_remaining_seconds"] is None
    reporter.finalizing(8, 8)
    assert json.loads((tmp_path / "progress.json").read_text())["percentage"] < 100


def test_running_real_worker_exposes_progress_and_eta(tmp_path):
    manager = JobManager(FileRepository(tmp_path))
    try:
        record = manager.submit(
            {
                "simulation": {"population": {"size": 2000}, "voting": {"strategies": ["equal"]}},
                "timeline": {"duration_months": 12},
                "experiment": {"trials": 10},
            }
        )
        measured = False
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            current = manager.get(record["id"])
            progress = current["progress"]
            if (
                current["status"] == "running"
                and progress.get("estimated_remaining_seconds") is not None
            ):
                assert 0 < progress["percentage"] < 100
                assert progress["estimated_remaining_seconds"] >= 0
                measured = True
                break
            if current["status"] in {"failed", "completed"}:
                break
            time.sleep(0.02)
        assert measured, current
        cancelled = manager.cancel(record["id"])
        assert cancelled["status"] == "cancelled"
        assert cancelled["progress"]["percentage"] < 100
        assert cancelled["progress"].get("estimated_remaining_seconds") is None
    finally:
        manager.shutdown()


def test_progress_read_lock_does_not_abort_scientific_execution(tmp_path, monkeypatch):
    from fan_governance.api import worker

    original = worker.atomic_json
    attempts = []

    def transient_reader_lock(path, value):
        attempts.append(path)
        if len(attempts) == 1:
            raise PermissionError("Windows reader temporarily prevents atomic replacement")
        original(path, value)

    monkeypatch.setattr(worker, "atomic_json", transient_reader_lock)
    reporter = worker.ProgressReporter(tmp_path, 1)
    reporter.publish(force=True)
    reporter.finalizing(0, 8)
    assert json.loads((tmp_path / "progress.json").read_text())["phase"] == "finalizing"
