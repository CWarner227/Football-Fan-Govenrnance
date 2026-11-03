from dataclasses import dataclass

import numpy as np

from fan_governance.agents.models import Supporter
from fan_governance.core.behavior import AttributeBehavior
from fan_governance.core.context import VotingContext
from fan_governance.membership.models import Membership


@dataclass(frozen=True)
class AttributeBasedParticipation(AttributeBehavior):
    def participates(
        self,
        supporter: Supporter,
        membership: Membership,
        context: VotingContext,
        rng: np.random.Generator,
    ) -> bool:
        return bool(rng.random() < self.probability_for(supporter))
