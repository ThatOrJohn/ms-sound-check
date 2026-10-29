import { useEffect, useState } from "react";
import type { TideStrip as Strip } from "../lib/types";
import { fmtTime } from "../lib/format";

interface Props { strip: Strip }

const HOUR = 3600e3, BACK = 12 * HOUR, AHEAD = 36 * HOUR;
const W = 600, H = 44, PAD = 4;
const TZ = "America/Chicago";
const dayKey = (t: number) => new Date(t).toLocaleDateString("en-CA", { timeZone: TZ });
const weekday = (t: number) => new Date(t).toLocaleDateString("en-US", { weekday: "short", timeZone: TZ });
const ft = (v: number) => `${v < 0 ? "−" : ""}${Math.abs(v).toFixed(1)} ft`;

/** Predicted water level between NOAA's highs and lows: the usual half-cosine between turning points. */
function level(ev: { t: number; ft: number }[], t: number): number {
  const i = Math.max(0, ev.findIndex((_, k) => k === ev.length - 1 || ev[k + 1].t > t));
  const a = ev[i], b = ev[Math.min(i + 1, ev.length - 1)];
  if (b.t === a.t) return a.ft;
  const f = Math.min(1, Math.max(0, (t - a.t) / (b.t - a.t)));
  return a.ft + (b.ft - a.ft) * (1 - Math.cos(Math.PI * f)) / 2;
}

/** The last 12 hours and next 36 of predicted tide at one station, with "now" marked. Rendered in the browser so
 *  "now" is the reader's now, not the build's. */
export default function TideStrip({ strip }: Props) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const id = window.setInterval(() => setNow(Date.now()), 5 * 60e3); return () => window.clearInterval(id); }, []);
  const [narrow, setNarrow] = useState(() => matchMedia("(max-width: 520px)").matches);
  useEffect(() => {
    const mq = matchMedia("(max-width: 520px)"), on = () => setNarrow(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  const ev = strip.events.map((e) => ({ ...e, t: Date.parse(e.time) }));
  if (ev.length < 2 || now < ev[0].t || now > ev.at(-1)!.t) return null;
  const t0 = Math.max(ev[0].t, now - BACK), t1 = Math.min(ev.at(-1)!.t, now + AHEAD);
  const lo = Math.min(...ev.map((e) => e.ft)), hi = Math.max(...ev.map((e) => e.ft)), span = hi - lo || 1;
  const x = (t: number) => ((t - t0) / (t1 - t0)) * W;
  const y = (v: number) => H - PAD - ((v - lo) / span) * (H - 2 * PAD);
  const path = (a: number, b: number) => {
    let d = "";
    for (let t = a; ; t = Math.min(b, t + HOUR / 6)) {
      d += `${d ? "L" : "M"}${x(t).toFixed(1)},${y(level(ev, t)).toFixed(1)} `;
      if (t >= b) return d;
    }
  };

  const next = ev.filter((e) => e.t > now).slice(0, 2);
  const when = (t: number) => {
    const d = dayKey(t), today = dayKey(now), tomorrow = dayKey(now + 24 * HOUR);
    return `${fmtTime(new Date(t).toISOString())}${d === today ? "" : d === tomorrow ? " tomorrow" : ` ${weekday(t)}`}`;
  };
  const say = next.length
    ? `${next[0].type === "high" ? "Rising" : "Falling"}: ${next[0].type} ${ft(next[0].ft)} at ${when(next[0].t)}` +
      (next[1] ? `, then ${next[1].type} ${ft(next[1].ft)} at ${when(next[1].t)}.` : ".")
    : "";
  // Label turns that have room, upcoming ones first: on a phone, four turns in a day would overlap.
  const room = (narrow ? 0.24 : 0.12) * (t1 - t0), turns: typeof ev = [];
  const inView = ev.filter((e) => e.t >= t0 && e.t <= t1);
  for (const e of [...inView.filter((e) => e.t > now), ...inView.filter((e) => e.t <= now).reverse()])
    if (turns.every((k) => Math.abs(k.t - e.t) >= room)) turns.push(e);
  // Midnights inside the window, to mark where each day starts.
  const days: number[] = [];
  for (let t = Math.ceil(t0 / HOUR) * HOUR; t <= t1; t += HOUR) if (dayKey(t) !== dayKey(t - HOUR)) days.push(t);
  const pct = (t: number) => `${Math.min(96, Math.max(4, (x(t) / W) * 100)).toFixed(2)}%`;

  return (
    <section className="tide" aria-labelledby="tide-h">
      <p className="tide-say"><span id="tide-h" className="eyebrow">{`Tide, ${strip.name}`}</span>{say}</p>
      <div className="tide-plot" aria-hidden="true">
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
          {days.map((t) => <line key={t} className="tide-day" x1={x(t)} x2={x(t)} y1={0} y2={H} />)}
          <path className="tide-fill" d={`${path(now, t1)}L${W},${H} L${x(now).toFixed(1)},${H} Z`} />
          <path className="tide-past" d={path(t0, now)} />
          <path className="tide-next" d={path(now, t1)} />
          <line className="tide-now" x1={x(now)} x2={x(now)} y1={0} y2={H} />
        </svg>
        <span className="tide-dot" style={{ left: `${(x(now) / W) * 100}%`, top: `${(y(level(ev, now)) / H) * 100}%` }} />
        {days.map((t) => <span key={t} className="tide-daylabel" style={{ left: `${(x(t) / W) * 100}%` }}>{weekday(t)}</span>)}
      </div>
      <div className="tide-turns" aria-hidden="true">
        {turns.map((e) => (
          <span key={e.t} style={{ left: pct(e.t) }} data-past={e.t < now ? "" : undefined}>
            <b>{`${e.type === "high" ? "High" : "Low"} ${ft(e.ft)}`}</b>{fmtTime(e.time)}
          </span>
        ))}
      </div>
      <p className="tide-src">
        {"NOAA predictions. Wind can push the water well above or below them. "}
        <a href={`https://tidesandcurrents.noaa.gov/stationhome.html?id=${strip.station}`}>{`${strip.name} at NOAA`}</a>
      </p>
    </section>
  );
}
