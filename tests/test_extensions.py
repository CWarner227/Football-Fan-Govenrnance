import json

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError
from test_elections import fixture_club, runner

from fan_governance.agents.generator import SyntheticPopulationGenerator
from fan_governance.core.config import (
    DistributionConfig,
    PopulationConfig,
    SimulationConfig,
    load_config,
)
from fan_governance.core.context import RandomStreams
from fan_governance.core.registry import default_registry
from fan_governance.elections.models import GovernanceProposal
from fan_governance.elections.runner import Realization
from fan_governance.experiments.runner import ExperimentRunner
from fan_governance.output.exporters import export_results


def test_custom_metric_does_not_change_outcomes():
    class AdditionalMetric:
        def calculate(self, data):
            return {"custom": sum(data.eligible_weights)}

    election = runner()
    election.metrics = AdditionalMetric()
    result = election.run(fixture_club(), GovernanceProposal(), RandomStreams(5))
    assert result.metrics == {"custom": 4}
    assert result.votes_cast == 4


def test_custom_eligibility_and_participation_are_replaceable():
    class EveryoneEligible:
        def eligible(self, supporters, memberships):
            return memberships

    class EveryoneVotes:
        def participates(self, supporter, membership, context, rng):
            return True

    class EveryoneApproves:
        def choose(self, supporter, membership, proposal, context, rng):
            return proposal.options[0]

    registry = default_registry()
    registry.register("eligibility", "everyone", lambda waiting_period_days: EveryoneEligible())
    registry.register("participation", "everyone", EveryoneVotes)
    registry.register("preference", "everyone", EveryoneApproves)
    config = SimulationConfig.model_validate(
        {
            "population": {"size": 100},
            "governance": {"waiting_period_days": 9999, "eligibility": {"name": "everyone"}},
            "participation": {"name": "everyone"},
            "preference": {"name": "everyone"},
        }
    )
    result = ExperimentRunner(registry=registry).run(config)[0]
    assert result.eligible_voter_count == result.votes_cast == 100
    assert result.vote_totals == {"approve": 100, "reject": 0}
    assert result.passed


@pytest.mark.parametrize(
    "data",
    [
        {"type": "uniform", "parameters": {"low": 1, "high": 0}},
        {"type": "beta", "parameters": {"alpha": 0}},
        {"type": "normal", "lower": 1, "upper": 0},
        {"type": "lognormal", "parameters": {"sigma": float("nan")}},
    ],
)
def test_invalid_distribution_config(data):
    with pytest.raises(ValidationError):
        DistributionConfig.model_validate(data)


@pytest.mark.parametrize(
    "correlations",
    [
        {"wealth:wealth": 1},
        {"wealth:contribution": 1.1},
        {"wealth:contribution": 0.9, "wealth:loyalty": 0.9, "contribution:loyalty": -0.9},
        {"wealth:contribution": 0.1, "contribution:wealth": 0.2},
    ],
)
def test_invalid_correlations(correlations):
    with pytest.raises(ValidationError):
        PopulationConfig(correlations=correlations)


def test_duplicate_and_unknown_membership_returned_by_plugin_rejected():
    class BadEligibility:
        def eligible(self, supporters, memberships):
            return [memberships[0], memberships[0]]

    election = runner()
    election.eligibility = BadEligibility()
    with pytest.raises(ValueError, match="duplicate"):
        election.run(fixture_club(), GovernanceProposal(), RandomStreams(1))


def test_incomplete_realization_rejected():
    with pytest.raises(ValueError, match="missing"):
        runner().run(
            fixture_club(), GovernanceProposal(), RandomStreams(1), realization=Realization({}, {})
        )


def test_builtin_factories_validate_parameter_ranges():
    registry = default_registry()
    from fan_governance.core.config import ModelSpec

    for category, name, parameters in [
        ("voting", "capped", {"cap": 0}),
        ("voting", "diminishing", {"scale": -1}),
        ("participation", "probabilistic", {"probability": 1.1}),
        ("preference", "synthetic", {"approval_probability": -1}),
        ("eligibility", "standard", {"waiting_period_days": -1}),
    ]:
        with pytest.raises(ValueError, match="parameters"):
            registry.create(category, ModelSpec(name=name, parameters=parameters))


