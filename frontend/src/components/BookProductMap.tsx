"use client";

import { useMemo, useState } from "react";
import { OverviewGraphResult } from "@/lib/types";
import { assetClassColor } from "@/lib/colors";

/**
 * Firm-wide flow: clients to asset classes to products, in three fixed columns.
 *
 * Two things this fixes over the static version it replaces.
 *
 * Ordering. Clients and products were drawn in whatever order the API returned,
 * so every edge crossed most of the others and the middle of the diagram was a
 * solid mat of lines. Both outer columns are now ordered by the asset class they
 * connect to, which bundles the edges into bands. Same data, same positions
 * otherwise, far fewer crossings.
 *
 * Focus. A link diagram at this density cannot be read passively, and native
 * <title> tooltips only answer "what is this dot" one dot at a time. Hovering or
 * focusing any node now traces its whole path and dims everything else, so the
 * question a viewer actually has, which clients does this product serve and
 * through what, is answered by looking. Click or press Enter to pin that trace so
 * it survives the mouse leaving; Escape releases it.
 */
const COL_W = 880;
const X_CLIENT = 190;
const X_CLASS = 440;
const X_PRODUCT = 690;
const ROW_H = 30;
const TOP_PAD = 30;

type Sel = { id: string; kind: "client" | "class" | "product" } | null;

