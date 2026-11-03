import numpy as np
import pytest
from pydantic import ValidationError

from fan_governance.agents.generator import SyntheticPopulationGenerator, sample_distribution
from fan_governance.agents.models import Supporter
from fan_governance.core.config import DistributionConfig, PopulationConfig
from fan_governance.core.context import RandomStreams


def test_supporter_aliases_and_financial_validation():
    supporter = Supporter(fan_id="f", participation_rate=0.2, knowledge_score=0.8)
    assert supporter.supporter_id == supporter.fan_id == "f"
    assert supporter.participation_probability == supporter.participation_rate == 0.2
    assert supporter.knowledge == supporter.knowledge_score == 0.8
    with pytest.raises(ValidationError):
        Supporter(supporter_id="f", wealth=2, contribution=3)
    assert Supporter(supporter_id="f", contribution=3, allow_unfunded_contributions=True)
    with pytest.raises(ValidationError):
        Supporter(supporter_id="a", fan_id="b")


@pytest.mark.parametrize(
    "history",
    [
        {"forecast_sample_count": 1, "forecast_correct_count": 2},
        {"forecast_sample_count": -1},
        {"forecast_accuracy": 1.1},
    ],
)
def test_invalid_forecasting_histories_rejected(history):
    with pytest.raises(ValidationError):
        Supporter(supporter_id="f", **history)


def test_compact_population_finances_policy_and_synthetic_history():
    config = PopulationConfig.model_validate(
        {
            "size": 1000,
            "seed": 32,
            "wealth": {"distribution": "constant", "value": 100},
            "contribution": {"model": "wealth_fraction", "min_fraction": 0.1, "max_fraction": 0.2},
            "knowledge_score": {"distribution": "constant", "value": 0.7},
            "participation_rate": {"distribution": "constant", "value": 0.8},
            "forecast_accuracy": {"distribution": "constant", "value": 0.75},
            "forecast_sample_count": {"distribution": "constant", "value": 200},
            "preferred_policy": {
                "distribution": "categorical",
                "categories": ["yes", "no"],
                "probabilities": [0.8, 0.2],
            },
        }
    )
    generator = SyntheticPopulationGenerator()
    population = generator.generate(config, RandomStreams(32))
    assert population == generator.generate(config, RandomStreams(32))
    assert all(10 <= s.contribution <= 20 and s.wealth == 100 for s in population.supporters)
    assert all(
        s.knowledge_score == 0.7 and s.participation_rate == 0.8 for s in population.supporters
    )
    assert all(
        s.forecast_sample_count == 200 and s.forecast_history_source == "synthetic"
        for s in population.supporters
    )
    assert np.mean(
        [s.forecast_correct_count / 200 for s in population.supporters]
    ) == pytest.approx(0.75, abs=0.01)
    assert np.mean([s.preferred_policy == "yes" for s in population.supporters]) == pytest.approx(
        0.8, abs=0.04
    )


def test_independent_contributions_clipped_unless_explicitly_unfunded():
    config = PopulationConfig(
        size=5,
        wealth_distribution={"type": "constant", "parameters": {"value": 2}},
        contribution_distribution={"type": "constant", "parameters": {"value": 5}},
    )
    generator = SyntheticPopulationGenerator()
    assert all(s.contribution == 2 for s in generator.generate(config, RandomStreams(1)).supporters)
    config = PopulationConfig(**config.model_dump(), financial_mode="allow_unfunded")
    assert all(s.contribution == 5 for s in generator.generate(config, RandomStreams(1)).supporters)


def test_matrix_correlations_include_forecasts_and_aliases():
    config = PopulationConfig(
        size=3000,
        forecast_accuracy_distribution={"type": "uniform"},
        correlations={
            "attributes": ["knowledge_score", "forecast_accuracy"],
            "matrix": [[1, 0.85], [0.85, 1]],
        },
    )
    supporters = SyntheticPopulationGenerator().generate(config, RandomStreams(8)).supporters
    assert (
        np.corrcoef([s.knowledge for s in supporters], [s.forecast_accuracy for s in supporters])[
            0, 1
        ]
        > 0.78
    )
    assert (
        PopulationConfig(correlations={"loyalty:participation_rate": 0.5})
        .correlation_matrix()
        .max()
        == 1
    )


@pytest.mark.parametrize("matrix", [[[1, 0.3], [0.4, 1]], [[0.9, 0], [0, 1]], [[1, 2], [2, 1]]])
def test_invalid_correlation_matrices_rejected(matrix):
    with pytest.raises(ValidationError):
        PopulationConfig(correlations={"attributes": ["wealth", "loyalty"], "matrix": matrix})


def test_constant_distribution_and_categorical_validation():
    assert sample_distribution(
        DistributionConfig(type="constant", parameters={"value": 3}), 3, np.random.default_rng(1)
    ).tolist() == [3, 3, 3]
    with pytest.raises(ValidationError):
        DistributionConfig(type="categorical", categories=["a", "b"], probabilities=[0.1, 0.1])


def test_forecast_count_marginal_is_discretized_like_membership_age():
    config = PopulationConfig(
        size=100,
        forecast_accuracy_distribution={"type": "constant", "parameters": {"value": 1}},
        forecast_sample_count_distribution={
            "type": "uniform",
            "parameters": {"low": 5, "high": 10},
        },
    )
    supporters = SyntheticPopulationGenerator().generate(config, RandomStreams(9)).supporters
    assert {s.forecast_sample_count for s in supporters} == {5, 6, 7, 8, 9}
    assert all(s.forecast_correct_count == s.forecast_sample_count for s in supporters)


def test_missing_forecast_ability_cannot_generate_nonempty_histories():
    config = PopulationConfig(
        size=1, forecast_sample_count_distribution={"type": "constant", "parameters": {"value": 5}}
    )
    with pytest.raises(ValueError, match="requires forecast_accuracy_distribution"):
        SyntheticPopulationGenerator().generate(config, RandomStreams(9))
