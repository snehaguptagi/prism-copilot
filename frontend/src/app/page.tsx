"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getOverview } from "@/lib/api";
import { Overview } from "@/lib/types";
import { assetClassColor, sectorColor, severityColor } from "@/lib/colors";
import Topbar from "@/components/Topbar";
import NumberFlow from "@number-flow/react";

function crore(value: number): number {
  return Math.round(value / 1e7);
}

export default function OverviewPage() {
  const router = useRouter();
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOverview()
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  const maxTierAum = data ? Math.max(...data.risk_distribution.map((d) => d.aum), 1) : 1;
  const maxHolding = data ? Math.max(...data.top_holdings.map((h) => h.pct_of_book), 1) : 1;

  return (
    <>
      <Topbar />
      <div className="wrap">
        <header className="hero hero-tight">
          <p className="eyebrow">Book overview</p>
          <h1>Your entire book, at a glance</h1>
          <p className="lede">
            A live, firm wide summary of every client portfolio you manage. Every figure below is
            computed directly from current holdings, nothing estimated.
          </p>
        </header>

        {error && (
          <div className="panel" style={{ borderLeft: "3px solid var(--negative)" }}>
            <p style={{ color: "var(--negative)" }}>{error}</p>
          </div>
        )}

        {data && (
          <div className="fade-in">
            {/* KPI row */}
            <div className="kpi-row stagger">
              <div className="kpi">
                <div className="kpi-v">
                  <NumberFlow value={crore(data.kpis.total_aum)} prefix="₹" suffix=" Cr" />
                </div>
                <div className="kpi-l">Total assets under management</div>
              </div>
              <div className="kpi">
                <div className="kpi-v">
                  <NumberFlow value={data.kpis.client_count} />
                </div>
                <div className="kpi-l">Client accounts</div>
              </div>
              <div className="kpi">
                <div className="kpi-v">
                  <NumberFlow value={crore(data.kpis.annual_fee_revenue)} prefix="₹" suffix=" Cr" />
                </div>
                <div className="kpi-l">Annual fee revenue</div>
              </div>
              <div className="kpi">
                <div className="kpi-v">
                  <NumberFlow value={data.kpis.blended_fee_pct} suffix="%" />
                </div>
                <div className="kpi-l">Blended fee rate</div>
              </div>
              <div className="kpi">
                <div className="kpi-v">
                  <NumberFlow value={data.kpis.distinct_securities} />
                </div>
                <div className="kpi-l">Distinct securities held</div>
              </div>
            </div>

            {/* Action items: what needs attention */}
            {data.action_items.length > 0 && (
              <>
                <div className="shead">
                  What needs attention
                  <span className="shead-count">
                    {data.action_items.filter((a) => a.overdue || (a.days_until_due ?? 99) <= 3).length} due soon
                  </span>
                </div>
                <div className="action-list stagger">
                  {data.action_items.slice(0, 6).map((a) => {
                    const soon = a.overdue || (a.days_until_due ?? 99) <= 3;
                    return (
                      <button
                        key={a.portfolio_id}
                        className={`action-item${a.overdue ? " overdue" : soon ? " soon" : ""}`}
                        onClick={() => router.push(`/clients/${a.portfolio_id}`)}
                      >
                        <span className="action-due">
                          {a.overdue
                            ? `${Math.abs(a.days_until_due ?? 0)}d overdue`
                            : a.days_until_due === 0
                            ? "today"
                            : a.days_until_due != null
                            ? `in ${a.days_until_due}d`
                            : "—"}
                        </span>
                        <span className="action-body">
                          <span className="action-text">{a.action}</span>
                          <span className="action-client">{a.client_name}</span>
                        </span>
                        <span className={`chip action-prio prio-${a.priority.toLowerCase()}`}>{a.priority}</span>
                      </button>
                    );
                  })}
                </div>
              </>
            )}

            <div className="ov-grid">
              {/* Asset-class allocation */}
              <div className="panel">
                <div className="panel-title">Asset allocation across the book</div>
                <div className="alloc-bar">
                  {data.asset_class_allocation.map((a) => (
                    <span
                      key={a.asset_class}
                      style={{ width: `${a.pct}%`, background: assetClassColor(a.asset_class) }}
                      title={`${a.asset_class} ${a.pct}%`}
                    />
                  ))}
                </div>
                <div className="alloc-legend">
                  {data.asset_class_allocation.map((a) => (
                    <div key={a.asset_class} className="alloc-legend-item">
                      <span className="dot" style={{ background: assetClassColor(a.asset_class) }} />
                      <span className="alloc-name">{a.asset_class}</span>
                      <span className="alloc-pct">{a.pct}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Risk distribution */}
              <div className="panel">
                <div className="panel-title">AUM by risk tier</div>
                <div className="risk-rows">
                  {data.risk_distribution.map((d) => (
                    <div key={d.tier} className="risk-row">
                      <span className="risk-row-label" style={{ color: severityColor(d.tier) }}>
                        {d.tier}
                      </span>
                      <span className="risk-row-track">
                        <span
                          className="risk-row-fill"
                          style={{ width: `${(d.aum / maxTierAum) * 100}%`, background: severityColor(d.tier) }}
                        />
                      </span>
                      <span className="risk-row-val">
                        ₹{crore(d.aum).toLocaleString("en-IN")} Cr
                        <span className="risk-row-count"> · {d.count}</span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Sector allocation */}
            <div className="panel">
              <div className="panel-title">Sector exposure across all clients</div>
              <div className="sector-chips">
                {data.sector_allocation.map((s) => (
                  <div key={s.sector} className="sector-chip">
                    <span className="sector-chip-dot" style={{ background: sectorColor(s.sector) }} />
                    <span className="sector-chip-name">{s.sector}</span>
                    <span className="sector-chip-pct">{s.pct}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="ov-grid">
              {/* Top holdings */}
              <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
                <div className="panel-title" style={{ padding: "16px 18px 0" }}>
                  Largest positions across the book
                </div>
                <table style={{ marginTop: 10 }}>
                  <thead>
                    <tr>
                      <th>Security</th>
                      <th>Held by</th>
                      <th style={{ textAlign: "right" }}>% of book</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.top_holdings.map((h) => (
                      <tr key={h.security_id}>
                        <td>
                          <div className="holding-cell">
                            <span className="holding-name">{h.name}</span>
                            <span className="holding-tkr">{h.ticker}</span>
                          </div>
                        </td>
                        <td>
                          <span className="held-by">{h.held_by_count} of {data.kpis.client_count}</span>
                        </td>
                        <td className="num">
                          <div className="pct-cell">
                            <span className="pct-bar" style={{ width: `${(h.pct_of_book / maxHolding) * 100}%` }} />
                            <span>{h.pct_of_book}%</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Largest clients */}
              <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
                <div className="panel-title" style={{ padding: "16px 18px 0" }}>
                  Largest clients by AUM
                </div>
                <table style={{ marginTop: 10 }}>
                  <thead>
                    <tr>
                      <th>Client</th>
                      <th>Risk</th>
                      <th style={{ textAlign: "right" }}>AUM</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.largest_clients.map((c) => {
                      const tc = severityColor(c.risk_tier);
                      return (
                        <tr
                          key={c.portfolio_id}
                          className="clickable"
                          onClick={() => router.push(`/clients/${c.portfolio_id}`)}
                        >
                          <td>
                            <div className="holding-cell">
                              <span className="holding-name">{c.client_name}</span>
                              <span className="holding-tkr">{c.portfolio_name}</span>
                            </div>
                          </td>
                          <td>
                            <span className="chip" style={{ background: `color-mix(in srgb, ${tc} 12%, white)`, color: tc }}>
                              {c.risk_tier ?? "n/a"}
                            </span>
                          </td>
                          <td className="num">₹{crore(c.aum).toLocaleString("en-IN")} Cr</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {!data && !error && (
          <div className="panel">
            <p>Loading book summary...</p>
          </div>
        )}

        <footer>
          Decision-support tool. Not investment advice, not a trading system. Every figure is
          computed from current holdings and reproducible.
        </footer>
      </div>
    </>
  );
}
