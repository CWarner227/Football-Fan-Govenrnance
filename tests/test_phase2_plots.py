from pathlib import Path

import pytest

from fan_governance.core.config import SimulationConfig
from fan_governance.experiments.runner import ExperimentRunner
from fan_governance.output.research_plotting import plot_research_results


def research_results():
    config = SimulationConfig.model_validate(
        {
            "experiment": {"name": "plots", "trials": 2, "seed": 42},
            "population": {"size": 30},
            "participation": {"name": "probabilistic", "parameters": {"probability": 1}},
            "voting": {"strategies": ["equal", "proportional"]},
        }
    )
    first = ExperimentRunner().run(config)
    second = [result.model_copy(deep=True) for result in first]
    for result in first:
        result.execution_metadata["proposal_category"] = "funding"
    for result in second:
        result.execution_metadata["proposal_category"] = "constitutional"
    return first + second


def test_six_research_figures_are_nonempty_pngs(tmp_path):
    pytest.importorskip("matplotlib")
    paths = plot_research_results(research_results(), tmp_path / "figures")
    assert set(paths) == {
        "concentration",
        "effective_voters",
        "wealth_deciles",
        "approval_shares",
        "turnout",
        "outcome_disagreement",
    }
    for path in paths.values():
        assert isinstance(path, Path)
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert path.stat().st_size > 1000


def test_figures_keep_proposal_categories_separate(tmp_path, monkeypatch):
    plt = pytest.importorskip("matplotlib.pyplot")
    from matplotlib.figure import Figure

    saved = []
    original = Figure.savefig

    def record(figure, *args, **kwargs):
        saved.append(figure)
        return original(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", record)
    results = research_results()
    for result in results:
        option = next(iter(result.vote_totals))
        category = result.execution_metadata["proposal_category"]
        result.metrics["weighted_shares"][option] = 0.8 if category == "funding" else 0.4
        result.metrics["unweighted_shares"][option] = 0.2
    plot_research_results(results, tmp_path)
    assert len(saved) == 6
    for figure in saved:
        titles = {axis.get_title() for axis in figure.axes}
        assert titles == {"constitutional", "funding"}
        assert "Synthetic" in figure._suptitle.get_text()
        assert not plt.fignum_exists(figure.number)
    approval_figure = saved[3]
    for axis in approval_figure.axes:
        weighted = 0.8 if axis.get_title() == "funding" else 0.4
        assert [patch.get_height() for patch in axis.patches] == pytest.approx(
            [weighted, weighted, 0.2, 0.2]
        )


def test_empty_results_fail_with_explicit_error(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        plot_research_results([], tmp_path)


@pytest.mark.parametrize(
    "missing", ["gini", "representation", "weighted_shares", "outcome_differs_from_equal"]
)
def test_missing_metrics_fail_before_export(tmp_path, missing):
    results = research_results()
    del results[0].metrics[missing]
    with pytest.raises(ValueError, match="metric"):
        plot_research_results(results, tmp_path)
    assert not list(tmp_path.glob("*.png"))


def test_undefined_metrics_are_explicit_errors(tmp_path):
    results = research_results()
    results[0].metrics["gini"] = None
    with pytest.raises(ValueError, match="defined finite metric: gini"):
        plot_research_results(results, tmp_path)


def test_missing_category_is_an_explicit_error(tmp_path):
    results = research_results()
    del results[0].execution_metadata["proposal_category"]
    with pytest.raises(ValueError, match="proposal_category"):
        plot_research_results(results, tmp_path)
