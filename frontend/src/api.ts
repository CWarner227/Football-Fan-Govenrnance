import type {
  Capabilities,
  Comparison,
  Config,
  Model,
  Page,
  Row,
  Run,
  SavedConfig,
  Scenario,
} from "./types";
const prefix = "/api/v1";
export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(prefix + path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail ?? body.error ?? response.statusText;
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail, null, 2),
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
const post = <T>(path: string, data: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(data) });
export const api = {
  profiles: () =>
    request<
      Page<{
        id: string;
        name: string;
        description: string;
        configuration: Config;
      }>
    >("/profiles"),
  overview: () =>
    request<{
      completed_simulations: number;
      total_experiments: number;
      total_runs: number;
      active_runs: number;
      last_execution_seconds: number | null;
      recent_runs: Run[];
    }>("/overview"),
  capabilities: () => request<Capabilities>("/capabilities"),
  models: () => request<{ models: Model[] }>("/models"),
  scenarios: () => request<Page<Scenario>>("/scenarios"),
  configurations: () => request<Page<SavedConfig>>("/configurations"),
  configurationsPage: (offset: number, search: string) =>
    request<Page<SavedConfig>>(
      "/configurations?" +
        new URLSearchParams({
          offset: String(offset),
          limit: "50",
          search,
        }).toString(),
    ),
  save: (name: string, description: string, configuration: Config) =>
    post<SavedConfig>("/configurations/save", {
      name,
      description,
      configuration,
    }),
  validate: (configuration: Config) =>
    post<{ valid: boolean; configuration: Config; workload: Config }>(
      "/configurations/validate",
      { configuration },
    ),
  runs: () => request<Page<Run>>("/runs"),
  runsPage: (offset: number, search: string, status: string) =>
    request<Page<Run>>(
      "/runs?" +
        new URLSearchParams({
          offset: String(offset),
          limit: "50",
          search,
          status: status === "all" ? "" : status,
        }).toString(),
    ),
  run: (id: string) => request<Run>(`/runs/${id}`),
  submit: (
    name: string,
    description: string,
    kind: Run["kind"],
    configuration: Config,
  ) => post<Run>("/runs", { name, description, kind, configuration }),
  cancel: (id: string) => post<Run>(`/runs/${id}/cancel`, {}),
  remove: (id: string) => request<void>(`/runs/${id}`, { method: "DELETE" }),
  facets: (id: string, table: string) =>
    request<{ facets: Record<string, string[]>; truncated: boolean }>(
      `/runs/${id}/facets?table=${table}`,
    ),
  results: (id: string, query: string) =>
    request<Page<Row>>(`/runs/${id}/results?${query}`),
  charts: (id: string, query: string) =>
    request<Page<Row>>(`/runs/${id}/charts?${query}`),
  compare: (run_ids: string[]) => post<Comparison>("/comparisons", { run_ids }),
  export: (id: string, format: string, table = "summary") =>
    `${prefix}/runs/${id}/export?format=${format}&table=${table}`,
};
