import type { Card, Finding } from "../lib/types";
import { SEV_RANK, fmtDate } from "../lib/format";

interface Props {
  cards: Card[];
  findings: Finding[];
  siteHref: (slug: string) => string;
}

/** Salinity -> color, mixed in CSS so it follows the light/dark theme. */
export function salinityFill(v: number): string {
  if (v <= 12) {
    const t = Math.max(0, Math.min(100, (v / 12) * 100));
    return `color-mix(in oklab, var(--brackish) ${t.toFixed(0)}%, var(--fresh))`;
  }
  const t = Math.max(0, Math.min(100, ((v - 12) / 13) * 100));
  return `color-mix(in oklab, var(--gulf) ${t.toFixed(0)}%, var(--brackish))`;
}

// Schematic frame: west (Pearl) to east (Pascagoula). Not to scale.
const W = 1000, LON_W = -89.62, LON_E = -88.48, LAT_N = 30.42, LAT_S = 30.16;
const x = (lon: number) => 30 + ((lon - LON_W) / (LON_E - LON_W)) * (W - 60);
const y = (lat: number) => 92 + ((LAT_N - lat) / (LAT_N - LAT_S)) * 120;
const MOUTHS: Record<string, [number, number]> = {
  "USGS-02489500": [-89.58, 30.24],  // Pearl
  "USGS-02479000": [-88.57, 30.36],  // Pascagoula
};
const ISLANDS: [number, number, number, string][] = [
  [-89.17, -89.06, 30.225, "Cat Island"],
  [-88.99, -88.86, 30.21, "Ship Island"],
  [-88.79, -88.57, 30.235, "Horn Island"],
];
const FLOW_WORDS: Record<string, string> = { low: "very low", below: "a bit low", normal: "normal", above: "a bit high", high: "very high" };

export default function SoundStrip({ cards, findings, siteHref }: Props) {
  const alerting = new Set(findings.filter((f) => f.site && SEV_RANK[f.severity] >= 2).map((f) => f.site));
  const rivers = cards.filter((c) => c.kind === "river");
  const stations = cards.filter((c) => c.kind === "sound" || c.kind === "estuary");

  return (
    <figure className="strip" aria-labelledby="strip-cap">
      <svg viewBox="0 0 1000 262" role="group" aria-labelledby="strip-cap">
        <rect className="land" x={0} y={0} width={W} height={86} />
        <rect className="sound" x={0} y={86} width={W} height={176} />
        <text className="place" x={x(-89.32)} y={40}>Bay St. Louis</text>
        <text className="place" x={x(-89.09)} y={40}>Gulfport</text>
        <text className="place" x={x(-88.9)} y={40}>Biloxi</text>
        <text className="place" x={x(-88.7)} y={64}>Pascagoula</text>
        {ISLANDS.map(([w, e, lat, name]) => (
          <g key={name} aria-hidden="true">
            <rect className="island" x={x(w)} y={y(lat) + 26} width={x(e) - x(w)} height={9} rx={4.5} />
            <text className="lbl-soft" x={x(w)} y={y(lat) + 54}>{name}</text>
          </g>
        ))}
        {rivers.map((r) => {
          const v = r.vars.flow ?? {};
          const [mlon, mlat] = MOUTHS[r.id] ?? [r.lon, 30.35];
          const width = 4 + ((v.percentile ?? 50) / 100) * 22;
          const mx = x(mlon), my = y(mlat);
          const east = mx > W / 2;
          const tx = east ? mx - width / 2 - 8 : mx + width / 2 + 8;
          const label = v.display ? `${v.display}${v.band ? `, ${FLOW_WORDS[v.band]}` : ""}` : "no recent data";
          return (
            <a key={r.id} href={siteHref(r.slug)} aria-label={`${r.name}: ${label}. Open station page.`}>
              <path className="river" strokeWidth={width} d={`M ${mx} 0 C ${mx} ${my * 0.5}, ${mx} ${my * 0.7}, ${mx} ${my}`} />
              <text className="lbl" x={tx} y={22} textAnchor={east ? "end" : "start"}>{r.short}</text>
              <text className="lbl-soft" x={tx} y={40} textAnchor={east ? "end" : "start"}>{label}</text>
            </a>
          );
        })}
        {stations.map((c) => {
          const v = c.vars.salinity ?? {};
          const live = v.value !== undefined && !v.stale;
          const cx = x(c.lon), cy = y(c.lat);
          const right = cx < W - 190;
          const tx = right ? cx + 22 : cx - 22;
          const sub = live
            ? `${v.display}${v.suspect ? " (check)" : ""}`
            : v.date ? `quiet since ${fmtDate(v.date, { month: "short", day: "numeric" })}` : "no data";
          return (
            <a key={c.id} href={siteHref(c.slug)} aria-label={`${c.name}: salinity ${sub}. Open station page.`}>
              {alerting.has(c.id) && <circle className="ring" cx={cx} cy={cy} r={20} />}
              <circle className={`stn${live ? "" : " quiet"}`} cx={cx} cy={cy} r={13}
                style={live && v.value !== undefined ? { fill: salinityFill(v.value) } : undefined} />
              <text className="lbl" x={tx} y={cy - 2} textAnchor={right ? "start" : "end"}>{c.short}</text>
              <text className="lbl-soft" x={tx} y={cy + 16} textAnchor={right ? "start" : "end"}>{sub}</text>
            </a>
          );
        })}
      </svg>
      {/* Phones: the same picture as a west-to-east list. */}
      <ol className="strip-list">
        {[...rivers, ...stations].sort((a, b) => a.lon - b.lon).map((c) => {
          const isRiver = c.kind === "river";
          const v = (isRiver ? c.vars.flow : c.vars.salinity) ?? {};
          const live = v.value !== undefined && !v.stale;
          const chip = isRiver ? "var(--fresh)" : live && v.value !== undefined ? salinityFill(v.value) : "var(--rule)";
          const sub = !live
            ? v.date ? `quiet since ${fmtDate(v.date, { month: "short", day: "numeric" })}` : "no data"
            : isRiver ? `${v.display}${v.band ? `, ${FLOW_WORDS[v.band]}` : ""}` : `${v.display}${v.suspect ? " (check)" : ""}`;
          return (
            <li key={c.id} className={isRiver ? "is-river" : undefined}>
              <span className="chip" style={{ background: chip }} aria-hidden="true" />
              <a href={siteHref(c.slug)}>{c.short}</a>
              <span className="sub">{sub}{alerting.has(c.id) ? ", alert" : ""}</span>
            </li>
          );
        })}
      </ol>
      <figcaption className="strip-foot">
        <span id="strip-cap">The Sound from the Pearl River to the Pascagoula. Stations are colored by salinity; rivers are drawn wider when they run high. Not to scale.</span>
        <span className="scale" aria-hidden="true">Fresh <span className="scale-bar" /> Gulf salty</span>
      </figcaption>
    </figure>
  );
}
