"""Shared helpers for explicitly synthetic behavioral assumptions."""

import math
from dataclasses import dataclass, field
from numbers import Real

from fan_governance.agents.models import Supporter

NUMERIC_SUPPORTER_ATTRIBUTES = frozenset(
    {
        "wealth",
        "contribution",
        "loyalty",
        "knowledge",
        "knowledge_score",
        "membership_age_days",
        "participation_probability",
        "participation_rate",
        "forecast_accuracy",
    }
)


def finite_number(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def validate_probability(value: float, name: str) -> None:
    if not 0 <= finite_number(value, name) <= 1:
        raise ValueError(f"{name} must be in [0,1]")


def supporter_attribute(supporter: Supporter, name: str) -> float:
    """Read only approved numeric traits; absent forecast accuracy is neutral 0.5."""
    if name not in NUMERIC_SUPPORTER_ATTRIBUTES:
        raise ValueError(f"Unsupported behavioral attribute: {name}")
    aliases = {"knowledge_score": "knowledge", "participation_rate": "participation_probability"}
    value = getattr(supporter, name, None)
    if value is None and name in aliases:
        value = getattr(supporter, aliases[name])
    if value is None and name == "forecast_accuracy":
        value = 0.5
    return finite_number(value, name)


def logistic(value: float) -> float:
    """Stable sigmoid, including saturation for overflowed finite-input products."""
    if math.isnan(value):
        raise ValueError("Behavioral linear predictor is undefined")
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1 + exponential)


@dataclass(frozen=True)
class AttributeBehavior:
    """logistic(intercept + sum(coefficient * attribute / scale)).

    Scales default to 1. Missing optional forecast_accuracy defaults to 0.5;
    knowledge_score and participation_rate alias their Phase 1 field names.
    Coefficients are research assumptions, without an empirical interpretation.
    """

    intercept: float = 0.0
    coefficients: dict[str, float] = field(default_factory=dict)
    scales: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        finite_number(self.intercept, "intercept")
        for name, coefficient in self.coefficients.items():
            if name not in NUMERIC_SUPPORTER_ATTRIBUTES:
                raise ValueError(f"Unsupported behavioral attribute: {name}")
            finite_number(coefficient, f"coefficient {name}")
        for name, scale in self.scales.items():
            if name not in NUMERIC_SUPPORTER_ATTRIBUTES:
                raise ValueError(f"Unsupported behavioral attribute: {name}")
            if finite_number(scale, f"scale {name}") <= 0:
                raise ValueError("Behavioral scales must be positive")
        object.__setattr__(self, "coefficients", dict(self.coefficients))
        object.__setattr__(self, "scales", dict(self.scales))

    def probability_for(self, supporter: Supporter) -> float:
        predictor = self.intercept
        for name, coefficient in self.coefficients.items():
            predictor += coefficient * (
                supporter_attribute(supporter, name) / self.scales.get(name, 1.0)
            )
        return logistic(predictor)
