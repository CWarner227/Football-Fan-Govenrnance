"""Authoritative engine-factory validation and bounded local research workloads."""

from math import ceil, exp, prod

from pydantic import TypeAdapter

from fan_governance.adversarial.objectives import evaluate_objective
from fan_governance.core.config import ModelSpec
from fan_governance.core.engine import effective_voting_specs, proposal_from_config
from fan_governance.core.registry import default_registry
from fan_governance.lifecycle.clock import SimulationClock
from fan_governance.scenarios.config import ScenarioConfig
from fan_governance.scenarios.registry import default_scenario_registry
from fan_governance.scenarios.runner import expanded_configs

LIMITS = {
    "max_population": 100000,
    "max_trials": 1000,
    "max_grid_cells": 256,
    "max_work_units": 300000000,
    "max_concurrent_runs": 1,
    "timeout_seconds": 1800,
}


def _construct(registry, category, spec, **defaults):
    # Dataclass constructors do not enforce annotations, so validate their declared schema too.
    from fan_governance.api.catalog import parameter_model

    factory = registry.factories().get(category, {}).get(spec.name)
    if factory is None:
        return registry.create(
            category, spec, **defaults
        )  # Engine's informative unknown-name error.
    parameters = parameter_model(factory).model_validate(spec.parameters)
    if category == "voting" and spec.name == "hybrid":
        nested = [parameters.default_strategy, *(parameters.proposal_rules or {}).values()]
        for routed in nested:
            routed = ModelSpec(name=routed) if isinstance(routed, str) else routed
            if routed.name == "hybrid":
                raise ValueError("Recursive hybrid routing is not supported")
            _construct(registry, "voting", routed)
    if getattr(factory, "parameter_model", None) is None:
        # Validate strict primitive annotations without duplicating numerical model rules.
        import inspect
        from typing import get_type_hints

        try:
            hints = get_type_hints(factory.__init__ if inspect.isclass(factory) else factory)
        except (NameError, TypeError):
            hints = {}
        for name, value in spec.parameters.items():
            if name in hints:
                TypeAdapter(hints[name]).validate_python(value, strict=True)
    return registry.create(category, spec, **defaults)


def _validate_factories(candidate):
    registry, scenario = default_registry(), default_scenario_registry()
    simulation = candidate.simulation
    # The core schema intentionally permits injected custom distribution samplers;
    # the dashboard currently installs only the engine's built-in sampler.
    import numpy as np

    from fan_governance.agents.generator import sample_distribution
    from fan_governance.core.config import DistributionConfig

    for value in [*vars(simulation.population).values(), candidate.economics.income_distribution]:
        if isinstance(value, DistributionConfig):
            sample_distribution(value, 0, np.random.default_rng(0))
    for spec in simulation.voting.specs():
        _construct(registry, "voting", spec)
    for spec in effective_voting_specs(simulation):
        _construct(registry, "voting", spec)
    proposal = proposal_from_config(simulation)
    _construct(
        registry,
        "eligibility",
        simulation.governance.eligibility,
        waiting_period_days=simulation.governance.waiting_period_days,
    )
    _construct(
        registry,
        "eligibility",
        proposal.eligibility_rules.eligibility,
        waiting_period_days=proposal.eligibility_rules.waiting_period_days,
    )
    _construct(registry, "participation", simulation.participation)
    _construct(registry, "preference", simulation.preference)
    for spec in candidate.attacks:
        _construct(scenario, "attack", ModelSpec(name=spec.name, parameters=spec.parameters))
        evaluate_objective(spec.objective, {})
    for spec in candidate.defenses:
        _construct(scenario, "defense", spec)
    bases = {
        spec.parameters.get("basis", "eligible_members")
        for spec in candidate.defenses
        if spec.name == "quorum"
    }
    if len(bases) > 1:
        raise ValueError("Composed quorum policies require a common basis")


def validate_configuration(raw: dict) -> tuple[ScenarioConfig, dict]:
    """Validate every expanded cell before scheduling; never execute a simulation here."""
    if not isinstance(raw, dict):
        raise ValueError("Configuration must be a JSON object")
    config = ScenarioConfig.model_validate(raw)
    cells = prod(len(values) for values in config.experiment.grid.values())
    if cells > LIMITS["max_grid_cells"]:
        raise ValueError(f"Scenario grid exceeds {LIMITS['max_grid_cells']} cells")
    work_units = total_trials = trajectory_runs = 0
    try:
        _validate_factories(config)
        for _, candidate, _ in expanded_configs(config):
            _validate_factories(candidate)
            population = candidate.simulation.population.size
            if population > LIMITS["max_population"]:
                raise ValueError(f"Population exceeds {LIMITS['max_population']}")
            trials = candidate.experiment.trials
            if trials > LIMITS["max_trials"]:
                raise ValueError(f"Trials exceed {LIMITS['max_trials']}")
            # Validate dates through the engine clock, but avoid materializing a long daily list.
            clock = SimulationClock(**candidate.timeline.model_dump())
            steps = (
                clock.end_day + 1
                if candidate.timeline.timestep == "daily"
                else candidate.timeline.duration_months + 1
            )
            # Attacker operational budgets bound new synthetic accounts and repeated actions.
            operations = sum(a.operational_budget for a in candidate.attacks)
            if candidate.attacks:
                # Events inserted by adversaries and lifecycle changes can require daily updates.
                steps = clock.end_day + 1
            account_bound = population + operations + len(candidate.economics.investors)
            if candidate.economics.enabled and candidate.economics.membership_growth_rate:
                # Conservative resource estimate, not a projected scientific outcome: exponential
                # envelope plus one possible rounded addition per step bounds positive growth.
                exponent = candidate.economics.membership_growth_rate * clock.end_day / 30
                if exponent > 30:
                    raise ValueError("Workload exceeds local limits with membership growth")
                account_bound = ceil((account_bound + steps) * exp(exponent))
            variants = len(candidate.experiment.variants)
            # The engine runs extra matched references when attacks combine with shocks/defenses.
            if candidate.attacks:
                variants += bool(candidate.economics.shocks) + bool(candidate.defenses)
            models = len(effective_voting_specs(candidate.simulation))
            units = trials * variants * models * account_bound * steps
            # Zero-population long clocks still consume scheduling and economics work.
            work_units += max(units, trials * variants * models * steps)
            total_trials += trials
            trajectory_runs += trials * variants * models
            if work_units > LIMITS["max_work_units"]:
                raise ValueError(f"Workload exceeds {LIMITS['max_work_units']} work units")
    except (IndexError, KeyError, TypeError, AttributeError, OverflowError) as error:
        raise ValueError(f"Invalid scenario grid or timeline: {error}") from error
    return config, {
        "grid_cells": cells,
        "total_trials": total_trials,
        "trajectory_runs": trajectory_runs,
        "work_units": work_units,
    }
