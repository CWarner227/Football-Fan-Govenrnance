"""Analytical scenario projection and explicit investor-rights integration."""

from copy import deepcopy

import pytest

from fan_governance.adversarial.base import Attacker, Resources
from fan_governance.agents.models import Supporter
from fan_governance.core.context import RandomStreams
from fan_governance.core.engine import proposal_from_config
from fan_governance.core.registry import default_registry
from fan_governance.economics.models import EconomicState
from fan_governance.membership.models import Membership
from fan_governance.scenarios.config import ScenarioConfig
from fan_governance.scenarios.runner import _investors, _project, run_scenario
from fan_governance.scenarios.state import (
    Account,
    IdentityClaim,
    SimulationState,
    VoteOverride,
    VotingCredential,
)
from fan_governance.voting.strategies import EqualVoting, ProportionalVoting


def scenario(**updates):
    raw = {
        "name": "analytical",
        "timeline": {"duration_months": 1},
        "elections": {"interval_months": 1},
        "experiment": {"trials": 1, "seed": 9},
        "simulation": {
            "population": {
                "size": 4,
                "wealth": {"type": "constant", "value": 100},
                "contribution": {"type": "constant", "value": 1},
            },
            "governance": {"waiting_period_days": 0},
            "voting": {"strategies": ["equal"]},
            "preference": {"name": "synthetic", "parameters": {"approval_probability": 0}},
        },
        "economics": {"enabled": False},
        "honest_turnout": 1,
    }
    raw.update(updates)
    return ScenarioConfig.model_validate(raw)


def basic_state():
    person = Supporter(supporter_id="p", wealth=10, contribution=1)
    account = Account(
        "m",
        IdentityClaim("p", "p", verified=True, resolved_id="p"),
        Membership(member_id="m", supporter_id="p", age_days=365, contribution=1),
        VotingCredential("c"),
    )
    actor = Attacker(
        "a", "synthetic", {"target": "approve"}, Resources(100, 100), flags={"activation_day": 100}
    )
    return SimulationState({"p": person}, {"m": account}, {"a": actor}, day=31)


def project(state, config=None):
    config = config or scenario()
    return _project(
        state,
        config,
        proposal_from_config(config.simulation),
        RandomStreams(9),
        default_registry(),
        0,
        1,
    )


def test_activation_expired_override_and_compromised_controller_precedence():
    state = basic_state()
    state.attackers["a"].controlled_supporters.add("p")
    _, _, realization, controllers, _ = project(state)
    assert controllers["p"] is None
    assert realization.preferences["p"] == "reject"
    state.overrides["m"] = VoteOverride("a", "approve", 30, "influence", True)
    assert project(state)[3]["p"] is None
    state.accounts["m"].credential.controller_id = "a"
    assert project(state)[3]["p"] == "a"
    assert project(state)[2].preferences["p"] == "approve"
    state.accounts["m"].credential.controller_id = None
    state.day = 100
    assert project(state)[3]["p"] == "a"


def test_aliases_reuse_true_person_draws_and_strong_resolution_deduplicates():
    state = basic_state()
    original = project(state)[2]
    alias = deepcopy(state.accounts["m"])
    alias.account_id = "alias"
    alias.membership.member_id = "alias"
    alias.claim.claim_id = alias.claim.resolved_id = "alias"
    state.accounts["alias"] = alias
    realization = project(state)[2]
    assert realization.preferences["alias"] == original.preferences["p"]
    assert realization.participating["alias"] == original.participating["p"]
    alias.claim.resolved_id = "p"
    club, eligibility, realization, _, _ = project(state)
    assert len(eligibility.eligible(club.supporters, club.memberships)) == 1
    assert len(realization.preferences) == 1


