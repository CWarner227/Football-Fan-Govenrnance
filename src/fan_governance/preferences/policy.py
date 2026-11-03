from dataclasses import dataclass

import numpy as np

from fan_governance.agents.models import Supporter
from fan_governance.core.behavior import validate_probability
from fan_governance.core.context import VotingContext
from fan_governance.elections.models import GovernanceProposal
from fan_governance.membership.models import Membership


@dataclass(frozen=True)
class PolicyPreference:
    """Policy alignment controls probability of selecting proposal.options[0].

    metadata.policy_alignment is either a policy label favored by approval, or
    a mapping from supporter policy labels to approval probabilities. Missing
    alignment, unlisted mapping labels and preferred_policy='neutral' use
    neutral_probability. All map entries are validated before sampling.
    """

    alignment_probability: float = 0.9
    mismatch_probability: float = 0.1
    neutral_probability: float = 0.5
    abstention_probability: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "alignment_probability",
            "mismatch_probability",
            "neutral_probability",
            "abstention_probability",
        ):
            validate_probability(getattr(self, name), name)

    def choose(
        self,
        supporter: Supporter,
        membership: Membership,
        proposal: GovernanceProposal,
        context: VotingContext,
        rng: np.random.Generator,
    ) -> str | None:
        alignment = proposal.metadata.get("policy_alignment")
        if isinstance(alignment, dict):
            for label, probability in alignment.items():
                if not isinstance(label, str) or not label:
                    raise ValueError("Policy alignment keys must be nonempty policy labels")
                validate_probability(probability, f"policy_alignment[{label}]")
        elif alignment is not None and (not isinstance(alignment, str) or not alignment):
            raise ValueError("policy_alignment must be a policy label or probability mapping")

        preferred = supporter.preferred_policy
        probability = self.neutral_probability
        if alignment is not None and preferred != "neutral":
            if isinstance(alignment, dict):
                probability = alignment.get(preferred, self.neutral_probability)
            else:
                probability = (
                    self.alignment_probability
                    if preferred == alignment
                    else self.mismatch_probability
                )
        abstention, preference = rng.random(2)
        if abstention < self.abstention_probability:
            return None
        return proposal.options[0 if preference < probability else 1]
