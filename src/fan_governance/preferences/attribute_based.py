from dataclasses import dataclass

import numpy as np

from fan_governance.agents.models import Supporter
from fan_governance.core.behavior import AttributeBehavior, validate_probability
from fan_governance.core.context import VotingContext
from fan_governance.elections.models import GovernanceProposal
from fan_governance.membership.models import Membership


@dataclass(frozen=True)
class AttributeBasedPreference(AttributeBehavior):
    abstention_probability: float = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_probability(self.abstention_probability, "abstention_probability")

    def choose(
        self,
        supporter: Supporter,
        membership: Membership,
        proposal: GovernanceProposal,
        context: VotingContext,
        rng: np.random.Generator,
    ) -> str | None:
        probability = self.probability_for(supporter)
        abstention, preference = rng.random(2)
        if abstention < self.abstention_probability:
            return None
        return proposal.options[0 if preference < probability else 1]
