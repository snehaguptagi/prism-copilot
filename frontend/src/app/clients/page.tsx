"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import NumberFlow from "@number-flow/react";
import { getClients } from "@/lib/api";
import { ClientAccount } from "@/lib/types";
import { avatarColor, initials, severityColor } from "@/lib/colors";
import { inr, crValue } from "@/lib/format";
import Topbar from "@/components/Topbar";

const RISK_TIERS = ["All", "Low", "Moderate", "Elevated", "High", "Very High"] as const;

export default function ClientsPage() {
  const router = useRouter();
  const [clients, setClients] = useState<ClientAccount[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [tierFilter, setTierFilter] = useState<(typeof RISK_TIERS)[number]>("All");

  useEffect(() => {
    getClients()
      .then(setClients)
      .catch((e) => setError(String(e)));
  }, []);

  const totalAum = clients.reduce((sum, c) => sum + c.aum, 0);
  const avgFee = clients.length
    ? clients.reduce((sum, c) => sum + c.client.aum_fee_pct, 0) / clients.length
    : 0;

  const TIER_ORDER = ["Low", "Moderate", "Elevated", "High", "Very High"] as const;
  const tierCounts = TIER_ORDER.map((t) => ({
    tier: t,
    count: clients.filter((c) => c.risk_tier === t).length,
  }));

  const q = query.trim().toLowerCase();
  const filtered = clients.filter((c) => {
    if (tierFilter !== "All" && c.risk_tier !== tierFilter) return false;
    if (!q) return true;
    return (
      c.client.name.toLowerCase().includes(q) ||
      c.client.occupation.toLowerCase().includes(q) ||
      c.portfolio_name.toLowerCase().includes(q) ||
      c.client.city.toLowerCase().includes(q)
    );
  });

  return (
    <>
      <Topbar />
      <div className="wrap">
        <header className="hero">
          <p className="eyebrow">Relationship manager view</p>
          <h1>Your clients</h1>
          <p className="lede">
            Every client is a distinct person with a distinct reason for investing.
            Click any row for contact details, contract terms, and their portfolio.
          </p>

          {clients.length > 0 && (
            <div className="stats stagger">
              <div className="stat-tile">
                <div className="v">
                  <NumberFlow value={clients.length} />
                </div>
                <div className="l">Client accounts</div>
              </div>
              <div className="stat-tile">
                <div className="v">
                  <NumberFlow value={crValue(totalAum)} prefix="₹" suffix=" Cr" format={{ maximumFractionDigits: 1 }} />
                </div>
                <div className="l">Total AUM</div>
              </div>
              <div className="stat-tile">
                <div className="v">
                  <NumberFlow value={Number(avgFee.toFixed(2))} suffix="%" />
                </div>
                <div className="l">Average fee</div>
              </div>
              <div className="stat-tile risk-dist">
                <div className="l" style={{ marginTop: 0, marginBottom: 8 }}>Risk spread</div>
                <div className="risk-dist-bars">
                  {tierCounts.map((tc) => (
                    <button
                      key={tc.tier}
                      className="risk-dist-seg"
                      onClick={() => setTierFilter(tierFilter === tc.tier ? "All" : tc.tier)}
                      title={`${tc.count} ${tc.tier}`}
                      style={{ opacity: tierFilter === "All" || tierFilter === tc.tier ? 1 : 0.3 }}
                    >
                      <span className="risk-dist-count" style={{ color: severityColor(tc.tier) }}>
                        {tc.count}
                      </span>
                      <span
                        className="risk-dist-fill"
                        style={{
                          height: `${8 + tc.count * 9}px`,
                          background: severityColor(tc.tier),
                        }}
                      />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </header>

        {error && (
          <div className="panel" style={{ borderLeft: "3px solid var(--negative)" }}>
            <h3 style={{ color: "var(--negative)" }}>Error</h3>
            <p>{error}</p>
          </div>
        )}

        {clients.length > 0 && (
          <div className="controls" style={{ marginBottom: 16 }}>
            <input
              type="text"
              className="text-input"
              placeholder="Search by name, occupation, portfolio, or city…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ flex: 1, minWidth: 220 }}
            />
            <div className="select-wrap">
              <select value={tierFilter} onChange={(e) => setTierFilter(e.target.value as (typeof RISK_TIERS)[number])}>
                {RISK_TIERS.map((t) => (
                  <option key={t} value={t}>
                    {t === "All" ? "All risk tiers" : t}
                  </option>
                ))}
              </select>
            </div>
            <span style={{ fontSize: 12.5, color: "var(--text-faint)" }}>
              {filtered.length} of {clients.length}
            </span>
          </div>
        )}

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Client</th>
                <th>Occupation</th>
                <th>Portfolio</th>
                <th>Risk tier</th>
                <th>1Y vs Nifty</th>
                <th>Fee</th>
                <th style={{ textAlign: "right" }}>AUM</th>
              </tr>
            </thead>
            <tbody className="stagger">
              {filtered.map((c) => {
                const tierColor = severityColor(c.risk_tier);
                return (
                  <tr
                    key={c.portfolio_id}
                    className="clickable"
                    onClick={() => router.push(`/clients/${c.portfolio_id}`)}
                  >
                    <td>
                      <div className="client-row-name">
                        <div className="avatar" style={{ background: avatarColor(c.client.name) }}>
                          {initials(c.client.name)}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600 }}>{c.client.name}</div>
                          <div className="meta">{c.client.city}</div>
                        </div>
                      </div>
                    </td>
                    <td>{c.client.occupation}</td>
                    <td>{c.portfolio_name}</td>
                    <td>
                      <span
                        className="chip"
                        style={{ background: `color-mix(in srgb, ${tierColor} 12%, white)`, color: tierColor }}
                      >
                        <span className="chip-dot" />
                        {c.risk_tier ?? "n/a"}
                      </span>
                    </td>
                    <td>
                      {c.performance ? (() => {
                        const oy = c.performance.one_year_pct;
                        const bench = c.performance.benchmark_one_year_pct ?? 0;
                        const vs = c.performance.vs_benchmark_1y ?? 0;
                        const max = Math.max(oy, bench, 1);
                        return (
                          <div className="row-perf" title={`Book ${oy}% vs Nifty ${bench}% (1Y)`}>
                            <span className="row-spark">
                              <span className="row-spark-bar book" style={{ height: `${(oy / max) * 100}%` }} />
                              <span className="row-spark-bar bench" style={{ height: `${(bench / max) * 100}%` }} />
                            </span>
                            <span className="row-perf-text">
                              <span className="row-perf-v" style={{ color: oy >= 0 ? "var(--positive)" : "var(--negative)" }}>
                                {oy >= 0 ? "+" : ""}{oy}%
                              </span>
                              <span className="row-perf-delta" style={{ color: vs >= 0 ? "var(--positive)" : "var(--negative)" }}>
                                {vs >= 0 ? "+" : ""}{vs} vs Nifty
                              </span>
                            </span>
                          </div>
                        );
                      })() : (
                        <span style={{ color: "var(--text-faint)" }}>n/a</span>
                      )}
                    </td>
                    <td>{c.client.aum_fee_pct}%</td>
                    <td className="num">{inr(c.aum)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {clients.length > 0 && filtered.length === 0 && (
          <div className="panel">
            <p>No clients match &ldquo;{query}&rdquo;{tierFilter !== "All" ? ` in the ${tierFilter} risk tier` : ""}.</p>
          </div>
        )}

        {clients.length === 0 && !error && (
          <div className="panel">
            <p>Loading client roster…</p>
          </div>
        )}

        <footer>
          Decision-support tool. Not investment advice, not a trading system. Client details shown
          here are synthetic personas built for this MVP, not real individuals.
        </footer>
      </div>
    </>
  );
}
