import { useEffect, useRef, useState } from "react";
import type { HistoryFile, HistoryYear } from "../lib/types";
import { salinityRGB } from "../lib/salinity";
import { cellOf, setRefYear } from "../lib/refyear";

// Every day on record, one row per year, colored like the map's dots (decision 0028). The table in HistoryPanel.astro
// is the text alternative; this canvas adds the picture, a hover readout and, on station pages, picking a year to
// draw on the salinity chart.

interface Props {
  url: string;
  short: string;
  /** Station page: offer "compare a year" and honor #year-YYYY in the address. */
  pick?: boolean;
  compact?: boolean;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_START = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335];   // in a 366-day row

function tokens() {
  const cs = getComputedStyle(document.documentElement);
  const v = (n: string) => cs.getPropertyValue(n).trim();
  return { ink: v("--ink"), soft: v("--ink-soft"), empty: v("--paper-2"), fresh: v("--fresh"), brackish: v("--brackish"),
    gulf: v("--gulf"), mono: v("--mono") };
}

interface Layout { labelW: number; rowH: number; cellW: number; top: number; years: number[] }

function draw(canvas: HTMLCanvasElement, h: HistoryFile, compact: boolean, picked: number | null): Layout {
  const t = tokens();
  const first = h.years[0].year, last = h.years.at(-1)!.year;
  const years = Array.from({ length: last - first + 1 }, (_, i) => first + i);
  const byYear = new Map(h.years.map((y) => [y.year, y]));
  const W = canvas.clientWidth;
  const labelW = compact ? 30 : 36, rowH = compact ? 6 : 8, axisH = 16, top = 2;
  const H = top + years.length * rowH + axisH;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(W * dpr);
  canvas.height = Math.round(H * dpr);
  canvas.style.height = `${H}px`;
  const ctx = canvas.getContext("2d")!;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  const cellW = (W - labelW) / 366;
  const gap = rowH >= 6 ? 1 : 0;
  ctx.font = `10px ${t.mono}`;
  ctx.textBaseline = "middle";
  years.forEach((yr, r) => {
    const y = top + r * rowH;
    ctx.fillStyle = t.empty;
    ctx.fillRect(labelW, y, W - labelW, rowH - gap);
    const row = byYear.get(yr);
    if (row) {
      // Years with too few days stay faint: shown, but left out of the counts (shared rule, decision 0028).
      ctx.globalAlpha = row.counted ? 1 : 0.45;
      row.values.forEach((v, c) => {
        if (v === null && c === 59 && yr % 4 !== 0) v = row.values[58];   // no Feb 29 in common years: no stray gap
        if (v === null) return;
        ctx.fillStyle = `rgb(${salinityRGB(v, t).join(",")})`;
        ctx.fillRect(labelW + c * cellW, y, cellW + 0.6, rowH - gap);
      });
      ctx.globalAlpha = 1;
    }
    if (yr === first || yr === last || yr % 5 === 0 || yr === picked) {
      ctx.fillStyle = yr === picked ? t.ink : t.soft;
      ctx.fillText(String(yr), 0, y + rowH / 2);
    }
  });
  if (picked !== null && years.includes(picked)) {   // a bracket around the picked row
    const y = top + years.indexOf(picked) * rowH;
    ctx.strokeStyle = t.ink;
    ctx.lineWidth = 1;
    ctx.strokeRect(labelW - 0.5, y - 0.5, W - labelW, rowH);
  }
  // Today: a ring around its cell in the last row.
  const tc = cellOf(h.asof), ty = top + (years.length - 1) * rowH;
  ctx.strokeStyle = t.ink;
  ctx.lineWidth = 1.5;
  ctx.strokeRect(labelW + tc * cellW - 2, ty - 2, Math.max(cellW, 2) + 4, rowH - gap + 4);
  ctx.fillStyle = t.soft;
  ctx.textBaseline = "top";
  MONTH_START.forEach((c, m) => {
    const x = labelW + c * cellW;
    ctx.fillRect(x, top + years.length * rowH, 1, 3);
    if (!compact || m % 3 === 0) ctx.fillText(W - labelW < 420 ? MONTHS[m][0] : MONTHS[m], x + 2, top + years.length * rowH + 4);
  });
  return { labelW, rowH, cellW, top, years };
}

