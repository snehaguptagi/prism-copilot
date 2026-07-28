// Multi-segment donut chart (pure SVG). Segments tile the ring with a 2px gap
// and each carries a native hover tooltip. Used on the Overview and client
// detail pages for asset-class allocation.
export default function Donut({
  segments,
  centerTop,
  centerSub,
  size = 168,
}: {
  segments: { label: string; pct: number; color: string }[];
  centerTop: string;
  centerSub: string;
  size?: number;
}) {
  const stroke = size < 150 ? 20 : 24;
  const R = (size - stroke) / 2;
  const C = 2 * Math.PI * R;
  const cx = size / 2;
  const cy = size / 2;
  let acc = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="donut" role="img">
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="var(--surface-2)" strokeWidth={stroke} />
      {segments.map((s) => {
        const frac = s.pct / 100;
        const dash = Math.max(frac * C - 2, 0); // 2px surface gap between segments
        const offset = -acc * C;
        acc += frac;
        return (
          <circle
            key={s.label}
            cx={cx}
            cy={cy}
            r={R}
            fill="none"
            stroke={s.color}
            strokeWidth={stroke}
            strokeDasharray={`${dash} ${C - dash}`}
            strokeDashoffset={offset}
            transform={`rotate(-90 ${cx} ${cy})`}
            style={{ transition: "stroke-dasharray 700ms var(--ease-out)" }}
          >
            <title>{`${s.label}: ${s.pct}%`}</title>
          </circle>
        );
      })}
      <text x={cx} y={cy - 3} textAnchor="middle" className="donut-center-top" fill="var(--text)">
        {centerTop}
      </text>
      <text x={cx} y={cy + 15} textAnchor="middle" className="donut-center-sub" fill="var(--text-faint)">
        {centerSub}
      </text>
    </svg>
  );
}
