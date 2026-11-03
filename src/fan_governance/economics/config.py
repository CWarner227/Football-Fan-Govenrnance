"""Validated synthetic monthly financial assumptions, independent of voting models."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from fan_governance.core.config import (
    DistributionConfig,
    Nonnegative,
    Probability,
    ValidatedModel,
)


class InvestorSpec(ValidatedModel):
    investor_id: str = Field(min_length=1)
    capital: Nonnegative
    start_month: int = Field(default=0, ge=0)
    ownership_share: Probability = 0
    voting_rights: bool = False
    minimum_voting_power_share: Probability = 0
    willingness: Probability = 1


class ShockSpec(ValidatedModel):
    name: Literal["revenue_loss", "poor_recruitment", "stadium_closure", "economic_downturn"]
    shock_id: str | None = None
    start_month: int = Field(default=0, ge=0)
    duration_months: int = Field(default=1, ge=1)
    severity: Probability = 0.5
    recovery_months: int = Field(default=0, ge=0)
    keep_operating_costs: bool = True


class EconomicConfig(ValidatedModel):
    enabled: bool = True
    record_individual_transactions: bool = False
    income_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(
            type="lognormal",
            parameters={"mean": 7.8, "sigma": 0.6},
            lower=0,
        )
    )
    disposable_income_fraction: Probability = 0.2
    income_wealth_correlation: Annotated[float, Field(ge=-1, le=1)] | None = None
    starting_cash: Nonnegative = 100000
    operating_revenue: Nonnegative = 10000
    operating_expenses: Nonnegative = 5000
    wages: Nonnegative = 3000
    transfer_spending: Nonnegative = 0
    debt_principal: Nonnegative = 0
    debt_repayment: Nonnegative = 0
    debt_interest: Nonnegative = 0
    membership_fee: Nonnegative = 0
    renewal_probability: Probability = 1
    contribution_willingness: Probability = 0
    renewal_interval_months: int = Field(default=12, ge=1)
    membership_growth_rate: Probability = 0
    admin_cost_per_member: Nonnegative = 0
    squad_quality: Nonnegative = 1
    recruitment_effectiveness: Nonnegative = 1
    management_quality: Nonnegative = 1
    injury_rate: Probability = 0.05
    sporting_volatility: Nonnegative = 0.1
    sporting_revenue_sensitivity: Nonnegative = 0.1
    matchday_revenue_fraction: Probability = 0.5
    investors: list[InvestorSpec] = Field(default_factory=list)
    investor_voting_offer: bool = False
    investor_voting_power_share: Probability = 0
    investor_policy_factor: Probability = 1
    shocks: list[ShockSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_financial_policies(self) -> Self:
        ids = [investor.investor_id for investor in self.investors]
        if len(ids) != len(set(ids)):
            raise ValueError("Investor IDs must be unique")
        if sum(investor.ownership_share for investor in self.investors) > 1 + 1e-12:
            raise ValueError("Investor ownership shares must sum to at most one")
        keys = [s.shock_id or f"{s.name}:{s.start_month}" for s in self.shocks]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate shocks require distinct shock_id values")
        if self.income_distribution.type == "categorical":
            raise ValueError("Income requires a numeric distribution")
        if self.income_distribution.type not in {
            "uniform",
            "normal",
            "lognormal",
            "beta",
            "constant",
        }:
            raise ValueError("Unsupported income distribution")
        return self
