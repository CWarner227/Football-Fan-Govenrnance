"""Analytical financial tests independent of election strategies."""

import numpy as np
import pytest
from pydantic import ValidationError

from fan_governance.adversarial.base import Attacker, Resources
from fan_governance.agents.models import Supporter
from fan_governance.core.config import DistributionConfig
from fan_governance.economics import (
    EconomicConfig,
    EconomicEngine,
    InvestorSpec,
    ShockSpec,
    initialize_economy,
)
from fan_governance.economics.shocks import shock_effects
from fan_governance.membership.models import Membership
from fan_governance.scenarios.state import Account, IdentityClaim, SimulationState, VotingCredential


def config(**kwargs):
    values = dict(
        starting_cash=100,
        operating_revenue=100,
        operating_expenses=20,
        wages=30,
        injury_rate=0,
        sporting_volatility=0,
        sporting_revenue_sensitivity=0,
        income_distribution=DistributionConfig(type="constant", parameters={"value": 100}),
    )
    return EconomicConfig(**(values | kwargs))


def state_for(people=None):
    people = people or {"p": Supporter(supporter_id="p", wealth=100)}
    accounts = {
        pid: Account(
            pid,
            IdentityClaim(pid, pid),
            Membership(member_id=pid, supporter_id=pid),
            VotingCredential(pid),
        )
        for pid in people
    }
    return SimulationState(people, accounts, {}, day=30)


def step(state, cfg, month=1, days=30, seed=1):
    return EconomicEngine(cfg).step(
        state, month=month, elapsed_days=days, rng=np.random.default_rng(seed)
    )


def test_compact_receipts_preserve_exact_accounting_and_random_draws():
    compact, detailed = state_for(), state_for()
    first = step(compact, config(membership_fee=3, contribution_willingness=0.1))
    second = step(
        detailed,
        config(membership_fee=3, contribution_willingness=0.1, record_individual_transactions=True),
    )
    assert first == second
    assert compact.people == detailed.people
    assert compact.economic_state == detailed.economic_state
    assert not any(
        e["kind"] in ("membership_fee", "supporter_contribution") for e in compact.events
    )
    assert {e["kind"] for e in detailed.events} >= {"membership_fee", "supporter_contribution"}


def test_hand_calculated_cash_profit_and_debt_reconcile():
    cfg = config(
        membership_fee=10,
        admin_cost_per_member=2,
        debt_principal=100,
        debt_interest=0.05,
        debt_repayment=10,
        transfer_spending=8,
        investors=[InvestorSpec(investor_id="i", capital=40, ownership_share=0.2)],
    )
    state = state_for()
    state.pending_contributions = 7
    row = step(state, cfg)
    assert row["profit"] == 53
    assert row["cash_balance"] == 182
    assert row["debt"] == 90
    assert row["financing_cashflow"] == 37
    assert (
        row["cash_balance"]
        == row["opening_cash"]
        + row["profit"]
        + row["financing_cashflow"]
        + row["investing_cashflow"]
    )
    assert row["financial_runway_months"] is None


def test_pending_flows_and_historical_contributions_not_repeated():
    state = state_for({"p": Supporter(supporter_id="p", wealth=100, contribution=80)})
    state.pending_contributions = 15
    state.pending_membership_fees = 4
    state.pending_administrative_cost = 3
    cfg = config()
    first = step(state, cfg)
    state.day = 60
    second = step(state, cfg, month=2)
    assert first["contribution_inflow"] == 15
    assert second["contribution_inflow"] == 0
    assert second["membership_revenue"] == 0
    assert state.economic_state.cumulative_ledger["contribution_inflow"] == 15
    assert second["administrative_cost"] == 0
    assert state.pending_contributions == 0


