import math
from types import SimpleNamespace

import pytest

from fan_governance.agents.models import Supporter
from fan_governance.core.context import VotingContext
from fan_governance.membership.models import Membership
from fan_governance.voting.expertise import ExpertiseVoting
from fan_governance.voting.hybrid import HybridVoting
from fan_governance.voting.strategies import (
    CappedVoting,
    DiminishingVoting,
    EqualVoting,
    ProportionalVoting,
)


def weight(strategy, contribution=0, supporter=None, context=None):
    return strategy.calculate_weight(
        supporter or Supporter(supporter_id="s"),
        Membership(member_id="m", supporter_id="s", contribution=contribution),
        context,
    )


@pytest.mark.parametrize("contribution", [0, 1, 10, 100, 1e308])
def test_legacy_formulas_preserved(contribution):
    assert weight(ProportionalVoting(), contribution) == contribution
    assert weight(CappedVoting(), contribution) == min(contribution, 100)
    assert weight(CappedVoting(cap=25), contribution) == min(contribution, 25)
    expected = 2 * (math.log(contribution + 10) - math.log(10)) if contribution else 0
    assert weight(DiminishingVoting(scale=10, multiplier=2), contribution) == pytest.approx(
        expected
    )


def test_phase2_formulas_and_membership_contribution():
    supporter = Supporter(supporter_id="s", wealth=1000, contribution=999)
    assert weight(ProportionalVoting(reference_contribution=10), 30, supporter) == 3
    capped = CappedVoting(max_weight=5, base_weight=1, reference_contribution=10)
    diminishing = DiminishingVoting(max_weight=5, base_weight=1, reference_contribution=10)
    for contribution, expected in [(0, 1), (10, 2), (30, 3), (150, 5), (1e308, 5)]:
        assert weight(diminishing, contribution) == pytest.approx(expected)
    assert weight(capped, 0) == 1
    assert weight(capped, 30) == 4
    assert weight(capped, 1e308) == 5


def test_overflow_and_phase2_partial_configuration():
    assert weight(DiminishingVoting(scale=0.1), 1e308) == pytest.approx(711.4987937351601)
    assert weight(DiminishingVoting(max_weight=4), 7) == 4
    assert weight(CappedVoting(max_weight=4, reference_contribution=1e-308), 1e308) == 4
    assert weight(DiminishingVoting(reference_contribution=1e-308), 1e308) == 5
    with pytest.raises(ValueError, match="finite"):
        weight(ProportionalVoting(reference_contribution=1e-308), 1e308)


@pytest.mark.parametrize(
    "factory,parameters",
    [
        (ProportionalVoting, {"reference_contribution": 0}),
        (ProportionalVoting, {"reference_contribution": float("nan")}),
        (CappedVoting, {"max_weight": 2, "base_weight": 3}),
        (CappedVoting, {"base_weight": -1}),
        (CappedVoting, {"reference_contribution": 0}),
        (CappedVoting, {"max_weight": float("inf")}),
        (DiminishingVoting, {"reference_contribution": 0}),
        (DiminishingVoting, {"max_weight": 2, "base_weight": 3}),
        (DiminishingVoting, {"base_weight": float("nan")}),
        (DiminishingVoting, {"multiplier": float("inf")}),
        (ExpertiseVoting, {"expertise_multiplier": -1}),
        (ExpertiseVoting, {"minimum_samples": 1.5}),
        (ExpertiseVoting, {"confidence_z": 0}),
        (ExpertiseVoting, {"confidence_z": float("inf")}),
        (ExpertiseVoting, {"chance_accuracy": 1}),
        (ExpertiseVoting, {"max_weight": 0.5}),
    ],
)
def test_invalid_parameters(factory, parameters):
    with pytest.raises(ValueError):
        factory(**parameters)


def test_hybrid_routes_and_freezes_rules():
    rules = {"funding": CappedVoting(max_weight=5, base_weight=1)}
    hybrid = HybridVoting(EqualVoting(), rules)
    rules.clear()
    assert weight(hybrid, 100, context=SimpleNamespace(proposal_category="funding")) == 5
    assert weight(hybrid, 100, context=SimpleNamespace(proposal_category="constitutional")) == 1
    assert weight(hybrid, 100, context=VotingContext("p", 0, 1)) == 1


def test_expertise_requires_observed_history_and_ignores_latent_traits():
    strategy = ExpertiseVoting(expertise_multiplier=3, minimum_samples=20)
    for n, k in [(0, None), (19, 19), (100, None), (100, 50), (100, 0)]:
        supporter = SimpleNamespace(
            forecast_sample_count=n, forecast_correct_count=k, forecast_accuracy=1, knowledge=1
        )
        assert weight(strategy, supporter=supporter) == 1
    assert weight(strategy) == 1


def test_expertise_wilson_analytical_and_cap():
    supporter = SimpleNamespace(forecast_sample_count=100, forecast_correct_count=100)
    strategy = ExpertiseVoting(expertise_multiplier=2, minimum_samples=20)
    # For all correct observations, Wilson's lower bound is n/(n+z**2).
    reliability = (100 / (100 + 1.96**2) - 0.5) / 0.5
    assert weight(strategy, supporter=supporter) == pytest.approx(1 + 2 * reliability)
    assert (
        weight(ExpertiseVoting(expertise_multiplier=2, max_weight=1.5), supporter=supporter) == 1.5
    )
    small = SimpleNamespace(forecast_sample_count=20, forecast_correct_count=20)
    assert weight(strategy, supporter=small) < weight(strategy, supporter=supporter)


@pytest.mark.parametrize("n,k", [(-1, 0), (10, 11), (10, -1), (10.5, 5), (10, 5.5)])
def test_invalid_forecast_evidence_rejected(n, k):
    with pytest.raises(ValueError):
        weight(
            ExpertiseVoting(),
            supporter=SimpleNamespace(forecast_sample_count=n, forecast_correct_count=k),
        )


def test_extreme_expertise_parameters_stay_finite():
    supporter = SimpleNamespace(forecast_sample_count=100, forecast_correct_count=100)
    assert weight(ExpertiseVoting(confidence_z=1e308), supporter=supporter) == 1
    assert math.isfinite(weight(ExpertiseVoting(expertise_multiplier=1e308), supporter=supporter))


def test_hybrid_rejects_nonfinite_delegated_weights():
    class Invalid:
        def calculate_weight(self, supporter, membership, context):
            return float("nan")

    with pytest.raises(ValueError):
        weight(HybridVoting(Invalid(), {}), context=SimpleNamespace(proposal_category="funding"))
