from fan_governance.agents.generator import SyntheticPopulationGenerator
from fan_governance.core.config import SimulationConfig
from fan_governance.core.context import RandomStreams
from fan_governance.core.engine import SimulationEngine
from fan_governance.experiments.runner import ExperimentRunner


def test_standalone_engine_labels_proposal_strategy_override():
    config = SimulationConfig(population={"size": 5}, proposal={"voting_strategy": "proportional"})
    election = ExperimentRunner().components(config)[0][1]
    result = SimulationEngine(SyntheticPopulationGenerator(), election).run(config)
    assert result.voting_model == "proportional"


def test_standalone_engine_records_overridden_population_seed():
    config = SimulationConfig(population={"size": 5, "seed": 7}, experiment={"seed": 42})
    election = ExperimentRunner().components(config)[0][1]
    result = SimulationEngine(SyntheticPopulationGenerator(), election).run(config)
    for name in ["population.wealth", "population.forecast_history", "population.preferred_policy"]:
        assert result.component_seeds[name] == RandomStreams(7).component_seed(name)
    assert result.component_seeds["participation"] == RandomStreams(42).component_seed(
        "participation"
    )
