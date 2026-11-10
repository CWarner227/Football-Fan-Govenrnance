import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { RunProgress } from "../src/components/Common";
import type { Run } from "../src/types";

function running(progress: object, status = "running") {
  return {
    status,
    progress: {
      total_trials: 10,
      completed_trials: 2,
      percentage: 25,
      ...progress,
    },
  } as Run;
}
it("shows measured completion and an explicitly approximate time remaining", () => {
  render(
    <RunProgress
      run={running({ estimated_remaining_seconds: 125, phase: "simulating" })}
    />,
  );
  expect(screen.getByRole("progressbar")).toHaveAttribute("value", "25");
  expect(screen.getByText(/25% complete/)).toBeInTheDocument();
  expect(screen.getByText(/About 3 minutes remaining/)).toBeInTheDocument();
});
it("distinguishes startup, queued jobs and finalizing from a completion estimate", () => {
  const view = render(
    <RunProgress
      run={running({ percentage: 0, estimated_remaining_seconds: null })}
    />,
  );
  expect(screen.getByText(/Estimating time remaining/)).toBeInTheDocument();
  view.rerender(
    <RunProgress
      run={running({
        percentage: 95,
        phase: "finalizing",
        estimated_remaining_seconds: null,
      })}
    />,
  );
  expect(screen.getByText(/Finalizing results/)).toBeInTheDocument();
  view.rerender(<RunProgress run={running({ percentage: null }, "queued")} />);
  expect(screen.getByText(/Waiting in queue/)).toBeInTheDocument();
  expect(screen.queryByText(/remaining/)).not.toBeInTheDocument();
  view.rerender(<RunProgress run={running({}, "cancelled")} />);
  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
});