def test_empty_config_rejected(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    with pytest.raises(ValueError, match="mapping"):
        load_config(path)


def test_optional_parquet_roundtrip(tmp_path):
    pytest.importorskip("pyarrow")
    result = ExperimentRunner().run(SimulationConfig(population={"size": 10}))
    paths = export_results(result, tmp_path, ["parquet"])
    frame = pd.read_parquet(paths["parquet"])
    assert frame["votes_cast"].tolist() == [result[0].votes_cast]
    assert json.loads(frame["configuration"][0])["population"]["size"] == 10


def test_optional_plot(tmp_path):
    pytest.importorskip("matplotlib")
    from fan_governance.output.plotting import plot_results

    result = ExperimentRunner().run(SimulationConfig(population={"size": 10}))
    path = plot_results(result, tmp_path / "plot.png")
    assert path.stat().st_size > 1000


def test_extreme_weights_remain_numerically_stable():
    from fan_governance.metrics.concentration import concentration_metrics

    result = concentration_metrics([1e308, 1e308])
    assert result["effective_voters"] == pytest.approx(2)
    assert result["gini"] == pytest.approx(0)


def test_custom_population_distribution():
    generator = SyntheticPopulationGenerator(
        distributions={
            "constant": lambda config, size, rng: np.full(size, config.parameters["value"])
        }
    )
    config = PopulationConfig(
        size=10, wealth_distribution={"type": "constant", "parameters": {"value": 23}}
    )
    population = generator.generate(config, RandomStreams(1))
    assert all(s.wealth == 23 for s in population.supporters)


def test_nonfinite_custom_population_distribution_rejected():
    generator = SyntheticPopulationGenerator(
        distributions={"invalid": lambda config, size, rng: np.full(size, np.inf)}
    )
    config = PopulationConfig(size=1, wealth_distribution={"type": "invalid"})
    with pytest.raises(ValueError, match="nonfinite"):
        generator.generate(config, RandomStreams(1))


def test_custom_distribution_bounds_still_validate():
    with pytest.raises(ValidationError):
        DistributionConfig(type="constant", lower=2, upper=1)


def test_waiting_period_cannot_be_silently_overridden():
    config = SimulationConfig.model_validate(
        {
            "population": {"size": 5},
            "governance": {
                "waiting_period_days": 365,
                "eligibility": {"name": "standard", "parameters": {"waiting_period_days": 0}},
            },
        }
    )
    with pytest.raises(ValueError, match="waiting_period_days"):
        ExperimentRunner().run(config)


def test_cli_in_process_and_summary(tmp_path, capsys):
    from fan_governance.cli import main
    from fan_governance.experiments.comparison import comparison_summary

    assert main(["models"]) == 0
    assert "equal" in capsys.readouterr().out
    path = tmp_path / "experiment.yaml"
    path.write_text(
        "experiment:\n  trials: 2\npopulation:\n  size: 20\nvoting:\n  strategies: [equal, proportional]\n"
    )
    assert main(["experiment", "--config", str(path), "--output", str(tmp_path / "out")]) == 0
    assert len(pd.read_csv(tmp_path / "out" / "summary.csv")) == 2
    assert main(["simulate", "--config", str(path)]) == 2
    assert "one voting strategy" in capsys.readouterr().err
    assert comparison_summary([]).empty


def test_diminishing_weight_avoids_intermediate_overflow():
    from fan_governance.agents.models import Supporter
    from fan_governance.membership.models import Membership
    from fan_governance.voting.strategies import DiminishingVoting

    supporter = Supporter(supporter_id="s")
    member = Membership(member_id="m", supporter_id="s", contribution=1e308)
    assert DiminishingVoting(scale=0.1).calculate_weight(supporter, member, None) == pytest.approx(
        711.4987937351601
    )
