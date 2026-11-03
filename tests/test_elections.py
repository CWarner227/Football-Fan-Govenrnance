import pytest

from fan_governance.agents.models import Supporter
from fan_governance.clubs.models import Club
from fan_governance.core.config import GovernanceConfig
from fan_governance.core.context import RandomStreams
from fan_governance.core.engine import SimulationEngine
from fan_governance.elections.models import GovernanceProposal
from fan_governance.elections.runner import ElectionRunner, Realization
from fan_governance.membership.eligibility import StandardEligibility
from fan_governance.membership.models import Membership
from fan_governance.metrics.results import StandardMetrics
from fan_governance.participation.probabilistic import ProbabilisticParticipation
from fan_governance.preferences.synthetic import SyntheticPreference
from fan_governance.voting.strategies import EqualVoting, ProportionalVoting


def fixture_club(contributions=(1, 3, 0, 2), age=365):
    supporters = [
        Supporter(supporter_id=str(i), wealth=contributions[i], participation_probability=1)
        for i in range(len(contributions))
    ]
    memberships = [
        Membership(member_id=str(i), supporter_id=str(i), contribution=c, age_days=age)
        for i, c in enumerate(contributions)
    ]
    return Club(
        club_id="c",
        name="Synthetic club",
        supporters=supporters,
        memberships=memberships,
        governance=GovernanceConfig(waiting_period_days=0),
    )


def runner(strategy=None, waiting=0, **kwargs):
    return ElectionRunner(
        voting=strategy or EqualVoting(),
        eligibility=StandardEligibility(waiting),
        participation=ProbabilisticParticipation(),
        preference=SyntheticPreference(),
        metrics=StandardMetrics(),
        **kwargs,
    )


def test_weighted_aggregation_quorum_and_approval():
    club = fixture_club()
    proposal = GovernanceProposal(quorum=0.75, approval_threshold=0.7)
    realization = Realization(
        participating={"0": True, "1": True, "2": True, "3": False},
        preferences={"0": "reject", "1": "approve", "2": "reject", "3": "approve"},
    )
    result = runner(ProportionalVoting()).run(
        club, proposal, RandomStreams(42), realization=realization
    )
    assert result.vote_totals == {"approve": 3, "reject": 1}
    assert result.votes_cast == 3
    assert result.turnout == 0.75
    assert result.metrics["weighted_shares"]["approve"] == 0.75
    assert result.metrics["unweighted_shares"]["approve"] == pytest.approx(1 / 3)
    assert result.metrics["effective_voters"] == pytest.approx(36 / 14)
    assert result.quorum_achieved and result.approval_achieved and result.passed
    assert result.winning_option == "approve"
    assert (
        not runner()
        .run(
            club,
            proposal.model_copy(update={"quorum": 1.0}),
            RandomStreams(42),
            realization=realization,
        )
        .passed
    )


def test_ineligible_members_cannot_vote():
    result = runner(waiting=366).run(fixture_club(), GovernanceProposal(quorum=0), RandomStreams(1))
    assert result.eligible_voter_count == result.votes_cast == 0
    assert result.turnout is None
    assert not result.passed


@pytest.mark.parametrize("club", [fixture_club(()), fixture_club((0, 0))])
def test_empty_and_zero_power_never_pass(club):
    result = runner(ProportionalVoting()).run(
        club, GovernanceProposal(quorum=0, approval_threshold=0), RandomStreams(1)
    )
    assert result.metrics["gini"] is None
    assert result.winning_option is None
    assert not result.approval_achieved and not result.passed


def test_abstentions_invalid_and_ties():
    club = fixture_club()
    realization = Realization(
        participating=dict.fromkeys(["0", "1", "2", "3"], True),
        preferences={"0": "approve", "1": "reject", "2": None, "3": "typo"},
    )
    result = runner().run(
        club, GovernanceProposal(quorum=0.5), RandomStreams(1), realization=realization
    )
    assert result.votes_cast == 2
    assert result.metrics["abstentions"] == 1
    assert result.metrics["invalid_ballots"] == 1
    assert result.turnout == 0.5
    assert result.winning_option is None
    assert result.passed  # documented inclusive 50% threshold, even on a tie


def test_custom_strategy_injection_and_invalid_weight_rejection():
    class ConstantVoting:
        def calculate_weight(self, supporter, membership, context):
            return 7

    result = runner(ConstantVoting()).run(fixture_club(), GovernanceProposal(), RandomStreams(9))
    assert result.metrics["total_weight_cast"] == 28
    for weight in [-1, float("nan"), float("inf")]:

        class BrokenVoting:
            def calculate_weight(self, supporter, membership, context, weight=weight):
                return weight

        with pytest.raises(ValueError, match="weight"):
            runner(BrokenVoting()).run(fixture_club(), GovernanceProposal(), RandomStreams(9))


def test_independent_participation_and_preferences():
    s = Supporter(supporter_id="s", participation_probability=0)
    m = Membership(member_id="m", supporter_id="s")
    assert not ProbabilisticParticipation().participates(
        s, m, None, RandomStreams(1).generator("x")
    )
    assert ProbabilisticParticipation(probability=1).participates(
        s, m, None, RandomStreams(1).generator("x")
    )
    assert (
        SyntheticPreference(approval_probability=1).choose(
            s, m, GovernanceProposal(), None, RandomStreams(1).generator("x")
        )
        == "approve"
    )
    assert (
        SyntheticPreference(abstention_probability=1).choose(
            s, m, GovernanceProposal(), None, RandomStreams(1).generator("x")
        )
        is None
    )


def test_duplicate_canonical_ids_and_orphan_memberships_rejected():
    club = fixture_club()
    with pytest.raises(ValueError, match="supporter"):
        Club(club_id="bad", name="bad", supporters=[club.supporters[0]] * 2, memberships=[])
    with pytest.raises(ValueError, match="supporter"):
        Club(club_id="bad", name="bad", supporters=[], memberships=club.memberships)


def test_engine_uses_injected_generator_and_runner():
    from fan_governance.agents.generator import SyntheticPopulationGenerator
    from fan_governance.core.config import SimulationConfig

    result = SimulationEngine(SyntheticPopulationGenerator(), runner()).run(
        SimulationConfig(population={"size": 10}, governance={"waiting_period_days": 0})
    )
    assert result.population_size == 10
