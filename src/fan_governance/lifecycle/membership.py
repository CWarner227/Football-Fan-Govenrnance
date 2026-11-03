"""Age memberships and restore expired credential restrictions before elections."""

from fan_governance.scenarios.state import SimulationState


def advance_memberships(state: SimulationState, day: int) -> None:
    if day < state.day:
        raise ValueError("Simulation time cannot move backwards")
    elapsed = day - state.day
    state.day = day
    for account in state.accounts.values():
        account.membership.age_days += elapsed
        if (
            account.expires_day is not None
            and day >= account.expires_day
            and account.membership.active
        ):
            account.membership.active = False
            state.record("membership_expired", target_id=account.account_id)
        credential = account.credential
        if credential.restricted_until is not None and credential.restricted_until <= day:
            credential.restricted_until = None
            state.record("restriction_expired", target_id=account.account_id)
        if credential.recovery_day is not None and credential.recovery_day <= day:
            owner = credential.controller_id
            credential.controller_id = None
            credential.recovery_day = None
            state.record("credential_recovered", actor_id=owner or "", target_id=account.account_id)
    for identity in list(state.overrides):
        if state.overrides[identity].until_day <= day:
            del state.overrides[identity]
