import { useEffect, useRef, useState } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Map as MLMap, MapLayerMouseEvent, Popup, StyleSpecification } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import type { Replay, SatelliteLayer } from "../lib/types";
import { beachDetail } from "../lib/format";

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
}
const NO_RIVERS: string[] = [];

type LayerKey = "depth" | "contours" | "salinity" | "rivers" | "beaches" | "clarity" | "sst";
const LAYERS: { key: LayerKey; label: string; note?: string }[] = [
  { key: "beaches", label: "Beach status" },
  { key: "depth", label: "Depth shading" },
  { key: "contours", label: "Depth contours (ft)" },
  { key: "rivers", label: "River flow" },
  { key: "salinity", label: "Salinity sketch", note: "Estimated between a handful of stations. A sketch, not a measurement." },
  { key: "clarity", label: "Water clarity (satellite)" },
  { key: "sst", label: "Surface temp (satellite)" },
];
const DEFAULTS: Record<LayerKey, boolean> = { depth: true, contours: true, rivers: true, salinity: false, beaches: false, clarity: false, sst: false };
/** Layers that fill the water: only one at a time, since each hides the others. */
const FILLS: LayerKey[] = ["salinity", "clarity", "sst"];
const SAT_KEYS = ["clarity", "sst"] as const;
const VIEW: [[number, number], [number, number]] = [[-89.72, 30.13], [-88.42, 30.5]];
const OFM = "https://tiles.openfreemap.org";
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
    red: v("--marker-red"), cool: v("--sst-cool"), mild: v("--sst-mild"), warm: v("--sst-warm"),
  };
}
type Tokens = ReturnType<typeof tokens>;
const rgb = (hex: string) => { const n = parseInt(hex.replace("#", ""), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
function salinityRGB(v: number, t: Tokens): number[] {
  const [a, b, c] = [rgb(t.fresh), rgb(t.brackish), rgb(t.gulf)];
  const mix = (x: number[], y: number[], k: number) => x.map((xi, i) => Math.round(xi + (y[i] - xi) * k));
  return v <= 12 ? mix(a, b, Math.max(0, v) / 12) : mix(b, c, Math.min(1, (v - 12) / 13));
}
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
const fmtDay = (d: string) => new Date(d + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });

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

// ---------- salinity sketch: inverse-distance weighting, clipped to water, fading away from stations
async function salinityImage(meta: Meta, maskUrl: string, stations: MapStation[], t: Tokens): Promise<string | null> {
  const pts = stations.filter((s) => s.status === "live" && s.salinity !== null);
  if (pts.length < 2) return null;
  const img = new Image();
  img.crossOrigin = "anonymous";
  img.src = maskUrl;
  await img.decode();
  const [w, h] = [img.width, img.height];
  const cv = document.createElement("canvas");
  cv.width = w; cv.height = h;
  const ctx = cv.getContext("2d")!;
  ctx.drawImage(img, 0, 0);
  const mask = ctx.getImageData(0, 0, w, h);
  const out = ctx.createImageData(w, h);
  const [W, S, E, N] = meta.bounds;
  const kmLon = 111.32 * Math.cos((30.4 * Math.PI) / 180), kmLat = 110.57;
  const px = pts.map((p) => (p.lon - W) * kmLon), py = pts.map((p) => (N - p.lat) * kmLat), pv = pts.map((p) => p.salinity as number);
  const cellX = ((E - W) * kmLon) / w, cellY = ((N - S) * kmLat) / h;
  const colors = new Map<number, number[]>();
  for (let y = 0; y < h; y++) {
    const yk = (y + 0.5) * cellY;
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      if (mask.data[i] < 128) continue;              // land
      const xk = (x + 0.5) * cellX;
      let num = 0, den = 0, dmin = Infinity;
      for (let k = 0; k < px.length; k++) {
        const d = Math.hypot(xk - px[k], yk - py[k]) + 0.5;
        const wt = 1 / (d * d);
        num += wt * pv[k]; den += wt; if (d < dmin) dmin = d;
      }
      const key = Math.round((num / den) * 10);      // cache colors at 0.1 ppt steps
      let c = colors.get(key);
      if (!c) { c = salinityRGB(key / 10, t); colors.set(key, c); }
      const fade = Math.max(0, 1 - dmin / 30);       // fades out ~30 km from the nearest station
      out.data[i] = c[0]; out.data[i + 1] = c[1]; out.data[i + 2] = c[2];
      out.data[i + 3] = Math.round(200 * fade);
    }
  }
  ctx.putImageData(out, 0, 0);
  return cv.toDataURL("image/png");
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
  beachLinks = false, satellite, dataBase, replay }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const tRef = useRef<Tokens | null>(null);
  const layersRef = useRef<Record<LayerKey, boolean>>(personaDefaults(defaultLayers));
  const replayingRef = useRef(false);
  const last = replay ? replay.days.length - 1 : 0;
  const [frame, setFrame] = useState(last);       // index into replay.days; the last day is "now"
  const [playing, setPlaying] = useState(false);
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
      const ml = await import("maplibre-gl");
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
          const sal = await salinityImage(m, `${basemapBase}watermask.png`, stations, t);
          if (sal) {
            map.addSource("salinity", { type: "image", url: sal, coordinates: corners });
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
        applyLayers(map, layersRef.current);
        setReady(true);
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
      cleanup = () => { mq.removeEventListener("change", restyle); window.removeEventListener("sc-theme-change", restyle); map.remove(); };
    })().catch(() => setFailed(true));
    return () => { cancelled = true; cleanup(); };
  }, [stations, rivers, ungauged, basemapBase, beachesUrl, beachLinks, personaId, defaultLayers, satellite, dataBase]);

  /** While replaying a past day, today's-only layers (fills, alert rings) are hidden so nothing mixes two dates. */
  function applyLayers(map: MLMap, l: Record<LayerKey, boolean>) {
    const past = replayingRef.current;
    const vis = (on: boolean) => (on ? "visible" : "none");
    const set = (id: string, on: boolean) => { if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis(on)); };
    set("depth", l.depth); set("contours", l.contours); set("contour-labels", l.contours);
    set("salinity", l.salinity && !past); set("clarity", l.clarity && !past); set("sst", l.sst && !past);
    set("rivers", l.rivers); set("rivers-ungauged", l.rivers); set("beaches", l.beaches && !past);
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

  // ---------- replay: redraw stations and rivers for one day of the last 30
  useEffect(() => {
    const map = mapRef.current, t = tRef.current;
    if (!map || !t || !ready || !replay || !map.getSource("stations")) return;
    const past = frame < last;
    replayingRef.current = past;
    const src = map.getSource("stations") as any;
    if (!past) {
      src.setData(stationData(stations, t));
      map.setPaintProperty("rivers", "line-width", riverWidths(rivers, (r) => r.percentile) as any);
    } else {
      const day = stations.map((s) => {
        const v = replay.salinity[s.id]?.[frame] ?? null;
        return { ...s, salinity: v, status: v === null ? "quiet" : "live", display: v === null ? "no reading" : `${v.toFixed(1)} ppt`, alert: false } as MapStation;
      });
      src.setData(stationData(day, t));
      map.setPaintProperty("rivers", "line-width", riverWidths(rivers, (r) => replay.flow_pct[r.id]?.[frame]) as any);
    }
    applyLayers(map, layersRef.current);
  }, [frame, ready]);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => setFrame((f) => {
      if (f >= last) { setPlaying(false); return last; }
      return f + 1;
    }), 380);
    return () => window.clearInterval(id);
  }, [playing, last]);

  function play() {
    if (playing) { setPlaying(false); return; }
    if (frame >= last) setFrame(0);
    setPlaying(true);
  }

  const noBasemap = meta === null;
  const past = !!replay && frame < last;
  const fill = SAT_KEYS.find((k) => layers[k] && satellite?.[k]);
  const sat = fill ? satellite![fill] : null;
  const span = sat ? (sat.from === sat.to ? fmtDay(sat.to) : `${fmtDay(sat.from)}–${fmtDay(sat.to)}`) : "";
  return (
    <>
    <div className="map-wrap">
      <div ref={el} className="map" />
      {failed && <p className="map-msg">The map couldn't load. The station list below has the same readings.</p>}
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
        {past && (layers.salinity || fill || layers.beaches) && <p className="map-note">Fills and beach status show today only, so they're hidden while replaying.</p>}
        {layers.salinity && !noBasemap && <p className="map-note">Estimated between a handful of stations. A sketch, not a measurement.</p>}
        {noBasemap && <p className="map-note">Depth layers need the one-time basemap prep.</p>}
      </details>
      <div className="map-rivers" aria-hidden="true">
        {rivers.map((r) => {
          const pct = past ? replay!.flow_pct[r.id]?.[frame] : r.percentile;
          const band = past ? BAND(pct) : r.band;
          return (
            <div key={r.name}><span className="bar" style={{ height: 6 + ((pct ?? 50) / 100) * 10 }} />
              <b>{r.name}</b> {past ? (band ? FLOW_WORDS[band] : "no reading") : `${r.display}${band ? `, ${FLOW_WORDS[band]}` : ""}`}</div>
          );
        })}
      </div>
    </div>
    {replay && replay.days.length > 1 && (
      <div className="replay">
        <button type="button" className="replay-play" onClick={play} disabled={!ready} aria-pressed={playing}
          aria-label={playing ? "Pause the replay" : "Play the last 30 days"}>
          <span aria-hidden="true" data-icon={playing ? "pause" : "play"} />
        </button>
        <input type="range" min={0} max={last} step={1} value={frame} disabled={!ready}
          aria-label="Day shown on the map" aria-valuetext={frame === last ? `Today, ${fmtDay(replay.days[frame])}` : fmtDay(replay.days[frame])}
          onChange={(e) => { setPlaying(false); setFrame(Number(e.target.value)); }} />
        <span className="replay-day" data-past={past ? "" : undefined}>{frame === last ? "Today" : fmtDay(replay.days[frame])}</span>
        <span className="replay-note">{past ? "Station salinity and river flow that day." : "Replay the last 30 days of station salinity and river flow."}</span>
      </div>
    )}
    </>
  );
}