def test_hostile_membership_fees_debit_budget_or_expire():
    state = state_for()
    actor = Attacker("a", "infiltration", {}, Resources(15, 0), controlled_supporters={"p"})
    state.attackers["a"] = actor
    cfg = config(membership_fee=10, contribution_willingness=1)
    row = step(state, cfg)
    assert row["membership_revenue"] == 10
    assert row["contribution_inflow"] == 0
    assert actor.resources.financial_remaining == 5
    state.day = 60
    assert step(state, cfg, month=2)["membership_revenue"] == 0
    assert not state.accounts["p"].membership.active
    assert actor.resources.financial_remaining == 5


def test_honest_duplicate_claims_do_not_multiply_income_or_fees():
    state = state_for()
    state.accounts["alias"] = Account(
        "alias",
        IdentityClaim("alias", "p"),
        Membership(member_id="alias", supporter_id="p"),
        VotingCredential("alias"),
    )
    row = step(state, config(membership_fee=10, contribution_willingness=1))
    assert row["membership_revenue"] == 10
    assert row["contribution_inflow"] == 10
    assert state.economic_state.supporter_cash["p"] == 100
    assert state.people["p"].contribution == 10


def test_available_cash_bounds_fees_and_contributions():
    state = state_for({"p": Supporter(supporter_id="p", wealth=0)})
    cfg = config(membership_fee=30, contribution_willingness=1)
    row = step(state, cfg)
    assert row["membership_revenue"] == 0
    assert row["contribution_inflow"] == 0
    assert row["membership_affordability"] == 0
    assert state.economic_state.supporter_cash["p"] == 20
    assert not state.accounts["p"].membership.active


def test_renewal_is_due_annually_not_randomly_each_month():
    state = state_for()
    cfg = config(renewal_probability=0)
    for month in range(1, 12):
        state.day = month * 30
        step(state, cfg, month)
        assert state.accounts["p"].membership.active
    state.day = 360
    step(state, cfg, 12)
    assert not state.accounts["p"].membership.active
    assert len([e for e in state.events if e["kind"] == "membership_expiration"]) == 1


def test_investor_ownership_separate_from_explicit_voting_rights():
    state = state_for()
    cfg = config(
        investors=[
            InvestorSpec(investor_id="i", capital=50, ownership_share=0.8, voting_rights=True)
        ]
    )
    step(state, cfg)
    assert state.economic_state.investor_ownership == {"i": 0.8}
    assert not state.economic_state.investor_voting_rights
    assert len(state.accounts) == 1
    state2 = state_for()
    step(state2, cfg.model_copy(update={"investor_voting_offer": True}))
    assert state2.economic_state.investor_voting_rights == {"i"}
    assert len(state2.accounts) == 1  # Only the explicit governance adapter grants credentials.


def test_investor_demand_and_timing_decline_are_one_shot():
    cfg = config(
        investors=[
            InvestorSpec(
                investor_id="i",
                capital=50,
                start_month=2,
                voting_rights=True,
                minimum_voting_power_share=0.4,
            )
        ],
        investor_voting_offer=True,
        investor_voting_power_share=0.1,
    )
    state = state_for()
    assert step(state, cfg, 1)["capital_raised"] == 0
    state.day = 60
    assert step(state, cfg, 2)["capital_raised"] == 0
    state.day = 90
    step(state, cfg, 3)
    assert len([e for e in state.events if e["kind"] == "investor_declined"]) == 1


@pytest.mark.parametrize("correlation", [-1, 1])
def test_income_is_independent_marginal_with_configured_rank_correlation(correlation):
    people = {str(i): Supporter(supporter_id=str(i), wealth=i + 1) for i in range(100)}
    cfg = config(
        income_distribution=DistributionConfig(
            type="uniform", parameters={"low": 300, "high": 700}
        ),
        income_wealth_correlation=correlation,
    )
    econ = initialize_economy(cfg, people, np.random.default_rng(3))
    income = np.array(list(econ.supporter_income.values()))
    assert income.min() >= 300 and income.max() <= 700
    assert np.all(np.diff(income) * correlation > 0)
    assert np.array_equal([p.wealth for p in people.values()], np.arange(1, 101))


