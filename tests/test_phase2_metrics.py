import pytest

from fan_governance.metrics.representation import representation_metrics


def test_wealth_representation_uses_eligible_and_valid_cast_power_separately():
    # Four unique wealth ranks: poorest two have 3/10 of eligible power,
    # only richest and poorest vote, each casting their full potential power.
    result = representation_metrics(
        identities=("a", "b", "c", "d"),
        wealth=(1, 2, 3, 4),
        contributions=(1, 1, 2, 6),
        eligible_weights=(1, 2, 3, 4),
        cast_identities=("a", "d"),
        cast_weights=(1, 4),
    )
    assert result["potential"]["bottom_50_wealth_power_share"] == pytest.approx(0.3)
    assert result["realized"]["bottom_50_wealth_power_share"] == pytest.approx(0.2)
    assert result["potential"]["top_10_wealth_power_share"] == pytest.approx(0.4)
    assert result["potential"]["top_1_wealth_power_share"] == pytest.approx(0.4)
    assert result["potential"]["bottom_50_contribution_share"] == pytest.approx(0.2)
    assert result["potential"]["bottom_50_contribution_to_power_ratio"] == pytest.approx(2 / 3)
    assert sum(result["potential"]["wealth_decile_power_shares"].values()) == pytest.approx(1)


def test_undefined_representation_and_fixed_wealth_groups():
    empty = representation_metrics((), (), (), (), (), ())
    assert empty["potential"]["bottom_50_wealth_power_share"] is None
    zero = representation_metrics(("a", "b"), (1, 2), (0, 0), (0, 0), ("a",), (0,))
    assert zero["potential"]["bottom_50_contribution_to_power_ratio"] is None
    assert zero["realized"]["top_1_wealth_power_share"] is None


def test_wealth_ties_have_deterministic_identity_tiebreak():
    a = representation_metrics(("b", "a"), (1, 1), (1, 1), (4, 1), (), ())
    b = representation_metrics(("a", "b"), (1, 1), (1, 1), (1, 4), (), ())
    assert a == b
    assert a["potential"]["bottom_50_wealth_power_share"] == pytest.approx(0.2)
