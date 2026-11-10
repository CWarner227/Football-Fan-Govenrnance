"""Paired multi-period experiments, with attacks isolated from election mechanics."""

import json
from dataclasses import dataclass, field
from hashlib import sha256
from itertools import product
from time import perf_counter

from fan_governance.adversarial.base import Attacker, Resources, SimulationContext
from fan_governance.adversarial.objectives import evaluate_objective
from fan_governance.agents.generator import SyntheticPopulationGenerator
from fan_governance.agents.models import Supporter
from fan_governance.clubs.models import Club
from fan_governance.core.context import RandomStreams, VotingContext
from fan_governance.core.engine import effective_voting_specs, proposal_from_config
from fan_governance.core.registry import default_registry
from fan_governance.defenses.policies import IdentityVerification
from fan_governance.economics import EconomicEngine, initialize_economy
from fan_governance.economics.shocks import shock_effects
from fan_governance.elections.runner import ElectionRunner
from fan_governance.elections.snapshot import Realization
from fan_governance.lifecycle.clock import SimulationClock, add_months
from fan_governance.lifecycle.membership import advance_memberships
from fan_governance.lifecycle.scheduler import EventScheduler
from fan_governance.membership.models import Membership
from fan_governance.metrics.results import StandardMetrics
from fan_governance.scenarios.config import ScenarioConfig
from fan_governance.scenarios.registry import (
    create_attack,
    create_defense,
    default_scenario_registry,
)
from fan_governance.scenarios.state import Account, IdentityClaim, SimulationState, VotingCredential
from fan_governance.scenarios.transitions import TransitionExecutor, apply_defense_action


@dataclass
class ScenarioResults:
    summary: list[dict] = field(default_factory=list)
    elections: list[dict] = field(default_factory=list)
    timeseries: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def expanded_configs(config):
    """Expand strict dotted paths, including list indices, before any trial runs."""
    keys = sorted(config.experiment.grid)
    for values in product(*(config.experiment.grid[k] for k in keys)):
        raw = config.model_dump(mode="json")
        for path, value in zip(keys, values, strict=True):
            node = raw
            parts = path.split(".")
            try:
                for part in parts[:-1]:
                    node = node[int(part)] if isinstance(node, list) else node[part]
            except (KeyError, IndexError, ValueError, TypeError) as error:
                raise ValueError(f"Unknown scenario grid path: {path}") from error
            key = int(parts[-1]) if isinstance(node, list) else parts[-1]
            if isinstance(node, dict) and key not in node:
                # Strategy parameter dictionaries are intentionally extensible.
                if "parameters" not in parts:
                    raise ValueError(f"Unknown scenario grid path: {path}")
            node[key] = value
        candidate = ScenarioConfig.model_validate(raw)
        labels = dict(zip(keys, values, strict=True))
        identity = sha256(json.dumps(labels, sort_keys=True).encode()).hexdigest()[:12]
        yield identity, candidate, labels


class RecordedWeight:
    def __init__(self, strategy, cap=None):
        self.strategy, self.cap, self.weights = strategy, cap, {}

    def calculate_weight(self, supporter, membership, context):
        value = self.strategy.calculate_weight(supporter, membership, context)
        if self.cap is not None:
            value = min(value, self.cap)
        self.weights[supporter.supporter_id] = value
        return value


def _owner(state, account):
    if account.credential.controller_id is not None:
        return account.credential.controller_id
    override = state.overrides.get(account.account_id)
    if override is not None:
        return override.actor_id
    return next(
        (
            a.attacker_id
            for a in state.attackers.values()
            if account.person_id in a.controlled_supporters
        ),
        None,
    )


