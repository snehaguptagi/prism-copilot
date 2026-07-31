"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { GraphViewEdge, GraphViewNode } from "@/lib/types";
import { assetClassColor } from "@/lib/colors";

// Hand-rolled radial layout (client at centre, asset classes on a ring, held and
// suggested products on an outer ring clustered near their class), same house
// style as Donut/Gauge: plain SVG, no charting library.
//
// Interaction added on top of the static layout:
//   - hover or focus a node -> focus+context. Its edges and neighbours stay lit,
//     everything else drops to 18% so a single relationship is readable in a graph
//     with 30+ nodes. Previously every edge was equally prominent, which is the
//     usual reason a graph like this reads as a hairball.
//   - click or Enter/Space -> pins a node and opens a detail card, so the
//     rationale is readable rather than trapped in a native tooltip that vanishes.
//   - labels appear on the active node only. Labelling all of them permanently
//     would collide; labelling none of them means hunting with the mouse.
//   - a legend, because node size, ring colour and dash pattern all carry meaning
//     and none of it was explained.
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
  const [hovered, setHovered] = useState<string | null>(null);
  const [pinned, setPinned] = useState<string | null>(null);
  const active = hovered ?? pinned;

  const classNodes = useMemo(() => nodes.filter((n) => n.type === "asset_class"), [nodes]);
  const otherNodes = useMemo(
    () => nodes.filter((n) => n.type !== "client" && n.type !== "asset_class"),
    [nodes],
  );
  const clientNode = nodes.find((n) => n.type === "client");

  // Fan classes across a wide arc centred "up" from the client rather than a full
  // 360 ring: with one or two classes a full-circle split lands one directly
  // opposite another, isolated and disconnected-looking.
  const layout = useMemo(() => {
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

    // Crop the viewBox to the content's bounding box; the arc fan only occupies
    // part of a circle, so a fixed square canvas left dead space.
    const classIds = new Set(classNodes.map((n) => n.id));
    const allowance = (id: string) =>
      id === "client"
        ? { top: 34, bottom: 60, left: 40, right: 40 }
        : classIds.has(id)
        ? { top: 32, bottom: 22, left: 28, right: 28 }
        : { top: 24, bottom: 24, left: 24, right: 24 };

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
    return { positions, viewBox: `${minX} ${minY} ${maxX - minX} ${maxY - minY}` };
  }, [classNodes, otherNodes]);

  const { positions, viewBox } = layout;

  // Zoom and pan. The layout already crops the viewBox to the content's bounding
  // box; zoom narrows that window around its centre and pan slides it, so the
  // node geometry never has to be recomputed. Panning is measured in viewBox
  // units so a drag tracks the cursor at any zoom level.
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragFrom = useRef<{ x: number; y: number } | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const [baseX, baseY, baseW, baseH] = useMemo(() => viewBox.split(" ").map(Number), [viewBox]);
  const viewW = baseW / zoom;
  const viewH = baseH / zoom;
  const liveViewBox = [
    baseX + (baseW - viewW) / 2 - pan.x,
    baseY + (baseH - viewH) / 2 - pan.y,
    viewW,
    viewH,
  ].join(" ");

  const atRest = zoom === 1 && pan.x === 0 && pan.y === 0;
  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Wheel-to-zoom has to be a non-passive native listener: React's onWheel is
  // registered passively, so preventDefault there is ignored and the page
  // scrolls out from under the graph while you are trying to zoom it.
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      setZoom((z) => Math.min(4, Math.max(0.6, z * (e.deltaY < 0 ? 1.12 : 1 / 1.12))));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  function onPointerDown(e: React.PointerEvent<SVGSVGElement>) {
    dragFrom.current = { x: e.clientX, y: e.clientY };
  }

  function onPointerMove(e: React.PointerEvent<SVGSVGElement>) {
    const from = dragFrom.current;
    const el = svgRef.current;
    if (!from || !el) return;
    const rect = el.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dx = (e.clientX - from.x) * (viewW / rect.width);
    const dy = (e.clientY - from.y) * (viewH / rect.height);
    dragFrom.current = { x: e.clientX, y: e.clientY };
    setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
  }

  const endDrag = () => {
    dragFrom.current = null;
  };

  // Everything one hop from the active node stays lit. Computed once per active
  // change rather than per rendered element.
  const lit = useMemo(() => {
    if (!active) return null;
    const ids = new Set<string>([active]);
    const edgeIdx = new Set<number>();
    edges.forEach((e, i) => {
      if (e.source === active || e.target === active) {
        edgeIdx.add(i);
        ids.add(e.source);
        ids.add(e.target);
      }
    });
    return { ids, edgeIdx };
  }, [active, edges]);

  const dim = (id: string) => (lit && !lit.ids.has(id) ? 0.18 : 1);
  const dimEdge = (i: number) => (lit && !lit.edgeIdx.has(i) ? 0.07 : 1);

  const nodeRadius = (n: GraphViewNode) =>
    n.type === "client" ? 26 : n.type === "asset_class" ? 15 : n.best ? 14 : 9;

  const nodeFill = (n: GraphViewNode) =>
    n.type === "client"
      ? "var(--accent)"
      : n.type === "asset_class"
      ? assetClassColor(n.label)
      : assetClassColor(n.asset_class || "");

  const edgeStroke = (e: GraphViewEdge) =>
    e.kind === "in_class" ? "var(--border-strong)" : e.kind === "holds" ? "var(--text-faint)" : "var(--accent)";

  const activeNode = active ? nodes.find((n) => n.id === active) : null;
  const detailNode = pinned ? nodes.find((n) => n.id === pinned) : null;

  function toggle(id: string) {
    setPinned((p) => (p === id ? null : id));
  }

  // Interactive product/class node, shared by both rings so hover, focus, keyboard
  // and pinning behave identically everywhere.
  function InteractiveNode({ n, children }: { n: GraphViewNode; children: React.ReactNode }) {
    return (
      <g
        className={`kg-node${pinned === n.id ? " pinned" : ""}`}
        opacity={dim(n.id)}
        tabIndex={0}
        role="button"
        aria-label={[n.label, n.sub, n.rationale].filter(Boolean).join(". ")}
        aria-pressed={pinned === n.id}
        onMouseEnter={() => setHovered(n.id)}
        onMouseLeave={() => setHovered(null)}
        onFocus={() => setHovered(n.id)}
        onBlur={() => setHovered(null)}
        onClick={() => toggle(n.id)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggle(n.id);
          }
        }}
      >
        {children}
      </g>
    );
  }

  return (
    <div className="kg-wrap">
      {/* Buttons as well as the wheel: wheel-only zoom is undiscoverable and
          unusable without a mouse. Reset only appears once the view has moved. */}
      <div className="kg-zoom">
        <button onClick={() => setZoom((z) => Math.min(4, z * 1.25))} aria-label="Zoom in" title="Zoom in">+</button>
        <button onClick={() => setZoom((z) => Math.max(0.6, z / 1.25))} aria-label="Zoom out" title="Zoom out">-</button>
        {!atRest && (
          <button className="kg-zoom-reset" onClick={resetView} aria-label="Reset view" title="Reset view">
            Reset
          </button>
        )}
      </div>
      <svg
        ref={svgRef}
        viewBox={liveViewBox}
        className={`kg-svg${dragFrom.current ? " kg-dragging" : ""}`}
        role="img"
        aria-label="Client, asset classes, holdings and suggested products"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerLeave={endDrag}
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
              opacity={(e.kind === "in_class" ? 0.4 : isBest ? 0.9 : 0.55) * dimEdge(i)}
              className="kg-edge"
            />
          );
        })}

        {classNodes.map((n) => {
          const pos = positions[n.id];
          if (!pos) return null;
          return (
            <InteractiveNode n={n} key={n.id}>
              <circle cx={pos.x} cy={pos.y} r={nodeRadius(n)} fill={nodeFill(n)} stroke="var(--surface)" strokeWidth={2} />
              <text x={pos.x} y={pos.y - nodeRadius(n) - 8} textAnchor="middle" className="kg-class-label" fill="var(--text-secondary)">
                {n.label}
              </text>
            </InteractiveNode>
          );
        })}

        {otherNodes.map((n) => {
          const pos = positions[n.id];
          if (!pos) return null;
          const r = nodeRadius(n);
          const showLabel = active === n.id;
          return (
            <InteractiveNode n={n} key={n.id}>
              {n.best && (
                <circle cx={pos.x} cy={pos.y} r={r + 7} fill="none" stroke="var(--sev-elevated)" strokeWidth={2} className="kg-pulse" />
              )}
              {/* Invisible larger hit target: a 9px dot is a poor click and an
                  even worse touch target. */}
              <circle cx={pos.x} cy={pos.y} r={Math.max(r + 10, 18)} fill="transparent" />
              <circle
                cx={pos.x}
                cy={pos.y}
                r={r}
                fill={nodeFill(n)}
                stroke={n.type === "held" ? "var(--surface)" : "var(--sev-elevated)"}
                strokeWidth={n.best ? 2.5 : n.type === "suggested" ? 1.5 : 2}
                opacity={n.type === "held" ? 0.85 : 1}
                className="kg-dot"
              />
              {showLabel && (
                <text x={pos.x} y={pos.y - r - 9} textAnchor="middle" className="kg-node-label" fill="var(--text)">
                  {n.label}
                </text>
              )}
            </InteractiveNode>
          );
        })}

        {clientNode && (
          <InteractiveNode n={clientNode}>
            <circle cx={CX} cy={CY} r={nodeRadius(clientNode)} fill={nodeFill(clientNode)} stroke="var(--surface)" strokeWidth={3} />
            <text x={CX} y={CY + 4} textAnchor="middle" className="kg-client-initials" fill="#ffffff">
              {initialsOf(clientNode.label)}
            </text>
            <text x={CX} y={CY + nodeRadius(clientNode) + 17} textAnchor="middle" className="kg-client-name" fill="var(--text)">
              {clientNode.label}
            </text>
          </InteractiveNode>
        )}
      </svg>

      {/* Detail card for the pinned node. Hover alone does not open it, so moving
          the mouse across the graph does not make a panel flicker. */}
      {detailNode ? (
        <div className="kg-detail fade-in">
          <div className="kg-detail-head">
            <span className="kg-detail-swatch" style={{ background: nodeFill(detailNode) }} />
            <span className="kg-detail-name">{detailNode.label}</span>
            <button className="kg-detail-close" onClick={() => setPinned(null)} aria-label="Clear selection">
              ×
            </button>
          </div>
          <div className="kg-detail-kind">
            {detailNode.type === "client"
              ? `Client${detailNode.sub ? ` · ${detailNode.sub} mandate` : ""}`
              : detailNode.type === "asset_class"
              ? "Asset class"
              : detailNode.type === "held"
              ? `Currently held${detailNode.sub ? ` · ${detailNode.sub}` : ""}`
              : `Suggested${detailNode.best ? " · strongest match" : ""}`}
          </div>
          {/* A held node's only extra field is its ticker, which the kind line
              above already shows — repeating it read as a bug. Show the rationale
              when there is one, and otherwise say plainly that there is not. */}
          {detailNode.rationale ? (
            <p className="kg-detail-why">{detailNode.rationale}</p>
          ) : detailNode.type === "held" ? (
            <p className="kg-detail-why">Already in this book, so it is not offered as a suggestion.</p>
          ) : null}
        </div>
      ) : (
        <div className="kg-hint">
          {activeNode ? activeNode.label : "Hover to trace a relationship, click a node to inspect it"}
        </div>
      )}

      <div className="kg-legend">
        <span className="kg-legend-item"><span className="kg-key kg-key-client" />Client</span>
        <span className="kg-legend-item"><span className="kg-key kg-key-class" />Asset class</span>
        <span className="kg-legend-item"><span className="kg-key kg-key-held" />Held</span>
        <span className="kg-legend-item"><span className="kg-key kg-key-sugg" />Suggested</span>
        <span className="kg-legend-item"><span className="kg-key kg-key-best" />Strongest match</span>
      </div>
    </div>
  );
}
