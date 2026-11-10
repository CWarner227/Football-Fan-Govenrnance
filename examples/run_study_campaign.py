"""Resume the frozen presentation campaign through the dashboard API.

Run with the dashboard already started. Ledger and small analysis exports live in
results/study_campaign; full event logs remain in the dashboard volume.
"""

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "results" / "study_campaign"


def fingerprint(config):
    config = json.loads(json.dumps(config))
    # Worker-controlled destinations are not scientific settings.
    for section in (config, config.get("simulation", {})):
        section.pop("output", None)
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-free-gib",
        type=float,
        default=15,
        help="Physical-drive reserve checked before each new run",
    )
    parser.add_argument(
        "--docker-export",
        action="store_true",
        help="Copy raw JSONL directly from the local Docker volume",
    )
    args = parser.parse_args()
    if args.min_free_gib <= 0:
        parser.error("--min-free-gib must be positive")
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "configs/presentation_studies/manifest.json").read_text())
    ledger_path = DEST / "ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=120) as client:
        configurations = (
            client.get("/api/v1/configurations?limit=500").raise_for_status().json()["items"]
        )
        configurations = {item["name"]: item for item in configurations}
        # Pilot checks precede confirmatory batches; original recipe order retained.
        manifest.sort(key=lambda item: item["stage"] != "pilot")
        for index, entry in enumerate(manifest):
            key = entry["group"] + "/" + entry["stage"]
            config = configurations[entry["name"]]["configuration"]
            wanted = fingerprint(config)
            runs = client.get("/api/v1/runs?limit=500").raise_for_status().json()["items"]
            matches = [r for r in runs if fingerprint(r["configuration"]) == wanted]
            complete = [r for r in matches if r["status"] == "completed"]
            active = [r for r in matches if r["status"] in ("running", "queued")]
            if complete:
                run = sorted(complete, key=lambda r: r["completed_at"])[-1]
                print(f"REUSE {key}: {run['id']}", flush=True)
            elif active:
                run = active[0]
            else:
                if shutil.disk_usage(ROOT).free < args.min_free_gib * 1024**3:
                    raise RuntimeError(
                        f"Campaign paused: less than {args.min_free_gib:g} GiB physical drive space remains."
                    )
                run = (
                    client.post(
                        "/api/v1/runs",
                        json={
                            "name": entry["name"],
                            "description": entry["description"],
                            "kind": "experiment",
                            "configuration": config,
                        },
                    )
                    .raise_for_status()
                    .json()
                )
                print(f"START {index + 1}/95 {key}: {run['id']}", flush=True)
            while run["status"] in ("queued", "running"):
                ledger[key] = dict(entry, run_id=run["id"], status=run["status"])
                ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
                print(
                    f"PROGRESS {key}: {run.get('progress')} elapsed={run.get('elapsed_seconds')}",
                    flush=True,
                )
                time.sleep(5)
                run = client.get(f"/api/v1/runs/{run['id']}").raise_for_status().json()
            if run["status"] != "completed":
                raise RuntimeError(f"Campaign paused at {key}: {run['status']}: {run.get('error')}")
            local = DEST / entry["group"] / entry["stage"]
            local.mkdir(parents=True, exist_ok=True)
            for table in (
                "summary",
                "elections",
                "timeseries",
                "aggregate",
                "defense_effectiveness",
            ):
                if args.docker_export:
                    target = local / (table + ".jsonl")
                    if not target.exists():
                        temporary = target.with_suffix(".download.tmp")
                        subprocess.run(
                            [
                                "docker",
                                "cp",
                                f"football-governance-dashboard-1:/app/data/dashboard/runs/{run['id']}/artifacts/{table}.jsonl",
                                str(temporary),
                            ],
                            check=True,
                            capture_output=True,
                        )
                        temporary.replace(target)
                    continue
                target = local / (table + ".json")
                if not target.exists():
                    with client.stream(
                        "GET",
                        f"/api/v1/runs/{run['id']}/export",
                        params={"format": "json", "table": table},
                    ) as response:
                        response.raise_for_status()
                        temporary = target.with_suffix(".download.tmp")
                        with temporary.open("wb") as output:
                            for chunk in response.iter_bytes():
                                output.write(chunk)
                        temporary.replace(target)
            (local / "record.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
            ledger[key] = dict(
                entry, run_id=run["id"], status="completed", elapsed_seconds=run["elapsed_seconds"]
            )
            ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
            print(f"DONE {index + 1}/95 {key} ({run['elapsed_seconds']:.1f}s)", flush=True)
    print("CAMPAIGN COMPLETE: 95 configurations", flush=True)


if __name__ == "__main__":
    main()
