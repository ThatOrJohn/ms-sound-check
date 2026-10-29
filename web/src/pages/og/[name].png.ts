// One share image per page, rebuilt with the data every run: og/index.png (Coast), og/<persona>.png,
// og/station-<slug>.png and og/about.png. Base.astro points og:image at them.
import type { APIRoute, GetStaticPaths } from "astro";
import { loadHistory, loadLatest } from "../../lib/data";
import { bandWords, fmtDate, fmtTime, href } from "../../lib/format";
import { render, type Card } from "../../lib/og";
import { INPUT_KINDS } from "../../lib/types";
import { readoutTiles, split, type Tile } from "../../lib/readouts";
import { soundStrip } from "../../lib/strip";

export const getStaticPaths = (() => {
  const data = loadLatest();
  return [
    ...data.personas.map((p) => ({ params: { name: p.id === "general" ? "index" : p.id }, props: { persona: p.id } })),
    ...data.cards.filter((c) => !INPUT_KINDS.includes(c.kind)).map((c) => ({ params: { name: `station-${c.slug}` }, props: { station: c.id } })),
    { params: { name: "about" }, props: {} },
  ];
}) satisfies GetStaticPaths;

export const GET: APIRoute = async ({ props }) => {
  const data = loadLatest();
  const stamp = `Updated ${fmtDate(data.generated_at, { month: "short", day: "numeric", timeZone: "America/Chicago" })}, ${fmtTime(data.generated_at)} CT`;
  let card: Card;
  if (props.persona) {
    const p = data.personas.find((x) => x.id === props.persona)!;
    card = { eyebrow: `${data.region.name} · ${p.label}`, headline: data.headlines[p.id], stamp,
      tiles: readoutTiles(data, (slug) => href(`station/${slug}/`)) };
    // The home image is the whole record: the history pictures and how many years they cover (decision 0028).
    const stripes = p.id === "general" && data.history ? data.history.home.map((s) => loadHistory(s.slug)).filter((x) => x?.years.length) : [];
    // A persona with `share: strip` shows the Sound west to east instead of the tiles (decision 0037).
    const strip = p.share === "strip" ? soundStrip(data) : null;
    if (strip) card = { ...card, tiles: [], strip };
    if (stripes.length) card = { ...card, tiles: [], stripes: stripes as NonNullable<typeof stripes[0]>[],
      // Counted from the pictures shown, which can start later than the region's record (0036).
      headline: `${+data.asof.slice(0, 4) - Math.min(...stripes.map((x) => x!.years[0].year))} years of the ${data.region.name}, one row per year` };
  } else if (props.station) {
    const c = data.cards.find((x) => x.id === props.station)!;
    const tiles: Tile[] = Object.entries(c.vars).filter(([, r]) => r.display && !r.stale && !r.suspect && !c.retired).map(([vn, r]) => {
      const [value, unit] = split(r.display!);
      // The daily air temp is an average, as the station page says.
      const label = `${data.variables[vn]?.label ?? vn}${vn === "air_temp" ? ", daily avg" : ""}`;
      return { label, value, unit, sub: bandWords(vn, r.band) };
    });
    card = { eyebrow: c.short !== c.name ? `${data.region.name} · ${c.short}` : data.region.name, stamp, tiles,
      headline: tiles.length ? c.name : `${c.name}: no recent readings` };
  } else {
    card = { eyebrow: data.region.name, stamp, tiles: [],
      headline: "Free, plain-language conditions for the Mississippi Sound, from USGS, NOAA, the National Weather Service, MDEQ and MDMR." };
  }
  return new Response(new Uint8Array(await render(card)), { headers: { "Content-Type": "image/png" } });
};
