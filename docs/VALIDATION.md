# Phase 1 verification evidence

Historical Phase 1 record. Current Phase 2 verification and executed measurements
are recorded in PHASE2_RESULTS.md.

Verified locally on Windows, October 27, 2026, using Python 3.14.7. The package declares
Python >=3.12; this session did not execute tests on Python 3.12 or 3.13. Dependencies
and environment versions are retained in uv.lock and the demonstration manifest.

## Automated checks

```sh
uv run pytest --basetemp .pytest-work --cov=fan_governance --cov-report=term
uv run ruff check .
uv run ruff format --check .
uv build
```

Latest full suite: **68 passed**, **97% statement coverage** (703 statements, 23 missed).
Ruff lint passed; 42 Python files were already formatted. Coverage includes in-process
CLI checks; subprocess CLI integration is also exercised independently.

Tests cover voting formulas, negative/nonfinite weight rejection, extreme logarithm
stability, all four distribution families, opt-in correlations, generated 10,000-member
populations, domain validation, waiting periods (0/90/180/365/custom), duplicate canonical
membership, inactive/unverified membership, quorum/approval/aggregation, abstentions,
invalid ballots, ties, empty/zero-power elections, stream independence, exact substantive
reproducibility, strategy reordering, custom strategies/eligibility/behavior/distributions/
metrics, batch grids, CSV/JSON/Parquet, plotting, and malformed configuration errors.

## Packaging and execution

- Built an sdist and wheel using the configured uv_build backend.
- Installed that wheel into a fresh isolated uv environment and ran a 10-supporter
  simulation; confirmed Matplotlib and PyArrow were absent in that environment.
- Ran the installed `fan-governance models` console entry point and the library example.
- Ran the complete 100-trial x 10,000-supporter x four-strategy CLI experiment.
- Retained all 400 structured rows plus seeds, configuration, version metadata,
  summary CSV, manifest and a derived outcome-disagreement comparison.
- Generated a Matplotlib comparison figure and the measured demonstration report.

The independent code reviewer found one finite-input intermediate overflow in the
diminishing formula. A failing regression reproduced it; a stable logarithm expression
fixed it, followed by a passing full suite. The suite also caught and fixed skipped
bound validation for custom distribution names. No claim of security auditing or
empirical calibration follows from these checks.

## Local tooling notes

The sandbox blocked uv's initial executable setup and Pytest's default system temporary
directory. The approved project-local installation and a workspace-local `--basetemp`
resolved those environment limitations. The documented normal uv commands work in the
prepared environment. Verification used the installed `.venv/Scripts` commands directly
where appropriate. Generated environments/caches/test scratch directories are excluded
from lint scope and Git; they are absent from the checked distribution contents.

Raw benchmark values and timing are in [DEMONSTRATION.md](DEMONSTRATION.md). Runtime
depends on hardware and concurrent system load. The framework has no empirical
takeover-resistance claim and no Phase 2 attack implementation.