def _initial_state(population, config, variant):
    people = {s.supporter_id: s.model_copy(deep=True) for s in population.supporters}
    accounts = {}
    for member in population.memberships:
        m = member.model_copy(deep=True)
        accounts[m.member_id] = Account(
            m.member_id,
            IdentityClaim(
                m.supporter_id, m.supporter_id, resolved_id=m.supporter_id, verified=m.verified
            ),
            m,
            VotingCredential(m.member_id),
            joined_day=-m.age_days,
            last_contribution=m.contribution,
        )
    attackers = {}
    if variant not in ("control", "attack_control", "defense_control"):
        for spec in config.attacks:
            attackers[spec.attacker_id] = Attacker(
                spec.attacker_id,
                spec.name,
                spec.objective,
                Resources(spec.financial_budget, spec.operational_budget),
                spec.coordination_level,
                spec.risk_tolerance,
                spec.time_horizon_days,
                flags={
                    "activation_day": spec.parameters.get("activation_day", 0),
                    "hostile_turnout": spec.parameters.get("hostile_turnout", 1),
                },
            )
    return SimulationState(people, accounts, attackers)


def _project(state, config, proposal, streams, registry, turnout_boost, economic_factor):
    """Verification maps claims to perceived canonical people; true IDs remain in state."""
    supporters, memberships, sources = {}, [], {}
    for account in sorted(state.accounts.values(), key=lambda a: a.account_id):
        identity = account.claim.resolved_id or account.claim.claim_id
        person = state.people[account.person_id]
        if identity not in supporters:
            supporters[identity] = person.model_copy(deep=True, update={"supporter_id": identity})
        member = account.membership.model_copy(
            update={
                "supporter_id": identity,
                "verified": account.claim.verified,
                "active": account.membership.active
                and account.credential.active
                and (
                    account.credential.restricted_until is None
                    or account.credential.restricted_until <= state.day
                ),
            }
        )
        memberships.append(member)
        sources[member.member_id] = account
    club = Club(
        club_id="scenario-club",
        name="Synthetic scenario club",
        supporters=list(supporters.values()),
        memberships=memberships,
        governance=proposal.eligibility_rules,
    )
    eligibility = registry.create(
        "eligibility",
        proposal.eligibility_rules.eligibility,
        waiting_period_days=proposal.eligibility_rules.waiting_period_days,
    )
    selected = eligibility.eligible(club.supporters, club.memberships)
    participation = registry.create("participation", config.simulation.participation)
    preference = registry.create("preference", config.simulation.preference)
    participating, preferences, controllers = {}, {}, {}
    context = VotingContext(proposal.proposal_id, streams.trial, streams.seed, proposal.category)
    canonical_accounts = {}
    for account in sorted(state.accounts.values(), key=lambda a: (a.joined_day, a.account_id)):
        canonical_accounts.setdefault(account.person_id, account)
    baseline_draws = {}
    # Canonical true-person keyed streams keep ordinary ballots paired when claims are added.
    for member in selected:
        account = sources[member.member_id]
        person = state.people[account.person_id]
        prefix = f"election.{state.day}.person.{account.person_id}"
        prng, vrng = (
            streams.generator(prefix + ".turnout"),
            streams.generator(prefix + ".preference"),
        )
        if account.person_id not in baseline_draws:
            # Perceived aliases must not create additional independent behavioral draws.
            true_member = canonical_accounts[account.person_id].membership.model_copy(
                update={"supporter_id": account.person_id}
            )
            if config.honest_turnout is None:
                base = participation.participates(person, true_member, context, prng)
                joined = bool(base) or prng.random() < turnout_boost
                joined = joined and prng.random() < economic_factor
            else:
                probability = config.honest_turnout * economic_factor
                joined = prng.random() < probability + (1 - probability) * turnout_boost
            option = preference.choose(person, true_member, proposal, context, vrng)
            baseline_draws[account.person_id] = (joined, option)
        joined, option = baseline_draws[account.person_id]
        # Separate streams keep alias count from changing subsequent hostile draws.
        prng = streams.generator(prefix + ".hostile_turnout")
        vrng = streams.generator(prefix + ".coordination")
        override = state.overrides.get(account.account_id)
        if override is not None and override.until_day < state.day:
            override = None
        controller = account.credential.controller_id
        owner = controller if controller in state.attackers else None
        if owner is None and override is not None and override.actor_id in state.attackers:
            owner = override.actor_id
        if owner is None:
            owner = next(
                (
                    a.attacker_id
                    for a in state.attackers.values()
                    if account.person_id in a.controlled_supporters
                    and state.day >= a.flags.get("activation_day", 0)
                ),
                None,
            )
        if owner is not None:
            actor = state.attackers[owner]
            if controller == owner:
                joined, option = True, actor.objective.get("target", proposal.options[0])
            elif override is not None and override.actor_id == owner:
                joined = joined or override.force_turnout
                option = override.option
            else:
                joined = prng.random() < actor.flags.get("hostile_turnout", 1)
                if vrng.random() < actor.coordination_level:
                    option = actor.objective.get("target", proposal.options[0])
        participating[member.supporter_id] = bool(joined)
        preferences[member.supporter_id] = option
        controllers[member.supporter_id] = owner
    return club, eligibility, Realization(participating, preferences), controllers, sources


