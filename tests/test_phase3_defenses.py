"""Analytical tests for synthetic defensive proposals and procedural safeguards."""

from copy import deepcopy

import numpy as np
import pytest

from fan_governance.adversarial.base import SimulationContext
from fan_governance.agents.models import Supporter
from fan_governance.defenses.policies import (
    DEFENSE_FACTORIES,
    IdentityVerification,
    ParticipationIncentive,
    Quorum,
    SuspiciousActivity,
    VoteCap,
    WaitingPeriod,
)
from fan_governance.membership.models import Membership
from fan_governance.scenarios.state import (
    Account,
    IdentityClaim,
    SimulationState,
    VoteOverride,
    VotingCredential,
)


def context():
    people = {
        "honest": Supporter(supporter_id="honest", wealth=100),
        "hostile": Supporter(supporter_id="hostile", wealth=100, is_adversarial=True),
    }
    accounts = {}
    for key, person, fraud in [
        ("honest", "honest", False),
        ("hostile", "hostile", False),
        ("sybil1", "hostile", True),
        ("sybil2", "hostile", True),
        ("duplicate", "honest", False),
    ]:
        accounts[key] = Account(
            key,
            IdentityClaim("claim-" + key, person, fraudulent=fraud),
            Membership(member_id=key, supporter_id=person),
            VotingCredential("credential-" + key),
        )
    return SimulationContext(
        SimulationState(people, accounts, {}, day=100), np.random.default_rng(15)
    )


def test_strong_identity_rejects_fraud_but_accepts_hostile_people_and_deduplicates():
    effect = IdentityVerification(strength=1, verification_cost=2).apply(context())
    by_id = {a.target_id: a for a in effect.actions}
    assert by_id["hostile"].data["accepted"]
    assert by_id["honest"].data["resolved_id"] == by_id["duplicate"].data["resolved_id"] == "honest"
    assert all(not by_id[key].data["accepted"] for key in ("sybil1", "sybil2"))
    assert sum(a.administrative_cost for a in effect.actions) == 10


def test_weak_identity_can_false_accept_independent_aliases():
    effect = IdentityVerification(strength=0).apply(context())
    assert all(a.data["accepted"] for a in effect.actions)
    assert len({a.data["resolved_id"] for a in effect.actions}) == 5
    effect = IdentityVerification(strength=0, false_acceptance_probability=0).apply(context())
    assert not any(a.data["accepted"] for a in effect.actions if a.data["fraudulent"])


def test_identity_rejection_and_completed_verification():
    ctx = context()
    ctx.state.accounts["sybil1"].claim.verification_done = True
    effect = IdentityVerification(legitimate_rejection_probability=1).apply(ctx)
    assert len(effect.actions) == 4
    assert not any(a.data["accepted"] for a in effect.actions)


@pytest.mark.parametrize(
    "policy",
    [
        IdentityVerification(),
        WaitingPeriod(180),
        VoteCap(5),
        Quorum(0.4),
        ParticipationIncentive(0.2),
        SuspiciousActivity(),
    ],
)
def test_policies_do_not_mutate_simulation_state(policy):
    ctx = context()
    before = deepcopy(ctx.state)
    policy.apply(ctx)
    assert ctx.state == before


def test_governance_effects_expose_composable_bounds():
    ctx = context()
    assert WaitingPeriod(180).apply(ctx).waiting_period_days == 180
    assert VoteCap(0).apply(ctx).vote_cap == 0
    effect = Quorum(0.6, "eligible_weight").apply(ctx)
    assert (effect.quorum, effect.quorum_basis) == (0.6, "eligible_weight")


def test_participation_success_is_uncertain_and_campaign_cost_is_explicit():
    ctx = context()
    failed = ParticipationIncentive(0.3, 0, 2).apply(ctx)
    assert failed.turnout_boost == 0
    assert failed.actions[0].administrative_cost == 6
    assert ParticipationIncentive(0.3, 1).apply(ctx).turnout_boost == 0.3


def test_monitor_only_logs_all_accounts_without_restriction():
    effect = SuspiciousActivity(threshold=0.1, review_cost=3).apply(context())
    assert len(effect.actions) == 5
    assert all(a.data["flagged"] for a in effect.actions)
    assert all(a.data["restricted_until"] is None for a in effect.actions)
    assert sum(a.administrative_cost for a in effect.actions) == 15


def test_background_false_alert_without_confirmation_does_not_restrict():
    effect = SuspiciousActivity(
        strength=0,
        background_false_positive_probability=1,
        review_policy="temporary_restriction",
        confirmation_probability=0,
        false_confirmation_probability=0,
    ).apply(context())
    assert all(a.data["flagged"] and not a.data["confirmed"] for a in effect.actions)
    assert all(a.data["restricted_until"] is None for a in effect.actions)


def test_appeals_restore_false_confirmed_legitimate_accounts_and_restrictions_are_finite():
    effect = SuspiciousActivity(
        background_false_positive_probability=1,
        review_policy="temporary_restriction",
        confirmation_probability=1,
        false_confirmation_probability=1,
        appeal_probability=1,
        restriction_days=7,
    ).apply(context())
    for action in effect.actions:
        assert action.data["confirmed"]
        if action.data["malicious"]:
            assert action.data["restricted_until"] == 107
        else:
            assert action.data["appeal_success"]
            assert action.data["restricted_until"] is None


def test_risk_uses_observable_signals_not_hostility():
    ctx = context()
    ctx.state.accounts["honest"].credential.replacement_count = 2
    ctx.state.accounts["honest"].membership.contribution = 5
    ctx.state.overrides["honest"] = VoteOverride("actor", "yes", 100, "synthetic")
    ctx.state.overrides["hostile"] = VoteOverride("actor", "yes", 100, "synthetic")
    policy = SuspiciousActivity(threshold=1)
    effect = policy.apply(ctx)
    honest = next(a for a in effect.actions if a.target_id == "honest")
    assert honest.data["signals"] == {
        "joined_volume": 1.0,
        "contribution_change": 1.0,
        "credential_replacement": 1.0,
        "vote_synchronization": 0.25,
    }
    assert honest.data["risk"] == 0.8125
    ctx.state.people["honest"].is_adversarial = True
    alternate = policy.apply(ctx)
    assert [a.data["risk"] for a in alternate.actions] == [a.data["risk"] for a in effect.actions]


@pytest.mark.parametrize(
    "factory,params",
    [
        (IdentityVerification, {"strength": float("nan")}),
        (IdentityVerification, {"verification_cost": -1}),
        (WaitingPeriod, {"days": 1.5}),
        (VoteCap, {"cap": float("inf")}),
        (Quorum, {"threshold": 1.1}),
        (Quorum, {"basis": "all"}),
        (ParticipationIncentive, {"boost": -1}),
        (ParticipationIncentive, {"success_probability": 2}),
        (SuspiciousActivity, {"weights": {"unknown": 1}}),
        (SuspiciousActivity, {"weights": {"joined_volume": -1}}),
        (SuspiciousActivity, {"restriction_days": -1}),
        (SuspiciousActivity, {"review_policy": "automatic_permanent_ban"}),
    ],
)
def test_invalid_policy_parameters_rejected(factory, params):
    with pytest.raises(ValueError):
        factory(**params)


def test_registry_rejects_unknown_constructor_keys():
    assert len(DEFENSE_FACTORIES) == 6
    for factory in DEFENSE_FACTORIES.values():
        with pytest.raises(TypeError):
            factory(unknown=1)