def test_revenue_shock_recovers_without_compounding():
    cfg = config(
        shocks=[ShockSpec(name="revenue_loss", start_month=1, duration_months=2, severity=0.5)]
    )
    state = state_for()
    revenues = []
    for month in range(1, 4):
        state.day = month * 30
        revenues.append(step(state, cfg, month)["operating_revenue"])
    assert revenues == [50, 50, 100]


def test_independent_shocks_compose_once_and_recovery_is_linear():
    shocks = [
        ShockSpec(name="economic_downturn", severity=0.5, duration_months=1, recovery_months=1),
        ShockSpec(name="stadium_closure", severity=0.5),
    ]
    assert shock_effects(shocks, 0)["commercial_revenue"] == 0.5
    assert shock_effects(shocks, 0)["matchday_revenue"] == 0.5
    assert shock_effects(shocks, 0)["renewal"] == 0.25
    assert shock_effects(shocks, 1)["commercial_revenue"] == 0.75
    assert shock_effects(shocks, 2)["commercial_revenue"] == 1


def test_poor_recruitment_changes_value_without_reducing_transfer_cash():
    normal, shocked = state_for(), state_for()
    row = step(normal, config(transfer_spending=20))
    shock = step(
        shocked,
        config(
            transfer_spending=20,
            shocks=[ShockSpec(name="poor_recruitment", start_month=1, severity=0.8)],
        ),
    )
    assert row["transfer_spending"] == shock["transfer_spending"] == 20
    assert shock["recruitment_value"] == pytest.approx(4)
    assert row["recruitment_value"] == 20


def test_years_reconcile_and_reproduce_exactly():
    cfg = config(
        membership_fee=3,
        contribution_willingness=0.2,
        sporting_volatility=0.3,
        sporting_revenue_sensitivity=0.1,
        investors=[InvestorSpec(investor_id="i", capital=100, start_month=5)],
        shocks=[
            ShockSpec(
                name="economic_downturn", start_month=10, duration_months=6, recovery_months=3
            )
        ],
    )
    results = []
    for _ in range(2):
        state = state_for()
        rows = []
        for month in range(36):
            state.day = (month + 1) * 30
            row = step(state, cfg, month, seed=month)
            assert row["cash_balance"] == pytest.approx(
                row["opening_cash"]
                + row["profit"]
                + row["financing_cashflow"]
                - row["transfer_spending"]
            )
            rows.append(row)
        assert sum(r["capital_raised"] for r in rows) == 100
        results.append(rows)
    assert results[0] == results[1]


def test_common_random_sporting_and_renewal_streams_survive_extra_people():
    cfg = config(renewal_probability=0.5, sporting_volatility=1, renewal_interval_months=1)
    states = [
        state_for(),
        state_for(
            {
                "p": Supporter(supporter_id="p", wealth=100),
                "extra": Supporter(supporter_id="extra", wealth=100),
            }
        ),
    ]
    rows = [step(state, cfg) for state in states]
    assert rows[0]["sporting_index"] == rows[1]["sporting_index"]
    assert states[0].accounts["p"].membership.active == states[1].accounts["p"].membership.active


def test_intramonth_steps_are_allowed_but_duplicate_dates_are_rejected():
    state = state_for()
    cfg = config()
    step(state, cfg, month=1, days=15)
    state.day = 45
    step(state, cfg, month=1, days=15)
    with pytest.raises(ValueError, match="once"):
        step(state, cfg, month=1, days=15)


def test_invalid_ownership_and_duplicate_shocks_rejected():
    with pytest.raises(ValidationError, match="at most one"):
        config(
            investors=[
                InvestorSpec(investor_id="a", capital=0, ownership_share=0.7),
                InvestorSpec(investor_id="b", capital=0, ownership_share=0.4),
            ]
        )
    with pytest.raises(ValidationError, match="Duplicate shocks"):
        config(shocks=[ShockSpec(name="revenue_loss"), ShockSpec(name="revenue_loss")])
