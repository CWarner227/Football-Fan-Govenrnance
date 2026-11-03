"""Analytical, deterministic checks of synthetic strategy boundaries."""

from copy import deepcopy

import numpy as np
import pytest
from pydantic import ValidationError

from fan_governance.adversarial.base import Attacker, Resources, SimulationContext
from fan_governance.adversarial.objectives import evaluate_objective
from fan_governance.adversarial.strategies import ATTACK_FACTORIES
from fan_governance.agents.models import Supporter
from fan_governance.membership.models import Membership
from fan_governance.scenarios.state import Account, IdentityClaim, SimulationState, VotingCredential


def context(money=1000, operations=100, size=10):
    actor = Attacker(
        "a", "synthetic", {"type": "pass_target", "target": "yes"}, Resources(money, operations)
    )
    people = {str(i): Supporter(supporter_id=str(i), wealth=100) for i in range(size)}
    accounts = {
        i: Account(
            i, IdentityClaim(i, i), Membership(member_id=i, supporter_id=i), VotingCredential(i)
        )
        for i in people
    }
    state = SimulationState(people, accounts, {"a": actor})
    return SimulationContext(state, np.random.default_rng(32), actor)


@pytest.mark.parametrize("name", ATTACK_FACTORIES)
def test_all_plans_are_resource_bounded_and_do_not_mutate_state(name):
    ctx = context(money=2, operations=2)
    before = deepcopy(ctx.state)
    strategy = ATTACK_FACTORIES[name]()
    plan = strategy.plan(ctx)
    outcome = strategy.execute(plan, ctx)
    assert outcome.actions == plan.actions
    assert sum(a.financial_cost for a in plan.actions) <= 2
    assert sum(a.operational_cost for a in plan.actions) <= 2
    assert ctx.state == before


@pytest.mark.parametrize("name", ATTACK_FACTORIES)
def test_all_parameter_models_reject_unknown_and_nonfinite_fields(name):
    with pytest.raises(ValidationError):
        ATTACK_FACTORIES[name](callback=lambda: None)
    with pytest.raises(ValidationError):
        ATTACK_FACTORIES[name](hostile_turnout=float("nan"))


def test_wealthy_one_true_person_and_installments():
    ctx = context()
    strategy = ATTACK_FACTORIES["wealthy_takeover"](
        wealth=200, contribution_budget=120, contribution_strategy="installments", installments=3
    )
    (action,) = strategy.plan(ctx).actions
    assert action.data["contribution"] == 40
    assert action.data["wealth"] == 200
    assert action.data["fraudulent"] is False
    assert action.target_id == "a:account:0"


def test_coordinated_join_schedule_is_idempotent_from_state():
    ctx = context()
    ctx.state.day = 10
    strategy = ATTACK_FACTORIES["coordinated_infiltration"](number=4, joining_interval_days=10)
    assert len(strategy.plan(ctx).actions) == 2
    action = strategy.plan(ctx).actions[0]
    ctx.state.accounts[action.target_id] = Account(
        action.target_id,
        IdentityClaim("c", action.data["person_id"]),
        Membership(member_id="m", supporter_id=action.data["person_id"]),
        VotingCredential("v"),
    )
    assert len(strategy.plan(ctx).actions) == 1


def test_sybil_claims_share_single_true_person_and_cost_all_attempts():
    ctx = context(money=15)
    actions = (
        ATTACK_FACTORIES["sybil"](
            attempted_identities=10, verification_cost=2, account_creation_cost=3
        )
        .plan(ctx)
        .actions
    )
    assert len(actions) == 3
    assert len({a.data["person_id"] for a in actions}) == 1
    assert all(a.data["fraudulent"] for a in actions)
    assert sum(a.financial_cost for a in actions) == 15


def test_low_turnout_recruits_existing_people_without_new_claims():
    ctx = context(size=10)
    actions = ATTACK_FACTORIES["low_turnout"](hostile_population_share=0.3).plan(ctx).actions
    assert len(actions) == 3
    assert all(a.kind == "recruit" and a.target_id in ctx.state.accounts for a in actions)
    ctx.attacker.controlled_supporters.update(
        ctx.state.accounts[a.target_id].person_id for a in actions
    )
    assert not ATTACK_FACTORIES["low_turnout"](hostile_population_share=0.3).plan(ctx).actions


