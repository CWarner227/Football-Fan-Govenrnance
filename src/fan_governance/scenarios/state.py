"""True people, claims, memberships and voting credentials remain distinct."""

from dataclasses import dataclass, field
from typing import Any

from fan_governance.adversarial.base import Attacker
from fan_governance.agents.models import Supporter
from fan_governance.membership.models import Membership


@dataclass
class IdentityClaim:
    claim_id: str
    person_id: str
    fraudulent: bool = False
    resolved_id: str | None = None
    verified: bool = False
    verification_done: bool = False


@dataclass
class VotingCredential:
    credential_id: str
    controller_id: str | None = None
    active: bool = True
    restricted_until: int | None = None
    recovery_day: int | None = None
    replacement_count: int = 0


@dataclass
class Account:
    account_id: str
    claim: IdentityClaim
    membership: Membership
    credential: VotingCredential
    joined_day: int = 0
    expires_day: int | None = None
    last_contribution: float = 0.0
    fee_paid_day: int | None = None

    @property
    def person_id(self) -> str:
        return self.claim.person_id

    @property
    def fraudulent(self) -> bool:
        return self.claim.fraudulent


@dataclass(frozen=True)
class VoteOverride:
    actor_id: str
    option: str
    until_day: int
    reason: str
    force_turnout: bool = False


@dataclass
class SimulationState:
    people: dict[str, Supporter]
    accounts: dict[str, Account]
    attackers: dict[str, Attacker]
    day: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    overrides: dict[str, VoteOverride] = field(default_factory=dict)
    pending_contributions: float = 0.0
    pending_membership_fees: float = 0.0
    pending_administrative_cost: float = 0.0
    economic_state: Any = None

    def record(self, kind: str, *, actor_id: str = "", target_id: str = "", **data) -> None:
        self.events.append(
            {
                "sequence": len(self.events),
                "day": self.day,
                "kind": kind,
                "actor_id": actor_id,
                "target_id": target_id,
                **data,
            }
        )

    def controlled(self, account: Account) -> bool:
        return account.credential.controller_id is not None or any(
            account.person_id in a.controlled_supporters for a in self.attackers.values()
        )
