from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field

from fan_governance.core.config import GovernanceConfig, ModelSpec, ProposalConfig, ValidatedModel


class GovernanceProposal(ProposalConfig):
    quorum: float = Field(default=0.2, ge=0, le=1)
    approval_threshold: float = Field(default=0.5, ge=0, le=1)
    quorum_basis: Literal["eligible_members", "eligible_weight"] = "eligible_members"
    eligibility_rules: GovernanceConfig = Field(default_factory=GovernanceConfig)
    voting_method: ModelSpec | None = Field(default_factory=lambda: ModelSpec(name="equal"))


@dataclass(frozen=True)
class ElectionData:
    options: tuple[str, ...]
    eligible_weights: tuple[float, ...]
    cast_weights: tuple[float, ...]
    cast_options: tuple[str, ...]
    abstentions: int
    invalid_ballots: int
    eligible_identities: tuple[str, ...] = ()
    eligible_wealth: tuple[float, ...] = ()
    eligible_contributions: tuple[float, ...] = ()
    cast_identities: tuple[str, ...] = ()
    population_size: int = 0
    active_member_count: int = 0
    approval_threshold: float = 0.5
    quorum: float = 0.2
    quorum_basis: Literal["eligible_members", "eligible_weight"] = "eligible_members"


class SimulationResult(ValidatedModel):
    experiment_id: str
    scenario_id: str
    trial_id: int
    random_seed: int
    component_seeds: dict[str, int]
    configuration: dict[str, Any]
    governance_configuration: dict[str, Any]
    voting_model: str
    population_size: int
    eligible_voter_count: int
    votes_cast: int
    turnout: float | None
    vote_totals: dict[str, float]
    winning_option: str | None
    approval_achieved: bool
    quorum_achieved: bool
    passed: bool
    metrics: dict[str, Any]
    execution_metadata: dict[str, Any]
