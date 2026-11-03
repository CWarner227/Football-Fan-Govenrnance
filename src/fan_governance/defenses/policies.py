"""Composable synthetic policies returning proposals without changing simulation state."""

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import ClassVar

from fan_governance.adversarial.base import SimulationContext
from fan_governance.defenses.base import DefenseAction, DefenseEffect


def _number(name: str, value: float, *, probability: bool = False) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{name} must be finite and nonnegative")
    if probability and value > 1:
        raise ValueError(f"{name} must lie in [0, 1]")


def _days(name: str, value: int) -> None:
    _number(name, value)
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")


@dataclass(frozen=True)
class IdentityVerification:
    strength: float = 1.0
    false_acceptance_probability: float = 1.0
    legitimate_rejection_probability: float = 0.0
    verification_cost: float = 0.0
    phase: ClassVar[str] = "identity"

    def __post_init__(self):
        for name in (
            "strength",
            "false_acceptance_probability",
            "legitimate_rejection_probability",
        ):
            _number(name, getattr(self, name), probability=True)
        _number("verification_cost", self.verification_cost)

    def apply(self, context: SimulationContext) -> DefenseEffect:
        actions = []
        for account in context.state.accounts.values():
            claim = account.claim
            if claim.verification_done:
                continue
            probability = (
                (1 - self.strength) * self.false_acceptance_probability
                if claim.fraudulent
                else 1 - self.legitimate_rejection_probability
            )
            accepted = bool(context.rng.random() < probability)
            # False acceptance explicitly creates a mistaken distinct resolved identity.
            resolved = claim.claim_id if claim.fraudulent or self.strength == 0 else claim.person_id
            actions.append(
                DefenseAction(
                    "verify",
                    account.account_id,
                    {
                        "accepted": accepted,
                        "resolved_id": resolved if accepted else None,
                        "fraudulent": claim.fraudulent,
                        "verification_strength": self.strength,
                        "truth_legitimate": not claim.fraudulent,
                    },
                    self.verification_cost,
                )
            )
        return DefenseEffect(actions=tuple(actions))


@dataclass(frozen=True)
class WaitingPeriod:
    days: int = 0
    phase: ClassVar[str] = "governance"

    def __post_init__(self):
        _days("days", self.days)

    def apply(self, context: SimulationContext) -> DefenseEffect:
        return DefenseEffect(waiting_period_days=self.days)


@dataclass(frozen=True)
class VoteCap:
    cap: float
    phase: ClassVar[str] = "governance"

    def __post_init__(self):
        _number("cap", self.cap)

    def apply(self, context: SimulationContext) -> DefenseEffect:
        # The transition layer wraps the existing voting strategy with this bound.
        return DefenseEffect(vote_cap=self.cap)


@dataclass(frozen=True)
class Quorum:
    threshold: float = 0.0
    basis: str = "eligible_members"
    phase: ClassVar[str] = "governance"

    def __post_init__(self):
        _number("threshold", self.threshold, probability=True)
        if self.basis not in ("eligible_members", "eligible_weight"):
            raise ValueError("basis must be eligible_members or eligible_weight")

    def apply(self, context: SimulationContext) -> DefenseEffect:
        return DefenseEffect(quorum=self.threshold, quorum_basis=self.basis)


@dataclass(frozen=True)
class ParticipationIncentive:
    boost: float = 0.0
    success_probability: float = 1.0
    cost_per_member: float = 0.0
    phase: ClassVar[str] = "participation"

    def __post_init__(self):
        _number("boost", self.boost, probability=True)
        _number("success_probability", self.success_probability, probability=True)
        _number("cost_per_member", self.cost_per_member)

    def apply(self, context: SimulationContext) -> DefenseEffect:
        recipients = sum(
            a.membership.active and not a.fraudulent for a in context.state.accounts.values()
        )
        cost = self.cost_per_member * recipients
        successful = context.rng.random() < self.success_probability
        return DefenseEffect(
            actions=(
                DefenseAction(
                    "administrative",
                    "",
                    {"recipients": recipients, "successful": bool(successful)},
                    cost,
                ),
            ),
            turnout_boost=self.boost if successful else 0.0,
        )


_SIGNALS = (
    "joined_volume",
    "contribution_change",
    "credential_replacement",
    "vote_synchronization",
)