def test_sybil_strong_verification_prevents_duplicate_voting_rights():
    config = scenario(
        attacks=[{"name": "sybil", "parameters": {"attempted_identities": 8}}],
        defenses=[{"name": "identity_verification", "parameters": {"strength": 1}}],
    )
    rows = {r["variant"]: r for r in run_scenario(config).elections}
    assert rows["unprotected"]["eligible_voter_count"] == 12
    assert rows["defended"]["eligible_voter_count"] == rows["control"]["eligible_voter_count"] == 4
    assert rows["unprotected"]["attacker_vote_share"] == pytest.approx(8 / 12)
    assert rows["defended"]["attacker_vote_share"] == 0


def test_vote_cap_limits_wealthy_influence_analytically():
    config = scenario(
        attacks=[
            {"name": "wealthy_takeover", "parameters": {"wealth": 100, "contribution_budget": 100}}
        ],
        defenses=[{"name": "vote_cap", "parameters": {"cap": 1}}],
    )
    config.simulation.voting.strategies = ["proportional"]
    rows = {r["variant"]: r for r in run_scenario(config).elections}
    assert rows["unprotected"]["attacker_power_share"] == pytest.approx(100 / 104)
    assert rows["defended"]["attacker_power_share"] == pytest.approx(1 / 5)


def test_investor_actual_power_offer_respects_model_caps_and_eligibility():
    config = scenario(
        economics={
            "investor_voting_offer": True,
            "investors": [{"investor_id": "i", "capital": 9, "voting_rights": True}],
        }
    )
    state = basic_state()
    state.economic_state = EconomicState(0, 0)
    proposal = proposal_from_config(config.simulation)
    _investors(state, config.economics, proposal=proposal, voting=ProportionalVoting(), month=0)
    assert state.economic_state.offered_voting_power_share["i"] == pytest.approx(0.9)
    assert "investor:i" not in state.people
    _investors(state, config.economics, proposal=proposal, voting=EqualVoting(), month=0)
    assert state.economic_state.offered_voting_power_share["i"] == 0.5
    _investors(
        state, config.economics, proposal=proposal, voting=ProportionalVoting(), cap=1, month=0
    )
    assert state.economic_state.offered_voting_power_share["i"] == 0.5
    proposal.eligibility_rules.waiting_period_days = 30
    _investors(state, config.economics, proposal=proposal, voting=ProportionalVoting(), month=0)
    assert state.economic_state.offered_voting_power_share["i"] == 0
    state.economic_state.investor_funding["i"] = 9
    _investors(state, config.economics)
    assert "investor:i" not in state.people
    state.economic_state.investor_voting_rights.add("i")
    _investors(state, config.economics)
    assert state.accounts["investor:i"].membership.contribution == 9


def test_investor_funding_decision_uses_actual_governance_offer_before_payment():
    config = scenario(
        economics={
            "investor_voting_offer": True,
            "income_distribution": {"type": "constant", "value": 0},
            "investors": [
                {
                    "investor_id": "i",
                    "capital": 9,
                    "voting_rights": True,
                    "minimum_voting_power_share": 0.6,
                }
            ],
        },
        defenses=[{"name": "vote_cap", "parameters": {"cap": 1}}],
    )
    config.simulation.voting.strategies = ["proportional"]
    result = run_scenario(config)
    rows = {r["variant"]: r for r in result.elections}
    assert rows["unprotected"]["eligible_voter_count"] == 5
    assert rows["defended"]["eligible_voter_count"] == 4
    funding = [e for e in result.events if e["kind"] == "investor_funding"]
    assert any(e["variant"] == "unprotected" and e["capital"] == 9 for e in funding)
    assert not any(e["variant"] == "defended" for e in funding)


def test_financing_without_explicit_voting_grant_never_creates_an_elector():
    config = scenario(
        economics={
            "investor_voting_offer": True,
            "investors": [{"investor_id": "i", "capital": 9, "voting_rights": False}],
        }
    )
    result = run_scenario(config)
    assert all(r["eligible_voter_count"] == 4 for r in result.elections)
    assert any(e["kind"] == "investor_funding" and e["capital"] == 9 for e in result.events)
    assert not any(e["kind"] == "investor_voting_rights" for e in result.events)
