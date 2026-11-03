from pydantic import Field

from fan_governance.core.config import Nonnegative, ValidatedModel


class Membership(ValidatedModel):
    member_id: str = Field(min_length=1)
    supporter_id: str = Field(min_length=1)
    age_days: int = Field(default=365, ge=0)
    verified: bool = True
    active: bool = True
    contribution: Nonnegative = 0
