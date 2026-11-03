"""Research baseline artifacts layered on the existing export schema."""

import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import yaml

from fan_governance.core.config import SimulationConfig
from fan_governance.elections.models import SimulationResult
from fan_governance.experiments.comparison import comparison_summary
from fan_governance.output.exporters import results_frame
from fan_governance.output.provenance import source_provenance


def export_baseline(
    results: list[SimulationResult],
    config: SimulationConfig,
    directory: str | Path,
    *,
    elapsed_seconds: float,
) -> dict[str, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        name: directory / filename
        for name, filename in {
            "trials": "baseline_trials.csv",
            "summary": "baseline_summary.csv",
            "config": "baseline_config.yaml",
            "metadata": "baseline_metadata.json",
        }.items()
    }
    frame = results_frame(results)
    frame.to_csv(paths["trials"], index=False)
    comparison_summary(results).to_csv(paths["summary"], index=False)
    paths["config"].write_text(
        yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )
    versions = dict(results[0].execution_metadata) if results else {}
    metadata = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "synthetic": True,
        "seed": config.experiment.seed,
        "configuration": config.model_dump(mode="json"),
        "result_count": len(results),
        "elapsed_seconds": elapsed_seconds,
        "environment": {
            name: versions.get(name)
            for name in (
                "python",
                "numpy",
                "pandas",
                "pydantic",
                "fan_governance",
                "rng",
                "stream_scheme",
            )
        },
        **source_provenance(),
        "processor": platform.processor(),
        "pairing": "Same immutable electorate, memberships, eligibility, proposal, turnout, preferences per scenario/trial; only weights vary.",
    }
    paths["metadata"].write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8")
    if "parquet" in config.output.formats:
        try:
            paths["parquet"] = directory / "baseline_trials.parquet"
            frame.to_parquet(paths["parquet"], index=False, engine="pyarrow")
        except ImportError as error:
            raise ValueError("Baseline Parquet export requires the parquet extra") from error
    return paths
