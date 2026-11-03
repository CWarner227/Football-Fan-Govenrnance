"""Economic stocks and cumulative cash-flow ledger; monetary values are synthetic."""

from dataclasses import dataclass, field


@dataclass
class EconomicState:
    cash: float
    debt: float
    supporter_income: dict[str, float] = field(default_factory=dict)
    supporter_cash: dict[str, float] = field(default_factory=dict)
    supporter_disposable_income: dict[str, float] = field(default_factory=dict)
    supporter_affordability: dict[str, bool] = field(default_factory=dict)
    next_renewal_day: dict[str, int] = field(default_factory=dict)
    investor_funding: dict[str, float] = field(default_factory=dict)
    investor_ownership: dict[str, float] = field(default_factory=dict)
    investor_voting_rights: set[str] = field(default_factory=set)
    investors_considered: set[str] = field(default_factory=set)
    # A scenario adapter may fill actual offered shares before the funding decision.
    offered_voting_power_share: dict[str, float] = field(default_factory=dict)
    ledger: list[dict] = field(default_factory=list)
    cumulative_ledger: dict[str, float] = field(default_factory=dict)
    last_month: int | None = None
    last_day: int | None = None
    initial_member_count: int | None = None
    squad_value: float = 0

    @property
    def cumulative_profit(self) -> float:
        return self.cumulative_ledger.get("profit", 0.0)
