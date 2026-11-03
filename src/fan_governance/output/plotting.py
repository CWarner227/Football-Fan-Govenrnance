"""Optional plotting: Matplotlib is imported only when a plot is requested."""

from pathlib import Path

from fan_governance.elections.models import SimulationResult
from fan_governance.output.exporters import results_frame


def plot_results(results: list[SimulationResult], path: str | Path) -> Path:
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise ValueError("Plotting requires the optional plots extra") from error
    frame = results_frame(results)
    if frame.empty:
        raise ValueError("Cannot plot empty results")
    groups = list(frame.groupby("voting_model", sort=True))
    figure, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    for axis, (column, label) in zip(
        axes.flat,
        [
            ("metrics.gini", "Eligible voting power Gini"),
            ("turnout", "Turnout fraction"),
            ("metrics.effective_voters", "Effective number of voters"),
            ("passed", "Proposal pass rate"),
        ],
        strict=True,
    ):
        if column == "passed":
            axis.bar([name for name, _ in groups], [group[column].mean() for _, group in groups])
            axis.set_ylim(0, 1)
        else:
            samples = [group[column].dropna().to_numpy(dtype=float) for _, group in groups]
            axis.boxplot(samples, tick_labels=[name for name, _ in groups])
        axis.set_title(label)
        axis.tick_params(axis="x", rotation=20)
        axis.grid(axis="y", alpha=0.2)
    figure.suptitle("Synthetic fan governance — repeated trial distributions")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=160)
    plt.close(figure)
    return destination
