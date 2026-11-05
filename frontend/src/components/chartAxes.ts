/** Presentation defaults only; all values and units remain engine-produced. */
export function selectChartAxes(
  columns: string[],
  numeric: string[],
  preferred: string[],
  table: string,
  tab: string,
  x = "",
  y = "",
) {
  return {
    x: columns.includes(x)
      ? x
      : (["month", "day", "date", "trial"].find((k) => columns.includes(k)) ??
        numeric[0] ??
        columns[0] ??
        ""),
    y: preferred.includes(y)
      ? y
      : table === "aggregate" && preferred.includes("mean")
        ? "mean"
        : tab === "Economics" && preferred.includes("cash_balance")
          ? "cash_balance"
          : (preferred.find((k) => !/seed|trial|month|grid/.test(k)) ??
            preferred[0] ??
            ""),
  };
}
export function histogramCountLabel() {
  return "Observation count";
}
