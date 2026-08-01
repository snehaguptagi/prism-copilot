import { severityColor } from "@/lib/colors";
import { inr } from "@/lib/format";

/**
 * AUM and account count per risk tier, on one shared 0-100% scale.
 *
 * The previous form scaled each bar to the largest tier, which ranked the tiers
 * but hid the thing worth knowing: where the accounts are is not where the money
 * is. Two paired bars on a share scale make that divergence the point of the
 * panel rather than something you work out from the numbers.
 *
 * Tier identity comes from the row's own text label, so the status colours are
 * secondary encoding, never the sole carrier. That matters here because the
 * severity ramp is a status scale, not a categorical one: Elevated and High sit
 * only ΔE 7 apart, so anything relying on colour alone to separate them would be
 * unreadable regardless of colour vision.
 */
export default function RiskSplit({
  rows,
  totalAum,
  totalClients,
}: {
  rows: { tier: string; count: number; aum: number }[];
  totalAum: number;
  totalClients: number;
}) {
  if (!rows.length) return null;

  return (
    <div className="risk-split">
      <div className="risk-split-head">
        <span />
        <span className="risk-split-key">
          <span className="risk-split-swatch solid" />
          Share of AUM
        </span>
        <span className="risk-split-key">
          <span className="risk-split-swatch hollow" />
          Share of accounts
        </span>
      </div>

      {rows.map((r) => {
        const aumPct = totalAum > 0 ? (r.aum / totalAum) * 100 : 0;
        const clientPct = totalClients > 0 ? (r.count / totalClients) * 100 : 0;
        const color = severityColor(r.tier);
        return (
          <div className="risk-split-row" key={r.tier}>
            <span className="risk-split-tier" style={{ color }}>
              <span className="risk-split-dot" style={{ background: color }} />
              {r.tier}
            </span>

            <span className="risk-split-metric">
              <span
                className="risk-split-track"
                title={`${r.tier}: ${inr(r.aum)}, ${aumPct.toFixed(1)}% of book AUM`}
              >
                <span
                  className="risk-split-fill"
                  style={{ width: `${aumPct}%`, background: color }}
                />
              </span>
              <span className="risk-split-val">{aumPct.toFixed(1)}%</span>
            </span>

            <span className="risk-split-metric">
              <span
                className="risk-split-track"
                title={`${r.tier}: ${r.count} of ${totalClients} accounts, ${clientPct.toFixed(0)}%`}
              >
                <span
                  className="risk-split-fill hollow"
                  style={{ width: `${clientPct}%`, borderColor: color }}
                />
              </span>
              <span className="risk-split-val muted">
                {r.count}
                <span className="risk-split-of"> of {totalClients}</span>
              </span>
            </span>
          </div>
        );
      })}
    </div>
  );
}
