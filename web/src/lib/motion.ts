// Wind and river flow as motion on the map (decision 0034). Wind: a few hundred faint particles drifting with the day's
// mean wind over the middle of the Sound, kept on the water by the sketch's mask. It is one wind for the whole map, not
// a water current, and the map says so. Rivers: the river lines' dashes march toward the Sound at a speed set by each
// river's flow percentile. With prefers-reduced-motion, wind is drawn as still arrows and the dashes stand still.
// Nothing animates while the map is off screen or the tab is hidden.
import type { Map as MLMap } from "maplibre-gl";

export interface Wind { u: number; v: number }   // m/s toward east and north
export interface RiverMotion { layer: string; pct: number | null }

const N = 320;
const DEG_PER_MS = 0.00016;    // degrees moved per frame for each m/s of wind
// Dash phases for a marching line (MapLibre's "animate a line" pattern): [dash, gap, ...] shifted half a unit a step.
const DASHES = [[0, 4, 3], [0.5, 4, 2.5], [1, 4, 2], [1.5, 4, 1.5], [2, 4, 1], [2.5, 4, 0.5], [3, 4, 0],
  [0, 0.5, 3, 3.5], [0, 1, 3, 3], [0, 1.5, 3, 2.5], [0, 2, 3, 2], [0, 2.5, 3, 1.5], [0, 3, 3, 1], [0, 3.5, 3, 0.5]];

export class Motion {
  private canvas = document.createElement("canvas");
  private ctx = this.canvas.getContext("2d")!;
  private p = new Float32Array(N * 3);    // lon, lat, age
  private wind: Wind | null = null;
  private rivers: RiverMotion[] = [];
  private phase = new Map<string, number>();
  private show = { wind: false, rivers: false };
  private raf = 0;
  private visible = true;
  private io: IntersectionObserver;
  private reduced = matchMedia("(prefers-reduced-motion: reduce)");
  private last = 0;
  color = "#000";

  constructor(private map: MLMap, container: HTMLElement, private isWater: (lon: number, lat: number) => boolean,
              private bounds: [number, number, number, number]) {
    this.canvas.className = "map-wind";
    this.canvas.setAttribute("aria-hidden", "true");
    container.appendChild(this.canvas);
    for (let i = 0; i < N; i++) this.spawn(i, true);
    this.io = new IntersectionObserver(([e]) => { this.visible = e.isIntersecting; this.kick(); });
    this.io.observe(container);
    document.addEventListener("visibilitychange", this.kick);
    this.reduced.addEventListener("change", this.kick);
    map.on("move", this.onMove);
    map.on("resize", this.onMove);
    this.size();
  }

  setWind(w: Wind | null) { this.wind = w; this.kick(); if (this.reduced.matches) this.drawArrows(); }
  setRivers(r: RiverMotion[]) { this.rivers = r; this.kick(); }
  setShown(show: { wind: boolean; rivers: boolean }) {
    this.show = show;
    if (!show.wind) this.clear();
    if (!show.rivers || this.reduced.matches) this.stillRivers();
    this.kick();
  }
  destroy() {
    cancelAnimationFrame(this.raf);
    this.io.disconnect();
    document.removeEventListener("visibilitychange", this.kick);
    this.reduced.removeEventListener("change", this.kick);
    this.map.off("move", this.onMove);
    this.map.off("resize", this.onMove);
    this.canvas.remove();
  }

  private running() { return this.visible && !document.hidden && !this.reduced.matches && (this.show.wind || this.show.rivers); }
  private kick = () => {
    cancelAnimationFrame(this.raf);
    if (this.running()) this.raf = requestAnimationFrame(this.tick);
    else if (this.reduced.matches) { this.drawArrows(); this.stillRivers(); }
  };
  private onMove = () => { this.size(); this.clear(); if (this.reduced.matches) this.drawArrows(); };
  private size() {
    const c = this.map.getCanvas(), dpr = window.devicePixelRatio || 1;
    const w = c.clientWidth, h = c.clientHeight;
    if (this.canvas.width !== Math.round(w * dpr) || this.canvas.height !== Math.round(h * dpr)) {
      this.canvas.width = Math.round(w * dpr); this.canvas.height = Math.round(h * dpr);
      this.canvas.style.width = `${w}px`; this.canvas.style.height = `${h}px`;
    }
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  private clear() { this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height); }

