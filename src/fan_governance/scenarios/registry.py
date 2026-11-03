"""Extensible scenario component construction using existing validated factories."""

from fan_governance.adversarial.strategies import ATTACK_FACTORIES
from fan_governance.core.config import ModelSpec
from fan_governance.core.registry import ModelRegistry
from fan_governance.defenses.policies import DEFENSE_FACTORIES


def default_scenario_registry() -> ModelRegistry:
    registry = ModelRegistry()
    for name, factory in ATTACK_FACTORIES.items():
        registry.register("attack", name, factory)
    for name, factory in DEFENSE_FACTORIES.items():
        registry.register("defense", name, factory)
    return registry


def create_attack(
    name: str, parameters: dict | None = None, *, registry: ModelRegistry | None = None
):
    return (registry or default_scenario_registry()).create(
        "attack", ModelSpec(name=name, parameters=parameters or {})
    )


def create_defense(
    name: str, parameters: dict | None = None, *, registry: ModelRegistry | None = None
):
    return (registry or default_scenario_registry()).create(
        "defense", ModelSpec(name=name, parameters=parameters or {})
    )
