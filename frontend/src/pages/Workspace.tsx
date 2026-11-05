import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  FlaskConical,
  Layers3,
  ShieldCheck,
  Swords,
  Vote,
  Clock3,
} from "lucide-react";
import { api } from "../api";
import ComparisonChart from "../components/ComparisonChart";
import {
  PagedDataTable,
  Notice,
  PageTitle,
  RunList,
  Status,
  SelectorPagination,
  ExecutionHistory,
} from "../components/Common";
import type { Scenario } from "../types";
export function Overview() {
  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: api.overview,
    refetchInterval: 5000,
  });
  const runs = useQuery({
    queryKey: ["runs"],
    queryFn: api.runs,
    refetchInterval: 5000,
  });
  const scenarios = useQuery({
    queryKey: ["scenarios"],
    queryFn: api.scenarios,
  });
  const models = useQuery({ queryKey: ["models"], queryFn: api.models });
  const cards = [
    {
      name: "Completed simulations",
      value: overview.data?.completed_simulations,
      icon: FlaskConical,
    },
    {
      name: "Experiments",
      value: overview.data?.total_experiments,
      icon: Layers3,
    },
    {
      name: "Available scenarios",
      value: scenarios.data?.total,
      icon: Layers3,
    },
    {
      name: "Voting models",
      value: models.data?.models.filter((x) => x.category === "voting").length,
      icon: Vote,
    },
    {
      name: "Attack strategies",
      value: models.data?.models.filter((x) => x.category === "attack").length,
      icon: Swords,
    },
    {
      name: "Defensive policies",
      value: models.data?.models.filter((x) => x.category === "defense").length,
      icon: ShieldCheck,
    },
  ];
  return (
    <>
      <PageTitle
        title="Research overview"
        eyebrow="Football governance laboratory"
      >
        <Link className="button" to="/builder">
          New simulation <ArrowUpRight size={16} />
        </Link>
      </PageTitle>
      <p className="lead">
        Explore the trade-offs between democratic participation, resilient
        governance, and sustainable club funding.
      </p>
      {(runs.error || scenarios.error || models.error) && (
        <Notice error={runs.error ?? scenarios.error ?? models.error} />
      )}
      <div className="stat-grid">
        {cards.map(({ name, value, icon: Icon }) => (
          <div className="stat-card" key={name}>
            <div className="stat-top">
              <span>{name}</span>
              <Icon size={18} />
            </div>
            <strong>{value ?? "—"}</strong>
            <small>From your local research workspace</small>
          </div>
        ))}
      </div>
      <div className="overview-grid">
        <section className="panel">
          <div className="section-title">
            <h2>Recent activity</h2>
            <Link className="text-link" to="/history">
              View all runs →
            </Link>
          </div>
          {runs.isPending ? (
            <Notice>Loading runs…</Notice>
          ) : (
            <RunList
              runs={
                overview.data?.recent_runs ?? runs.data?.items.slice(0, 6) ?? []
              }
            />
          )}
        </section>
        <section className="panel">
          <h2>Research workflow</h2>
          <div className="workflow-step">
            <span>01</span>
            <div>
              <h3>Choose your assumptions</h3>
              <p>
                Start with a scenario and configure population, voting, and
                economics.
              </p>
              <Link to="/scenarios" className="text-link">
                Browse scenarios →
              </Link>
            </div>
          </div>
          <div className="workflow-step">
            <span>02</span>
            <div>
              <h3>Run reproducible experiments</h3>
              <p>
                Use fixed seeds and Monte Carlo trials to explore variation.
              </p>
              <Link to="/experiments" className="text-link">
                Create experiment →
              </Link>
            </div>
          </div>
          <div className="workflow-step">
            <span>03</span>
            <div>
              <h3>Inspect and compare</h3>
              <p>Keep grid cells and outcome definitions separate.</p>
              <Link to="/compare" className="text-link">
                Compare runs →
              </Link>
            </div>
          </div>
        </section>
      </div>
      <ExecutionHistory runs={overview.data?.recent_runs ?? []} />
      <section className="panel note">
        <Clock3 size={20} />
        <div>
          <strong>Last completed execution</strong>
          <p>
            {runs.data?.items.find(
              (x) => x.status === "completed" && x.completed_at,
            )?.completed_at
              ? new Date(
                  runs.data.items.find(
                    (x) => x.status === "completed" && x.completed_at,
                  )!.completed_at!,
                ).toLocaleString()
              : "No completed executions yet."}
            {overview.data?.last_execution_seconds != null &&
              ` · ${overview.data.last_execution_seconds} seconds`}
          </p>
          <small>
            All results are produced by the Python simulation engine. Open a
            completed run for charts; incompatible experiments are never pooled
            on this overview.
          </small>
        </div>
      </section>
    </>
  );
}
export function Scenarios() {
  const query = useQuery({ queryKey: ["scenarios"], queryFn: api.scenarios });
  const [search, setSearch] = useState("");
  const [view, setView] = useState<Scenario | null>(null);
  const navigate = useNavigate();
  const run = useMutation({
    mutationFn: (s: Scenario) =>
      api.submit(s.name, s.description, "simulation", s.configuration),
    onSuccess: (r) => navigate(`/results/${r.id}`),
  });
  return (
    <>
      <PageTitle title="Scenario library" eyebrow="Engine scenario catalog" />
      <p className="lead">
        Research starting points loaded from the existing YAML scenario library.
      </p>
      <label className="search field">
        Search scenarios
        <input
          placeholder="Search by name, category, attack…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      {query.error && <Notice error={query.error} />}
      {run.error && <Notice error={run.error} />}
      {query.isPending && <Notice>Loading scenarios…</Notice>}
      <div className="scenario-grid">
        {query.data?.items
          .filter((s) =>
            `${s.name} ${s.description} ${s.category} ${s.attacks}`
              .toLowerCase()
              .includes(search.toLowerCase()),
          )
          .map((s) => (
            <article className="panel scenario" key={s.id}>
              <span className="category">{s.category}</span>
              <h2>{s.name.replace(/_/g, " ")}</h2>
              <p>
                {s.description ||
                  "Configure this engine scenario to explore governance outcomes."}
              </p>
              <dl className="scenario-details">
                <div>
                  <dt>Population</dt>
                  <dd>{s.population_size.toLocaleString()}</dd>
                </div>
                <div>
                  <dt>Duration</dt>
                  <dd>{s.duration_months} months</dd>
                </div>
                <div>
                  <dt>Voting</dt>
                  <dd>{s.voting_models.join(", ") || "Engine default"}</dd>
                </div>
                <div>
                  <dt>Attacks</dt>
                  <dd>{s.attacks.join(", ") || "None"}</dd>
                </div>
                <div>
                  <dt>Defenses</dt>
                  <dd>{s.defenses.join(", ") || "None"}</dd>
                </div>
              </dl>
              <div className="actions">
                <button
                  onClick={() =>
                    navigate("/builder", {
                      state: { configuration: s.configuration, name: s.name },
                    })
                  }
                >
                  Configure →
                </button>
                <button
                  className="secondary"
                  disabled={run.isPending}
                  onClick={() => run.mutate(s)}
                >
                  Run now
                </button>
                <button className="subtle" onClick={() => setView(s)}>
                  View JSON
                </button>
                <button
                  className="subtle"
                  onClick={() =>
                    navigate("/builder", {
                      state: {
                        configuration: s.configuration,
                        name: `${s.name} copy`,
                      },
                    })
                  }
                >
                  Duplicate
                </button>
              </div>
            </article>
          ))}
      </div>
      {query.data &&
        !query.data.items.some((s) =>
          `${s.name} ${s.description} ${s.category} ${s.attacks}`
            .toLowerCase()
            .includes(search.toLowerCase()),
        ) && <Notice>No scenarios match your search.</Notice>}
      {view && (
        <div className="modal-backdrop">
          <section
            className="panel modal"
            role="dialog"
            aria-modal="true"
            aria-label="Scenario configuration"
          >
            <div className="section-title">
              <h2>{view.name}</h2>
              <button className="secondary" onClick={() => setView(null)}>
                Close
              </button>
            </div>
            <pre>{JSON.stringify(view.configuration, null, 2)}</pre>
          </section>
        </div>
      )}
    </>
  );
}
export function History() {
  const client = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [offset, setOffset] = useState(0);
  const query = useQuery({
    queryKey: ["runs", offset, search, status],
    queryFn: () => api.runsPage(offset, search, status),
    refetchInterval: 4000,
  });
  const [confirm, setConfirm] = useState("");
  const action = useMutation({
    mutationFn: async ({ id, type }: { id: string; type: string }) => {
      const r = query.data!.items.find((x) => x.id === id)!;
      if (type === "delete") {
        await api.remove(id);
        setConfirm("");
      } else {
        const next = await api.submit(
          `${r.name} rerun`,
          r.description,
          r.kind,
          r.configuration,
        );
        navigate(`/results/${next.id}`);
      }
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ["runs"] }),
  });
  const rows =
    query.data?.items.filter(
      (r) =>
        `${r.name} ${r.id}`.toLowerCase().includes(search.toLowerCase()) &&
        (status === "all" || r.status === status),
    ) ?? [];
  return (
    <>
      <PageTitle title="Run history" eyebrow="Persisted local executions">
        <Link className="button secondary" to="/compare">
          Compare completed runs
        </Link>
      </PageTitle>
      <div className="toolbar">
        <label className="field">
          Search runs
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
            placeholder="Run name or ID"
          />
        </label>
        <label className="field">
          Status
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setOffset(0);
            }}
          >
            {[
              "all",
              "queued",
              "running",
              "completed",
              "failed",
              "cancelled",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
      </div>
      {query.error && <Notice error={query.error} />}
      {action.error && <Notice error={action.error} />}
      {query.isPending ? (
        <Notice>Loading history…</Notice>
      ) : (
        <section className="panel">
          {rows.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Status</th>
                    <th>Seed</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <Link className="text-link" to={`/results/${r.id}`}>
                          {r.name}
                        </Link>
                        <small className="run-id">
                          {r.kind} · {r.id.slice(0, 8)}
                        </small>
                      </td>
                      <td>
                        <Status status={r.status} />
                      </td>
                      <td>{r.seed}</td>
                      <td>{new Date(r.created_at).toLocaleString()}</td>
                      <td>
                        <div className="actions">
                          <button
                            className="subtle"
                            onClick={() =>
                              navigate(
                                r.kind === "experiment"
                                  ? "/experiments"
                                  : "/builder",
                                {
                                  state: {
                                    configuration: r.configuration,
                                    name: `${r.name} copy`,
                                  },
                                },
                              )
                            }
                          >
                            Duplicate
                          </button>
                          <button
                            className="subtle"
                            disabled={action.isPending}
                            onClick={() =>
                              action.mutate({ id: r.id, type: "rerun" })
                            }
                          >
                            Rerun
                          </button>
                          {r.status === "completed" && (
                            <a
                              className="text-link"
                              href={api.export(r.id, "zip")}
                            >
                              Export
                            </a>
                          )}
                          {confirm === r.id ? (
                            <>
                              <button
                                className="danger secondary"
                                disabled={action.isPending}
                                onClick={() =>
                                  action.mutate({ id: r.id, type: "delete" })
                                }
                              >
                                Confirm delete
                              </button>
                              <button
                                className="subtle"
                                onClick={() => setConfirm("")}
                              >
                                Keep run
                              </button>
                            </>
                          ) : (
                            <button
                              className="subtle danger"
                              disabled={["running", "queued"].includes(
                                r.status,
                              )}
                              onClick={() => setConfirm(r.id)}
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Notice>No runs match your filters.</Notice>
          )}
          <div className="pagination">
            <span>{query.data?.total ?? 0} runs</span>
            <button
              className="secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - 50))}
            >
              Previous
            </button>
            <button
              className="secondary"
              disabled={offset + 50 >= (query.data?.total ?? 0)}
              onClick={() => setOffset(offset + 50)}
            >
              Next
            </button>
          </div>
        </section>
      )}
    </>
  );
}
export function Compare() {
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const runs = useQuery({
    queryKey: ["runs", "comparison", offset, search],
    queryFn: () => api.runsPage(offset, search, "completed"),
  });
  const [selected, setSelected] = useState<string[]>([]);
  const comparison = useMutation({ mutationFn: () => api.compare(selected) });
  return (
    <>
      <PageTitle title="Compare experiments" eyebrow="Controlled comparisons" />
      <p className="lead">
        Select completed runs. The backend checks assumptions and computes
        paired differences where matched trials are available.
      </p>
      <section className="panel">
        <h2>Select runs</h2>
        <label className="field">
          Search completed runs
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
            placeholder="Run name or description"
          />
        </label>
        <p className="hint">
          {selected.length} of 4 selected. Selections are retained across pages.
        </p>
        {runs.error && <Notice error={runs.error} />}
        {runs.data?.items
          .filter((r) => r.status === "completed")
          .map((r) => (
            <label className="check-row" key={r.id}>
              <input
                type="checkbox"
                checked={selected.includes(r.id)}
                disabled={!selected.includes(r.id) && selected.length >= 4}
                onChange={(e) =>
                  setSelected(
                    e.target.checked
                      ? [...selected, r.id]
                      : selected.filter((x) => x !== r.id),
                  )
                }
              />
              {r.name}
              <small>
                {r.id.slice(0, 8)} · seed {r.seed}
              </small>
            </label>
          ))}
        {runs.data &&
          !runs.data.items.some((r) => r.status === "completed") && (
            <Notice>Complete at least two runs to compare results.</Notice>
          )}
        <SelectorPagination
          offset={offset}
          total={runs.data?.total ?? 0}
          onPage={setOffset}
          label="comparison runs"
        />
        {selected.length > 0 && (
          <button
            type="button"
            className="subtle"
            onClick={() => setSelected([])}
          >
            Clear selection
          </button>
        )}
        <button
          disabled={selected.length < 2 || comparison.isPending}
          onClick={() => comparison.mutate()}
        >
          {comparison.isPending ? "Comparing…" : "Compare selected runs"}
        </button>
      </section>
      {comparison.error && <Notice error={comparison.error} />}
      {comparison.data && (
        <>
          {comparison.data.warnings.map((w) => (
            <Notice key={w}>{w}</Notice>
          ))}
          <section className="panel">
            <h2>Configuration differences</h2>
            <PagedDataTable
              label="configuration differences"
              rows={comparison.data.differences.map((d) => ({
                parameter: d.path,
                ...Object.fromEntries(
                  Object.entries(d.values).map(([id, value]) => [
                    comparison.data!.runs.find((x) => x.run.id === id)?.run
                      .name +
                      " · " +
                      id.slice(0, 6),
                    value,
                  ]),
                ),
              }))}
            />
          </section>
          <div className="compare-grid">
            {comparison.data.runs.map((x) => (
              <section className="panel" key={x.run.id}>
                <h2>{x.run.name}</h2>
                <PagedDataTable
                  label={`${x.run.name} outcomes`}
                  rows={x.summary.items}
                  columns={[
                    "grid_id",
                    "trial",
                    "variant",
                    "voting_model",
                    "capture_success",
                    "turnout",
                    "gini",
                    "cash_balance",
                  ].filter((c) => x.summary.columns?.includes(c))}
                />
                <Link className="text-link" to={`/results/${x.run.id}`}>
                  Inspect charts →
                </Link>
              </section>
            ))}
          </div>
          <ComparisonChart comparison={comparison.data} />
          <section className="panel">
            <h2>Matched-trial differences</h2>
            <PagedDataTable
              label="matched differences"
              rows={comparison.data.paired_differences}
            />
          </section>
          <p className="hint">
            Observed differences do not establish causation without controlled
            assumptions.
          </p>
        </>
      )}
    </>
  );
}
export function Integrations() {
  const q = useQuery({ queryKey: ["capabilities"], queryFn: api.capabilities });
  return (
    <>
      <PageTitle
        title="Integrations"
        eyebrow="Extensible research infrastructure"
      />
      <p className="lead">
        Optional modules are discovered through the backend capability registry.
      </p>
      {q.error && <Notice error={q.error} />}
      <div className="scenario-grid">
        {q.data?.integrations.map((i) => (
          <section className="panel" key={i.id}>
            <div className="section-title">
              <h2>{i.name}</h2>
              <Status status={i.enabled ? "completed" : "planned"} />
            </div>
            <p>
              {i.status ??
                (i.enabled ? "Installed" : "Not installed · planned")}
            </p>
            <ul>
              {i.capabilities.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      {q.data && !q.data.integrations.length && (
        <Notice>
          No integration modules are installed. Blockchain adapters can register
          additional capabilities here.
        </Notice>
      )}
    </>
  );
}
export function Settings() {
  const q = useQuery({ queryKey: ["capabilities"], queryFn: api.capabilities });
  const [theme, setTheme] = useState(localStorage.getItem("theme") ?? "light");
  return (
    <>
      <PageTitle title="Settings" eyebrow="Local workspace preferences" />
      <section className="panel">
        <h2>Appearance</h2>
        <label className="field">
          Theme
          <select
            value={theme}
            onChange={(e) => {
              setTheme(e.target.value);
              document.documentElement.dataset.theme = e.target.value;
              localStorage.setItem("theme", e.target.value);
            }}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </label>
        <p className="hint">Saved in this browser.</p>
      </section>
      <section className="panel">
        <h2>Research API</h2>
        <p>
          API prefix: <code>/api/v1</code>
        </p>
        <p>Engine version: {q.data?.version ?? "Connecting…"}</p>
        <a
          className="text-link"
          href="http://127.0.0.1:8000/docs"
          target="_blank"
          rel="noreferrer"
        >
          Open local API documentation ↗
        </a>
        {q.error && <Notice error={q.error} />}
        <h3>Resource limits</h3>
        <pre>{JSON.stringify(q.data?.limits ?? {}, null, 2)}</pre>
      </section>
      <section className="panel">
        <h2>Research concepts</h2>
        <dl className="glossary">
          <dt>Voting concentration</dt>
          <dd>
            How unevenly voting power is distributed; a higher Gini indicates
            greater inequality.
          </dd>
          <dt>Effective number of voters</dt>
          <dd>
            The number of equally weighted voters with equivalent concentration.
          </dd>
          <dt>Capture probability</dt>
          <dd>
            Frequency of attacker capture across simulated trials, under the
            stated configuration.
          </dd>
          <dt>Quorum</dt>
          <dd>Minimum participation required for an election to be valid.</dd>
          <dt>Waiting period</dt>
          <dd>Minimum membership age before a supporter becomes eligible.</dd>
          <dt>Sybil attack</dt>
          <dd>One attacker creates multiple identities to gain influence.</dd>
          <dt>Monte Carlo trials</dt>
          <dd>
            Repeated stochastic executions used to study outcome variation.
          </dd>
          <dt>Financial runway</dt>
          <dd>
            Time a club can continue operating under modeled funding and
            expenditure assumptions.
          </dd>
        </dl>
      </section>
    </>
  );
}
