import pytest
from test_elections import fixture_club, runner

from fan_governance.core.context import RandomStreams
from fan_governance.elections.models import GovernanceProposal
from fan_governance.voting.strategies import ProportionalVoting


def test_snapshot_preserves_baseline_and_frozen_behavior():
    club = fixture_club()
    proposal = GovernanceProposal()
    election = runner()
    snapshot = election.prepare(club, proposal, RandomStreams(7))
    before = election.run(club, proposal, RandomStreams(7), snapshot=snapshot)
    club.memberships[0].contribution = 999
    after = runner(ProportionalVoting()).run(club, proposal, RandomStreams(7), snapshot=snapshot)
    assert before.execution_metadata["input_digest"] == after.execution_metadata["input_digest"]
    assert before.votes_cast == after.votes_cast
    assert after.metrics["total_weight_cast"] == 6
    with pytest.raises((TypeError, ValueError)):
        snapshot.realization.participating["0"] = False
    with pytest.raises(ValueError):
        snapshot.supporters["0"].wealth = 100


def test_eligibility_is_evaluated_once_for_matched_strategies():
    class CountingEligibility:
        def __init__(self):
            self.calls = 0

        def eligible(self, supporters, memberships):
            self.calls += 1
            return memberships

    policy = CountingEligibility()
    election = runner()
    election.eligibility = policy
    club, proposal = fixture_club(), GovernanceProposal()
    snapshot = election.prepare(club, proposal, RandomStreams(7))
    election.run(club, proposal, RandomStreams(7), snapshot=snapshot)
    election.voting = ProportionalVoting()
    election.run(club, proposal, RandomStreams(7), snapshot=snapshot)
    assert policy.calls == 1