  private spawn(i: number, scatter = false) {
    const [W, S, E, N_] = this.bounds;
    for (let tries = 0; tries < 30; tries++) {
      const lon = W + Math.random() * (E - W), lat = S + Math.random() * (N_ - S);
      if (this.isWater(lon, lat)) {
        this.p[i * 3] = lon; this.p[i * 3 + 1] = lat; this.p[i * 3 + 2] = scatter ? Math.random() * 120 : 0;
        return;
      }
    }
    this.p[i * 3 + 2] = 999;   // no water found this time; try again next frame
  }

  private tick = (t: number) => {
    this.raf = requestAnimationFrame(this.tick);
    const dt = Math.min(3, this.last ? (t - this.last) / 16.7 : 1);
    this.last = t;
    if (this.show.wind && this.wind) this.stepWind(dt);
    if (this.show.rivers) this.stepRivers(dt);
  };

  private stepWind(dt: number) {
    const { u, v } = this.wind!;
    const ctx = this.ctx;
    const w = this.canvas.clientWidth || this.canvas.width, h = this.canvas.clientHeight || this.canvas.height;
    // Fade the old trails a little each frame.
    ctx.globalCompositeOperation = "destination-out";
    ctx.fillStyle = "rgba(0,0,0,0.07)";
    ctx.fillRect(0, 0, w, h);
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = this.color;
    ctx.lineWidth = 1.3;
    ctx.globalAlpha = 0.75;
    ctx.beginPath();
    const cos = Math.cos((30.3 * Math.PI) / 180);
    for (let i = 0; i < N; i++) {
      const lon = this.p[i * 3], lat = this.p[i * 3 + 1];
      const age = (this.p[i * 3 + 2] += dt);
      if (age > 140 || !this.isWater(lon, lat)) { this.spawn(i); continue; }
      const nl = lon + (u * DEG_PER_MS * dt) / cos, nt = lat + v * DEG_PER_MS * dt;
      const a = this.map.project([lon, lat]), b = this.map.project([nl, nt]);
      ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
      this.p[i * 3] = nl; this.p[i * 3 + 1] = nt;
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  private stepRivers(dt: number) {
    for (const r of this.rivers) {
      if (!this.map.getLayer(r.layer)) continue;
      // Steps per second: about 1 for a very low river, up to 15 for a very high one.
      const rate = 1 + ((r.pct ?? 50) / 100) ** 1.5 * 14;
      const before = this.phase.get(r.layer) ?? 0;
      const now = before + (rate * dt) / 60;
      this.phase.set(r.layer, now);
      if (Math.floor(now) !== Math.floor(before)) this.map.setPaintProperty(r.layer, "line-dasharray", DASHES[Math.floor(now) % DASHES.length]);
    }
  }
  private stillRivers() {
    for (const r of this.rivers) if (this.map.getLayer(r.layer)) this.map.setPaintProperty(r.layer, "line-dasharray", DASHES[0]);
  }

  /** Reduced motion: a sparse grid of still arrows pointing where the wind blows, longer for stronger wind. */
  private drawArrows() {
    this.clear();
    if (!this.show.wind || !this.wind) return;
    const { u, v } = this.wind;
    const speed = Math.hypot(u, v);
    if (speed < 0.3) return;
    const ctx = this.ctx;
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    const len = 8 + Math.min(1, speed / 10) * 16, dx = u / speed, dy = -v / speed;   // screen y runs down
    ctx.strokeStyle = this.color;
    ctx.globalAlpha = 0.8;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let y = 30; y < h; y += 56) {
      for (let x = 30 + ((y / 56) % 2) * 28; x < w; x += 56) {
        const ll = this.map.unproject([x, y]);
        if (!this.isWater(ll.lng, ll.lat)) continue;
        const x0 = x - (dx * len) / 2, y0 = y - (dy * len) / 2, x1 = x + (dx * len) / 2, y1 = y + (dy * len) / 2;
        ctx.moveTo(x0, y0); ctx.lineTo(x1, y1);
        ctx.moveTo(x1, y1); ctx.lineTo(x1 - dx * 5 - dy * 3.5, y1 - dy * 5 + dx * 3.5);
        ctx.moveTo(x1, y1); ctx.lineTo(x1 - dx * 5 + dy * 3.5, y1 - dy * 5 - dx * 3.5);
      }
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
}

const COMPASS = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"];
/** "from the southeast at about 9 mph" for a wind blowing toward (u, v). */
export function windWords(w: Wind): string {
  const mph = Math.hypot(w.u, w.v) * 2.23694;
  if (mph < 2) return "nearly calm";
  const from = (Math.atan2(-w.u, -w.v) * 180) / Math.PI;     // compass bearing the wind comes from
  return `from the ${COMPASS[Math.round(((from + 360) % 360) / 45) % 8]} at about ${Math.round(mph)} mph`;
}
