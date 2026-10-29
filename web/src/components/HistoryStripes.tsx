import { useEffect, useRef, useState } from "react";
import type { HistoryFile, HistoryYear } from "../lib/types";
import { hexRGB, salinityRGB } from "../lib/salinity";
import { cellOf, setRefYear } from "../lib/refyear";

// Every day on record, one row per year, colored like the map's dots (decisions 0028, 0032). Years that count come
// first; years with readings on under 80% of their days sit in their own group below, so faded rows don't mix in.
// The table in HistoryPanel.astro is the text alternative; this canvas adds the picture, a hover readout, notable-year
// tags in the right margin and, on a tap, links to that year's station page and that day on the map.

interface Props {
  url: string;
  short: string;
  /** Station page: offer "compare a year" and honor #year-YYYY in the address. */
  pick?: boolean;
  /** Home: smaller rows. Phones always get the compact rows. */
  compact?: boolean;
  /** Home: a tapped row links to this station page's #year-YYYY. */
  stationHref?: string;
  /** Where the map lives: a tapped day links to `${mapHref}#YYYY-MM-DD` (decision 0033). */
  mapHref?: string;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_START = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335];   // in a 366-day row
const GROUP_GAP = 22;

const rgb = hexRGB;
const mixHex = (a: string, b: string, k: number) => `rgb(${rgb(a).map((x, i) => Math.round(x + (rgb(b)[i] - x) * k)).join(",")})`;

function tokens() {
  const cs = getComputedStyle(document.documentElement);
  const v = (n: string) => cs.getPropertyValue(n).trim();
  return { ink: v("--ink"), soft: v("--ink-soft"), paper: v("--paper"), fresh: v("--fresh"), brackish: v("--brackish"),
    gulf: v("--gulf"), mono: v("--mono") };
}

interface Row { year: number; y: number }
interface Layout { labelW: number; rowH: number; cellW: number; rows: Row[]; partialY: number | null }

const isCurrent = (h: HistoryFile, y: HistoryYear) => y.year === h.years.at(-1)!.year;

