from typing import Self

from pydantic import Field, model_validator

from fan_governance.agents.models import Supporter
from fan_governance.core.config import GovernanceConfig, Nonnegative, ValidatedModel
from fan_governance.membership.models import Membership


class Club(ValidatedModel):
    club_id: str
    name: str
    supporters: list[Supporter] = Field(default_factory=list)
    memberships: list[Membership] = Field(default_factory=list)
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)
    financial_attributes: dict[str, Nonnegative] = Field(default_factory=dict)

    @model_validator(mode="after")
    def canonical_identities(self) -> Self:
        identities = {s.supporter_id for s in self.supporters}
        if len(identities) != len(self.supporters):
            raise ValueError("Duplicate canonical supporter identities")
        if len({m.member_id for m in self.memberships}) != len(self.memberships):
            raise ValueError("Duplicate member record identifiers")
        if any(m.supporter_id not in identities for m in self.memberships):
            raise ValueError("Membership references an unknown supporter")
        people = {s.supporter_id: s for s in self.supporters}
        for member in self.memberships:
            supporter = people[member.supporter_id]
            if (
                member.contribution > supporter.wealth
                and not supporter.allow_unfunded_contributions
            ):
                raise ValueError(
                    "Membership contribution cannot exceed supporter wealth without an explicit override"
                )
        return self
