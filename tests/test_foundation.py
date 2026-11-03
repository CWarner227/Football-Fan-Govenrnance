import math

import numpy as np
import pytest
from pydantic import ValidationError

from fan_governance.agents.generator import SyntheticPopulationGenerator
from fan_governance.agents.models import Supporter
from fan_governance.core.config import DistributionConfig, PopulationConfig, SimulationConfig
from fan_governance.core.context import RandomStreams
from fan_governance.membership.eligibility import StandardEligibility
from fan_governance.membership.models import Membership
from fan_governance.metrics.concentration import concentration_metrics
from fan_governance.voting.strategies import (
    CappedVoting,
    DiminishingVoting,
    EqualVoting,
    ProportionalVoting,
)


@pytest.mark.parametrize("contribution", [0, 10, 100])
def test_voting_formulas(contribution):
    s = Supporter(supporter_id="s")
    m = Membership(member_id="m", supporter_id="s", contribution=contribution)
    assert EqualVoting().calculate_weight(s, m, None) == 1
    assert ProportionalVoting().calculate_weight(s, m, None) == contribution
    assert CappedVoting(cap=25).calculate_weight(s, m, None) == min(contribution, 25)
    assert DiminishingVoting(scale=10, multiplier=2).calculate_weight(s, m, None) == pytest.approx(
        2 * math.log1p(contribution / 10)
    )


def test_eligibility_waiting_and_duplicate_identity():
    population = [Supporter(supporter_id="s")]
    memberships = [
        Membership(member_id="z", supporter_id="s", age_days=180),
        Membership(member_id="a", supporter_id="s", age_days=180),
        Membership(member_id="b", supporter_id="s", age_days=90),
    ]
    assert [m.member_id for m in StandardEligibility(180).eligible(population, memberships)] == [
        "a"
    ]
    assert StandardEligibility(181).eligible(population, memberships) == []
    for field in ["active", "verified"]:
        m = memberships[0].model_copy(update={field: False})
        assert StandardEligibility(0).eligible(population, [m]) == []


def test_concentration_hand_calculated():
    result = concentration_metrics([0, 1, 3, 0])
    assert result["gini"] == pytest.approx(0.625)
    assert result["effective_voters"] == pytest.approx(1.6)
    assert result["max_power_share"] == 0.75
    assert result["top_1_share"] == 0.75
    equal = concentration_metrics([1] * 100)
    assert equal["gini"] == 0
    assert equal["effective_voters"] == pytest.approx(100)
    assert equal["top_5_share"] == pytest.approx(0.05)


@pytest.mark.parametrize("weights", [[], [0, 0]])
def test_undefined_concentration_is_explicit(weights):
    assert all(value is None for value in concentration_metrics(weights).values())


@pytest.mark.parametrize("weights", [[-1], [float("inf")], [float("nan")]])
def test_invalid_weights_are_rejected(weights):
    with pytest.raises(ValueError):
        concentration_metrics(weights)


def test_population_reproducible_and_bounded():
    config = PopulationConfig(size=10000, adversarial_fraction=0.2)
    generator = SyntheticPopulationGenerator()
    a = generator.generate(config, RandomStreams(42))
    b = generator.generate(config, RandomStreams(42))
    assert a == b
    assert len(a.supporters) == len(a.memberships) == 10000
    assert len({s.supporter_id for s in a.supporters}) == 10000
    assert all(0 <= s.loyalty <= 1 and s.wealth >= 0 for s in a.supporters)
    assert 1800 < sum(s.is_adversarial for s in a.supporters) < 2200


@pytest.mark.parametrize(
    "kind,parameters",
    [
        ("uniform", {"low": 0, "high": 1}),
        ("normal", {"mean": 0.5, "std": 0.2}),
        ("lognormal", {"mean": 0, "sigma": 1}),
        ("beta", {"alpha": 2, "beta": 3}),
    ],
)
def test_all_distribution_families(kind, parameters):
    config = PopulationConfig(
        size=100,
        loyalty_distribution=DistributionConfig(type=kind, parameters=parameters, lower=0, upper=1),
    )
    population = SyntheticPopulationGenerator().generate(config, RandomStreams(9))
    assert all(0 <= s.loyalty <= 1 for s in population.supporters)


def test_explicit_correlation_and_component_independence():
    base = PopulationConfig(size=2000)
    changed = base.model_copy(
        update={
            "wealth_distribution": DistributionConfig(
                type="uniform", parameters={"low": 0, "high": 1}
            )
        }
    )
    g = SyntheticPopulationGenerator()
    a, b = g.generate(base, RandomStreams(3)), g.generate(changed, RandomStreams(3))
    assert [s.loyalty for s in a.supporters] == [s.loyalty for s in b.supporters]
    correlated = PopulationConfig(size=2000, correlations={"wealth:contribution": 0.95})
    c = g.generate(correlated, RandomStreams(3))
    ranks = (
        np.array([[s.wealth for s in c.supporters], [s.contribution for s in c.supporters]])
        .argsort(axis=1)
        .argsort(axis=1)
    )
    assert np.corrcoef(ranks)[0, 1] > 0.9


@pytest.mark.parametrize(
    "data",
    [
        {"population": {"size": -1}},
        {"population": {"typo": 3}},
        {"governance": {"waiting_period_days": -1}},
        {"population": {"wealth_distribution": {"type": "normal", "parameters": {"std": -1}}}},
        {"population": {"wealth_distribution": {"type": "uniform", "parameters": {"typo": 2}}}},
    ],
)
def test_malformed_config_rejected(data):
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


def test_domain_rejects_nonfinite_or_negative_values():
    for amount in [-1, float("inf"), float("nan")]:
        with pytest.raises(ValidationError):
            Membership(member_id="m", supporter_id="s", contribution=amount)


def test_named_streams_do_not_depend_on_call_order():
    streams = RandomStreams(42, trial=3)
    before = streams.generator("preferences").random(5)
    streams.generator("population").random(999)
    assert np.array_equal(before, streams.generator("preferences").random(5))
    assert not np.array_equal(before, RandomStreams(42, trial=4).generator("preferences").random(5))
