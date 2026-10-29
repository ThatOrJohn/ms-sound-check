/** Salinity -> color, mixed in CSS so it follows the light/dark theme. */
export function salinityFill(v: number): string {
  if (v <= 12) {
    const t = Math.max(0, Math.min(100, (v / 12) * 100));
    return `color-mix(in oklab, var(--brackish) ${t.toFixed(0)}%, var(--fresh))`;
  }
  const t = Math.max(0, Math.min(100, ((v - 12) / 13) * 100));
  return `color-mix(in oklab, var(--gulf) ${t.toFixed(0)}%, var(--brackish))`;
}

/** The same ramp as hex tokens mixed in RGB, for canvas and the map (which can't use color-mix). */
const rgb = (hex: string) => { const n = parseInt(hex.replace("#", ""), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
const mix = (x: number[], y: number[], k: number) => x.map((xi, i) => Math.round(xi + (y[i] - xi) * k));
export function salinityRGB(v: number, t: { fresh: string; brackish: string; gulf: string }): number[] {
  const [a, b, c] = [rgb(t.fresh), rgb(t.brackish), rgb(t.gulf)];
  return v <= 12 ? mix(a, b, Math.max(0, v) / 12) : mix(b, c, Math.min(1, (v - 12) / 13));
}
