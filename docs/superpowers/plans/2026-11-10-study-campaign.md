# Studies 01–07 execution and research report

**Goal:** Execute all 95 frozen presets and summarize actual results for an academic audience.

**Method:** Reuse exact completed configurations and seeds, run remaining pilots before presentation batches through the dashboard, then analyze raw trial summaries. Preserve complete dashboard artifacts; copy smaller analysis tables to ignored results storage. Create a reproducible report with figures and condition-level tables.

- [x] Execute 19 pilots and 76 presentation batches, recording every selected run ID.
- [x] Verify 100 distinct seed/trial observations per presentation condition/model/variant; keep pilots separate.
- [x] Recompute binary Wilson intervals, paired contrasts, continuous distributions, and calendar outcomes from raw rows.
- [x] Audit financial continuity and source provenance; never pool heterogeneous conditions or duplicate references.
- [x] Produce and visually inspect PDF/HTML figures, tables, methods, limitations, and research implications.

**Files:** `examples/run_study_campaign.py` owns resumable execution; `examples/report_study_campaign.py` owns analysis and report source generation; `results/study_campaign` holds analysis data and ledger; `reports/studies_01_07` holds the shareable report and derived tables/figures.

**Checks:** Exact configuration reuse including integer/float equivalent JSON; missing/duplicate trials rejected; Wilson interval edge cases; paired observations keyed by seed/trial; complete 95-run ledger; accounting identities checked independently; visual inspection of final pages.

**Verified outcome:** 95 completed configurations; 1,368 presentation estimates at 100 trials each; 475 copied artifacts match source hashes; 1,801,800 economic rows and 1,663,200 cash transitions reconcile; 32 targeted/configuration tests pass. Report: 30 PDF pages, HTML, 15 standalone PNG/SVG figures. The combined-crisis 100k attacker exhausts its budget and expires on day 31 in all 2,400 targeted correlated trajectories; the report explicitly excludes interpreting this as defensive efficacy.

**Operational note:** The initial 15 GiB reserve paused the controller after 91 configurations. Measured remaining output was about 1 GiB; the last four batches completed with a reassessed 12 GiB reserve. Scientific settings were unchanged.

**Constraints:** Frozen scientific settings, seeds 99001 (pilots) and 11001–11004 (presentation), six models, three matched variants, 15 GiB physical-drive reserve. Synthetic uncalibrated assumptions; monetary amounts have no real currency calibration. No claims of actual club takeover, empirically established verification accuracy, or measured blockchain benefit.
