"""Research API discovery, validation and confined persistence contracts."""

from dataclasses import dataclass
from uuid import uuid4

import pytest

from fan_governance.api.catalog import capabilities, catalog
from fan_governance.api.schemas import ComparisonRequest
from fan_governance.api.validation import validate_configuration
from fan_governance.core.registry import default_registry
from fan_governance.storage.filesystem import FileRepository


def test_catalog_counts_and_dynamic_factory_metadata():
    models = catalog()["models"]
    for category, count in {"voting": 6, "attack": 7, "defense": 6, "shock": 4}.items():
        assert len([m for m in models if m["category"] == category]) == count
    hybrid = next(m for m in models if m["id"] == "hybrid")
    assert "proposal_rules" in hybrid["schema"]["properties"]
    registry = default_registry()

    @dataclass
    class AdditionalVoting:
        multiplier: float = 2.0

    registry.register("voting", "additional", AdditionalVoting)
    added = next(m for m in catalog(registry=registry)["models"] if m["id"] == "additional")
    assert added["defaults"] == {"multiplier": 2.0}
    assert added["schema"]["additionalProperties"] is False


def test_default_config_and_grid_validation():
    raw = capabilities()["defaults"]
    config, workload = validate_configuration(raw)
    assert config.simulation.population.size == 100
    assert config.experiment.trials == 1
    assert workload["grid_cells"] == 1
    raw["experiment"]["grid"] = {"simulation.population.size": [10, 20]}
    assert validate_configuration(raw)[1]["grid_cells"] == 2
    raw["experiment"]["grid"] = {"missing.path": [1]}
    with pytest.raises(ValueError, match="grid"):
        validate_configuration(raw)


@pytest.mark.parametrize(
    "edit",
    [
        lambda c: c["simulation"]["population"].update(size=100001),
        lambda c: c["experiment"].update(trials=1001),
        lambda c: c["experiment"].update(grid={"simulation.population.size": list(range(257))}),
        lambda c: c["experiment"].update(grid={"simulation.voting.strategies.0": ["missing"]}),
        lambda c: c["simulation"]["voting"].update(
            strategies=[{"name": "capped", "parameters": {"typo": 1}}]
        ),
        lambda c: c["simulation"]["voting"].update(
            strategies=[
                {
                    "name": "hybrid",
                    "parameters": {
                        "proposal_rules": {"funding": {"name": "capped", "parameters": {"typo": 1}}}
                    },
                }
            ]
        ),
        lambda c: (
            c["simulation"]["population"].update(size=100000) or c["experiment"].update(trials=1000)
        ),
    ],
)
def test_invalid_or_excessive_configurations_rejected(edit):
    raw = capabilities()["defaults"]
    edit(raw)
    with pytest.raises(ValueError):
        validate_configuration(raw)


def test_growth_and_scheduled_attack_workload_is_bounded():
    raw = capabilities()["defaults"]
    raw["economics"]["membership_growth_rate"] = 1
    raw["timeline"]["duration_months"] = 120
    with pytest.raises(ValueError, match="[Ww]orkload"):
        validate_configuration(raw)


def test_invalid_untyped_hybrid_parameters_have_validation_error():
    raw = capabilities()["defaults"]
    raw["simulation"]["voting"]["strategies"] = [
        {"name": "hybrid", "parameters": {"proposal_rules": []}}
    ]
    with pytest.raises(ValueError):
        validate_configuration(raw)


def test_incompatible_quorum_policies_rejected_before_execution():
    raw = capabilities()["defaults"]
    raw["defenses"] = [
        {"name": "quorum", "parameters": {"basis": "eligible_members"}},
        {"name": "quorum", "parameters": {"basis": "eligible_weight"}},
    ]
    with pytest.raises(ValueError, match="basis"):
        validate_configuration(raw)


def test_reference_trajectories_are_included_in_workload():
    raw = capabilities()["defaults"]
    raw["attacks"] = [{"name": "sybil", "operational_budget": 1}]
    raw["defenses"] = [{"name": "identity_verification"}]
    raw["economics"]["shocks"] = [{"name": "revenue_loss"}]
    workload = validate_configuration(raw)[1]
    assert workload["total_trials"] == 1
    assert workload["trajectory_runs"] == 5


def test_nested_hybrid_strict_parameter_validation():
    raw = capabilities()["defaults"]
    raw["simulation"]["voting"]["strategies"] = [
        {
            "name": "hybrid",
            "parameters": {"default_strategy": {"name": "capped", "parameters": {"cap": True}}},
        }
    ]
    with pytest.raises(ValueError):
        validate_configuration(raw)


def test_uninstalled_distribution_is_rejected_before_run():
    raw = capabilities()["defaults"]
    raw["simulation"]["population"]["wealth_distribution"]["type"] = "uninstalled"
    with pytest.raises(ValueError, match="distribution"):
        validate_configuration(raw)


def test_comparison_request_matches_bounded_service_contract():
    with pytest.raises(ValueError):
        ComparisonRequest(run_ids=[uuid4().hex for _ in range(5)])


def test_file_repository_persistence_delete_and_atomic_failure(tmp_path, monkeypatch):
    repo = FileRepository(tmp_path)
    identifier = uuid4().hex
    repo.save("runs", identifier, {"status": "queued"})
    assert FileRepository(tmp_path).get("runs", identifier) == {"status": "queued"}
    assert repo.list("runs") == [{"status": "queued"}]

    def fail(*args):
        raise OSError("interrupted replace")

    monkeypatch.setattr("fan_governance.storage.filesystem.os.replace", fail)
    with pytest.raises(OSError):
        repo.save("runs", identifier, {"status": "running"})
    assert repo.get("runs", identifier)["status"] == "queued"
    repo.delete("runs", identifier)
    with pytest.raises(KeyError):
        repo.get("runs", identifier)


@pytest.mark.parametrize("identifier", ["../outside", "a/b", "C:\\test", "a" * 31, "A" * 32])
def test_repository_rejects_nonopaque_identifiers(tmp_path, identifier):
    with pytest.raises(ValueError):
        FileRepository(tmp_path).directory("runs", identifier)


def test_repository_rejects_symlinks(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "store"
    root.mkdir()
    try:
        (root / "runs").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating Windows symlinks requires developer mode")
    with pytest.raises(ValueError, match="[Ss]ymlink"):
        FileRepository(root).directory("runs", uuid4().hex)
