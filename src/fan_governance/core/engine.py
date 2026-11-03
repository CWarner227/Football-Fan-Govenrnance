"""Small standalone orchestration facade with injected generation and election models."""

from dataclasses import dataclass

from fan_governance.clubs.models import Club
from fan_governance.core.config import ModelSpec, SimulationConfig
from fan_governance.core.context import RandomStreams, population_component_seeds
from fan_governance.core.interfaces import PopulationGenerator
from fan_governance.elections.models import GovernanceProposal, SimulationResult
from fan_governance.elections.runner import ElectionRunner


def effective_voting_specs(config: SimulationConfig) -> list[ModelSpec]:
    override = config.proposal.voting_strategy
    if override is None:
        return config.voting.specs()
    return [ModelSpec(name=override) if isinstance(override, str) else override]


def proposal_from_config(config: SimulationConfig) -> GovernanceProposal:
    governance = config.governance.model_copy(deep=True)
    for name in ("quorum", "approval_threshold", "waiting_period_days"):
        override = getattr(config.proposal, name)
        if override is not None:
            setattr(governance, name, override)
    if config.proposal.eligibility is not None:
        governance.eligibility = config.proposal.eligibility
    raw = config.proposal.model_dump(exclude_none=True)
    raw.update(
        quorum=governance.quorum,
        approval_threshold=governance.approval_threshold,
        quorum_basis=governance.quorum_basis,
        eligibility_rules=governance,
        voting_method=effective_voting_specs(config)[0],
    )
    return GovernanceProposal.model_validate(raw)


@dataclass
class SimulationEngine:
    population_generator: PopulationGenerator
    election_runner: ElectionRunner

    def run(self, config: SimulationConfig, trial_id: int = 0) -> SimulationResult:
        streams = RandomStreams(config.experiment.seed, trial_id)
        population_streams = RandomStreams(
            config.population.seed if config.population.seed is not None else streams.seed, trial_id
        )
        population = self.population_generator.generate(config.population, population_streams)
        club = Club(
            club_id="synthetic-club",
            name="Synthetic Football Club",
            supporters=population.supporters,
            memberships=population.memberships,
            governance=config.governance,
        )
        result = self.election_runner.run(
            club,
            proposal_from_config(config),
            streams,
            experiment_id=config.experiment.name,
            voting_model=effective_voting_specs(config)[0].name,
            configuration=config.model_dump(mode="json"),
        )
        result.component_seeds.update(population_component_seeds(population_streams))
        return result
