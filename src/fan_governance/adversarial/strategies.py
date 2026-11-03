"""Bounded, synthetic transition proposals. Only the central executor spends resources."""

from typing import Literal

import numpy as np
from pydantic import Field, model_validator

from fan_governance.adversarial.base import AttackAction, AttackOutcome, AttackPlan
from fan_governance.agents.generator import sample_distribution
from fan_governance.core.config import DistributionConfig, Nonnegative, Probability, ValidatedModel


class CommonParameters(ValidatedModel):
    start_day: int = Field(default=0, ge=0)
    activation_day: int = Field(default=0, ge=0)
    hostile_turnout: Probability = 1.0


class WealthyParameters(CommonParameters):
    wealth: Nonnegative = 1_000_000
    contribution_budget: Nonnegative = 100_000
    contribution_strategy: Literal["lump_sum", "installments"] = "lump_sum"
    installments: int = Field(default=12, ge=1, le=100_000)
    account_creation_cost: Nonnegative = 0


class CoordinatedParameters(CommonParameters):
    number: int = Field(default=10, ge=0, le=1_000_000)
    hostile_share: Probability | None = None
    joining_interval_days: int = Field(default=0, ge=0)
    contribution: Nonnegative = 0
    account_creation_cost: Nonnegative = 0


class SybilParameters(CommonParameters):
    attempted_identities: int = Field(default=10, ge=0, le=1_000_000)
    contribution: Nonnegative = 0
    verification_cost: Nonnegative = 0
    account_creation_cost: Nonnegative = 1


class LowTurnoutParameters(CommonParameters):
    hostile_population_share: Probability = 0.1
    recruitment_cost: Nonnegative = 0


class InfluenceParameters(CommonParameters):
    targets: int = Field(default=10, ge=0, le=1_000_000)
    cost_per_attempt: Nonnegative = 1
    acceptance_probability: Probability = 0.5
    detection_probability: Probability = 0
    susceptibility_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(type="constant", parameters={"value": 1})
    )
    influence_duration_days: int = Field(default=30, ge=1)
    mode: Literal["financial", "coercive"] = "financial"
    force_turnout: bool = True

    @model_validator(mode="after")
    def numeric_susceptibility(self):
        if self.susceptibility_distribution.type not in {
            "constant",
            "uniform",
            "normal",
            "lognormal",
            "beta",
        }:
            raise ValueError("Susceptibility requires a built-in numeric distribution")
        sample_distribution(self.susceptibility_distribution, 0, np.random.default_rng(0))
        return self


class CompromiseParameters(CommonParameters):
    targets: int = Field(default=10, ge=0, le=1_000_000)
    cost_per_attempt: Nonnegative = 1
    compromise_probability: Probability = 0.2
    recovery_probability: Probability = 0.5
    detection_probability: Probability = 0
    recovery_delay_days: int = Field(default=30, ge=0)
    time_before_election_days: int = Field(default=30, ge=0)


class LongTermParameters(CoordinatedParameters):
    retention_probability: Probability = 1
    maintenance_cost: Nonnegative = 0


class SyntheticStrategy:
    parameter_model = CommonParameters

    def __init__(self, **parameters):
        self.parameters = self.parameter_model(**parameters)

    def execute(self, plan, context):
        actor = context.attacker
        if actor is None or any(a.actor_id != actor.attacker_id for a in plan.actions):
            raise ValueError("Attack plan must belong to the contextual attacker")
        return AttackOutcome(plan.actions)

    def _ready(self, context):
        return (
            context.attacker is not None
            and self.parameters.start_day <= context.state.day <= context.attacker.time_horizon
        )

    def _bounded(self, context, actions):
        financial = operations = 0
        selected = []
        for action in actions:
            if context.attacker.resources.can_spend(
                financial + action.financial_cost, operations + action.operational_cost
            ):
                selected.append(action)
                financial += action.financial_cost
                operations += action.operational_cost
        return AttackPlan(tuple(selected))

    def _join(self, context, index, contribution, creation_cost, fraudulent=False, wealth=None):
        actor = context.attacker.attacker_id
        account_id = f"{actor}:account:{index}"
        person_id = f"{actor}:person:{0 if fraudulent else index}"
        return AttackAction(
            "join",
            actor,
            account_id,
            contribution + creation_cost,
            data={
                "person_id": person_id,
                "contribution": contribution,
                "wealth": contribution if wealth is None else wealth,
                "fraudulent": fraudulent,
                "activation_day": self.parameters.activation_day,
                "hostile_turnout": self.parameters.hostile_turnout,
                "account_creation_cost": creation_cost,
            },
        )

    def _targets(self, context):
        return [
            a
            for _, a in sorted(context.state.accounts.items())
            if a.membership.active and not context.state.controlled(a)
        ]


