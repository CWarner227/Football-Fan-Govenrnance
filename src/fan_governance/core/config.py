"""Strict experiment schema; model-specific options are validated by factories."""

from pathlib import Path
from typing import Annotated, Any, Literal, Self

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class ValidatedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, allow_inf_nan=False)


class DistributionConfig(ValidatedModel):
    """Parameters describe underlying marginals; bounds clip rather than resample."""

    type: str = Field(default="uniform", min_length=1)
    parameters: dict[str, float] = Field(default_factory=dict)
    lower: float | None = None
    upper: float | None = None
    categories: list[str] | None = None
    probabilities: list[Probability] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_compact_distribution(cls, data):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if "distribution" in data:
            family = data.pop("distribution")
            if "type" in data and data["type"] != family:
                raise ValueError("Conflicting distribution and type")
            data["type"] = family
        parameters = dict(data.get("parameters", {}))
        for key in ("min", "max", "low", "high", "mean", "std", "sigma", "alpha", "beta", "value"):
            if key in data:
                canonical = {"min": "low", "max": "high"}.get(key, key)
                value = data.pop(key)
                if canonical in parameters and parameters[canonical] != value:
                    raise ValueError(f"Conflicting distribution parameter {canonical}")
                parameters[canonical] = value
        data["parameters"] = parameters
        return data

    @model_validator(mode="after")
    def validate_distribution(self) -> Self:
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("lower must not exceed upper")
        families = {
            "uniform": {"low": 0.0, "high": 1.0},
            "normal": {"mean": 0.0, "std": 1.0},
            "lognormal": {"mean": 0.0, "sigma": 1.0},
            "beta": {"alpha": 2.0, "beta": 2.0},
            "constant": {"value": 0.0},
        }
        if self.type == "categorical":
            if not self.categories or len(set(self.categories)) != len(self.categories):
                raise ValueError("categorical categories must be nonempty and unique")
            if self.parameters or self.lower is not None or self.upper is not None:
                raise ValueError(
                    "categorical distributions do not accept numeric parameters or bounds"
                )
            if self.probabilities is not None and (
                len(self.probabilities) != len(self.categories)
                or not np.isclose(sum(self.probabilities), 1, rtol=0, atol=1e-10)
            ):
                raise ValueError("categorical probabilities must match categories and sum to one")
            return self
        if self.categories is not None or self.probabilities is not None:
            raise ValueError("categories and probabilities require a categorical distribution")
        if self.type not in families:
            # Injected distribution samplers own their parameter validation.
            return self
        defaults = families[self.type]
        unknown = self.parameters.keys() - defaults.keys()
        if unknown:
            raise ValueError(f"Unknown {self.type} parameters: {sorted(unknown)}")
        p = defaults | self.parameters
        if self.type == "uniform" and p["high"] <= p["low"]:
            raise ValueError("uniform high must exceed low")
        for key in ("std", "sigma", "alpha", "beta"):
            if key in p and p[key] <= 0:
                raise ValueError(f"{key} must be positive")
        return self


ATTRIBUTE_NAMES = (
    "wealth",
    "contribution",
    "membership_age_days",
    "loyalty",
    "knowledge",
    "participation_probability",
    "forecast_accuracy",
)


