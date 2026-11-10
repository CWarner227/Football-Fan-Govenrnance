"""Guard research sample identity and uncertainty at important edge cases."""

import json
from copy import deepcopy

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("httpx")

import examples.report_study_campaign as analysis
from examples.report_study_campaign import aggregate, condition_identity, paired_contrasts, wilson
from examples.run_study_campaign import fingerprint


def test_configuration_reuse_ignores_destination_and_numeric_json_spelling():
    a = {"experiment": {"seed": 1}, "parameter": 1, "output": {"directory": "a"}}
    b = {"experiment": {"seed": 1}, "parameter": 1.0, "output": {"directory": "b"}}
    assert fingerprint(a) == fingerprint(b)
    b["experiment"]["seed"] = 2
    assert fingerprint(a) != fingerprint(b)
    assert "output" in a


def test_wilson_zero_is_not_proof_of_zero_risk():
    lo, hi = wilson(0, 100)
    assert lo == pytest.approx(0, abs=1e-15)
    assert hi == pytest.approx(0.0369935, abs=1e-6)
    lo, hi = wilson(100, 100)
    assert lo == pytest.approx(0.9630065, abs=1e-6)
    assert hi == pytest.approx(1)


def test_condition_identity_normalizes_numeric_spelling_but_not_scientific_changes():
    assert condition_identity({"wealth": {"sigma": 1}, "quorum": 0}) == condition_identity(
        {"quorum": 0.0, "wealth": {"sigma": 1.0}}
    )
    assert condition_identity({"sigma": 1}) != condition_identity({"sigma": 2})
    assert condition_identity({"rights": True}) != condition_identity({"rights": 1})


def row(seed=11001):
    return dict(
        group="02-wealthy",
        grid_id="cell",
        voting_model="equal",
        variant="control",
        seed=seed,
        trial=0,
        **{"attacks.0.parameters.contribution_budget": 5000},
        representation={"potential": {"bottom_50_wealth_power_share": 0.5}},
        capture_success=False,
    )


def test_cross_seed_trial_zero_is_distinct_but_duplicate_seed_is_rejected():
    a, b = row(), row(11002)
    assert aggregate([a, b], 2)[0]["n"] == 2
    with pytest.raises(ValueError, match="Missing/duplicate"):
        aggregate([a, deepcopy(a)], 2)


def test_one_hundred_rows_from_the_wrong_seed_design_are_rejected():
    values = []
    for trial in range(100):
        value = row()
        value["trial"] = trial
        values.append(value)
    with pytest.raises(ValueError, match="frozen four-batch"):
        aggregate(values, 100)


def test_paired_contrast_counts_discordance_and_keeps_conditions_separate():
    rows = []
    for seed in (11001, 11002):
        for variant in ("control", "unprotected", "defended"):
            r = row(seed)
            r.update(variant=variant, capture_success=variant == "unprotected")
            rows.append(r)
    result = paired_contrasts(rows)[0]
    assert result["n"] == 2
    assert result["defended_minus_unprotected"] == -1
    assert result["defended_lower"] == 2
    with pytest.raises(ValueError, match="Incomplete paired"):
        paired_contrasts(rows[:-1])


def test_streaming_audit_detects_cross_period_discontinuity(tmp_path, monkeypatch):
    monkeypatch.setattr(analysis, "DATA", tmp_path)
    folder = tmp_path / "example/batch01"
    folder.mkdir(parents=True)
    (tmp_path / "ledger.json").write_text(
        json.dumps({"example/batch01": {"run_id": "run", "stage": "batch01"}})
    )
    counts = {table: 0 for table in ("summary", "elections", "aggregate", "defense_effectiveness")}
    for table in counts:
        (folder / (table + ".jsonl")).write_text("")
    base = dict(
        grid_id="cell",
        trial=0,
        voting_model="equal",
        variant="control",
        month=0,
        opening_cash=100,
        operating_surplus=0,
        financing_cashflow=0,
        investing_cashflow=0,
        cash_balance=100,
    )
    second = dict(base, month=1, operating_surplus=-10, cash_balance=90)
    target = folder / "timeseries.jsonl"
    target.write_text(json.dumps(base) + "\n" + json.dumps(second) + "\n")
    counts["timeseries"] = 2
    manifests = {
        "run": {
            "manifest": {"row_counts": counts, "metadata": {"source": {"source_sha256": "source"}}}
        }
    }
    result = analysis.audit_exports(manifests)
    assert result["cash_transitions_checked"] == 1
    assert result["economic_period_rows_reconciled"] == 2
    # Each row still balances, but the second period silently lost five units.
    second.update(opening_cash=95, cash_balance=85)
    target.write_text(json.dumps(base) + "\n" + json.dumps(second) + "\n")
    with pytest.raises(ValueError, match="continuity"):
        analysis.audit_exports(manifests)
