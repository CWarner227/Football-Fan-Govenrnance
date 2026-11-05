import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { Row, Run } from "../types";
export function SelectorPagination({
  offset,
  total,
  onPage,
  label,
}: {
  offset: number;
  total: number;
  onPage: (offset: number) => void;
  label: string;
}) {
  return (
    <div className="pagination">
      <span>
        {total} available · page {Math.floor(offset / 50) + 1}
      </span>
      <button
        type="button"
        className="secondary"
        aria-label={`Previous ${label}`}
        disabled={offset === 0}
        onClick={() => onPage(Math.max(0, offset - 50))}
      >
        Previous
      </button>
      <button
        type="button"
        className="secondary"
        aria-label={`Next ${label}`}
        disabled={offset + 50 >= total}
        onClick={() => onPage(offset + 50)}
      >
        Next
      </button>
    </div>
  );
}
export function PageTitle({
  eyebrow = "Research workspace",
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
      </div>
      <div className="actions">{children}</div>
    </div>
  );
}
export function Notice({
  error,
  children,
}: {
  error?: unknown;
  children?: ReactNode;
}) {
  return (
    <div
      className={error ? "notice error" : "notice"}
      role={error ? "alert" : "status"}
    >
      {error
        ? error instanceof Error
          ? error.message
          : String(error)
        : children}
    </div>
  );
}
export function Status({ status }: { status: string }) {
  return <span className={`status ${status}`}>{status}</span>;
}
export function format(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "number")
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumSignificantDigits: 6 });
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
export function DataTable({
  rows,
  columns,
  onSort,
}: {
  rows: Row[];
  columns?: string[];
  onSort?: (key: string) => void;
}) {
  const cols = columns?.length
    ? columns
    : [...new Set(rows.flatMap(Object.keys))];
  return rows.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c}>
                {onSort ? (
                  <button type="button" onClick={() => onSort(c)}>
                    {c.replace(/_/g, " ")} ↕
                  </button>
                ) : (
                  c.replace(/_/g, " ")
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c} title={format(row[c])}>
                  {format(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Notice>No data is available for this selection.</Notice>
  );
}
export function PagedDataTable({
  rows,
  columns,
  label,
}: {
  rows: Row[];
  columns?: string[];
  label: string;
}) {
  const [offset, setOffset] = useState(0);
  const start = Math.min(
    offset,
    Math.max(0, Math.floor((rows.length - 1) / 50) * 50),
  );
  return (
    <>
      <DataTable rows={rows.slice(start, start + 50)} columns={columns} />
      <SelectorPagination
        offset={start}
        total={rows.length}
        onPage={setOffset}
        label={label}
      />
    </>
  );
}
export function RunList({ runs }: { runs: Run[] }) {
  return runs.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Run</th>
            <th>Type</th>
            <th>Status</th>
            <th>Created</th>
            <th>Elapsed</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id}>
              <td>
                <Link className="text-link" to={`/results/${r.id}`}>
                  {r.name}
                </Link>
                <small className="run-id">{r.id.slice(0, 8)}</small>
              </td>
              <td>{r.kind}</td>
              <td>
                <Status status={r.status} />
              </td>
              <td>{new Date(r.created_at).toLocaleString()}</td>
              <td>{format(r.elapsed_seconds)} s</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Notice>
      No runs yet. Start with a scenario or build a configuration.
    </Notice>
  );
}
export function ExecutionHistory({ runs }: { runs: Run[] }) {
  const completed = runs.filter(
    (r) => r.status === "completed" && Number.isFinite(r.elapsed_seconds),
  );
  const maximum = Math.max(1, ...completed.map((r) => r.elapsed_seconds));
  return (
    <section className="panel">
      <h2>Recent execution durations</h2>
      <p className="hint">
        Measured seconds per completed run. Different configurations can require
        different work.
      </p>
      {completed.length ? (
        completed.map((r) => (
          <label className="field" key={r.id}>
            {r.name} · {format(r.elapsed_seconds)} seconds
            <meter
              aria-label={`${r.name} elapsed seconds`}
              min={0}
              max={maximum}
              value={r.elapsed_seconds}
              style={{ width: "100%", height: 24 }}
            />
          </label>
        ))
      ) : (
        <Notice>Complete a run to see measured execution history.</Notice>
      )}
    </section>
  );
}
export function RunMonitor({ id }: { id: string }) {
  const client = useQueryClient();
  const run = useQuery({
    queryKey: ["run", id],
    queryFn: () => api.run(id),
    refetchInterval: (q) =>
      ["queued", "running"].includes(q.state.data?.status ?? "") ? 1500 : false,
  });
  const cancel = useMutation({
    mutationFn: () => api.cancel(id),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["run", id] });
      void client.invalidateQueries({ queryKey: ["runs"] });
    },
  });
  if (run.error) return <Notice error={run.error} />;
  if (!run.data) return <Notice>Loading run…</Notice>;
  const r = run.data;
  return (
    <section className="panel">
      <div className="section-title">
        <h2>{r.name}</h2>
        <Status status={r.status} />
      </div>
      <dl className="metadata">
        <div>
          <dt>Run ID</dt>
          <dd>{r.id}</dd>
        </div>
        <div>
          <dt>Started</dt>
          <dd>
            {r.started_at
              ? new Date(r.started_at).toLocaleString()
              : "Waiting to start"}
          </dd>
        </div>
        <div>
          <dt>Elapsed</dt>
          <dd>{format(r.elapsed_seconds)} seconds</dd>
        </div>
        <div>
          <dt>Trials</dt>
          <dd>
            {r.progress.completed_trials ?? "Unmeasured"} /{" "}
            {r.progress.total_trials}
          </dd>
        </div>
        <div>
          <dt>Seed / engine</dt>
          <dd>
            {r.seed} / {r.engine_version}
          </dd>
        </div>
      </dl>
      {["queued", "running"].includes(r.status) && (
        <>
          <progress
            aria-label="Run progress"
            {...(r.progress.percentage === null
              ? {}
              : { value: r.progress.percentage, max: 100 })}
          />
          <p className="hint">
            {r.progress.percentage === null
              ? "Execution in progress; exact progress is not available."
              : `${r.progress.percentage}% complete`}
          </p>
          <button
            className="secondary"
            onClick={() => cancel.mutate()}
            disabled={cancel.isPending}
          >
            Cancel run
          </button>
        </>
      )}
      {r.error && <Notice error={r.error} />}
      {cancel.error && <Notice error={cancel.error} />}
    </section>
  );
}