def _governance(config, state, policies, streams, elapsed, due):
    proposal = proposal_from_config(config.simulation)
    cap, boost = None, 0.0
    bases = set()
    for index, policy in enumerate(policies):
        ctx = SimulationContext(
            state,
            streams.generator(f"defense.{index}.{state.day}"),
            period_days=elapsed,
            election_due=due,
        )
        effect = policy.apply(ctx)
        for action in effect.actions:
            apply_defense_action(action, state)
        if effect.waiting_period_days is not None:
            proposal.eligibility_rules.waiting_period_days = max(
                proposal.eligibility_rules.waiting_period_days, effect.waiting_period_days
            )
        if effect.vote_cap is not None:
            cap = effect.vote_cap if cap is None else min(cap, effect.vote_cap)
        if effect.quorum is not None:
            proposal.quorum = max(proposal.quorum, effect.quorum)
        if effect.quorum_basis is not None:
            bases.add(effect.quorum_basis)
            proposal.quorum_basis = effect.quorum_basis
        boost = 1 - (1 - boost) * (1 - effect.turnout_boost)
    if len(bases) > 1:
        raise ValueError("Composed quorum policies require a common basis")
    return proposal, cap, boost


def _investors(state, economic_config, *, proposal=None, voting=None, cap=None, month=None):
    """Price explicit rights before funding, then install only accepted funded grants.

    Simultaneous offers assume all due eligible grants are accepted. The resulting
    shares are conservative when another same-date investor declines the offer.
    """
    economy = state.economic_state
    if proposal is not None:
        if voting is None or month is None:
            raise ValueError("Investor offers require a voting strategy and simulated month")
        registry = default_registry()
        eligibility = registry.create(
            "eligibility",
            proposal.eligibility_rules.eligibility,
            waiting_period_days=proposal.eligibility_rules.waiting_period_days,
        )
        supporters, memberships = {}, []
        for account in sorted(state.accounts.values(), key=lambda a: a.account_id):
            identity = account.claim.resolved_id or account.claim.claim_id
            supporters.setdefault(
                identity,
                state.people[account.person_id].model_copy(update={"supporter_id": identity}),
            )
            memberships.append(
                account.membership.model_copy(
                    update={
                        "supporter_id": identity,
                        "verified": account.claim.verified,
                        "active": account.membership.active
                        and account.credential.active
                        and (
                            account.credential.restricted_until is None
                            or account.credential.restricted_until <= state.day
                        ),
                    }
                )
            )
        offered = []
        for spec in economic_config.investors:
            if (
                month < spec.start_month
                or spec.investor_id in economy.investors_considered
                or not spec.voting_rights
                or not economic_config.investor_voting_offer
            ):
                continue
            identity = f"investor:{spec.investor_id}"
            supporters[identity] = Supporter(
                supporter_id=identity, wealth=spec.capital, contribution=spec.capital
            )
            memberships.append(
                Membership(
                    member_id=identity,
                    supporter_id=identity,
                    age_days=0,
                    verified=True,
                    contribution=spec.capital,
                )
            )
            offered.append((spec.investor_id, identity))
        context = VotingContext(proposal.proposal_id, 0, 0, proposal.category)
        weights = {}
        for member in eligibility.eligible(list(supporters.values()), memberships):
            value = voting.calculate_weight(supporters[member.supporter_id], member, context)
            weights[member.supporter_id] = value if cap is None else min(value, cap)
        total = sum(weights.values())
        for investor_id, identity in offered:
            economy.offered_voting_power_share[investor_id] = (
                weights.get(identity, 0) / total if total else 0
            )
    for spec in economic_config.investors:
        identity = f"investor:{spec.investor_id}"
        if spec.investor_id not in economy.investor_voting_rights or identity in state.people:
            continue
        capital = economy.investor_funding[spec.investor_id]
        person = Supporter(supporter_id=identity, wealth=capital, contribution=capital)
        member = Membership(
            member_id=identity,
            supporter_id=identity,
            age_days=0,
            verified=True,
            contribution=capital,
        )
        state.people[identity] = person
        state.accounts[identity] = Account(
            identity,
            IdentityClaim(identity, identity, verified=True, resolved_id=identity),
            member,
            VotingCredential(identity),
            joined_day=state.day,
        )
        state.record("investor_voting_rights", target_id=identity, capital=capital)


