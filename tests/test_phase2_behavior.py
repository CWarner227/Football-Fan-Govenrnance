import math

import numpy as np
import pytest

from fan_governance.agents.models import Supporter
from fan_governance.core.context import VotingContext
from fan_governance.elections.models import GovernanceProposal
from fan_governance.membership.models import Membership
from fan_governance.participation.attribute_based import AttributeBasedParticipation
from fan_governance.preferences.attribute_based import AttributeBasedPreference
from fan_governance.preferences.policy import PolicyPreference


def inputs(**supporter_values):
    return (
        Supporter(supporter_id="fan", **supporter_values),
        Membership(member_id="m", supporter_id="fan"),
        GovernanceProposal(proposal_id="p", options=("support", "oppose")),
        VotingContext(proposal_id="p", trial_id=0, seed=42),
    )


def test_attribute_turnout_uses_scaled_logistic_and_one_random_draw():
    supporter, member, _, context = inputs(wealth=400, loyalty=0.8)
    model = AttributeBasedParticipation(
        intercept=-1, coefficients={"wealth": 0.5, "loyalty": 2}, scales={"wealth": 200}
    )
    actual_rng = np.random.default_rng(42)
    expected_rng = np.random.default_rng(42)
    probability = 1 / (1 + math.exp(-1.6))
    assert model.participates(supporter, member, context, actual_rng) == (
        expected_rng.random() < probability
    )
    assert actual_rng.random() == expected_rng.random()


@pytest.mark.parametrize("intercept, expected", [(1000, True), (-1000, False)])
def test_extreme_logits_remain_bounded(intercept, expected):
    supporter, member, _, context = inputs()
    model = AttributeBasedParticipation(intercept=intercept, coefficients={})
    assert model.participates(supporter, member, context, np.random.default_rng(2)) is expected


@pytest.mark.parametrize("model_type", [AttributeBasedParticipation, AttributeBasedPreference])
@pytest.mark.parametrize(
    "parameters",
    [
        {"intercept": float("nan")},
        {"coefficients": {"loyalty": float("inf")}},
        {"coefficients": {"supporter_id": 1}},
        {"coefficients": {"attributes": 1}},
        {"coefficients": {"loyalty": 1}, "scales": {"loyalty": 0}},
        {"coefficients": {"loyalty": 1}, "scales": {"loyalty": -1}},
        {"scales": {"wealth": float("inf")}},
    ],
)
def test_attribute_models_reject_invalid_parameters(model_type, parameters):
    with pytest.raises(ValueError):
        model_type(**parameters)


def test_attribute_preference_is_seeded_and_draws_twice_even_on_abstention():
    supporter, member, proposal, context = inputs(loyalty=0.8)
    model = AttributeBasedPreference(coefficients={"loyalty": 2}, abstention_probability=1)
    actual_rng = np.random.default_rng(42)
    expected_rng = np.random.default_rng(42)
    assert model.choose(supporter, member, proposal, context, actual_rng) is None
    expected_rng.random(2)
    assert actual_rng.random() == expected_rng.random()
    model = AttributeBasedPreference(coefficients={"loyalty": 2})
    rng_a, rng_b = np.random.default_rng(42), np.random.default_rng(42)
    assert [model.choose(supporter, member, proposal, context, rng_a) for _ in range(20)] == [
        model.choose(supporter, member, proposal, context, rng_b) for _ in range(20)
    ]


def test_attribute_preference_uses_proposal_options_and_forecast_missing_default():
    supporter, member, proposal, context = inputs()
    model = AttributeBasedPreference(intercept=-100, coefficients={"forecast_accuracy": 400})
    assert (
        model.choose(supporter, member, proposal, context, np.random.default_rng(42)) == "support"
    )


def test_attribute_aliases_and_known_logistic_probability():
    supporter, _, _, _ = inputs(knowledge=0.75, participation_probability=0.25)
    model = AttributeBasedPreference(coefficients={"knowledge_score": 2, "participation_rate": -2})
    assert model.probability_for(supporter) == pytest.approx(0.7310585786300049)


@pytest.mark.parametrize("probability", [-0.1, 1.1, float("inf")])
def test_attribute_preference_rejects_invalid_abstention(probability):
    with pytest.raises(ValueError):
        AttributeBasedPreference(abstention_probability=probability)


@pytest.mark.parametrize(
    "alignment, preferred, expected",
    [
        ("community", "community", "support"),
        ("community", "investment", "oppose"),
        ("community", "neutral", "support"),
        (None, "community", "support"),
        ({"community": 1, "investment": 0}, "community", "support"),
        ({"community": 1, "investment": 0}, "investment", "oppose"),
        ({"community": 1}, "other", "support"),
    ],
)
def test_policy_alignment_schema(alignment, preferred, expected):
    supporter, member, proposal, context = inputs(preferred_policy=preferred)
    proposal = proposal.model_copy(update={"metadata": {"policy_alignment": alignment}})
    model = PolicyPreference(alignment_probability=1, mismatch_probability=0, neutral_probability=1)
    assert model.choose(supporter, member, proposal, context, np.random.default_rng(42)) == expected


@pytest.mark.parametrize(
    "alignment", [42, [], {"community": 1.1}, {"other": float("nan")}, {1: 0.5}]
)
def test_policy_alignment_validates_all_entries_at_use(alignment):
    supporter, member, proposal, context = inputs()
    proposal = proposal.model_copy(update={"metadata": {"policy_alignment": alignment}})
    with pytest.raises(ValueError):
        PolicyPreference().choose(supporter, member, proposal, context, np.random.default_rng(42))


@pytest.mark.parametrize(
    "parameter",
    [
        "alignment_probability",
        "mismatch_probability",
        "neutral_probability",
        "abstention_probability",
    ],
)
def test_policy_probability_validation(parameter):
    with pytest.raises(ValueError):
        PolicyPreference(**{parameter: float("nan")})


def test_policy_preference_preserves_two_draw_stream_on_abstention():
    supporter, member, proposal, context = inputs()
    actual_rng, expected_rng = np.random.default_rng(42), np.random.default_rng(42)
    assert (
        PolicyPreference(abstention_probability=1).choose(
            supporter, member, proposal, context, actual_rng
        )
        is None
    )
    expected_rng.random(2)
    assert actual_rng.random() == expected_rng.random()


def test_registered_constant_model_uses_a_common_default():
    from fan_governance.core.config import ModelSpec
    from fan_governance.core.registry import default_registry

    model = default_registry().create("participation", ModelSpec(name="constant"))
    assert model.probability == 0.6
