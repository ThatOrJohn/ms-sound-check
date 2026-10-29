// The readout strip: a handful of numbers that sum up the Sound right now. Shared by the home and persona pages
// and their share images, so the picture and the page never disagree.
import type { Latest, YearDots } from "./types";
import { bandWords, nowTileSub } from "./format";

export type Tile = { label: string; value: string; unit: string; sub: string; percentile?: number; href?: string; live?: string;
  /** River flow: every year for today's date, shown instead of the meter (decision 0032). */
  years?: YearDots; varName?: string };

/** "1,491 cfs" -> ["1,491", "cfs"], so the number and its unit can be styled apart. */
export const split = (d: string) => { const m = d.replace(" past 7 days", "").match(/^(~?[\d.,–-]+)\s*(.*)$/); return m ? [m[1], m[2]] : [d, ""]; };

export function readoutTiles(data: Latest, siteHref: (slug: string) => string): Tile[] {
  const live = (c: (typeof data.cards)[number], vn: string) => {
    const r = c.vars[vn]; return r && r.display && r.value !== undefined && !r.stale && !r.suspect && !c.retired ? r : null;
  };
  const tiles: Tile[] = [];
  const near = (where: string, vn: string, band?: any) => { const w = bandWords(vn, band); return w ? `${where}, ${w.toLowerCase()}` : where; };
  const sal = data.cards.filter((c) => c.kind === "sound").map((c) => live(c, "salinity")?.value).filter((v): v is number => v !== undefined);
  if (sal.length) {
    const sorted = [...sal].sort((a, b) => a - b), mid = sorted[Math.floor(sorted.length / 2)];
    tiles.push({ label: "Sound salinity", value: mid.toFixed(1), unit: "ppt",
      sub: sal.length > 1 ? `${sorted[0].toFixed(0)}–${sorted.at(-1)!.toFixed(0)} across ${sal.length} stations` : "one station reporting" });
  }
  const wt = data.cards.filter((c) => c.kind === "sound").map((c) => ({ c, r: live(c, "water_temp") })).find((x) => x.r);
  if (wt) { const [v, u] = split(wt.r!.display!); tiles.push({ label: "Water temp", value: v, unit: u, sub: near(wt.c.short, "water_temp", wt.r!.band), percentile: wt.r!.percentile, href: siteHref(wt.c.slug) }); }
  for (const c of data.cards.filter((c) => c.kind === "river" && !c.minor)) {
    const r = live(c, "flow"); if (!r) continue;
    const [v, u] = split(r.display!);
    tiles.push({ label: `${c.short} flow`, value: v, unit: u, sub: bandWords("flow", r.band), percentile: r.percentile, href: siteHref(c.slug),
      years: r.years, varName: "flow" });
  }
  const rainCard = data.cards.find((c) => c.kind === "rain" && /biloxi|local/i.test(c.id)) ?? data.cards.find((c) => c.kind === "rain");
  const rr = rainCard && rainCard.vars.rain;
  if (rainCard && rr?.display) { const [v, u] = split(rr.display); const fc = data.rain_forecast[rainCard.id]?.total;
    tiles.push({ label: "Rain, 7 days", value: v, unit: u, sub: fc ? `${fc} forecast next 7` : bandWords("rain", rr.band), percentile: rr.percentile, href: siteHref(rainCard.slug) }); }
  const wx = data.cards.find((c) => c.kind === "weather");
  const at = wx && live(wx, "air_temp");
  // The daily value is an average (a cool morning drags it down), so lead with the newest observation when there is one.
  if (wx && at?.now) { tiles.push({ label: "Air temp", value: String(Math.round(at.now.value)), unit: at.unit!, sub: nowTileSub(wx.short, at.now, at.unit!), href: siteHref(wx.slug),
    live: JSON.stringify({ kind: "tile", where: wx.short, unit: at.unit, ...at.now }) }); }
  else if (wx && at) { const [v, u] = split(at.display!); tiles.push({ label: "Air temp, daily avg", value: v, unit: u, sub: near(wx.short, "air_temp", at.band), percentile: at.percentile, href: siteHref(wx.slug) }); }
  return tiles;
}
