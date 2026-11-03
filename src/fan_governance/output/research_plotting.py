"""Optional, category-separated research figures for synthetic election trials."""

import math
from collections import defaultdict
from numbers import Real
from pathlib import Path

import numpy as np

from fan_governance.elections.models import SimulationResult


def _number(value, metric: str) -> float:
    if not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"Research plots require a defined finite metric: {metric}")
    return float(value)


def _plot_rows(results: list[SimulationResult]) -> dict:
    if not results:
        raise ValueError("Cannot plot empty results")
    groups = defaultdict(lambda: defaultdict(list))
    for result in results:
        category = result.execution_metadata.get("proposal_category")
        if not isinstance(category, str) or not category:
            raise ValueError("Research plots require proposal_category metadata")
        try:
            metrics = result.metrics
            # Vote totals preserve the proposal's option order; option zero is approval.
            first_option = next(iter(result.vote_totals))
            deciles = metrics["representation"]["potential"]["wealth_decile_power_shares"]
            row = {
                "concentration": _number(metrics["gini"], "gini"),
                "effective_voters": _number(metrics["effective_voters"], "effective_voters"),
                "wealth_deciles": [
                    _number(deciles[str(decile)], f"wealth_decile_power_shares.{decile}")
                    for decile in range(10, 101, 10)
                ],
                "weighted": _number(metrics["weighted_shares"][first_option], "weighted_shares"),
                "unweighted": _number(
                    metrics["unweighted_shares"][first_option], "unweighted_shares"
                ),
                "turnout": _number(result.turnout, "turnout"),
                "outcome_disagreement": _number(
                    metrics["outcome_differs_from_equal"], "outcome_differs_from_equal"
                ),
            }
        except (KeyError, TypeError, StopIteration) as error:
            raise ValueError(f"Missing research plot metric: {error}") from error
        groups[category][result.voting_model].append(row)
    return groups


def plot_research_results(
    results: list[SimulationResult], directory: Path | str
) -> dict[str, Path]:
    """Save six PNGs, with separate panels for every proposal category.

    Boxplots and turnout histograms show trial distributions. Wealth decile,
    approval and disagreement figures show arithmetic means across trials per
    model and category. Approval always means the proposal's first option;
    disagreement uses the engine's quorum-aware equal-outcome comparison.
    Empty results, missing categories or absent/undefined required metrics raise
    ValueError before writing files. Matplotlib is an optional, lazy import.
    """
    groups = _plot_rows(results)
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise ValueError("Research plotting requires the optional plots extra") from error

    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    descriptions = {
        "concentration": ("Eligible voting power concentration", "Gini coefficient"),
        "effective_voters": ("Effective number of voters", "Effective voters"),
        "wealth_deciles": ("Wealth decile versus potential voting power", "Voting power share"),
        "approval_shares": ("Weighted and unweighted approval", "Mean first-option vote share"),
        "turnout": ("Turnout distributions", "Number of trials"),
        "outcome_disagreement": ("Disagreement with equal-vote outcome", "Fraction of trials"),
    }
    paths = {}
    categories = sorted(groups)
    for name, (title, ylabel) in descriptions.items():
        figure, axes = plt.subplots(
            1,
            len(categories),
            squeeze=False,
            figsize=(max(6, 5 * len(categories)), 5),
            constrained_layout=True,
        )
        try:
            for axis, category in zip(axes.flat, categories, strict=True):
                model_rows = groups[category]
                models = sorted(model_rows)
                samples = (
                    {
                        key: [[row[key] for row in model_rows[model]] for model in models]
                        for key in ("weighted", "unweighted")
                        if name == "approval_shares"
                    }
                    if name == "approval_shares"
                    else {name: [[row[name] for row in model_rows[model]] for model in models]}
                )
                positions = np.arange(len(models))
                if name in ("concentration", "effective_voters"):
                    axis.boxplot(samples[name], tick_labels=models)
                    axis.tick_params(axis="x", rotation=25)
                elif name == "wealth_deciles":
                    for model, values in zip(models, samples[name], strict=True):
                        axis.plot(
                            range(10, 101, 10), np.mean(values, axis=0), marker="o", label=model
                        )
                    axis.set_xlabel("Wealth decile upper percentile (poorest to richest)")
                    axis.set_xticks(range(10, 101, 10))
                    axis.legend()
                    axis.set_ylim(0, 1)
                elif name == "approval_shares":
                    axis.bar(
                        positions - 0.2,
                        [np.mean(v) for v in samples["weighted"]],
                        0.4,
                        label="Weighted",
                    )
                    axis.bar(
                        positions + 0.2,
                        [np.mean(v) for v in samples["unweighted"]],
                        0.4,
                        label="Unweighted",
                    )
                    axis.set_xticks(positions, models, rotation=25)
                    axis.set_ylim(0, 1)
                    axis.legend()
                elif name == "turnout":
                    for model, values in zip(models, samples[name], strict=True):
                        axis.hist(
                            values,
                            bins=np.linspace(0, 1, 11),
                            histtype="step",
                            linewidth=2,
                            label=model,
                        )
                    axis.set_xlim(0, 1)
                    axis.set_xlabel("Turnout fraction")
                    axis.legend()
                else:
                    axis.bar(models, [np.mean(v) for v in samples[name]])
                    axis.tick_params(axis="x", rotation=25)
                    axis.set_ylim(0, 1)
                axis.set_title(category)
                axis.set_ylabel(ylabel)
                axis.grid(axis="y", alpha=0.2)
            figure.suptitle(f"Synthetic simulation results — {title}")
            path = destination / f"{name}.png"
            figure.savefig(path, dpi=160)
            paths[name] = path
        finally:
            plt.close(figure)
    return paths
