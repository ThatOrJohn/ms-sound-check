import type { Card, Finding } from "../lib/types";
import { SEV_RANK, fmtDate } from "../lib/format";
import { salinityFill } from "../lib/salinity";

interface Props { cards: Card[]; findings: Finding[]; siteHref: (slug: string) => string }
const FLOW_WORDS: Record<string, string> = { low: "very low", below: "a bit low", normal: "normal", above: "a bit high", high: "very high" };

/** West-to-east list of rivers and stations: the accessible, at-a-glance companion to the map. */
export default function StationList({ cards, findings, siteHref }: Props) {
  const alerting = new Set(findings.filter((f) => f.site && SEV_RANK[f.severity] >= 2).map((f) => f.site));
  const items = cards.filter((c) => ["river", "sound", "estuary"].includes(c.kind)).sort((a, b) => a.lon - b.lon);
  return (
    <ol className="station-list" aria-label="Rivers and stations, west to east">
      {items.map((c) => {
        const isRiver = c.kind === "river";
        const v = (isRiver ? c.vars.flow : c.vars.salinity) ?? {};
        const live = v.value !== undefined && !v.stale && !c.retired;
        const est = !live && v.estimate ? v.estimate : null;
        const chip = isRiver ? "var(--fresh)" : live && v.value !== undefined ? salinityFill(v.value) : est ? salinityFill(est.value) : "var(--rule)";
        const sub = est ? `~${est.display}, estimated`
          : c.retired ? "sensor offline"
          : !live ? v.date ? `quiet since ${fmtDate(v.date, { month: "short", day: "numeric" })}` : "no data"
          : isRiver ? `${v.display}${v.band ? `, ${FLOW_WORDS[v.band]}` : ""}` : `${v.display}${v.suspect ? " (check)" : ""}`;
        return (
          <li key={c.id} className={[isRiver ? "is-river" : "", est ? "is-est" : ""].join(" ").trim() || undefined}>
            <span className="chip" style={est ? { borderColor: chip } : { background: chip }} aria-hidden="true" />
            <a href={siteHref(c.slug)}>{c.short}</a>
            <span className="sub">{sub}{alerting.has(c.id) ? ", alert" : ""}</span>
          </li>
        );
      })}
    </ol>
  );
}
