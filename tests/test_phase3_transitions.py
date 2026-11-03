from copy import deepcopy

import pytest

from fan_governance.adversarial.base import AttackAction, Attacker, Resources
from fan_governance.scenarios.state import SimulationState
from fan_governance.scenarios.transitions import TransitionExecutor


def test_attacker_cannot_create_unfunded_contribution_or_duplicate_account():
    actor = Attacker("a", "wealthy_takeover", {}, Resources(10, 2))
    state = SimulationState({}, {}, {"a": actor})
    executor = TransitionExecutor()
    with pytest.raises(ValueError, match="underfund"):
        executor.apply(
            AttackAction(
                "join",
                "a",
                "a:account:0",
                0,
                data={"person_id": "a:person:0", "contribution": 10, "wealth": 10},
            ),
            state,
        )
    assert actor.resources.financial_remaining == 10
    action = AttackAction(
        "join",
        "a",
        "a:account:0",
        10,
        data={"person_id": "a:person:0", "contribution": 10, "wealth": 10},
    )
    assert executor.apply(action, state)
    assert actor.resources.financial_remaining == 0
    assert state.pending_contributions == 10
    assert not executor.apply(
        AttackAction("contribute", "a", "a:account:0", 1, data={"amount": 1}), state
    )
    assert state.accounts["a:account:0"].membership.contribution == 10


def test_failed_influence_still_costs_resources():
    actor = Attacker("a", "sybil", {}, Resources(5, 3))
    state = SimulationState({}, {}, {"a": actor})
    executor = TransitionExecutor()
    executor.apply(
        AttackAction(
            "join",
            "a",
            "a:account:0",
            0,
            data={"person_id": "a:person:0", "contribution": 0, "wealth": 0},
        ),
        state,
    )
    executor.apply(
        AttackAction(
            "influence",
            "a",
            "a:account:0",
            2,
            data={"success": False, "detected": False, "option": "approve", "until_day": 30},
        ),
        state,
    )
    assert actor.resources.financial_remaining == 3
    assert state.overrides == {}


@pytest.mark.parametrize(
    "money,operations",
    [(True, 1), (1, True), (1, 1.5), (float("nan"), 1), (1, -1), (1, float("inf"))],
)
def test_resource_budgets_reject_invalid_numeric_types(money, operations):
    with pytest.raises(ValueError):
        Resources(money, operations)


@pytest.mark.parametrize(
    "money,operations", [(True, 0), (0, True), (0, 0.5), (float("inf"), 0), (-1, 0)]
)
def test_invalid_spend_does_not_change_resources(money, operations):
    resources = Resources(10, 10)
    before = deepcopy(resources)
    with pytest.raises(ValueError):
        resources.spend(money, operations)
    assert resources == before


def test_no_epsilon_can_create_resources():
    resources = Resources(0, 0)
    assert not resources.can_spend(1e-12, 0)


@pytest.mark.parametrize(
    "kind,data",
    [
        ("contribute", {}),
        ("contribute", {"amount": True}),
        ("influence", {"success": True}),
        ("influence", {"success": True, "option": "approve", "until_day": float("inf")}),
        ("influence", {"success": 1, "option": "approve", "until_day": 20}),
        ("compromise", {}),
        ("compromise", {"success": True, "recovery_day": -1}),
        ("maintain", {"membership_fee": -1}),
        ("expire", {"day": 123}),
    ],
)
def test_malformed_commands_are_rejected_before_any_mutation(kind, data):
    actor = Attacker("a", "synthetic", {}, Resources(100, 10))
    state = SimulationState({}, {}, {"a": actor})
    executor = TransitionExecutor()
    executor.apply(
        AttackAction("join", "a", "a:account:0", data={"person_id": "a:person:0"}), state
    )
    before = deepcopy(state)
    with pytest.raises(ValueError):
        executor.apply(AttackAction(kind, "a", "a:account:0", 5, data=data), state)
    assert state == before


@pytest.mark.parametrize(
    "data",
    [
        {"person_id": "a:person:0", "membership_fee": -20, "contribution": 10},
        {"person_id": "a:person:0", "membership_fee": float("nan")},
        {"person_id": "a:person:0", "wealth": True},
        {"person_id": "a:person:0", "contribution": 10, "wealth": 1},
        {"person_id": None},
        {"person_id": "a:person:0", "fraudulent": "yes"},
        {"person_id": "a:person:0", "financial_cost": 0},
    ],
)
def test_invalid_join_cannot_debit_or_create_people_or_memberships(data):
    actor = Attacker("a", "synthetic", {}, Resources(100, 10))
    state = SimulationState({}, {}, {"a": actor})
    before = deepcopy(state)
    with pytest.raises(ValueError):
        TransitionExecutor().apply(AttackAction("join", "a", "a:account:0", 20, data=data), state)
    assert state == before


def test_compromise_changes_controller_without_creating_identity_or_membership():
    actor = Attacker("a", "synthetic", {}, Resources(100, 10))
    state = SimulationState({}, {}, {"a": actor})
    executor = TransitionExecutor()
    executor.apply(
        AttackAction("join", "a", "a:account:0", data={"person_id": "a:person:0"}), state
    )
    account = deepcopy(state.accounts["a:account:0"])
    executor.apply(
        AttackAction(
            "compromise", "a", "a:account:0", 1, data={"success": True, "recovery_day": 10}
        ),
        state,
    )
    assert len(state.people) == len(state.accounts) == 1
    assert state.accounts["a:account:0"].claim == account.claim
    assert state.accounts["a:account:0"].membership == account.membership
    assert state.accounts["a:account:0"].credential.controller_id == "a"


@pytest.mark.parametrize(
    "kind,data",
    [
        ("verify", {"accepted": True}),
        ("verify", {"accepted": True, "resolved_id": None}),
        (
            "review",
            {
                "confirmed": True,
                "flagged": True,
                "restricted_until": float("inf"),
                "review_policy": "temporary_restriction",
            },
        ),
        (
            "review",
            {
                "confirmed": True,
                "flagged": False,
                "restricted_until": 10,
                "review_policy": "temporary_restriction",
            },
        ),
        (
            "review",
            {
                "confirmed": True,
                "flagged": True,
                "restricted_until": 10,
                "review_policy": "monitor_only",
            },
        ),
    ],
)
def test_defensive_commands_are_atomic_and_restrictions_require_review_safeguards(kind, data):
    from fan_governance.defenses.base import DefenseAction
    from fan_governance.scenarios.transitions import apply_defense_action

    actor = Attacker("a", "synthetic", {}, Resources(100, 10))
    state = SimulationState({}, {}, {"a": actor})
    TransitionExecutor().apply(
        AttackAction("join", "a", "a:account:0", data={"person_id": "a:person:0"}), state
    )
    before = deepcopy(state)
    with pytest.raises(ValueError):
        apply_defense_action(DefenseAction(kind, "a:account:0", data, 1), state)
    assert state == before
