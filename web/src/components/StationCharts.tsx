import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { BarChart, CustomChart, LineChart } from "echarts/charts";
import {
  AriaComponent, AxisPointerComponent, GridComponent,
  MarkLineComponent, TitleComponent, TooltipComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { SeriesPoint } from "../lib/types";
import { getRefYear, onRefYear, refValue, type RefYear } from "../lib/refyear";

echarts.use([LineChart, BarChart, CustomChart, GridComponent, TooltipComponent, MarkLineComponent,
  AxisPointerComponent, TitleComponent, AriaComponent, SVGRenderer]);

export interface Panel {
  key: string;
  title: string;
  unit: string;
  kind: "line" | "bar";
  points: SeriesPoint[];
  threshold?: { value: number; label: string };
  thresholds?: { value: number; label: string }[];
  /** Official forecast continuing past the last observation: [ISO time, value] */
  forecast?: [string, number][];
  log?: boolean;          // log scale (river flow spans orders of magnitude)
  /** Virtual sensor: [date, expected, lo90, hi90] */
  expected?: [string, number | null, number | null, number | null][];
}

const RANGES = [
  { days: 30, label: "30 days" },
  { days: 120, label: "4 months" },
  { days: 365, label: "1 year" },
];
const PANEL_H = 128, TITLE_H = 30, GAP = 26, AXIS_H = 28;

function tokens() {
  const cs = getComputedStyle(document.documentElement);
  const v = (n: string) => cs.getPropertyValue(n).trim();
  return {
    ink: v("--ink"), soft: v("--ink-soft"), rule: v("--rule"), water: v("--water"), paper: v("--paper"),
    gulf: v("--gulf"), fresh: v("--fresh"), red: v("--marker-red"),
    sans: v("--sans"), mono: v("--mono"), accent: v("--accent"),
  };
}

function fmtVal(v: number | null | undefined, unit: string) {
  if (v === null || v === undefined) return "—";
  if (unit === "cfs") return `${Math.round(v).toLocaleString("en-US")} ${unit}`;
  if (unit.startsWith("°")) return `${Math.round(v)}${unit}`;
  if (unit === "in") return `${v.toFixed(2)} ${unit}`;
  return `${v.toFixed(1)} ${unit}`;
}

function buildOption(allPanels: Panel[], t: ReturnType<typeof tokens>, days: number, ref: RefYear | null, asofYear: number) {
  // Show only the selected range so each axis scales to what's on screen.
  const panels = allPanels.map((p) => ({ ...p, points: p.points.slice(-days), expected: p.expected?.slice(-days) }));
  const last = panels[0]?.points.at(-1)?.[0];
  const fcEnd = Math.max(0, ...panels.flatMap((p) => (p.forecast ?? []).map((f) => new Date(f[0]).getTime())));
  const end = Math.max(last ? new Date(`${last}T12:00:00`).getTime() : Date.now(), fcEnd);
  const start = end - (days - 1) * 86400_000;
  const grids = panels.map((_, i) => ({
    left: 64, right: 18, top: i * (PANEL_H + TITLE_H + GAP) + TITLE_H, height: PANEL_H, containLabel: false,
  }));
  const ts = (d: string) => `${d}T12:00:00`;
  const series: any[] = [];
  panels.forEach((p, i) => {
    const band = p.points.filter((q) => q[2] !== null && q[4] !== null);
    if (band.length > 2) {
      // Normal band (p10-p90) as one polygon: correct on linear and log axes alike.
      series.push({
        type: "custom", xAxisIndex: i, yAxisIndex: i, silent: true, clip: true, z: 1, tooltip: { show: false },
        // Real band values as data so the axis extent fits them; draw the polygon once.
        data: band.flatMap((q) => [[ts(q[0]), q[2]], [ts(q[0]), q[4]]]),
        renderItem: (params: any, api: any) => {
          if (params.dataIndex !== 0) return null;
          const top = band.map((q) => api.coord([ts(q[0]), Math.max(q[4] as number, 1e-6)]));
          const bot = band.slice().reverse().map((q) => api.coord([ts(q[0]), Math.max(q[2] as number, 1e-6)]));
          return { type: "polygon", shape: { points: [...top, ...bot] }, style: { fill: t.water }, silent: true };
        },
      });
      series.push({
        type: "line", xAxisIndex: i, yAxisIndex: i, symbol: "none", z: 2, silent: true,
        lineStyle: { color: t.soft, width: 1, type: [4, 4] }, data: p.points.map((q) => [ts(q[0]), q[3]]),
      });
    }
    const ex = (p.expected ?? []).filter((q) => q[2] !== null && q[3] !== null);
    if (ex.length > 2) {
      series.push({
        type: "custom", xAxisIndex: i, yAxisIndex: i, silent: true, clip: true, z: 2, tooltip: { show: false },
        data: ex.flatMap((q) => [[ts(q[0]), q[2]], [ts(q[0]), q[3]]]),
        renderItem: (params: any, api: any) => {
          if (params.dataIndex !== 0) return null;
          const top = ex.map((q) => api.coord([ts(q[0]), q[3]]));
          const bot = ex.slice().reverse().map((q) => api.coord([ts(q[0]), q[2]]));
          return { type: "polygon", shape: { points: [...top, ...bot] }, style: { fill: t.soft, opacity: 0.12 }, silent: true };
        },
      }, {
        type: "line", xAxisIndex: i, yAxisIndex: i, symbol: "none", z: 2, silent: true, connectNulls: false,
        lineStyle: { color: t.ink, width: 1.2, type: [2, 3], opacity: 0.7 }, data: (p.expected ?? []).map((q) => [ts(q[0]), q[1]]),
      });
    }
    if (ref && p.key === `${ref.site}:salinity`) {   // a year picked on the history picture, on the same dates
      series.push({
        type: "line", xAxisIndex: i, yAxisIndex: i, symbol: "none", z: 2, silent: true, connectNulls: false,
        lineStyle: { color: t.soft, width: 1.4, opacity: 0.75 }, data: p.points.map((q) => [ts(q[0]), refValue(ref, q[0], asofYear)]),
      });
    }
    if (p.forecast?.length) {
      series.push({
        name: `${p.key}-forecast`, type: "line", xAxisIndex: i, yAxisIndex: i, symbol: "none", z: 3,
        lineStyle: { color: t.gulf, width: 2, type: [5, 4] }, data: p.forecast,
      });
    }
    series.push({
      name: p.key, type: p.kind, xAxisIndex: i, yAxisIndex: i, symbol: "none", connectNulls: false, z: 3,
      barMaxWidth: 6, itemStyle: { color: p.kind === "bar" ? t.fresh : t.accent },
      lineStyle: { color: t.accent, width: 1.8 },
      data: p.points.map((q) => [ts(q[0]), p.log && q[1] !== null && q[1] <= 0 ? null : q[1]]),
      markLine: (p.threshold || p.thresholds?.length) ? {
        silent: true, symbol: "none", lineStyle: { color: t.red, type: [6, 4], width: 1.2 },
        label: { color: t.red, fontFamily: t.sans, fontSize: 11, position: "insideEndTop" },
        data: [...(p.threshold ? [p.threshold] : []), ...(p.thresholds ?? [])]
          .map((th) => ({ yAxis: th.value, label: { formatter: th.label } })),
      } : undefined,
    });
  });

  return {
    animation: false,
    aria: { enabled: true, decal: { show: false } },
    textStyle: { fontFamily: t.sans, color: t.soft },
    title: panels.map((p, i) => ({
      text: `${p.title}  {u|${p.unit}}`, subtext: "", left: 64, top: grids[i].top - TITLE_H + 4,
      textStyle: { fontFamily: t.sans, fontSize: 14, fontWeight: 600, color: t.ink,
        rich: { u: { fontFamily: t.sans, fontSize: 13, fontWeight: 400, color: t.soft } } },
    })),
    grid: grids,
    xAxis: panels.map((_, i) => ({
      type: "time", gridIndex: i, min: start, max: end + 43200_000,
      axisLine: { lineStyle: { color: t.rule } }, axisTick: { show: false },
      axisLabel: { show: i === panels.length - 1, color: t.soft, fontFamily: t.sans, hideOverlap: true,
        formatter: (v: number) => new Date(v).toLocaleDateString("en-US", days > 120 ? { month: "short" } : { month: "short", day: "numeric" }) },
      splitLine: { show: false },
    })),
    yAxis: panels.map((p, i) => ({
      type: p.log ? "log" : "value", gridIndex: i, scale: p.kind !== "bar", splitNumber: 3, logBase: 10,
      // Keep threshold lines on the chart even when the river is far below them.
      max: p.thresholds?.length ? (v: { max: number }) => Math.ceil(Math.max(v.max, ...p.thresholds!.map((th) => th.value)) + 1) : undefined,
      axisLabel: { color: t.soft, fontFamily: t.sans, formatter: (v: number) => (Math.abs(v) >= 1000 ? `${Math.round(v / 1000)}k` : `${+v.toFixed(1)}`) },
      splitLine: { lineStyle: { color: t.rule, opacity: 0.7 } },
    })),
    axisPointer: { link: [{ xAxisIndex: "all" }], lineStyle: { color: t.soft }, label: { show: false } },
    tooltip: {
      trigger: "axis", confine: true, backgroundColor: t.paper, borderColor: t.rule, textStyle: { color: t.ink, fontFamily: t.sans, fontSize: 13 },
      formatter: (items: any[]) => {
        if (!items.length) return "";
        const date = new Date(items[0].axisValue).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
        const rows = panels.map((p) => {
          const pt = p.points.find((q) => `${q[0]}T12:00:00` === items[0].axisValueLabel || new Date(`${q[0]}T12:00:00`).getTime() === items[0].axisValue);
          const val = fmtVal(pt?.[1], p.unit);
          const typ = pt && pt[3] !== null ? ` <span style="color:${t.soft}">(typical ${fmtVal(pt[3], p.unit)})</span>` : "";
          const exp = p.expected?.find((q) => new Date(`${q[0]}T12:00:00`).getTime() === items[0].axisValue);
          const expTxt = exp && exp[1] !== null ? ` <span style="color:${t.soft}">(neighbors suggest ${fmtVal(exp[1], p.unit)})</span>` : "";
          const rv = ref && pt && p.key === `${ref.site}:salinity` ? refValue(ref, pt[0], asofYear) : null;
          const refTxt = rv !== null ? ` <span style="color:${t.soft}">(${ref!.year - (asofYear - +pt![0].slice(0, 4))}: ${fmtVal(rv, p.unit)})</span>` : "";
          return `<div>${p.title}: <b>${val}</b>${typ}${expTxt}${refTxt}</div>`;
        });
        return `<div style="font-weight:600;margin-bottom:4px">${date}</div>${rows.join("")}`;
      },
    },
    series,
  };
}

export default function StationCharts({ panels, note, asofYear }: { panels: Panel[]; note?: string; asofYear: number }) {
  const el = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const [days, setDays] = useState(120);
  const [ref, setRef] = useState<RefYear | null>(getRefYear);
  useEffect(() => onRefYear(setRef), []);
  const height = panels.length * (PANEL_H + TITLE_H + GAP) - GAP + AXIS_H;

  useEffect(() => {
    if (!el.current) return;
    const c = echarts.init(el.current, null, { renderer: "svg" });
    chart.current = c;
    const draw = () => c.setOption(buildOption(panels, tokens(), days, ref, asofYear) as any, true);
    draw();
    const ro = new ResizeObserver(() => c.resize());
    ro.observe(el.current);
    const mq = matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", draw);
    window.addEventListener("sc-theme-change", draw);
    return () => {
      ro.disconnect();
      mq.removeEventListener("change", draw);
      window.removeEventListener("sc-theme-change", draw);
      c.dispose();
    };
  }, [panels, days, ref, asofYear]);

  return (
    <section className="panel" aria-labelledby="charts-h">
      <div className="panel-head">
        <h2 id="charts-h">History</h2>
        <div className="ranges" role="group" aria-label="Time range">
          {RANGES.map((r) => (
            <button key={r.days} type="button" className="btn" aria-pressed={days === r.days} onClick={() => setDays(r.days)}>{r.label}</button>
          ))}
        </div>
      </div>
      <div ref={el} className="chart-box" style={{ height }} role="img"
        aria-label={`Charts of ${panels.map((p) => p.title).join(", ")} over the last ${days} days`} />
      <p className="chart-note">
        Shaded band: the middle 80% of past readings for that time of year. Dashed line: typical.
        Charts share one time axis, upstream first: rain, then the river, then this station. Hover or tap for values.
        {panels.some((p) => p.forecast?.length) && " Dashed line past today: the official NWS forecast."}
        {note && <> {note}</>}
        {ref && panels.some((p) => p.key === `${ref.site}:salinity`) && ` Solid gray line: ${ref.year} on the same dates.`}
      </p>
    </section>
  );
}
