"""Structural contracts for injection; implementations need no inheritance."""

from collections.abc import Sequence
from typing import Any, Protocol

import numpy as np

from fan_governance.agents.generator import Population
from fan_governance.agents.models import Supporter
from fan_governance.core.config import PopulationConfig
from fan_governance.core.context import RandomStreams, VotingContext
from fan_governance.elections.models import ElectionData, GovernanceProposal
from fan_governance.membership.models import Membership


class PopulationGenerator(Protocol):
    def generate(self, config: PopulationConfig, streams: RandomStreams) -> Population: ...


class VotingStrategy(Protocol):
    def calculate_weight(
        self, supporter: Supporter, membership: Membership, context: VotingContext
    ) -> float: ...


class EligibilityPolicy(Protocol):
    def eligible(
        self, supporters: Sequence[Supporter], memberships: Sequence[Membership]
    ) -> Sequence[Membership]: ...


class ParticipationModel(Protocol):
    def participates(
        self,
        supporter: Supporter,
        membership: Membership,
        context: VotingContext,
        rng: np.random.Generator,
    ) -> bool: ...


class PreferenceModel(Protocol):
    def choose(
        self,
        supporter: Supporter,
        membership: Membership,
        proposal: GovernanceProposal,
        context: VotingContext,
        rng: np.random.Generator,
    ) -> str | None: ...


class MetricCalculator(Protocol):
    def calculate(self, data: ElectionData) -> dict[str, Any]: ...