export default function BookProductMap({ data }: { data: OverviewGraphResult }) {
  const [hover, setHover] = useState<Sel>(null);
  const [pinned, setPinned] = useState<Sel>(null);
  const active = pinned ?? hover;

  const layout = useMemo(() => {
    const classIndex = new Map(data.classes.map((c, i) => [c.id, i]));

    // Order each outer column by the class it attaches to, so edges leave in
    // bands instead of fanning across the whole diagram.
    const classOfClient = new Map<string, number>();
    data.edges_client_class.forEach((e) => {
      const i = classIndex.get(e.target);
      if (i == null) return;
      const cur = classOfClient.get(e.source);
      if (cur == null || i < cur) classOfClient.set(e.source, i);
    });

    const clients = [...data.clients].sort(
      (a, b) =>
        (classOfClient.get(a.id) ?? 99) - (classOfClient.get(b.id) ?? 99) ||
        a.label.localeCompare(b.label)
    );
    const products = [...data.products].sort(
      (a, b) =>
        (classIndex.get(`class:${a.asset_class}`) ?? 99) -
          (classIndex.get(`class:${b.asset_class}`) ?? 99) ||
        b.client_count - a.client_count
    );

    const rows = Math.max(clients.length, data.classes.length, products.length);
    const height = TOP_PAD * 2 + rows * ROW_H;
    const evenY = (i: number, n: number) => {
      if (n <= 1) return height / 2;
      const start = (height - (n - 1) * ROW_H) / 2;
      return start + i * ROW_H;
    };

    const pos: Record<string, { x: number; y: number }> = {};
    clients.forEach((c, i) => (pos[c.id] = { x: X_CLIENT, y: evenY(i, clients.length) }));
    data.classes.forEach((c, i) => (pos[c.id] = { x: X_CLASS, y: evenY(i, data.classes.length) }));
    products.forEach((p, i) => (pos[p.id] = { x: X_PRODUCT, y: evenY(i, products.length) }));

    return { clients, products, pos, height };
  }, [data]);

  // What lights up for a given selection. The graph is a three-column DAG, so
  // this is just "walk outward from the selected column in both directions".
  const lit = useMemo(() => {
    if (!active) return null;
    const nodes = new Set<string>([active.id]);
    const edges = new Set<string>();

    const classesOf = (clientId: string) =>
      data.edges_client_class.filter((e) => e.source === clientId).map((e) => e.target);

    if (active.kind === "client") {
      classesOf(active.id).forEach((cid) => {
        nodes.add(cid);
        edges.add(`cc:${active.id}>${cid}`);
        data.edges_class_product
          .filter((e) => e.source === cid)
          .forEach((e) => {
            nodes.add(e.target);
            edges.add(`cp:${cid}>${e.target}`);
          });
      });
    } else if (active.kind === "product") {
      data.edges_class_product
        .filter((e) => e.target === active.id)
        .forEach((e) => {
          nodes.add(e.source);
          edges.add(`cp:${e.source}>${active.id}`);
          data.edges_client_class
            .filter((c) => c.target === e.source)
            .forEach((c) => {
              nodes.add(c.source);
              edges.add(`cc:${c.source}>${e.source}`);
            });
        });
    } else {
      data.edges_client_class
        .filter((e) => e.target === active.id)
        .forEach((e) => {
          nodes.add(e.source);
          edges.add(`cc:${e.source}>${active.id}`);
        });
      data.edges_class_product
        .filter((e) => e.source === active.id)
        .forEach((e) => {
          nodes.add(e.target);
          edges.add(`cp:${active.id}>${e.target}`);
        });
    }
    return { nodes, edges };
  }, [active, data]);

  const dimNode = (id: string) => (lit ? !lit.nodes.has(id) : false);
  const dimEdge = (key: string) => (lit ? !lit.edges.has(key) : false);

  const maxCount = Math.max(...data.products.map((p) => p.client_count), 1);
  const { pos, height } = layout;

  const curve = (a: { x: number; y: number }, b: { x: number; y: number }) => {
    const mx = (a.x + b.x) / 2;
    return `M ${a.x} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`;
  };

  const select = (sel: Sel) => setPinned((cur) => (cur && cur.id === sel?.id ? null : sel));

  const readout = (() => {
    if (!active) return "Hover or tab to any client, asset class, or product to trace its path. Click to pin.";
    if (active.kind === "client") {
      const c = layout.clients.find((x) => x.id === active.id);
      return c
        ? `${c.label}: ${c.best_match ? `best match ${c.best_match}` : "no suitable match today"}.`
        : "";
    }
    if (active.kind === "product") {
      const p = layout.products.find((x) => x.id === active.id);
      return p
        ? `${p.label} (${p.ticker}), ${p.asset_class}. Best match for ${p.client_count} client${
            p.client_count !== 1 ? "s" : ""
          }: ${p.client_names.join(", ")}.`
        : "";
    }
    const cls = data.classes.find((x) => x.id === active.id);
    const n = data.edges_client_class.filter((e) => e.target === active.id).length;
    return cls ? `${cls.label}: preferred by ${n} client${n !== 1 ? "s" : ""}.` : "";
  })();

  return (
    <div className="bpm" onMouseLeave={() => setHover(null)}>
      <svg
        viewBox={`0 0 ${COL_W} ${height}`}
        className={`bpm-svg${lit ? " has-focus" : ""}`}
        role="application"
        aria-label="Product fit across the whole book. Clients on the left, asset classes in the middle, products on the right."
        onKeyDown={(e) => e.key === "Escape" && (setPinned(null), setHover(null))}
      >
        <g className="bpm-col-heads">
          <text x={X_CLIENT} y={14} textAnchor="end" className="bpm-col-head">Clients</text>
          <text x={X_CLASS} y={14} textAnchor="middle" className="bpm-col-head">Asset class</text>
          <text x={X_PRODUCT} y={14} textAnchor="start" className="bpm-col-head">Best-fit product</text>
        </g>

        {data.edges_client_class.map((e, i) => {
          const s = pos[e.source];
          const t = pos[e.target];
          if (!s || !t) return null;
          const cls = data.classes.find((c) => c.id === e.target);
          return (
            <path
              key={`cc-${i}`}
              d={curve(s, t)}
              fill="none"
              stroke={cls ? assetClassColor(cls.label) : "var(--border-strong)"}
              strokeWidth={1.2}
              className={`bpm-edge${dimEdge(`cc:${e.source}>${e.target}`) ? " dim" : ""}`}
            />
          );
        })}

        {data.edges_class_product.map((e, i) => {
          const s = pos[e.source];
          const t = pos[e.target];
          if (!s || !t) return null;
          const cls = data.classes.find((c) => c.id === e.source);
          return (
            <path
              key={`cp-${i}`}
              d={curve(s, t)}
              fill="none"
              stroke={cls ? assetClassColor(cls.label) : "var(--accent)"}
              strokeWidth={Math.min(1 + e.weight * 0.9, 5)}
              className={`bpm-edge strong${dimEdge(`cp:${e.source}>${e.target}`) ? " dim" : ""}`}
            />
          );
        })}

        {layout.clients.map((c) => {
          const p = pos[c.id];
          if (!p) return null;
          const sel: Sel = { id: c.id, kind: "client" };
          return (
            <g
              key={c.id}
              className={`bpm-node${dimNode(c.id) ? " dim" : ""}${pinned?.id === c.id ? " pinned" : ""}`}
              tabIndex={0}
              role="button"
              aria-label={`Client ${c.label}. ${c.best_match ? `Best match ${c.best_match}` : "No match"}`}
              onMouseEnter={() => setHover(sel)}
              onFocus={() => setHover(sel)}
              onBlur={() => setHover(null)}
              onClick={() => select(sel)}
              onKeyDown={(e) => e.key === "Enter" && select(sel)}
            >
              <circle cx={p.x} cy={p.y} r={13} className="bpm-hit" />
              <circle cx={p.x} cy={p.y} r={6} fill="var(--accent)" stroke="var(--surface)" strokeWidth={1.5} />
              <text x={p.x - 12} y={p.y + 3.5} textAnchor="end" className="bpm-client-label">
                {c.label}
              </text>
            </g>
          );
        })}

        {data.classes.map((cls) => {
          const p = pos[cls.id];
          if (!p) return null;
          const sel: Sel = { id: cls.id, kind: "class" };
          return (
            <g
              key={cls.id}
              className={`bpm-node${dimNode(cls.id) ? " dim" : ""}${pinned?.id === cls.id ? " pinned" : ""}`}
              tabIndex={0}
              role="button"
              aria-label={`Asset class ${cls.label}`}
              onMouseEnter={() => setHover(sel)}
              onFocus={() => setHover(sel)}
              onBlur={() => setHover(null)}
              onClick={() => select(sel)}
              onKeyDown={(e) => e.key === "Enter" && select(sel)}
            >
              <circle cx={p.x} cy={p.y} r={18} className="bpm-hit" />
              <circle cx={p.x} cy={p.y} r={14} fill={assetClassColor(cls.label)} stroke="var(--surface)" strokeWidth={2} />
              <text x={p.x} y={p.y - 20} textAnchor="middle" className="bpm-class-label">
                {cls.label}
              </text>
            </g>
          );
        })}

        {layout.products.map((pr) => {
          const p = pos[pr.id];
          if (!p) return null;
          const r = 8 + (pr.client_count / maxCount) * 12;
          const sel: Sel = { id: pr.id, kind: "product" };
          return (
            <g
              key={pr.id}
              className={`bpm-node${dimNode(pr.id) ? " dim" : ""}${pinned?.id === pr.id ? " pinned" : ""}`}
              tabIndex={0}
              role="button"
              aria-label={`Product ${pr.label}, best match for ${pr.client_count} clients`}
              onMouseEnter={() => setHover(sel)}
              onFocus={() => setHover(sel)}
              onBlur={() => setHover(null)}
              onClick={() => select(sel)}
              onKeyDown={(e) => e.key === "Enter" && select(sel)}
            >
              <circle cx={p.x} cy={p.y} r={r + 7} className="bpm-hit" />
              {pr.confirmed && (
                <circle cx={p.x} cy={p.y} r={r + 5} fill="none" stroke="var(--sev-elevated)" strokeWidth={1.5} opacity={0.55} />
              )}
              <circle cx={p.x} cy={p.y} r={r} fill={assetClassColor(pr.asset_class)} stroke="var(--surface)" strokeWidth={2} />
              <text x={p.x + r + 8} y={p.y + 3.5} textAnchor="start" className="bpm-product-label">
                {pr.label}
                <tspan className="bpm-product-count"> · {pr.client_count}</tspan>
              </text>
            </g>
          );
        })}
      </svg>

      <div className="bpm-readout" aria-live="polite">
        {pinned && <span className="bpm-pin-tag">Pinned</span>}
        {readout}
      </div>
    </div>
  );
}
