// Shapes of the JSON written by the Python pipeline (msc/build.py).

export type Severity = "notice" | "watch" | "warning" | "alert";
export type Band = "low" | "below" | "normal" | "above" | "high";
export type Kind = "sound" | "estuary" | "river" | "rain" | "weather" | "gauge" | "wind" | "water_level";
/** Inputs to the models and event text, not stations anyone browses to. */
export const INPUT_KINDS: Kind[] = ["wind", "water_level"];
export type Section = Kind | "beaches" | "oyster_watch" | "oyster_stress" |"fishing_outlook" | "shrimp_season" | "spillway" | "vibrio" | "history" | "strip";
export type Kind2 = Kind | "gauge";

export interface Persona {
  id: string;
  label: string;
  blurb: string;
  focus: string[];
  card_order: Section[];
  /** "strip": the share image shows the Sound west to east instead of the readout tiles (decision 0037). */
  share?: "strip";
  map_layers?: string[];
}

export interface BeachStation {
  id: string; name: string; location: string | null; county: string | null; from: string | null; to: string | null;
  lat: number | null; lon: number | null; status: "clear" | "advisory" | "closure"; event: string | null;
  text: string | null; since: string | null; last_sample: string | null; days_flagged: number | null;
  reason: "high bacteria" | "algal bloom" | "debris" | null;
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
  /** `record` findings: where today ranks ("third-lowest"), and on which side. */
  rank?: number;
  side?: "low" | "high";
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
  /** Every year's value for today's date, where a `record` indicator ranks this reading (decision 0032). */
  years?: YearDots;
}

/** Each year's mean over the `window` days ending on today's date; the same numbers the record text ranks.
 *  rank_high 1 = highest of `of` years. */
export interface YearDots {
  window: number; season: string; points: [number, number][]; rank_high: number; rank_low: number; of: number; record: string;
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
  /** A smaller river: shown, but kept out of the headline and readout tiles. */
  minor?: boolean;
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
  /** MDMR's own oyster season notices (openings, closures, area changes), newest first. */
  notices?: MdmrNotice[]; notices_available?: boolean; notices_link?: string | null;
  /** MDMR's season page, quoted (0044); null when the snapshot is stale or the page didn't parse. */
  season?: OysterSeasonPage | null;
}
/** MDMR page fields every quoted page carries: where it is and when MDMR last changed it. */
interface MdmrPage { link: string; modified: string }
export interface OysterSeasonPage extends MdmrPage {
  season?: string; summary: string[]; orders: { title: string; link: string }[];
  no_harvest: { lead: string; days: string[] } | null;
}
export interface ShrimpStatusPage extends MdmrPage {
  areas: { area: string; status: "open" | "closed"; footnote: boolean }[]; note: string | null;
}
/** MDMR's growing-water classes for the map (0043). Never open or closed: that's MDMR's call. */
export type ShellfishClass = "approved" | "conditional" | "restricted" | "prohibited" | "unclassified";
export interface ShellfishAreas {
  source: string | null; link: string | null; fetched_at: string; edited: string | null; classes: ShellfishClass[];
}

/** Fresh-and-hot days near the reefs (decision 0039). `to_date`: days up to today's day of the year. */
export interface StressYear { year: number; days: number; run: number; run_now: number; to_date: number; complete: boolean }
export interface StressNow {
  days: number; run: number; run_now: number; complete: boolean;
  /** Past complete years, and how many of them had more by this date. */
  of: number; more: number; median: number; last_as_many: number | null;
}
export interface OysterStressStation {
  id: string; short: string; name: string; since: number; years: StressYear[];
  now: StressNow | null; stale: boolean; suspect: boolean;
}
export interface OysterStress {
  salinity_below: number; temp_above_c: number; season_months: [number, number]; min_coverage: number;
  stations: OysterStressStation[];
}

