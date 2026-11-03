"""Policies propose effects; the scenario transition layer commits them."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from fan_governance.adversarial.base import SimulationContext


@dataclass(frozen=True)
class DefenseAction:
    kind: str
    target_id: str
    data: dict[str, Any] = field(default_factory=dict)
    administrative_cost: float = 0.0


@dataclass(frozen=True)
class DefenseEffect:
    actions: tuple[DefenseAction, ...] = ()
    waiting_period_days: int | None = None
    vote_cap: float | None = None
    quorum: float | None = None
    quorum_basis: str | None = None
    turnout_boost: float = 0.0


class DefensivePolicy(Protocol):
    phase: str

    def apply(self, context: SimulationContext) -> DefenseEffect: ...
