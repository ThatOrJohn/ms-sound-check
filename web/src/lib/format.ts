import type { Band, Finding, Persona, Reading } from "./types";

/** Join a path onto the configured base (works under /<repo>/ on GitHub Pages). */
export function href(p = ""): string {
  const base = import.meta.env.BASE_URL.replace(/\/?$/, "/");
  return base + p.replace(/^\//, "");
}

export const personaPath = (id: string) => (id === "general" ? href() : href(`for/${id}/`));

export function fmtDate(iso: string, opts: Intl.DateTimeFormatOptions = { month: "long", day: "numeric", year: "numeric" }) {
  const d = new Date(iso.length === 10 ? `${iso}T12:00:00` : iso);
  return d.toLocaleDateString("en-US", opts);
}

export const SEV_RANK: Record<string, number> = { alert: 4, warning: 3, watch: 2, notice: 1 };
export const SEV_LABEL: Record<string, string> = { alert: "Alert", warning: "Warning", watch: "Watch", notice: "Note" };

export function forPersona(findings: Finding[], persona: Persona): Finding[] {
  const rank = (f: Finding) => Math.min(...f.topics.map((t) => { const i = persona.focus.indexOf(t); return i < 0 ? 99 : i; }));
  return findings
    .filter((f) => f.topics.some((t) => persona.focus.includes(t)))
    .sort((a, b) => (SEV_RANK[b.severity] - SEV_RANK[a.severity]) || (rank(a) - rank(b)));
}

const WORDS: Record<string, Record<Band, string>> = {
  salinity:   { low: "Much fresher than usual", below: "A bit fresher than usual", normal: "About normal", above: "A bit saltier than usual", high: "Much saltier than usual" },
  water_temp: { low: "Much colder than usual", below: "A bit colder than usual", normal: "About normal", above: "A bit warmer than usual", high: "Much warmer than usual" },
  air_temp:   { low: "Much colder than usual", below: "A bit colder than usual", normal: "About normal", above: "A bit warmer than usual", high: "Much warmer than usual" },
  flow:       { low: "Running very low", below: "Running a bit low", normal: "About normal", above: "Running a bit high", high: "Running very high" },
  rain:       { low: "Much drier than usual", below: "A bit drier than usual", normal: "About normal", above: "A bit wetter than usual", high: "Much wetter than usual" },
};

export function bandWords(varName: string, band?: Band): string {
  if (!band) return "";
  return WORDS[varName.startsWith("rain") ? "rain" : varName]?.[band] ?? "";
}

export function typical(varName: string, r: Reading): string {
  const v = r.normal?.p50;
  if (v === undefined || v === null) return "";
  const u = r.unit ?? "";
  if (varName === "flow") return `${Math.round(v).toLocaleString("en-US")} ${u}`;
  if (varName.endsWith("temp")) return `${Math.round(v)}${u}`;
  if (varName.startsWith("rain")) return `${v.toFixed(2)} ${u}`;
  return `${v.toFixed(1)} ${u}`;
}

export const GROUPS: Record<string, { title: string; blurb: string }> = {
  sound:   { title: "Out in the Sound", blurb: "Salinity and water temperature at the monitoring lights and in Back Bay." },
  estuary: { title: "River mouths", blurb: "Where river water meets the Sound. Salt here means the rivers are low." },
  river:   { title: "Rivers feeding the Sound", blurb: "When these run high the Sound turns fresher, and stays that way while they stay up." },
  rain:    { title: "Rain", blurb: "Rain upstream reaches the rivers days later. Basin totals are approximate." },
  weather: { title: "On the coast", blurb: "" },
};
