"""Experimental weighting from observed (possibly synthetic) forecast histories.

This is not a measure of real-world supporter expertise or decision quality.
Latent knowledge and raw forecast accuracy never substitute for observed counts.
"""

import math
from dataclasses import dataclass

from fan_governance.agents.models import Supporter
from fan_governance.core.context import VotingContext
from fan_governance.membership.models import Membership
from fan_governance.voting.strategies import (
    _nonnegative_finite,
    _positive_finite,
    _validated_weight,
)


@dataclass(frozen=True)
class ExpertiseVoting:
    expertise_multiplier: float = 1.0
    minimum_samples: int = 20
    max_weight: float | None = None
    confidence_z: float = 1.96
    chance_accuracy: float = 0.5

    def __post_init__(self) -> None:
        _nonnegative_finite(self.expertise_multiplier, "expertise_multiplier")
        if (
            isinstance(self.minimum_samples, bool)
            or not isinstance(self.minimum_samples, int)
            or self.minimum_samples < 1
        ):
            raise ValueError("minimum_samples must be a positive integer")
        _positive_finite(self.confidence_z, "confidence_z")
        _nonnegative_finite(self.chance_accuracy, "chance_accuracy")
        if self.chance_accuracy >= 1:
            raise ValueError("chance_accuracy must be below 1")
        if self.max_weight is not None:
            _nonnegative_finite(self.max_weight, "max_weight")
            if self.max_weight < 1:
                raise ValueError("max_weight must not be below neutral weight 1")

    def reliability_score(self, supporter: Supporter) -> float:
        count = getattr(supporter, "forecast_sample_count", 0)
        correct = getattr(supporter, "forecast_correct_count", None)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("forecast_sample_count must be a nonnegative integer")
        if correct is not None and (
            isinstance(correct, bool) or not isinstance(correct, int) or not 0 <= correct <= count
        ):
            raise ValueError("forecast_correct_count must be an integer between 0 and sample count")
        if correct is None or count < self.minimum_samples:
            return 0.0
        proportion = correct / count
        z_over_root_n = self.confidence_z / math.sqrt(count)
        if proportion == 0 or z_over_root_n > 1e150:
            return 0.0
        # Rationalized Wilson lower bound avoids subtracting nearly equal terms.
        t_squared = z_over_root_n * z_over_root_n
        denominator = (
            proportion
            + t_squared / 2
            + z_over_root_n * math.sqrt(proportion * (1 - proportion) + t_squared / 4)
        )
        lower = proportion * proportion / denominator
        return min(1.0, max(0.0, (lower - self.chance_accuracy) / (1 - self.chance_accuracy)))

    def calculate_weight(
        self, supporter: Supporter, membership: Membership, context: VotingContext
    ) -> float:
        weight = 1.0 + self.expertise_multiplier * self.reliability_score(supporter)
        if self.max_weight is not None:
            weight = min(self.max_weight, weight)
        return _validated_weight(weight)
