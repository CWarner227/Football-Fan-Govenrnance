import math
from dataclasses import dataclass

import numpy as np

from fan_governance.agents.models import Supporter
from fan_governance.core.context import VotingContext
from fan_governance.membership.models import Membership


@dataclass(frozen=True)
class ProbabilisticParticipation:
    probability: float | None = None

    def __post_init__(self) -> None:
        if self.probability is not None and (
            not math.isfinite(self.probability) or not 0 <= self.probability <= 1
        ):
            raise ValueError("probability must be in [0,1]")

    def participates(
        self,
        supporter: Supporter,
        membership: Membership,
        context: VotingContext,
        rng: np.random.Generator,
    ) -> bool:
        probability = (
            supporter.participation_probability if self.probability is None else self.probability
        )
        return bool(rng.random() < probability)


@dataclass(frozen=True)
class ConstantParticipation(ProbabilisticParticipation):
    probability: float = 0.6

    def __post_init__(self) -> None:
        if self.probability is None:
            raise ValueError("Constant participation requires a common probability")
        super().__post_init__()
