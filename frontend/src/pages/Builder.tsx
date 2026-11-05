import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { parse, stringify } from "yaml";
import { api } from "../api";
import type { Config } from "../types";
import { PageTitle, Notice, SelectorPagination } from "../components/Common";
import { SchemaField } from "../components/SchemaForm";
const identity = z.object({
  name: z.string().trim().min(1, "A run name is required."),
  description: z.string(),
});
export default function Builder({
  experiment = false,
}: {
  experiment?: boolean;
}) {
  const capabilities = useQuery({
    queryKey: ["capabilities"],
    queryFn: api.capabilities,
  });
  const models = useQuery({ queryKey: ["models"], queryFn: api.models });
  const profiles = useQuery({ queryKey: ["profiles"], queryFn: api.profiles });
  const [savedSearch, setSavedSearch] = useState("");
  const [savedOffset, setSavedOffset] = useState(0);
  const saved = useQuery({
    queryKey: ["configurations", savedOffset, savedSearch],
    queryFn: () => api.configurationsPage(savedOffset, savedSearch),
  });
  const location = useLocation();
  const navigate = useNavigate();
  const client = useQueryClient();
  const [config, setConfig] = useState<Config | null>(null);
  const [editor, setEditor] = useState("");
  const [syntax, setSyntax] = useState("json");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [advanced, setAdvanced] = useState(false);
  const form = useForm<{ name: string; description: string }>({
    resolver: zodResolver(identity),
    defaultValues: {
      name: experiment ? "Research experiment" : "Governance simulation",
      description: "",
    },
  });
  useEffect(() => {
    const incoming = location.state as {
      configuration?: Config;
      name?: string;
    } | null;
    if (capabilities.data) {
      setConfig(
        structuredClone(incoming?.configuration ?? capabilities.data.defaults),
      );
      if (incoming?.name) form.setValue("name", incoming.name);
    }
  }, [capabilities.data, location.key, form]);
  const encode = (c: Config) =>
    syntax === "yaml" ? stringify(c) : JSON.stringify(c, null, 2);
  const current = () => {
    if (!document.querySelector("form")?.reportValidity())
      throw new Error(
        "Correct invalid configuration fields before continuing.",
      );
    const c = advanced
      ? syntax === "yaml"
        ? parse(editor)
        : JSON.parse(editor)
      : config;
    if (!c || typeof c !== "object" || Array.isArray(c))
      throw new Error("Configuration must be an object.");
    return c as Config;
  };
  const action = useMutation({
    mutationFn: async (type: string) => {
      setError("");
      setMessage("");
      const c = current();
      const result = await api.validate(c);
      setConfig(result.configuration);
      if (advanced) setEditor(encode(result.configuration));
      if (type === "validate") {
        setMessage(
          `Configuration valid. Workload: ${JSON.stringify(result.workload)}`,
        );
        return;
      }
      const values = form.getValues();
      if (type === "save") {
        await api.save(values.name, values.description, result.configuration);
        void client.invalidateQueries({ queryKey: ["configurations"] });
        setMessage("Configuration saved.");
        return;
      }
      const run = await api.submit(
        values.name,
        values.description,
        experiment ? "experiment" : "simulation",
        result.configuration,
      );
      void client.invalidateQueries({ queryKey: ["runs"] });
      navigate(`/results/${run.id}`);
    },
    onError: (e) => setError(e instanceof Error ? e.message : String(e)),
  });
  if (capabilities.error || models.error)
    return <Notice error={capabilities.error ?? models.error} />;
  if (!config || !capabilities.data || !models.data)
    return <Notice>Loading engine configuration…</Notice>;
  return (
    <>
      <PageTitle
        title={experiment ? "Experiments" : "Simulation Builder"}
        eyebrow={
          experiment
            ? "Controlled Monte Carlo research"
            : "Configure · Validate · Execute"
        }
      />
      <p className="lead">
        {experiment
          ? "Configure trials, seeds and parameter grids in Experiment. Each selected variant and voting model is evaluated by the Python engine."
          : "Build a reproducible governance simulation. Parameters and defaults come directly from the engine."}
      </p>
      <form onSubmit={form.handleSubmit(() => action.mutate("run"))}>
        <section className="panel">
          <h2>Run details</h2>
          <div className="form-grid">
            <label className="field">
              Run name
              <input {...form.register("name")} />
              {form.formState.errors.name && (
                <span role="alert">{form.formState.errors.name.message}</span>
              )}
            </label>
            <label className="field">
              Description
              <input {...form.register("description")} />
            </label>
            <label className="field">
              Saved configurations
              <select
                value=""
                onChange={(e) => {
                  const item = saved.data?.items.find(
                    (x) => x.id === e.target.value,
                  );
                  if (item) {
                    setConfig(structuredClone(item.configuration));
                    form.setValue("name", `${item.name} copy`);
                    if (advanced) setEditor(encode(item.configuration));
                    setMessage("Saved configuration loaded.");
                  }
                }}
              >
                <option value="">Load a configuration…</option>
                {saved.data?.items.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Search saved configurations
              <input
                placeholder="Configuration name or description"
                value={savedSearch}
                onChange={(e) => {
                  setSavedSearch(e.target.value);
                  setSavedOffset(0);
                }}
              />
            </label>
            <div className="wide">
              <SelectorPagination
                offset={savedOffset}
                total={saved.data?.total ?? 0}
                onPage={setSavedOffset}
                label="saved configurations"
              />
              {saved.error && <Notice error={saved.error} />}
            </div>
            <label className="field">
              Population profile
              <select
                aria-label="Population profile"
                value=""
                onChange={(e) => {
                  const profile = profiles.data?.items.find(
                    (p) => p.id === e.target.value,
                  );
                  if (!profile) return;
                  try {
                    const base = current();
                    const next = {
                      ...base,
                      simulation: {
                        ...(base.simulation as Config),
                        population: structuredClone(profile.configuration),
                      },
                    };
                    setConfig(next);
                    if (advanced) setEditor(encode(next));
                    setMessage(`Population profile loaded: ${profile.name}`);
                  } catch (e) {
                    setError(String(e));
                  }
                }}
              >
                <option value="">
                  {profiles.isPending
                    ? "Loading profiles…"
                    : "Load a population profile…"}
                </option>
                {profiles.data?.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <small>
                Replaces supporter population settings while preserving the rest
                of the configuration.
              </small>
              {profiles.error && (
                <span role="alert">{profiles.error.message}</span>
              )}
            </label>
          </div>
        </section>
        <section className="panel">
          <div className="section-title">
            <h2>Engine configuration</h2>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                if (!advanced) setEditor(encode(config));
                else {
                  try {
                    setConfig(current());
                  } catch (e) {
                    setError(String(e));
                    return;
                  }
                }
                setAdvanced(!advanced);
              }}
            >
              {advanced ? "Form view" : "Advanced JSON / YAML"}
            </button>
          </div>
          <p className="hint">
            Use the outer Experiment section for Monte Carlo trials and random
            seed. The nested Phase 2 experiment settings in advanced JSON are
            retained for compatibility and ignored by the Phase 3 runner.
          </p>
          {advanced ? (
            <>
              <div className="actions">
                <label>
                  Format{" "}
                  <select
                    aria-label="Configuration format"
                    value={syntax}
                    onChange={(e) => {
                      try {
                        const c = current();
                        setSyntax(e.target.value);
                        setEditor(
                          e.target.value === "yaml"
                            ? stringify(c)
                            : JSON.stringify(c, null, 2),
                        );
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    <option value="json">JSON</option>
                    <option value="yaml">YAML</option>
                  </select>
                </label>
              </div>
              <label className="field">
                Configuration editor
                <textarea
                  className="code-editor"
                  rows={28}
                  value={editor}
                  onChange={(e) => setEditor(e.target.value)}
                />
              </label>
            </>
          ) : (
            <SchemaField
              name="Configuration"
              schema={capabilities.data.schema}
              root={capabilities.data.schema}
              value={config}
              onChange={(v) => {
                setConfig(v as Config);
                setMessage("");
              }}
              models={models.data.models}
            />
          )}
        </section>
        {error && <Notice error={error} />}
        {message && <Notice>{message}</Notice>}
        <div className="builder-footer">
          <div className="actions">
            <button
              type="button"
              className="secondary"
              disabled={action.isPending}
              onClick={() => action.mutate("validate")}
            >
              Validate configuration
            </button>
            <button
              type="button"
              className="secondary"
              disabled={action.isPending}
              onClick={form.handleSubmit(() => action.mutate("save"))}
            >
              Save configuration
            </button>
            <label className="button secondary">
              Import
              <input
                type="file"
                hidden
                accept=".json,.yaml,.yml"
                onChange={async (e) => {
                  try {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    const c = parse(await file.text());
                    if (!c || typeof c !== "object" || Array.isArray(c))
                      throw new Error(
                        "Import must contain a configuration object.",
                      );
                    setConfig(c);
                    if (advanced) setEditor(encode(c));
                    setMessage("Imported. Validate before execution.");
                  } catch (e) {
                    setError(String(e));
                  }
                  e.target.value = "";
                }}
              />
            </label>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                try {
                  const blob = new Blob([encode(current())], {
                    type: "text/plain",
                  });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `configuration.${syntax}`;
                  a.click();
                  URL.revokeObjectURL(url);
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              Export
            </button>
            <button
              type="button"
              className="subtle"
              onClick={() => {
                const c = structuredClone(capabilities.data!.defaults);
                setConfig(c);
                if (advanced) setEditor(encode(c));
                setMessage("Defaults restored.");
              }}
            >
              Reset defaults
            </button>
            <button
              type="button"
              className="subtle"
              onClick={() => {
                form.setValue("name", `${form.getValues("name")} copy`);
                setMessage("Configuration duplicated. Save to keep this copy.");
              }}
            >
              Duplicate
            </button>
          </div>
          <button type="submit" disabled={action.isPending}>
            {action.isPending
              ? "Processing…"
              : experiment
                ? "Run experiment"
                : "Run simulation"}{" "}
            →
          </button>
        </div>
      </form>
    </>
  );
}