def _trajectory(
    config, population, model, variant, streams, scenario_registry, progress_callback=None
):
    registry = default_registry()
    state = _initial_state(population, config, variant)
    strategies = [
        (spec, create_attack(spec.name, spec.parameters, registry=scenario_registry))
        for spec in config.attacks
        if variant not in ("control", "attack_control", "defense_control")
    ]
    policies = (
        [
            create_defense(spec.name, spec.parameters, registry=scenario_registry)
            for spec in config.defenses
        ]
        if variant in ("defended", "defense_control")
        else []
    )
    if not any(p.phase == "identity" for p in policies):
        policies.insert(0, IdentityVerification(strength=0))
    # Stable phase ordering: identity, review, governance, participation.
    policies.sort(
        key=lambda p: {"identity": 0, "review": 1, "governance": 2, "participation": 3}[p.phase]
    )
    economy_config = config.economics.model_copy(deep=True)
    if variant == "control":
        economy_config.shocks = []
    state.economic_state = initialize_economy(
        economy_config, state.people, streams.generator("economics.initialize")
    )
    economy = EconomicEngine(economy_config)
    clock = SimulationClock(**config.timeline.model_dump())
    election_days = {
        (add_months(clock.start_date, month) - clock.start_date).days
        for month in range(
            config.elections.interval_months,
            config.timeline.duration_months + 1,
            config.elections.interval_months,
        )
    }
    days = set(clock.days()) | election_days
    for spec in config.attacks:
        for key in ("start_day", "activation_day"):
            day = spec.parameters.get(key, 0)
            if 0 <= day <= clock.end_day:
                days.add(day)
        interval = spec.parameters.get("joining_interval_days", 0)
        if interval:
            number = spec.parameters.get("number", 10)
            share = spec.parameters.get("hostile_share")
            if share is not None:
                import math

                number = min(
                    number, math.ceil(len(population.memberships) * share / max(1e-12, 1 - share))
                )
            days.update(
                spec.parameters.get("start_day", 0) + i * interval
                for i in range(number)
                if spec.parameters.get("start_day", 0) + i * interval <= clock.end_day
            )
        lead = spec.parameters.get("time_before_election_days")
        if lead is not None:
            days.update(max(0, d - lead) for d in election_days)
    # Economic shocks, renewals, and investor offers retain monthly resolution,
    # even when the requested observation step is yearly.
    days.update(
        (add_months(clock.start_date, m) - clock.start_date).days
        for m in range(config.timeline.duration_months + 1)
    )
    scheduler = EventScheduler()
    scheduled = set(days)
    for day in sorted(days):
        scheduler.schedule(day, "period")
    executor = TransitionExecutor()
    rows, times, previous = [], [], 0
    while scheduler:
        day, scheduled_events = scheduler.pop_day()
        elapsed = day - previous
        advance_memberships(state, day)
        if all(event.kind == "lifecycle" for event in scheduled_events):
            continue
        due = day in election_days
        for spec, strategy in strategies:
            actor = state.attackers[spec.attacker_id]
            actor.flags["next_election_day"] = next(
                (d for d in sorted(election_days) if d >= day), clock.end_day + 1
            )
            if day > actor.time_horizon:
                continue
            ctx = SimulationContext(
                state,
                streams.generator(f"attack.{actor.attacker_id}.{day}"),
                actor,
                elapsed,
                due,
                economy_config.membership_fee * elapsed / 30,
                config.simulation.governance.waiting_period_days,
            )
            for action in strategy.execute(strategy.plan(ctx), ctx).actions:
                executor.apply(action, state)
        proposal, cap, boost = _governance(config, state, policies, streams, elapsed, due)
        # Record the observation baseline after all reviewers see the same change.
        for account in state.accounts.values():
            account.last_contribution = account.membership.contribution
        _investors(
            state,
            economy_config,
            proposal=proposal,
            voting=registry.create("voting", model),
            cap=cap,
            month=clock.month_at(day),
        )
        financial = economy.step(
            state,
            month=clock.month_at(day),
            elapsed_days=elapsed,
            rng=streams.generator(f"economics.{day}"),
        )
        _investors(state, economy_config)
        # Growth and explicitly granted investor rights pass the same identity policy before voting.
        for policy in policies:
            if policy.phase == "identity":
                for action in policy.apply(
                    SimulationContext(state, streams.generator(f"identity.new.{day}"))
                ).actions:
                    apply_defense_action(action, state)
        times.append({"day": day, **financial})
        for account in state.accounts.values():
            for future in (
                account.credential.recovery_day,
                account.credential.restricted_until,
                account.expires_day,
            ):
                if future is not None and day < future <= clock.end_day and future not in scheduled:
                    scheduler.schedule(future, "lifecycle")
                    scheduled.add(future)
        if due:
            shock = shock_effects(economy_config.shocks, clock.month_at(day))
            factor = max(
                0,
                min(1, 1 - config.economic_turnout_sensitivity * (1 - shock["disposable_income"])),
            )
            club, eligibility, realization, controllers, sources = _project(
                state, config, proposal, streams, registry, boost, factor
            )
            weight = RecordedWeight(registry.create("voting", model), cap)
            runner = ElectionRunner(
                weight,
                eligibility,
                registry.create("participation", config.simulation.participation),
                registry.create("preference", config.simulation.preference),
                StandardMetrics(),
            )
            result = runner.run(
                club, proposal, streams, realization=realization, voting_model=model.name
            )
            cast = {
                identity
                for identity in weight.weights
                if realization.participating[identity]
                and realization.preferences[identity] in proposal.options
            }
            total_power, total_cast = (
                sum(weight.weights.values()),
                sum(weight.weights[i] for i in cast),
            )
            actor_metrics = {}
            for actor in state.attackers.values():
                controlled = {i for i, owner in controllers.items() if owner == actor.attacker_id}
                actor_metrics[actor.attacker_id] = {
                    "attacker_power_share": sum(weight.weights[i] for i in controlled) / total_power
                    if total_power
                    else 0,
                    "attacker_vote_share": sum(weight.weights[i] for i in cast & controlled)
                    / total_cast
                    if total_cast
                    else 0,
                    "attacker_count_share": len(cast & controlled) / len(cast) if cast else 0,
                    "financial_spent": actor.resources.financial_spent,
                    "proposal_passed": result.passed,
                    "quorum_achieved": result.quorum_achieved,
                    "disruption_count": sum(
                        e["kind"] == "attack_compromise"
                        and e.get("success", False)
                        and e["actor_id"] == actor.attacker_id
                        for e in state.events
                    ),
                }
            hostile = {i for i, owner in controllers.items() if owner is not None}
            compromised_ids = {
                m.supporter_id
                for m in eligibility.eligible(club.supporters, club.memberships)
                if sources[m.member_id].credential.controller_id is not None
            }
            rows.append(
                {
                    "day": day,
                    "passed": result.passed,
                    "quorum_achieved": result.quorum_achieved,
                    "turnout": result.turnout,
                    "votes_cast": result.votes_cast,
                    "eligible_voter_count": result.eligible_voter_count,
                    "unauthorized_votes_attempted": sum(
                        a.credential.controller_id is not None and a.membership.active
                        for a in state.accounts.values()
                    ),
                    "unauthorized_votes_accepted": len(cast & compromised_ids),
                    "attacker_power_share": sum(weight.weights[i] for i in hostile) / total_power
                    if total_power
                    else 0,
                    "attacker_vote_share": sum(weight.weights[i] for i in cast & hostile)
                    / total_cast
                    if total_cast
                    else 0,
                    "attacker_count_share": len(cast & hostile) / len(cast) if cast else 0,
                    "financial_spent": sum(
                        a.resources.financial_spent for a in state.attackers.values()
                    ),
                    "actor_metrics": actor_metrics,
                    "ballots": {
                        sources[m.member_id].person_id: realization.preferences[m.supporter_id]
                        for m in eligibility.eligible(club.supporters, club.memberships)
                        if m.supporter_id in cast
                    },
                    **result.metrics,
                }
            )
        previous = day
        if progress_callback is not None:
            progress_callback((day + 1) / (clock.end_day + 1))
    return rows, times, state


