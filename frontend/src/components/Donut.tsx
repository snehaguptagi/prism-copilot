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
  const renderedSegments = segments.reduce<{
    total: number;
    items: { label: string; pct: number; color: string; dash: number; offset: number }[];
  }>(
    (state, segment) => {
      const fraction = segment.pct / 100;
      return {
        total: state.total + fraction,
        items: [
          ...state.items,
          {
            ...segment,
            dash: Math.max(fraction * C - 2, 0),
            offset: -state.total * C,
          },
        ],
      };
    },
    { total: 0, items: [] },
  ).items;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="donut" role="img">
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="var(--surface-2)" strokeWidth={stroke} />
      {renderedSegments.map((segment) => (
        <circle
          key={segment.label}
          cx={cx}
          cy={cy}
          r={R}
          fill="none"
          stroke={segment.color}
          strokeWidth={stroke}
          strokeDasharray={`${segment.dash} ${C - segment.dash}`}
          strokeDashoffset={segment.offset}
          transform={`rotate(-90 ${cx} ${cy})`}
          style={{ transition: "stroke-dasharray 700ms var(--ease-out)" }}
        >
          <title>{`${segment.label}: ${segment.pct}%`}</title>
        </circle>
      ))}
      <text x={cx} y={cy - 3} textAnchor="middle" className="donut-center-top" fill="var(--text)">
        {centerTop}
      </text>
      <text x={cx} y={cy + 15} textAnchor="middle" className="donut-center-sub" fill="var(--text-faint)">
        {centerSub}
      </text>
    </svg>
  );
}
