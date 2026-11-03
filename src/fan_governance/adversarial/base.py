"""Synthetic actors and immutable transition proposals; never real-world operations."""

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

if TYPE_CHECKING:
    from fan_governance.scenarios.state import SimulationState


@dataclass
class Resources:
    financial_budget: float
    operational_budget: int
    financial_remaining: float = field(init=False)
    operational_remaining: int = field(init=False)

    def __post_init__(self):
        if (
            isinstance(self.financial_budget, bool)
            or not isinstance(self.financial_budget, (int, float))
            or not math.isfinite(self.financial_budget)
            or self.financial_budget < 0
            or type(self.operational_budget) is not int
            or self.operational_budget < 0
        ):
            raise ValueError("Attacker budgets must be finite and nonnegative")
        self.financial_remaining = self.financial_budget
        self.operational_remaining = self.operational_budget

    def can_spend(self, financial: float, operations: int = 1) -> bool:
        if (
            isinstance(financial, bool)
            or not isinstance(financial, (int, float))
            or not math.isfinite(financial)
            or financial < 0
            or type(operations) is not int
            or operations < 0
        ):
            raise ValueError("Resource costs must be finite and nonnegative")
        return financial <= self.financial_remaining and operations <= self.operational_remaining

    def spend(self, financial: float, operations: int = 1) -> None:
        if not self.can_spend(financial, operations):
            raise ValueError("Insufficient attacker resources")
        self.financial_remaining = max(0.0, self.financial_remaining - financial)
        self.operational_remaining -= operations

    @property
    def financial_spent(self) -> float:
        return self.financial_budget - self.financial_remaining


@dataclass
class Attacker:
    attacker_id: str
    attacker_type: str
    objective: dict[str, Any]
    resources: Resources
    coordination_level: float = 1.0
    risk_tolerance: float = 0.5
    time_horizon: int = 1095
    controlled_supporters: set[str] = field(default_factory=set)
    controlled_credentials: set[str] = field(default_factory=set)
    flags: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AttackAction:
    kind: str
    actor_id: str
    target_id: str = ""
    financial_cost: float = 0.0
    operational_cost: int = 1
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AttackPlan:
    actions: tuple[AttackAction, ...] = ()


@dataclass(frozen=True)
class AttackOutcome:
    actions: tuple[AttackAction, ...] = ()


@dataclass(frozen=True)
class SimulationContext:
    state: "SimulationState"
    rng: np.random.Generator
    attacker: Attacker | None = None
    period_days: int = 30
    election_due: bool = False
    membership_fee: float = 0.0
    waiting_period_days: int = 0


class AdversarialStrategy(Protocol):
    def plan(self, context: SimulationContext) -> AttackPlan: ...
    def execute(self, plan: AttackPlan, context: SimulationContext) -> AttackOutcome: ...
