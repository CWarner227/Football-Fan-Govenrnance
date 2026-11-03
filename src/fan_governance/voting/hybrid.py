"""Proposal-category routing over injected voting strategies."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from fan_governance.agents.models import Supporter
from fan_governance.core.context import VotingContext
from fan_governance.membership.models import Membership
from fan_governance.voting.strategies import _validated_weight

if TYPE_CHECKING:
    from fan_governance.core.interfaces import VotingStrategy


@dataclass(frozen=True)
class HybridVoting:
    default_strategy: "VotingStrategy"
    proposal_rules: Mapping[str, "VotingStrategy"]

    def __post_init__(self) -> None:
        rules = dict(self.proposal_rules)
        if any(not isinstance(category, str) or not category for category in rules):
            raise ValueError("proposal rule categories must be nonempty strings")
        for strategy in (self.default_strategy, *rules.values()):
            if not callable(getattr(strategy, "calculate_weight", None)):
                raise ValueError("hybrid delegates must implement calculate_weight")
        object.__setattr__(self, "proposal_rules", MappingProxyType(rules))

    def calculate_weight(
        self, supporter: Supporter, membership: Membership, context: VotingContext
    ) -> float:
        strategy = self.proposal_rules.get(context.proposal_category, self.default_strategy)
        return _validated_weight(strategy.calculate_weight(supporter, membership, context))
