"""Discover installed YAML scenarios rather than maintaining a second catalogue."""

from pathlib import Path

from fan_governance.core.config import load_config
from fan_governance.scenarios.config import load_scenario


def population_profiles(directory: Path):
    items = []
    for path in sorted(directory.glob("*.yaml")):
        if path.is_symlink() or path.is_junction():
            continue
        population = load_config(path).population
        items.append(
            {
                "id": path.stem,
                "name": path.stem.replace("_", " ").title(),
                "description": "Synthetic population assumptions from the installed profile library.",
                "configuration": population.model_dump(mode="json"),
            }
        )
    return items


def scenario_catalog(directory: Path):
    items = []
    if not directory.is_dir():
        return items
    for path in sorted(directory.glob("*.yaml")):
        if path.is_symlink() or path.is_junction():
            continue
        config = load_scenario(path)
        attacks = [a.name for a in config.attacks]
        shocks = [s.name for s in config.economics.shocks]
        category = "Combined" if attacks and shocks else "Adversarial" if attacks else "Economics"
        items.append(
            {
                "id": path.stem,
                "name": config.name.replace("_", " ").title(),
                "description": f"{category} scenario: {', '.join(attacks + shocks) or 'baseline governance'}. All inputs are synthetic.",
                "category": category,
                "population_size": config.simulation.population.size,
                "voting_models": [s.name for s in config.simulation.voting.specs()],
                "attacks": attacks,
                "defenses": [d.name for d in config.defenses],
                "duration_months": config.timeline.duration_months,
                "configuration": config.model_dump(mode="json"),
            }
        )
    return items
