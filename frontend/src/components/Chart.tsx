import { useEffect, useRef, useState } from "react";
import type { Row } from "../types";
import { human } from "./SchemaForm";
import { histogramCountLabel } from "./chartAxes";
import { Notice } from "./Common";
type Plot = {
  react: (
    el: HTMLElement,
    data: unknown[],
    layout: unknown,
    config: unknown,
  ) => Promise<void>;
  purge: (el: HTMLElement) => void;
};
export default function Chart({
  rows,
  x,
  y,
  kind,
  category,
}: {
  rows: Row[];
  x: string;
  y: string;
  kind: string;
  category?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    let plot: Plot | undefined;
    const el = ref.current!;
    setError("");
    void import("plotly.js-dist-min")
      .then(async (module) => {
        if (!alive) return;
        plot = module.default as Plot;
        const groups = category
          ? [...new Set(rows.map((r) => String(r[category] ?? "Unspecified")))]
          : ["Selected trials"];
        const traces = groups.map((g, i) => {
          const data = category
            ? rows.filter((r) => String(r[category] ?? "Unspecified") === g)
            : rows;
          const xs = data.map((r) => r[x]);
          const ys = data.map((r) => r[y]);
          const colors = [
            "#16785b",
            "#3d65a5",
            "#b97c2a",
            "#8c5bab",
            "#d16c61",
          ];
          if (kind === "histogram")
            return {
              type: "histogram",
              x: ys,
              name: g,
              opacity: 0.7,
              marker: { color: colors[i % colors.length] },
            };
          if (kind === "box")
            return {
              type: "box",
              y: ys,
              name: g,
              boxpoints: "outliers",
              marker: { color: colors[i % colors.length] },
            };
          if (kind === "heatmap")
            return {
              type: "heatmap",
              x: [...new Set(xs)],
              y: [human(y)],
              z: [ys],
              colorscale: "Greens",
              name: g,
            };
          const low =
            y === "mean" && data.some((r) => typeof r.wilson_lower === "number")
              ? "wilson_lower"
              : y === "q50"
                ? "q025"
                : `${y.replace(/_mean$/, "")}_ci_low`;
          const high =
            low === "wilson_lower"
              ? "wilson_upper"
              : y === "q50"
                ? "q975"
                : `${y.replace(/_mean$/, "")}_ci_high`;
          return {
            type: kind === "bar" ? "bar" : "scatter",
            mode: kind === "scatter" ? "markers" : "lines+markers",
            x: xs,
            y: ys,
            name: g,
            marker: { color: colors[i % colors.length], size: 5 },
            error_y: data.some(
              (r) => typeof r[low] === "number" && typeof r[high] === "number",
            )
              ? {
                  type: "data",
                  symmetric: false,
                  array: data.map((r) => Number(r[high]) - Number(r[y])),
                  arrayminus: data.map((r) => Number(r[y]) - Number(r[low])),
                }
              : undefined,
          };
        });
        await plot.react(
          el,
          traces,
          {
            autosize: true,
            height: 430,
            margin: { l: 70, r: 30, t: 30, b: 75 },
            paper_bgcolor: "transparent",
            plot_bgcolor: "transparent",
            font: { family: "Inter, Segoe UI, sans-serif", color: "#64748b" },
            xaxis: {
              title: { text: human(kind === "histogram" ? y : x) },
              gridcolor: "#e9edf2",
            },
            yaxis: {
              title: {
                text:
                  kind === "histogram"
                    ? histogramCountLabel()
                    : human(
                        y === "mean" && rows[0]?.metric
                          ? String(rows[0].metric) + " (mean)"
                          : y,
                      ),
              },
              gridcolor: "#e9edf2",
            },
            legend: { orientation: "h", y: -0.2 },
            hovermode: "closest",
          },
          {
            responsive: true,
            displaylogo: false,
            toImageButtonOptions: {
              format: "svg",
              filename: "governance-research-chart",
            },
            modeBarButtonsToAdd: [
              {
                name: "Download PNG",
                icon: { width: 20, height: 20, path: "M4 4h12v12H4z" },
                click: (gd: unknown) => {
                  const exporter = module.default as unknown as {
                    downloadImage: (gd: unknown, options: unknown) => void;
                  };
                  exporter.downloadImage(gd, {
                    format: "png",
                    filename: "governance-research-chart",
                  });
                },
              },
            ],
          },
        );
      })
      .catch((e) => {
        if (alive) setError(String(e));
      });
    return () => {
      alive = false;
      plot?.purge(el);
    };
  }, [rows, x, y, kind, category]);
  return (
    <>
      {error && <Notice error={error} />}
      <div
        ref={ref}
        className="plot"
        aria-label={`${human(y)} ${kind} chart`}
        role="img"
      />
    </>
  );
}
