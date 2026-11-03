"""Small analytical scenarios exercise the full Phase 3 transition pipeline."""

from collections import defaultdict
from pathlib import Path

import pytest

from fan_governance.core.config import ModelSpec
from fan_governance.scenarios.config import ScenarioConfig, load_scenario
from fan_governance.scenarios.runner import run_scenario


@pytest.mark.parametrize(
    "path", sorted(Path("configs/scenarios").glob("*.yaml")), ids=lambda p: p.stem
)
def test_each_library_scenario_executes_end_to_end(path):
    config = load_scenario(path)
    config.simulation.population.size = 30
    config.simulation.voting.strategies = [ModelSpec(name="equal")]
    config.experiment.trials = 1
    results = run_scenario(config)
    assert len(results.summary) == 3
    assert all(
        row["financial_spent"] <= sum(a.financial_budget for a in config.attacks)
        for row in results.summary
    )


def small_config(**changes):
    raw = {
        "name": "integration",
        "simulation": {
            "population": {
                "size": 12,
                "wealth": {"distribution": "constant", "value": 1000},
                "contribution": {"distribution": "constant", "value": 10},
                "membership_age_days": {"distribution": "constant", "value": 730},
            },
            "governance": {"waiting_period_days": 0, "quorum": 0},
            "voting": {"strategies": ["equal", "proportional"]},
        },
        "timeline": {"duration_months": 6},
        "elections": {"interval_months": 3},
        "economics": {"enabled": False},
        "experiment": {"trials": 1, "seed": 43},
        "honest_turnout": 0.7,
    }
    raw.update(changes)
    return ScenarioConfig.model_validate(raw)


def actor(name, **parameters):
    return {
        "name": name,
        "attacker_id": "hostile",
        "financial_budget": 100000,
        "operational_budget": 1000,
        "parameters": parameters,
    }


def test_defense_alone_cannot_satisfy_inactive_attacker_objective():
    config = small_config(
        attacks=[
            {
                "name": "wealthy_takeover",
                "financial_budget": 0,
                "operational_budget": 0,
                "objective": {"type": "prevent_quorum"},
            }
        ],
        defenses=[{"name": "quorum", "parameters": {"threshold": 1}}],
    )
    result = run_scenario(config)
    assert not any(row["capture_success"] for row in result.summary)
    assert not any(row["outcome_changed"] for row in result.elections)


def test_historical_stake_is_not_a_repeated_contribution_change_signal():
    config = small_config(
        defenses=[
            {
                "name": "suspicious_activity",
                "parameters": {"weights": {"contribution_change": 1}, "threshold": 0.01},
            }
        ]
    )
    results = run_scenario(config)
    reviews = [e for e in results.events if e["kind"] == "defense_review"]
    assert reviews
    assert all(e["signals"]["contribution_change"] == 0 for e in reviews)
    assert not any(e["flagged"] for e in reviews)


def test_administrative_cost_includes_club_and_defense_costs():
    config = small_config(
        economics={"enabled": True, "admin_cost_per_member": 2},
        defenses=[{"name": "identity_verification", "parameters": {"verification_cost": 1}}],
    )
    result = run_scenario(config)
    for summary in result.summary:
        matching = [
            r
            for r in result.timeseries
            if r["variant"] == summary["variant"] and r["voting_model"] == summary["voting_model"]
        ]
        assert summary["administrative_cost"] == pytest.approx(
            sum(r["administrative_cost"] for r in matching)
        )
        assert summary["administrative_cost"] >= summary["defense_administrative_cost"]


def test_run_scenario_reproducible_and_no_attack_variants_pair():
    config = small_config()
    first, second = run_scenario(config), run_scenario(config)
    assert first.summary == second.summary
    assert first.elections == second.elections
    assert first.events == second.events
    assert first.timeseries == second.timeseries

    def comparable_metadata(metadata):
        return {k: v for k, v in metadata.items() if k != "elapsed_seconds"}

    assert comparable_metadata(first.metadata) == comparable_metadata(second.metadata)
    paired = defaultdict(list)
    for row in first.elections:
        paired[row["voting_model"], row["day"]].append(row)
    for rows in paired.values():
        assert {row["variant"] for row in rows} == {"control", "unprotected", "defended"}
        signatures = {
            (row["votes_cast"], row["eligible_voter_count"], row["passed"], row["turnout"])
            for row in rows
        }
        assert len(signatures) == 1


