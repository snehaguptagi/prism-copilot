"use client";

import NumberFlow from "@number-flow/react";
import { PortfolioImpact } from "@/lib/types";

/** Lens-2 from LLD §12 / DESIGN.md §5: "you" vs. the reference book, same
 * scale, absolute % as the primary label, the multiple as a smaller
 * secondary annotation — never the headline figure. */
export default function ComparisonBar({ impact }: { impact: PortfolioImpact }) {
  const mult = impact.vs_reference_multiple;
  const multLabel =
    mult == null ? null : typeof mult === "string" ? mult : `${mult}x`;

  return (
    <div className="compare">
      <div className="compare-row">
        <span className="label">You</span>
        <div className="bar-track">
          <div
            className="bar-fill"
            style={{ width: `${Math.min(impact.pct_nav_touched, 100)}%`, background: "var(--accent)" }}
          />
        </div>
        <span className="pct">
          <NumberFlow value={impact.pct_nav_touched} suffix="%" />
        </span>
      </div>
      <div className="compare-row">
        <span className="label">Reference</span>
        <div className="bar-track">
          <div
            className="bar-fill"
            style={{ width: `${Math.min(impact.vs_reference_pct, 100)}%`, background: "var(--text-faint)" }}
          />
        </div>
        <span className="pct" style={{ color: "var(--text-secondary)" }}>
          <NumberFlow value={impact.vs_reference_pct} suffix="%" />
        </span>
      </div>
      {multLabel && <div className="multiple">you are {multLabel} a normal book</div>}
    </div>
  );
}
