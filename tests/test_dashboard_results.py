"""Bounded artifact access and matched comparison contracts."""

import json
from uuid import uuid4

import pytest

from fan_governance.api.results import ResultsService
from fan_governance.storage.filesystem import FileRepository


def saved(repository, rows, **configuration):
    identifier = uuid4().hex
    record = {
        "id": identifier,
        "name": "test",
        "status": "completed",
        "configuration": {
            "simulation": {"population": {"size": 10}, "voting": {"strategies": ["equal"]}},
            "experiment": {"seed": 42, "trials": 1},
            **configuration,
        },
    }
    repository.save("runs", identifier, record)
    directory = repository.directory("runs", identifier) / "artifacts"
    directory.mkdir()
    for table in (
        "summary",
        "elections",
        "timeseries",
        "events",
        "aggregate",
        "defense_effectiveness",
    ):
        (directory / f"{table}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    (directory / "manifest.json").write_text(json.dumps({"row_counts": {"summary": len(rows)}}))
    return identifier


def test_streamed_pagination_search_sort_and_filters(tmp_path):
    repository = FileRepository(tmp_path)
    identifier = saved(
        repository,
        [
            {
                "trial": i,
                "variant": "defended" if i % 2 else "control",
                "score": i,
                "nested": {"value": i},
            }
            for i in range(40)
        ],
    )
    service = ResultsService(repository)
    page = service.page(
        identifier,
        "summary",
        offset=3,
        limit=4,
        sort="score",
        descending=True,
        filters={"variant": "defended"},
    )
    assert page["total"] == 20
    assert [row["score"] for row in page["items"]] == [33, 31, 29, 27]
    assert "nested.value" in page["columns"]
    assert service.page(identifier, "events", search="defended", limit=2)["total"] == 20
    with pytest.raises(ValueError):
        service.page(identifier, "../record")


def test_results_reject_unfinished_runs_and_export_only_safe_files(tmp_path):
    repository = FileRepository(tmp_path)
    identifier = saved(repository, [{"score": 1}])
    service = ResultsService(repository)
    assert json.loads("".join(service.export_rows(identifier, "summary", "json"))) == [{"score": 1}]
    assert "score" in "".join(service.export_rows(identifier, "summary", "csv"))
    record = repository.get("runs", identifier)
    record["status"] = "running"
    repository.save("runs", identifier, record)
    with pytest.raises(ValueError, match="completed"):
        service.page(identifier, "summary")


def test_comparison_pairs_identical_trials_and_warns_for_seed_change(tmp_path):
    repository = FileRepository(tmp_path)
    row = {
        "trial": 0,
        "grid_id": "base",
        "voting_model": "equal",
        "variant": "defended",
        "turnout": 0.5,
    }
    left = saved(repository, [row])
    right = saved(repository, [row | {"turnout": 0.75}])
    service = ResultsService(repository)
    comparison = service.compare([left, right])
    difference = next(r for r in comparison["paired_differences"] if r["metric"] == "turnout")
    assert difference["difference"] == 0.25
    changed = saved(repository, [row], experiment={"seed": 43, "trials": 1})
    comparison = service.compare([left, changed])
    assert comparison["warnings"]
    assert not comparison["paired_differences"]


def test_comparison_response_is_bounded_and_reports_truncation(tmp_path):
    repository = FileRepository(tmp_path)
    rows = [
        {
            "trial": i,
            "grid_id": "base",
            "voting_model": "equal",
            "variant": "control",
            "turnout": 0.5,
            "gini": 0,
            "attacker_power_share": 0,
            "attacker_vote_share": 0,
            "capture_success": False,
            "passed": True,
            "cash_balance": 10,
            "administrative_cost": 1,
            "financial_runway_months": 2,
        }
        for i in range(600)
    ]
    identifiers = [saved(repository, rows) for _ in range(4)]
    result = ResultsService(repository).compare(identifiers)
    assert len(result["paired_differences"]) <= 5000
    assert all(len(item["summary"]["items"]) <= 500 for item in result["runs"])
    assert any("truncat" in message.lower() for message in result["warnings"])


def test_facets_discover_cells_beyond_a_chart_page(tmp_path):
    repository = FileRepository(tmp_path)
    identifier = saved(
        repository,
        [
            {
                "trial": i,
                "grid_id": "later" if i == 2100 else "first",
                "voting_model": "equal",
                "variant": "control",
            }
            for i in range(2101)
        ],
    )
    facets = ResultsService(repository).facets(identifier, "summary")
    assert facets["facets"]["grid_id"] == ["first", "later"]
    assert not facets["truncated"]