function draw(canvas: HTMLCanvasElement, h: HistoryFile, compact: boolean, picked: number | null, pin: Pin | null): Layout {
  const t = tokens();
  const W = canvas.clientWidth;
  const small = compact || W < 560;
  const first = h.years[0].year, last = h.years.at(-1)!.year;
  const byYear = new Map(h.years.map((y) => [y.year, y]));
  // Counted years (and this one) in date order, with any missing year as an empty row so the gaps show; partial years below.
  const main = Array.from({ length: last - first + 1 }, (_, i) => first + i).filter((y) => !byYear.has(y) || byYear.get(y)!.counted || y === last);
  const partial = h.years.filter((y) => !y.counted && !isCurrent(h, y)).map((y) => y.year);
  const tags = h.tags ?? {};
  const tagW = W >= 480 && Object.keys(tags).length ? (small ? 74 : 104) : 0;
  const labelW = small ? 30 : 38, rowH = small ? 6 : 10, axisH = 18, top = 2;
  const gap = rowH >= 6 ? 1 : 0;
  const rows: Row[] = main.map((year, i) => ({ year, y: top + i * rowH }));
  const mainEnd = top + main.length * rowH;
  const partialY = partial.length ? mainEnd + axisH + GROUP_GAP : null;
  partial.forEach((year, i) => rows.push({ year, y: partialY! + i * rowH }));
  const H = (partialY !== null ? partialY + partial.length * rowH : mainEnd + axisH) + 4;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(W * dpr);
  canvas.height = Math.round(H * dpr);
  canvas.style.height = `${H}px`;
  const ctx = canvas.getContext("2d")!;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  const gridW = W - labelW - tagW;
  const cellW = gridW / 366;
  const missing = mixHex(t.paper, t.ink, 0.07);     // one light, even color for days with no reading
  ctx.font = `${small ? 9.5 : 10.5}px ${t.mono}`;
  ctx.textBaseline = "middle";
  const colors = new Map<number, string>();
  const color = (v: number) => {
    const k = Math.round(v * 5);
    let c = colors.get(k);
    if (!c) { c = `rgb(${salinityRGB(k / 5, t).join(",")})`; colors.set(k, c); }
    return c;
  };
  for (const { year, y } of rows) {
    ctx.fillStyle = missing;
    ctx.fillRect(labelW, y, gridW, rowH - gap);
    const row = byYear.get(year);
    row?.values.forEach((v, c) => {
      if (v === null && c === 59 && year % 4 !== 0) v = row.values[58];   // no Feb 29 in common years: no stray gap
      if (v === null) return;
      ctx.fillStyle = color(v);
      ctx.fillRect(labelW + c * cellW, y, cellW + 0.6, rowH - gap);
    });
    const inPartial = partial.includes(year);
    // Partial years are listed out of order, so each gets its label when the rows are tall enough; otherwise the ends.
    const label = year === picked || year === pin?.year || (inPartial
      ? rowH >= 10 || year === partial[0] || year === partial.at(-1)
      : year === first || year === last || year % 5 === 0);
    if (label) {
      ctx.fillStyle = year === picked || year === pin?.year ? t.ink : t.soft;
      ctx.textAlign = "left";
      ctx.fillText(String(year), 0, y + rowH / 2);
    }
    if (tagW && tags[year] && rowH >= 6) {
      ctx.fillStyle = t.soft;
      ctx.textAlign = "left";
      ctx.fillText(tags[year], labelW + gridW + 6, y + rowH / 2, tagW - 8);
    }
  }
  ctx.textAlign = "left";
  // Faint month lines through every row, so a column is easy to follow down the years.
  const groups: [number, number][] = [[top, mainEnd]];
  if (partialY !== null) groups.push([partialY, partialY + partial.length * rowH]);
  ctx.fillStyle = t.paper;
  ctx.globalAlpha = 0.55;
  for (const [y0, y1] of groups) MONTH_START.slice(1).forEach((c) => ctx.fillRect(labelW + c * cellW - 0.5, y0, 1, y1 - y0 - gap));
  ctx.globalAlpha = 1;
  // Today: a full-height line through the counted years, and a ring around its cell in this year's row.
  const tc = cellOf(h.asof), tx = labelW + (tc + 0.5) * cellW;
  ctx.fillStyle = t.ink;
  ctx.fillRect(tx - 0.75, top - 1, 1.5, mainEnd - top + 4);
  const ty = rows.find((r) => r.year === last)!.y;
  ctx.strokeStyle = t.ink;
  ctx.lineWidth = 1.5;
  ctx.strokeRect(labelW + tc * cellW - 2, ty - 2, Math.max(cellW, 2) + 4, rowH - gap + 4);
  for (const yr of [picked, pin?.year]) {             // a bracket around the picked or tapped row
    const r = rows.find((r) => r.year === yr);
    if (!r) continue;
    ctx.lineWidth = 1;
    ctx.strokeRect(labelW - 0.5, r.y - 0.5, gridW + 1, rowH);
  }
  if (pin) {
    const r = rows.find((r) => r.year === pin.year);
    if (r) { ctx.fillStyle = t.ink; ctx.fillRect(labelW + pin.cell * cellW - 0.5, r.y - 3, Math.max(cellW, 1.5) + 1, rowH + 6 - gap); }
  }
  ctx.fillStyle = t.soft;
  ctx.textBaseline = "top";
  const todayX = Math.min(tx + 3, labelW + gridW - 32);
  MONTH_START.forEach((c, m) => {
    const x = labelW + c * cellW;
    ctx.fillRect(x, mainEnd, 1, 3);
    const near = x + 2 > todayX - 26 && x + 2 < todayX + 34;   // "Today" wins over a month name it would overlap
    if ((!small || m % 3 === 0) && !near) ctx.fillText(gridW < 420 ? MONTHS[m][0] : MONTHS[m], x + 2, mainEnd + 4);
  });
  ctx.fillStyle = t.ink;
  ctx.fillText("Today", todayX, mainEnd + 4);
  if (partialY !== null) {
    ctx.fillStyle = t.soft;
    ctx.textBaseline = "bottom";
    ctx.fillText(gridW < 420 ? "Partial years, not counted" : "Partial years: readings on under 80% of days, not counted", labelW, partialY - 3);
  }
  return { labelW, rowH, cellW, rows, partialY };
}

