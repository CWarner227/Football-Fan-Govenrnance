"""Default metrics, replaceable or composable without changing the election loop."""

import math
from typing import Any

from fan_governance.elections.models import ElectionData
from fan_governance.metrics.concentration import concentration_metrics
from fan_governance.metrics.participation import participation_metrics
from fan_governance.metrics.representation import representation_metrics


class StandardMetrics:
    def calculate(self, data: ElectionData) -> dict[str, Any]:
        totals = {
            option: math.fsum(
                w for o, w in zip(data.cast_options, data.cast_weights, strict=True) if o == option
            )
            for option in data.options
        }
        total_weight = math.fsum(totals.values())
        if not math.isfinite(total_weight):
            raise ValueError("Aggregate voting weight is nonfinite")
        count = len(data.cast_options)
        counts = {option: data.cast_options.count(option) for option in data.options}
        turnout = count / len(data.eligible_weights) if data.eligible_weights else None
        eligible_weight = math.fsum(data.eligible_weights)
        if not math.isfinite(eligible_weight):
            raise ValueError("Aggregate eligible voting weight is nonfinite")
        weighted_turnout = total_weight / eligible_weight if eligible_weight > 0 else None
        quorum_participation = (
            weighted_turnout if data.quorum_basis == "eligible_weight" else turnout
        )
        equal_share = counts[data.options[0]] / count if count else None
        quorum = quorum_participation is not None and quorum_participation >= data.quorum
        equal_quorum = turnout is not None and turnout >= data.quorum
        equal_passed = bool(
            equal_quorum and equal_share is not None and equal_share >= data.approval_threshold
        )
        weighted_share = totals[data.options[0]] / total_weight if total_weight else None
        weighted_passed = bool(
            quorum and weighted_share is not None and weighted_share >= data.approval_threshold
        )
        result = (
            concentration_metrics(data.eligible_weights)
            | participation_metrics(len(data.eligible_weights), count, total_weight)
            | {
                "weighted_shares": {
                    o: totals[o] / total_weight if total_weight else None for o in data.options
                },
                "unweighted_shares": {
                    o: counts[o] / count if count else None for o in data.options
                },
                "unweighted_counts": counts,
                "weighted_turnout": weighted_turnout,
                "quorum_participation": quorum_participation,
                "quorum_basis": data.quorum_basis,
                "abstentions": data.abstentions,
                "invalid_ballots": data.invalid_ballots,
                "total_supporters": data.population_size,
                "active_members": data.active_member_count,
                "realized_concentration": concentration_metrics(data.cast_weights),
                "equal_vote_approval_share": equal_share,
                "equal_vote_passed": equal_passed,
                "outcome_differs_from_equal": weighted_passed != equal_passed,
                "approval_share_difference_from_equal": weighted_share - equal_share
                if weighted_share is not None and equal_share is not None
                else None,
            }
        )
        if len(data.eligible_identities) == len(data.eligible_weights):
            result["representation"] = representation_metrics(
                data.eligible_identities,
                data.eligible_wealth,
                data.eligible_contributions,
                data.eligible_weights,
                data.cast_identities,
                data.cast_weights,
            )
        return result
