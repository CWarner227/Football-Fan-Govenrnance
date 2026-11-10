# Running and reproducing Studies 01–07

The frozen design is documented in [PRESENTATION_STUDIES.md](PRESENTATION_STUDIES.md).
It contains 19 pilots and 76 presentation batches (100 presentation trials per
condition, from four distinct seeds). Pilots do not contribute to those estimates.

Start the existing Docker dashboard and import the saved presets before running:

```powershell
uv run --extra dashboard python examples/run_study_campaign.py --docker-export
```

The controller uses the local dashboard API to submit runs sequentially; each run
uses the engine's existing automatic CPU trial workers. It reuses completed exact
configurations/seeds and resumes matching active runs. The Docker export option
copies the five smaller scientific JSONL tables directly, avoiding row-by-row HTTP
export overhead. Raw event logs remain in the dashboard volume. The controller
pauses on simulation failure or insufficient physical drive space, rather than
silently reducing trials or changing parameters. The default reserve is 15 GiB;
`--min-free-gib` permits an explicitly reassessed reserve on another machine.

During the November 2026 campaign, the controller paused at the 15 GiB reserve
after 91 configurations. The final four combined-crisis batches were resumed with
`--min-free-gib 12` after their pilot sizes projected about 1 GiB of remaining
output. This operational change did not alter any scientific configuration.

The durable local ledger and analysis copies are in `results/study_campaign`.
Generated raw data is ignored by Git. Successful reruns with the same seed are not
additional independent replications. Do not run two campaign controllers together.

After all 95 configurations have completed:

```powershell
uv run --all-extras python examples/collect_campaign_provenance.py
uv run --all-extras python examples/report_study_campaign.py
uv run --all-extras python examples/write_study_findings.py
uv run --with reportlab python examples/publish_study_report.py
```

The PDF publisher requires ReportLab; analysis requires the project's `plots`
extra. The completed report, figures, derived CSVs and audit are written to
`reports/studies_01_07`. Exact analysis package versions are recorded in the audit;
per-run scientific source hashes and execution metadata accompany the report.

The analysis rejects missing/repeated trials, wrong seed designs, source-hash
mismatches, artifact-copy hash mismatches, row-count discrepancies and cash-ledger
discontinuities. It canonicalizes equivalent integer/float grid labels while
retaining original engine grid IDs in derived provenance columns. It streams full
economic audits and retains only the calendar rows needed for figures.

## Lossless event-log archives

For this campaign, archiving completed event logs was authorized to preserve disk
headroom. The archive utility validates a compressed file against the original
SHA-256 before removing the original event file. It never removes other scientific
tables or modifies the original manifest. Archive metadata is retained per run.

Restore an archived run before using its dashboard Events view or full ZIP export:

```powershell
docker compose exec -T dashboard python /app/data/dashboard/archive_campaign_events.py restore RUN_ID
```

If the helper is not already in the volume, copy it first:

```powershell
docker cp examples/archive_campaign_events.py football-governance-dashboard-1:/app/data/dashboard/archive_campaign_events.py
```

Archiving a completed run uses the same command with `archive` instead of
`restore`. Restore needs enough free space for the full uncompressed log. Docker's
virtual disk can retain allocated Windows disk space after files are compressed;
logical savings inside the volume do not guarantee immediate physical reclamation.

These experiments are synthetic sensitivity studies. The report's uncertainty
estimates are conditional on the model assumptions, not empirical club forecasts
or measured blockchain/security benefits.