class PopulationConfig(ValidatedModel):
    size: int = Field(default=10000, ge=0)
    seed: int | None = Field(default=None, ge=0)
    contribution_model: Literal["independent", "wealth_fraction"] = "independent"
    allow_unfunded_contributions: bool = False
    contribution_fraction_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(parameters={"low": 0.001, "high": 0.05})
    )
    forecast_accuracy_distribution: DistributionConfig | None = None
    forecast_sample_count_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(type="constant", parameters={"value": 0})
    )
    preferred_policy_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(type="categorical", categories=["neutral"])
    )
    adversarial_fraction: Probability = 0.0
    wealth_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(
            type="lognormal", parameters={"mean": 10, "sigma": 1}, lower=0
        )
    )
    contribution_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(
            type="lognormal", parameters={"mean": 4, "sigma": 1.5}, lower=0
        )
    )
    membership_age_days_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(parameters={"low": 0, "high": 1826}, lower=0)
    )
    loyalty_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(
            type="beta", parameters={"alpha": 3, "beta": 2}, lower=0, upper=1
        )
    )
    knowledge_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(type="beta", lower=0, upper=1)
    )
    participation_probability_distribution: DistributionConfig = Field(
        default_factory=lambda: DistributionConfig(
            type="beta", parameters={"alpha": 3, "beta": 2}, lower=0, upper=1
        )
    )
    correlations: dict[str, float] | dict[str, list] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_population(cls, data):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        aliases = {
            "participation_rate": "participation_probability",
            "knowledge_score": "knowledge",
        }
        for alias, canonical in aliases.items():
            for suffix in ("", "_distribution"):
                key = alias + suffix
                target = canonical + suffix
                if key in data:
                    value = data.pop(key)
                    if target in data and data[target] != value:
                        raise ValueError(f"Conflicting {key} and {target}")
                    data[target] = value
        mode = data.pop("financial_mode", None)
        if mode is not None:
            if mode not in ("independent", "wealth_fraction", "allow_unfunded"):
                raise ValueError("Unknown financial_mode")
            if mode == "allow_unfunded":
                data["allow_unfunded_contributions"] = True
            else:
                if "contribution_model" in data and data["contribution_model"] != mode:
                    raise ValueError("Conflicting financial_mode and contribution_model")
                data["contribution_model"] = mode
        contribution = data.get("contribution")
        if isinstance(contribution, dict) and "model" in contribution:
            contribution = dict(data.pop("contribution"))
            model = contribution.pop("model")
            if model == "allow_unfunded":
                data["allow_unfunded_contributions"] = True
                model = "independent"
            if "contribution_model" in data and data["contribution_model"] != model:
                raise ValueError("Conflicting contribution models")
            data["contribution_model"] = model
            if model == "wealth_fraction":
                minimum = contribution.pop("min_fraction", 0.001)
                maximum = contribution.pop("max_fraction", 0.05)
                if contribution or not 0 <= minimum <= maximum <= 1:
                    raise ValueError(
                        "wealth fractions must satisfy 0 <= min_fraction <= max_fraction <= 1"
                    )
                data["contribution_fraction_distribution"] = (
                    {"type": "constant", "parameters": {"value": minimum}}
                    if minimum == maximum
                    else {"type": "uniform", "parameters": {"low": minimum, "high": maximum}}
                )
            elif contribution:
                data["contribution"] = contribution
        for name in (*ATTRIBUTE_NAMES, "forecast_sample_count", "preferred_policy"):
            if name in data:
                value = data.pop(name)
                target = f"{name}_distribution"
                if target in data and data[target] != value:
                    raise ValueError(f"Conflicting {name} distribution specifications")
                data[target] = value
        return data

    def correlation_matrix(self) -> np.ndarray:
        matrix = np.eye(len(ATTRIBUTE_NAMES))
        aliases = {
            "participation_rate": "participation_probability",
            "knowledge_score": "knowledge",
        }
        if "attributes" in self.correlations or "matrix" in self.correlations:
            if set(self.correlations) != {"attributes", "matrix"}:
                raise ValueError("Matrix correlations require only attributes and matrix")
            names = [aliases.get(n, n) for n in self.correlations["attributes"]]
            if len(set(names)) != len(names) or any(n not in ATTRIBUTE_NAMES for n in names):
                raise ValueError("Correlation attributes must be unique known numeric traits")
            supplied = np.asarray(self.correlations["matrix"], dtype=float)
            if (
                not names
                or supplied.shape != (len(names), len(names))
                or not np.isfinite(supplied).all()
                or not np.allclose(supplied, supplied.T, rtol=0, atol=1e-10)
                or not np.allclose(np.diag(supplied), 1, rtol=0, atol=1e-10)
            ):
                raise ValueError("Correlation matrix must be finite, symmetric with unit diagonal")
            indices = [ATTRIBUTE_NAMES.index(n) for n in names]
            matrix[np.ix_(indices, indices)] = supplied
            if np.linalg.eigvalsh(matrix).min() < -1e-10:
                raise ValueError("Correlation matrix must be positive semidefinite")
            return matrix
        seen = set()
        for pair, coefficient in sorted(self.correlations.items()):
            names = [aliases.get(n, n) for n in pair.split(":")]
            if (
                len(names) != 2
                or any(n not in ATTRIBUTE_NAMES for n in names)
                or names[0] == names[1]
            ):
                raise ValueError(f"Invalid correlation pair {pair!r}; use attribute:attribute")
            indices = tuple(sorted(ATTRIBUTE_NAMES.index(n) for n in names))
            if indices in seen or not -1 <= coefficient <= 1:
                raise ValueError(f"Duplicate pair or correlation outside [-1,1]: {pair}")
            seen.add(indices)
            matrix[indices[0], indices[1]] = matrix[indices[1], indices[0]] = coefficient
        if np.linalg.eigvalsh(matrix).min() < -1e-10:
            raise ValueError("Correlation matrix must be positive semidefinite")
        return matrix

    @model_validator(mode="after")
    def validate_correlations(self) -> Self:
        self.correlation_matrix()
        for name in ATTRIBUTE_NAMES:
            distribution = getattr(self, f"{name}_distribution")
            if distribution is None:
                continue
            if distribution.type == "categorical":
                raise ValueError(f"{name} requires a numeric distribution")
            if distribution.upper is not None and distribution.upper < 0:
                raise ValueError(f"{name} upper bound cannot be negative")
            if (
                name in ("loyalty", "knowledge", "participation_probability", "forecast_accuracy")
                and distribution.lower is not None
                and distribution.lower > 1
            ):
                raise ValueError(f"{name} lower bound cannot exceed 1")
        if self.forecast_sample_count_distribution.type == "categorical":
            raise ValueError("forecast_sample_count requires a numeric distribution")
        if self.contribution_fraction_distribution.type == "categorical":
            raise ValueError("contribution fractions require a numeric distribution")
        if self.preferred_policy_distribution.type != "categorical":
            raise ValueError("preferred_policy requires a categorical distribution")
        return self


