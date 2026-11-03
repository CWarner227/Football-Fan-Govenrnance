"""Analytical quorum denominator and extensible construction checks."""

import pytest

from fan_governance.agents.models import Supporter
from fan_governance.clubs.models import Club
from fan_governance.core.config import GovernanceConfig, ModelSpec
from fan_governance.core.context import RandomStreams
from fan_governance.elections.models import GovernanceProposal
from fan_governance.elections.runner import ElectionRunner, Realization
from fan_governance.membership.eligibility import StandardEligibility
from fan_governance.membership.models import Membership
from fan_governance.metrics.results import StandardMetrics
from fan_governance.participation.probabilistic import ProbabilisticParticipation
from fan_governance.preferences.synthetic import SyntheticPreference
from fan_governance.scenarios.registry import (
    create_attack,
    create_defense,
    default_scenario_registry,
)
from fan_governance.voting.strategies import ProportionalVoting


def election(weights, preferences, *, basis="eligible_weight", threshold=0.5, metrics=None):
    supporters = [Supporter(supporter_id=str(i), wealth=w) for i, w in enumerate(weights)]
    memberships = [
        Membership(member_id=str(i), supporter_id=str(i), contribution=w)
        for i, w in enumerate(weights)
    ]
    club = Club(club_id="c", name="Synthetic", supporters=supporters, memberships=memberships)
    runner = ElectionRunner(
        ProportionalVoting(),
        StandardEligibility(0),
        ProbabilisticParticipation(),
        SyntheticPreference(),
        metrics or StandardMetrics(),
    )
    return runner.run(
        club,
        GovernanceProposal(quorum_basis=basis, quorum=threshold),
        RandomStreams(7),
        realization=Realization(
            {str(i): p != "absent" for i, p in enumerate(preferences)},
            {str(i): p for i, p in enumerate(preferences)},
        ),
    )


def test_weighted_quorum_uses_full_eligible_weight_and_preserves_count_turnout():
    result = election([9, 1, 1, 1], ["approve", "absent", "absent", "absent"], threshold=0.75)
    assert result.turnout == 0.25
    assert result.quorum_achieved
    assert result.metrics["weighted_turnout"] == 0.75
    assert result.metrics["quorum_participation"] == 0.75
    assert result.governance_configuration["quorum_basis"] == "eligible_weight"
    assert not result.metrics["equal_vote_passed"]
    assert result.metrics["outcome_differs_from_equal"]
    count_result = election(
        [9, 1, 1, 1],
        ["approve", "absent", "absent", "absent"],
        basis="eligible_members",
        threshold=0.75,
    )
    assert not count_result.quorum_achieved


def test_invalid_and_abstaining_power_does_not_count_toward_quorum():
    result = election([1, 8, 1], ["approve", "invalid", None], threshold=0.2)
    assert result.metrics["weighted_turnout"] == 0.1
    assert result.turnout == pytest.approx(1 / 3)
    assert not result.quorum_achieved


def test_zero_eligible_weight_cannot_achieve_even_zero_weighted_quorum():
    result = election([0, 0], ["approve", "approve"], threshold=0)
    assert result.turnout == 1
    assert result.metrics["weighted_turnout"] is None
    assert not result.quorum_achieved


def test_optional_metrics_cannot_change_core_weighted_quorum():
    class EmptyMetrics:
        def calculate(self, data):
            assert data.quorum_basis == "eligible_weight"
            return {}

    assert election(
        [9, 1], ["approve", "absent"], threshold=0.8, metrics=EmptyMetrics()
    ).quorum_achieved


def test_governance_quorum_basis_is_validated():
    assert GovernanceConfig(quorum_basis="eligible_weight").quorum_basis == "eligible_weight"
    with pytest.raises(ValueError):
        GovernanceProposal(quorum_basis="arbitrary")


def test_registry_wraps_strict_factories_and_extends_without_engine_edits():
    registry = default_scenario_registry()
    assert len(registry.names()["attack"]) == 7
    assert len(registry.names()["defense"]) == 6
    assert create_attack("sybil", {"attempted_identities": 3}).parameters.attempted_identities == 3
    assert create_defense("waiting_period", {"days": 7}).days == 7
    with pytest.raises(ValueError, match="Invalid parameters"):
        create_attack("sybil", {"unrecognized": 1})
    with pytest.raises(ValueError, match="Unknown attack"):
        create_attack("missing")
    registry.register("attack", "custom", lambda strength: ("synthetic", strength))
    assert create_attack("custom", {"strength": 2}, registry=registry) == ("synthetic", 2)
    assert registry.create("attack", ModelSpec(name="custom", parameters={"strength": 3})) == (
        "synthetic",
        3,
    )
