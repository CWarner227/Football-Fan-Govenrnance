"""JSON is lossless; CSV/Parquet flatten metrics and retain nested provenance as JSON."""

import json
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from fan_governance.elections.models import SimulationResult


def results_frame(results: Sequence[SimulationResult]) -> pd.DataFrame:
    rows = []
    for result in results:
        row = result.model_dump(mode="json")
        for name in ("configuration", "governance_configuration", "component_seeds"):
            row[name] = json.dumps(row[name], sort_keys=True, allow_nan=False)
        rows.append(row)
    return pd.json_normalize(rows)


def export_results(
    results: Sequence[SimulationResult],
    directory: str | Path,
    formats: Sequence[str] = ("csv", "json"),
) -> dict[str, Path]:
    unknown = set(formats) - {"csv", "json", "parquet"}
    if unknown:
        raise ValueError(f"Unknown export formats: {sorted(unknown)}")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {}
    frame = None
    for format_name in dict.fromkeys(formats):
        path = directory / f"results.{format_name}"
        if format_name == "json":
            path.write_text(
                json.dumps([r.model_dump(mode="json") for r in results], indent=2, allow_nan=False),
                encoding="utf-8",
            )
        else:
            if frame is None:
                frame = results_frame(results)
            if format_name == "csv":
                frame.to_csv(path, index=False)
            else:
                try:
                    frame.to_parquet(path, index=False, engine="pyarrow")
                except ImportError as error:
                    raise ValueError(
                        "Parquet export requires the optional parquet extra"
                    ) from error
        paths[format_name] = path
    return paths
