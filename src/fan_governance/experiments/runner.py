"""Sequential batch execution with paired populations and ballot realizations."""

import json
import platform
from collections.abc import Callable, Iterator
from hashlib import sha256
from itertools import product
from time import perf_counter

import numpy as np
import pandas as pd
import pydantic

from fan_governance import __version__
from fan_governance.agents.generator import SyntheticPopulationGenerator
from fan_governance.clubs.models import Club
from fan_governance.core.config import SimulationConfig
from fan_governance.core.context import RandomStreams, population_component_seeds
from fan_governance.core.engine import effective_voting_specs, proposal_from_config
from fan_governance.core.interfaces import MetricCalculator, PopulationGenerator
from fan_governance.core.registry import ModelRegistry, default_registry
from fan_governance.elections.models import SimulationResult
from fan_governance.elections.runner import ElectionRunner
from fan_governance.metrics.results import StandardMetrics


def scenarios(config: SimulationConfig) -> Iterator[tuple[str, SimulationConfig]]:
    experiment = config.experiment
    axes = product(
        experiment.population_sizes or [config.population.size],
        experiment.waiting_periods or [config.governance.waiting_period_days],
        experiment.participation_levels if experiment.participation_levels is not None else [None],
        experiment.wealth_distributions or [config.population.wealth_distribution],
        list(experiment.population_profiles.items())
        if experiment.population_profiles
        else [("default", config.population)],
        experiment.participation_models or [config.participation],
        experiment.proposal_categories or [config.proposal.category],
    )
    for size, waiting, probability, wealth, (
        profile_name,
        profile,
    ), participation, category in axes:
        scenario = config.model_copy(deep=True)
        if experiment.population_profiles:
            scenario.population = profile.model_copy(deep=True)
        else:
            scenario.population.size = size
            scenario.population.wealth_distribution = wealth
        scenario.governance.waiting_period_days = waiting
        if experiment.waiting_periods and scenario.proposal.waiting_period_days is not None:
            scenario.proposal.waiting_period_days = waiting
        scenario.participation = participation.model_copy(deep=True)
        scenario.proposal.category = category
        if probability is not None:
            scenario.participation.parameters = scenario.participation.parameters | {
                "probability": probability
            }
        key = json.dumps(
            [
                profile_name,
                scenario.population.model_dump(mode="json"),
                waiting,
                scenario.participation.model_dump(),
                scenario.proposal.model_dump(mode="json"),
            ],
            sort_keys=True,
        )
        yield sha256(key.encode()).hexdigest()[:16], scenario


class ExperimentRunner:
    def __init__(
        self,
        *,
        registry: ModelRegistry | None = None,
        population_generator: PopulationGenerator | None = None,
        metrics: MetricCalculator | None = None,
    ) -> None:
        self.registry = registry if registry is not None else default_registry()
        self.population_generator = (
            population_generator
            if population_generator is not None
            else SyntheticPopulationGenerator()
        )
        self.metrics = metrics if metrics is not None else StandardMetrics()
        self.elapsed_seconds = 0.0

    def components(self, config: SimulationConfig) -> list[tuple[str, ElectionRunner]]:
        proposal = proposal_from_config(config)
        eligibility = self.registry.create(
            "eligibility",
            proposal.eligibility_rules.eligibility,
            waiting_period_days=proposal.eligibility_rules.waiting_period_days,
        )
        participation = self.registry.create("participation", config.participation)
        preference = self.registry.create("preference", config.preference)
        specs = effective_voting_specs(config)
        return [
            (
                spec.name,
                ElectionRunner(
                    self.registry.create("voting", spec),
                    eligibility,
                    participation,
                    preference,
                    self.metrics,
                ),
            )
            for spec in specs
        ]

    def run(
        self, config: SimulationConfig, *, progress: Callable[[str, int, int], None] | None = None
    ) -> list[SimulationResult]:
        started = perf_counter()
        results = []
        # Validate all factories before running the first potentially expensive trial.
        for _, scenario in scenarios(config):
            self.components(scenario)
        versions = {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "pydantic": pydantic.__version__,
            "fan_governance": __version__,
            "rng": "PCG64",
            "stream_scheme": "sha256-v1",
        }
        from fan_governance.output.provenance import source_provenance

        versions.update(source_provenance())
        for scenario_id, scenario in scenarios(config):
            components = self.components(scenario)
            recorded = scenario.model_dump(mode="json")
            # Canonical order makes the scientific record independent of execution order.
            recorded["voting"]["strategies"] = sorted(
                [spec.model_dump() for spec in scenario.voting.specs()], key=lambda s: s["name"]
            )
            for trial in range(config.experiment.trials):
                trial_started = perf_counter()
                streams = RandomStreams(config.experiment.seed, trial)
                population_streams = RandomStreams(
                    scenario.population.seed
                    if scenario.population.seed is not None
                    else streams.seed,
                    trial,
                )
                population = self.population_generator.generate(
                    scenario.population, population_streams
                )
                club = Club(
                    club_id="synthetic-club",
                    name="Synthetic Football Club",
                    supporters=population.supporters,
                    memberships=population.memberships,
                    governance=scenario.governance,
                )
                proposal = proposal_from_config(scenario)
                snapshot = components[0][1].prepare(club, proposal, streams)
                preparation_seconds = perf_counter() - trial_started
                for name, election in components:
                    result = election.run(
                        club,
                        proposal,
                        streams,
                        snapshot=snapshot,
                        experiment_id=config.experiment.name,
                        scenario_id=scenario_id,
                        voting_model=name,
                        configuration=recorded,
                    )
                    result.execution_metadata.update(
                        versions | {"shared_preparation_seconds": preparation_seconds}
                    )
                    result.component_seeds.update(population_component_seeds(population_streams))
                    results.append(result)
                if progress is not None:
                    progress(scenario_id, trial + 1, config.experiment.trials)
        self.elapsed_seconds = perf_counter() - started
        return results
