import json

import pandas as pd

from fan_governance.core.config import SimulationConfig
from fan_governance.experiments.runner import ExperimentRunner
from fan_governance.output.baseline import export_baseline


def config():
    return SimulationConfig.model_validate(
        {
            "experiment": {
                "trials": 2,
                "seed": 9,
                "proposal_categories": ["constitutional", "funding"],
            },
            "population": {
                "size": 100,
                "forecast_accuracy": {"distribution": "beta", "alpha": 5, "beta": 2},
                "forecast_sample_count": {"distribution": "constant", "value": 100},
            },
            "voting": {
                "strategies": [
                    "equal",
                    {"name": "proportional", "parameters": {"reference_contribution": 100}},
                    {
                        "name": "capped",
                        "parameters": {
                            "max_weight": 5,
                            "base_weight": 1,
                            "reference_contribution": 100,
                        },
                    },
                    {
                        "name": "diminishing",
                        "parameters": {
                            "max_weight": 5,
                            "base_weight": 1,
                            "reference_contribution": 100,
                        },
                    },
                    {
                        "name": "hybrid",
                        "parameters": {
                            "default_strategy": "equal",
                            "proposal_rules": {
                                "funding": {
                                    "name": "capped",
                                    "parameters": {
                                        "max_weight": 5,
                                        "base_weight": 1,
                                        "reference_contribution": 100,
                                    },
                                }
                            },
                        },
                    },
                    {
                        "name": "expertise",
                        "parameters": {"minimum_samples": 20, "expertise_multiplier": 2},
                    },
                ]
            },
        }
    )


def test_six_models_match_inputs_and_hybrid_routes():
    results = ExperimentRunner().run(config())
    assert len(results) == 24
    groups = {}
    for result in results:
        groups.setdefault((result.scenario_id, result.trial_id), []).append(result)
    for group in groups.values():
        assert len({r.execution_metadata["input_digest"] for r in group}) == 1
        assert len({r.execution_metadata["realization_digest"] for r in group}) == 1
        lookup = {r.voting_model: r for r in group}
        category = group[0].execution_metadata["proposal_category"]
        target = "capped" if category == "funding" else "equal"
        assert lookup["hybrid"].vote_totals == lookup[target].vote_totals
        for row in group:
            assert row.metrics["outcome_differs_from_equal"] == (
                row.passed != lookup["equal"].passed
            )


def test_reordering_has_identical_scientific_results():
    original = config()
    reverse = config()
    reverse.voting.strategies.reverse()

    def scientific(c):
        return {
            (r.scenario_id, r.trial_id, r.voting_model): r.model_dump(
                exclude={"execution_metadata"}
            )
            for r in ExperimentRunner().run(c)
        }

    assert scientific(original) == scientific(reverse)


def test_proposal_overrides_governance_and_single_strategy():
    config = SimulationConfig.model_validate(
        {
            "population": {"size": 50},
            "governance": {"waiting_period_days": 99999, "quorum": 1},
            "proposal": {
                "category": "funding",
                "quorum": 0,
                "approval_threshold": 0.9,
                "waiting_period_days": 0,
                "eligibility": {"name": "standard", "parameters": {"minimum_contribution": 0}},
                "voting_strategy": "proportional",
                "metadata": {"policy_alignment": "expand"},
            },
        }
    )
    result = ExperimentRunner().run(config)[0]
    assert result.eligible_voter_count == 50
    assert result.voting_model == "proportional"
    assert result.governance_configuration["approval_threshold"] == 0.9
    assert result.governance_configuration["waiting_period_days"] == 0


def test_profiles_and_participation_axes():
    c = SimulationConfig.model_validate(
        {
            "experiment": {
                "population_profiles": {"small": {"size": 10}, "medium": {"size": 20}},
                "participation_models": [
                    {"name": "constant", "parameters": {"probability": 0}},
                    {"name": "constant", "parameters": {"probability": 1}},
                ],
            },
        }
    )
    results = ExperimentRunner().run(c)
    assert len(results) == 4
    assert {r.population_size for r in results} == {10, 20}
    assert all(r.votes_cast == 0 or r.votes_cast == r.eligible_voter_count for r in results)


def test_baseline_artifacts_complete(tmp_path):
    c = config()
    results = ExperimentRunner().run(c)
    paths = export_baseline(results, c, tmp_path, elapsed_seconds=1.0)
    assert all(
        (tmp_path / name).exists()
        for name in [
            "baseline_trials.csv",
            "baseline_summary.csv",
            "baseline_config.yaml",
            "baseline_metadata.json",
        ]
    )
    frame = pd.read_csv(paths["trials"])
    assert len(frame) == 24
    metadata = json.loads(paths["metadata"].read_text())
    assert metadata["result_count"] == 24
    assert metadata["source_sha256"] and metadata["environment"]["python"]
    assert len(pd.read_csv(paths["summary"])) == 12


def test_baseline_cli_small_end_to_end(tmp_path):
    import yaml

    from fan_governance.cli import main

    c = config()
    c.experiment.trials = 1
    path = tmp_path / "baseline.yaml"
    path.write_text(yaml.safe_dump(c.model_dump(mode="json")), encoding="utf-8")
    assert main(["baseline", "--config", str(path), "--output", str(tmp_path / "out")]) == 0
    assert len(pd.read_csv(tmp_path / "out" / "baseline_trials.csv")) == 12


def test_proposal_specific_eligibility_filters_contributions():
    c = SimulationConfig.model_validate(
        {
            "population": {
                "size": 10,
                "wealth": {"distribution": "constant", "value": 10},
                "contribution": {"distribution": "constant", "value": 3},
            },
            "proposal": {
                "waiting_period_days": 0,
                "eligibility": {"name": "standard", "parameters": {"minimum_contribution": 4}},
            },
        }
    )
    assert ExperimentRunner().run(c)[0].eligible_voter_count == 0
