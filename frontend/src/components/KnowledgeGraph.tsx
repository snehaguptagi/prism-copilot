"use client";

import { useMemo, useState } from "react";
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
  // Same interaction contract as the whole-book map: hover or focus traces a
  // node's connections and dims the rest, click or Enter pins that trace,
  // Escape releases. Native <title> tooltips alone made the viewer interrogate
  // one dot at a time, which is the wrong shape of work for a graph.
  const [hover, setHover] = useState<string | null>(null);
  const [pinned, setPinned] = useState<string | null>(null);
  const active = pinned ?? hover;

  const lit = useMemo(() => {
    if (!active) return null;
    const litNodes = new Set<string>([active]);
    const litEdges = new Set<number>();
    edges.forEach((e, i) => {
      if (e.source === active || e.target === active) {
        litEdges.add(i);
        litNodes.add(e.source);
        litNodes.add(e.target);
      }
    });
    return { litNodes, litEdges };
  }, [active, edges]);

  const dimNode = (id: string) => (lit ? !lit.litNodes.has(id) : false);
  const dimEdge = (i: number) => (lit ? !lit.litEdges.has(i) : false);
  const select = (id: string) => setPinned((cur) => (cur === id ? null : id));

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

  // Crop the viewBox to the content's actual bounding box, rather than a fixed
  // square: the arc fan only ever occupies part of a full circle, so a fixed
  // canvas left a lot of dead space below and to the sides. Each node type
  // gets an allowance for what renders around it (labels, the pulse ring).
  const classIds = new Set(classNodes.map((n) => n.id));
  function allowance(id: string) {
    if (id === "client") return { top: 30, bottom: 56, left: 34, right: 34 };
    if (classIds.has(id)) return { top: 30, bottom: 20, left: 24, right: 24 };
    return { top: 22, bottom: 22, left: 22, right: 22 };
  }
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  Object.entries(positions).forEach(([id, pos]) => {
    const a = allowance(id);
    minX = Math.min(minX, pos.x - a.left);
    maxX = Math.max(maxX, pos.x + a.right);
    minY = Math.min(minY, pos.y - a.top);
    maxY = Math.max(maxY, pos.y + a.bottom);
  });
  const viewBox = `${minX} ${minY} ${maxX - minX} ${maxY - minY}`;

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

  const activeNode = active ? nodes.find((n) => n.id === active) : null;
  const readout = activeNode
    ? [activeNode.label, activeNode.sub, activeNode.rationale].filter(Boolean).join(". ")
    : "Hover or tab to any node to trace what it connects to. Click to pin.";

  return (
    <div className="kg" onMouseLeave={() => setHover(null)}>
    <svg
      viewBox={viewBox}
      className={`kg-svg${lit ? " has-focus" : ""}`}
      role="application"
      aria-label="Product fit graph: this client, the asset classes they hold, and held and suggested products."
      onKeyDown={(e) => e.key === "Escape" && (setPinned(null), setHover(null))}
    >
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
            className={`kg-edge${e.kind === "in_class" ? " faint" : isBest ? " best" : ""}${dimEdge(i) ? " dim" : ""}`}
          />
        );
      })}

      {classNodes.map((n) => {
        const pos = positions[n.id];
        if (!pos) return null;
        return (
          <g
            key={n.id}
            className={`kg-node${dimNode(n.id) ? " dim" : ""}${pinned === n.id ? " pinned" : ""}`}
            tabIndex={0}
            role="button"
            aria-label={`Asset class ${n.label}`}
            onMouseEnter={() => setHover(n.id)}
            onFocus={() => setHover(n.id)}
            onBlur={() => setHover(null)}
            onClick={() => select(n.id)}
            onKeyDown={(e) => e.key === "Enter" && select(n.id)}
          >
            <circle cx={pos.x} cy={pos.y} r={nodeRadius(n) + 8} className="kg-hit" />
            <circle cx={pos.x} cy={pos.y} r={nodeRadius(n)} fill={nodeFill(n)} stroke="var(--surface)" strokeWidth={2} />
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
        return (
          <g
            key={n.id}
            className={`kg-node${n.best ? " kg-best-node" : ""}${dimNode(n.id) ? " dim" : ""}${
              pinned === n.id ? " pinned" : ""
            }`}
            tabIndex={0}
            role="button"
            aria-label={[n.label, n.sub, n.rationale].filter(Boolean).join(". ")}
            onMouseEnter={() => setHover(n.id)}
            onFocus={() => setHover(n.id)}
            onBlur={() => setHover(null)}
            onClick={() => select(n.id)}
            onKeyDown={(e) => e.key === "Enter" && select(n.id)}
          >
            <circle cx={pos.x} cy={pos.y} r={r + 9} className="kg-hit" />
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
            />
          </g>
        );
      })}

      {clientNode && (
        <g
          className={`kg-node${dimNode(clientNode.id) ? " dim" : ""}${pinned === clientNode.id ? " pinned" : ""}`}
          tabIndex={0}
          role="button"
          aria-label={`${clientNode.label}${clientNode.sub ? `, ${clientNode.sub} mandate` : ""}`}
          onMouseEnter={() => setHover(clientNode.id)}
          onFocus={() => setHover(clientNode.id)}
          onBlur={() => setHover(null)}
          onClick={() => select(clientNode.id)}
          onKeyDown={(e) => e.key === "Enter" && select(clientNode.id)}
        >
          <circle cx={CX} cy={CY} r={nodeRadius(clientNode) + 6} className="kg-hit" />
          <circle cx={CX} cy={CY} r={nodeRadius(clientNode)} fill={nodeFill(clientNode)} stroke="var(--surface)" strokeWidth={3} />
          <text x={CX} y={CY + 4} textAnchor="middle" className="kg-client-initials" fill="#ffffff">
            {initialsOf(clientNode.label)}
          </text>
          <text x={CX} y={CY + nodeRadius(clientNode) + 16} textAnchor="middle" className="kg-client-name" fill="var(--text)">
            {clientNode.label}
          </text>
        </g>
      )}
    </svg>

      <div className="kg-readout" aria-live="polite">
        {pinned && <span className="bpm-pin-tag">Pinned</span>}
        {readout}
      </div>
    </div>
  );
}
