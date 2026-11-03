"""Run after installing the package, from any working directory."""

from fan_governance.core.config import SimulationConfig
from fan_governance.experiments.runner import ExperimentRunner

config = SimulationConfig.model_validate(
    {
        "population": {"size": 1000},
        "voting": {"strategies": ["equal", "proportional", "capped", "diminishing"]},
    }
)
for result in ExperimentRunner().run(config):
    print(result.voting_model, result.turnout, result.metrics["gini"], result.passed)
