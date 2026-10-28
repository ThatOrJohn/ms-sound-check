import type { Reading } from "../lib/types";
import { bandWords, fmtDate, typical } from "../lib/format";
import Sparkline from "./Sparkline";

interface Props {
  varName: string;
  label: string;
  r: Reading;
  forecast?: string;   // rain cards: next-7-day total
}

export default function ReadingRow({ varName, label, r, forecast }: Props) {
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
      <span className="what">{isRain ? "Rain, past 7 days" : label}</span>
      <span className="val">{r.display.replace(" past 7 days", "")}</span>
      <Sparkline points={r.spark ?? []} label={label} />
      {r.suspect ? (
        <span className="caveat">Higher than this water normally gets. Possibly a sensor problem; USGS hasn't reviewed it yet.</span>
      ) : r.stale && r.date ? (
        <span className="caveat">Station quiet since {fmtDate(r.date, { month: "short", day: "numeric", year: "numeric" })}</span>
      ) : r.band ? (
        <span className="band" data-band={r.band}>{bandWords(varName, r.band)}{t && ` (typical ${t})`}</span>
      ) : null}
      {forecast && <span className="extra">Next 7 days: {forecast} forecast</span>}
    </div>
  );
}