export interface Tide { station: string; name: string; time: string; type: "high" | "low"; ft: number }
/** Highs and lows at one station from yesterday on; times carry their UTC offset. */
export interface TideStrip { station: string; name: string; events: { time: string; type: "high" | "low"; ft: number }[] }
export interface FishingDay {
  date: string; label: string; wind: string | null; wind_mph_hi: number | null; sky: string | null;
  rain_pct: number | null; high_f: number | null; verdict: string | null; verdict_text: string | null; tides: Tide[];
  /** The NWS marine forecast's own wave sentence for the daytime period, e.g. "Waves 2 to 3 feet." */
  waves?: string | null;
  /** Local 'YYYY-MM-DD HH:MM' times (null when it doesn't happen that day), computed in msc/models/sky.py (0040). */
  sky_times?: SkyTimes;
}
export interface SkyTimes {
  sunrise: string | null; sunset: string | null; moonrise: string | null; moonset: string | null;
  moon_phase: "new moon" | "first quarter" | "full moon" | "last quarter" | "waxing crescent" | "waxing gibbous" | "waning gibbous" | "waning crescent";
  moon_lit_pct: number;
}
export interface FishingOutlook {
  days: FishingDay[]; weekend: boolean;
  water: { temp_f: number | null; temp_change_7d: number | null; saltiest: [string, number] | null; freshest: [string, number] | null };
  muddy: { level: "clean" | "some runoff" | "muddy"; reasons: string[]; local_rain_3d_in: number | null; forecast_rain_in: number | null };
  tide_stations: { id: string; name: string }[];
  marine_zone?: { id: string; name: string } | null;
}

export interface MdmrNotice { id: number; date: string; title: string; summary: string; link: string }
export interface ShrimpWindDay {
  date: string; label: string; day_wind: string | null; night_wind: string | null; wind_mph_hi: number | null;
  sky: string | null; rain_pct: number | null; verdict: string | null;
}
export interface ShrimpSeason {
  notices: MdmrNotice[]; notices_available: boolean; link: string | null; source: string | null; days: ShrimpWindDay[];
  /** MDMR's open/closed box from its Shrimp & Crab page, quoted (0044). */
  status?: ShrimpStatusPage | null;
}

export interface ReferenceSite {
  id: string; name: string; place: string | null; lat: number; lon: number; link: string | null;
  salinity: number | null; date: string | null; nearest: string | null; km: number | null; east: boolean;
}

export interface SpillwayOpening { opened: string; year: number; days: number | null; closed: string | null; max_bays: number | null; peak_cfs: number | null }
/** One year of past openings at our Sound station (0038). Days count from the year's first opening; `bands` are the
 *  open spells. `before` is the median of the 4 weeks before; `fresh_run` the longest run of days under `fresh_ppt`. */
export interface SpillwayPast {
  year: number; opened: string[]; bands: [number, number][]; days_open: number;
  series: [number, number][]; typical: [number, number][];
  before: number; low: number; low_day: number; fresh_run: number; fresh_run_day: number | null;
}
export interface Spillway {
  gauge_name: string; open_ft: number; watch_ft: number; link: string | null;
  openings: SpillwayOpening[]; open_now: SpillwayOpening | null; count: number; since: number | null; since_2000: number;
  past: SpillwayPast[]; fresh_ppt: number; sound_site: string;
  /** Null when the river readings are missing or stale. */
  river: null | {
    stage: number; time: string; change_24h: number | null; status: "open_level" | "forecast_open" | "watch" | "low";
    forecast: [string, number][]; crest: number | null; crest_time: string | null;
    reach_open_time: string | null; reach_watch_time: string | null; observed: [string, number][];
  };
}

/** Stations where the water is warm and moderately salty, as Vibrio favors (decision 0024). Null when none are. */
export interface Vibrio {
  stations: { id: string; short: string; in_text: string; salinity: string; water_temp: string }[];
  places: string; temp_min: string; salinity_range: string; days: number; season: string | null;
  links: { label: string; url: string }[];
}

