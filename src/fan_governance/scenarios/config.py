"""Separate scenario schema preserves the original single-election YAML interface."""

from datetime import date
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import Field, model_validator

from fan_governance.core.config import (
    ModelSpec,
    Nonnegative,
    OutputConfig,
    Probability,
    SimulationConfig,
    ValidatedModel,
)
from fan_governance.economics.config import EconomicConfig


class AttackerSpec(ValidatedModel):
    attacker_id: str = Field(default="attacker", min_length=1)
    name: str
    financial_budget: Nonnegative = 100000
    operational_budget: int = Field(default=10000, ge=0)
    coordination_level: Probability = 1
    risk_tolerance: Probability = 0.5
    time_horizon_days: int = Field(default=3650, ge=0)
    objective: dict[str, Any] = Field(
        default_factory=lambda: {"type": "majority_cast", "threshold": 0.5, "target": "approve"}
    )
    parameters: dict[str, Any] = Field(default_factory=dict)


class TimelineConfig(ValidatedModel):
    start_date: date = date(2027, 1, 1)
    duration_months: int = Field(default=12, ge=1)
    timestep: Literal["daily", "monthly", "yearly"] = "monthly"


class ElectionsConfig(ValidatedModel):
    interval_months: int = Field(default=12, ge=1)


class ScenarioExperiment(ValidatedModel):
    trials: int = Field(default=5, ge=1)
    seed: int = Field(default=42, ge=0)
    variants: list[Literal["control", "unprotected", "defended"]] = Field(
        default_factory=lambda: ["control", "unprotected", "defended"], min_length=1
    )
    grid: dict[str, list[Any]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_grid(self) -> Self:
        if len(set(self.variants)) != len(self.variants):
            raise ValueError("Scenario variants must be unique")
        if not {"control", "unprotected", "defended"} <= set(self.variants):
            raise ValueError(
                "Paired scenario analysis requires control, unprotected and defended variants"
            )
        if any(not key or not values for key, values in self.grid.items()):
            raise ValueError("Grid paths and value lists must be nonempty")
        return self


class ScenarioConfig(ValidatedModel):
    name: str = Field(default="scenario", pattern=r"^[A-Za-z0-9_-]+$")
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    timeline: TimelineConfig = Field(default_factory=TimelineConfig)
    elections: ElectionsConfig = Field(default_factory=ElectionsConfig)
    attacks: list[AttackerSpec] = Field(default_factory=list)
    defenses: list[ModelSpec] = Field(default_factory=list)
    economics: EconomicConfig = Field(default_factory=EconomicConfig)
    experiment: ScenarioExperiment = Field(default_factory=ScenarioExperiment)
    honest_turnout: Probability | None = None
    economic_turnout_sensitivity: Nonnegative = 0
    metrics: list[Literal["capture", "defense", "economics", "combined"]] = Field(
        default_factory=lambda: ["capture", "defense", "economics", "combined"]
    )
    output: OutputConfig = Field(
        default_factory=lambda: OutputConfig(directory=Path("results/scenario"))
    )

    @model_validator(mode="after")
    def validate_scenario(self) -> Self:
        if len({a.attacker_id for a in self.attacks}) != len(self.attacks):
            raise ValueError("Attacker IDs must be unique")
        if self.elections.interval_months > self.timeline.duration_months:
            raise ValueError("Timeline must contain at least one scheduled election")
        if any(
            getattr(self.simulation.experiment, axis) is not None
            for axis in (
                "population_sizes",
                "population_profiles",
                "participation_models",
                "proposal_categories",
                "waiting_periods",
                "wealth_distributions",
                "participation_levels",
            )
        ):
            raise ValueError("Use scenario experiment.grid, not nested Phase 2 axes")
        return self


def load_scenario(path: str | Path) -> ScenarioConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Scenario must be a YAML mapping")
    return ScenarioConfig.model_validate(raw)
