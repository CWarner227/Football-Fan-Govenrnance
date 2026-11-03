from datetime import date

import pytest

from fan_governance.agents.models import Supporter
from fan_governance.lifecycle.clock import SimulationClock, add_months
from fan_governance.lifecycle.membership import advance_memberships
from fan_governance.lifecycle.scheduler import EventScheduler
from fan_governance.membership.models import Membership
from fan_governance.scenarios.state import Account, IdentityClaim, SimulationState, VotingCredential


def test_calendar_and_stable_event_order():
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)
    clock = SimulationClock(date(2027, 1, 1), 36)
    assert clock.end_day == 1096
    assert clock.month_at(365) == 12
    scheduler = EventScheduler()
    scheduler.schedule(3, "election", priority=50)
    scheduler.schedule(3, "recovery", priority=10)
    scheduler.schedule(3, "age", priority=10)
    day, events = scheduler.pop_day()
    assert day == 3
    assert [e.kind for e in events] == ["recovery", "age", "election"]
    with pytest.raises(ValueError):
        scheduler.schedule(2, "past")


def test_aging_expiry_and_recovery_precede_voting():
    person = Supporter(supporter_id="p")
    account = Account(
        "a",
        IdentityClaim("claim", "p"),
        Membership(member_id="m", supporter_id="p", age_days=0),
        VotingCredential("v", controller_id="attacker", recovery_day=90, restricted_until=90),
        expires_day=90,
    )
    state = SimulationState({"p": person}, {"a": account}, {})
    advance_memberships(state, 90)
    assert account.membership.age_days == 90
    assert not account.membership.active
    assert account.credential.controller_id is None
    assert account.credential.restricted_until is None
