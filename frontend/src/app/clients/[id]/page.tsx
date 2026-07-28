"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getClients, getGraphSuggestions } from "@/lib/api";
import { ClientAccount, GraphSuggestion } from "@/lib/types";
import { assetClassColor, avatarColor, initials, sectorColor, severityColor } from "@/lib/colors";
import { inr, crValue } from "@/lib/format";
import Topbar from "@/components/Topbar";
import Donut from "@/components/Donut";
import PerfHorizons from "@/components/PerfHorizons";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
}

const TABS = ["Profile", "Portfolio", "Holdings", "Communication"] as const;
type Tab = (typeof TABS)[number];

function channelIcon(channel: string): string {
  const c = channel.toLowerCase();
  if (c.includes("phone") || c.includes("call")) return "☎";
  if (c.includes("email")) return "✉";
  if (c.includes("whatsapp") || c.includes("app")) return "💬";
  if (c.includes("video")) return "🎥";
  if (c.includes("person")) return "🤝";
  return "•";
}

export default function ClientDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [account, setAccount] = useState<ClientAccount | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("Profile");
  const [graphSuggestions, setGraphSuggestions] = useState<GraphSuggestion[] | null>(null);
  const [graphEnabled, setGraphEnabled] = useState(false);

  useEffect(() => {
    getClients()
      .then((clients) => {
        const found = clients.find((c) => c.portfolio_id === params.id);
        if (!found) setError("Client not found.");
        else setAccount(found);
      })
      .catch((e) => setError(String(e)));

    // Knowledge-graph suggestions are additive: if the graph is not configured
    // this quietly returns { enabled: false, suggestions: [] } and the section
    // simply does not render. Never blocks the rest of the page.
    getGraphSuggestions(params.id)
      .then((r) => {
        setGraphEnabled(r.enabled);
        setGraphSuggestions(r.suggestions);
      })
      .catch(() => {
        setGraphEnabled(false);
        setGraphSuggestions(null);
      });
  }, [params.id]);

  if (error) {
    return (
      <>
        <Topbar />
        <div className="wrap">
          <Link href="/clients" className="back-link">‹ Back to clients</Link>
          <div className="panel" style={{ borderLeft: "3px solid var(--negative)" }}>
            <p style={{ color: "var(--negative)" }}>{error}</p>
          </div>
        </div>
      </>
    );
  }

  if (!account) {
    return (
      <>
        <Topbar />
        <div className="wrap">
          <p style={{ padding: "40px 0", color: "var(--text-secondary)" }}>Loading...</p>
        </div>
      </>
    );
  }

  const c = account.client;
  const psy = c.psychographics;
  const ins = account.insights;
  const tierColor = severityColor(account.risk_tier);

  return (
    <>
      <Topbar />
      <div className="wrap">
        <Link href="/clients" className="back-link">‹ Back to clients</Link>

        {/* header */}
        <div className="detail-head fade-in">
          <div className="avatar avatar-lg" style={{ background: avatarColor(c.name) }}>
            {initials(c.name)}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="detail-name">{c.name}</div>
            <div className="detail-sub">{c.age} · {c.occupation} · {c.city}</div>
            <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
              <span className="chip" style={{ background: `color-mix(in srgb, ${tierColor} 14%, white)`, color: tierColor }}>
                <span className="chip-dot" />{account.risk_tier ?? "n/a"} risk
              </span>
              <span className="chip" style={{ background: "var(--surface-2)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
                {c.risk_mandate}
              </span>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="kpi" style={{ border: "1px solid var(--border)", borderRadius: 10 }}>
              <div className="kpi-v">{inr(account.aum)}</div>
              <div className="kpi-l">AUM · {c.aum_fee_pct}% fee</div>
            </div>
          </div>
        </div>

        {/* quick contact strip */}
        <div className="contact-strip">
          <span><b>Email</b> {c.email}</span>
          <span><b>Phone</b> {c.phone}</span>
          <span><b>Client since</b> {formatDate(c.relationship_since)}</span>
        </div>

        <div className="section-tabs">
          {TABS.map((t) => (
            <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>{t}</button>
          ))}
        </div>

        {tab === "Profile" && psy && (
          <div className="stagger">
            <div className="panel">
              <div className="panel-title">Who they are</div>
              <p style={{ color: "var(--text-secondary)", fontSize: 13.5, lineHeight: 1.6 }}>{c.persona}</p>
            </div>

            <div className="panel">
              <div className="panel-title">Behavioral profile</div>
              <div className="psy-grid">
                <PsyItem label="Decision style" value={psy.decision_style} />
                <PsyItem label="Loss aversion" value={psy.loss_aversion} />
                <PsyItem label="Financial literacy" value={psy.financial_literacy} />
                <PsyItem label="Engagement" value={psy.engagement} />
                <PsyItem label="Prefers" value={psy.comms_pref} />
                <PsyItem label="Life stage" value={psy.life_stage} />
              </div>
            </div>

            <div className="panel">
              <div className="panel-title">Goals</div>
              <div className="psy-grid">
                <PsyItem label="Primary goal" value={psy.primary_goal} />
                <PsyItem label="Time horizon" value={psy.time_horizon} />
                <PsyItem label="Mandate" value={c.risk_mandate} />
              </div>
            </div>

            {c.relationship && (
              <div className="panel">
                <div className="panel-title">Relationship insights</div>
                <div className="psy-grid">
                  <PsyItem label="Came in via" value={c.relationship.referral_source} />
                  <PsyItem label="Household" value={c.relationship.dependents} />
                  <PsyItem label="Satisfaction" value={c.relationship.satisfaction} />
                </div>
                <div className="manager-note">
                  <span className="manager-note-label">Manager note</span>
                  {c.relationship.manager_note}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === "Portfolio" && ins && (
          <div className="stagger">
            {/* performance */}
            {account.performance && (
              <div className="panel">
                <div className="panel-title" style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Performance</span>
                  {account.performance.vs_benchmark_1y != null && (
                    <span
                      className="chip"
                      style={{
                        background: account.performance.vs_benchmark_1y >= 0 ? "color-mix(in srgb, var(--positive) 12%, white)" : "color-mix(in srgb, var(--negative) 12%, white)",
                        color: account.performance.vs_benchmark_1y >= 0 ? "var(--positive)" : "var(--negative)",
                      }}
                    >
                      {account.performance.vs_benchmark_1y >= 0 ? "+" : ""}{account.performance.vs_benchmark_1y}% vs Nifty (1Y)
                    </span>
                  )}
                </div>
                <div className="perf-row">
                  <PerfCell v={account.performance.ytd_pct} l="YTD" />
                  <PerfCell v={account.performance.one_year_pct} l="1 year" />
                  <PerfCell v={account.performance.three_year_cagr_pct} l="3Y CAGR" />
                  <PerfCell v={account.performance.since_inception_cagr_pct} l="Since inception" />
                </div>
                <div className="perf-gain">
                  1-year gain <b>{inr(account.performance.gain_1y)}</b>
                  {account.performance.benchmark_one_year_pct != null && (
                    <span className="perf-bench"> · Nifty 50 returned {account.performance.benchmark_one_year_pct}% over the same period</span>
                  )}
                </div>
                {account.performance.horizons && account.performance.horizons.length > 0 && (
                  <div style={{ marginTop: 14, borderTop: "1px solid var(--border)", paddingTop: 14 }}>
                    <div className="mini-head">Returns by horizon vs Nifty 50</div>
                    <PerfHorizons horizons={account.performance.horizons} benchmarkName="Nifty 50" />
                  </div>
                )}
              </div>
            )}

            {/* suitability */}
            {account.suitability && account.suitability.status !== "unknown" && (
              <div
                className="panel suitability"
                style={{ borderLeft: `3px solid ${account.suitability.status === "matched" ? "var(--positive)" : "var(--sev-high)"}` }}
              >
                <div className="suit-head">
                  <span className="suit-icon" style={{ color: account.suitability.status === "matched" ? "var(--positive)" : "var(--sev-high)" }}>
                    {account.suitability.status === "matched" ? "✓" : "!"}
                  </span>
                  <span className="suit-label">{account.suitability.label}</span>
                </div>
                {account.suitability.detail && <p className="suit-detail">{account.suitability.detail}</p>}
              </div>
            )}

            <div className="metric-row">
              <Metric v={`${ins.est_vol ?? "n/a"}%`} l="Est. volatility" />
              <Metric v={ins.wtd_beta != null ? ins.wtd_beta.toFixed(2) : "n/a"} l="Weighted beta" />
              <Metric v={String(ins.num_holdings)} l="Holdings" />
              <Metric v={String(ins.num_sectors)} l="Sectors" />
              <Metric v={ins.concentration} l="Concentration" color={ins.concentration === "High" ? "var(--sev-high)" : ins.concentration === "Moderate" ? "var(--sev-elevated)" : "var(--sev-low)"} />
            </div>

            <div className="ov-grid">
              {/* asset-class donut */}
              {account.asset_class_allocation && account.asset_class_allocation.length > 0 && (
                <div className="panel">
                  <div className="panel-title">Asset allocation</div>
                  <div className="donut-wrap">
                    <Donut
                      size={140}
                      segments={account.asset_class_allocation.map((a) => ({
                        label: a.asset_class,
                        pct: a.pct,
                        color: assetClassColor(a.asset_class),
                      }))}
                      centerTop={`₹${crValue(account.aum)}`}
                      centerSub="Cr book"
                    />
                    <div className="donut-legend">
                      {account.asset_class_allocation.map((a) => (
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
              )}

              {/* sector ranked bars */}
              <div className="panel">
                <div className="panel-title">Sector allocation</div>
                {(() => {
                  const sorted = [...account.sector_breakdown].sort((a, b) => b.weight_pct - a.weight_pct);
                  const max = Math.max(...sorted.map((s) => s.weight_pct), 1);
                  return (
                    <div className="sector-bars" style={{ gridTemplateColumns: "1fr" }}>
                      {sorted.map((s) => (
                        <div key={s.sector} className="sector-bar-row" title={`${s.sector}: ${s.weight_pct}%`}>
                          <span className="sector-bar-name">{s.sector}</span>
                          <span className="sector-bar-track">
                            <span className="sector-bar-fill" style={{ width: `${(s.weight_pct / max) * 100}%`, background: sectorColor(s.sector) }} />
                          </span>
                          <span className="sector-bar-val">{s.weight_pct}%</span>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>
            </div>

            <div className="ov-grid">
              <div className="panel">
                <div className="panel-title">Largest position</div>
                <div className="big-fact">
                  <div className="big-fact-v">{ins.top_position_pct}%</div>
                  <div className="big-fact-l">{ins.top_position_name}</div>
                </div>
                <p style={{ fontSize: 12, color: "var(--text-faint)", marginTop: 8 }}>
                  Largest sector: {ins.largest_sector} at {ins.largest_sector_pct}% of the book.
                </p>
              </div>

              <div className="panel">
                <div className="panel-title">Macro-factor sensitivity</div>
                {ins.factor_exposures.length === 0 ? (
                  <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>No material macro-factor exposure detected.</p>
                ) : (
                  <div className="factor-rows">
                    {ins.factor_exposures.map((f) => (
                      <div key={f.factor} className="factor-exp-row">
                        <span className="factor-exp-name">{f.factor}</span>
                        <span className="factor-exp-track">
                          <span className="factor-exp-fill" style={{ width: `${Math.min(f.pct, 100)}%` }} />
                        </span>
                        <span className="factor-exp-pct">{f.pct}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="panel">
              <div className="panel-title">Mandate</div>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.55 }}>{account.mandate}</p>
            </div>

            {account.product_suggestions && account.product_suggestions.length > 0 && (
              <div className="panel">
                <div className="panel-title">Products suited to {c.name.split(" ")[0]}</div>
                <p className="cross-sell-note">
                  Matched to this client&apos;s stated preferences and risk mandate, drawn from the sellable
                  universe. Ideas to raise in conversation, not a recommendation to buy.
                </p>
                <div className="cross-sell-grid stagger">
                  {account.product_suggestions.map((p) => (
                    <div key={p.security_id} className="cross-sell-card">
                      <div className="cross-sell-head">
                        <span className="cross-sell-name">{p.name}</span>
                        <span className="cross-sell-tkr">{p.ticker}</span>
                      </div>
                      <div className="cross-sell-tags">
                        <span
                          className="chip"
                          style={{ background: `color-mix(in srgb, ${sectorColor(p.sector)} 12%, white)`, color: sectorColor(p.sector) }}
                        >
                          {p.asset_class}
                        </span>
                        <span className="cross-sell-instrument">{p.instrument_type}</span>
                      </div>
                      <p className="cross-sell-why">{p.rationale}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {graphEnabled && graphSuggestions && graphSuggestions.length > 0 && (
              <div className="panel">
                <div className="panel-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="graph-badge" title="Powered by the Neo4j knowledge graph">◈ Graph</span>
                  Similar clients also hold
                </div>
                <p className="cross-sell-note">
                  From the knowledge graph: products in an asset class {c.name.split(" ")[0]} prefers, within
                  their mandate, ranked by how many clients with a similar profile already hold each.
                </p>
                <div className="cross-sell-grid stagger">
                  {graphSuggestions.map((p) => (
                    <div key={p.security_id} className="cross-sell-card">
                      <div className="cross-sell-head">
                        <span className="cross-sell-name">{p.name}</span>
                        <span className="cross-sell-tkr">{p.ticker}</span>
                      </div>
                      <div className="cross-sell-tags">
                        <span
                          className="chip"
                          style={{ background: `color-mix(in srgb, ${sectorColor(p.sector)} 12%, white)`, color: sectorColor(p.sector) }}
                        >
                          {p.asset_class}
                        </span>
                        {p.peers > 0 && <span className="cross-sell-instrument">{p.peers} similar client{p.peers !== 1 ? "s" : ""}</span>}
                      </div>
                      <p className="cross-sell-why">{p.rationale}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button className="btn" style={{ marginTop: 4 }} onClick={() => router.push(`/analysis?portfolio=${account.portfolio_id}`)}>
              Run market analysis on this book ›
            </button>
          </div>
        )}

        {tab === "Holdings" && (
          <div className="table-wrap fade-in">
            <table>
              <thead>
                <tr>
                  <th>Holding</th>
                  <th>Ticker</th>
                  <th style={{ textAlign: "right" }}>Weight</th>
                  <th style={{ textAlign: "right" }}>Value</th>
                </tr>
              </thead>
              <tbody className="stagger">
                {account.holdings.map((h) => (
                  <tr key={h.security_id}>
                    <td>{h.name}</td>
                    <td>{h.ticker}</td>
                    <td className="num">{h.weight_pct}%</td>
                    <td className="num">{inr(h.market_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === "Communication" && (
          <div className="stagger">
            {c.next_action && (
              <div className="panel next-action-panel">
                <div className="na-left">
                  <div className="na-label">Next action</div>
                  <div className="na-action">{c.next_action.action}</div>
                  <div className="na-due">Due {formatDate(c.next_action.due)}</div>
                </div>
                <span className={`chip na-priority na-${c.next_action.priority.toLowerCase()}`}>
                  {c.next_action.priority} priority
                </span>
              </div>
            )}

            <div className="panel-title" style={{ margin: "18px 0 10px" }}>Recent interactions</div>
            <div className="comm-timeline">
              {(c.communications ?? []).map((m, i) => (
                <div className="comm-item" key={i}>
                  <div className="comm-icon">{channelIcon(m.channel)}</div>
                  <div className="comm-body">
                    <div className="comm-meta">
                      <span className="comm-channel">{m.channel}</span>
                      <span className={`comm-dir comm-${m.direction}`}>
                        {m.direction === "inbound" ? "client → you" : m.direction === "outbound" ? "you → client" : "meeting"}
                      </span>
                      <span className="comm-date">{formatDate(m.date)}</span>
                    </div>
                    <div className="comm-summary">{m.summary}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <footer>Decision-support tool. Not investment advice, not a trading system.</footer>
      </div>
    </>
  );
}

function PsyItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="psy-item">
      <div className="psy-label">{label}</div>
      <div className="psy-value">{value}</div>
    </div>
  );
}

function PerfCell({ v, l }: { v: number; l: string }) {
  const color = v > 0 ? "var(--positive)" : v < 0 ? "var(--negative)" : "var(--text)";
  return (
    <div className="perf-cell">
      <div className="perf-v" style={{ color }}>{v > 0 ? "+" : ""}{v}%</div>
      <div className="perf-l">{l}</div>
    </div>
  );
}

function Metric({ v, l, color }: { v: string; l: string; color?: string }) {
  return (
    <div className="metric">
      <div className="metric-v" style={color ? { color } : undefined}>{v}</div>
      <div className="metric-l">{l}</div>
    </div>
  );
}
