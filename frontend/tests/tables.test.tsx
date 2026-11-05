import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { it, expect } from "vitest";
import { PagedDataTable, ExecutionHistory } from "../src/components/Common";
import type { Run } from "../src/types";
it("charts measured completed execution durations without including cancelled work", () => {
  render(
    <ExecutionHistory
      runs={
        [
          {
            id: "a",
            name: "Completed",
            status: "completed",
            elapsed_seconds: 2,
          },
          {
            id: "b",
            name: "Cancelled",
            status: "cancelled",
            elapsed_seconds: 9,
          },
        ] as Run[]
      }
    />,
  );
  expect(screen.getAllByRole("meter")).toHaveLength(1);
  expect(screen.getByRole("meter")).toHaveAttribute("value", "2");
  expect(screen.queryByText("Cancelled")).not.toBeInTheDocument();
});
it("renders only fifty comparison observations at once", async () => {
  render(
    <PagedDataTable
      label="Matched observations"
      rows={Array.from({ length: 5000 }, (_, i) => ({
        metric: "turnout",
        trial: i,
        difference: i / 10000,
      }))}
    />,
  );
  expect(screen.getAllByRole("row")).toHaveLength(51);
  expect(screen.getByText("0.0049")).toBeInTheDocument();
  expect(screen.queryByText("0.005")).not.toBeInTheDocument();
  await userEvent.click(
    screen.getByRole("button", { name: "Next Matched observations" }),
  );
  expect(screen.getAllByRole("row")).toHaveLength(51);
  expect(screen.getByText("0.005")).toBeInTheDocument();
});
