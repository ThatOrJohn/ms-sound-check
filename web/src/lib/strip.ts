// The Sound west to east (decision 0037): every salinity station placed by longitude, today's readings blended into
// one bar and the typical (median for this time of year) in a fainter one. Shared by SoundStrip.astro and the share
// image, which color it their own way (CSS color-mix vs. RGB).
import type { Band, Latest } from "./types";
import { bandWords } from "./format";

export interface StripStation {
  id: string; short: string; slug: string;
  /** 0-100, west to east */
  x: number;
  /** Today's value when it can color the bar: live and not suspect, or a published estimate. */
  value: number | null;
  /** The reading itself, suspect or not (for the text alternative). */
  raw: number | null;
  /** "27.3", "~22 est.", "37.4?" or "no reading" */
  display: string;
  status: "live" | "estimate" | "suspect" | "none";
  typical: number | null;
  band?: Band;
}
export interface Strip {
  stations: StripStation[];
  /** Gradient stops for today: only stations with a value; the bar is blank outside the first and last of them. */
  today: { x: number; v: number }[];
  typical: { x: number; v: number }[];
  /** "Much saltier than usual at Pearl River mouth; a bit saltier than usual at West Sound; about normal at Biloxi Back Bay." */
  summary: string;
  /** Screen-reader text for the bars: every station west to east, today and typical. */
  label: string;
  season: string;
}

const PAD = 3;   // % of the bar kept clear at each end so the end stations' markers aren't cut off
const ppt = (v: number) => v.toFixed(1);
const words = (xs: string[]) => xs.length <= 2 ? xs.join(" and ") : `${xs.slice(0, -1).join(", ")} and ${xs.at(-1)}`;

export function soundStrip(data: Latest): Strip | null {
  // Retired sensors only count while we publish an estimate for them, as on the map.
  const cards = data.cards.filter((c) => (c.kind === "sound" || c.kind === "estuary") && c.vars.salinity
    && !(c.retired && !c.vars.salinity.estimate));
  if (cards.length < 2) return null;
  const lons = cards.map((c) => c.lon), w = Math.min(...lons), e = Math.max(...lons);
  const stations: StripStation[] = cards.map((c) => {
    const r = c.vars.salinity;
    const live = r.value !== undefined && !r.stale && !c.retired;
    const status: StripStation["status"] = live ? (r.suspect ? "suspect" : "live") : r.estimate ? "estimate" : "none";
    const value = status === "live" ? r.value! : status === "estimate" ? r.estimate!.value : null;
    const display = status === "live" ? ppt(r.value!) : status === "suspect" ? `${ppt(r.value!)}?`
      : status === "estimate" ? `~${Math.round(r.estimate!.value)} est.` : "no reading";
    return { id: c.id, short: c.short, slug: c.slug, x: PAD + ((c.lon - w) / Math.max(1e-6, e - w)) * (100 - 2 * PAD),
      value, raw: live ? r.value! : null, display, status, typical: r.normal?.p50 ?? null, band: status === "live" ? r.band : undefined };
  }).sort((a, b) => a.x - b.x);

  const today = stations.filter((s) => s.value !== null).map((s) => ({ x: s.x, v: s.value! }));
  const typical = stations.filter((s) => s.typical !== null).map((s) => ({ x: s.x, v: s.typical! }));

  // One plain sentence in the readings table's own band words, strongest first, so it can't read stronger than they do.
  const live = stations.filter((s) => s.status === "live" && s.band);
  const groups = (["high", "above", "normal", "below", "low"] as Band[])
    .map((b) => ({ words: bandWords("salinity", b), at: live.filter((s) => s.band === b).map((s) => s.short) })).filter((g) => g.at.length);
  let summary: string;
  if (!live.length) summary = "No station has a usable reading right now.";
  else if (groups.length === 1) summary = live.length === 1 ? `${groups[0].words} at ${live[0].short}, the only station reporting.`
    : `${groups[0].words} at all ${live.length} stations reporting, from ${live[0].short} to ${live.at(-1)!.short}.`;
  else summary = groups.map((g, i) => `${i ? g.words[0].toLowerCase() + g.words.slice(1) : g.words} at ${words(g.at)}`).join("; ") + ".";
  const odd = stations.filter((s) => s.status === "suspect").map((s) => s.short);
  if (odd.length) summary += odd.length > 1 ? ` The readings at ${words(odd)} may be sensor problems and are left out of the colors.`
    : ` The reading at ${odd[0]} may be a sensor problem and is left out of the colors.`;

  const label = `Salinity from west to east: ` + stations.map((s) =>
    `${s.short} ${s.status === "none" ? "no reading" : s.status === "suspect" ? `${ppt(s.raw!)} ppt, possibly a sensor problem`
      : s.status === "estimate" ? `about ${Math.round(s.value!)} ppt, estimated` : `${ppt(s.value!)} ppt`}` +
    (s.typical !== null ? `, typically ${ppt(s.typical)}` : "")).join("; ") + ".";
  return { stations, today, typical, summary, label, season: data.season };
}

/** Label rows, so no leader line crosses a label at any width. West-half labels sit above the bar and run right
 *  from their station; east-half labels sit below and run left. In each half the station nearer the middle takes the
 *  row nearest the bar, so the leaders of the outer stations pass west (or east) of every label they cross. */
export function labelRows(stations: StripStation[]) {
  const west = stations.filter((s) => s.x < 50).sort((a, b) => b.x - a.x);
  const east = stations.filter((s) => s.x >= 50).sort((a, b) => a.x - b.x);
  return { above: west.map((station, row) => ({ station, row })), below: east.map((station, row) => ({ station, row })) };
}
