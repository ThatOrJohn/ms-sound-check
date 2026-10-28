// Shapes of the JSON written by the Python pipeline (msc/build.py).

export type Severity = "notice" | "watch" | "warning" | "alert";
export type Band = "low" | "below" | "normal" | "above" | "high";
export type Kind = "sound" | "estuary" | "river" | "rain" | "weather" | "gauge" | "wind";
export type Section = Kind | "beaches" | "oyster_watch" | "fishing_outlook" | "shrimp_season";
export type Kind2 = Kind | "gauge";

export interface Persona {
  id: string;
  label: string;
  blurb: string;
  focus: string[];
  card_order: Section[];
  map_layers?: string[];
}

export interface BeachStation {
  id: string; name: string; location: string | null; county: string | null; from: string | null; to: string | null;
  lat: number | null; lon: number | null; status: "clear" | "advisory" | "closure"; event: string | null;
  text: string | null; since: string | null; last_sample: string | null; days_flagged: number | null;
}
export interface BeachSection {
  source: string | null; link: string | null; fetched_at: string | null; total: number;
  counts: { clear: number; advisory: number; closure: number }; latest_sample: string | null;
  stations: BeachStation[];
}

export interface Finding {
  indicator: string;
  site: string | null;
  sites?: string[];      // stations an event involves (site is null for events across stations)
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
  suspect_reason?: "ceiling" | "neighbors" | null;
  /** What nearby stations and river flow imply right now (virtual sensor). */
  expected?: Estimate;
  /** Live reading falls outside the virtual sensor's 90% range. */
  vs_neighbors?: "high" | "low";
  /** Published estimate for a station with no live reading. */
  estimate?: Estimate;
  /** Newest observation (only for variables whose daily value hides "right now", e.g. air temp). */
  now?: Now;
}

/** lo/hi: today's range so far (absent once the day has turned); url: where the page refreshes it on load. */
export interface Now { value: number; display: string; time: string; lo?: number; hi?: number; url?: string }

export interface Estimate { value: number; lo: number; hi: number; display: string; mae: number | null; published: boolean }

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
  retired?: boolean;
  vars: Record<string, Reading>;
  findings: number[];
}

export interface OysterGroup {
  areas: string[]; names: string | null; stage_ft: number; status: "above" | "forecast" | "near" | "clear";
  crossing_time: string | null; rain_in: Record<string, number> | null; rain_triggered: string[];
  history: OysterHistory | null;
}
export interface OysterHistory {
  since: number; days_per_year: number; rises_per_year: number; peak_months: number[]; month: number; this_month_pct: number;
}
export interface OysterWatch {
  available: boolean; stale?: boolean;
  gauge?: { id: string; name: string; lid: string; stage: number; time: string; change_24h: number | null };
  forecast?: { points: [string, number][]; max: number | null; max_time: string | null };
  rain?: { site: string; yesterday_in: number | null; approximate: boolean };
  groups?: OysterGroup[];
  plan_name: string; plan_url: string; status_url?: string; hotline?: string;
}

export interface Tide { station: string; name: string; time: string; type: "high" | "low"; ft: number }
export interface FishingDay {
  date: string; label: string; wind: string | null; wind_mph_hi: number | null; sky: string | null;
  rain_pct: number | null; high_f: number | null; verdict: string | null; verdict_text: string | null; tides: Tide[];
}
export interface FishingOutlook {
  days: FishingDay[]; weekend: boolean;
  water: { temp_f: number | null; temp_change_7d: number | null; saltiest: [string, number] | null; freshest: [string, number] | null };
  muddy: { level: "clean" | "some runoff" | "muddy"; reasons: string[]; local_rain_3d_in: number | null; forecast_rain_in: number | null };
  tide_stations: { id: string; name: string }[];
}

export interface ShrimpNotice { id: number; date: string; title: string; summary: string; link: string }
export interface ShrimpWindDay {
  date: string; label: string; day_wind: string | null; night_wind: string | null; wind_mph_hi: number | null;
  sky: string | null; rain_pct: number | null; verdict: string | null;
}
export interface ShrimpSeason {
  notices: ShrimpNotice[]; notices_available: boolean; link: string | null; source: string | null; days: ShrimpWindDay[];
}

export interface Latest {
  fishing_outlook?: FishingOutlook | null;
  shrimp_season?: ShrimpSeason | null;
  oyster_watch?: OysterWatch | null;
  beaches?: BeachSection | null;
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
  series: Record<string, {
    unit: string; label: string; points: SeriesPoint[];
    /** [date, expected, lo90, hi90] from the virtual sensor */
    expected?: [string, number | null, number | null, number | null][];
    expected_mae?: number | null;
  }>;
}