class WealthyTakeover(SyntheticStrategy):
    parameter_model = WealthyParameters

    def plan(self, context):
        if not self._ready(context):
            return AttackPlan()
        p = self.parameters
        key = f"{context.attacker.attacker_id}:account:0"
        account = context.state.accounts.get(key)
        spent = account.membership.contribution if account else 0
        remaining = max(0, min(p.contribution_budget, p.wealth) - spent)
        amount = (
            remaining
            if p.contribution_strategy == "lump_sum"
            else min(remaining, min(p.contribution_budget, p.wealth) / p.installments)
        )
        amount = min(
            amount,
            max(
                0,
                context.attacker.resources.financial_remaining
                - (p.account_creation_cost if account is None else 0),
            ),
        )
        if account is None:
            return self._bounded(
                context, [self._join(context, 0, amount, p.account_creation_cost, wealth=p.wealth)]
            )
        if (
            amount > 0
            and account.person_id in context.attacker.controlled_supporters
            and account.membership.active
        ):
            return self._bounded(
                context,
                [
                    AttackAction(
                        "contribute",
                        context.attacker.attacker_id,
                        key,
                        amount,
                        data={"amount": amount},
                    )
                ],
            )
        return AttackPlan()


class CoordinatedInfiltration(SyntheticStrategy):
    parameter_model = CoordinatedParameters

    def _number(self, context):
        p = self.parameters
        if p.hostile_share is None:
            return p.number
        honest = sum(not context.state.controlled(a) for a in context.state.accounts.values())
        return min(
            p.number, int(np.ceil(honest * p.hostile_share / max(1e-12, 1 - p.hostile_share)))
        )

    def plan(self, context):
        if not self._ready(context):
            return AttackPlan()
        p = self.parameters
        actions = (
            self._join(context, i, p.contribution, p.account_creation_cost)
            for i in range(self._number(context))
            if context.state.day >= p.start_day + i * p.joining_interval_days
            and f"{context.attacker.attacker_id}:account:{i}" not in context.state.accounts
        )
        return self._bounded(context, actions)


class SybilAttack(SyntheticStrategy):
    parameter_model = SybilParameters

    def plan(self, context):
        if not self._ready(context):
            return AttackPlan()
        p = self.parameters
        return self._bounded(
            context,
            (
                self._join(
                    context,
                    i,
                    p.contribution,
                    p.account_creation_cost + p.verification_cost,
                    fraudulent=True,
                )
                for i in range(p.attempted_identities)
                if f"{context.attacker.attacker_id}:account:{i}" not in context.state.accounts
            ),
        )


class LowTurnoutCapture(SyntheticStrategy):
    parameter_model = LowTurnoutParameters

    def plan(self, context):
        if not self._ready(context):
            return AttackPlan()
        p = self.parameters
        existing = {a.person_id for a in context.state.accounts.values()}
        desired = int(len(existing) * p.hostile_population_share)
        count = max(0, desired - len(context.attacker.controlled_supporters & existing))
        targets = list({a.person_id: a for a in self._targets(context)}.values())[:count]
        return self._bounded(
            context,
            (
                AttackAction(
                    "recruit",
                    context.attacker.attacker_id,
                    a.account_id,
                    p.recruitment_cost,
                    data={"activation_day": p.activation_day, "hostile_turnout": p.hostile_turnout},
                )
                for a in targets
            ),
        )