def run_scenario(
    config: ScenarioConfig, *, registry=None, progress_callback=None
) -> ScenarioResults:
    started = perf_counter()
    output = ScenarioResults()
    registry = registry if registry is not None else default_scenario_registry()
    expanded = list(expanded_configs(config))
    total_trials = sum(c.experiment.trials for _, c, _ in expanded)
    total_trajectories = sum(
        c.experiment.trials
        * len(effective_voting_specs(c.simulation))
        * (3 + bool(c.attacks and c.economics.shocks) + bool(c.attacks and c.defenses))
        for _, c, _ in expanded
    )
    completed_trials = completed_trajectories = 0

    def report(fraction=0):
        if progress_callback is not None:
            progress_callback(
                {
                    "completed_trials": completed_trials,
                    "total_trials": total_trials,
                    "completed_trajectories": completed_trajectories + fraction,
                    "total_trajectories": total_trajectories,
                }
            )

    def trajectory(*args):
        nonlocal completed_trajectories
        result = _trajectory(*args, progress_callback=report if progress_callback else None)
        completed_trajectories += 1
        report()
        return result

    for _, candidate, _ in expanded:
        for spec in candidate.attacks:
            create_attack(spec.name, spec.parameters, registry=registry)
            evaluate_objective(spec.objective, {})
        for spec in candidate.defenses:
            create_defense(spec.name, spec.parameters, registry=registry)
        bases = {
            d.parameters.get("basis", "eligible_members")
            for d in candidate.defenses
            if d.name == "quorum"
        }
        if len(bases) > 1:
            raise ValueError("Composed quorum policies require a common basis")
        for model in effective_voting_specs(candidate.simulation):
            default_registry().create("voting", model)
    report()
    for grid_id, candidate, labels in expanded:
        for trial in range(candidate.experiment.trials):
            streams = RandomStreams(candidate.experiment.seed, trial)
            population = SyntheticPopulationGenerator().generate(
                candidate.simulation.population,
                RandomStreams(
                    candidate.simulation.population.seed
                    if candidate.simulation.population.seed is not None
                    else streams.seed,
                    trial,
                ),
            )
            for model in effective_voting_specs(candidate.simulation):
                paired = {}
                stressed_reference = None
                if candidate.attacks and candidate.economics.shocks:
                    reference_rows, _, _ = trajectory(
                        candidate, population, model, "attack_control", streams, registry
                    )
                    stressed_reference = {r["day"]: r for r in reference_rows}
                defense_reference = None
                if candidate.attacks and candidate.defenses:
                    reference_rows, _, _ = trajectory(
                        candidate, population, model, "defense_control", streams, registry
                    )
                    defense_reference = {r["day"]: r for r in reference_rows}
                for variant in ("control", "unprotected", "defended"):
                    ids = {
                        "scenario": candidate.name,
                        "grid_id": grid_id,
                        "trial": trial,
                        "voting_model": model.name,
                        "variant": variant,
                    }
                    rows, times, state = trajectory(
                        candidate, population, model, variant, streams, registry
                    )
                    paired[variant] = rows
                    paired[variant + "_times"] = times
                    baseline = (
                        stressed_reference
                        if variant != "control" and stressed_reference is not None
                        else {r["day"]: r for r in paired["control"]}
                    )
                    if variant == "defended" and defense_reference is not None:
                        baseline = defense_reference
                    for row in rows:
                        base = baseline[row["day"]]
                        row["outcome_changed"] = row["passed"] != base["passed"]
                        row["votes_shifted"] = sum(
                            identity in base["ballots"] and option != base["ballots"][identity]
                            for identity, option in row["ballots"].items()
                        )
                        successes = []
                        for spec in candidate.attacks if variant != "control" else []:
                            metrics = row["actor_metrics"][spec.attacker_id]
                            metrics.update(
                                baseline_passed=base["passed"],
                                baseline_quorum=base["quorum_achieved"],
                                votes_shifted=row["votes_shifted"],
                            )
                            metrics["capture_success"] = evaluate_objective(spec.objective, metrics)
                            successes.append(metrics["capture_success"])
                        row["capture_success"] = any(successes)
                        output.elections.append(
                            ids | {k: v for k, v in row.items() if k != "ballots"}
                        )
                    output.timeseries.extend(ids | row for row in times)
                    output.events.extend(ids | event for event in state.events)
                    captured = [r for r in rows if r["capture_success"]]
                    verifies = [e for e in state.events if e["kind"] == "defense_verify"]
                    reviews = [e for e in state.events if e["kind"] == "defense_review"]
                    genuine = [e for e in verifies if not e.get("fraudulent", False)]
                    fraud = [e for e in verifies if e.get("fraudulent", False)]
                    legit_reviews = [e for e in reviews if not e.get("malicious", False)]
                    bad_reviews = [e for e in reviews if e.get("malicious", False)]
                    last = rows[-1]
                    summary = (
                        ids
                        | labels
                        | {k: v for k, v in last.items() if k not in ("ballots", "actor_metrics")}
                    )
                    summary.update({k: v for k, v in times[-1].items() if k != "day"})
                    summary.update(state.economic_state.cumulative_ledger)
                    total_attempts = sum(e["kind"] == "attack_influence" for e in state.events)
                    successes = sum(
                        e["kind"] == "attack_influence"
                        and e.get("success", False)
                        and not e.get("detected", False)
                        for e in state.events
                    )
                    compromised = sum(
                        e["kind"] == "attack_compromise"
                        and e.get("success", False)
                        and not e.get("detected", False)
                        for e in state.events
                    )
                    recovered = sum(e["kind"] == "credential_recovered" for e in state.events)
                    recovery_time = None
                    if candidate.economics.shocks and variant != "control":
                        clock = SimulationClock(**candidate.timeline.model_dump())
                        end_month = max(
                            s.start_month + s.duration_months for s in candidate.economics.shocks
                        )
                        shock_end = (
                            add_months(clock.start_date, end_month) - clock.start_date
                        ).days
                        reference = {r["day"]: r for r in paired["control_times"]}
                        recovered_rows = [
                            r
                            for r in times
                            if r["day"] >= shock_end
                            and r.get("operating_revenue", 0)
                            >= 0.95
                            * reference.get(r["day"], {}).get("operating_revenue", float("inf"))
                        ]
                        if recovered_rows:
                            recovery_time = recovered_rows[0]["day"] - shock_end
                    summary.update(
                        capture_success=bool(captured),
                        hostile_population_share=sum(
                            any(pid in a.controlled_supporters for a in state.attackers.values())
                            for pid in state.people
                        )
                        / len(state.people)
                        if state.people
                        else 0,
                        honest_turnout=candidate.honest_turnout,
                        detection_rate=sum(e.get("flagged", False) for e in bad_reviews)
                        / len(bad_reviews)
                        if bad_reviews
                        else None,
                        time_to_capture=captured[0]["day"] if captured else None,
                        financial_cost_of_capture=captured[0]["financial_spent"]
                        if captured
                        else None,
                        proposals_influenced=sum(r["outcome_changed"] for r in rows) / len(rows),
                        fraudulent_identities_detected=sum(
                            not e.get("accepted", False) for e in fraud
                        ),
                        fraudulent_identities_accepted=sum(e.get("accepted", False) for e in fraud),
                        legitimate_rejection_rate=sum(not e.get("accepted", False) for e in genuine)
                        / len(genuine)
                        if genuine
                        else None,
                        false_positive_rate=sum(e.get("flagged", False) for e in legit_reviews)
                        / len(legit_reviews)
                        if legit_reviews
                        else None,
                        false_negative_rate=sum(not e.get("flagged", False) for e in bad_reviews)
                        / len(bad_reviews)
                        if bad_reviews
                        else None,
                        legitimate_supporters_restricted=sum(
                            e.get("restricted_until") is not None for e in legit_reviews
                        ),
                        administrative_cost=state.economic_state.cumulative_ledger.get(
                            "administrative_cost",
                            sum(
                                e.get("administrative_cost", 0)
                                for e in state.events
                                if e["kind"].startswith("defense_")
                            ),
                        ),
                        defense_administrative_cost=sum(
                            e.get("administrative_cost", 0)
                            for e in state.events
                            if e["kind"].startswith("defense_")
                        ),
                        influence_attempts=total_attempts,
                        successful_influence=successes,
                        influence_detection_rate=sum(
                            e["kind"] == "attack_influence" and e.get("detected", False)
                            for e in state.events
                        )
                        / total_attempts
                        if total_attempts
                        else None,
                        cost_per_shifted_vote=last["financial_spent"]
                        / sum(r["votes_shifted"] for r in rows)
                        if sum(r["votes_shifted"] for r in rows)
                        else None,
                        credentials_compromised=compromised,
                        credentials_recovered=recovered,
                        unauthorized_votes_attempted=sum(
                            r["unauthorized_votes_attempted"] for r in rows
                        ),
                        unauthorized_votes_accepted=sum(
                            r["unauthorized_votes_accepted"] for r in rows
                        ),
                        fraudulent_identity_detection_rate=sum(
                            not e.get("accepted", False) for e in fraud
                        )
                        / len(fraud)
                        if fraud
                        else None,
                        hostile_membership_survival=sum(
                            a.membership.active and state.controlled(a)
                            for a in state.accounts.values()
                        )
                        / sum(state.controlled(a) for a in state.accounts.values())
                        if any(state.controlled(a) for a in state.accounts.values())
                        else None,
                        recovery_time_after_shocks_days=recovery_time,
                        financially_survived=not any(r.get("insolvent", False) for r in times),
                    )
                    output.summary.append(summary)
                triplet = output.summary[-3:]
                control, unprotected, defended = triplet
                defended["participation_impact"] = (defended["turnout"] or 0) - (
                    unprotected["turnout"] or 0
                )
                # Trial paired outcome, aggregate relative probability reduction computed on export.
                defended["capture_prevented"] = (
                    unprotected["capture_success"] and not defended["capture_success"]
                )
            completed_trials += 1
            report()
    from fan_governance.output.provenance import source_provenance

    output.metadata = {
        "schema_version": "phase3-v1",
        "seed": config.experiment.seed,
        "trials": config.experiment.trials,
        "grid_cells": len(expanded),
        "elapsed_seconds": perf_counter() - started,
        "source": source_provenance(),
        "random_stream_scheme": "sha256-v1; true-person keyed ballots",
        "proposal_counterfactual": "no attack, same configured shocks and same variant defenses",
        "economic_counterfactual": "no attack and no shocks",
        "event_order": [
            "age/recover",
            "attacks",
            "identity/review/policies",
            "economics",
            "new identity verification",
            "election",
        ],
        "synthetic": True,
    }
    return output
