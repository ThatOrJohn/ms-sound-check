import { useEffect, useRef, useState } from "react";
import type { CanvasSource, Map as MLMap, MapLayerMouseEvent, Popup, StyleSpecification } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import cssUrl from "maplibre-gl/dist/maplibre-gl.css?url";

import type { ReferenceSite, Replay, ReplayIndex, ReplayWind, ReplayYear, SatelliteLayer } from "../lib/types";
import { beachDetail } from "../lib/format";
import { hexRGB, salinityRGB } from "../lib/salinity";
import { Sketch } from "../lib/sketch";
import { Motion, windWords, type Wind } from "../lib/motion";

export interface MapStation {
  id: string; short: string; kind: string; lon: number; lat: number; href: string;
  salinity: number | null; display: string; status: "live" | "suspect" | "quiet" | "estimate"; alert: boolean;
}
export interface MapRiver { id: string; name: string; osmNames: string[]; display: string; band?: string; percentile?: number }

interface Props {
  stations: MapStation[]; rivers: MapRiver[]; basemapBase: string;
  /** OSM names of rivers with no flow gauge: drawn thin and named, never widened. */
  ungauged?: string[];
  beachesUrl?: string; personaId?: string; defaultLayers?: string[];
  /** The page has a Beaches section, so beach popups can link to each beach's row (#beach-<id>). */
  beachLinks?: boolean;
  /** Satellite layers and where their PNGs live (the region's data folder). */
  satellite?: Record<string, SatelliteLayer>; dataBase?: string;
  /** The last 30 days, for the replay slider. */
  replay?: Replay;
  /** Years with a replay file (fetched from `${dataBase}replay/<year>.json` when picked) and days to jump to. */
  replayIndex?: ReplayIndex | null;
  /** Every salinity station the replay can draw, retired ones included (they're shown on days they had readings). */
  replaySites?: MapStation[];
  /** Reference sites past the map's east edge (Dauphin Island): a chip at that edge, never a station dot. */
  reference?: ReferenceSite[];
}
const NO_RIVERS: string[] = [];

type LayerKey = "depth" | "contours" | "salinity" | "rivers" | "wind" | "beaches" | "clarity" | "sst";
const LAYERS: { key: LayerKey; label: string; note?: string }[] = [
  { key: "beaches", label: "Beach status" },
  { key: "depth", label: "Depth shading" },
  { key: "contours", label: "Depth contours (ft)" },
  { key: "rivers", label: "River flow" },
  { key: "wind", label: "Wind", note: "Wind over the middle of the Sound, shown across the map. Not a water current." },
  { key: "salinity", label: "Salinity sketch", note: "Estimated between a handful of stations. A sketch, not a measurement." },
  { key: "clarity", label: "Water clarity (satellite)" },
  { key: "sst", label: "Surface temp (satellite)" },
];
const DEFAULTS: Record<LayerKey, boolean> = { depth: true, contours: true, rivers: true, wind: false, salinity: false, beaches: false, clarity: false, sst: false };
/** Layers that fill the water: only one at a time, since each hides the others. */
const FILLS: LayerKey[] = ["salinity", "clarity", "sst"];
const SAT_KEYS = ["clarity", "sst"] as const;
const VIEW: [[number, number], [number, number]] = [[-89.72, 30.13], [-88.42, 30.5]];
export const OFM = "https://tiles.openfreemap.org";
const FLOW_WORDS: Record<string, string> = { low: "very low", below: "a bit low", normal: "normal", above: "a bit high", high: "very high" };

interface Meta { bounds: [number, number, number, number]; mask_size: [number, number]; attribution: string }

// ---------- colors from the site's CSS tokens
function tokens() {
  const cs = getComputedStyle(document.documentElement);
  const v = (n: string) => cs.getPropertyValue(n).trim();
  const dark = cs.getPropertyValue("color-scheme").trim() === "dark";
  return {
    dark, land: v("--land"), water: v("--water"), sky: v("--sky"), paper: v("--paper"), ink: v("--ink"),
    soft: v("--ink-soft"), rule: v("--rule"), fresh: v("--fresh"), brackish: v("--brackish"), gulf: v("--gulf"),
    red: v("--marker-red"), cool: v("--sst-cool"), mild: v("--sst-mild"), warm: v("--sst-warm"), wind: v("--wind"),
  };
}
type Tokens = ReturnType<typeof tokens>;
const rgb = hexRGB;
const css = (c: number[]) => `rgb(${c.join(",")})`;
const mix = (x: number[], y: number[], k: number) => x.map((xi, i) => Math.round(xi + (y[i] - xi) * k));
/** Gray level 1-255 from a satellite PNG -> color. Clarity runs clear (Gulf water) to murky (river water). */
function satRGB(key: "clarity" | "sst", k: number, t: Tokens): number[] {
  if (key === "clarity") return mix(rgb(t.gulf), rgb(t.fresh), k);
  return k < 0.5 ? mix(rgb(t.cool), rgb(t.mild), k * 2) : mix(rgb(t.mild), rgb(t.warm), (k - 0.5) * 2);
}
const BAND = (pct: number | null | undefined) =>
  pct == null ? undefined : pct <= 10 ? "low" : pct >= 90 ? "high" : pct < 25 ? "below" : pct > 75 ? "above" : "normal";
