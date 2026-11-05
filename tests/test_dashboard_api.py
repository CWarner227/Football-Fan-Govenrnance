"""Real local HTTP lifecycle, configuration persistence and artifact integration."""

import csv
import io
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from fan_governance.api.main import create_app


def tiny():
    return {
        "name": "api_test",
        "simulation": {
            "population": {"size": 8},
            "governance": {"waiting_period_days": 0},
            "voting": {"strategies": ["equal"]},
        },
        "timeline": {"duration_months": 1},
        "elections": {"interval_months": 1},
        "experiment": {"trials": 1},
    }


def test_health_discovery_validation_and_configuration_persistence(tmp_path):
    app = create_app(tmp_path, scenarios_dir=Path("configs/scenarios"))
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        assert client.get("/api/v1/capabilities").json()["defaults"]["experiment"]["trials"] == 1
        assert len(client.get("/api/v1/models").json()["models"]) >= 23
        scenarios = client.get("/api/v1/scenarios").json()["items"]
        assert len(scenarios) == 11
        profiles = client.get("/api/v1/profiles").json()["items"]
        assert len(profiles) == 6
        assert all("size" in item["configuration"] for item in profiles)
        assert client.get("/api/v1/scenarios/" + scenarios[0]["id"]).status_code == 200
        assert client.post(
            "/api/v1/configurations/validate", json={"configuration": tiny()}
        ).json()["valid"]
        invalid = tiny()
        invalid["simulation"]["population"]["size"] = -1
        assert (
            client.post(
                "/api/v1/configurations/validate", json={"configuration": invalid}
            ).status_code
            == 422
        )
        saved = client.post(
            "/api/v1/configurations/save", json={"name": "saved", "configuration": tiny()}
        ).json()
        assert client.get("/api/v1/configurations/" + saved["id"]).json()["name"] == "saved"
        assert client.get("/api/v1/configurations").json()["total"] == 1
        assert client.get("/api/v1/configurations/not-a-valid-id").status_code == 400
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/v1/configurations").json()["total"] == 1


def test_real_simulation_results_exports_comparison_and_delete(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        records = []
        for index in range(2):
            response = client.post(
                "/api/v1/runs", json={"name": f"run{index}", "configuration": tiny()}
            )
            assert response.status_code == 202, response.text
            record = response.json()
            deadline = time.monotonic() + 30
            while record["status"] in ("queued", "running") and time.monotonic() < deadline:
                time.sleep(0.05)
                record = client.get("/api/v1/runs/" + record["id"]).json()
            assert record["status"] == "completed", record
            records.append(record)
        identifier = records[0]["id"]
        page = client.get(f"/api/v1/runs/{identifier}/results?table=summary&limit=2").json()
        assert page["total"] == 3 and len(page["items"]) == 2
        assert page["items"][0]["trial"] == 0
        assert client.get(f"/api/v1/runs/{identifier}/events?limit=2").status_code == 200
        response = client.get(f"/api/v1/runs/{identifier}/export?format=csv")
        csv_rows = list(csv.DictReader(io.StringIO(response.text)))
        assert len(csv_rows) == 3 and {row["variant"] for row in csv_rows} == {
            "control",
            "unprotected",
            "defended",
        }
        exported = client.get(f"/api/v1/runs/{identifier}/export?format=json").json()
        assert len(exported) == 3
        archive = client.get(f"/api/v1/runs/{identifier}/export?format=zip")
        assert archive.content[:2] == b"PK"
        compare = client.post(
            "/api/v1/comparisons", json={"run_ids": [r["id"] for r in records]}
        ).json()
        assert compare["paired_differences"]
        assert client.delete("/api/v1/runs/" + identifier).status_code == 204
        assert client.get("/api/v1/runs/" + identifier).status_code == 404


def test_rejects_untrusted_browser_origin_and_unknown_export_tables(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert (
            client.post(
                "/api/v1/runs",
                json={"configuration": tiny()},
                headers={"Origin": "https://untrusted.example"},
            ).status_code
            == 403
        )
        assert (
            client.get("/api/v1/runs/" + "a" * 32 + "/results?table=../secret").status_code == 400
        )
