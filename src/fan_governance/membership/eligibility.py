"""One canonical supporter, one eligible membership within a club."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from fan_governance.agents.models import Supporter
from fan_governance.membership.models import Membership


@dataclass(frozen=True)
class StandardEligibility:
    waiting_period_days: int = 180
    minimum_contribution: float = 0
    minimum_loyalty: float = 0

    def __post_init__(self) -> None:
        if not isinstance(self.waiting_period_days, int) or self.waiting_period_days < 0:
            raise ValueError("waiting_period_days must be a nonnegative integer")
        if (
            not math.isfinite(self.minimum_contribution)
            or self.minimum_contribution < 0
            or not math.isfinite(self.minimum_loyalty)
            or not 0 <= self.minimum_loyalty <= 1
        ):
            raise ValueError("Eligibility contribution/loyalty bounds are invalid")

    def eligible(
        self, supporters: Sequence[Supporter], memberships: Sequence[Membership]
    ) -> list[Membership]:
        canonical = {s.supporter_id for s in supporters}
        people = {s.supporter_id: s for s in supporters}
        seen: set[str] = set()
        selected = []
        for member in sorted(memberships, key=lambda m: m.member_id):
            if (
                member.supporter_id in canonical
                and member.supporter_id not in seen
                and member.active
                and member.verified
                and member.age_days >= self.waiting_period_days
                and member.contribution >= self.minimum_contribution
                and people[member.supporter_id].loyalty >= self.minimum_loyalty
            ):
                seen.add(member.supporter_id)
                selected.append(member)
        return selected
