"""Central event interpreter enforces resource conservation and scoped changes."""

import math

from fan_governance.adversarial.base import AttackAction
from fan_governance.agents.models import Supporter
from fan_governance.defenses.base import DefenseAction
from fan_governance.membership.models import Membership
from fan_governance.scenarios.state import (
    Account,
    IdentityClaim,
    SimulationState,
    VoteOverride,
    VotingCredential,
)


class TransitionExecutor:
    def __init__(self):
        self.handlers = {
            "join": self._join,
            "contribute": self._contribute,
            "recruit": self._recruit,
            "influence": self._influence,
            "compromise": self._compromise,
            "expire": self._expire,
            "maintain": self._maintain,
        }

    def apply(self, action: AttackAction, state: SimulationState) -> bool:
        if action.kind not in self.handlers or action.actor_id not in state.attackers:
            raise ValueError("Unknown transition or attacker")
        actor = state.attackers[action.actor_id]
        self._validate(action, state)
        if not actor.resources.can_spend(action.financial_cost, action.operational_cost):
            state.record(
                "resource_rejected",
                actor_id=action.actor_id,
                target_id=action.target_id,
                action=action.kind,
            )
            return False
        actor.resources.spend(action.financial_cost, action.operational_cost)
        self.handlers[action.kind](action, state)
        state.record(
            "attack_" + action.kind,
            actor_id=action.actor_id,
            target_id=action.target_id,
            financial_cost=action.financial_cost,
            operational_cost=action.operational_cost,
            **action.data,
        )
        return True

    @staticmethod
    def _validate(action, state):
        """Check all handler inputs and accounting results before the first mutation."""
        actor = state.attackers[action.actor_id]
        actor.resources.can_spend(action.financial_cost, action.operational_cost)
        schemas = {
            "join": {
                "person_id",
                "contribution",
                "wealth",
                "fraudulent",
                "activation_day",
                "hostile_turnout",
                "account_creation_cost",
                "membership_fee",
            },
            "contribute": {"amount"},
            "recruit": {"activation_day", "hostile_turnout"},
            "influence": {"success", "detected", "option", "until_day", "force_turnout", "mode"},
            "compromise": {"success", "detected", "recovery_day"},
            "expire": set(),
            "maintain": {"membership_fee"},
        }
        if not isinstance(action.data, dict) or action.data.keys() - schemas[action.kind]:
            raise ValueError("Unknown transition data fields")
        if not isinstance(action.target_id, str) or not action.target_id:
            raise ValueError("Transition requires a nonempty account identifier")
        for key in ("success", "detected", "force_turnout", "fraudulent"):
            if key in action.data and type(action.data[key]) is not bool:
                raise ValueError(f"{key} must be a boolean")
        for key in ("activation_day", "until_day", "recovery_day"):
            if key in action.data:
                value = action.data[key]
                if key == "recovery_day" and value is None:
                    continue
                if type(value) is not int or value < 0:
                    raise ValueError(f"{key} must be a nonnegative integer day")
        if "hostile_turnout" in action.data:
            _nonnegative("hostile_turnout", action.data["hostile_turnout"])
            if action.data["hostile_turnout"] > 1:
                raise ValueError("hostile_turnout must lie in [0, 1]")
        if "mode" in action.data and action.data["mode"] not in ("financial", "coercive"):
            raise ValueError("Influence mode must be financial or coercive")
        if action.kind == "join":
            contribution = action.data.get("contribution", 0)
            for key in ("contribution", "account_creation_cost", "membership_fee", "wealth"):
                _nonnegative(key, action.data.get(key, contribution if key == "wealth" else 0))
            minimum = (
                contribution
                + action.data.get("account_creation_cost", 0)
                + action.data.get("membership_fee", 0)
            )
            person_id = action.data.get("person_id", "")
            if (
                not isinstance(person_id, str)
                or not person_id
                or action.target_id in state.accounts
                or not person_id.startswith(action.actor_id + ":")
            ):
                raise ValueError("Join cannot overwrite an account or impersonate another actor")
            if person_id in state.people and person_id not in actor.controlled_supporters:
                raise ValueError("Attacker does not own that synthetic person")
            if not math.isfinite(minimum) or action.financial_cost < minimum:
                raise ValueError("Join costs cannot underfund contributions or creation")
            if (
                not math.isfinite(action.data.get("wealth", contribution))
                or action.data.get("wealth", contribution) < contribution
            ):
                raise ValueError("Joined supporter wealth must fund their contribution")
            old = state.people.get(person_id)
            total_contribution = (old.contribution if old is not None else 0) + contribution
            _nonnegative("total person contribution", total_contribution)
            Supporter(
                supporter_id=person_id,
                wealth=max(old.wealth, total_contribution)
                if old is not None
                else action.data.get("wealth", contribution),
                contribution=total_contribution,
                is_adversarial=True,
            )
            Membership(
                member_id=action.target_id, supporter_id=person_id, contribution=contribution
            )
            _nonnegative("pending contributions", state.pending_contributions + contribution)
            _nonnegative(
                "pending membership fees",
                state.pending_membership_fees + action.data.get("membership_fee", 0),
            )
        else:
            if action.target_id not in state.accounts:
                raise ValueError("Transition targets an unknown account")
            account = state.accounts[action.target_id]
            if account.person_id not in state.people:
                raise ValueError("Account refers to an unknown person")
            if (
                action.kind in ("contribute", "expire", "maintain")
                and account.person_id not in actor.controlled_supporters
            ):
                raise ValueError("Attacker cannot spend or expire unrelated memberships")
            if action.kind in ("contribute", "maintain"):
                if action.kind == "contribute" and "amount" not in action.data:
                    raise ValueError("Contribution requires an amount")
                required = (
                    action.data.get("amount", 0)
                    if action.kind == "contribute"
                    else action.data.get("membership_fee", 0)
                )
                _nonnegative("required payment", required)
                if action.financial_cost < required:
                    raise ValueError("Transition cannot create contribution or fee money")
                if action.kind == "contribute":
                    person = state.people[account.person_id]
                    for key, value in (
                        ("person wealth", person.wealth + required),
                        ("person contribution", person.contribution + required),
                        ("membership contribution", account.membership.contribution + required),
                        ("pending contributions", state.pending_contributions + required),
                    ):
                        _nonnegative(key, value)
                else:
                    _nonnegative(
                        "pending membership fees", state.pending_membership_fees + required
                    )
            if action.kind in ("influence", "compromise") and "success" not in action.data:
                raise ValueError("Investigation outcome requires a success boolean")
            if action.kind == "influence":
                if (
                    not isinstance(action.data.get("option"), str)
                    or not action.data["option"]
                    or "until_day" not in action.data
                    or action.data["until_day"] <= state.day
                ):
                    raise ValueError("Influence requires an option and finite future expiry")
            if action.kind == "compromise":
                recovery = action.data.get("recovery_day")
                if recovery is not None and recovery < state.day:
                    raise ValueError("Recovery cannot be scheduled in the past")

    def _join(self, action, state):
        data, actor = action.data, state.attackers[action.actor_id]
        person_id = data["person_id"]
        contribution = data.get("contribution", 0)
        if person_id not in state.people:
            state.people[person_id] = Supporter(
                supporter_id=person_id,
                wealth=data.get("wealth", contribution),
                contribution=0,
                is_adversarial=True,
            )
        person = state.people[person_id]
        # Transfer from the separately charged attacker wallet into committed assets.
        person.wealth = max(person.wealth, person.contribution + contribution)
        person.contribution += contribution
        member = Membership(
            member_id=action.target_id,
            supporter_id=person_id,
            age_days=0,
            verified=False,
            contribution=contribution,
        )
        claim = IdentityClaim(
            action.target_id + ":claim", person_id, fraudulent=data.get("fraudulent", False)
        )
        state.accounts[action.target_id] = Account(
            action.target_id,
            claim,
            member,
            VotingCredential(action.target_id + ":credential"),
            joined_day=state.day,
        )
        actor.controlled_supporters.add(person_id)
        actor.controlled_credentials.add(action.target_id + ":credential")
        state.pending_contributions += contribution
        fee = data.get("membership_fee", 0)
        if fee:
            state.pending_membership_fees += fee
            state.accounts[action.target_id].fee_paid_day = state.day

    def _contribute(self, action, state):
        account = state.accounts[action.target_id]
        amount = action.data["amount"]
        person = state.people[account.person_id]
        person.wealth += amount
        person.contribution += amount
        account.membership.contribution += amount
        state.pending_contributions += amount

    def _recruit(self, action, state):
        person = state.people[state.accounts[action.target_id].person_id]
        person.is_adversarial = True
        actor = state.attackers[action.actor_id]
        actor.controlled_supporters.add(person.supporter_id)
        actor.controlled_credentials.add(state.accounts[action.target_id].credential.credential_id)

    def _influence(self, action, state):
        if action.data["success"] and not action.data.get("detected", False):
            state.overrides[action.target_id] = VoteOverride(
                action.actor_id,
                action.data["option"],
                action.data["until_day"],
                "influence",
                action.data.get("force_turnout", False),
            )

    def _compromise(self, action, state):
        if action.data["success"] and not action.data.get("detected", False):
            credential = state.accounts[action.target_id].credential
            credential.controller_id = action.actor_id
            credential.recovery_day = action.data.get("recovery_day")
            credential.replacement_count += 1
            state.attackers[action.actor_id].controlled_credentials.add(credential.credential_id)

    def _expire(self, action, state):
        state.accounts[action.target_id].membership.active = False

    def _maintain(self, action, state):
        state.pending_membership_fees += action.data.get("membership_fee", 0)
        state.accounts[action.target_id].fee_paid_day = state.day


