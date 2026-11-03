import math
from dataclasses import dataclass

import numpy as np

from fan_governance.agents.models import Supporter
from fan_governance.core.context import VotingContext
from fan_governance.elections.models import GovernanceProposal
from fan_governance.membership.models import Membership


@dataclass(frozen=True)
class SyntheticPreference:
    approval_probability: float = 0.5
    abstention_probability: float = 0.0

    def __post_init__(self) -> None:
        if any(
            not math.isfinite(v) or not 0 <= v <= 1
            for v in (self.approval_probability, self.abstention_probability)
        ):
            raise ValueError("Preference probabilities must be in [0,1]")

    def choose(
        self,
        supporter: Supporter,
        membership: Membership,
        proposal: GovernanceProposal,
        context: VotingContext,
        rng: np.random.Generator,
    ) -> str | None:
        # Always draw both variates so changing abstention doesn't shift preferences.
        abstention, preference = rng.random(2)
        if abstention < self.abstention_probability:
            return None
        return proposal.options[0 if preference < self.approval_probability else 1]
