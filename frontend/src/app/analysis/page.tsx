"use client";

import { useEffect, useState } from "react";
import { getClients, getSectors, getTalkingPoints } from "@/lib/api";
import { ClientAccount, TalkingPointsResult } from "@/lib/types";
import { avatarColor, initials, sectorColor, severityColor } from "@/lib/colors";
import Topbar from "@/components/Topbar";
import ComparisonBar from "@/components/ComparisonBar";

function formatCrore(value: number): string {
  return `₹${(value / 1e7).toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`;
}

export default function AnalysisPage() {
  const [clients, setClients] = useState<ClientAccount[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [selected, setSelected] = useState<ClientAccount | null>(null);
  const [sector, setSector] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TalkingPointsResult | null>(null);

  useEffect(() => {
    Promise.all([getClients(), getSectors()])
      .then(([c, s]) => {
        setClients(c);
        setSectors(s);
        // deep-link from a client detail page: /analysis?portfolio=<id>
        const preId = new URLSearchParams(window.location.search).get("portfolio");
        const pre = preId ? c.find((x) => x.portfolio_id === preId) : null;
        if (pre) {
          setSelected(pre);
          setSector(pre.suggested_sector ?? pre.sector_breakdown[0]?.sector ?? s[0] ?? "");
        }
      })
      .catch((e) => setError(String(e)));
  }, []);

  function pickClient(c: ClientAccount) {
    setSelected(c);
    setResult(null);
    setError(null);
    setSector(c.suggested_sector ?? c.sector_breakdown[0]?.sector ?? sectors[0] ?? "");
  }

  async function runAnalysis() {
    if (!selected || !sector) return;
    setLoading(true);
    setError(null);
    try {
      const r = await getTalkingPoints(selected.portfolio_id, sector);
      setResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Topbar />
      <div className="wrap">
        <header className="hero">
          <p className="eyebrow">Portfolio-first market analysis</p>
          <h1>Analyze a client&apos;s book</h1>
          <p className="lede">
            Pick a portfolio, run live market analysis on what it&apos;s most exposed to, and get
            ready-to-use conversation points, grounded in real news and computed against the actual book.
          </p>
        </header>

        {/* Step 1 — pick a portfolio */}
        <div className="step-head">
          <span className="step-num">1</span>
          <span>Select a portfolio</span>
        </div>

        {error && !selected && (
          <div className="panel" style={{ borderLeft: "3px solid var(--negative)" }}>
            <p style={{ color: "var(--negative)" }}>{error}</p>
          </div>
        )}

        <div className="pick-grid stagger">
          {clients.map((c) => {
            const active = selected?.portfolio_id === c.portfolio_id;
            const tierColor = severityColor(c.risk_tier);
            return (
              <button
                key={c.portfolio_id}
                className={`pick-card${active ? " active" : ""}`}
                onClick={() => pickClient(c)}
              >
                <div className="pick-top">
                  <div className="avatar" style={{ background: avatarColor(c.client.name) }}>
                    {initials(c.client.name)}
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div className="pick-name">{c.client.name}</div>
                    <div className="pick-sub">{c.portfolio_name}</div>
                  </div>
                </div>
                <div className="pick-meta">
                  <span
                    className="chip"
                    style={{ background: `color-mix(in srgb, ${tierColor} 12%, white)`, color: tierColor }}
                  >
                    <span className="chip-dot" />
                    {c.risk_tier ?? "n/a"}
                  </span>
                  <span className="pick-aum">{formatCrore(c.aum)}</span>
                </div>
                <div className="expo-bar">
                  {c.sector_breakdown.map((b) => (
                    <span
                      key={b.sector}
                      style={{ width: `${b.weight_pct}%`, background: sectorColor(b.sector) }}
                      title={`${b.sector} ${b.weight_pct}%`}
                    />
                  ))}
                </div>
              </button>
            );
          })}
        </div>

        {/* Step 2 — run analysis */}
        {selected && (
          <div className="fade-in">
            <div className="step-head">
              <span className="step-num">2</span>
              <span>Run market analysis</span>
            </div>

            <div className="panel analysis-run">
              <div className="run-context">
                <div className="avatar avatar-lg" style={{ background: avatarColor(selected.client.name) }}>
                  {initials(selected.client.name)}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="detail-name" style={{ fontSize: 17 }}>{selected.client.name}</div>
                  <div className="detail-sub">
                    {selected.portfolio_name} · {selected.risk_tier} risk
                  </div>
                  <div className="expo-legend">
                    {selected.sector_breakdown.slice(0, 5).map((b) => (
                      <span key={b.sector} className="expo-legend-item">
                        <span className="dot" style={{ background: sectorColor(b.sector) }} />
                        {b.sector} {b.weight_pct}%
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="run-controls">
                <div>
                  <div className="run-label">Analyze exposure to</div>
                  <div className="select-wrap">
                    <select value={sector} onChange={(e) => setSector(e.target.value)}>
                      {sectors.map((s) => (
                        <option key={s} value={s}>
                          {s}
                          {selected.suggested_sector === s ? "  (largest exposure)" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <button className="btn" onClick={runAnalysis} disabled={loading}>
                  {loading && <span className="spinner" />}
                  {loading ? "Analyzing live market…" : "Run market analysis"}
                </button>
              </div>
            </div>

            {error && selected && (
              <div className="panel" style={{ borderLeft: "3px solid var(--negative)" }}>
                <p style={{ color: "var(--negative)" }}>{error}</p>
              </div>
            )}
          </div>
        )}

        {/* Step 3 — results & suggestions */}
        {result && (
          <div className="fade-in">
            <div className="step-head">
              <span className="step-num">3</span>
              <span>What it means for this book</span>
            </div>

            {(() => {
              const tw = result.factor_impact?.tailwind_pct ?? 0;
              const hw = result.factor_impact?.headwind_pct ?? 0;
              const net = tw - hw;
              const touched = result.impact?.pct_nav_touched ?? 0;
              const verdict =
                touched === 0 && tw === 0 && hw === 0
                  ? { label: "Quiet for this book", color: "var(--text-secondary)", detail: "Today's research does not touch this portfolio, directly or through macro factors." }
                  : net > 5
                  ? { label: "Net tailwind", color: "var(--tailwind)", detail: `About ${tw}% of NAV benefits from today's macro read; little on the other side.` }
                  : net < -5
                  ? { label: "Net headwind", color: "var(--headwind)", detail: `About ${hw}% of NAV faces pressure from today's macro read.` }
                  : touched > 0
                  ? { label: "Direct exposure", color: "var(--accent)", detail: `${touched}% of NAV sits in names in today's research.` }
                  : { label: "Mixed / mild", color: "var(--sev-elevated)", detail: "Small and offsetting effects, nothing decisive for this book today." };

              return (
                <>
                  {/* verdict banner */}
                  <div className="verdict-banner" style={{ borderLeftColor: verdict.color }}>
                    <span className="verdict-dot" style={{ background: verdict.color }} />
                    <div>
                      <div className="verdict-label" style={{ color: verdict.color }}>{verdict.label}</div>
                      <div className="verdict-detail">{verdict.detail}</div>
                    </div>
                  </div>

                  {/* at-a-glance stat gauges */}
                  <div className="gauge-row">
                    <Gauge value={touched} label="of NAV in named holdings" color="var(--accent)" />
                    <Gauge value={tw} label="of NAV a tailwind" color="var(--tailwind)" />
                    <Gauge value={hw} label="of NAV a headwind" color="var(--headwind)" />
                  </div>

                  <div className="result-grid">
                    <div className="panel">
                      <div className="panel-title">Exposure vs. a normal book</div>
                      {result.impact ? (
                        <ComparisonBar impact={result.impact} />
                      ) : (
                        <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.55 }}>
                          No individual company in this book was named in today&apos;s research. That is
                          expected for a cash and short-term-debt book, its exposure comes through interest
                          rates, shown in the factor read, not single stocks.
                        </p>
                      )}
                    </div>
                    <div className="panel">
                      <div className="panel-title">Tailwind vs. headwind</div>
                      {tw === 0 && hw === 0 ? (
                        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>No material macro-factor effect on this book today.</p>
                      ) : (
                        <>
                          <div className="tw-hw-bar">
                            <span className="tw-seg" style={{ flex: Math.max(tw, 0.5) }} />
                            <span className="hw-seg" style={{ flex: Math.max(hw, 0.5) }} />
                          </div>
                          <div className="tw-hw-legend">
                            <span><span className="dot" style={{ background: "var(--tailwind)" }} />Tailwind {tw}%</span>
                            <span><span className="dot" style={{ background: "var(--headwind)" }} />Headwind {hw}%</span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </>
              );
            })()}

            {result.market_insights.length > 0 && (
              <div className="panel">
                <div className="narrative-head">Market context · {result.sector}</div>
                <ul className="keypoint-list stagger" style={{ marginTop: 10 }}>
                  {result.market_insights.map((m, i) => (
                    <li className="keypoint" key={i}>
                      <span className="keypoint-dot" />
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="step-head" style={{ marginTop: 26 }}>
              <span className="step-num">4</span>
              <span>Suggested talking points for {result.client_name}</span>
            </div>
            <div className="panel suggestions">
              <ul className="tp-list stagger">
                {result.points.map((point, i) => (
                  <li key={i} className="tp-item">
                    <span className="tp-num">{i + 1}</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="shead">Sources ({result.citations.length})</div>
            <div className="panel stagger">
              {result.citations.map((c, i) => (
                <div className="citation" key={i}>
                  <a href={c.url} target="_blank" rel="noreferrer">
                    {c.title || c.url}
                  </a>
                  <span className="tag">
                    {c.linked_security_ids.length > 0
                      ? `→ ${c.linked_security_ids.join(", ")}`
                      : "no security match"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <footer>
          Decision-support tool. Not investment advice, not a trading system. Suggestions are talking
          points for a client conversation, generated from already-computed, deterministic exposure
          numbers, never buy/sell/hold guidance.
        </footer>
      </div>
    </>
  );
}

function Gauge({ value, label, color }: { value: number; label: string; color: string }) {
  const pct = Math.min(Math.max(value, 0), 100);
  const R = 26;
  const C = 2 * Math.PI * R;
  const dash = (pct / 100) * C;
  return (
    <div className="gauge">
      <svg width="64" height="64" viewBox="0 0 64 64">
        <circle cx="32" cy="32" r={R} fill="none" stroke="var(--border)" strokeWidth="7" />
        <circle
          cx="32" cy="32" r={R} fill="none" stroke={color} strokeWidth="7" strokeLinecap="round"
          strokeDasharray={`${dash} ${C - dash}`} transform="rotate(-90 32 32)"
        />
        <text x="32" y="36" textAnchor="middle" className="gauge-num" fill="var(--text)">
          {Math.round(value)}%
        </text>
      </svg>
      <div className="gauge-label">{label}</div>
    </div>
  );
}
