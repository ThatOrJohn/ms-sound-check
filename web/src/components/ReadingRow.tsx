import type { Reading } from "../lib/types";
import { bandWords, fmtDate, nowRowText, typical } from "../lib/format";
import Sparkline from "./Sparkline";
import Meter from "./Meter";
import YearDots from "./YearDots";

interface Props {
  varName: string;
  label: string;
  r: Reading;
  forecast?: string;   // rain cards: next-7-day total
  retired?: boolean;   // sensor permanently offline
  /** Station pages: today against every year, where a record indicator ranks this reading (decision 0032). */
  years?: boolean;
}

const fmtRange = (lo: number, hi: number, unit = "ppt") => `${Math.round(lo)}–${Math.round(hi)} ${unit}`;

export default function ReadingRow({ varName, label, r, forecast, retired, years }: Props) {
  const offlineSince = r?.date ? fmtDate(r.date, { month: "short", year: "numeric" }) : null;
  // No live reading: show a published estimate, or say plainly that there's nothing to show.
  if (r && (retired || r.stale) && r.estimate) {
    const e = r.estimate;
    return (
      <div className="reading">
        <span className="what">{label}, estimated</span>
        <span className="val est">~{e.display}</span>
        <span className="band">
          Estimated from nearby stations and river flow; likely {fmtRange(e.lo, e.hi)}.
          {offlineSince && ` The sensor here has been offline since ${offlineSince}.`}
        </span>
      </div>
    );
  }
  if (r && retired) {
    return (
      <div className="reading">
        <span className="what">{label}</span>
        <span className="val">—</span>
        <span className="caveat">
          Sensor offline{offlineSince ? ` since ${offlineSince}` : ""}. Nearby stations don't predict this spot well enough to estimate it.
        </span>
      </div>
    );
  }
  if (!r || r.status === "no_data" || !r.display) {
    return (
      <div className="reading">
        <span className="what">{label}</span>
        <span className="val">—</span>
        <span className="caveat">No readings yet</span>
      </div>
    );
  }
  const isRain = varName === "rain";
  const t = typical(varName, r);
  return (
    <div className="reading">
      <span className="what">{isRain ? "Rain, past 7 days" : r.now ? `${label}, daily average` : label}</span>
      <span className="val">{r.display.replace(" past 7 days", "")}</span>
      <Sparkline points={r.spark ?? []} label={label} />
      {r.suspect ? (
        <span className="caveat">
          {r.suspect_reason === "neighbors"
            ? "Doesn't match nearby stations. Possibly a sensor problem; alerts are paused for this reading."
            : "Higher than this water normally gets. Possibly a sensor problem; USGS hasn't reviewed it yet."}
          {r.expected && ` Nearby stations and the rivers suggest about ${r.expected.display}.`}
        </span>
      ) : r.stale && r.date ? (
        <span className="caveat">Station quiet since {fmtDate(r.date, { month: "short", day: "numeric", year: "numeric" })}</span>
      ) : r.band ? (
        <span className="band" data-band={r.band}>
          <Meter percentile={r.percentile} />
          <span>{bandWords(varName, r.band)}{t && ` (typical ${t})`}</span>
        </span>
      ) : null}
      {years && r.years && !r.suspect && !r.stale && <YearDots dots={r.years} varName={varName} unit={r.unit} />}
      {!r.suspect && !r.stale && r.vs_neighbors && r.expected && (
        <span className="extra">
          Reads {r.vs_neighbors === "high" ? "saltier" : "fresher"} than nearby stations suggest (about {r.expected.display}).
        </span>
      )}
      {r.now && <span className="extra" data-live={JSON.stringify({ kind: "row", unit: r.unit, ...r.now })} data-live-text>{nowRowText(r.now, r.unit ?? "")}</span>}
      {forecast && <span className="extra">Next 7 days: {forecast} forecast</span>}
    </div>
  );
}