function describe(row: HistoryYear | undefined, year: number, cell: number): string {
  const date = new Date(Date.UTC(2000, 0, 1 + cell)).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
  const v = row?.values[cell];
  return `${date}, ${year}: ${v === null || v === undefined ? "no reading" : `${v.toFixed(1)} ppt`}`;
}

export default function HistoryStripes({ url, short, pick, compact }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const layout = useRef<Layout | null>(null);
  const [h, setH] = useState<HistoryFile | null>(null);
  const [failed, setFailed] = useState(false);
  const [picked, setPicked] = useState<number | null>(null);
  const [readout, setReadout] = useState("");

  useEffect(() => {
    fetch(url).then((r) => r.ok ? r.json() : Promise.reject(r.status)).then((d: HistoryFile) => {
      setH(d);
      const m = pick && location.hash.match(/^#year-(\d{4})$/);
      if (m && d.years.some((y) => y.year === +m[1])) {
        setPicked(+m[1]);
        requestAnimationFrame(() => canvas.current?.scrollIntoView({ block: "center" }));
      }
    }).catch(() => setFailed(true));
  }, [url, pick]);

  useEffect(() => {
    if (!h || !canvas.current) return;
    const c = canvas.current;
    const redraw = () => { layout.current = draw(c, h, !!compact, picked); };
    redraw();
    const ro = new ResizeObserver(redraw);
    ro.observe(c);
    const mq = matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", redraw);
    window.addEventListener("sc-theme-change", redraw);
    return () => { ro.disconnect(); mq.removeEventListener("change", redraw); window.removeEventListener("sc-theme-change", redraw); };
  }, [h, compact, picked]);

  useEffect(() => {
    if (!h || !pick) return;
    setRefYear(picked === null ? null : { site: h.id, year: picked, rows: Object.fromEntries(h.years.map((y) => [y.year, y.values])) });
  }, [h, pick, picked]);

  const at = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const L = layout.current;
    if (!L || !h) return null;
    const box = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - box.left - L.labelW, y = e.clientY - box.top - L.top;
    const r = Math.floor(y / L.rowH), cell = Math.floor(x / L.cellW);
    if (r < 0 || r >= L.years.length || cell < 0 || cell > 365) return null;
    return { year: L.years[r], cell };
  };
  const onMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const p = at(e);
    setReadout(p && h ? describe(h.years.find((y) => y.year === p.year), p.year, p.cell) : "");
  };

  if (failed) return <p className="quiet-note">The history picture didn't load. The table below has the same years.</p>;
  const first = h?.years[0].year, last = h?.years.at(-1)?.year;
  return (
    <div className="stripes">
      {pick && h && (
        <label className="stripes-pick">
          {"Compare a year on the salinity chart "}
          <select value={picked ?? ""} onChange={(e) => setPicked(e.target.value ? +e.target.value : null)}>
            <option value="">None</option>
            {h.years.slice().reverse().filter((y) => y.year !== last).map((y) => <option key={y.year} value={y.year}>{y.year}</option>)}
          </select>
        </label>
      )}
      <canvas ref={canvas} className="stripes-canvas" role="img"
        aria-label={h ? `Daily salinity at ${short}, one row per year from ${first} to ${last}, colored from brown (fresh river water) through green (brackish) to blue (Gulf water). The table below lists each year.` : `Loading salinity history for ${short}`}
        onPointerMove={onMove} onPointerLeave={() => setReadout("")}
        onClick={(e) => { const p = pick && at(e); if (p && p.year !== last) setPicked(p.year === picked ? null : p.year); }} />
      <p className="stripes-readout" aria-hidden="true">{readout || " "}</p>
    </div>
  );
}
