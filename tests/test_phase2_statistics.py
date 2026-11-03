import math

import numpy as np
import pytest

from fan_governance.agents.generator import SyntheticPopulationGenerator, sample_distribution
from fan_governance.core.config import DistributionConfig, PopulationConfig
from fan_governance.core.context import RandomStreams


@pytest.mark.parametrize(
    "kind,parameters,mean,variance,tolerance",
    [
        ("uniform", {"low": 0, "high": 1}, 0.5, 1 / 12, 0.01),
        ("normal", {"mean": 2, "std": 0.3}, 2, 0.09, 0.01),
        ("beta", {"alpha": 2, "beta": 3}, 0.4, 0.04, 0.01),
        (
            "lognormal",
            {"mean": 0, "sigma": 0.4},
            math.exp(0.08),
            math.exp(0.16) * (math.exp(0.16) - 1),
            0.02,
        ),
        ("constant", {"value": 3}, 3, 0, 0),
    ],
)
def test_distribution_moments_under_fixed_seed(kind, parameters, mean, variance, tolerance):
    values = sample_distribution(
        DistributionConfig(type=kind, parameters=parameters), 20000, np.random.default_rng(827)
    )
    assert values.mean() == pytest.approx(mean, abs=tolerance)
    assert values.var() == pytest.approx(variance, abs=tolerance)


def test_copula_rank_correlation_matches_gaussian_prediction():
    rho = 0.8
    config = PopulationConfig(size=5000, correlations={"knowledge_score:participation_rate": rho})
    supporters = SyntheticPopulationGenerator().generate(config, RandomStreams(27)).supporters
    ranks = (
        np.array(
            [[s.knowledge for s in supporters], [s.participation_probability for s in supporters]]
        )
        .argsort(axis=1)
        .argsort(axis=1)
    )
    observed = np.corrcoef(ranks)[0, 1]
    expected = 6 / math.pi * math.asin(rho / 2)
    assert observed == pytest.approx(expected, abs=0.03)
