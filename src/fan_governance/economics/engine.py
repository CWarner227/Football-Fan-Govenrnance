"""Monthly financial transitions with an explicit cash/profit reconciliation.

A financial month is 30 simulated days. Revenue, wages, expenses and fees are
monthly flows; debt_principal is an opening stock, debt_repayment a monthly flow,
and debt_interest a monthly rate on opening debt. Historical population
contributions establish voting stakes only and are never booked as new cash.
Disposable income is new cash; remaining gross income is consumed outside the
model. Contribution willingness allocates that fraction of current disposable
income after fees, bounded by spendable cash. Wealth includes historical stake
plus remaining spendable assets; income is sampled separately.
"""

import hashlib
from statistics import NormalDist

import numpy as np

from fan_governance.agents.generator import sample_distribution
from fan_governance.economics.config import EconomicConfig
from fan_governance.economics.models import EconomicState
from fan_governance.economics.shocks import shock_effects as calculate_shock_effects


def _stream(seed: int, label: str) -> np.random.Generator:
    digest = hashlib.sha256(f"{seed}:{label}".encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:16], "little"))


def initialize_economy(config: EconomicConfig, people: dict, rng) -> EconomicState:
    ids = list(people)
    seed = int(rng.integers(0, 2**63))
    income = np.array(
        [
            max(
                0.0,
                float(sample_distribution(config.income_distribution, 1, _stream(seed, pid))[0]),
            )
            for pid in ids
        ]
    )
    correlation = config.income_wealth_correlation
    if correlation is not None and len(ids) > 1:
        wealth = np.array([people[pid].wealth for pid in ids])
        _, indices, counts = np.unique(wealth, return_inverse=True, return_counts=True)
        midranks = (np.cumsum(counts) - counts / 2) / len(ids)
        normal_scores = np.array([NormalDist().inv_cdf(float(x)) for x in midranks])[indices]
        latent = correlation * normal_scores + np.sqrt(1 - correlation**2) * _stream(
            seed, "copula"
        ).normal(size=len(ids))
        reordered = np.empty(len(ids))
        reordered[np.argsort(latent, kind="stable")] = np.sort(income)
        income = reordered
    result = EconomicState(cash=config.starting_cash, debt=config.debt_principal)
    for pid, monthly_income in zip(ids, income, strict=True):
        result.supporter_income[pid] = float(monthly_income)
        result.supporter_cash[pid] = max(0.0, people[pid].wealth - people[pid].contribution)
        people[pid].attributes["monthly_income"] = float(monthly_income)
    return result


