// Refreshes "now" readings (air temp) from the source on page load, so they aren't up to 3 hours behind the
// scheduled build (0015). Anything that goes wrong leaves the built value in place, which already says its time.
import { nowRowText, nowTileSub } from "./format";
import type { Now } from "./types";

type Live = Now & { kind: "tile" | "row"; unit: string; where?: string };

const MAX_AGE_MS = 4 * 3600_000;   // matches NOW_MAX_AGE in msc/build.py
const localDay = (iso: string) => new Date(iso).toLocaleDateString("en-US", { timeZone: "America/Chicago" });

async function latest(url: string): Promise<{ c: number; time: string } | null> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 8000);
  try {
    const res = await fetch(url, { signal: ctl.signal });
    if (!res.ok) return null;
    const p = (await res.json())?.properties;
    const c = p?.temperature?.value;
    return typeof c === "number" && p.timestamp ? { c, time: p.timestamp } : null;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function apply(el: HTMLElement, built: Live, obs: { c: number; time: string }) {
  const t = new Date(obs.time).getTime();
  if (t <= new Date(built.time).getTime() || Date.now() - t > MAX_AGE_MS) return;
  const value = built.unit === "°F" ? obs.c * 9 / 5 + 32 : obs.c;
  // Today's range only carries over if the new reading is from the same local day.
  const sameDay = localDay(obs.time) === localDay(built.time) && built.lo !== undefined && built.hi !== undefined;
  const n: Now = { ...built, value, display: `${Math.round(value)}${built.unit}`, time: obs.time,
    lo: sameDay ? Math.min(built.lo!, value) : undefined, hi: sameDay ? Math.max(built.hi!, value) : undefined };
  const text = built.kind === "tile" ? nowTileSub(built.where ?? "", n, built.unit) : nowRowText(n, built.unit);
  el.querySelector<HTMLElement>("[data-live-value]")?.replaceChildren(String(Math.round(value)));
  (el.matches("[data-live-text]") ? el : el.querySelector<HTMLElement>("[data-live-text]"))?.replaceChildren(text);
  el.dataset.liveUpdated = "";
}

const els = [...document.querySelectorAll<HTMLElement>("[data-live]")];
const byUrl = new Map<string, HTMLElement[]>();
for (const el of els) {
  const url = (JSON.parse(el.dataset.live!) as Live).url;
  if (url) byUrl.set(url, [...(byUrl.get(url) ?? []), el]);
}
for (const [url, group] of byUrl) {
  latest(url).then((obs) => { if (obs) group.forEach((el) => apply(el, JSON.parse(el.dataset.live!), obs)); });
}
