"""Stable named random streams, independent of strategy order and call order."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RandomStreams:
    seed: int
    trial: int = 0

    def component_seed(self, component: str) -> int:
        payload = f"fan-governance-v1:{self.seed}:{self.trial}:{component}".encode()
        return int.from_bytes(sha256(payload).digest()[:16], "big")

    def generator(self, component: str) -> np.random.Generator:
        """Return a fresh PCG64 generator at this component's initial state."""
        return np.random.Generator(np.random.PCG64(self.component_seed(component)))


@dataclass(frozen=True)
class VotingContext:
    proposal_id: str
    trial_id: int
    seed: int
    proposal_category: str = "club_policy"
    metadata: Mapping[str, Any] = field(default_factory=dict)


def population_component_seeds(streams: RandomStreams) -> dict[str, int]:
    from fan_governance.core.config import ATTRIBUTE_NAMES

    names = [f"population.{name}" for name in ATTRIBUTE_NAMES]
    names += [
        "population.adversarial",
        "population.copula",
        "population.forecast_sample_count",
        "population.forecast_history",
        "population.preferred_policy",
        "population.contribution_fraction",
    ]
    return {name: streams.component_seed(name) for name in names}
