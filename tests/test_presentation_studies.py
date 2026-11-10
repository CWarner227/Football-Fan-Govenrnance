"""Research configuration contracts and frontend import, using authoritative validation."""

import runpy
from functools import cache

import pytest

from fan_governance.api.validation import validate_configuration
from fan_governance.scenarios.runner import expanded_configs, run_scenario


@cache
def helpers():
    return runpy.run_path("examples/presentation_studies.py")


@cache
def bundle():
    return helpers()["build_bundle"]()


def test_all_study_batches_fit_dashboard_and_have_distinct_sampling_blocks():
    records = bundle()
    assert len(records) == 95
    groups = {}
    for record in records:
        config, workload = validate_configuration(record["configuration"])
        assert workload["work_units"] <= 300_000_000
        assert len(config.simulation.voting.specs()) == 6
        assert config.simulation.population.seed is None
        groups.setdefault(record["group"], []).append(config)
    assert len(groups) == 19
    for group in groups.values():
        pilots = [c for c in group if c.experiment.trials == 10]
        batches = [c for c in group if c.experiment.trials == 25]
        assert len(pilots) == 1 and len(batches) == 4
        assert sum(c.experiment.trials for c in batches) == 100
        assert len({c.experiment.seed for c in group}) == 5


def test_design_covers_profiles_timing_alias_pressure_and_defense_packages():
    records = bundle()
    pilots = [r for r in records if r["stage"] == "pilot"]
    baseline = next(r for r in pilots if r["group"] == "01-baseline")
    cells = [
        c for _, c, _ in expanded_configs(validate_configuration(baseline["configuration"])[0])
    ]
    assert len(cells) == 6
    assert {c.simulation.proposal.category for c in cells} == {"funding", "constitutional"}
    assert all(c.honest_turnout is None and not c.economics.enabled for c in cells)
    assert {
        c.simulation.population.participation_probability_distribution.parameters.get("value")
        for c in cells
    } >= {0.15}
    infiltration = next(r for r in pilots if r["group"].startswith("04-"))
    config = validate_configuration(infiltration["configuration"])[0]
    assert config.elections.interval_months == 3
    assert config.experiment.grid["defenses.1.parameters.days"] == [0, 90, 180]
    sybil = next(r for r in pilots if r["group"].startswith("03-"))
    actors = sybil["configuration"]["experiment"]["grid"]["attacks"]
    assert {a[0]["parameters"]["attempted_identities"] for a in actors} == {50, 200, 400}
    assert all(
        a[0]["operational_budget"] == a[0]["parameters"]["attempted_identities"] for a in actors
    )
    defense = [r for r in pilots if r["group"].startswith("06-")]
    assert sum(len(r["configuration"]["experiment"]["grid"]["defenses"]) for r in defense) == 10


def test_import_is_idempotent_and_rejects_name_collisions(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from fan_governance.api.main import create_app

    module = helpers()
    records = bundle()[:2]
    with TestClient(create_app(tmp_path)) as client:
        assert module["import_bundle"](records, client) == {"created": 2, "existing": 0}
        stored = client.get("/api/v1/configurations").json()["items"][0]
        directory = stored["configuration"]["output"]["directory"]
        stored["configuration"]["output"]["directory"] = (
            directory.replace("/", "\\") if "/" in directory else directory.replace("\\", "/")
        )
        client.app.state.repository.save("configurations", stored["id"], stored)
        assert module["import_bundle"](records, client) == {"created": 0, "existing": 2}
        changed = [dict(records[0], description="a changed design")]
        with pytest.raises(ValueError, match="already exists"):
            module["import_bundle"](changed, client)
        assert client.get("/api/v1/configurations").json()["total"] == 2


def test_container_import_mode_does_not_write_source_files(tmp_path, monkeypatch):
    import sys

    module = helpers()
    monkeypatch.setitem(module["main"].__globals__, "DESTINATION", tmp_path / "read-only-source")
    monkeypatch.setattr(sys, "argv", ["presentation_studies.py", "--no-write"])
    module["main"]()
    assert not (tmp_path / "read-only-source").exists()


@pytest.mark.parametrize("group_index", range(19))
def test_one_real_trial_of_first_cell_of_every_group(group_index):
    records = [r for r in bundle() if r["stage"] == "pilot"]
    config = validate_configuration(records[group_index]["configuration"])[0]
    _, candidate, _ = next(expanded_configs(config))
    candidate.experiment.grid = {}
    candidate.experiment.trials = 1
    result = run_scenario(candidate)
    assert len(result.summary) == 18
    assert {row["voting_model"] for row in result.summary} == {
        "equal",
        "proportional",
        "capped",
        "diminishing",
        "hybrid",
        "expertise",
    }
