// The year a reader picked on a station's history picture, drawn as a faint line on its salinity chart.
// The picture and the charts are separate islands; this module is shared between them on the page.
import type { HistoryYear } from "./types";

/** site: the station; year: the picked year; rows: every year's row, so a chart reaching into last year can follow. */
export interface RefYear { site: string; year: number; rows: Record<number, HistoryYear["values"]> }

let current: RefYear | null = null;
const subs = new Set<(r: RefYear | null) => void>();
export const getRefYear = () => current;
export function setRefYear(r: RefYear | null) { current = r; subs.forEach((f) => f(r)); }
export function onRefYear(f: (r: RefYear | null) => void) { subs.add(f); return () => { subs.delete(f); }; }

/** "2026-03-01" -> its column in a history row (Jan 1 = 0, Feb 29 = 59, Mar 1 = 60). */
export const cellOf = (iso: string) =>
  Math.round((Date.UTC(2000, +iso.slice(5, 7) - 1, +iso.slice(8, 10)) - Date.UTC(2000, 0, 1)) / 86400_000);

/** The picked year's value on the same calendar day as `iso`, shifted back as far as the chart's date is. */
export function refValue(r: RefYear, iso: string, asofYear: number): number | null {
  const row = r.rows[r.year - (asofYear - +iso.slice(0, 4))];
  return row?.[cellOf(iso)] ?? null;
}
