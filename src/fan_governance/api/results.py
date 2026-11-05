"""Streaming artifact queries and explicit matched-trial comparisons."""

import csv
import heapq
import io
import json
import math
import os
import tempfile
import zipfile
from itertools import combinations
from pathlib import Path

TABLES = frozenset(
    {"summary", "elections", "timeseries", "events", "aggregate", "defense_effectiveness"}
)
METRICS = (
    "turnout",
    "gini",
    "attacker_power_share",
    "attacker_vote_share",
    "capture_success",
    "passed",
    "cash_balance",
    "administrative_cost",
    "financial_runway_months",
)


def flatten(value, prefix=""):
    result = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict) and item:
            result.update(flatten(item, path))
        else:
            result[path] = item
    return result


def _order(value):
    if value is None:
        return (3, "")
    if isinstance(value, (int, float)):
        return (0, float(value))
    return (1, str(value).casefold())


class ResultsService:
    def __init__(self, repository):
        self.repository = repository

    def artifact(self, run_id, filename):
        record = self.repository.get("runs", run_id)
        if record["status"] != "completed":
            raise ValueError("Results are available only for completed runs")
        directory = self.repository.directory("runs", run_id)
        path = directory / "artifacts" / filename
        for component in (path, path.parent):
            if component.is_symlink() or component.is_junction():
                raise ValueError("Linked artifacts are not supported")
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Invalid artifact path")
        if not path.is_file():
            raise KeyError("Result artifact is not available")
        return path

    def rows(self, run_id, table):
        if table not in TABLES:
            raise ValueError("Unknown result table")
        path = self.artifact(run_id, f"{table}.jsonl")
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)

    def page(
        self,
        run_id,
        table,
        *,
        offset=0,
        limit=100,
        search="",
        sort="",
        descending=False,
        filters=None,
    ):
        if not 0 <= offset <= 100000 or not 1 <= limit <= 5000:
            raise ValueError("Page offset or limit exceeds local query bounds")
        columns, total, selected = set(), 0, []
        filters = {k: v for k, v in (filters or {}).items() if v is not None and v != ""}

        def matches():
            nonlocal total
            for raw in self.rows(run_id, table):
                row = flatten(raw)
                columns.update(row)
                if any(str(row.get(k)) != str(v) for k, v in filters.items()):
                    continue
                if (
                    search
                    and search.casefold() not in json.dumps(row, ensure_ascii=False).casefold()
                ):
                    continue
                total += 1
                yield row

        if sort:
            # Bounded heap, not an in-memory copy of the whole table.
            function = heapq.nlargest if descending else heapq.nsmallest
            selected = function(offset + limit, matches(), key=lambda row: _order(row.get(sort)))[
                offset:
            ]
        else:
            for index, row in enumerate(matches()):
                if offset <= index < offset + limit:
                    selected.append(row)
        return {
            "items": selected,
            "total": total,
            "offset": offset,
            "limit": limit,
            "columns": sorted(columns),
        }

    def export_rows(self, run_id, table, format):
        if format not in ("csv", "json"):
            raise ValueError("Unsupported export format")
        # Validate before a StreamingResponse sends its headers.
        if table not in TABLES:
            raise ValueError("Unknown result table")
        self.artifact(run_id, f"{table}.jsonl")
        if format == "json":

            def objects():
                yield "["
                for index, row in enumerate(self.rows(run_id, table)):
                    yield ("," if index else "") + json.dumps(
                        row, ensure_ascii=False, allow_nan=False
                    )
                yield "]"

            return objects()
        columns = set()
        for row in self.rows(run_id, table):
            columns.update(flatten(row))
        columns = sorted(columns) or ["scenario", "trial"]

        def csv_rows():
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=columns)
            writer.writeheader()
            yield buffer.getvalue()
            for row in self.rows(run_id, table):
                buffer.seek(0)
                buffer.truncate(0)
                writer.writerow(
                    {
                        k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                        for k, v in flatten(row).items()
                    }
                )
                yield buffer.getvalue()

        return csv_rows()

    def facets(self, run_id, table):
        if table not in TABLES:
            raise ValueError("Unknown result table")
        manifest = json.loads(self.artifact(run_id, "manifest.json").read_text(encoding="utf-8"))
        if table in manifest.get("facets", {}):
            return {
                "facets": manifest["facets"][table],
                "truncated": manifest.get("facets_truncated", {}).get(table, False),
            }
        fields = ("grid_id", "voting_model", "variant", "metric")
        values = {key: set() for key in fields}
        truncated = False
        for row in self.rows(run_id, table):
            for key in fields:
                if row.get(key) is not None:
                    value = str(row[key])
                    if len(values[key]) < 500 or value in values[key]:
                        values[key].add(value)
                    else:
                        truncated = True
        return {
            "facets": {key: sorted(items) for key, items in values.items()},
            "truncated": truncated,
        }

    def archive(self, run_id):
        self.artifact(run_id, "manifest.json")
        directory = self.repository.directory("runs", run_id)
        destination = directory / "results.zip"
        if destination.is_symlink() or destination.is_junction():
            raise ValueError("Invalid export path")
        if destination.exists():
            return destination
        descriptor, temporary = tempfile.mkstemp(dir=directory, suffix=".zip")
        os.close(descriptor)
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for table in sorted(TABLES):
                    archive.write(self.artifact(run_id, f"{table}.jsonl"), f"{table}.jsonl")
                archive.write(self.artifact(run_id, "manifest.json"), "manifest.json")
                archive.writestr(
                    "run.json", json.dumps(self.repository.get("runs", run_id), indent=2)
                )
                configuration = directory / "artifacts" / "configuration.json"
                if configuration.is_file():
                    archive.write(self.artifact(run_id, "configuration.json"), "configuration.json")
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return destination

    def compare(self, run_ids):
        if len(set(run_ids)) != len(run_ids) or not 2 <= len(run_ids) <= 4:
            raise ValueError("Choose two to four distinct completed runs")
        runs = [
            {
                "run": self.repository.get("runs", identifier),
                "summary": self.page(identifier, "summary", limit=500),
            }
            for identifier in run_ids
        ]
        configurations = {item["run"]["id"]: flatten(item["run"]["configuration"]) for item in runs}
        paths = sorted(set().union(*(c.keys() for c in configurations.values())))
        differences = [
            {
                "path": path,
                "values": {identifier: c.get(path) for identifier, c in configurations.items()},
            }
            for path in paths
            if len({json.dumps(c.get(path), sort_keys=True) for c in configurations.values()}) > 1
        ]
        warnings, paired = [], []
        paired_total = 0
        for left, right in combinations(runs, 2):
            a, b = left["run"], right["run"]
            ca, cb = a["configuration"], b["configuration"]
            reasons = []
            for path, label in [
                ("simulation.population", "population"),
                ("experiment.seed", "seed"),
                ("experiment.trials", "trial count"),
                ("timeline", "timeline"),
                ("elections", "election schedule"),
                ("simulation.proposal", "proposal definition"),
                ("attacks", "attacker objectives/strategies"),
            ]:

                def pick(config, path=path):
                    value = config
                    for part in path.split("."):
                        value = value.get(part, {}) if isinstance(value, dict) else None
                    return value

                # An attack parameter change is a legitimate intervention; objectives must match.
                if path == "attacks":
                    av = [x.get("objective", {}) for x in ca.get("attacks", [])]
                    bv = [x.get("objective", {}) for x in cb.get("attacks", [])]
                else:
                    av, bv = pick(ca), pick(cb)
                if av != bv:
                    reasons.append(label)
            if reasons:
                warnings.append(
                    f"{a['name']} vs {b['name']}: incompatible {', '.join(reasons)}; no paired effects estimated."
                )
                continue
            rows_a, rows_b = left["summary"]["items"], right["summary"]["items"]
            if left["summary"]["total"] > 500 or right["summary"]["total"] > 500:
                warnings.append(
                    "Comparison truncated to 500 summary rows per run; export full records for broader analysis."
                )
            models_a = {r.get("voting_model") for r in rows_a}
            models_b = {r.get("voting_model") for r in rows_b}
            single = len(models_a) == len(models_b) == 1

            def key(row, single=single):
                return (
                    row.get("grid_id"),
                    row.get("trial"),
                    row.get("variant"),
                    None if single else row.get("voting_model"),
                )

            index = {key(row): row for row in rows_b}
            for first in rows_a:
                second = index.get(key(first))
                if second is None:
                    continue
                for metric in METRICS:
                    x, y = first.get(metric), second.get(metric)
                    if (
                        not isinstance(x, (int, float))
                        or not isinstance(y, (int, float))
                        or not math.isfinite(x)
                        or not math.isfinite(y)
                    ):
                        continue
                    paired_total += 1
                    if len(paired) >= 5000:
                        continue
                    paired.append(
                        {
                            "left_run_id": a["id"],
                            "right_run_id": b["id"],
                            "trial": first.get("trial"),
                            "grid_id": first.get("grid_id"),
                            "variant": first.get("variant"),
                            "voting_model": first.get("voting_model"),
                            "metric": metric,
                            "left": x,
                            "right": y,
                            "difference": float(y) - float(x),
                        }
                    )
        if paired_total > len(paired):
            warnings.append(
                f"Paired details truncated to {len(paired):,} of {paired_total:,} matched metric differences within the selected summaries; export full records for analysis."
            )
        if not paired:
            warnings.append(
                "No comparable matched trial pairs are available. Inspect configurations before drawing conclusions."
            )
        warnings.append(
            "Comparisons describe synthetic assumptions; uncontrolled configuration differences do not establish causation."
        )
        return {
            "runs": runs,
            "warnings": warnings,
            "differences": differences,
            "paired_differences": paired,
        }
