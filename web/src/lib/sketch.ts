// The salinity sketch (decision 0033): inverse-distance weighting between stations, clipped to the water and fading
// away from stations. Stations don't move, so each cell's distance to every station is worked out once; a redraw is
// a weighted sum on a coarse grid, scaled up and clipped by the full-resolution water mask. Fast enough to redraw on
// every replay frame.
import { salinityRGB } from "./salinity";

export interface SketchPoint { id: string; lon: number; lat: number }
interface Ramp { fresh: string; brackish: string; gulf: string }

const STEP = 4;                 // one sketch cell per 4x4 mask pixels
const OUT = 1;                  // the drawn sketch's size relative to the mask (0.5 measured no faster: map repaint dominates)
const FADE_KM = 30;             // the fill fades out this far from the nearest station
const KM_LON = 111.32 * Math.cos((30.4 * Math.PI) / 180), KM_LAT = 110.57;

export class Sketch {
  readonly canvas = document.createElement("canvas");
  private small = document.createElement("canvas");
  private mask = document.createElement("canvas");
  private dist: Float32Array;   // cell-major: dist[cell * K + k], km (+0.5 so a station's own cell isn't infinite)
  private water: Uint8Array;    // cells with any water in them
  private gw: number; private gh: number;
  private index = new Map<string, number>();
  private wet: Uint8Array;      // full-resolution water mask, for isWater
  private mw: number; private mh: number; private bounds: [number, number, number, number];

  private constructor(maskImg: HTMLImageElement, bounds: [number, number, number, number], points: SketchPoint[]) {
    const [w, h] = [maskImg.width, maskImg.height];
    this.canvas.width = Math.round(w * OUT); this.canvas.height = Math.round(h * OUT);
    // The mask PNG is white water on black land; turn it into alpha so it can clip with destination-in.
    this.mask.width = w; this.mask.height = h;
    const mctx = this.mask.getContext("2d", { willReadFrequently: true })!;
    mctx.drawImage(maskImg, 0, 0);
    const md = mctx.getImageData(0, 0, w, h);
    for (let i = 0; i < md.data.length; i += 4) { md.data[i + 3] = md.data[i]; md.data[i] = md.data[i + 1] = md.data[i + 2] = 255; }
    mctx.putImageData(md, 0, 0);
    this.mw = w; this.mh = h; this.bounds = bounds;
    this.wet = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) this.wet[i] = md.data[i * 4 + 3] >= 128 ? 1 : 0;
    this.gw = Math.ceil(w / STEP); this.gh = Math.ceil(h / STEP);
    this.small.width = this.gw; this.small.height = this.gh;
    const [W, S, E, N] = bounds;
    const K = points.length;
    points.forEach((p, k) => this.index.set(p.id, k));
    const px = points.map((p) => (p.lon - W) * KM_LON), py = points.map((p) => (N - p.lat) * KM_LAT);
    const cellX = ((E - W) * KM_LON) / this.gw, cellY = ((N - S) * KM_LAT) / this.gh;
    this.dist = new Float32Array(this.gw * this.gh * K);
    this.water = new Uint8Array(this.gw * this.gh);
    for (let gy = 0; gy < this.gh; gy++) {
      for (let gx = 0; gx < this.gw; gx++) {
        const c = gy * this.gw + gx;
        let wet = 0;   // any water pixel in this block?
        for (let y = gy * STEP; y < Math.min(h, gy * STEP + STEP) && !wet; y++)
          for (let x = gx * STEP; x < Math.min(w, gx * STEP + STEP); x++) if (md.data[(y * w + x) * 4 + 3] >= 128) { wet = 1; break; }
        this.water[c] = wet;
        const xk = (gx + 0.5) * cellX, yk = (gy + 0.5) * cellY;
        for (let k = 0; k < K; k++) this.dist[c * K + k] = Math.hypot(xk - px[k], yk - py[k]) + 0.5;
      }
    }
  }

  static async create(maskUrl: string, bounds: [number, number, number, number], points: SketchPoint[]): Promise<Sketch> {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = maskUrl;
    await img.decode();
    return new Sketch(img, bounds, points);
  }

  /** Is this point on the water? (Used by the wind particles.) */
  isWater = (lon: number, lat: number): boolean => {
    const [W, S, E, N] = this.bounds;
    const x = Math.floor(((lon - W) / (E - W)) * this.mw), y = Math.floor(((N - lat) / (N - S)) * this.mh);
    return x >= 0 && y >= 0 && x < this.mw && y < this.mh && this.wet[y * this.mw + x] === 1;
  };

  /** Redraw from {station id: ppt}. Returns false (and clears) when fewer than two stations have a value. */
  draw(values: Record<string, number | null | undefined>, ramp: Ramp): boolean {
    const have = [...this.index].filter(([id]) => values[id] !== null && values[id] !== undefined);
    const ctx = this.canvas.getContext("2d")!;
    ctx.globalCompositeOperation = "source-over";
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (have.length < 2) return false;
    const K = this.index.size;
    const ks = have.map(([, k]) => k), vs = have.map(([id]) => values[id] as number);
    const sctx = this.small.getContext("2d")!;
    const img = sctx.createImageData(this.gw, this.gh);
    const colors = new Map<number, number[]>();
    for (let c = 0; c < this.gw * this.gh; c++) {
      if (!this.water[c]) continue;
      let num = 0, den = 0, dmin = Infinity;
      for (let j = 0; j < ks.length; j++) {
        const d = this.dist[c * K + ks[j]];
        const wt = 1 / (d * d);
        num += wt * vs[j]; den += wt; if (d < dmin) dmin = d;
      }
      const key = Math.round((num / den) * 10);      // colors cached at 0.1 ppt steps
      let col = colors.get(key);
      if (!col) { col = salinityRGB(key / 10, ramp); colors.set(key, col); }
      const i = c * 4;
      img.data[i] = col[0]; img.data[i + 1] = col[1]; img.data[i + 2] = col[2];
      img.data[i + 3] = Math.round(200 * Math.max(0, 1 - dmin / FADE_KM));
    }
    sctx.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(this.small, 0, 0, this.gw * STEP * OUT, this.gh * STEP * OUT);
    ctx.globalCompositeOperation = "destination-in";
    ctx.drawImage(this.mask, 0, 0, this.canvas.width, this.canvas.height);
    ctx.globalCompositeOperation = "source-over";
    return true;
  }
}