class EconomicEngine:
    def __init__(self, config: EconomicConfig):
        self.config = config

    def _grow_membership(self, state, econ, scale, seed):
        """Exogenous new synthetic persons sampled from existing honest profiles."""
        if not self.config.membership_growth_rate:
            return
        templates = [p for p in state.people.values() if not p.is_adversarial]
        active = sum(a.membership.active for a in state.accounts.values())
        expectation = active * self.config.membership_growth_rate * scale
        growth_rng = _stream(seed, "membership_growth")
        count = int(expectation) + int(growth_rng.random() < expectation % 1)
        if not templates:
            return
        from fan_governance.membership.models import Membership
        from fan_governance.scenarios.state import Account, IdentityClaim, VotingCredential

        for index in range(count):
            pid = f"economic-member-{state.day}-{index}"
            if pid in state.people:
                raise ValueError("Economic growth person ID collision")
            template = templates[int(growth_rng.integers(len(templates)))]
            person = template.model_copy(
                deep=True,
                update={
                    "supporter_id": pid,
                    "contribution": 0.0,
                    "membership_age_days": 0,
                },
            )
            state.people[pid] = person
            state.accounts[pid] = Account(
                pid,
                IdentityClaim(pid, pid),
                Membership(member_id=pid, supporter_id=pid, age_days=0),
                VotingCredential(pid),
                joined_day=state.day,
            )
            state.record("membership_growth", target_id=pid)

    def step(self, state, *, month: int, elapsed_days: int, rng, shock_effects=None) -> dict:
        config = self.config
        if not config.enabled:
            return {}
        if elapsed_days < 0 or month < 0:
            raise ValueError("Economic month and elapsed days must be nonnegative")
        econ = state.economic_state
        if econ is None:
            econ = state.economic_state = initialize_economy(config, state.people, rng)
        if econ.last_day is not None and state.day <= econ.last_day:
            raise ValueError("Economic dates must be processed once in increasing order")
        if econ.last_month is not None and month < econ.last_month:
            raise ValueError("Economic months must not move backwards")
        seed = int(rng.integers(0, 2**63))
        factors = (
            calculate_shock_effects(config.shocks, month)
            if shock_effects is None
            else shock_effects
        )
        factors = calculate_shock_effects([], month) | dict(factors)
        if any(not np.isfinite(v) or v < 0 or v > 1 for v in factors.values()):
            raise ValueError("Shock multipliers must be finite values in [0,1]")
        scale = elapsed_days / 30
        if econ.initial_member_count is None:
            econ.initial_member_count = sum(a.membership.active for a in state.accounts.values())
        self._grow_membership(state, econ, scale, seed)
        # Pending flows have already been resource-checked by attack/defense transitions.
        contributions = float(state.pending_contributions)
        fees = float(state.pending_membership_fees)
        administrative_cost = float(state.pending_administrative_cost)
        opening_cash = econ.cash
        opening_debt = econ.debt
        renewal_due = renewals = 0
        affordable_count = 0
        affordability_attempts = 0
        honest_seen = set()
        accounts_by_person = {}
        controllers = {}
        for actor in state.attackers.values():
            for pid in actor.controlled_supporters:
                controllers.setdefault(pid, actor)
        for account in state.accounts.values():
            accounts_by_person.setdefault(account.person_id, []).append(account)
        # Income and spending are per true person, irrespective of account claims.
        for pid, person in state.people.items():
            if pid not in econ.supporter_income:
                econ.supporter_income[pid] = max(
                    0.0,
                    float(
                        sample_distribution(
                            config.income_distribution,
                            1,
                            _stream(seed, f"income:{pid}"),
                        )[0]
                    ),
                )
                econ.supporter_cash[pid] = max(0.0, person.wealth - person.contribution)
            disposable = (
                econ.supporter_income[pid]
                * config.disposable_income_fraction
                * factors["disposable_income"]
                * scale
            )
            econ.supporter_disposable_income[pid] = disposable
            econ.supporter_cash[pid] += disposable
            person.attributes["monthly_income"] = econ.supporter_income[pid]
            person.attributes["disposable_income"] = disposable
        active_before = sum(a.membership.active for a in state.accounts.values())
        for account in state.accounts.values():
            # Calendar lifecycle may have just expired an explicit term; renewal
            # is still permitted on that due date, but not after a rejected renewal.
            due = econ.next_renewal_day.get(account.account_id)
            if (
                not account.membership.active
                and due is not None
                and account.expires_day == due
                and state.day >= due
            ):
                account.membership.active = True
            if not account.membership.active:
                continue
            pid = account.person_id
            person = state.people[pid]
            actor = controllers.get(pid)
            # Compromised credentials alone do not transfer the person's finances.
            hostile = actor is not None
            if not hostile and pid in honest_seen:
                continue
            honest_seen.add(pid)
            due_day = econ.next_renewal_day.setdefault(
                account.account_id,
                account.expires_day
                if account.expires_day is not None
                else max(0, account.joined_day) + config.renewal_interval_months * 30,
            )
            if state.day >= due_day:
                renew_rng = _stream(seed, f"renewal:{account.account_id if hostile else pid}")
                renewal_due += 1
                retention = config.renewal_probability * factors["renewal"]
                if hostile:
                    retention *= float(actor.flags.get("retention_probability", 1))
                if renew_rng.random() >= retention:
                    self._expire(state, account, "nonrenewal", accounts_by_person, hostile)
                    continue
                renewals += 1
                econ.next_renewal_day[account.account_id] = (
                    state.day + config.renewal_interval_months * 30
                )
                if account.expires_day is not None:
                    account.expires_day = econ.next_renewal_day[account.account_id]
                state.record(
                    "membership_renewal",
                    actor_id=actor.attacker_id if hostile else "",
                    target_id=account.account_id,
                )
            fee = (
                0.0
                if getattr(account, "fee_paid_day", None) == state.day
                else config.membership_fee * scale
            )
            available = actor.resources.financial_remaining if hostile else econ.supporter_cash[pid]
            affordable = available + 1e-9 >= fee
            affordability_attempts += 1
            econ.supporter_affordability[pid] = affordable
            person.attributes["membership_affordable"] = affordable
            affordable_count += int(affordable)
            if not affordable:
                self._expire(state, account, "unaffordable", accounts_by_person, hostile)
                continue
            if hostile:
                actor.resources.spend(fee, operations=0)
            else:
                econ.supporter_cash[pid] = max(0.0, econ.supporter_cash[pid] - fee)
            fees += fee
            if hasattr(account, "fee_paid_day"):
                account.fee_paid_day = state.day
            if fee and (hostile or config.record_individual_transactions):
                state.record(
                    "membership_fee",
                    actor_id=actor.attacker_id if hostile else "",
                    target_id=account.account_id,
                    amount=fee,
                )
            if not hostile:
                # Actual disposable income has already entered the liquid stock;
                # committing it changes its classification, not gross wealth.
                person.wealth = person.contribution + econ.supporter_cash[pid]
                amount = min(
                    econ.supporter_cash[pid],
                    max(0.0, econ.supporter_disposable_income[pid] - fee)
                    * config.contribution_willingness,
                )
                econ.supporter_cash[pid] -= amount
                if amount:
                    person.contribution += amount
                    account.membership.contribution += amount
                    contributions += amount
                    if config.record_individual_transactions:
                        state.record(
                            "supporter_contribution", target_id=account.account_id, amount=amount
                        )
            person.wealth = person.contribution + econ.supporter_cash[pid]
        administrative_cost += (
            config.admin_cost_per_member
            * sum(a.membership.active for a in state.accounts.values())
            * scale
        )
        capital = 0.0
        for investor in config.investors:
            if month < investor.start_month or investor.investor_id in econ.investors_considered:
                continue
            econ.investors_considered.add(investor.investor_id)
            offered = econ.offered_voting_power_share.get(
                investor.investor_id, config.investor_voting_power_share
            )
            rights = investor.voting_rights and config.investor_voting_offer
            demand_met = investor.minimum_voting_power_share <= (offered if rights else 0)
            willingness = (
                investor.willingness
                * factors["investor_willingness"]
                * config.investor_policy_factor
            )
            accepted = (
                demand_met
                and _stream(seed, f"investor:{investor.investor_id}").random() < willingness
            )
            if not accepted:
                state.record(
                    "investor_declined",
                    actor_id=investor.investor_id,
                    expected_voting_share=investor.minimum_voting_power_share,
                    offered_voting_share=offered if rights else 0,
                )
                continue
            capital += investor.capital
            econ.investor_funding[investor.investor_id] = investor.capital
            econ.investor_ownership[investor.investor_id] = investor.ownership_share
            if rights:
                econ.investor_voting_rights.add(investor.investor_id)
            state.record(
                "investor_funding",
                actor_id=investor.investor_id,
                capital=investor.capital,
                ownership_share=investor.ownership_share,
                voting_rights=rights,
            )
        sporting_rng = _stream(seed, "sporting")
        injury_factor = 1 - config.injury_rate
        recruitment_value = (
            config.transfer_spending
            * scale
            * config.recruitment_effectiveness
            * factors["recruitment"]
        )
        econ.squad_value += recruitment_value
        sporting_index = max(
            0.0,
            config.squad_quality
            * config.management_quality
            * injury_factor
            * factors["recruitment"]
            + sporting_rng.normal(0, config.sporting_volatility),
        )
        sporting_factor = max(0.0, 1 + config.sporting_revenue_sensitivity * (sporting_index - 1))
        revenue_factor = (
            config.matchday_revenue_fraction * factors["matchday_revenue"]
            + (1 - config.matchday_revenue_fraction) * factors["commercial_revenue"]
        )
        revenue = config.operating_revenue * scale * revenue_factor * sporting_factor
        expenses = config.operating_expenses * scale * factors["operating_costs"]
        wages = config.wages * scale
        interest = opening_debt * config.debt_interest * scale
        principal = min(opening_debt, config.debt_repayment * scale)
        transfers = config.transfer_spending * scale
        profit = revenue + fees - expenses - wages - administrative_cost - interest
        financing = contributions + capital - principal
        econ.cash = opening_cash + profit + financing - transfers
        econ.debt = opening_debt - principal
        burn = max(0.0, -(profit - transfers - principal))
        active_after = sum(a.membership.active for a in state.accounts.values())
        row = {
            "month": month,
            "day": state.day,
            "opening_cash": opening_cash,
            "operating_revenue": revenue,
            "membership_revenue": fees,
            "operating_expenses": expenses,
            "wages": wages,
            "administrative_cost": administrative_cost,
            "interest": interest,
            "profit": profit,
            "operating_surplus": profit,
            "capital_raised": capital,
            "contribution_inflow": contributions,
            "debt_principal_repaid": principal,
            "financing_cashflow": financing,
            "transfer_spending": transfers,
            "investing_cashflow": -transfers,
            "cash_balance": econ.cash,
            "debt": econ.debt,
            "financial_runway_months": max(0.0, econ.cash) / (burn / scale)
            if burn > 0 and scale > 0
            else None,
            "insolvent": econ.cash < 0,
            "membership_affordability": affordable_count / affordability_attempts
            if affordability_attempts
            else 1.0,
            "membership_retention": active_after / active_before if active_before else 1.0,
            "renewal_rate": renewals / renewal_due if renewal_due else 1.0,
            "active_memberships": active_after,
            "sporting_index": sporting_index,
            "squad_value": econ.squad_value,
            "recruitment_value": recruitment_value,
            "shock_factor": revenue_factor,
            "investor_concentration": max(econ.investor_ownership.values(), default=0.0),
        }
        # Pending amounts are consumed once, after the successful accounting transition.
        state.pending_contributions = state.pending_membership_fees = (
            state.pending_administrative_cost
        ) = 0.0
        for key in (
            "operating_revenue",
            "membership_revenue",
            "operating_expenses",
            "wages",
            "administrative_cost",
            "interest",
            "profit",
            "capital_raised",
            "contribution_inflow",
            "debt_principal_repaid",
            "transfer_spending",
        ):
            econ.cumulative_ledger[key] = econ.cumulative_ledger.get(key, 0.0) + row[key]
        econ.ledger.append(row)
        econ.last_month = month
        econ.last_day = state.day
        state.record("economic_update", **row)
        return row

    @staticmethod
    def _expire(state, account, reason, accounts_by_person, hostile):
        affected = [account] if hostile else accounts_by_person[account.person_id]
        for candidate in affected:
            if candidate.membership.active:
                candidate.membership.active = False
                candidate.expires_day = None
                state.record("membership_expiration", target_id=candidate.account_id, reason=reason)
