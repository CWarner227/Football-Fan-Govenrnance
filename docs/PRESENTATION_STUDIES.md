# Presentation study configurations

These are planned synthetic experiments, not completed research results. All six
voting models and matched control/unprotected/defended variants are retained.
The bundle has **95 saved configurations: 19 pilots and 76 presentation batches**.

## Run from the frontend

The presets have been imported into the current local dashboard's Saved
configurations. Open **Experiments**, enter a study name in **Search saved
configurations**, and choose a preset in **Saved configurations**. Validate it,
then click **Run experiment**. Loading adds `copy` to the run name; this does not
change the configuration or seed. Run names can be edited for clarity.

1. Start with each group's **PILOT 10 trials**. Search `PILOT` to find all 19.
2. Check events, outcomes, elapsed time and population/attack assumptions. Change
   ranges deliberately if needed, document the changes, then freeze the design.
3. Run **B01, B02, B03, B04** once each for every retained group. Each has 25
   trials per grid cell: the four batches provide **100 trials per condition**.
4. Export each completed run as ZIP. Keep its configuration, source provenance,
   seed and grid labels alongside its results. Failed/cancelled runs do not count.

Rerunning the same preset repeats its seed; it does **not** provide new independent
replications. Pilots use seed 99001; presentation batches use 11001–11004. Matching
batch numbers reuse the same seed across study groups for controlled comparisons.
Population seeds are unset so populations vary with each trial/master seed.

## Study groups

| Search | Groups | Cells per group | Design |
| --- | ---: | --- | --- |
| `Study 01` | 1 | 6 | 10,000 supporters; ordinary, wealth-unequal (wealth sigma 2), low participation (0.15); constitutional/funding proposals; one election, economics disabled. |
| `Study 02` | 1 | 3 | 200 supporters; wealthy attacker contributions 5,000/50,000/250,000; financial budget 300,000; verification plus cap 5 in defended variant. |
| `Study 03` | 3 | 3 | Verification strength 0/0.8/1 separated into groups; attempted aliases 50/200/400 for 200 ordinary supporters. |
| `Study 04` | 4 | 3 | Honest turnout 0.2/0.6 x hostile share 0.1/0.3 separated into groups; waiting periods 0/90/180 days; quarterly elections over 12 months. |
| `Study 05` | 4 | 4 | Honest turnout 0.2/0.6 x hostile turnout 0.5/1; 15% recruited; verification alone, +quorum 0.4, +incentive 0.2, +both. |
| `Study 06` | 4 | 3/3/3/1 | Existing ten defense packages split into four sets; 200 attempted aliases for 200 supporters; quarterly elections. |
| `Study 07 Economic` | 1 | 16 | Fees 0/30 x population 100/300 x downturn severity 0.3/0.7 x no capital/30,000 capital without voting rights. |
| `Study 07 Combined` | 1 | 4 | Revenue-loss severity 0.3/0.7 x wealthy attacker contribution 10,000/100,000; downturn fixed at 0.5, protected capital and combined defenses retained. |

The final row extends the seventh study with combined-crisis sensitivity. Most
adversarial scenarios last 12 months with six-month elections; Studies 04/06 use
quarterly elections to expose waiting-period expiry. Study 04's 100 operational
units cover at most 86 intended joins; Study 05 has 30 recruitment operations.
Wealthy attackers have one operation for their specified lump-sum join. Sybil
budgets match the number of attempted identities. These are documented finite
budgets, replacing the oversized 10,000-operation demonstration defaults.

Study 06 sets preserve the original policy ordering:

- Set 1: 180-day wait; cap 3; quorum 0.5.
- Set 2: participation boost 0.4; suspicious-activity temporary restriction;
  verification strength 0.
- Set 3: verification strength 1; verification plus wait; verification plus
  suspicious-activity manual review.
- Set 4: verification, cap 3, quorum 0.3, and participation boost 0.2 together.

Every preset passes authoritative dashboard validation, including all grid cells,
strategy factories and the 300-million work-unit limit. That bound is an estimate,
not a guarantee of runtime or memory usage. Inspect pilots before queueing a large
campaign; the existing 30-minute timeout still applies. No full campaign is
launched by generation or import.

## Interpret results correctly

- Study 01's three required variants are redundant references without attacks or
  defenses. Use **control** for baseline figures; do not count them as three
  independent samples. Honest turnout is not forced, allowing profile differences.
- Preserve grid/model/variant labels and use matched seeds/trials for differences.
  Repeated elections and voting models within a trial are related observations.
- Cast-weight capture and hostile proposal passage are different outcomes.
- Verification acceptance/rejection probabilities and all economic relationships
  remain synthetic. Existing defense packages retain their own parameters; a
  same-named strength setting alone does not establish identical verification
  assumptions across different studies.
- Batch-local trial indices restart at zero. Identify observations by **master
  seed + trial + grid + model + variant**, never by trial index alone.
- Do not average confidence interval endpoints or pool repeated controls. For a
  final 100-trial estimate, combine the four batches' raw summaries by the actual
  condition and recompute uncertainty. The dashboard's Compare view is a bounded,
  matched-run inspection tool, not a cross-seed statistical pooling tool. Use full
  exports for the final combined analysis.
- For 400-trial follow-up, create twelve additional 25-trial batches with new
  seeds 11005–11016 for selected conditions; keep the same scientific settings.
  These additional configurations are not preloaded in the 100-trial bundle.

## Restore or import on another machine

With Docker Desktop running, double-click **Import-Study-Configurations.cmd**.
It builds/starts the dashboard, imports missing presets and opens Experiments.
No host Python installation is needed. It does not start any simulations.

Equivalent command after `docker compose up --build -d --wait`:

```sh
docker compose exec -T dashboard python examples/presentation_studies.py --no-write --import-url http://127.0.0.1:8000
```

Existing identical presets are skipped. A same-name preset with changed scientific
settings or description causes a conflict instead of overwriting user work.
Output directory separators are compared portably between Windows and Linux.

For a source installation:

```sh
uv run --extra dashboard python examples/presentation_studies.py --import-url http://127.0.0.1:8000
```

Omit `--import-url` to generate YAML files and `manifest.json` only. The generated
bundle lives in `configs/presentation_studies/`; the manifest lists each preset's
group, seed-bearing description, filename and workload estimate. These files are
separate from the original Scenario Library and experiment demonstration suite.
