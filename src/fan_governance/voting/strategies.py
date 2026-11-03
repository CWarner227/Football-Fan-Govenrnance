"""Weights use the canonical membership contribution; eligibility is external."""

import math
from dataclasses import dataclass, field

from fan_governance.agents.models import Supporter
from fan_governance.core.context import VotingContext
from fan_governance.membership.models import Membership


def _nonnegative_finite(value: float, name: str) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")


def _positive_finite(value: float, name: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


def _validated_weight(weight: float) -> float:
    _nonnegative_finite(weight, "Voting weight")
    return weight


def _log1p_ratio(contribution: float, reference: float) -> float:
    """Natural logarithm without overflowing the intermediate ratio."""
    _nonnegative_finite(contribution, "contribution")
    if contribution <= reference:
        return math.log1p(contribution / reference)
    return math.log(contribution) - math.log(reference) + math.log1p(reference / contribution)


@dataclass(frozen=True)
class EqualVoting:
    def calculate_weight(
        self, supporter: Supporter, membership: Membership, context: VotingContext
    ) -> float:
        return 1.0


@dataclass(frozen=True)
class ProportionalVoting:
    """Zero-contribution members have zero weight; default preserves Phase 1 units."""

    reference_contribution: float = 1.0

    def __post_init__(self) -> None:
        _positive_finite(self.reference_contribution, "reference_contribution")

    def calculate_weight(
        self, supporter: Supporter, membership: Membership, context: VotingContext
    ) -> float:
        return _validated_weight(membership.contribution / self.reference_contribution)


@dataclass(frozen=True)
class CappedVoting:
    """The legacy ``cap`` alias remains supported; ``max_weight`` takes precedence."""

    cap: float = 100.0
    max_weight: float | None = field(default=None, kw_only=True)
    base_weight: float = field(default=0.0, kw_only=True)
    reference_contribution: float = field(default=1.0, kw_only=True)

    def __post_init__(self) -> None:
        _positive_finite(self.cap, "cap")
        _nonnegative_finite(self.base_weight, "base_weight")
        _positive_finite(self.reference_contribution, "reference_contribution")
        if self.max_weight is not None:
            _nonnegative_finite(self.max_weight, "max_weight")
        if self.effective_cap < self.base_weight:
            raise ValueError("cap must not be below base_weight")

    @property
    def effective_cap(self) -> float:
        return self.cap if self.max_weight is None else self.max_weight

    def calculate_weight(
        self, supporter: Supporter, membership: Membership, context: VotingContext
    ) -> float:
        _nonnegative_finite(membership.contribution, "contribution")
        return _validated_weight(
            min(
                self.effective_cap,
                self.base_weight + membership.contribution / self.reference_contribution,
            )
        )


@dataclass(frozen=True)
class DiminishingVoting:
    """Legacy natural-log formula unless a Phase 2 parameter is supplied.

    Supplying reference_contribution, base_weight, or max_weight selects the
    base + log2(1 + contribution/reference) formula. Its omitted values are
    reference=1, base=1, cap=5. Scale and multiplier govern only the legacy form.
    """

    scale: float = 10.0
    multiplier: float = 1.0
    reference_contribution: float | None = field(default=None, kw_only=True)
    base_weight: float | None = field(default=None, kw_only=True)
    max_weight: float | None = field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        _positive_finite(self.scale, "scale")
        _positive_finite(self.multiplier, "multiplier")
        if self.phase2:
            reference = 1.0 if self.reference_contribution is None else self.reference_contribution
            base = 1.0 if self.base_weight is None else self.base_weight
            cap = 5.0 if self.max_weight is None else self.max_weight
            _positive_finite(reference, "reference_contribution")
            _nonnegative_finite(base, "base_weight")
            _nonnegative_finite(cap, "max_weight")
            if cap < base:
                raise ValueError("max_weight must not be below base_weight")
            object.__setattr__(self, "reference_contribution", reference)
            object.__setattr__(self, "base_weight", base)
            object.__setattr__(self, "max_weight", cap)

    @property
    def phase2(self) -> bool:
        return any(
            value is not None
            for value in (self.reference_contribution, self.base_weight, self.max_weight)
        )

    def calculate_weight(
        self, supporter: Supporter, membership: Membership, context: VotingContext
    ) -> float:
        if self.phase2:
            logarithm = _log1p_ratio(membership.contribution, self.reference_contribution)
            return _validated_weight(
                min(self.max_weight, self.base_weight + logarithm / math.log(2))
            )
        logarithm = _log1p_ratio(membership.contribution, self.scale)
        return _validated_weight(self.multiplier * logarithm)
