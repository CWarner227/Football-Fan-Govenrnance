"""Frozen scientific inputs shared by all weight strategies in a comparison."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

from pydantic import ConfigDict

from fan_governance.agents.models import Supporter
from fan_governance.membership.models import Membership


class FrozenSupporter(Supporter):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class FrozenMembership(Membership):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


@dataclass(frozen=True)
class Realization:
    participating: Mapping[str, bool]
    preferences: Mapping[str, str | None]

    def __post_init__(self) -> None:
        object.__setattr__(self, "participating", MappingProxyType(dict(self.participating)))
        object.__setattr__(self, "preferences", MappingProxyType(dict(self.preferences)))

    def digest(self) -> str:
        payload = json.dumps(
            [dict(self.participating), dict(self.preferences)],
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class ElectionSnapshot:
    club_id: str
    supporters: Mapping[str, Supporter]
    memberships: Mapping[str, Membership]
    eligible_member_ids: tuple[str, ...]
    proposal_json: str
    realization: Realization
    active_member_count: int
    input_digest: str
    seed: int
    trial: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "supporters", MappingProxyType(dict(self.supporters)))
        object.__setattr__(self, "memberships", MappingProxyType(dict(self.memberships)))
