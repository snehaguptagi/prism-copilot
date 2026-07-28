"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getOverview } from "@/lib/api";
import { Overview } from "@/lib/types";
import { assetClassColor, sectorColor, severityColor } from "@/lib/colors";
import { inr, crValue } from "@/lib/format";
import Topbar from "@/components/Topbar";
import Donut from "@/components/Donut";
import PerfHorizons from "@/components/PerfHorizons";
import NumberFlow from "@number-flow/react";

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
                  <NumberFlow value={crValue(data.kpis.total_aum)} prefix="₹" suffix=" Cr" format={{ maximumFractionDigits: 1 }} />
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
                  <NumberFlow value={data.kpis.annual_fee_revenue / 1e7} prefix="₹" suffix=" Cr" format={{ maximumFractionDigits: 2 }} />
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

            {/* Book performance vs benchmark */}
            {data.performance && (
              <div className="perf-banner">
                <div className="perf-banner-main">
                  <div className="perf-banner-label">Book return, trailing 1 year</div>
                  <div className="perf-banner-row">
                    <span className="perf-banner-v" style={{ color: data.performance.book_one_year_pct >= 0 ? "var(--positive)" : "var(--negative)" }}>
                      +{data.performance.book_one_year_pct}%
                    </span>
                    {data.performance.vs_benchmark_1y != null && (
                      <span
                        className="chip"
                        style={{
                          background: data.performance.vs_benchmark_1y >= 0 ? "color-mix(in srgb, var(--positive) 12%, var(--surface))" : "color-mix(in srgb, var(--negative) 12%, var(--surface))",
                          color: data.performance.vs_benchmark_1y >= 0 ? "var(--positive)" : "var(--negative)",
                        }}
                      >
                        {data.performance.vs_benchmark_1y >= 0 ? "+" : ""}{data.performance.vs_benchmark_1y}% vs {data.performance.benchmark_name}
                      </span>
                    )}
                  </div>
                </div>

                <PerfHorizons horizons={data.performance.horizons} benchmarkName={data.performance.benchmark_name} />

                {data.performance.best && data.performance.worst && (
                  <div className="perf-banner-bw">
                    <button className="perf-bw-item" onClick={() => router.push(`/clients/${data.performance.best!.portfolio_id}`)}>
                      <span className="perf-bw-label">Best</span>
                      <span className="perf-bw-name">{data.performance.best.client_name}</span>
                      <span className="perf-bw-val up">+{data.performance.best.one_year_pct}%</span>
                    </button>
                    <button className="perf-bw-item" onClick={() => router.push(`/clients/${data.performance.worst!.portfolio_id}`)}>
                      <span className="perf-bw-label">Lagging</span>
                      <span className="perf-bw-name">{data.performance.worst.client_name}</span>
                      <span className="perf-bw-val">+{data.performance.worst.one_year_pct}%</span>
                    </button>
                  </div>
                )}
              </div>
            )}

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
                            : "--"}
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
                <div className="donut-wrap">
                  <Donut
                    segments={data.asset_class_allocation.map((a) => ({
                      label: a.asset_class,
                      pct: a.pct,
                      color: assetClassColor(a.asset_class),
                    }))}
                    centerTop={`₹${crValue(data.kpis.total_aum)}`}
                    centerSub="Cr AUM"
                  />
                  <div className="donut-legend">
                    {[...data.asset_class_allocation]
                      .sort((a, b) => b.pct - a.pct)
                      .map((a) => (
                        <div key={a.asset_class} className="donut-legend-row">
                          <span className="donut-dot" style={{ background: assetClassColor(a.asset_class) }} />
                          <span className="donut-legend-name">{a.asset_class}</span>
                          <span className="donut-legend-pct">{a.pct}%</span>
                          <span className="donut-legend-val">{inr(a.value)}</span>
                        </div>
                      ))}
                  </div>
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
                        {inr(d.aum)}
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
              {(() => {
                const sorted = [...data.sector_allocation].sort((a, b) => b.pct - a.pct);
                const max = Math.max(...sorted.map((s) => s.pct), 1);
                return (
                  <div className="sector-bars">
                    {sorted.map((s) => (
                      <div
                        key={s.sector}
                        className="sector-bar-row"
                        title={`${s.sector}: ${s.pct}% of the book (${inr(s.value)})`}
                      >
                        <span className="sector-bar-name">{s.sector}</span>
                        <span className="sector-bar-track">
                          <span
                            className="sector-bar-fill"
                            style={{ width: `${(s.pct / max) * 100}%`, background: sectorColor(s.sector) }}
                          />
                        </span>
                        <span className="sector-bar-val">{s.pct}%</span>
                      </div>
                    ))}
                  </div>
                );
              })()}
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
                            <span className="chip" style={{ background: `color-mix(in srgb, ${tc} 12%, var(--surface))`, color: tc }}>
                              {c.risk_tier ?? "n/a"}
                            </span>
                          </td>
                          <td className="num">{inr(c.aum)}</td>
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
