// Shapes of the JSON written by the Python pipeline (msc/build.py).

export type Severity = "notice" | "watch" | "warning" | "alert";
export type Band = "low" | "below" | "normal" | "above" | "high";
export type Kind = "sound" | "estuary" | "river" | "rain" | "weather";

export interface Persona {
  id: string;
  label: string;
  blurb: string;
  focus: string[];
  card_order: Kind[];
}

export interface Finding {
  indicator: string;
  site: string | null;
  severity: Severity;
  topics: string[];
  text: string;
  var?: string;
}

export interface Normal { p10: number; p25: number; p50: number; p75: number; p90: number }

export interface Reading {
  status?: "no_data";
  value?: number;
  display?: string;
  unit?: string;
  date?: string;
  stale?: boolean;
  suspect?: boolean;
  age_days?: number;
  spark?: [string, number | null][];
  change_7d?: number;
  total_7d?: number;
  normal?: Normal;
  percentile?: number;
  band?: Band;
}

export interface Card {
  id: string;
  slug: string;
  name: string;
  short: string;
  kind: Kind;
  note?: string | null;
  lat: number;
  lon: number;
  drains_from?: string[] | null;
  osm_names?: string[] | null;
  vars: Record<string, Reading>;
  findings: number[];
}

export interface Latest {
  region: { id: string; name: string; units: Record<string, string>; map: { center: [number, number]; zoom: number } };
  generated_at: string;
  asof: string;
  season: string;
  personas: Persona[];
  headlines: Record<string, string>;
  findings: Finding[];
  cards: Card[];
  rain_forecast: Record<string, { days: [string, number | null][]; total: string }>;
  variables: Record<string, { label: string }>;
}

/** [date, value, p10, p50, p90] */
export type SeriesPoint = [string, number | null, number | null, number | null, number | null];

export interface SiteFile {
  id: string;
  slug: string;
  name: string;
  drains_from: string[];
  note?: string | null;
  series: Record<string, { unit: string; label: string; points: SeriesPoint[] }>;
}
