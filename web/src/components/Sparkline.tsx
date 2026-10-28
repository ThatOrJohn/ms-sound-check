interface Props { points: [string, number | null][]; label: string }

/** 30-day trend; the dot marks the latest reading. */
export default function Sparkline({ points, label }: Props) {
  const vals = points.map((p) => p[1]).filter((v): v is number => v !== null);
  if (vals.length < 3) return null;
  const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
  const n = Math.max(1, points.length - 1);
  let d = "", pen = false, last: [number, number] | null = null;
  points.forEach(([, v], i) => {
    if (v === null) { pen = false; return; }
    const px = (i / n) * 100, py = 28 - ((v - lo) / span) * 26;
    d += `${pen ? "L" : "M"}${px.toFixed(1)},${py.toFixed(1)} `;
    pen = true; last = [px, py];
  });
  const end = last as [number, number] | null;
  return (
    <svg className="spark" viewBox="0 0 100 30" role="img" aria-label={`${label}, past 30 days`}>
      <path d={d} />
      {end && <circle cx={end[0]} cy={end[1]} r={2.4} />}
    </svg>
  );
}
