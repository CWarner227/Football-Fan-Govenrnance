import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { useState } from "react";
import { SchemaField } from "../src/components/SchemaForm";
describe("schema fields", () => {
  it("hides only ignored Phase 2 experiment controls and retains the authoritative experiment", () => {
    const root = {
      $defs: {
        SimulationConfig: {
          title: "SimulationConfig",
          type: "object",
          properties: {
            experiment: {
              type: "object",
              properties: {
                trials: { type: "integer", title: "Ignored trials" },
                seed: { type: "integer", title: "Ignored seed" },
              },
            },
            population: {
              type: "object",
              properties: {
                size: { type: "integer", title: "Population size" },
              },
            },
          },
        },
      },
      type: "object",
      properties: {
        simulation: { $ref: "#/$defs/SimulationConfig" },
        experiment: {
          type: "object",
          properties: {
            trials: { type: "integer", title: "Monte Carlo trials" },
            seed: { type: "integer", title: "Monte Carlo seed" },
          },
        },
      },
    };
    render(
      <SchemaField
        name="Configuration"
        schema={root}
        root={root}
        value={{
          simulation: {
            experiment: { trials: 99, seed: 99 },
            population: { size: 20 },
          },
          experiment: { trials: 2, seed: 42 },
        }}
        onChange={() => {}}
        models={[]}
      />,
    );
    expect(screen.queryByLabelText("Ignored trials")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Ignored seed")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Monte Carlo trials")).toHaveValue(2);
    expect(screen.getByLabelText("Monte Carlo seed")).toHaveValue(42);
  });
  it("exposes backend constraints and changes numeric values", async () => {
    const change = vi.fn();
    function Field() {
      const [value, setValue] = useState<unknown>(30);
      return (
        <SchemaField
          name="Population size"
          schema={{ type: "integer", minimum: 1 }}
          root={{}}
          value={value}
          onChange={(v) => {
            change(v);
            setValue(v);
          }}
          models={[]}
        />
      );
    }
    render(<Field />);
    const input = screen.getByLabelText("Population size");
    expect(input).toHaveAttribute("min", "1");
    await userEvent.clear(input);
    await userEvent.type(input, "4");
    expect(change).toHaveBeenCalledWith(4);
  });
  it("shows only selected model parameters and changes model defaults", async () => {
    const change = vi.fn();
    function Field() {
      const [value, setValue] = useState<unknown>({
        name: "equal",
        parameters: {},
      });
      return (
        <SchemaField
          name="Voting model"
          schema={{ $ref: "#/$defs/ModelSpec" }}
          root={{ $defs: { ModelSpec: { type: "object" } } }}
          value={value}
          category="voting"
          onChange={(v) => {
            change(v);
            setValue(v);
          }}
          models={[
            {
              id: "equal",
              name: "Equal",
              category: "voting",
              schema: { type: "object", properties: {} },
              defaults: {},
            },
            {
              id: "capped",
              name: "Capped",
              category: "voting",
              schema: {
                type: "object",
                properties: { cap: { type: "number" } },
              },
              defaults: { cap: 5 },
            },
          ]}
        />
      );
    }
    render(<Field />);
    expect(screen.queryByLabelText("Cap")).not.toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText("Voting model"),
      "capped",
    );
    expect(change).toHaveBeenCalledWith({
      name: "capped",
      parameters: { cap: 5 },
    });
    expect(screen.getByLabelText("Cap")).toHaveValue(5);
  });
  it("retains JSON editor focus after valid changes and blocks invalid JSON", async () => {
    function Field() {
      const [value, setValue] = useState<unknown>({ alpha: 1 });
      return (
        <SchemaField
          name="Parameters"
          schema={{ type: "object" }}
          root={{}}
          value={value}
          onChange={setValue}
          models={[]}
        />
      );
    }
    render(<Field />);
    const editor = screen.getByLabelText("Parameters");
    await userEvent.clear(editor);
    await userEvent.type(editor, '{{"beta":2}');
    expect(editor).toHaveFocus();
    expect(editor).toHaveValue('{"beta":2}');
    await userEvent.type(editor, "!");
    expect(editor).toBeInvalid();
    expect(screen.getByRole("alert")).toHaveTextContent("Enter valid JSON");
  });
  it("assigns distinct attacker identities when adding multiple attacks", async () => {
    const change = vi.fn();
    function Field() {
      const [value, setValue] = useState<unknown>([]);
      return (
        <SchemaField
          name="Attacks"
          schema={{ type: "array", items: { $ref: "#/$defs/AttackerSpec" } }}
          root={{
            $defs: {
              AttackerSpec: {
                title: "AttackerSpec",
                type: "object",
                properties: {
                  attacker_id: { type: "string", default: "attacker" },
                  name: { type: "string" },
                },
              },
            },
          }}
          value={value}
          onChange={(v) => {
            change(v);
            setValue(v);
          }}
          models={[
            {
              id: "sybil",
              name: "Sybil",
              category: "attack",
              schema: { type: "object", properties: {} },
              defaults: {},
            },
          ]}
        />
      );
    }
    render(<Field />);
    await userEvent.click(
      screen.getByRole("button", { name: "+ Add attacks" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "+ Add attacks" }),
    );
    const values = change.mock.calls.at(-1)![0] as { attacker_id: string }[];
    expect(new Set(values.map((v) => v.attacker_id)).size).toBe(2);
  });
});
