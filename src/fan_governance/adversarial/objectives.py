"""Operational simulated capture definitions, distinct from permanent legal control."""

import math
from collections.abc import Mapping


def evaluate_objective(spec: Mapping, metrics: Mapping) -> bool:
    """Missing observations never count as success; proposal effects use paired controls."""
    kind = spec.get("type", "majority_cast")
    if kind == "board_seats":
        raise ValueError("board_seats is an unimplemented future objective")
    threshold = float(
        spec.get(
            "threshold",
            0.5 if kind in {"majority_cast", "voting_power_threshold", "power_threshold"} else 1,
        )
    )
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError("Objective threshold must be finite and nonnegative")
    share = metrics.get("attacker_vote_share")
    changed = spec.get("require_outcome_change", True)
    if kind == "majority_cast":
        return share is not None and share > threshold
    if kind in {"voting_power_threshold", "power_threshold"}:
        value = metrics.get("attacker_power_share")
        return value is not None and value >= threshold
    if kind in {"pass_target", "block_target"}:
        passed = metrics.get("proposal_passed")
        baseline = metrics.get("baseline_passed")
        desired = kind == "pass_target"
        return (
            passed is desired
            and share is not None
            and share > 0
            and (not changed or baseline is (not desired))
        )
    if kind == "prevent_quorum":
        return metrics.get("quorum_achieved") is False and (
            not changed or metrics.get("baseline_quorum") is True
        )
    if kind == "disruption":
        value = metrics.get("disruption_count")
        return value is not None and value >= threshold
    if kind == "influence_per_cost":
        cost = metrics.get("financial_spent")
        return cost is not None and cost > 0 and share is not None and share / cost >= threshold
    raise ValueError(f"Unknown attacker objective {kind!r}")