const riverWidth = (pct: number | null | undefined) => 1.5 + ((pct ?? 50) / 100) * 5;
const fmtDay = (d: string, year = false) => new Date(d + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", ...(year ? { year: "numeric" } : {}) });
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAY_HASH = /^#(\d{4})-(\d{2})-(\d{2})$/;

/** What the replay is showing: the last 30 days (from latest.json), or one calendar year (fetched on demand). */
interface ReplaySet { year: number | null; days: string[]; salinity: Replay["salinity"]; flow_pct: Replay["flow_pct"]; wind: ReplayWind | null }
function yearSet(f: ReplayYear): ReplaySet {
  const t0 = Date.parse(f.start + "T00:00:00Z");
  const days = Array.from({ length: f.n }, (_, i) => new Date(t0 + i * 86400_000).toISOString().slice(0, 10));
  return { year: f.year, days, salinity: f.salinity, flow_pct: f.flow_pct, wind: f.wind };
}
const windAt = (w: ReplayWind | null | undefined, i: number): Wind | null =>
  w && w.u[i] != null && w.v[i] != null ? { u: w.u[i]!, v: w.v[i]! } : null;
/** The day's wind; for today, the newest of the last few days (the wind feed runs about a day behind). */
function windOf(set: ReplaySet | null, i: number, today: boolean): { w: Wind; day: string } | null {
  if (!set) return null;
  for (let k = i; k >= (today ? Math.max(0, i - 2) : i); k--) { const w = windAt(set.wind, k); if (w) return { w, day: set.days[k] }; }
  return null;
}

// ---------- style: OpenFreeMap vector tiles, drawn in our palette
function baseStyle(t: Tokens): StyleSpecification {
  return {
    version: 8,
    glyphs: `${OFM}/fonts/{fontstack}/{range}.pbf`,
    sources: {
      omt: { type: "vector", url: `${OFM}/planet`,
        attribution: '<a href="https://openfreemap.org">OpenFreeMap</a> © <a href="https://www.openmaptiles.org/">OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' },    },
    layers: [
      { id: "land", type: "background", paint: { "background-color": t.land } },
      { id: "marsh", type: "fill", source: "omt", "source-layer": "landcover", filter: ["==", ["get", "class"], "wetland"],
        paint: { "fill-color": t.brackish, "fill-opacity": t.dark ? 0.18 : 0.14 } },
      { id: "water", type: "fill", source: "omt", "source-layer": "water", paint: { "fill-color": t.water } },
      { id: "waterway", type: "line", source: "omt", "source-layer": "waterway",
        paint: { "line-color": t.water, "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.5, 12, 1.5] } },
      { id: "roads", type: "line", source: "omt", "source-layer": "transportation",
        filter: ["in", ["get", "class"], ["literal", ["motorway", "trunk"]]],
        paint: { "line-color": t.soft, "line-opacity": 0.25, "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.5, 12, 1.4] } },
      { id: "places", type: "symbol", source: "omt", "source-layer": "place",
        filter: ["in", ["get", "class"], ["literal", ["city", "town"]]],
        layout: { "text-field": ["get", "name:en"], "text-font": ["Noto Sans Italic"], "text-size": 12 },
        paint: { "text-color": t.soft, "text-halo-color": t.land, "text-halo-width": 1.2 } },
      { id: "water-names", type: "symbol", source: "omt", "source-layer": "water_name",
        layout: { "text-field": ["get", "name:en"], "text-font": ["Noto Sans Italic"], "text-size": 12, "text-letter-spacing": 0.05 },
        paint: { "text-color": t.soft, "text-halo-color": t.water, "text-halo-width": 1 } },
    ],
  };
}

// ---------- satellite layer: data PNG -> theme colors, resampled onto the water mask so the coast stays crisp
async function satImage(meta: Meta, maskUrl: string, key: "clarity" | "sst", layer: SatelliteLayer, url: string, t: Tokens): Promise<string | null> {
  const load = async (src: string) => { const i = new Image(); i.crossOrigin = "anonymous"; i.src = src; await i.decode(); return i; };
  const [mask, sat] = await Promise.all([load(maskUrl), load(url)]);
  const [w, h] = [mask.width, mask.height];
  const cv = document.createElement("canvas");
  cv.width = w; cv.height = h;
  const ctx = cv.getContext("2d", { willReadFrequently: true })!;
  ctx.drawImage(mask, 0, 0);
  const m = ctx.getImageData(0, 0, w, h);
  ctx.clearRect(0, 0, w, h);
  const [W, S, E, N] = meta.bounds, [sw, ss, se, sn] = layer.bounds;
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(sat, ((sw - W) / (E - W)) * w, ((N - sn) / (N - S)) * h, ((se - sw) / (E - W)) * w, ((sn - ss) / (N - S)) * h);
  const d = ctx.getImageData(0, 0, w, h);
  const colors = new Map<number, number[]>();
  for (let i = 0; i < d.data.length; i += 4) {
    if (m.data[i] < 128 || d.data[i + 3] < 128) { d.data[i + 3] = 0; continue; }   // land, or no clear view
    // Smoothing premultiplies by alpha at the edges; undo it before reading the value.
    const g = Math.min(255, Math.round((d.data[i] * 255) / d.data[i + 3]));
    let c = colors.get(g);
    if (!c) { c = satRGB(key, Math.max(0, g - 1) / 254, t); colors.set(g, c); }
    d.data[i] = c[0]; d.data[i + 1] = c[1]; d.data[i + 2] = c[2]; d.data[i + 3] = 215;
  }
  ctx.putImageData(d, 0, 0);
  return cv.toDataURL("image/png");
}

function stationData(stations: MapStation[], t: Tokens) {
  return {
    type: "FeatureCollection" as const,
    features: stations.map((s) => ({
      type: "Feature" as const, geometry: { type: "Point" as const, coordinates: [s.lon, s.lat] },
      properties: {
        href: s.href, label: `${s.short}\n${s.display}${s.status === "suspect" ? " (check)" : ""}`,
        color: (s.status === "live" || s.status === "estimate") && s.salinity !== null ? css(salinityRGB(s.salinity, t)) : t.rule,
        est: s.status === "estimate", alert: s.alert,
      },
    })),
  };
}
/** Popup for one beach segment. Built from DOM nodes, not HTML, since the names come from the feature service. */
function beachPopup(p: Record<string, any>, link: boolean): HTMLElement {
  const box = document.createElement("div");
  const add = (tag: string, text: string, cls?: string) => {
    const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; box.append(n); return n;
  };
  add("strong", p.name ?? "Beach");
  if (p.location) add("span", p.location, "beach-pop-where");
  add("p", beachDetail(p));
  if (link && p.id) (add("a", "Details in Beaches below") as HTMLAnchorElement).href = `#beach-${p.id}`;
  return box;
}
/** Resolves once the page has loaded and gone idle (or 2 s on) and the map box is near the screen, or a replay day
 *  is in the address (#YYYY-MM-DD, which scrolls to the map once it's ready). The map is the heaviest thing on the
 *  page, so the headline and readings paint first. */
function whenIdleAndNear(node: Element): Promise<void> {
  const idle = new Promise<void>((done) => {
    const go = () => ("requestIdleCallback" in window ? requestIdleCallback(() => done(), { timeout: 2000 }) : setTimeout(done, 200));
    if (document.readyState === "complete") go(); else addEventListener("load", go, { once: true });
  });
  const near = new Promise<void>((done) => {
    const finish = () => { io.disconnect(); removeEventListener("hashchange", onHash); done(); };
    const onHash = () => { if (DAY_HASH.test(location.hash)) finish(); };
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) finish(); }, { rootMargin: "200px" });
    io.observe(node);
    addEventListener("hashchange", onHash);
    onHash();
  });
  return Promise.all([idle, near]).then(() => {});
}
function loadCss(url: string): Promise<void> {
  const found = document.querySelector<HTMLLinkElement>(`link[href="${url}"]`);
  if (found) return Promise.resolve();
  return new Promise((done) => {
    const link = Object.assign(document.createElement("link"), { rel: "stylesheet", href: url });
    link.onload = link.onerror = () => done();
    document.head.append(link);
  });
}
function riverWidths(rivers: MapRiver[], pct: (r: MapRiver) => number | null | undefined): any[] {
  const match: any[] = ["match", ["get", "name"]];
  rivers.forEach((r) => r.osmNames.forEach((n) => match.push(n, riverWidth(pct(r)))));
  match.push(0);
  return match;
}

/** Each persona starts from its own layer set (region config); choices are remembered per persona. */
function personaDefaults(defaultLayers?: string[]): Record<LayerKey, boolean> {
  if (!defaultLayers) return { ...DEFAULTS };
  return Object.fromEntries(LAYERS.map((l) => [l.key, defaultLayers.includes(l.key)])) as Record<LayerKey, boolean>;
}
function readLayers(personaId: string | undefined, defaultLayers?: string[]): Record<LayerKey, boolean> {
  const base = personaDefaults(defaultLayers);
  try { return { ...base, ...JSON.parse(localStorage.getItem(`sc-layers:${personaId ?? "general"}`) || "{}") }; } catch { return base; }
}

export default function SoundMap({ stations, rivers, ungauged = NO_RIVERS, basemapBase, beachesUrl, personaId, defaultLayers,
  beachLinks = false, satellite, dataBase, replay, replayIndex, replaySites, reference }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const tRef = useRef<Tokens | null>(null);
  const layersRef = useRef<Record<LayerKey, boolean>>(personaDefaults(defaultLayers));
  const replayingRef = useRef(false);
  const sketchRef = useRef<Sketch | null>(null);
  const motionRef = useRef<Motion | null>(null);
  const recent: ReplaySet | null = replay ? { year: null, ...replay } : null;
  const [set, setSet] = useState<ReplaySet | null>(recent);
  const last = set ? set.days.length - 1 : 0;
  const [frame, setFrame] = useState(last);       // index into set.days; the last day of the recent set is "now"
  const [playing, setPlaying] = useState(false);
  const [loadingYear, setLoadingYear] = useState(false);
  const [sketched, setSketched] = useState(true);   // false: too few stations that day to draw the fill
  const [said, setSaid] = useState("");             // screen reader line for the day shown
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>(() => personaDefaults(defaultLayers));
  const [meta, setMeta] = useState<Meta | null | undefined>(undefined);   // undefined = loading, null = no basemap
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  useEffect(() => setPanelOpen(window.matchMedia("(min-width: 900px)").matches), []);

  useEffect(() => { const l = readLayers(personaId, defaultLayers); layersRef.current = l; setLayers(l); }, [personaId, defaultLayers]);

  // Build the map once; restyle on theme change.
  useEffect(() => {
    let cancelled = false;
    let cleanup = () => {};
    (async () => {
      if (!el.current) return;
      await whenIdleAndNear(el.current);
      if (cancelled) return;
      // The stylesheet is linked here, not imported, so Astro doesn't put it in <head> where it holds up the first paint.
      const [ml] = await Promise.all([import("maplibre-gl"), loadCss(cssUrl)]);
      ml.setWorkerUrl(workerUrl);
      const m: Meta | null = await fetch(`${basemapBase}meta.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
      if (cancelled || !el.current) return;
      setMeta(m);
      let t = tokens();
      const map = new ml.Map({
        container: el.current, style: baseStyle(t), bounds: VIEW, fitBoundsOptions: { padding: 12 },
        // Stay inside the depth data, and stop zooming where one 90 m depth pixel would start to blur.
        maxBounds: [[-90.0, 29.9], [-88.1, 30.72]], minZoom: 8, maxZoom: 12.5,
        dragRotate: false, pitchWithRotate: false, touchPitch: false, cooperativeGestures: true,
        // Labels are matched across redraws by their text, so a changed value ("15.3 ppt" -> "16.1 ppt") would fade
        // out and back in on every replay step. No fade: they just update.
        fadeDuration: 0,
        attributionControl: { compact: true },
      });
      mapRef.current = map;
      // The canvas is focusable (arrow keys pan, +/- zoom). Describe it, and point to the list with the same readings.
      map.getCanvas().setAttribute("aria-label",
        "Map of the Mississippi Sound with monitoring stations colored by salinity. The same readings are listed below the map.");
      map.touchZoomRotate.disableRotation();
      map.addControl(new ml.NavigationControl({ showCompass: false }), "bottom-right");
      map.on("error", (e) => { if (String(e?.error?.message || "").includes("planet")) setFailed(true); });

      const addOverlays = async () => {
        t = tokens();
        tRef.current = t;
        if (m) {
          const corners: [[number, number], [number, number], [number, number], [number, number]] =
            [[m.bounds[0], m.bounds[3]], [m.bounds[2], m.bounds[3]], [m.bounds[2], m.bounds[1]], [m.bounds[0], m.bounds[1]]];
          map.addSource("depth", { type: "image", url: `${basemapBase}depth-${t.dark ? "dark" : "light"}.png`, coordinates: corners });
          map.addLayer({ id: "depth", type: "raster", source: "depth", paint: { "raster-opacity": 0.95, "raster-fade-duration": 0 } }, "waterway");
          map.addSource("contours", { type: "geojson", data: `${basemapBase}contours.geojson`, attribution: m.attribution });
          map.addLayer({ id: "contours", type: "line", source: "contours",
            paint: { "line-color": t.ink, "line-opacity": ["interpolate", ["linear"], ["get", "depth_ft"], 6, 0.18, 40, 0.32], "line-width": 0.7 } }, "waterway");
          map.addLayer({ id: "contour-labels", type: "symbol", source: "contours", minzoom: 9.5,
            layout: { "symbol-placement": "line", "text-field": ["concat", ["to-string", ["get", "depth_ft"]], " ft"],
              "text-font": ["Noto Sans Regular"], "text-size": 10, "symbol-spacing": 320 },
            paint: { "text-color": t.soft, "text-halo-color": t.water, "text-halo-width": 1 } });
          // Every station the sketch may ever use, so each cell's distances are worked out once (decision 0033).
          if (!sketchRef.current) {
            const pts = [...stations, ...(replaySites ?? [])].filter((p, i, a) => a.findIndex((q) => q.id === p.id) === i);
            sketchRef.current = await Sketch.create(`${basemapBase}watermask.png`, m.bounds, pts).catch(() => null);
          }
          if (sketchRef.current) {
            map.addSource("salinity", { type: "canvas", canvas: sketchRef.current.canvas, coordinates: corners, animate: false });
            map.addLayer({ id: "salinity", type: "raster", source: "salinity", paint: { "raster-opacity": 0.85, "raster-fade-duration": 0 } }, "waterway");
          }
          for (const key of SAT_KEYS) {
            const layer = satellite?.[key];
            if (!layer || !dataBase) continue;
            const img = await satImage(m, `${basemapBase}watermask.png`, key, layer, `${dataBase}${layer.png}`, t).catch(() => null);
            if (!img) continue;
            map.addSource(key, { type: "image", url: img, coordinates: corners, attribution: "Satellite: NOAA CoastWatch" } as any);
            map.addLayer({ id: key, type: "raster", source: key, paint: { "raster-opacity": 0.9, "raster-fade-duration": 0 } }, "waterway");
          }
        }
        // Rivers: widen the real river lines by how hard they're running.
        const match = riverWidths(rivers, (r) => r.percentile);
        // River lines come from basemap prep (`python -m msc rivers`): at the Sound-wide zoom the vector tiles
        // keep only the Pearl.
        map.addSource("river-lines", { type: "geojson", data: `${basemapBase}rivers.geojson` });
        map.addLayer({ id: "rivers-ungauged", type: "line", source: "river-lines",
          filter: ["all", ["!", ["has", "label"]], ["in", ["get", "name"], ["literal", ungauged]]],
          layout: { "line-cap": "round", "line-join": "round" },
          paint: { "line-color": t.fresh, "line-opacity": 0.85, "line-width": 1.6, "line-dasharray": [3, 2.5] } }, "places");
        map.addLayer({ id: "rivers", type: "line", source: "river-lines",
          filter: ["all", ["!", ["has", "label"]], ["in", ["get", "name"], ["literal", rivers.flatMap((r) => r.osmNames)]]],
          layout: { "line-cap": "round", "line-join": "round" },
          paint: { "line-color": t.fresh, "line-opacity": 0.9, "line-width": match as any } }, "places");
        // Flow as motion (decision 0034): a light dash on each gauged river that marches at its flow percentile's pace.
        rivers.forEach((r, i) => map.addLayer({ id: `river-flow-${i}`, type: "line", source: "river-lines",
          filter: ["all", ["!", ["has", "label"]], ["in", ["get", "name"], ["literal", r.osmNames]]],
          layout: { "line-cap": "butt", "line-join": "round" },
          paint: { "line-color": t.paper, "line-opacity": t.dark ? 0.4 : 0.6, "line-width": 1.3, "line-dasharray": [0, 4, 3] } }, "places"));
        // Name every river we track, gauged or not, at its `label` point near the coast.
        map.addLayer({ id: "river-names", type: "symbol", source: "river-lines",
          // One name per river (not each West/East branch).
          filter: ["all", ["has", "label"], ["in", ["get", "name"], ["literal", [...rivers.map((r) => r.osmNames[0]), ...ungauged]]]],
          layout: { "text-field": ["get", "name"], "text-font": ["Noto Sans Italic"], "text-size": 11.5,
            "text-variable-anchor": ["left", "right"], "text-radial-offset": 0.5 },
          paint: { "text-color": t.soft, "text-halo-color": t.land, "text-halo-width": 1.4 } });

        map.addSource("stations", { type: "geojson", data: stationData(stations, t) });
        map.addLayer({ id: "station-ring", type: "circle", source: "stations", filter: ["==", ["get", "alert"], true],
          paint: { "circle-radius": 15, "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": t.red, "circle-stroke-width": 3 } });
        map.addLayer({ id: "stations", type: "circle", source: "stations",
          // Estimates are hollow rings in the estimated color; measured stations are solid.
          paint: { "circle-radius": ["case", ["get", "est"], 7.5, 9],
            "circle-color": ["case", ["get", "est"], t.paper, ["get", "color"]],
            "circle-stroke-color": ["case", ["get", "est"], ["get", "color"], t.paper],
            "circle-stroke-width": ["case", ["get", "est"], 3.5, 2.5] } });
        map.addLayer({ id: "station-labels", type: "symbol", source: "stations",
          layout: { "text-field": ["get", "label"], "text-font": ["Noto Sans Bold"], "text-size": 12.5, "text-anchor": "left",
            "text-offset": [1.1, 0], "text-justify": "left", "text-line-height": 1.25, "text-allow-overlap": false },
          paint: { "text-color": t.ink, "text-halo-color": t.paper, "text-halo-width": 1.6 } });
        if (beachesUrl) {
          // Beach segments by status; drawn wide so they read at Sound-wide zoom. Color plus a line pattern
          // (solid clear, dashed advisory, dotted closed) and a word on flagged ones, so color isn't the only cue.
          map.addSource("beaches", { type: "geojson", data: beachesUrl });
          const color = ["match", ["get", "status"], "closure", t.red, "advisory", getComputedStyle(document.documentElement).getPropertyValue("--amber").trim(), getComputedStyle(document.documentElement).getPropertyValue("--marker-green").trim()];
          map.addLayer({ id: "beaches", type: "line", source: "beaches",
            layout: { "line-cap": "round" },
            paint: { "line-color": color as any, "line-width": ["interpolate", ["linear"], ["zoom"], 8, 4, 12, 8], "line-opacity": 0.95,
              "line-dasharray": ["match", ["get", "status"], "closure", ["literal", [0.01, 1.6]], "advisory", ["literal", [1.6, 1.1]], ["literal", [1, 0]]] as any } }, "station-ring");
          // Label flagged segments at their midpoints: most are shorter than the word, so line placement drops it.
          const segs: any = await fetch(beachesUrl).then((r) => r.json()).catch(() => null);
          const mid = (c: [number, number][]) => c[Math.floor((c.length - 1) / 2)].map((v, i) => (v + c[Math.ceil((c.length - 1) / 2)][i]) / 2);
          map.addSource("beach-points", { type: "geojson", data: { type: "FeatureCollection", features: (segs?.features ?? [])
            .filter((f: any) => f.properties.status !== "clear" && f.geometry?.type === "LineString")
            .map((f: any) => ({ type: "Feature", properties: f.properties, geometry: { type: "Point", coordinates: mid(f.geometry.coordinates) } })) } });
          map.addLayer({ id: "beach-labels", type: "symbol", source: "beach-points",
            layout: { "text-field": ["match", ["get", "status"], "closure", "Closed", "Advisory"],
              "text-font": ["Noto Sans Bold"], "text-size": 11, "text-anchor": "top", "text-offset": [0, 0.7] },
            paint: { "text-color": t.ink, "text-halo-color": t.paper, "text-halo-width": 1.6 } });
          // An invisible, much wider copy of the segments to hover and tap: most are only a few pixels long.
          map.addLayer({ id: "beach-hit", type: "line", source: "beaches", layout: { "line-cap": "round" },
            paint: { "line-color": t.ink, "line-opacity": 0, "line-width": 22 } }, "station-ring");
        }
        if (m && sketchRef.current) {
          motionRef.current?.destroy();
          motionRef.current = new Motion(map, el.current!, sketchRef.current.isWater, m.bounds);
          motionRef.current.color = t.wind;
        }
        applyLayers(map, layersRef.current);
        setReady(true);
        setRedraw((n) => n + 1);   // repaint the day shown in the new style
      };

      map.on("load", addOverlays);
      map.on("click", "stations", (e) => { const h = e.features?.[0]?.properties?.href; if (h) window.location.assign(h); });
      map.on("mouseenter", "stations", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "stations", () => (map.getCanvas().style.cursor = ""));

      // Beach popups: hover where there's a mouse, tap anywhere; a tap pins one until the next tap off the beach.
      const popup = new ml.Popup({ closeButton: false, closeOnClick: false, focusAfterOpen: false, maxWidth: "260px", offset: 12, className: "beach-pop" });
      popupRef.current = popup;
      let pinned = false;
      const canHover = matchMedia("(hover: hover)").matches;
      const show = (e: MapLayerMouseEvent) => {
        const f = e.features?.[0];
        if (f) popup.setLngLat(e.lngLat).setDOMContent(beachPopup(f.properties, beachLinks)).addTo(map);
      };
      const onStation = (e: MapLayerMouseEvent) => map.getLayer("stations") && map.queryRenderedFeatures(e.point, { layers: ["stations"] }).length > 0;
      map.on("mousemove", "beach-hit", (e) => {
        if (onStation(e)) return;
        map.getCanvas().style.cursor = "pointer";
        if (canHover && !pinned) show(e);
      });
      map.on("mouseleave", "beach-hit", () => { map.getCanvas().style.cursor = ""; if (!pinned) popup.remove(); });
      map.on("click", (e) => {
        const hit = map.getLayer("beach-hit") && !onStation(e as MapLayerMouseEvent)
          ? map.queryRenderedFeatures(e.point, { layers: ["beach-hit"] })[0] : undefined;
        pinned = !!hit;
        if (hit) show({ ...e, features: [hit] } as MapLayerMouseEvent); else popup.remove();
      });

      const restyle = () => {
        setReady(false);
        // diff: false forces a full reload so "style.load" fires and the overlays are rebuilt in the new colors.
        map.once("style.load", addOverlays);
        map.setStyle(baseStyle(tokens()), { diff: false });
      };
      const mq = matchMedia("(prefers-color-scheme: dark)");
      mq.addEventListener("change", restyle);
      window.addEventListener("sc-theme-change", restyle);
      cleanup = () => {
        mq.removeEventListener("change", restyle); window.removeEventListener("sc-theme-change", restyle);
        motionRef.current?.destroy(); motionRef.current = null; map.remove();
      };
    })().catch(() => setFailed(true));
    return () => { cancelled = true; cleanup(); };
  }, [stations, rivers, ungauged, basemapBase, beachesUrl, beachLinks, personaId, defaultLayers, satellite, dataBase, replaySites]);
  const [redraw, setRedraw] = useState(0);

  /** While replaying a past day, today's-only layers (satellite fills, beaches, alert rings) are hidden so nothing mixes
   *  two dates. The salinity sketch and the wind are redrawn for the day shown, so they stay. */
  function applyLayers(map: MLMap, l: Record<LayerKey, boolean>) {
    const past = replayingRef.current;
    const vis = (on: boolean) => (on ? "visible" : "none");
    const set = (id: string, on: boolean) => { if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis(on)); };
    set("depth", l.depth); set("contours", l.contours); set("contour-labels", l.contours);
    set("salinity", l.salinity); set("clarity", l.clarity && !past); set("sst", l.sst && !past);
    set("rivers", l.rivers); set("rivers-ungauged", l.rivers);
    rivers.forEach((_, i) => set(`river-flow-${i}`, l.rivers));
    motionRef.current?.setShown({ wind: l.wind, rivers: l.rivers }); set("beaches", l.beaches && !past);
    set("beach-labels", l.beaches && !past); set("beach-hit", l.beaches && !past); set("station-ring", !past);
    if (!l.beaches || past) popupRef.current?.remove();
  }
  function toggle(key: LayerKey) {
    const next = { ...layers, [key]: !layers[key] };
    if (next[key] && FILLS.includes(key)) FILLS.forEach((k) => { if (k !== key) next[k] = false; });
    setLayers(next);
    layersRef.current = next;
    try { localStorage.setItem(`sc-layers:${personaId ?? "general"}`, JSON.stringify(next)); } catch { /* private mode */ }
    if (mapRef.current) applyLayers(mapRef.current, next);
  }

  // ---------- replay: redraw stations, the salinity sketch, rivers and wind for the day shown
  const today = !set || (set.year === null && frame === last);
  useEffect(() => {
    const map = mapRef.current, t = tRef.current;
    if (!map || !t || !ready || !map.getSource("stations")) return;
    const past = !today && !!set;
    replayingRef.current = past;
    const src = map.getSource("stations") as any;
    let values: Record<string, number | null>;
    let pct: (r: MapRiver) => number | null | undefined;
    if (!past) {
      src.setData(stationData(stations, t));
      values = Object.fromEntries(stations.filter((s) => s.status === "live").map((s) => [s.id, s.salinity]));
      pct = (r) => r.percentile;
    } else {
      // Measured values only, including stations retired since (shown on the days they reported).
      const sites = replaySites?.length ? replaySites : stations;
      const day = sites.flatMap((s) => {
        const v = set!.salinity[s.id]?.[frame] ?? null;
        if (v === null && s.status === "quiet" && s.display === "offline") return [];
        return [{ ...s, salinity: v, status: v === null ? "quiet" : "live", display: v === null ? "no reading" : `${v.toFixed(1)} ppt`, alert: false } as MapStation];
      });
      src.setData(stationData(day, t));
      values = Object.fromEntries(Object.entries(set!.salinity).map(([id, vs]) => [id, vs[frame]]));
      pct = (r) => set!.flow_pct[r.id]?.[frame];
    }
    map.setPaintProperty("rivers", "line-width", riverWidths(rivers, pct) as any);
    const sk = sketchRef.current, cs = map.getSource("salinity") as CanvasSource | undefined;
    if (sk && cs) {
      setSketched(sk.draw(values, t));
      cs.play();                                   // re-read the canvas for one frame, then stop
      map.once("render", () => cs.pause());
      map.triggerRepaint();
    }
    const w = windOf(set, past ? frame : last, !past)?.w ?? null;
    motionRef.current?.setWind(w);
    motionRef.current?.setRivers(rivers.map((r, i) => ({ layer: `river-flow-${i}`, pct: pct(r) ?? null })));
    applyLayers(map, layersRef.current);
    if (!playing) setSaid(daySentence(values, pct, w));
  }, [frame, ready, set, redraw]);

  /** "May 10, 2019: West Sound 0.6 ppt, ...; Pearl River very high, ...; wind from the south at about 9 mph." */
  function daySentence(values: Record<string, number | null>, pct: (r: MapRiver) => number | null | undefined, w: Wind | null): string {
    if (!set) return "";
    const when = today ? "Today" : fmtDay(set.days[frame], true);
    const names = new Map([...(replaySites ?? []), ...stations].map((s) => [s.id, s.short]));
    const sal = Object.entries(values).filter(([, v]) => v !== null && v !== undefined)
      .map(([id, v]) => `${names.get(id) ?? id} ${v!.toFixed(1)} ppt`);
    const flows = rivers.map((r) => { const b = BAND(pct(r)); return b ? `${r.name} ${FLOW_WORDS[b]}` : null; }).filter(Boolean);
    return `${when}: ${sal.length ? sal.join(", ") : "no salinity readings"}${flows.length ? `; ${flows.join(", ")}` : ""}` +
      `${w ? `; wind ${windWords(w)}` : ""}.`;
  }

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => setFrame((f) => {
      if (f >= last) { setPlaying(false); return last; }
      return f + 1;
    }), set?.year === null ? 380 : 110);
    return () => window.clearInterval(id);
  }, [playing, last, set]);

  function play() {
    if (playing) { setPlaying(false); return; }
    if (frame >= last) setFrame(0);
    setPlaying(true);
  }

  // ---------- the long replay (decision 0033): any day since the record starts, by year, month, notable day or #YYYY-MM-DD
  async function goTo(year: number | null, day?: string) {
    setPlaying(false);
    if (year === null || !replayIndex || !dataBase) {
      if (recent) { setSet(recent); setFrame(recent.days.length - 1); }
      if (DAY_HASH.test(location.hash)) history.replaceState(null, "", location.pathname + location.search);
      return;
    }
    let next = set?.year === year ? set : null;
    if (!next) {
      setLoadingYear(true);
      const f: ReplayYear | null = await fetch(`${dataBase}replay/${year}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
      setLoadingYear(false);
      if (!f) return;
      next = yearSet(f);
    }
    const i = day ? next.days.indexOf(day) : 0;
    setSet(next);
    setFrame(i < 0 ? (day && day > next.days.at(-1)! ? next.days.length - 1 : 0) : i);
  }
  useEffect(() => {
    const fromHash = (scroll: boolean) => {
      const m = location.hash.match(DAY_HASH);
      if (!m || !replayIndex?.years.includes(+m[1])) return;
      goTo(+m[1], `${m[1]}-${m[2]}-${m[3]}`);
      if (scroll) el.current?.scrollIntoView({ block: "center" });
    };
    if (ready) fromHash(true);
    const onHash = () => fromHash(true);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [ready, replayIndex]);
  // Keep the address on the day shown, so it can be shared; not while playing.
  useEffect(() => {
    if (!set || set.year === null || playing) return;
    history.replaceState(null, "", `${location.pathname}${location.search}#${set.days[frame]}`);
  }, [set, frame, playing]);

  const noBasemap = meta === null;
  const past = !today;
  const fill = SAT_KEYS.find((k) => layers[k] && satellite?.[k]);
  const sat = fill ? satellite![fill] : null;
  const span = sat ? (sat.from === sat.to ? fmtDay(sat.to) : `${fmtDay(sat.from)}–${fmtDay(sat.to)}`) : "";
  const refs = past ? [] : (reference ?? []).filter((r) => r.salinity !== null && r.east);
  const riverRows = rivers.map((r) => {
    const pct = past ? set!.flow_pct[r.id]?.[frame] : r.percentile;
    const band = past ? BAND(pct) : r.band;
    return (
      <div key={r.name}><span className="bar" style={{ height: 6 + ((pct ?? 50) / 100) * 10 }} />
        <b>{r.name}</b> {past ? (band ? FLOW_WORDS[band] : "no reading") : `${r.display}${band ? `, ${FLOW_WORDS[band]}` : ""}`}</div>
    );
  });
  return (
    <>
    <div className="map-wrap">
      <div ref={el} className="map" />
      {failed && <p className="map-msg">The map couldn't load. The station list below has the same readings.</p>}
      {/* One column down the right edge, so a tall Layers panel stacks above the reference chip instead of under it. */}
      <div className="map-side">
      <details className="map-layers" open={panelOpen} onToggle={(e) => setPanelOpen((e.target as HTMLDetailsElement).open)}>
        <summary>Layers</summary>
        {LAYERS.map((l) => {
          if (l.key === "beaches" && !beachesUrl) return null;
          if ((l.key === "clarity" || l.key === "sst") && !satellite?.[l.key]) return null;
          const disabled = noBasemap && !["rivers", "beaches"].includes(l.key);
          return (
            <label key={l.key} title={l.note} className={disabled ? "off" : undefined}>
              <input type="checkbox" checked={layers[l.key] && !disabled} disabled={disabled || !ready} onChange={() => toggle(l.key)} />
              {l.label}
            </label>
          );
        })}
        {layers.beaches && beachesUrl && (
          <ul className="beach-key" aria-label="Beach status key">
            <li><span className="swatch" data-status="clear" />Clear</li>
            <li><span className="swatch" data-status="advisory" />Advisory</li>
            <li><span className="swatch" data-status="closure" />Closed</li>
          </ul>
        )}
        {sat && fill && !noBasemap && !past && (
          <div className="sat-key">
            <span className="sat-ramp" data-layer={fill} aria-hidden="true" />
            <span className="sat-ends">
              <span>{fill === "clarity" ? "Clear" : `${sat.range[0]}${sat.unit ?? ""}`}</span>
              <span>{fill === "clarity" ? "Murky" : `${sat.range[1]}${sat.unit ?? ""}`}</span>
            </span>
            {sat.summary && <p className="map-note">{sat.summary}</p>}
            <p className="map-note">{`Satellite, ${span}: the newest clear view of each spot. Gaps are clouds.`}</p>
          </div>
        )}
        {past && (fill || layers.beaches) && <p className="map-note">Satellite fills and beach status show today only, so they're hidden while replaying.</p>}
        {layers.salinity && !noBasemap && <p className="map-note">{sketched
          ? `Estimated between a handful of stations${past ? ", from their measured readings that day" : ""}. A sketch, not a measurement.`
          : "Fewer than two stations reported on this day, so there's no sketch."}</p>}
        {layers.wind && !noBasemap && (() => { const w = windOf(set, frame, today);
          return <p className="map-note">{`Wind over the middle of the Sound, shown across the map. Not a water current. ${
            w ? `${fmtDay(w.day, set!.year !== null)}: ${windWords(w.w)}, daily average.` : "No wind reading for this day."}`}</p>; })()}
        {noBasemap && <p className="map-note">Depth layers need the one-time basemap prep.</p>}
      </details>
      {refs.map((r) => (
        <p key={r.id} className="map-ref" title={`${r.name}. Not one of our stations: shown for comparison only.`}>
          <span className="map-ref-place">{`${r.place ?? r.name} `}<span aria-hidden="true">→</span></span>
          <b>{`${r.salinity!.toFixed(1)} ppt`}</b>
          <span className="map-ref-note">{`Reference, ${r.km} km east of ${r.nearest}`}</span>
        </p>
      ))}
      </div>
      <div className="map-rivers" aria-hidden="true">{riverRows}</div>
    </div>
    {/* Phones: the same rows as a strip under the map, which is too small to float them over. */}
    <div className="map-rivers-row">
      <div className="rows" aria-hidden="true">{riverRows}</div>
      {refs.map((r) => (
        <p key={r.id} className="map-ref-row">
          {`${r.place ?? r.name}: `}<b>{`${r.salinity!.toFixed(1)} ppt`}</b>{`. Reference, ${r.km} km east of ${r.nearest}.`}
        </p>
      ))}
    </div>
    {set && set.days.length > 1 && (
      <div className="replay">
        <div className="replay-row">
          <button type="button" className="replay-play" onClick={play} disabled={!ready || loadingYear} aria-pressed={playing}
            aria-label={playing ? "Pause the replay" : set.year === null ? "Play the last 30 days" : `Play ${set.year}`}>
            <span aria-hidden="true" data-icon={playing ? "pause" : "play"} />
          </button>
          <input type="range" min={0} max={last} step={1} value={frame} disabled={!ready || loadingYear}
            aria-label="Day shown on the map" aria-valuetext={today ? `Today, ${fmtDay(set.days[frame])}` : fmtDay(set.days[frame], set.year !== null)}
            onChange={(e) => { setPlaying(false); setFrame(Number(e.target.value)); }} />
          <span className="replay-day" data-past={past ? "" : undefined}>{today ? "Today" : fmtDay(set.days[frame], set.year !== null)}</span>
        </div>
        {replayIndex && replayIndex.years.length > 0 && (
          <div className="replay-pick">
            <label>{"Year "}
              <select value={set.year ?? ""} disabled={!ready || loadingYear} onChange={(e) => goTo(e.target.value ? +e.target.value : null)}>
                <option value="">Last 30 days</option>
                {replayIndex.years.slice().reverse().map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </label>
            {set.year !== null && (
              <label>{"Month "}
                <select value={+set.days[frame].slice(5, 7) - 1} disabled={!ready}
                  onChange={(e) => { setPlaying(false); const i = set.days.findIndex((d) => +d.slice(5, 7) - 1 === +e.target.value); if (i >= 0) setFrame(i); }}>
                  {MONTHS.map((m, i) => <option key={m} value={i} disabled={!set.days.some((d) => +d.slice(5, 7) - 1 === i)}>{m}</option>)}
                </select>
              </label>
            )}
            {replayIndex.shortcuts.length > 0 && (
              <label>{"Jump to "}
                <select value="" disabled={!ready || loadingYear}
                  onChange={(e) => { const d = e.target.value; if (d) goTo(+d.slice(0, 4), d); }}>
                  <option value="">A notable day…</option>
                  {replayIndex.shortcuts.slice().reverse().map((x) => <option key={x.date + x.label} value={x.date}>{`${x.label}, ${fmtDay(x.date, true)}`}</option>)}
                </select>
              </label>
            )}
          </div>
        )}
        <span className="replay-note">{loadingYear ? "Loading that year…" : set.year !== null
          ? `Measured station salinity, river flow and wind each day of ${set.year}. Link to a day with its address.`
          : past ? "Station salinity, river flow and wind that day." : "Replay the last 30 days, or pick any year since the record starts."}</span>
        <p className="visually-hidden" aria-live="polite">{playing ? "" : said}</p>
      </div>
    )}
    </>
  );
}
