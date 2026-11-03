"""Export statistics, synthetic figures and Phase 3 CLI compatibility."""

import argparse
import json

import numpy as np
import pandas as pd
import pytest
import yaml

from fan_governance.cli import _scenario_configs, main
from fan_governance.scenarios.config import ScenarioConfig
from fan_governance.scenarios.output import (
    aggregate_trials,
    export_scenario,
    paired_defense_effectiveness,
    plot_scenario,
)


def trial_rows():
    return [
        dict(
            scenario="s",
            grid_id="0",
            trial=i,
            voting_model="equal",
            variant="defended",
            capture_success=i == 0,
            cash_balance=10 * i,
        )
        for i in range(4)
    ]


def test_wilson_interval_and_quantiles_are_grouped_by_model_variant_grid():
    rows = trial_rows()
    rows += [rows[0] | {"voting_model": "stake", "capture_success": True}]
    aggregate = aggregate_trials(rows)
    capture = next(
        row
        for row in aggregate
        if row["voting_model"] == "equal" and row["metric"] == "capture_success"
    )
    assert capture["mean"] == 0.25
    assert capture["n"] == 4
    assert capture["wilson_lower"] == pytest.approx(0.0455872608)
    assert capture["wilson_upper"] == pytest.approx(0.6993581574)
    cash = next(
        row
        for row in aggregate
        if row["voting_model"] == "equal" and row["metric"] == "cash_balance"
    )
    assert cash["q50"] == 15
    assert cash["q025"] == pytest.approx(0.75)
    assert cash["q975"] == pytest.approx(29.25)
    assert cash["uncertainty_kind"] == "trial_quantiles"
    assert cash["wilson_lower"] is None


def test_aggregate_rejects_pseudoreplication_and_nonbinary_capture():
    with pytest.raises(ValueError, match="one row per trial"):
        aggregate_trials([trial_rows()[0], trial_rows()[0]])
    with pytest.raises(ValueError, match="Binary metric"):
        aggregate_trials([trial_rows()[0] | {"capture_success": 0.5}])


def test_relative_reduction_preserves_pairs_and_zero_baseline_is_undefined():
    rows = trial_rows()
    rows += [
        row | {"variant": "unprotected", "capture_success": row["trial"] < 2}
        for row in trial_rows()
    ]
    result = paired_defense_effectiveness(rows)[0]
    assert result["paired_trials"] == 4
    assert result["absolute_capture_reduction"] == 0.25
    assert result["relative_capture_reduction"] == 0.5
    assert result["capture_prevented_rate"] == 0.25
    zero = [row | {"capture_success": False} for row in rows]
    assert paired_defense_effectiveness(zero)[0]["relative_capture_reduction"] is None


def test_json_csv_manifest_preserve_nested_events_and_missing_runway(tmp_path):
    config = ScenarioConfig(output={"directory": tmp_path})
    row = trial_rows()[0] | {"financial_runway_months": np.nan}
    event = {"kind": "review", "details": {"reasons": ["signal"], "cost": np.float64(2)}}
    destination = export_scenario(config, [row], [], [], [event], {"seed": 7})
    assert destination == tmp_path
    assert json.loads((tmp_path / "summary.json").read_text())[0]["financial_runway_months"] is None
    assert json.loads((tmp_path / "events.json").read_text())[0]["details"]["cost"] == 2
    assert len(pd.read_csv(tmp_path / "elections.csv")) == 0
    assert json.loads((tmp_path / "manifest.json").read_text())["row_counts"]["events"] == 1
    assert (tmp_path / "configuration.yaml").exists()
    assert (tmp_path / "aggregate.csv").exists()


def test_suite_relative_paths_confined_and_output_overrides_unique(tmp_path):
    root = tmp_path / "configs"
    (root / "experiments").mkdir(parents=True)
    (root / "scenarios").mkdir()
    (root / "scenarios" / "a.yaml").write_text(yaml.safe_dump({"name": "a"}))
    suite = root / "experiments" / "suite.yaml"
    suite.write_text(yaml.safe_dump({"experiments": ["../scenarios/a.yaml"]}))
    args = argparse.Namespace(
        config=str(suite), command="scenario-suite", output=str(tmp_path / "out")
    )
    configs = _scenario_configs(args)
    assert configs[0].name == "a"
    assert configs[0].output.directory == tmp_path / "out" / "a"
    suite.write_text(yaml.safe_dump({"experiments": ["../../outside.yaml"]}))
    with pytest.raises(ValueError, match="relative YAML paths"):
        _scenario_configs(args)


def test_eight_optional_figures_are_written_even_when_a_scenario_lacks_axes(tmp_path):
    pytest.importorskip("matplotlib")
    rows = trial_rows() + [
        trial_rows()[0] | {"variant": "control", "capture_success": False},
        trial_rows()[0] | {"variant": "unprotected", "capture_success": True},
    ]
    paths = plot_scenario(rows, [], [], tmp_path)
    assert len(paths) == 8
    assert all(path.stat().st_size > 1000 for path in paths.values())


def test_scenario_cli_executes_and_exports_with_original_models_command_intact(tmp_path, capsys):
    path = tmp_path / "scenario.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "name": "tiny",
                "timeline": {"duration_months": 1},
                "elections": {"interval_months": 1},
                "simulation": {"population": {"size": 4}, "governance": {"waiting_period_days": 0}},
                "experiment": {"trials": 1},
                "output": {"directory": str(tmp_path / "out")},
            }
        )
    )
    assert main(["scenario", "--config", str(path)]) == 0
    assert (tmp_path / "out" / "summary.json").exists()
    assert "Synthetic scenario: tiny" in capsys.readouterr().out
    assert main(["models"]) == 0


def test_scenario_cli_reports_invalid_suite_as_configuration_error(tmp_path, capsys):
    path = tmp_path / "bad.yaml"
    path.write_text("experiments: []")
    assert main(["scenario-suite", "--config", str(path)]) == 2
    assert "nonempty list" in capsys.readouterr().err
