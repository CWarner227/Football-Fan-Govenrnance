def participation_metrics(
    eligible_count: int, voter_count: int, total_weight: float
) -> dict[str, int | float | None]:
    turnout = voter_count / eligible_count if eligible_count else None
    return {
        "eligible_member_count": eligible_count,
        "voter_count": voter_count,
        "turnout": turnout,
        "turnout_percentage": 100 * turnout if turnout is not None else None,
        "total_weight_cast": total_weight,
    }
