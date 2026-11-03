import json
import subprocess
import sys

from fan_governance.core.config import SimulationConfig
from fan_governance.experiments.benchmark import measured_run, run_case, workload_config


def test_workload_removes_grid_axes_and_preserves_original():
    config = SimulationConfig.model_validate(
        {
            "experiment": {
                "trials": 20,
                "population_profiles": {"small": {"size": 5}},
                "waiting_periods": [0, 10],
                "participation_levels": [0.2, 0.8],
                "participation_models": [{"name": "constant", "parameters": {"probability": 1}}],
                "proposal_categories": ["constitutional", "funding"],
            },
            "proposal": {"voting_strategy": "proportional"},
            "voting": {
                "strategies": [
                    "equal",
                    {"name": "proportional", "parameters": {"reference_contribution": 5}},
                ]
            },
        }
    )
    before = config.model_dump()
    workload = workload_config(config, size=12, trials=2, strategies=["proportional"])
    assert config.model_dump() == before
    assert workload.population.size == 12
    assert workload.experiment.trials == 2
    assert workload.experiment.proposal_categories == ["funding"]
    assert workload.experiment.population_profiles is None
    assert workload.experiment.waiting_periods is None
    assert workload.experiment.participation_levels is None
    assert workload.experiment.participation_models is None
    assert workload.proposal.voting_strategy is None
    assert workload.voting.specs()[0].parameters == {"reference_contribution": 5}


def test_measured_run_reports_actual_rows_and_process_memory():
    report = run_case(SimulationConfig(), size=10, trials=2, strategies=["equal"])
    assert report["population_size"] == 10
    assert report["trials"] == 2
    assert report["strategies"] == ["equal"]
    assert report["result_rows"] == 2
    assert report["runtime_seconds"] > 0
    assert report["peak_resident_memory_bytes"] > 0
    assert "absolute" in report["memory_scope"]
    assert report["memory_method"] in {"windows.PeakWorkingSetSize", "resource.ru_maxrss"}
    assert report["python"]
    assert report["configuration"]["population"]["size"] == 10


def test_measured_run_counts_six_real_strategies():
    strategies = ["equal", "proportional", "capped", "diminishing", "hybrid", "expertise"]
    config = workload_config(SimulationConfig(), size=6, trials=1, strategies=strategies)
    assert measured_run(config)["result_rows"] == 6


def test_cli_uses_a_fresh_worker_for_each_case(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        json.dumps(
            {
                "voting": {
                    "strategies": [
                        "equal",
                        "proportional",
                        "capped",
                        "diminishing",
                        "hybrid",
                        "expertise",
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "benchmarks.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fan_governance.experiments.benchmark",
            "--config",
            str(config),
            "--output",
            str(output),
            "--size",
            "4",
            "--trials",
            "1",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert len(report["benchmarks"]) == 3
    assert len({row["process_id"] for row in report["benchmarks"]}) == 3
    assert [row["result_rows"] for row in report["benchmarks"]] == [1, 6, 1]
    assert "benchmarks.json" in completed.stdout