/** A satellite map layer: a data PNG (gray = value scaled to range, log if `log`; alpha 0 = no clear view). */
export interface SatelliteLayer {
  label: string; png: string; source: string | null; bounds: [number, number, number, number];
  from: string; to: string; log: boolean; range: [number, number]; unit: string | null; coverage: number;
  summary: string | null; zones: [string, number][];
}

/** Daily mean wind over the middle of the Sound, m/s toward east (u) and north (v), and the day's peak. */
export interface ReplayWind { u: (number | null)[]; v: (number | null)[]; max: (number | null)[] }
/** Last 30 days for the map's replay: measured salinity per station (retired ones too while they ran; never an
 *  estimate), flow percentile per river, wind (null = no reading). */
export interface Replay {
  days: string[]; salinity: Record<string, (number | null)[]>; flow_pct: Record<string, (number | null)[]>; wind: ReplayWind | null;
}
/** web/public/data/<region>/replay/<year>.json: the same, for one calendar year, `n` days from `start` (decision 0033). */
export interface ReplayYear { year: number; start: string; n: number; salinity: Replay["salinity"]; flow_pct: Replay["flow_pct"]; wind: ReplayWind | null }
/** In latest.json: which years have a replay file, every salinity station's position, and days worth jumping to. */
export interface ReplayIndex {
  years: number[]; sites: { id: string; short: string; lat: number; lon: number; retired: boolean }[];
  shortcuts: { date: string; label: string }[];
}

/** One year of a station's daily salinity (decision 0028). `values` has 366 cells, Jan 1 to Dec 31 of a leap year, so
 *  Feb 29 is null in common years. `counted`: enough days (80%) to count in per-year numbers; the current year always is. */
export interface HistoryYear {
  year: number; counted: boolean; coverage: number; mean: number; under: number; over: number; values: (number | null)[];
}
/** web/public/data/<region>/history/<slug>.json */
export interface HistoryFile {
  id: string; slug: string; short: string; name: string; asof: string; fresh_below: number; salty_above: number;
  years: HistoryYear[];
  /** A word or two per notable year ("spillway", "Ida"), for the picture's right margin. */
  tags?: Record<string, string>;
}
/** In latest.json: which stations have a history file, the ones the home section draws, and its takeaway line. */
export interface HistorySummary {
  since: number; fresh_below: number; salty_above: number; home: { id: string; slug: string; short: string }[];
  stations: Record<string, string>; takeaway: string | null;
}

/** Past years whose rivers over the last `days` days looked most like now, closest first. Background, never a forecast. */
export interface SimilarYears {
  days: number; label: string; compared: number; link_slug: string | null; link_short: string | null;
  years: { year: number; rms: number; note: string | null }[];
}

/** One week's digest entry (web/public/data/<region>/digest.json, newest first). */
export interface DigestEntry { id: string; date: string; title: string; headline: string; lines: string[] }

export interface Latest {
  history?: HistorySummary | null;
  similar_years?: SimilarYears | null;
  spillway?: Spillway | null;
  vibrio?: Vibrio | null;
  satellite?: Record<string, SatelliteLayer>;
  replay?: Replay;
  replay_index?: ReplayIndex | null;
  /** Reference salinity sites (not our stations); salinity is null when the newest daily mean is stale. */
  reference?: ReferenceSite[];
  fishing_outlook?: FishingOutlook | null;
  tide_strip?: TideStrip | null;
  shrimp_season?: ShrimpSeason | null;
  oyster_watch?: OysterWatch | null;
  oyster_stress?: OysterStress | null;
  beaches?: BeachSection | null;
  shellfish_areas?: ShellfishAreas | null;
  region: { id: string; name: string; units: Record<string, string>; map: { center: [number, number]; zoom: number } };
  generated_at: string;
  asof: string;
  season: string;
  personas: Persona[];
  headlines: Record<string, string>;
  findings: Finding[];
  cards: Card[];
  /** Rivers that reach the Sound without a live flow gauge: drawn and named on the map only. */
  ungauged_rivers?: { name: string; into: string; osm_names: string[] }[];
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
