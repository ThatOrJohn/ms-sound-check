/** Salinity -> color, mixed in CSS so it follows the light/dark theme. */
export function salinityFill(v: number): string {
  if (v <= 12) {
    const t = Math.max(0, Math.min(100, (v / 12) * 100));
    return `color-mix(in oklab, var(--brackish) ${t.toFixed(0)}%, var(--fresh))`;
  }
  const t = Math.max(0, Math.min(100, ((v - 12) / 13) * 100));
  return `color-mix(in oklab, var(--gulf) ${t.toFixed(0)}%, var(--brackish))`;
}
