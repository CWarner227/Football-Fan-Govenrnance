import { lazy, Suspense, useState } from "react";
import type { Comparison } from "../types";
import { Notice } from "./Common";
import { human } from "./SchemaForm";
const Chart = lazy(() => import("./Chart"));
export default function ComparisonChart({
  comparison,
}: {
  comparison: Comparison;
}) {
  const [metric, setMetric] = useState("");
  const rows = comparison.runs.flatMap(({ run, summary }) =>
    summary.items.map((row, i) => ({
      ...row,
      run: `${run.name} · ${run.id.slice(0, 6)}`,
      observation: i + 1,
    })),
  );
  const columns = [...new Set(rows.flatMap(Object.keys))].filter(
    (k) =>
      rows.some(
        (row) => typeof (row as Record<string, unknown>)[k] === "number",
      ) && !["trial", "seed", "observation"].includes(k),
  );
  const selected = columns.includes(metric)
    ? metric
    : (columns.find((k) => /capture|turnout|gini/.test(k)) ?? columns[0]);
  return (
    <section className="panel">
      <h2>Observed outcomes by run</h2>
      <p className="hint">
        Each point is an engine-produced observation. Scatter points preserve
        individual observations and do not pool runs into an estimate. Inspect
        configuration warnings above.
      </p>
      {selected ? (
        <>
          <label className="field">
            Comparison metric
            <select
              value={selected}
              onChange={(e) => setMetric(e.target.value)}
            >
              {columns.map((c) => (
                <option key={c} value={c}>
                  {human(c)}
                </option>
              ))}
            </select>
          </label>
          <Suspense fallback={<Notice>Loading chart…</Notice>}>
            <Chart
              rows={rows}
              x="observation"
              y={selected}
              kind="scatter"
              category="run"
            />
          </Suspense>
        </>
      ) : (
        <Notice>No shared numeric outcomes are available.</Notice>
      )}
    </section>
  );
}
