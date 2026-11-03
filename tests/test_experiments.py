import json
import subprocess
import sys

import pandas as pd
import pytest

from fan_governance.core.config import SimulationConfig, load_config
from fan_governance.core.registry import default_registry
from fan_governance.experiments.runner import ExperimentRunner
from fan_governance.output.exporters import export_results, results_frame


def config():
    return SimulationConfig.model_validate(
        {
            "experiment": {"name": "test", "trials": 3, "seed": 19},
            "population": {"size": 100},
            "governance": {"waiting_period_days": 90},
            "voting": {"strategies": ["equal", "proportional", "capped", "diminishing"]},
        }
    )


def substantive(results):
    return [r.model_dump(exclude={"execution_metadata"}) for r in results]


def test_reproducibility_and_paired_randomness():
    results = ExperimentRunner().run(config())
    assert len(results) == 12
    assert substantive(results) == substantive(ExperimentRunner().run(config()))
    for trial in range(3):
        rows = results[trial * 4 : (trial + 1) * 4]
        assert len({r.votes_cast for r in rows}) == 1
        assert len({r.eligible_voter_count for r in rows}) == 1
        assert len({json.dumps(r.metrics["unweighted_shares"]) for r in rows}) == 1
        assert len({r.execution_metadata["realization_digest"] for r in rows}) == 1
    reversed_config = config()
    reversed_config.voting.strategies.reverse()
    a = {(r.trial_id, r.voting_model): r for r in results}
    b = {(r.trial_id, r.voting_model): r for r in ExperimentRunner().run(reversed_config)}
    assert {k: substantive([v]) for k, v in a.items()} == {
        k: substantive([v]) for k, v in b.items()
    }


def test_experiment_grid():
    c = config()
    c.experiment.trials = 1
    c.experiment.population_sizes = [0, 50]
    c.experiment.waiting_periods = [0, 365]
    c.experiment.participation_levels = [0, 1]
    result = ExperimentRunner().run(c)
    assert len(result) == 32
    assert {r.population_size for r in result} == {0, 50}
    assert all(
        r.votes_cast == r.eligible_voter_count
        for r in result
        if r.configuration["participation"]["parameters"].get("probability") == 1
    )


def test_exports_complete_and_round_trip(tmp_path):
    results = ExperimentRunner().run(config())
    paths = export_results(results, tmp_path, ["csv", "json"])
    rows = json.loads(paths["json"].read_text())
    assert len(rows) == 12
    assert rows[0]["configuration"]["experiment"]["seed"] == 19
    assert rows[0]["component_seeds"]["participation"] > 0
    frame = pd.read_csv(paths["csv"])
    assert len(frame) == 12
    assert "metrics.gini" in frame.columns
    assert "configuration" in frame.columns
    assert results_frame(results)["votes_cast"].tolist() == [r.votes_cast for r in results]


def test_export_undefined_is_json_null(tmp_path):
    c = config()
    c.population.size = 0
    results = ExperimentRunner().run(c)
    path = export_results(results, tmp_path, ["json"])["json"]
    assert "NaN" not in path.read_text()
    assert json.loads(path.read_text())[0]["metrics"]["gini"] is None


def test_unknown_models_fail_before_trials():
    c = config()
    c.voting.strategies = ["unknown"]
    with pytest.raises(ValueError, match="Unknown voting"):
        ExperimentRunner().run(c)
    c.voting.strategies = ["equal"]
    c.participation.parameters = {"typo": 1}
    with pytest.raises(ValueError, match="parameters"):
        ExperimentRunner().run(c)


def test_custom_registered_model():
    class DoubleVoting:
        def calculate_weight(self, supporter, membership, context):
            return 2

    registry = default_registry()
    registry.register("voting", "double", DoubleVoting)
    c = config()
    c.voting.strategies = ["double"]
    result = ExperimentRunner(registry=registry).run(c)[0]
    assert result.metrics["total_weight_cast"] == 2 * result.votes_cast
    assert "double" in registry.names()["voting"]


def test_yaml_configs_and_cli(tmp_path):
    for path in [
        "configs/default.yaml",
        "configs/equal_voting.yaml",
        "configs/stake_voting.yaml",
        "configs/experiments/voting_comparison.yaml",
    ]:
        assert load_config(path).population.size == 10000
    models = subprocess.run(
        [sys.executable, "-m", "fan_governance.cli", "models"], capture_output=True, text=True
    )
    assert models.returncode == 0
    assert all(
        name in models.stdout
        for name in ["equal", "proportional", "capped", "diminishing", "standard", "synthetic"]
    )
    cfg = tmp_path / "small.yaml"
    cfg.write_text(f"population:\n  size: 10\noutput:\n  directory: {tmp_path.as_posix()}/out\n")
    run = subprocess.run(
        [sys.executable, "-m", "fan_governance.cli", "simulate", "--config", str(cfg)],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert "seed=42" in run.stdout
    assert (tmp_path / "out" / "results.json").exists()
    cfg.write_text("population:\n  typo: 1\n")
    invalid = subprocess.run(
        [sys.executable, "-m", "fan_governance.cli", "simulate", "--config", str(cfg)],
        capture_output=True,
        text=True,
    )
    assert invalid.returncode == 2
    assert "typo" in invalid.stderr