def test_long_term_members_wait_and_activate_at_the_configured_time():
    config = small_config(
        timeline={"duration_months": 12},
        elections={"interval_months": 3},
        attacks=[
            actor("long_term_infiltration", number=3, retention_probability=1, activation_day=181)
        ],
        defenses=[
            {"name": "identity_verification", "parameters": {"strength": 1}},
            {"name": "waiting_period", "parameters": {"days": 180}},
        ],
    )
    result = run_scenario(config)
    rows = sorted(
        (
            r
            for r in result.elections
            if r["variant"] == "defended" and r["voting_model"] == "equal"
        ),
        key=lambda r: r["day"],
    )
    assert rows[0]["day"] < 180
    assert rows[0]["eligible_voter_count"] == 12
    assert rows[0]["attacker_power_share"] == 0
    assert rows[1]["day"] >= 181
    assert rows[1]["eligible_voter_count"] == 15
    assert rows[1]["attacker_power_share"] == pytest.approx(3 / 15)
    joins = [
        event
        for event in result.events
        if event["variant"] == "defended"
        and event["voting_model"] == "equal"
        and event["kind"] == "attack_join"
    ]
    assert len(joins) == 3
    assert {event["day"] for event in joins} == {0}


def test_off_grid_zero_attempt_attack_does_not_change_paired_economics():
    config = small_config(
        attacks=[actor("sybil", attempted_identities=0, start_day=15)],
        economics={
            "enabled": True,
            "sporting_volatility": 0.5,
            "sporting_revenue_sensitivity": 0.5,
        },
    )
    result = run_scenario(config)
    for model in ("equal", "proportional"):
        balances = [row["cash_balance"] for row in result.summary if row["voting_model"] == model]
        assert balances == pytest.approx([balances[0]] * 3)


def test_disabling_identity_defense_restores_unprotected_fraudulent_votes():
    config = small_config(
        attacks=[actor("sybil", attempted_identities=5)],
        defenses=[{"name": "identity_verification", "parameters": {"strength": 1}}],
    )
    protected = run_scenario(config)
    disabled = config.model_copy(deep=True)
    disabled.defenses = []
    restored = run_scenario(disabled)
    for model in ("equal", "proportional"):
        strong = [
            r
            for r in protected.elections
            if r["variant"] == "defended" and r["voting_model"] == model
        ]
        assert all(r["eligible_voter_count"] == 12 for r in strong)
        weak = [
            r
            for r in restored.elections
            if r["variant"] == "defended" and r["voting_model"] == model
        ]
        baseline = [
            r
            for r in restored.elections
            if r["variant"] == "unprotected" and r["voting_model"] == model
        ]
        assert all(r["eligible_voter_count"] == 17 for r in weak)
        assert [(r["votes_cast"], r["attacker_power_share"], r["passed"]) for r in weak] == [
            (r["votes_cast"], r["attacker_power_share"], r["passed"]) for r in baseline
        ]


def test_combined_crisis_cash_reconciles_with_each_flow_and_investor_capital_once():
    config = load_scenario("configs/scenarios/combined_crisis.yaml")
    config.simulation.population.size = 15
    config.simulation.voting.strategies = config.simulation.voting.strategies[:1]
    config.experiment.trials = 1
    config.timeline.duration_months = 6
    config.elections.interval_months = 3
    result = run_scenario(config)
    groups = defaultdict(list)
    for row in result.timeseries:
        groups[row["variant"]].append(row)
        assert row["cash_balance"] == pytest.approx(
            row["opening_cash"]
            + row["profit"]
            + row["financing_cashflow"]
            + row["investing_cashflow"]
        )
        assert row["profit"] == pytest.approx(
            row["operating_revenue"]
            + row["membership_revenue"]
            - row["operating_expenses"]
            - row["wages"]
            - row["administrative_cost"]
            - row["interest"]
        )
        assert row["financing_cashflow"] == pytest.approx(
            row["capital_raised"] + row["contribution_inflow"] - row["debt_principal_repaid"]
        )
    for rows in groups.values():
        ordered = sorted(rows, key=lambda r: r["day"])
        assert ordered[0]["opening_cash"] == config.economics.starting_cash
        for prior, current in zip(ordered, ordered[1:], strict=False):
            assert current["opening_cash"] == pytest.approx(prior["cash_balance"])
        assert sum(r["capital_raised"] for r in rows) == 20000
    assert not any(event["kind"] == "investor_voting_rights" for event in result.events)
    assert not any(
        row["attacker_power_share"] for row in result.elections if row["variant"] == "control"
    )