def _nonnegative(name, value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{name} must be finite and nonnegative")


def apply_defense_action(action: DefenseAction, state: SimulationState) -> None:
    _nonnegative("Administrative costs", action.administrative_cost)
    _nonnegative(
        "Pending administrative costs",
        state.pending_administrative_cost + action.administrative_cost,
    )
    reserved = {"kind", "day", "sequence", "actor_id", "target_id", "administrative_cost"}
    if not isinstance(action.data, dict) or reserved & action.data.keys():
        raise ValueError("Defense action contains invalid event fields")
    if action.kind not in ("verify", "review", "administrative"):
        raise ValueError("Unknown defensive transition")
    if action.kind in ("verify", "review") and action.target_id not in state.accounts:
        raise ValueError("Defense targets an unknown account")
    if action.kind == "verify":
        if type(action.data.get("accepted")) is not bool or "resolved_id" not in action.data:
            raise ValueError("Verification requires accepted and resolved_id")
        resolved = action.data["resolved_id"]
        if action.data["accepted"] and (not isinstance(resolved, str) or not resolved):
            raise ValueError("Accepted verification requires a nonempty resolved identity")
        if not action.data["accepted"] and resolved is not None:
            raise ValueError("Rejected verification cannot resolve an identity")
    if action.kind == "review" and action.data.get("restricted_until") is not None:
        until = action.data["restricted_until"]
        if (
            type(until) is not int
            or until <= state.day
            or action.data.get("confirmed") is not True
            or action.data.get("flagged") is not True
            or action.data.get("appeal_success") is True
            or action.data.get("review_policy")
            not in ("temporary_restriction", "escalated_verification")
        ):
            raise ValueError(
                "Restriction requires confirmed flagged review and finite future expiry"
            )
    if action.kind == "verify":
        account = state.accounts[action.target_id]
        account.claim.verified = bool(action.data["accepted"])
        account.claim.resolved_id = action.data["resolved_id"]
        account.claim.verification_done = True
        account.membership.verified = account.claim.verified
    elif action.kind == "review":
        account = state.accounts[action.target_id]
        until = action.data.get("restricted_until")
        if until is not None:
            account.credential.restricted_until = max(
                account.credential.restricted_until or 0, until
            )
    elif action.kind != "administrative":
        raise ValueError("Unknown defensive transition")
    state.pending_administrative_cost += action.administrative_cost
    state.record(
        "defense_" + action.kind,
        target_id=action.target_id,
        administrative_cost=action.administrative_cost,
        **action.data,
    )