@dataclass(frozen=True)
class SuspiciousActivity:
    strength: float = 1.0
    threshold: float = 0.5
    background_false_positive_probability: float = 0.0
    weights: dict[str, float] = field(default_factory=lambda: dict.fromkeys(_SIGNALS, 1.0))
    review_policy: str = "monitor_only"
    confirmation_probability: float = 0.9
    false_confirmation_probability: float = 0.01
    restriction_days: int = 30
    review_cost: float = 0.0
    appeal_probability: float = 0.5
    phase: ClassVar[str] = "review"

    def __post_init__(self):
        for name in (
            "strength",
            "threshold",
            "background_false_positive_probability",
            "confirmation_probability",
            "false_confirmation_probability",
            "appeal_probability",
        ):
            _number(name, getattr(self, name), probability=True)
        _number("review_cost", self.review_cost)
        _days("restriction_days", self.restriction_days)
        if self.review_policy not in (
            "monitor_only",
            "manual_review",
            "temporary_restriction",
            "escalated_verification",
        ):
            raise ValueError("Unknown suspicious-activity review_policy")
        if not isinstance(self.weights, dict) or set(self.weights) - set(_SIGNALS):
            raise ValueError(f"weights must use only {', '.join(_SIGNALS)}")
        for name, weight in self.weights.items():
            _number(f"weights.{name}", weight)
        # Own the configuration mapping instead of retaining a caller-owned object.
        object.__setattr__(self, "weights", dict(self.weights))

    def apply(self, context: SimulationContext) -> DefenseEffect:
        state = context.state
        accounts = state.accounts.values()
        joined = Counter(a.joined_day for a in accounts)
        synchronized = Counter(
            o.option for o in state.overrides.values() if o.until_day >= state.day
        )
        denominator = max(len(state.accounts) - 1, 1)
        total_weight = sum(self.weights.values())
        actions = []
        for account in state.accounts.values():
            override = state.overrides.get(account.account_id) or state.overrides.get(
                account.person_id
            )
            signals = {
                "joined_volume": (joined[account.joined_day] - 1) / denominator,
                "contribution_change": min(
                    1.0,
                    abs(account.membership.contribution - account.last_contribution)
                    / max(abs(account.last_contribution), 1.0),
                ),
                "credential_replacement": min(1.0, account.credential.replacement_count),
                "vote_synchronization": (
                    max(0, synchronized[override.option] - 1) / denominator
                    if override is not None and override.until_day >= state.day
                    else 0.0
                ),
            }
            risk = (
                self.strength
                * sum(self.weights.get(k, 0) * v for k, v in signals.items())
                / total_weight
                if total_weight
                else 0.0
            )
            background_alert = context.rng.random() < self.background_false_positive_probability
            flagged = bool((risk > 0 and risk >= self.threshold) or background_alert)
            # Ground truth is consulted only after scoring, to simulate investigation accuracy.
            malicious = bool(
                account.fraudulent
                or state.controlled(account)
                or state.people[account.person_id].is_adversarial
            )
            confirmed = False
            appeal_success = False
            restricted_until = None
            if flagged and self.review_policy != "monitor_only":
                accuracy = (
                    self.confirmation_probability
                    if malicious
                    else self.false_confirmation_probability
                )
                confirmed = bool(context.rng.random() < accuracy)
                if confirmed and not malicious:
                    appeal_success = bool(context.rng.random() < self.appeal_probability)
                if (
                    confirmed
                    and not appeal_success
                    and self.restriction_days > 0
                    and self.review_policy in ("temporary_restriction", "escalated_verification")
                ):
                    restricted_until = state.day + self.restriction_days
            actions.append(
                DefenseAction(
                    "review",
                    account.account_id,
                    {
                        "risk": risk,
                        "signals": signals,
                        "flagged": flagged,
                        "confirmed": confirmed,
                        "malicious": malicious,
                        "restricted_until": restricted_until,
                        "review_policy": self.review_policy,
                        "appeal_success": appeal_success,
                    },
                    self.review_cost if flagged else 0.0,
                )
            )
        return DefenseEffect(actions=tuple(actions))


DEFENSE_FACTORIES = {
    "identity_verification": IdentityVerification,
    "waiting_period": WaitingPeriod,
    "vote_cap": VoteCap,
    "quorum": Quorum,
    "participation_incentive": ParticipationIncentive,
    "suspicious_activity": SuspiciousActivity,
}
