import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import {
  DataTable,
  Notice,
  PageTitle,
  RunList,
  RunMonitor,
} from "../components/Common";
import { human } from "../components/SchemaForm";
import { selectChartAxes } from "../components/chartAxes";
const Chart = lazy(() => import("../components/Chart"));
const tabs = [
  "Summary",
  "Governance",
  "Adversarial",
  "Economics",
  "Timeline",
  "Raw",
];
export default function Results() {
  const { id } = useParams();
  const [tab, setTab] = useState("Summary");
  const [table, setTable] = useState("summary");
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("");
  const [descending, setDescending] = useState(false);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [kind, setKind] = useState("line");
  const [x, setX] = useState("");
  const [y, setY] = useState("");
  const [series, setSeries] = useState("trial");
  const [outcome, setOutcome] = useState("");
  const list = useQuery({
    queryKey: ["runs"],
    queryFn: api.runs,
    enabled: !id,
  });
  const run = useQuery({
    queryKey: ["run", id],
    queryFn: () => api.run(id!),
    enabled: !!id,
    refetchInterval: (q) =>
      ["queued", "running"].includes(q.state.data?.status ?? "") ? 1500 : false,
  });
  const ready = run.data?.status === "completed";
  const chartTable = ["Economics", "Timeline"].includes(tab)
    ? "timeseries"
    : table === "aggregate"
      ? "aggregate"
      : "summary";
  const rawQuery = new URLSearchParams({
    table,
    offset: String(offset),
    limit: "50",
    search,
    sort,
    descending: String(descending),
  }).toString();
  const data = useQuery({
    queryKey: ["results", id, rawQuery],
    queryFn: () => api.results(id!, rawQuery),
    enabled: !!id && ready,
  });
  const chartQuery = new URLSearchParams({
    table: chartTable,
    limit: "2000",
    ...filters,
  }).toString();
  const chart = useQuery({
    queryKey: ["charts", id, chartQuery],
    queryFn: () => api.charts(id!, chartQuery),
    enabled: !!id && ready,
  });
  const discovery = useQuery({
    queryKey: ["chart-cells", id, chartTable],
    queryFn: () => api.facets(id!, chartTable),
    enabled: !!id && ready,
  });
  const rows = chart.data?.items ?? [];
  const groups = [
    "grid_id",
    "voting_model",
    "variant",
    ...(chartTable === "aggregate" ? ["metric"] : []),
  ];
  const choices = Object.fromEntries(
    groups.map((g) => [
      g,
      discovery.data?.facets?.[g] ?? [
        ...new Set(rows.filter((r) => r[g] != null).map((r) => String(r[g]))),
      ],
    ]),
  );
  useEffect(() => {
    if (!rows.length) return;
    const next = { ...filters };
    let changed = false;
    for (const key of groups) {
      if (!next[key] && choices[key].length) {
        next[key] = choices[key][0];
        changed = true;
      }
    }
    if (changed) setFilters(next);
  }, [chart.data, discovery.data]); // A chart always represents a single experimental cell.
  const outcomeChoices = [
    ...new Set(
      rows.filter((r) => r.metric != null).map((r) => String(r.metric)),
    ),
  ];
  const selectedOutcome = outcomeChoices.includes(outcome)
    ? outcome
    : (outcomeChoices[0] ?? "");
  const selectedRows = useMemo(
    () =>
      rows.filter(
        (r) =>
          groups.every(
            (g) => !filters[g] || r[g] == null || String(r[g]) === filters[g],
          ) &&
          (!selectedOutcome || String(r.metric) === selectedOutcome),
      ),
    [chart.data, filters, selectedOutcome],
  );
  const numeric = (chart.data?.columns ?? Object.keys(rows[0] ?? {})).filter(
    (k) => selectedRows.some((r) => typeof r[k] === "number"),
  );
  const preferred = numeric.filter((k) =>
    chartTable === "aggregate"
      ? true
      : tab === "Governance"
        ? /gini|turnout|vot|concentration|participation|weight|effective/i.test(
            k,
          )
        : tab === "Adversarial"
          ? /capture|attack|defense|cost|false|power_share/i.test(k)
          : tab === "Economics"
            ? /cash|revenue|expense|runway|debt|fund|contribution|wage|financial/i.test(
                k,
              )
            : true,
  );
  const { x: effectiveX, y: effectiveY } = selectChartAxes(
    chart.data?.columns ?? [],
    numeric,
    preferred,
    chartTable,
    tab,
    x,
    y,
  );
  useEffect(() => {
    setOffset(0);
    setFilters({});
    setX("");
    setY("");
  }, [id, chartTable]);
  if (!id)
    return (
      <>
        <PageTitle title="Results Explorer" eyebrow="Inspect engine outputs">
          <Link className="button secondary" to="/history">
            Find older runs in history
          </Link>
        </PageTitle>
        {list.error && <Notice error={list.error} />}
        <section className="panel">
          <h2>Select a completed run</h2>
          <RunList
            runs={
              list.data?.items.filter((r) => r.status === "completed") ?? []
            }
          />
        </section>
      </>
    );
  return (
    <>
      <PageTitle
        title="Results Explorer"
        eyebrow="Reproducible simulation outputs"
      >
        <Link className="button secondary" to="/compare">
          Compare runs
        </Link>
        {ready && (
          <a className="button" href={api.export(id, "zip")}>
            Export run ↓
          </a>
        )}
      </PageTitle>
      <RunMonitor id={id} />
      {run.error && <Notice error={run.error} />}
      {ready && (
        <>
          <nav className="tabs" aria-label="Result categories">
            {tabs.map((t) => (
              <button
                className={tab === t ? "active" : ""}
                key={t}
                onClick={() => {
                  setTab(t);
                  setTable(
                    t === "Timeline"
                      ? "events"
                      : t === "Economics"
                        ? "timeseries"
                        : "summary",
                  );
                  setOffset(0);
                  setSearch("");
                }}
              >
                {t}
              </button>
            ))}
          </nav>
          {tab === "Summary" && (
            <details className="panel">
              <summary>Configuration snapshot</summary>
              <pre>{JSON.stringify(run.data?.configuration, null, 2)}</pre>
            </details>
          )}
          {tab !== "Raw" && (
            <section className="panel">
              <div className="section-title">
                <h2>
                  {tab === "Timeline"
                    ? "Multi-period observations"
                    : `${tab} metrics`}
                </h2>
                <span className="category">Actual engine outputs</span>
              </div>
              {(chart.error || discovery.error) && (
                <Notice error={chart.error ?? discovery.error} />
              )}
              {discovery.data?.truncated && (
                <Notice>
                  Facet choices are bounded to 500 values per dimension. Export
                  the full run for broader analysis.
                </Notice>
              )}
              {chart.isPending && <Notice>Loading bounded chart data…</Notice>}
              <div className="toolbar">
                {groups.map((g) => (
                  <label className="field" key={g}>
                    {human(g)}
                    <select
                      aria-label={human(g)}
                      value={filters[g] ?? ""}
                      onChange={(e) =>
                        setFilters({ ...filters, [g]: e.target.value })
                      }
                    >
                      <option value="">
                        {choices[g].length ? "Select cell…" : "Not present"}
                      </option>
                      {[
                        ...new Set([
                          ...(filters[g] ? [filters[g]] : []),
                          ...choices[g],
                        ]),
                      ].map((v) => (
                        <option key={v}>{v}</option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              {outcomeChoices.length > 0 && chartTable !== "aggregate" && (
                <label className="field">
                  Outcome measure
                  <select
                    value={selectedOutcome}
                    onChange={(e) => setOutcome(e.target.value)}
                  >
                    {outcomeChoices.map((m) => (
                      <option key={m} value={m}>
                        {human(m)}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <p className="hint">
                Each chart is restricted to one grid cell, voting model, and
                variant. Trial lines remain separate. Values retain engine units
                and proportions.
              </p>
              {effectiveY && selectedRows.length ? (
                <>
                  <div className="toolbar">
                    <label className="field">
                      Chart type
                      <select
                        value={kind}
                        onChange={(e) => setKind(e.target.value)}
                      >
                        {[
                          "line",
                          "bar",
                          "histogram",
                          "scatter",
                          "box",
                          "heatmap",
                        ].map((k) => (
                          <option key={k}>{k}</option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      X axis
                      <select
                        value={effectiveX}
                        onChange={(e) => setX(e.target.value)}
                      >
                        {(chart.data?.columns ?? []).map((k) => (
                          <option key={k} value={k}>
                            {human(k)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      Metric / Y axis
                      <select
                        value={effectiveY}
                        onChange={(e) => setY(e.target.value)}
                      >
                        {preferred.map((k) => (
                          <option key={k} value={k}>
                            {human(k)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      Series
                      <select
                        value={series}
                        onChange={(e) => setSeries(e.target.value)}
                      >
                        <option value="">One series</option>
                        {["trial", "trial_id"]
                          .filter((k) =>
                            (chart.data?.columns ?? []).includes(k),
                          )
                          .map((k) => (
                            <option key={k} value={k}>
                              {human(k)}
                            </option>
                          ))}
                      </select>
                    </label>
                  </div>
                  <Suspense
                    fallback={
                      <Notice>Loading interactive plotting library…</Notice>
                    }
                  >
                    <Chart
                      rows={selectedRows}
                      kind={kind}
                      x={effectiveX}
                      y={effectiveY}
                      category={
                        series && selectedRows.some((r) => r[series] != null)
                          ? series
                          : undefined
                      }
                    />
                  </Suspense>
                  {chart.data && chart.data.total > rows.length && (
                    <Notice>
                      Chart displays a bounded subset of{" "}
                      {rows.length.toLocaleString()} of{" "}
                      {chart.data.total.toLocaleString()} rows. Export the full
                      table for analysis.
                    </Notice>
                  )}
                </>
              ) : (
                !chart.isPending && (
                  <Notice>
                    The engine did not produce plottable {tab.toLowerCase()}{" "}
                    metrics for this selection.
                  </Notice>
                )
              )}
            </section>
          )}
          <section className="panel">
            <div className="section-title">
              <h2>{tab === "Timeline" ? "Event timeline" : "Result data"}</h2>
              <div className="actions">
                <a className="text-link" href={api.export(id, "csv", table)}>
                  CSV ↓
                </a>
                <a className="text-link" href={api.export(id, "json", table)}>
                  JSON ↓
                </a>
              </div>
            </div>
            <div className="toolbar">
              <label className="field">
                Table
                <select
                  value={table}
                  onChange={(e) => {
                    setTable(e.target.value);
                    setOffset(0);
                  }}
                >
                  {[
                    "summary",
                    "elections",
                    "timeseries",
                    "events",
                    "aggregate",
                    "defense_effectiveness",
                  ].map((t) => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                Search data
                <input
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setOffset(0);
                  }}
                  placeholder="Filter table rows…"
                />
              </label>
            </div>
            {data.error && <Notice error={data.error} />}
            {data.isPending ? (
              <Notice>Loading result rows…</Notice>
            ) : (
              <DataTable
                rows={data.data?.items ?? []}
                columns={data.data?.columns}
                onSort={(key) => {
                  if (sort === key) setDescending(!descending);
                  else {
                    setSort(key);
                    setDescending(false);
                  }
                }}
              />
            )}
            <div className="pagination">
              <span>
                {data.data?.total ?? 0} rows · showing{" "}
                {data.data?.items.length ? offset + 1 : 0}–
                {offset + (data.data?.items.length ?? 0)}
              </span>
              <button
                className="secondary"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 50))}
              >
                Previous
              </button>
              <button
                className="secondary"
                disabled={offset + 50 >= (data.data?.total ?? 0)}
                onClick={() => setOffset(offset + 50)}
              >
                Next
              </button>
            </div>
          </section>
        </>
      )}
    </>
  );
}
