"""Performance changes must preserve full scientific results and paired seeds."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from fan_governance.scenarios import runner
from fan_governance.scenarios.config import ScenarioConfig


def tiny():
    return ScenarioConfig.model_validate(
        {
            "simulation": {
                "population": {"size": 12},
                "voting": {"strategies": ["equal", "proportional"]},
            },
            "timeline": {"duration_months": 1},
            "elections": {"interval_months": 1},
            "experiment": {"trials": 2, "grid": {"honest_turnout": [0.2, 0.7]}},
        }
    )


def scientific(result):
    return {key: getattr(result, key) for key in ("summary", "elections", "timeseries", "events")}


def test_identical_variants_are_reused_without_changing_tables(monkeypatch):
    original = runner._trajectory
    calls = []

    def measured(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(runner, "_trajectory", measured)
    optimized = runner.run_scenario(tiny())
    assert len(calls) == 8  # 2 grids x 2 trials x 2 models; three identical variants reused
    monkeypatch.setattr(runner, "_can_reuse_variants", lambda *args: False)
    reference = runner.run_scenario(tiny())
    assert scientific(optimized) == scientific(reference)


@pytest.mark.parametrize("adversarial", [False, True])
def test_parallel_trials_preserve_order_seeds_and_progress(adversarial):
    config = tiny()
    if adversarial:
        config = ScenarioConfig.model_validate(
            config.model_dump(mode="json")
            | {
                "attacks": [
                    {
                        "name": "sybil",
                        "operational_budget": 4,
                        "parameters": {"attempted_identities": 4},
                    }
                ],
                "defenses": [{"name": "identity_verification", "parameters": {"strength": 0.8}}],
                "economics": {"shocks": [{"name": "revenue_loss", "severity": 0.4}]},
            }
        )
    updates = []
    serial = runner.run_scenario(config)
    parallel = runner.run_scenario(config, workers=2, progress_callback=updates.append)
    assert scientific(serial) == scientific(parallel)
    assert parallel.metadata["execution"]["workers"] == 2
    assert 1 <= len(set(parallel.metadata["execution"]["process_ids"])) <= 2
    assert updates[-1]["completed_trials"] == updates[-1]["total_trials"] == 4
    completed = [u["completed_trajectories"] for u in updates]
    assert completed == sorted(completed)
    assert completed[-1] == updates[-1]["total_trajectories"]
    json.dumps(parallel.summary, allow_nan=False)


def test_parallel_worker_choice_respects_cpu_and_memory_budget():
    from fan_governance.scenarios.parallel import recommended_workers

    assert recommended_workers(10000, cpus=18, memory_bytes=24 * 1024**3) == 8
    assert recommended_workers(10000, cpus=2, memory_bytes=24 * 1024**3) == 1
    assert recommended_workers(100000, cpus=18, memory_bytes=2 * 1024**3) == 1


def test_parallel_children_exit_when_owner_is_force_killed(tmp_path):
    script = tmp_path / "owner.py"
    marker = tmp_path / "children.json"
    script.write_text("""
import json,os,sys
from pathlib import Path
from fan_governance.scenarios.config import ScenarioConfig
from fan_governance.scenarios.runner import run_scenario
def progress(event):
    ids=event.get('worker_process_ids',[])
    if len(ids)>=2:
        Path(sys.argv[1]).write_text(json.dumps(ids))
        os._exit(0)
if __name__=='__main__':
    config=ScenarioConfig.model_validate({'simulation':{'population':{'size':10000}},'experiment':{'trials':20}})
    run_scenario(config,workers=2,progress_callback=progress)
""")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    owner = subprocess.Popen([sys.executable, str(script), str(marker)], env=env)
    try:
        owner.wait(timeout=30)
        assert marker.is_file()
        pids = json.loads(marker.read_text())
        assert len(pids) == 2
        for pid in pids:
            if sys.platform == "win32":
                import ctypes

                handle = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)
                if handle:
                    try:
                        assert ctypes.windll.kernel32.WaitForSingleObject(handle, 10000) == 0
                    finally:
                        ctypes.windll.kernel32.CloseHandle(handle)
            else:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    try:
                        status = Path(f"/proc/{pid}/stat").read_text().split()[2]
                    except FileNotFoundError:
                        break
                    if status == "Z":
                        break
                    time.sleep(0.02)
                else:
                    pytest.fail(f"Parallel worker {pid} survived owner death")
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.wait()


def test_fast_json_export_preserves_nested_numpy_null_and_date_values(tmp_path):
    from datetime import date
    from types import MappingProxyType

    import numpy as np

    from fan_governance.api.worker import atomic_rows
    from fan_governance.scenarios.output import _clean

    raw = {
        "int": np.int64(7),
        "nan": float("nan"),
        "inf": float("inf"),
        "bool": True,
        "negative_zero": -0.0,
        "date": date(2027, 1, 1),
        "path": Path("result"),
        "nested": MappingProxyType({1: (None, "λ", np.float64(0.25))}),
    }
    expected = {
        "int": 7,
        "nan": None,
        "inf": None,
        "bool": True,
        "negative_zero": -0.0,
        "date": "2027-01-01",
        "path": "result",
        "nested": {"1": [None, "λ", 0.25]},
    }
    assert _clean(raw) == expected
    destination = tmp_path / "rows.jsonl"
    atomic_rows(destination, [raw])
    assert (
        destination.read_text()
        == json.dumps(expected, allow_nan=False, separators=(",", ":")) + "\n"
    )
