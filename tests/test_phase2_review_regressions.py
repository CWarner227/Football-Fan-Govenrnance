import pytest
from test_elections import runner

from fan_governance.agents.models import Supporter
from fan_governance.clubs.models import Club
from fan_governance.core.context import RandomStreams
from fan_governance.elections.models import GovernanceProposal
from fan_governance.membership.models import Membership


def test_authoritative_membership_also_requires_affordability():
    supporter = Supporter(supporter_id="s", wealth=10)
    membership = Membership(member_id="m", supporter_id="s", contribution=11)
    with pytest.raises(ValueError, match="wealth"):
        Club(club_id="c", name="c", supporters=[supporter], memberships=[membership])
    alternative = supporter.model_copy(update={"allow_unfunded_contributions": True})
    assert Club(club_id="c", name="c", supporters=[alternative], memberships=[membership])


def test_inactive_duplicate_does_not_change_behavioral_membership():
    class ActiveTurnout:
        def participates(self, supporter, membership, context, rng):
            return membership.active

    club = Club(
        club_id="c",
        name="c",
        supporters=[Supporter(supporter_id="s")],
        memberships=[Membership(member_id="z", supporter_id="s")],
    )
    election = runner()
    election.participation = ActiveTurnout()
    first = election.run(club, GovernanceProposal(), RandomStreams(1))
    club.memberships.append(Membership(member_id="a", supporter_id="s", active=False))
    second = election.run(club, GovernanceProposal(), RandomStreams(1))
    assert first.votes_cast == second.votes_cast == 1


def test_mutated_membership_cannot_bypass_validation_before_snapshot():
    club = Club(
        club_id="c",
        name="c",
        supporters=[Supporter(supporter_id="s", wealth=10)],
        memberships=[Membership(member_id="m", supporter_id="s", contribution=5)],
    )
    club.memberships[0].contribution = 11
    with pytest.raises(ValueError, match="wealth"):
        runner().prepare(club, GovernanceProposal(), RandomStreams(1))
