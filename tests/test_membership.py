import pytest
from test_elections import fixture_club, runner

from fan_governance.agents.models import Supporter
from fan_governance.core.context import RandomStreams
from fan_governance.elections.models import GovernanceProposal
from fan_governance.membership.eligibility import StandardEligibility
from fan_governance.membership.models import Membership


@pytest.mark.parametrize("waiting", [0, 90, 180, 365, 712])
def test_waiting_period_boundaries(waiting):
    population = [Supporter(supporter_id="s")]
    member = Membership(member_id="m", supporter_id="s", age_days=waiting)
    assert StandardEligibility(waiting).eligible(population, [member]) == [member]
    if waiting:
        younger = member.model_copy(update={"age_days": waiting - 1})
        assert StandardEligibility(waiting).eligible(population, [younger]) == []


def test_duplicate_membership_does_not_increase_power_or_ballot_count():
    club = fixture_club((10,))
    club.supporters[0].wealth = 10000
    club.memberships.append(Membership(member_id="duplicate", supporter_id="0", contribution=10000))
    result = runner().run(club, GovernanceProposal(), RandomStreams(1))
    assert result.eligible_voter_count == result.votes_cast == 1
    assert sum(result.vote_totals.values()) == 1
