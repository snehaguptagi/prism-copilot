"use client";

import { useState } from "react";
import { inr } from "@/lib/format";

/**
 * How much of the book sits in its largest few relationships.
 *
 * The dashboard already listed the largest clients, but a ranked list answers
 * "who is biggest" and never answers "how exposed am I to losing one of them",
 * which is the question concentration actually poses. This is a cumulative
 * share curve: bar n is the share of AUM held by the top n clients, so the shape
 * of the curve IS the concentration. A book spread evenly across 16 accounts
 * climbs in a straight line; one that reaches 80% by the fourth bar does not.
 *
 * One series, so no legend box and no categorical palette: the accent carries the
 * marks and the callout above names what is being measured. The threshold rule is
 * the only reference mark, direct-labelled rather than put in a key.
 */
export default function Concentration({
  clients,
  totalAum,
  maxBars = 10,
}: {
  clients: { portfolio_id: string; client_name: string; aum: number }[];
  totalAum: number;
  maxBars?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);

  if (!clients.length || totalAum <= 0) return null;

  const ranked = [...clients].sort((a, b) => b.aum - a.aum).slice(0, maxBars);
  let running = 0;
  const points = ranked.map((c, i) => {
    running += c.aum;
    return {
      n: i + 1,
      name: c.client_name,
      ownAum: c.aum,
      ownPct: (c.aum / totalAum) * 100,
      cumPct: (running / totalAum) * 100,
      cumAum: running,
    };
  });

  // The headline is top-5, or the whole book when the desk is smaller than that.
  const headlineIdx = Math.min(4, points.length - 1);
  const headline = points[headlineIdx];
  const active = hover != null ? points[hover] : null;

  return (
    <div className="conc">
      <div className="conc-headline">
        <span className="conc-figure">{headline.cumPct.toFixed(1)}%</span>
        <span className="conc-caption">
          of book AUM sits with the top {headline.n} client{headline.n !== 1 ? "s" : ""}
          <span className="conc-sub">{inr(headline.cumAum)} of {inr(totalAum)}</span>
        </span>
      </div>

      <div className="conc-chart" onMouseLeave={() => setHover(null)}>
        {points.map((p, i) => (
          <button
            key={p.name}
            className={`conc-col${hover === i ? " active" : ""}`}
            onMouseEnter={() => setHover(i)}
            onFocus={() => setHover(i)}
            onBlur={() => setHover(null)}
            aria-label={`Top ${p.n} clients hold ${p.cumPct.toFixed(1)} percent of book AUM`}
          >
            <span className="conc-col-track">
              <span className="conc-col-fill" style={{ height: `${p.cumPct}%` }} />
            </span>
            <span className="conc-col-n">{p.n}</span>
          </button>
        ))}
        <span className="conc-rule" style={{ bottom: "50%" }}>
          <span className="conc-rule-label">50% of book</span>
        </span>
      </div>

      <div className="conc-readout" aria-live="polite">
        {active ? (
          <>
            <span className="conc-readout-strong">Top {active.n}</span> hold{" "}
            <span className="conc-readout-strong">{active.cumPct.toFixed(1)}%</span>. Largest of
            them, {active.name}, is {active.ownPct.toFixed(1)}% on their own.
          </>
        ) : (
          <>Hover a bar for the cumulative share held by the largest n clients.</>
        )}
      </div>
    </div>
  );
}