def test_influence_failure_still_costs_and_distribution_controls_success():
    ctx = context()
    actions = (
        ATTACK_FACTORIES["vote_influence"](
            targets=3,
            cost_per_attempt=4,
            acceptance_probability=1,
            susceptibility_distribution={"type": "constant", "parameters": {"value": 0}},
        )
        .plan(ctx)
        .actions
    )
    assert len(actions) == 3
    assert all(not a.data["success"] and a.financial_cost == 4 for a in actions)


def test_compromise_recovery_and_detection_are_explicit():
    ctx = context()
    (action,) = (
        ATTACK_FACTORIES["account_compromise"](
            targets=1,
            compromise_probability=1,
            recovery_probability=1,
            detection_probability=1,
            recovery_delay_days=7,
        )
        .plan(ctx)
        .actions
    )
    assert action.data == {"success": True, "detected": True, "recovery_day": 7}


def test_longterm_attrition_expires_instead_of_creating_extra_rights():
    ctx = context()
    ctx.attacker.controlled_supporters.add("0")
    actions = (
        ATTACK_FACTORIES["long_term_infiltration"](number=0, retention_probability=0)
        .plan(ctx)
        .actions
    )
    assert len(actions) == 1
    assert actions[0].kind == "expire"
    assert actions[0].operational_cost == 0


def test_longterm_nonpayment_expires_and_initial_tick_is_free():
    ctx = context(money=0)
    ctx.attacker.controlled_supporters.add("0")
    strategy = ATTACK_FACTORIES["long_term_infiltration"](number=0, maintenance_cost=10)
    (action,) = strategy.plan(ctx).actions
    assert action.kind == "expire"
    initial = SimulationContext(ctx.state, ctx.rng, ctx.attacker, period_days=0, membership_fee=50)
    (action,) = strategy.plan(initial).actions
    assert action.kind == "maintain" and action.financial_cost == 0


def test_compromise_obeys_election_window():
    ctx = context()
    ctx.attacker.flags["next_election_day"] = 100
    strategy = ATTACK_FACTORIES["account_compromise"](time_before_election_days=10)
    assert not strategy.plan(ctx).actions
    ctx.state.day = 90
    assert strategy.plan(ctx).actions


def test_wealthy_uses_available_budget_without_exceeding_wealth():
    ctx = context(money=7)
    (action,) = (
        ATTACK_FACTORIES["wealthy_takeover"](
            wealth=100, contribution_budget=100, account_creation_cost=2
        )
        .plan(ctx)
        .actions
    )
    assert action.financial_cost == 7
    assert action.data["contribution"] == 5


@pytest.mark.parametrize("name", ATTACK_FACTORIES)
def test_empty_account_history_and_empty_population_supported(name):
    ctx = context(size=0)
    strategy = ATTACK_FACTORIES[name]()
    assert strategy.execute(strategy.plan(ctx), ctx) is not None


def test_objectives_boundary_and_causal_control():
    assert not evaluate_objective({"type": "majority_cast"}, {"attacker_vote_share": 0.5})
    assert evaluate_objective({"type": "majority_cast"}, {"attacker_vote_share": 0.51})
    assert evaluate_objective(
        {"type": "voting_power_threshold", "threshold": 0.5}, {"attacker_power_share": 0.5}
    )
    assert not evaluate_objective(
        {"type": "pass_target"},
        {"proposal_passed": True, "baseline_passed": True, "attacker_vote_share": 0.7},
    )
    assert evaluate_objective(
        {"type": "block_target"},
        {"proposal_passed": False, "baseline_passed": True, "attacker_vote_share": 0.7},
    )
    assert not evaluate_objective(
        {"type": "influence_per_cost"}, {"financial_spent": 0, "attacker_vote_share": 1}
    )
    assert not evaluate_objective(
        {"type": "prevent_quorum"}, {"quorum_achieved": False, "baseline_quorum": False}
    )
    with pytest.raises(ValueError, match="future"):
        evaluate_objective({"type": "board_seats"}, {})
