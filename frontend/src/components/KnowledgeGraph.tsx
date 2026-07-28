import { GraphViewEdge, GraphViewNode } from "@/lib/types";
import { assetClassColor } from "@/lib/colors";

// Hand-rolled radial layout (client at center, asset classes on a ring, held
// and suggested products on an outer ring clustered near their class), same
// house style as Donut/Gauge: plain SVG, native <title> tooltips, no charting
// library. Keeps this consistent with every other chart in the app.
const SIZE = 560;
const CX = SIZE / 2;
const CY = SIZE / 2;
const R_CLASS = 130;
const R_PRODUCT = 235;

function polar(r: number, angleDeg: number) {
  const a = ((angleDeg - 90) * Math.PI) / 180;
  return { x: CX + r * Math.cos(a), y: CY + r * Math.sin(a) };
}

function initialsOf(name: string): string {
  const parts = name.replace("&", " ").split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function KnowledgeGraph({ nodes, edges }: { nodes: GraphViewNode[]; edges: GraphViewEdge[] }) {
  const classNodes = nodes.filter((n) => n.type === "asset_class");
  const otherNodes = nodes.filter((n) => n.type !== "client" && n.type !== "asset_class");
  const clientNode = nodes.find((n) => n.type === "client");

  // Fan classes across a wide arc centered "up" from the client rather than a
  // full 360 degree ring: with few classes (often just 1 or 2), a full-circle
  // split lands one directly opposite another, isolated and disconnected-
  // looking. An arc keeps every layout, regardless of class count, reading as
  // one coherent fan rather than a scatter.
  const ARC = 260;
  const classAngle: Record<string, number> = {};
  classNodes.forEach((n, i) => {
    const t = classNodes.length === 1 ? 0.5 : i / (classNodes.length - 1);
    classAngle[n.id] = -ARC / 2 + ARC * t;
  });

  const byClass: Record<string, GraphViewNode[]> = {};
  otherNodes.forEach((n) => {
    const clsId = `class:${n.asset_class}`;
    (byClass[clsId] ||= []).push(n);
  });

  const positions: Record<string, { x: number; y: number }> = { client: { x: CX, y: CY } };
  classNodes.forEach((n) => {
    positions[n.id] = polar(R_CLASS, classAngle[n.id]);
  });
  Object.entries(byClass).forEach(([clsId, list]) => {
    const baseAngle = classAngle[clsId] ?? 0;
    const spread = Math.min(20 * list.length, 70);
    list.forEach((n, i) => {
      const t = list.length === 1 ? 0.5 : i / (list.length - 1);
      positions[n.id] = polar(R_PRODUCT, baseAngle - spread / 2 + spread * t);
    });
  });

  function nodeRadius(n: GraphViewNode) {
    if (n.type === "client") return 26;
    if (n.type === "asset_class") return 15;
    if (n.best) return 14;
    return 9;
  }

  function nodeFill(n: GraphViewNode) {
    if (n.type === "client") return "var(--accent)";
    if (n.type === "asset_class") return assetClassColor(n.label);
    return assetClassColor(n.asset_class || "");
  }

  function edgeStroke(e: GraphViewEdge) {
    if (e.kind === "in_class") return "var(--border-strong)";
    if (e.kind === "holds") return "var(--text-faint)";
    return "var(--accent)"; // suggests
  }

  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="kg-svg" role="img">
      {edges.map((e, i) => {
        const s = positions[e.source];
        const t = positions[e.target];
        if (!s || !t) return null;
        const targetNode = nodes.find((n) => n.id === e.target);
        const isBest = e.kind === "suggests" && targetNode?.best;
        return (
          <line
            key={i}
            x1={s.x}
            y1={s.y}
            x2={t.x}
            y2={t.y}
            stroke={isBest ? "var(--sev-elevated)" : edgeStroke(e)}
            strokeWidth={isBest ? 2.5 : e.kind === "in_class" ? 1 : 1.5}
            strokeDasharray={e.kind === "in_class" ? "3 3" : e.kind === "suggests" ? "5 3" : undefined}
            opacity={e.kind === "in_class" ? 0.4 : isBest ? 0.9 : 0.55}
          />
        );
      })}

      {classNodes.map((n) => {
        const pos = positions[n.id];
        if (!pos) return null;
        return (
          <g key={n.id}>
            <circle cx={pos.x} cy={pos.y} r={nodeRadius(n)} fill={nodeFill(n)} stroke="var(--surface)" strokeWidth={2}>
              <title>{n.label}</title>
            </circle>
            <text
              x={pos.x}
              y={pos.y - nodeRadius(n) - 7}
              textAnchor="middle"
              className="kg-class-label"
              fill="var(--text-secondary)"
            >
              {n.label}
            </text>
          </g>
        );
      })}

      {otherNodes.map((n) => {
        const pos = positions[n.id];
        if (!pos) return null;
        const r = nodeRadius(n);
        const tooltip = [n.label, n.sub, n.rationale].filter(Boolean).join(" – ");
        return (
          <g key={n.id} className={n.best ? "kg-best-node" : undefined}>
            {n.best && (
              <circle cx={pos.x} cy={pos.y} r={r + 7} fill="none" stroke="var(--sev-elevated)" strokeWidth={2} className="kg-pulse" />
            )}
            <circle
              cx={pos.x}
              cy={pos.y}
              r={r}
              fill={nodeFill(n)}
              stroke={n.type === "held" ? "var(--surface)" : "var(--sev-elevated)"}
              strokeWidth={n.best ? 2.5 : n.type === "suggested" ? 1.5 : 2}
              opacity={n.type === "held" ? 0.85 : 1}
            >
              <title>{tooltip}</title>
            </circle>
          </g>
        );
      })}

      {clientNode && (
        <g>
          <circle cx={CX} cy={CY} r={nodeRadius(clientNode)} fill={nodeFill(clientNode)} stroke="var(--surface)" strokeWidth={3}>
            <title>{clientNode.label}{clientNode.sub ? ` – ${clientNode.sub} mandate` : ""}</title>
          </circle>
          <text x={CX} y={CY + 4} textAnchor="middle" className="kg-client-initials" fill="#ffffff">
            {initialsOf(clientNode.label)}
          </text>
          <text x={CX} y={CY + nodeRadius(clientNode) + 16} textAnchor="middle" className="kg-client-name" fill="var(--text)">
            {clientNode.label}
          </text>
        </g>
      )}
    </svg>
  );
}
