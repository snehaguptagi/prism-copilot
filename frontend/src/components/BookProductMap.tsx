import { OverviewGraphResult } from "@/lib/types";
import { assetClassColor } from "@/lib/colors";

// Firm-wide flow: clients -> asset classes -> products, three fixed columns.
// Product node radius scales with client_count, so the diagram itself shows
// where cross-sell demand concentrates across the whole book at a glance.
// Same house style as the other hand-rolled SVG charts: plain SVG, native
// <title> tooltips, no charting library.
const COL_W = 880;
const X_CLIENT = 190; // leaves room for client-name labels anchored left of the column
const X_CLASS = 440;
const X_PRODUCT = 690; // leaves room for product-name labels to the right
const ROW_H = 30;
const TOP_PAD = 30;

function colX(pos: { x: number; y: number }) {
  return pos.x;
}

export default function BookProductMap({ data }: { data: OverviewGraphResult }) {
  const rows = Math.max(data.clients.length, data.classes.length, data.products.length);
  const height = TOP_PAD * 2 + rows * ROW_H;

  function evenY(index: number, count: number) {
    if (count <= 1) return height / 2;
    const span = (count - 1) * ROW_H;
    const start = (height - span) / 2;
    return start + index * ROW_H;
  }

  const positions: Record<string, { x: number; y: number }> = {};
  data.clients.forEach((c, i) => {
    positions[c.id] = { x: X_CLIENT, y: evenY(i, data.clients.length) };
  });
  data.classes.forEach((c, i) => {
    positions[c.id] = { x: X_CLASS, y: evenY(i, data.classes.length) };
  });
  data.products.forEach((p, i) => {
    positions[p.id] = { x: X_PRODUCT, y: evenY(i, data.products.length) };
  });

  const maxCount = Math.max(...data.products.map((p) => p.client_count), 1);

  function curve(a: { x: number; y: number }, b: { x: number; y: number }) {
    const mx = (a.x + b.x) / 2;
    return `M ${a.x} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`;
  }

  return (
    <svg viewBox={`0 0 ${COL_W} ${height}`} className="bpm-svg" role="img">
      {data.edges_client_class.map((e, i) => {
        const s = positions[e.source];
        const t = positions[e.target];
        if (!s || !t) return null;
        const cls = data.classes.find((c) => c.id === e.target);
        return (
          <path
            key={`cc-${i}`}
            d={curve(s, t)}
            fill="none"
            stroke={cls ? assetClassColor(cls.label) : "var(--border-strong)"}
            strokeWidth={1.2}
            opacity={0.28}
          />
        );
      })}
      {data.edges_class_product.map((e, i) => {
        const s = positions[e.source];
        const t = positions[e.target];
        if (!s || !t) return null;
        const cls = data.classes.find((c) => c.id === e.source);
        return (
          <path
            key={`cp-${i}`}
            d={curve(s, t)}
            fill="none"
            stroke={cls ? assetClassColor(cls.label) : "var(--accent)"}
            strokeWidth={Math.min(1 + e.weight * 0.9, 5)}
            opacity={0.45}
          />
        );
      })}

      {data.clients.map((c) => {
        const pos = positions[c.id];
        if (!pos) return null;
        return (
          <g key={c.id}>
            <circle cx={colX(pos)} cy={pos.y} r={6} fill="var(--accent)" stroke="var(--surface)" strokeWidth={1.5}>
              <title>{c.label}{c.best_match ? ` – best match: ${c.best_match}` : " – no match found"}</title>
            </circle>
            <text x={pos.x - 12} y={pos.y + 3.5} textAnchor="end" className="bpm-client-label">
              {c.label}
            </text>
          </g>
        );
      })}

      {data.classes.map((cls) => {
        const pos = positions[cls.id];
        if (!pos) return null;
        return (
          <g key={cls.id}>
            <circle cx={pos.x} cy={pos.y} r={14} fill={assetClassColor(cls.label)} stroke="var(--surface)" strokeWidth={2}>
              <title>{cls.label}</title>
            </circle>
            <text x={pos.x} y={pos.y - 20} textAnchor="middle" className="bpm-class-label">
              {cls.label}
            </text>
          </g>
        );
      })}

      {data.products.map((p) => {
        const pos = positions[p.id];
        if (!pos) return null;
        const r = 8 + (p.client_count / maxCount) * 12;
        return (
          <g key={p.id}>
            {p.confirmed && (
              <circle cx={pos.x} cy={pos.y} r={r + 5} fill="none" stroke="var(--sev-elevated)" strokeWidth={1.5} opacity={0.55} />
            )}
            <circle
              cx={pos.x}
              cy={pos.y}
              r={r}
              fill={assetClassColor(p.asset_class)}
              stroke="var(--surface)"
              strokeWidth={2}
            >
              <title>
                {p.label} ({p.ticker}) – best match for {p.client_count} client{p.client_count !== 1 ? "s" : ""}:{" "}
                {p.client_names.join(", ")}
              </title>
            </circle>
            <text x={pos.x + r + 8} y={pos.y + 3.5} textAnchor="start" className="bpm-product-label">
              {p.label}
              <tspan className="bpm-product-count"> · {p.client_count}</tspan>
            </text>
          </g>
        );
      })}
    </svg>
  );
}
