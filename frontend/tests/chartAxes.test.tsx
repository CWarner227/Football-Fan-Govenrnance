import { describe, it, expect } from "vitest";
import {
  selectChartAxes,
  histogramCountLabel,
} from "../src/components/chartAxes";
describe("chart presentation defaults", () => {
  it("prefers actual time columns over metric names containing month", () => {
    const columns = [
      "financial_runway_months",
      "trial",
      "date",
      "day",
      "month",
      "cash_balance",
    ];
    expect(
      selectChartAxes(columns, columns, columns, "timeseries", "Economics").x,
    ).toBe("month");
    expect(
      selectChartAxes(
        ["runway_months", "date", "day", "trial"],
        [],
        [],
        "timeseries",
        "Timeline",
      ).x,
    ).toBe("day");
    expect(
      selectChartAxes(
        ["runway_months", "trial", "date"],
        [],
        [],
        "summary",
        "Summary",
      ).x,
    ).toBe("date");
  });
  it("prefers cash balance for economics while preserving explicit selections and aggregate mean", () => {
    const columns = ["administrative_cost", "cash_balance", "month"];
    expect(
      selectChartAxes(columns, columns, columns, "timeseries", "Economics").y,
    ).toBe("cash_balance");
    expect(
      selectChartAxes(
        columns,
        columns,
        columns,
        "timeseries",
        "Economics",
        "administrative_cost",
        "administrative_cost",
      ),
    ).toEqual({ x: "administrative_cost", y: "administrative_cost" });
    expect(
      selectChartAxes(
        ["mean", "month"],
        ["mean"],
        ["mean"],
        "aggregate",
        "Economics",
      ).y,
    ).toBe("mean");
  });
  it("labels histogram counts as observations across table types", () => {
    expect(histogramCountLabel()).toBe("Observation count");
  });
});