class ModelSpec(ValidatedModel):
    name: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class GovernanceConfig(ValidatedModel):
    waiting_period_days: int = Field(default=180, ge=0)
    eligibility: ModelSpec = Field(default_factory=lambda: ModelSpec(name="standard"))
    quorum: Probability = 0.2
    quorum_basis: Literal["eligible_members", "eligible_weight"] = "eligible_members"
    approval_threshold: Probability = 0.5


class VotingConfig(ValidatedModel):
    strategies: list[str | ModelSpec] = Field(default_factory=lambda: ["equal"], min_length=1)

    def specs(self) -> list[ModelSpec]:
        return [ModelSpec(name=s) if isinstance(s, str) else s for s in self.strategies]

    @model_validator(mode="after")
    def unique_names(self) -> Self:
        names = [s.name for s in self.specs()]
        if len(names) != len(set(names)):
            raise ValueError("Strategy names must be unique within an experiment")
        return self


class ProposalConfig(ValidatedModel):
    proposal_id: str = "proposal-1"
    category: str = "club_policy"
    options: tuple[str, str] = ("approve", "reject")
    quorum: Probability | None = None
    approval_threshold: Probability | None = None
    waiting_period_days: int | None = Field(default=None, ge=0)
    eligibility: ModelSpec | None = None
    voting_strategy: str | ModelSpec | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_options(self) -> Self:
        if any(not option for option in self.options) or self.options[0] == self.options[1]:
            raise ValueError(
                "Binary options must be distinct nonempty strings; first option is approval"
            )
        return self


class ExperimentConfig(ValidatedModel):
    name: str = Field(default="fan_governance", pattern=r"^[A-Za-z0-9_-]+$")
    trials: int = Field(default=1, ge=1)
    seed: int = Field(default=42, ge=0)
    population_sizes: list[Annotated[int, Field(ge=0)]] | None = Field(default=None, min_length=1)
    waiting_periods: list[Annotated[int, Field(ge=0)]] | None = Field(default=None, min_length=1)
    participation_levels: list[Probability] | None = Field(default=None, min_length=1)
    wealth_distributions: list[DistributionConfig] | None = Field(default=None, min_length=1)
    population_profiles: dict[str, PopulationConfig] | None = Field(default=None, min_length=1)
    participation_models: list[ModelSpec] | None = Field(default=None, min_length=1)
    proposal_categories: list[str] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_axes(self) -> Self:
        if self.proposal_categories is not None and (
            len(set(self.proposal_categories)) != len(self.proposal_categories)
            or any(not c for c in self.proposal_categories)
        ):
            raise ValueError("Proposal categories must be distinct nonempty names")
        if self.population_profiles and (self.population_sizes or self.wealth_distributions):
            raise ValueError(
                "Use population_profiles or population_sizes/wealth_distributions, not both"
            )
        return self


class OutputConfig(ValidatedModel):
    directory: Path = Path("results")
    formats: list[Literal["csv", "json", "parquet"]] = Field(
        default_factory=lambda: ["csv", "json"], min_length=1
    )


class SimulationConfig(ValidatedModel):
    experiment: ExperimentConfig = Field(default_factory=ExperimentConfig)
    population: PopulationConfig = Field(default_factory=PopulationConfig)
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)
    voting: VotingConfig = Field(default_factory=VotingConfig)
    participation: ModelSpec = Field(default_factory=lambda: ModelSpec(name="probabilistic"))
    preference: ModelSpec = Field(
        default_factory=lambda: ModelSpec(
            name="synthetic", parameters={"approval_probability": 0.5}
        )
    )
    proposal: ProposalConfig = Field(default_factory=ProposalConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(path: str | Path) -> SimulationConfig:
    """Load YAML using safe constructors; reject empty/nonmapping documents."""
    with Path(path).open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError("Configuration must be a YAML mapping")
    return SimulationConfig.model_validate(raw)
