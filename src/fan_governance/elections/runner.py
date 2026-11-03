"""Election mechanics; all model behavior enters through injected interfaces."""

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from time import perf_counter
from types import MappingProxyType
from typing import Any

from fan_governance.clubs.models import Club
from fan_governance.core.context import RandomStreams, VotingContext
from fan_governance.core.interfaces import (
    EligibilityPolicy,
    MetricCalculator,
    ParticipationModel,
    PreferenceModel,
    VotingStrategy,
)
from fan_governance.elections.models import ElectionData, GovernanceProposal, SimulationResult
from fan_governance.elections.snapshot import (
    ElectionSnapshot,
    FrozenMembership,
    FrozenSupporter,
    Realization,
)


@dataclass
class ElectionRunner:
    voting: VotingStrategy
    eligibility: EligibilityPolicy
    participation: ParticipationModel
    preference: PreferenceModel
    metrics: MetricCalculator

    def realize(
        self,
        club: Club,
        proposal: GovernanceProposal,
        streams: RandomStreams,
        *,
        selected_memberships=None,
    ) -> Realization:
        """Draw before weighting. Canonical records preserve pairing across rule changes."""
        participation_rng = streams.generator("participation")
        preference_rng = streams.generator("preferences")
        context = VotingContext(
            proposal.proposal_id,
            streams.trial,
            streams.seed,
            proposal.category,
            getattr(proposal, "metadata", {}),
        )
        supporters = {s.supporter_id: s for s in club.supporters}
        canonical_memberships = {}
        for m in sorted(club.memberships, key=lambda m: m.member_id):
            canonical_memberships.setdefault(m.supporter_id, m)
        selected = (
            self.eligibility.eligible(club.supporters, club.memberships)
            if selected_memberships is None
            else selected_memberships
        )
        for member in selected:
            canonical_memberships[member.supporter_id] = member
        participating, preferences = {}, {}
        for identity, member in sorted(canonical_memberships.items()):
            supporter = supporters[identity]
            participating[identity] = self.participation.participates(
                supporter, member, context, participation_rng
            )
            preferences[identity] = self.preference.choose(
                supporter, member, proposal, context, preference_rng
            )
        return Realization(participating, preferences)

    def prepare(
        self,
        club: Club,
        proposal: GovernanceProposal,
        streams: RandomStreams,
        *,
        realization: Realization | None = None,
    ) -> ElectionSnapshot:
        club.canonical_identities()
        supporters = {s.supporter_id: FrozenSupporter(**s.model_dump()) for s in club.supporters}
        memberships = {m.member_id: FrozenMembership(**m.model_dump()) for m in club.memberships}
        eligible = tuple(
            self.eligibility.eligible(tuple(supporters.values()), tuple(memberships.values()))
        )
        seen = set()
        for member in eligible:
            if (
                member.supporter_id in seen
                or member.supporter_id not in supporters
                or memberships.get(member.member_id) != member
            ):
                raise ValueError("Eligibility policy returned duplicate or unknown membership")
            seen.add(member.supporter_id)
        # Serialize before replacing extension dictionaries by immutable views.
        proposal_json = proposal.model_dump_json()
        payload = json.dumps(
            {
                "club_id": club.club_id,
                "supporters": [
                    s.model_dump(mode="json")
                    for s in sorted(supporters.values(), key=lambda s: s.supporter_id)
                ],
                "memberships": [
                    m.model_dump(mode="json")
                    for m in sorted(memberships.values(), key=lambda m: m.member_id)
                ],
                "proposal": json.loads(proposal_json) | {"voting_method": None},
                "eligible": [m.member_id for m in eligible],
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        for supporter in supporters.values():
            object.__setattr__(
                supporter, "attributes", MappingProxyType(dict(supporter.attributes))
            )
        # Behavioral models receive a neutral voting_method in experiments; their draws
        # cannot depend on whichever comparison strategy happens to execute first.
        frozen_club = Club.model_construct(
            club_id=club.club_id,
            name=club.name,
            supporters=list(supporters.values()),
            memberships=list(memberships.values()),
            governance=club.governance,
        )
        neutral_proposal = proposal.model_copy(
            deep=True, update={"voting_method": None, "voting_strategy": None}
        )
        realized = (
            realization
            if realization is not None
            else self.realize(frozen_club, neutral_proposal, streams, selected_memberships=eligible)
        )
        digest = sha256((payload + realized.digest()).encode()).hexdigest()
        active = len({m.supporter_id for m in memberships.values() if m.active})
        return ElectionSnapshot(
            club.club_id,
            supporters,
            memberships,
            tuple(m.member_id for m in eligible),
            proposal_json,
            realized,
            active,
            digest,
            streams.seed,
            streams.trial,
        )

    def run(
        self,
        club: Club,
        proposal: GovernanceProposal,
        streams: RandomStreams,
        *,
        realization: Realization | None = None,
        snapshot: ElectionSnapshot | None = None,
        experiment_id: str = "simulation",
        scenario_id: str = "base",
        voting_model: str = "injected",
        configuration: dict[str, Any] | None = None,
    ) -> SimulationResult:
        started = perf_counter()
        inputs = (
            snapshot
            if snapshot is not None
            else self.prepare(club, proposal, streams, realization=realization)
        )
        if (
            inputs.club_id != club.club_id
            or inputs.seed != streams.seed
            or inputs.trial != streams.trial
        ):
            raise ValueError("Snapshot belongs to another club or trial")
        proposal = GovernanceProposal.model_validate_json(inputs.proposal_json)
        realized = inputs.realization
        eligible = [inputs.memberships[identity] for identity in inputs.eligible_member_ids]
        supporters = inputs.supporters
        context = VotingContext(
            proposal.proposal_id,
            streams.trial,
            streams.seed,
            proposal.category,
            getattr(proposal, "metadata", {}),
        )
        seen, weights, cast_weights, cast_options = set(), [], [], []
        abstentions = invalid = 0
        members_by_id = inputs.memberships
        eligible_identities, eligible_wealth, eligible_contributions, cast_identities = (
            [],
            [],
            [],
            [],
        )
        for member in eligible:
            identity = member.supporter_id
            # Defend identity uniqueness even for a custom eligibility implementation.
            if (
                identity in seen
                or identity not in supporters
                or members_by_id.get(member.member_id) != member
            ):
                raise ValueError("Eligibility policy returned duplicate or unknown membership")
            seen.add(identity)
            weight = self.voting.calculate_weight(supporters[identity], member, context)
            if not math.isfinite(weight) or weight < 0:
                raise ValueError("Voting weight must be finite and nonnegative")
            weights.append(weight)
            eligible_identities.append(identity)
            eligible_wealth.append(supporters[identity].wealth)
            eligible_contributions.append(member.contribution)
            if identity not in realized.participating or identity not in realized.preferences:
                raise ValueError("Realization is missing an eligible supporter")
            if not realized.participating[identity]:
                continue
            option = realized.preferences[identity]
            if option is None:
                abstentions += 1
            elif option not in proposal.options:
                invalid += 1
            else:
                cast_weights.append(weight)
                cast_options.append(option)
                cast_identities.append(identity)
        data = ElectionData(
            proposal.options,
            tuple(weights),
            tuple(cast_weights),
            tuple(cast_options),
            abstentions,
            invalid,
            tuple(eligible_identities),
            tuple(eligible_wealth),
            tuple(eligible_contributions),
            tuple(cast_identities),
            len(supporters),
            inputs.active_member_count,
            proposal.approval_threshold,
            proposal.quorum,
            proposal.quorum_basis,
        )
        metrics = self.metrics.calculate(data)
        # Core outcomes depend on ballots, never on an optional metric plugin's keys.
        totals = {
            o: math.fsum(
                w for option, w in zip(cast_options, cast_weights, strict=True) if option == o
            )
            for o in proposal.options
        }
        total = math.fsum(totals.values())
        if not math.isfinite(total):
            raise ValueError("Aggregate voting weight must be finite")
        count = len(cast_options)
        turnout = count / len(weights) if weights else None
        eligible_weight = math.fsum(weights)
        if not math.isfinite(eligible_weight):
            raise ValueError("Aggregate eligible voting weight must be finite")
        weighted_turnout = total / eligible_weight if eligible_weight > 0 else None
        quorum_participation = (
            weighted_turnout if proposal.quorum_basis == "eligible_weight" else turnout
        )
        quorum = quorum_participation is not None and quorum_participation >= proposal.quorum
        approval = total > 0 and totals[proposal.options[0]] / total >= proposal.approval_threshold
        winners = [o for o in proposal.options if totals[o] == max(totals.values())]
        winner = winners[0] if total > 0 and len(winners) == 1 else None
        return SimulationResult(
            experiment_id=experiment_id,
            scenario_id=scenario_id,
            trial_id=streams.trial,
            random_seed=streams.seed,
            component_seeds={
                name: streams.component_seed(name)
                for name in (
                    "participation",
                    "preferences",
                    "population.wealth",
                    "population.contribution",
                    "population.membership_age_days",
                    "population.loyalty",
                    "population.knowledge",
                    "population.participation_probability",
                    "population.adversarial",
                    "population.copula",
                )
            },
            configuration=configuration or {},
            governance_configuration=proposal.eligibility_rules.model_dump(mode="json")
            | {
                "quorum": proposal.quorum,
                "quorum_basis": proposal.quorum_basis,
                "approval_threshold": proposal.approval_threshold,
            },
            voting_model=voting_model,
            population_size=len(supporters),
            eligible_voter_count=len(weights),
            votes_cast=count,
            turnout=turnout,
            vote_totals=totals,
            winning_option=winner,
            approval_achieved=approval,
            quorum_achieved=quorum,
            passed=bool(approval and quorum),
            metrics=metrics,
            execution_metadata={
                "elapsed_seconds": perf_counter() - started,
                "realization_digest": realized.digest(),
                "input_digest": inputs.input_digest,
                "proposal_category": proposal.category,
                "proposal_id": proposal.proposal_id,
            },
        )
