"""Copy small manifests and event-archive metadata from the dashboard volume."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ledger = json.loads((ROOT / "results/study_campaign/ledger.json").read_text())
    if len(ledger) != 95 or any(r["status"] != "completed" for r in ledger.values()):
        raise ValueError("Campaign incomplete")
    ids = [r["run_id"] for r in ledger.values()]
    code = """
import hashlib,json,pathlib,sys
from collections import Counter
root=pathlib.Path('/app/data/dashboard/runs')
out={}
for identifier in json.loads(sys.argv[1]):
    p=root/identifier
    manifest=json.loads((p/'artifacts/manifest.json').read_text())
    archive=p/'event_archive.json'
    hashes={}
    for table in ('summary','elections','timeseries','aggregate','defense_effectiveness'):
        with (p/'artifacts'/(table+'.jsonl')).open('rb') as stream:
            hashes[table]=hashlib.file_digest(stream,'sha256').hexdigest()
    out[identifier]={'manifest':manifest,'artifact_sha256':hashes,'event_archive':json.loads(archive.read_text()) if archive.exists() else None}
    if manifest['configuration']['name'].startswith('presentation_v1_07-combined_batch'):
        selected=[json.loads(line) for line in (p/'artifacts/summary.jsonl').open()]
        selected=[r for r in selected if r['attacks.0.parameters.contribution_budget']==100000 and r['variant'] in ('unprotected','defended')]
        expected={(r['grid_id'],r['trial'],r['voting_model'],r['variant']) for r in selected}
        expirations=set(); days=Counter(); reasons=Counter(); joined=0; digest=hashlib.sha256()
        for line in (p/'artifacts/events.jsonl').open('rb'):
            digest.update(line)
            if b'membership_expiration' not in line and b'attack_join' not in line:
                continue
            event=json.loads(line)
            key=event['grid_id'],event['trial'],event['voting_model'],event['variant']
            if key not in expected or not event.get('target_id','').startswith('synthetic-attacker:account:'):
                continue
            if event['kind']=='attack_join':
                joined+=1
            elif event['kind']=='membership_expiration':
                expirations.add(key); days[str(event['day'])]+=1; reasons[event.get('reason','')]+=1
        out[identifier]['combined_budget_diagnostic']={
            'trajectory_count':len(selected),'join_events':joined,'expired_trajectories':len(expirations),
            'spent_full_budget_count':sum(r['financial_spent']==100000 for r in selected),
            'zero_hostile_membership_survival_count':sum(r['hostile_membership_survival']==0 for r in selected),
            'zero_final_attacker_power_count':sum(r['attacker_power_share']==0 for r in selected),
            'capture_count':sum(r['capture_success'] for r in selected),
            'expiration_day_counts':dict(days),'expiration_reason_counts':dict(reasons),
            'all_target_paths_expired':expirations==expected,'events_sha256':digest.hexdigest()}
print(json.dumps(out))
"""
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "dashboard", "python", "-c", code, json.dumps(ids)],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)
    assert len(payload) == 95
    output = ROOT / "reports/studies_01_07"
    output.mkdir(parents=True, exist_ok=True)
    (output / "source_manifests.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    diagnostics = {
        identifier: entry["combined_budget_diagnostic"]
        for identifier, entry in payload.items()
        if "combined_budget_diagnostic" in entry
    }
    (output / "combined_crisis_diagnostic.json").write_text(
        json.dumps(diagnostics, indent=2), encoding="utf-8"
    )
    print("Collected 95 scientific manifests and archive metadata")


if __name__ == "__main__":
    main()
