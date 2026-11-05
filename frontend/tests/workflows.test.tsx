import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
vi.mock("../src/components/Chart", () => ({
  default: () => <div role="img" aria-label="Engine chart" />,
}));
const config = {
  name: "test",
  simulation: { population: { size: 20 }, voting: { strategies: ["equal"] } },
  experiment: { trials: 1, seed: 42 },
  timeline: { duration_months: 1 },
};
const schema = {
  type: "object",
  properties: {
    name: { type: "string" },
    simulation: {
      type: "object",
      properties: {
        population: {
          type: "object",
          properties: {
            size: { type: "integer", title: "Population size", minimum: 1 },
          },
        },
      },
    },
  },
};
const run = {
  id: "run-1",
  name: "Test run",
  kind: "simulation",
  status: "running",
  created_at: new Date().toISOString(),
  started_at: null,
  completed_at: null,
  elapsed_seconds: 0,
  configuration: config,
  seed: 42,
  engine_version: "test",
  error: null,
  progress: { total_trials: 1, completed_trials: null, percentage: null },
};
function mount(path = "/") {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, options?: RequestInit) => {
      const path = url.split("?")[0];
      let data: unknown = {};
      if (path.endsWith("/capabilities"))
        data = {
          version: "test",
          schema,
          defaults: config,
          limits: {},
          integrations: [],
        };
      else if (path.endsWith("/models")) data = { models: [] };
      else if (path.endsWith("/scenarios"))
        data = {
          items: [
            {
              id: "tiny",
              name: "Tiny baseline",
              configuration: config,
              category: "baseline",
              description: "Small controlled population",
              population_size: 20,
              voting_models: ["equal"],
              attacks: [],
              defenses: [],
              duration_months: 1,
            },
          ],
          total: 1,
        };
      else if (path.endsWith("/runs/run-1")) data = run;
      else if (path.endsWith("/runs") && options?.method === "POST") data = run;
      else if (path.endsWith("/validate"))
        data = {
          valid: true,
          configuration: JSON.parse(String(options?.body)).configuration,
          workload: { trials: 1 },
        };
      else data = { items: [], total: 0 };
      return new Response(JSON.stringify(data), {
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());
describe("research workflows", () => {
  it("loads an older saved configuration using bounded pagination", async () => {
    const original = fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, options?: RequestInit) => {
        if (url.includes("/configurations")) {
          const old =
            new URL(url, "http://localhost").searchParams.get("offset") ===
            "50";
          return new Response(
            JSON.stringify({
              items: [
                {
                  id: old ? "old" : "recent",
                  name: old ? "Older configuration" : "Recent configuration",
                  description: "",
                  created_at: "",
                  configuration: {
                    ...config,
                    simulation: {
                      ...config.simulation,
                      population: { size: old ? 7 : 20 },
                    },
                  },
                },
              ],
              total: 51,
            }),
          );
        }
        return original(url, options);
      }),
    );
    mount("/builder");
    await screen.findByLabelText("Population size");
    await userEvent.click(
      screen.getByRole("button", { name: "Next saved configurations" }),
    );
    await screen.findByRole("option", { name: "Older configuration" });
    await userEvent.selectOptions(
      screen.getByLabelText("Saved configurations"),
      "old",
    );
    expect(screen.getByLabelText("Population size")).toHaveValue(7);
  });
  it("keeps completed runs selected across comparison pages", async () => {
    const original = fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, options?: RequestInit) => {
        if (url.includes("/runs?")) {
          const old =
            new URL(url, "http://localhost").searchParams.get("offset") ===
            "50";
          return new Response(
            JSON.stringify({
              items: [
                {
                  ...run,
                  id: old ? "old-run" : "recent-run",
                  name: old ? "Older completed run" : "Recent completed run",
                  status: "completed",
                },
              ],
              total: 51,
            }),
          );
        }
        if (url.endsWith("/comparisons"))
          return new Response(
            JSON.stringify({
              runs: [],
              warnings: [],
              differences: [],
              paired_differences: [],
            }),
          );
        return original(url, options);
      }),
    );
    mount("/compare");
    await userEvent.click(
      await screen.findByRole("checkbox", { name: /Recent completed run/ }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Next comparison runs" }),
    );
    await userEvent.click(
      await screen.findByRole("checkbox", { name: /Older completed run/ }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Compare selected runs" }),
    );
    await screen.findByRole("heading", { name: "Matched-trial differences" });
    const call = vi
      .mocked(fetch)
      .mock.calls.find(([url]) => String(url).endsWith("/comparisons"));
    expect(JSON.parse(String(call?.[1]?.body)).run_ids).toEqual([
      "recent-run",
      "old-run",
    ]);
  });
  it("plots one selected aggregate metric using engine means", async () => {
    const original = fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, options?: RequestInit) => {
        if (url.includes("/runs/run-1/facets"))
          return new Response(
            JSON.stringify({
              facets: {
                grid_id: ["0"],
                voting_model: ["equal"],
                variant: ["control"],
                metric: ["turnout"],
              },
              truncated: false,
            }),
          );
        if (
          url.includes("/runs/run-1/results") ||
          url.includes("/runs/run-1/charts")
        )
          return new Response(
            JSON.stringify({
              items: [
                {
                  metric: "turnout",
                  mean: 0.625,
                  wilson_lower: 0.4,
                  wilson_upper: 0.8,
                  voting_model: "equal",
                  variant: "control",
                  grid_id: "0",
                },
              ],
              total: 1,
              columns: [
                "metric",
                "mean",
                "wilson_lower",
                "wilson_upper",
                "voting_model",
                "variant",
                "grid_id",
              ],
            }),
          );
        if (url.endsWith("/runs/run-1"))
          return new Response(JSON.stringify({ ...run, status: "completed" }));
        return original(url, options);
      }),
    );
    mount("/results/run-1");
    await screen.findByRole("button", { name: "Governance" });
    await userEvent.click(screen.getByRole("button", { name: "Governance" }));
    await userEvent.selectOptions(screen.getByLabelText("Table"), "aggregate");
    expect(await screen.findByLabelText("Metric / Y axis")).toHaveValue("mean");
    expect(screen.getByLabelText("Metric")).toHaveValue("turnout");
  });
  it("loads backend population profiles without changing voting settings", async () => {
    const original = fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, options?: RequestInit) =>
        url.endsWith("/profiles")
          ? Promise.resolve(
              new Response(
                JSON.stringify({
                  items: [
                    {
                      id: "small",
                      name: "Small supporters",
                      description: "",
                      configuration: { size: 7 },
                    },
                  ],
                  total: 1,
                }),
              ),
            )
          : original(url, options),
      ),
    );
    mount("/builder");
    await screen.findByLabelText("Population size");
    await userEvent.selectOptions(
      screen.getByLabelText("Population profile"),
      "small",
    );
    expect(screen.getByLabelText("Population size")).toHaveValue(7);
    await userEvent.click(
      screen.getByRole("button", { name: "Advanced JSON / YAML" }),
    );
    const value = JSON.parse(
      (screen.getByLabelText("Configuration editor") as HTMLTextAreaElement)
        .value,
    );
    expect(value.simulation.voting).toEqual(config.simulation.voting);
  });
  it("navigates to all primary pages through accessible navigation", async () => {
    mount();
    expect(
      await screen.findByRole("heading", { name: "Research overview" }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: "Scenarios" }));
    expect(await screen.findByText("Tiny baseline")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: "Settings" }));
    expect(screen.getByLabelText("Theme")).toBeInTheDocument();
  });
  it("loads scenario configuration and submits actual edited values", async () => {
    mount("/scenarios");
    await userEvent.click(
      await screen.findByRole("button", { name: "Configure →" }),
    );
    const input = await screen.findByLabelText("Population size");
    await userEvent.clear(input);
    await userEvent.type(input, "12");
    await userEvent.click(
      screen.getByRole("button", { name: "Run simulation →" }),
    );
    await screen.findByText(
      "Execution in progress; exact progress is not available.",
    );
    const calls = vi.mocked(fetch).mock.calls;
    const submitted = calls.find(
      ([u, o]) => String(u).endsWith("/runs") && o?.method === "POST",
    );
    expect(
      JSON.parse(String(submitted?.[1]?.body)).configuration.simulation
        .population.size,
    ).toBe(12);
    expect(screen.getByRole("progressbar")).not.toHaveAttribute("value");
  });
  it("shows authoritative backend validation errors", async () => {
    mount("/builder");
    await screen.findByLabelText("Population size");
    const original = fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, options?: RequestInit) =>
        url.endsWith("/validate")
          ? Promise.resolve(
              new Response(
                JSON.stringify({
                  detail: "Population workload exceeds local limit",
                }),
                { status: 422 },
              ),
            )
          : original(url, options),
      ),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Validate configuration" }),
    );
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Population workload exceeds local limit",
      ),
    );
  });
  it("requires a run name before submission", async () => {
    mount("/builder");
    await screen.findByLabelText("Population size");
    await userEvent.clear(screen.getByLabelText("Run name"));
    await userEvent.click(
      screen.getByRole("button", { name: "Run simulation →" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A run name is required.",
    );
  });
  it("renders only real result columns and exposes table exports", async () => {
    const original = fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, options?: RequestInit) => {
        if (
          url.includes("/runs/run-1/results") ||
          url.includes("/runs/run-1/charts")
        )
          return new Response(
            JSON.stringify({
              items: [
                {
                  trial: 1,
                  voting_model: "equal",
                  variant: "control",
                  grid_id: 0,
                  turnout: 0.625,
                },
              ],
              total: 1,
              columns: [
                "trial",
                "voting_model",
                "variant",
                "grid_id",
                "turnout",
              ],
            }),
          );
        if (url.endsWith("/runs/run-1"))
          return new Response(JSON.stringify({ ...run, status: "completed" }));
        return original(url, options);
      }),
    );
    mount("/results/run-1");
    expect(await screen.findByText("0.625")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "CSV ↓" })).toHaveAttribute(
      "href",
      "/api/v1/runs/run-1/export?format=csv&table=summary",
    );
    expect(screen.queryByText("capture probability")).not.toBeInTheDocument();
  });
  it("shows backend comparison warnings and matched differences", async () => {
    const original = fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, options?: RequestInit) => {
        if (url.split("?")[0].endsWith("/runs"))
          return new Response(
            JSON.stringify({
              items: [
                { ...run, status: "completed" },
                {
                  ...run,
                  id: "run-2",
                  name: "Second run",
                  status: "completed",
                },
              ],
              total: 2,
            }),
          );
        if (url.endsWith("/comparisons"))
          return new Response(
            JSON.stringify({
              runs: [],
              warnings: ["Population assumptions differ"],
              differences: [
                {
                  path: "population.size",
                  values: { "run-1": 20, "run-2": 40 },
                },
              ],
              paired_differences: [{ metric: "turnout", difference: 0.125 }],
            }),
          );
        return original(url, options);
      }),
    );
    mount("/compare");
    const boxes = await screen.findAllByRole("checkbox");
    await userEvent.click(boxes[0]);
    await userEvent.click(boxes[1]);
    await userEvent.click(
      screen.getByRole("button", { name: "Compare selected runs" }),
    );
    expect(
      await screen.findByText("Population assumptions differ"),
    ).toBeInTheDocument();
    expect(screen.getByText("population.size")).toBeInTheDocument();
    expect(screen.getByText("0.125")).toBeInTheDocument();
  });
});
