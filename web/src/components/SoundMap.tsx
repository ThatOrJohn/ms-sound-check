import { useEffect, useRef, useState } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Map as MLMap, StyleSpecification } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

export interface MapStation {
  id: string; short: string; kind: string; lon: number; lat: number; href: string;
  salinity: number | null; display: string; status: "live" | "suspect" | "quiet" | "estimate"; alert: boolean;
}
export interface MapRiver { name: string; osmNames: string[]; display: string; band?: string; percentile?: number }

interface Props { stations: MapStation[]; rivers: MapRiver[]; basemapBase: string }

type LayerKey = "depth" | "contours" | "salinity" | "rivers";
const LAYERS: { key: LayerKey; label: string; note?: string }[] = [
  { key: "depth", label: "Depth shading" },
  { key: "contours", label: "Depth contours (ft)" },
  { key: "rivers", label: "River flow" },
  { key: "salinity", label: "Salinity sketch", note: "Estimated between a handful of stations. A sketch, not a measurement." },
];
const DEFAULTS: Record<LayerKey, boolean> = { depth: true, contours: true, rivers: true, salinity: false };
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
    red: v("--marker-red"),
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

// ---------- style: OpenFreeMap vector tiles, drawn in our palette
function baseStyle(t: Tokens): StyleSpecification {
  return {
    version: 8,
    glyphs: `${OFM}/fonts/{fontstack}/{range}.pbf`,
    sources: {
      omt: { type: "vector", url: `${OFM}/planet`,
        attribution: '<a href="https://openfreemap.org">OpenFreeMap</a> © <a href="https://www.openmaptiles.org/">OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' },
    },
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

function readLayers(): Record<LayerKey, boolean> {
  try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem("sc-layers") || "{}") }; } catch { return { ...DEFAULTS }; }
}

export default function SoundMap({ stations, rivers, basemapBase }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>(DEFAULTS);
  const [meta, setMeta] = useState<Meta | null | undefined>(undefined);   // undefined = loading, null = no basemap
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  useEffect(() => setPanelOpen(window.matchMedia("(min-width: 900px)").matches), []);

  useEffect(() => setLayers(readLayers()), []);

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
        attributionControl: { compact: true },
      });
      mapRef.current = map;
      map.touchZoomRotate.disableRotation();
      map.addControl(new ml.NavigationControl({ showCompass: false }), "bottom-right");
      map.on("error", (e) => { if (String(e?.error?.message || "").includes("planet")) setFailed(true); });

      const addOverlays = async () => {
        t = tokens();
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
        }
        // Rivers: widen the real river lines by how hard they're running.
        const width = (pct: number | undefined) => 1.5 + ((pct ?? 50) / 100) * 5;
        const match: any[] = ["match", ["get", "name"]];
        rivers.forEach((r) => r.osmNames.forEach((n) => match.push(n, width(r.percentile))));
        match.push(0);
        map.addLayer({ id: "rivers", type: "line", source: "omt", "source-layer": "waterway",
          filter: ["in", ["get", "name"], ["literal", rivers.flatMap((r) => r.osmNames)]],
          layout: { "line-cap": "round", "line-join": "round" },
          paint: { "line-color": t.fresh, "line-opacity": 0.9, "line-width": match as any } }, "places");

        const fc = {
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
        map.addSource("stations", { type: "geojson", data: fc });
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
        applyLayers(map, readLayers());
        setReady(true);
      };

      map.on("load", addOverlays);
      map.on("click", "stations", (e) => { const h = e.features?.[0]?.properties?.href; if (h) window.location.assign(h); });
      map.on("mouseenter", "stations", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "stations", () => (map.getCanvas().style.cursor = ""));

      const restyle = () => {
        setReady(false);
        map.setStyle(baseStyle(tokens()));
        map.once("style.load", addOverlays);
      };
      const mq = matchMedia("(prefers-color-scheme: dark)");
      mq.addEventListener("change", restyle);
      window.addEventListener("sc-theme-change", restyle);
      cleanup = () => { mq.removeEventListener("change", restyle); window.removeEventListener("sc-theme-change", restyle); map.remove(); };
    })().catch(() => setFailed(true));
    return () => { cancelled = true; cleanup(); };
  }, [stations, rivers, basemapBase]);

  function applyLayers(map: MLMap, l: Record<LayerKey, boolean>) {
    const vis = (on: boolean) => (on ? "visible" : "none");
    const set = (id: string, on: boolean) => { if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis(on)); };
    set("depth", l.depth); set("contours", l.contours); set("contour-labels", l.contours);
    set("salinity", l.salinity); set("rivers", l.rivers);
  }
  function toggle(key: LayerKey) {
    const next = { ...layers, [key]: !layers[key] };
    setLayers(next);
    try { localStorage.setItem("sc-layers", JSON.stringify(next)); } catch { /* private mode */ }
    if (mapRef.current) applyLayers(mapRef.current, next);
  }

  const noBasemap = meta === null;
  return (
    <div className="map-wrap">
      <div ref={el} className="map" aria-hidden="true" />
      {failed && <p className="map-msg">The map couldn't load. The station list below has the same readings.</p>}
      <details className="map-layers" open={panelOpen} onToggle={(e) => setPanelOpen((e.target as HTMLDetailsElement).open)}>
        <summary>Layers</summary>
        {LAYERS.map((l) => {
          const disabled = noBasemap && l.key !== "rivers";
          return (
            <label key={l.key} title={l.note} className={disabled ? "off" : undefined}>
              <input type="checkbox" checked={layers[l.key] && !disabled} disabled={disabled || !ready} onChange={() => toggle(l.key)} />
              {l.label}
            </label>
          );
        })}
        {layers.salinity && !noBasemap && <p className="map-note">Estimated between a handful of stations. A sketch, not a measurement.</p>}
        {noBasemap && <p className="map-note">Depth layers need the one-time basemap prep.</p>}
      </details>
      <div className="map-rivers" aria-hidden="true">
        {rivers.map((r) => (
          <div key={r.name}><span className="bar" style={{ height: 6 + ((r.percentile ?? 50) / 100) * 10 }} />
            <b>{r.name}</b> {r.display}{r.band ? `, ${FLOW_WORDS[r.band]}` : ""}</div>
        ))}
      </div>
    </div>
  );
}
