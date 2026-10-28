interface Props { percentile?: number; small?: boolean }

/** Where today's reading sits among every year's readings for this date: 0 = lowest, 100 = highest.
 *  The shaded middle is the typical half (25th to 75th percentile). Decorative; the band words carry the meaning. */
export default function Meter({ percentile, small }: Props) {
  if (percentile === undefined || percentile === null || Number.isNaN(percentile)) return null;
  const p = Math.max(0, Math.min(100, percentile));
  const off = p < 10 || p > 90 ? "far" : p < 25 || p > 75 ? "off" : "in";
  return (
    <span className={`meter${small ? " meter-sm" : ""}`} data-pos={off} aria-hidden="true">
      <span className="meter-typ" />
      <span className="meter-mid" />
      <span className="meter-dot" style={{ left: `${p}%` }} />
    </span>
  );
}