const dateOf = (year: number, cell: number) => {
  const d = new Date(Date.UTC(2000, 0, 1 + cell));
  return { iso: `${year}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`,
    text: `${d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" })}, ${year}` };
};

function describe(h: HistoryFile, row: HistoryYear | undefined, year: number, cell: number): string {
  const v = row?.values[cell];
  const day = `${dateOf(year, cell).text}: ${v === null || v === undefined ? "no reading" : `${v.toFixed(1)} ppt`}`;
  if (!row) return day;
  const tag = h.tags?.[year] ? ` (${h.tags[year]})` : "";
  return `${day} · ${year}${tag}: ${row.under} days under ${h.fresh_below} ppt, ${row.over} over ${h.salty_above}`;
}

interface Pin { year: number; cell: number }

export default function HistoryStripes({ url, short, pick, compact, stationHref, mapHref }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const layout = useRef<Layout | null>(null);
  const [h, setH] = useState<HistoryFile | null>(null);
  const [failed, setFailed] = useState(false);
  const [picked, setPicked] = useState<number | null>(null);
  const [pin, setPin] = useState<Pin | null>(null);
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
    const redraw = () => { layout.current = draw(c, h, !!compact, picked, pin); c.dataset.drawn = ""; };
    redraw();
    const ro = new ResizeObserver(redraw);
    ro.observe(c);
    const mq = matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", redraw);
    window.addEventListener("sc-theme-change", redraw);
    return () => { ro.disconnect(); mq.removeEventListener("change", redraw); window.removeEventListener("sc-theme-change", redraw); };
  }, [h, compact, picked, pin]);

  useEffect(() => {
    if (!h || !pick) return;
    setRefYear(picked === null ? null : { site: h.id, year: picked, rows: Object.fromEntries(h.years.map((y) => [y.year, y.values])) });
  }, [h, pick, picked]);

  const at = (e: React.MouseEvent<HTMLCanvasElement>): Pin | null => {
    const L = layout.current;
    if (!L || !h) return null;
    const box = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - box.left - L.labelW, y = e.clientY - box.top;
    const row = L.rows.find((r) => y >= r.y && y < r.y + L.rowH);
    const cell = Math.floor(x / L.cellW);
    if (!row || cell < 0 || cell > 365) return null;
    return { year: row.year, cell };
  };
  const onMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const p = at(e);
    setReadout(p && h ? describe(h, h.years.find((y) => y.year === p.year), p.year, p.cell) : "");
  };
  const onTap = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const p = at(e);
    if (!p || !h) { setPin(null); return; }
    const same = pin && pin.year === p.year && pin.cell === p.cell;
    setPin(same ? null : p);
    if (pick && p.year !== h.years.at(-1)!.year && !same) setPicked(p.year);
  };

  if (failed) return <p className="quiet-note">The history picture didn't load. The table below has the same years.</p>;
  const first = h?.years[0].year, last = h?.years.at(-1)?.year;
  const pinDay = pin ? dateOf(pin.year, pin.cell) : null;
  const pinRow = pin && h ? h.years.find((y) => y.year === pin.year) : undefined;
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
        onPointerMove={onMove} onPointerLeave={() => setReadout("")} onClick={onTap} />
      <p className="stripes-readout" aria-hidden="true">{readout || (pin && h ? describe(h, pinRow, pin.year, pin.cell) : " ")}</p>
      {pin && pinDay && (stationHref || mapHref !== undefined) && (
        <p className="stripes-links">
          {stationHref && <a href={`${stationHref}#year-${pin.year}`}>{`${pin.year} at ${short}`}</a>}
          {mapHref !== undefined && pinRow && <a href={`${mapHref}#${pinDay.iso}`}>{`${pinDay.text} on the map`}</a>}
        </p>
      )}
    </div>
  );
}