class VoteInfluence(SyntheticStrategy):
    parameter_model = InfluenceParameters

    def plan(self, context):
        if not self._ready(context):
            return AttackPlan()
        p = self.parameters
        targets = [
            a for a in self._targets(context) if a.account_id not in context.state.overrides
        ][: p.targets]
        susceptibility = np.clip(
            sample_distribution(p.susceptibility_distribution, len(targets), context.rng), 0, 1
        )
        actions = []
        for a, susceptibility_value in zip(targets, susceptibility, strict=True):
            actions.append(
                AttackAction(
                    "influence",
                    context.attacker.attacker_id,
                    a.account_id,
                    p.cost_per_attempt,
                    data={
                        "success": bool(
                            context.rng.random() < p.acceptance_probability * susceptibility_value
                        ),
                        "detected": bool(context.rng.random() < p.detection_probability),
                        "option": context.attacker.objective.get("target", "yes"),
                        "until_day": context.state.day + p.influence_duration_days,
                        "force_turnout": p.force_turnout,
                        "mode": p.mode,
                    },
                )
            )
        return self._bounded(context, actions)


class AccountCompromise(SyntheticStrategy):
    parameter_model = CompromiseParameters

    def plan(self, context):
        if not self._ready(context):
            return AttackPlan()
        p = self.parameters
        next_election = context.attacker.flags.get("next_election_day")
        if (
            next_election is not None
            and next_election - context.state.day > p.time_before_election_days
        ):
            return AttackPlan()
        if p.time_before_election_days == 0 and not context.election_due:
            return AttackPlan()
        actions = []
        for a in self._targets(context)[: p.targets]:
            success = bool(context.rng.random() < p.compromise_probability)
            recovered = bool(context.rng.random() < p.recovery_probability)
            actions.append(
                AttackAction(
                    "compromise",
                    context.attacker.attacker_id,
                    a.account_id,
                    p.cost_per_attempt,
                    data={
                        "success": success,
                        "detected": bool(context.rng.random() < p.detection_probability),
                        "recovery_day": context.state.day + p.recovery_delay_days
                        if recovered
                        else None,
                    },
                )
            )
        return self._bounded(context, actions)


class LongTermInfiltration(CoordinatedInfiltration):
    parameter_model = LongTermParameters

    def plan(self, context):
        if not self._ready(context):
            return AttackPlan()
        p = self.parameters
        actions = []
        allocated = 0.0
        survival = p.retention_probability ** (context.period_days / 30)
        for a in context.state.accounts.values():
            if a.person_id not in context.attacker.controlled_supporters or not a.membership.active:
                continue
            fee = (
                context.membership_fee + p.maintenance_cost * context.period_days / 30
                if context.period_days > 0
                else 0
            )
            if context.rng.random() >= survival or not context.attacker.resources.can_spend(
                allocated + fee, 0
            ):
                actions.append(
                    AttackAction(
                        "expire", context.attacker.attacker_id, a.account_id, operational_cost=0
                    )
                )
            else:
                allocated += fee
                actions.append(
                    AttackAction(
                        "maintain",
                        context.attacker.attacker_id,
                        a.account_id,
                        fee,
                        operational_cost=0,
                        data={
                            "membership_fee": context.membership_fee
                            if context.period_days > 0
                            else 0
                        },
                    )
                )
        # Maintenance has priority over additional recruitment. Nonpayment is enforced centrally.
        actions.extend(super().plan(context).actions)
        return self._bounded(context, actions)


ATTACK_FACTORIES = {
    "wealthy_takeover": WealthyTakeover,
    "coordinated_infiltration": CoordinatedInfiltration,
    "sybil": SybilAttack,
    "low_turnout": LowTurnoutCapture,
    "vote_influence": VoteInfluence,
    "account_compromise": AccountCompromise,
    "long_term_infiltration": LongTermInfiltration,
}
