import type { YearDots as Dots } from "../lib/types";

// Today against every year (decision 0032): one dot per year for today's date, today ringed, the highest and lowest
// years named, the middle half of the years shaded. Plain SVG drawn at build time; lib/yeardots.ts adds the hover
// and tap readout. The sentence under it is the text alternative, and it uses the record indicator's own ranks.

interface Props { dots: Dots; varName: string; unit?: string; small?: boolean }

const W = 300, R = 3.4, PAD = 16;
const ORD = (n: number) => n === 1 ? "" : `${n}${n % 100 >= 11 && n % 100 <= 13 ? "th" : ["th", "st", "nd", "rd"][n % 10] ?? "th"} `;

export function fmtValue(v: number, varName: string, unit = ""): string {
  if (varName === "flow") return `${Math.round(v).toLocaleString("en-US")} ${unit}`.trim();
  return `${v.toFixed(1)} ${unit}`.trim();
}

/** "14-day average 26.2 ppt: 3rd highest of 14 years for late October" ("lowest" when today sits in the bottom half).
 *  Short form, where the reading is already shown beside it: "3rd highest of 14 years for late October". The dots are
 *  window averages, so the long form says so rather than show a second number that looks like today's. */
export function rankSentence(d: Dots, varName: string, unit?: string, short = false): string {
  const now = d.points.at(-1)![1];
  const high = d.rank_high <= d.rank_low;
  const rank = `${ORD(high ? d.rank_high : d.rank_low)}${high ? "highest" : "lowest"} of ${d.of} years for ${d.season.replace("-", " ")}`;
  return short ? rank[0].toUpperCase() + rank.slice(1) : `${d.window}-day average ${fmtValue(now, varName, unit)}: ${rank}`;
}

export default function YearDots({ dots, varName, unit, small }: Props) {
  const pts = dots.points;
  const log = varName === "flow" && pts.every(([, v]) => v > 0);
  const f = (v: number) => (log ? Math.log10(v) : v);
  const vals = pts.map(([, v]) => f(v));
  const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
  const x = (v: number) => PAD + ((f(v) - lo) / span) * (W - 2 * PAD);
  const sorted = [...vals].sort((a, b) => a - b);
  const q = (p: number) => sorted[Math.min(sorted.length - 1, Math.floor(p * (sorted.length - 1) + 0.5))];
  const band = [PAD + ((q(0.25) - lo) / span) * (W - 2 * PAD), PAD + ((q(0.75) - lo) / span) * (W - 2 * PAD)];
  // A small beeswarm: each dot takes the first lane (center, then alternating out) where it doesn't touch a neighbor.
  const lanes = [0, -1, 1, -2, 2, -3, 3];
  const placed: { cx: number; lane: number }[] = [];
  const order = pts.map((p, i) => ({ i, cx: x(p[1]) })).sort((a, b) => a.cx - b.cx);
  const laneOf = new Map<number, number>();
  for (const { i, cx } of order) {
    const lane = lanes.find((l) => !placed.some((p) => p.lane === l && Math.abs(p.cx - cx) < 2 * R + 0.6)) ?? 0;
    placed.push({ cx, lane });
    laneOf.set(i, lane);
  }
  const used = Math.max(1, ...[...laneOf.values()].map(Math.abs));
  const mid = R * 2 * used + R + 2, H = mid * 2 + 12;
  const now = pts.length - 1;
  const iMin = vals.indexOf(lo), iMax = vals.indexOf(hi);
  const say = rankSentence(dots, varName, unit, small);
  return (
    <div className={`yeardots${small ? " yeardots-sm" : ""}`} data-default={say}>
      <svg viewBox={`0 0 ${W} ${H}`} aria-hidden="true" focusable="false">
        <rect className="yd-typ" x={band[0]} y={2} width={Math.max(1, band[1] - band[0])} height={mid * 2 - 4} rx={3} />
        <line className="yd-axis" x1={PAD} x2={W - PAD} y1={mid} y2={mid} />
        {pts.map(([yr, v], i) => i === now ? null : (
          <circle key={yr} cx={x(v)} cy={mid + laneOf.get(i)! * 2 * R} r={R} data-say={`${yr}: ${fmtValue(v, varName, unit)}`}>
            <title>{`${yr}: ${fmtValue(v, varName, unit)}`}</title>
          </circle>
        ))}
        <circle className="yd-now" cx={x(pts[now][1])} cy={mid + laneOf.get(now)! * 2 * R} r={R + 1.6}
          data-say={`${pts[now][0]}, now: ${fmtValue(pts[now][1], varName, unit)}`}>
          <title>{`${pts[now][0]}, now: ${fmtValue(pts[now][1], varName, unit)}`}</title>
        </circle>
        {[iMin, iMax].filter((i, k, a) => i !== now && a.indexOf(i) === k).map((i) => (
          <text key={i} x={x(pts[i][1])} y={H - 1} textAnchor={i === iMin ? "start" : "end"} dx={i === iMin ? -R : R}>
            {`${pts[i][0]} ${i === iMin ? "lowest" : "highest"}`}
          </text>
        ))}
      </svg>
      <p className="yd-say"><span className="yd-read">{say}</span></p>
    </div>
  );
}
