"""Independent marginal sampling with optional explicit copula correlations."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np

from fan_governance.agents.models import Supporter
from fan_governance.core.config import ATTRIBUTE_NAMES, DistributionConfig, PopulationConfig
from fan_governance.core.context import RandomStreams
from fan_governance.membership.models import Membership


@dataclass
class Population:
    supporters: list[Supporter]
    memberships: list[Membership]


def sample_distribution(
    config: DistributionConfig, size: int, rng: np.random.Generator
) -> np.ndarray:
    p = config.parameters
    if config.type == "uniform":
        values = rng.uniform(p.get("low", 0), p.get("high", 1), size)
    elif config.type == "normal":
        values = rng.normal(p.get("mean", 0), p.get("std", 1), size)
    elif config.type == "lognormal":
        with np.errstate(over="raise", invalid="raise"):
            values = rng.lognormal(p.get("mean", 0), p.get("sigma", 1), size)
    elif config.type == "beta":
        values = rng.beta(p.get("alpha", 2), p.get("beta", 2), size)
    elif config.type == "constant":
        values = np.full(size, p.get("value", 0), dtype=float)
    elif config.type == "categorical":
        return rng.choice(config.categories, size=size, p=config.probabilities)
    else:
        raise ValueError(f"Unknown distribution {config.type!r}; inject a sampler")
    if not np.isfinite(values).all():
        raise ValueError("Distribution generated nonfinite values; reduce its parameters")
    return np.clip(
        values,
        -np.inf if config.lower is None else config.lower,
        np.inf if config.upper is None else config.upper,
    )


class SyntheticPopulationGenerator:
    def __init__(
        self,
        distributions: Mapping[
            str, Callable[[DistributionConfig, int, np.random.Generator], np.ndarray]
        ]
        | None = None,
    ) -> None:
        self.distributions = dict(distributions or {})

    def sample(self, config: DistributionConfig, size: int, rng: np.random.Generator) -> np.ndarray:
        sampler = self.distributions.get(config.type, sample_distribution)
        values = np.asarray(sampler(config, size, rng), dtype=float)
        if values.shape != (size,) or not np.isfinite(values).all():
            raise ValueError("Distribution returned a wrong shape or nonfinite values")
        return np.clip(
            values,
            -np.inf if config.lower is None else config.lower,
            np.inf if config.upper is None else config.upper,
        )

    def generate(self, config: PopulationConfig, streams: RandomStreams) -> Population:
        names = tuple(
            name for name in ATTRIBUTE_NAMES if getattr(config, f"{name}_distribution") is not None
        )
        values = {
            name: self.sample(
                getattr(config, f"{name}_distribution"),
                config.size,
                streams.generator(f"population.{name}"),
            )
            for name in names
        }
        if config.correlations and config.size:
            latent = streams.generator("population.copula").multivariate_normal(
                np.zeros(len(ATTRIBUTE_NAMES)),
                config.correlation_matrix(),
                config.size,
                check_valid="raise",
                tol=1e-9,
            )
            for index, name in enumerate(ATTRIBUTE_NAMES):
                if name not in values:
                    continue
                order = np.argsort(latent[:, index], kind="stable")
                reordered = np.empty(config.size)
                reordered[order] = np.sort(values[name])
                values[name] = reordered
        # Domain bounds are always enforced, independently of the selected marginal.
        for name in names:
            values[name] = np.clip(
                values[name],
                0,
                1
                if name
                in ("loyalty", "knowledge", "participation_probability", "forecast_accuracy")
                else np.inf,
            )
        if config.contribution_model == "wealth_fraction":
            fraction = self.sample(
                config.contribution_fraction_distribution,
                config.size,
                streams.generator("population.contribution_fraction"),
            )
            if np.any((fraction < 0) | (fraction > 1)):
                raise ValueError("Contribution fractions must be between zero and one")
            values["contribution"] = values["wealth"] * fraction
        if not config.allow_unfunded_contributions:
            values["contribution"] = np.minimum(values["contribution"], values["wealth"])
        sample_counts = self.sample(
            config.forecast_sample_count_distribution,
            config.size,
            streams.generator("population.forecast_sample_count"),
        )
        # Count marginals are floored after bounding, as with membership ages.
        sample_counts = np.floor(np.maximum(sample_counts, 0))
        if "forecast_accuracy" not in values and np.any(sample_counts):
            raise ValueError(
                "Generating forecast histories requires forecast_accuracy_distribution"
            )
        if np.any(sample_counts >= 2**63):
            raise ValueError("Forecast sample counts exceed supported integer range")
        sample_counts = sample_counts.astype(np.int64)
        correct_counts = streams.generator("population.forecast_history").binomial(
            sample_counts, values.get("forecast_accuracy", np.zeros(config.size))
        )
        policy = sample_distribution(
            config.preferred_policy_distribution,
            config.size,
            streams.generator("population.preferred_policy"),
        )
        adversarial = (
            streams.generator("population.adversarial").random(config.size)
            < config.adversarial_fraction
        )
        supporters, memberships = [], []
        for i in range(config.size):
            fields = {name: float(values[name][i]) for name in names}
            fields["membership_age_days"] = int(fields["membership_age_days"])
            supporter = Supporter(
                supporter_id=f"supporter-{i:08d}",
                **fields,
                is_adversarial=bool(adversarial[i]),
                forecast_sample_count=int(sample_counts[i]),
                forecast_correct_count=int(correct_counts[i]),
                preferred_policy=str(policy[i]),
                allow_unfunded_contributions=config.allow_unfunded_contributions,
            )
            supporters.append(supporter)
            memberships.append(
                Membership(
                    member_id=f"member-{i:08d}",
                    supporter_id=supporter.supporter_id,
                    age_days=supporter.membership_age_days,
                    contribution=supporter.contribution,
                )
            )
        return Population(supporters, memberships)
