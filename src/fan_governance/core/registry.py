"""Construction belongs here, keeping component selection out of engine mechanics."""

from collections.abc import Callable
from typing import Any

from fan_governance.core.config import ModelSpec


class ModelRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, dict[str, Callable[..., Any]]] = {}

    def register(self, category: str, name: str, factory: Callable[..., Any]) -> None:
        group = self._factories.setdefault(category, {})
        if name in group:
            raise ValueError(f"Model already registered: {category}.{name}")
        group[name] = factory

    def create(self, category: str, spec: ModelSpec, **defaults: Any) -> Any:
        group = self._factories.get(category, {})
        if spec.name not in group:
            raise ValueError(
                f"Unknown {category} model {spec.name!r}; available: {', '.join(sorted(group))}"
            )
        conflicts = defaults.keys() & spec.parameters.keys()
        if conflicts:
            raise ValueError(
                f"Model parameters cannot override governance settings: {sorted(conflicts)}"
            )
        try:
            return group[spec.name](**(defaults | spec.parameters))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid parameters for {category}.{spec.name}: {error}") from error

    def names(self) -> dict[str, list[str]]:
        return {category: sorted(group) for category, group in sorted(self._factories.items())}

    def factories(self) -> dict[str, dict[str, Callable[..., Any]]]:
        """Return a detached discovery view without exposing registry mutation."""
        return {category: dict(group) for category, group in self._factories.items()}


def default_registry() -> ModelRegistry:
    from fan_governance.membership.eligibility import StandardEligibility
    from fan_governance.participation.probabilistic import (
        ConstantParticipation,
        ProbabilisticParticipation,
    )
    from fan_governance.preferences.synthetic import SyntheticPreference
    from fan_governance.voting.strategies import (
        CappedVoting,
        DiminishingVoting,
        EqualVoting,
        ProportionalVoting,
    )

    registry = ModelRegistry()
    for name, factory in {
        "equal": EqualVoting,
        "proportional": ProportionalVoting,
        "capped": CappedVoting,
        "diminishing": DiminishingVoting,
    }.items():
        registry.register("voting", name, factory)
    registry.register("eligibility", "standard", StandardEligibility)
    registry.register("participation", "probabilistic", ProbabilisticParticipation)
    registry.register("preference", "synthetic", SyntheticPreference)
    from fan_governance.participation.attribute_based import AttributeBasedParticipation
    from fan_governance.preferences.attribute_based import AttributeBasedPreference
    from fan_governance.preferences.policy import PolicyPreference
    from fan_governance.voting.expertise import ExpertiseVoting
    from fan_governance.voting.hybrid import HybridVoting

    def hybrid_factory(default_strategy="equal", proposal_rules=None):
        def construct(value):
            spec = (
                ModelSpec(name=value) if isinstance(value, str) else ModelSpec.model_validate(value)
            )
            if spec.name == "hybrid":
                raise ValueError("Recursive hybrid routing is not supported")
            return registry.create("voting", spec)

        rules = (
            {
                "constitutional": "equal",
                "board_election": "equal",
                "funding": "capped",
                "fan_experience": "equal",
            }
            if proposal_rules is None
            else proposal_rules
        )
        return HybridVoting(
            construct(default_strategy),
            {category: construct(value) for category, value in rules.items()},
        )

    registry.register("voting", "hybrid", hybrid_factory)
    registry.register("voting", "expertise", ExpertiseVoting)
    registry.register("participation", "constant", ConstantParticipation)
    registry.register("participation", "attribute_based", AttributeBasedParticipation)
    registry.register("preference", "policy", PolicyPreference)
    registry.register("preference", "attribute_based", AttributeBasedPreference)
    return registry
