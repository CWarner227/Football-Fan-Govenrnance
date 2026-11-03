import pandas as pd

from fan_governance.elections.models import SimulationResult
from fan_governance.output.exporters import results_frame


def comparison_summary(results: list[SimulationResult]) -> pd.DataFrame:
    """Means and pass rates; undefined statistics remain missing, never filled with zero."""
    frame = results_frame(results)
    if frame.empty:
        return pd.DataFrame()
    return (
        frame.groupby(["scenario_id", "voting_model"], sort=True)
        .agg(
            trials=("trial_id", "count"),
            average_turnout=("turnout", "mean"),
            average_effective_voters=("metrics.effective_voters", "mean"),
            average_gini=("metrics.gini", "mean"),
            average_max_power_share=("metrics.max_power_share", "mean"),
            average_top_1_share=("metrics.top_1_share", "mean"),
            average_top_5_share=("metrics.top_5_share", "mean"),
            average_top_10_share=("metrics.top_10_share", "mean"),
            pass_rate=("passed", "mean"),
            average_election_seconds=("execution_metadata.elapsed_seconds", "mean"),
            disagreement_with_equal_rate=("metrics.outcome_differs_from_equal", "mean"),
            average_bottom_50_wealth_power=(
                "metrics.representation.potential.bottom_50_wealth_power_share",
                "mean",
            ),
            average_top_10_wealth_power=(
                "metrics.representation.potential.top_10_wealth_power_share",
                "mean",
            ),
            average_top_1_wealth_power=(
                "metrics.representation.potential.top_1_wealth_power_share",
                "mean",
            ),
            proposal_category=("execution_metadata.proposal_category", "first"),
        )
        .reset_index()
    )
