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

            <div className="result-grid">
              <div className="panel">
                <h3>Exposure vs. a normal book</h3>
                {result.impact ? (
                  <ComparisonBar impact={result.impact} />
                ) : (
                  <p>No held security in this book was directly named in today&apos;s {result.sector} research.</p>
                )}
              </div>
              {result.factor_impact && (
                <div className="panel">
                  <h3>Factor exposure</h3>
                  <div className="factor-split">
                    <div>
                      <div className="factor-v" style={{ color: "var(--tailwind)" }}>
                        {result.factor_impact.tailwind_pct}%
                      </div>
                      <div className="factor-l">tailwind</div>
                    </div>
                    <div>
                      <div className="factor-v" style={{ color: "var(--headwind)" }}>
                        {result.factor_impact.headwind_pct}%
                      </div>
                      <div className="factor-l">headwind</div>
                    </div>
                  </div>
                </div>
              )}
            </div>

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
