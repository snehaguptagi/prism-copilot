"use client";

import { useEffect, useState } from "react";
import { getClients, getClientGraphView } from "@/lib/api";
import { ClientAccount, GraphViewResult } from "@/lib/types";
import { avatarColor, initials, severityColor, assetClassColor } from "@/lib/colors";
import Topbar from "@/components/Topbar";
import KnowledgeGraph from "@/components/KnowledgeGraph";

const SOURCE_LABEL = {
  both: "Confirmed match",
  graph: "Similar-client match",
  rule: "Preference match",
} as const;

export default function GraphPage() {
  const [clients, setClients] = useState<ClientAccount[]>([]);
  const [selected, setSelected] = useState<ClientAccount | null>(null);
  const [view, setView] = useState<GraphViewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getClients()
      .then((c) => {
        setClients(c);
        if (c[0]) pick(c[0]);
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function pick(c: ClientAccount) {
    setSelected(c);
    setView(null);
    setError(null);
    setLoading(true);
    getClientGraphView(c.portfolio_id)
      .then(setView)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }

  return (
    <>
      <Topbar />
      <div className="wrap">
        <header className="hero hero-tight">
          <p className="eyebrow">Product fit</p>
          <h1>Find the right product for each client</h1>
          <p className="lede">
            Pick a client to see their current holdings, what they care about, and the products most
            worth raising in conversation. The highlighted pick is the strongest match, confirmed by
            both the client&apos;s preferences and what similar clients already hold.
          </p>
        </header>

        {error && (
          <div className="panel" style={{ borderLeft: "3px solid var(--negative)" }}>
            <p style={{ color: "var(--negative)" }}>{error}</p>
          </div>
        )}

        <div className="pick-grid stagger" style={{ marginBottom: 22 }}>
          {clients.map((c) => {
            const active = selected?.portfolio_id === c.portfolio_id;
            const tierColor = severityColor(c.risk_tier);
            return (
              <button key={c.portfolio_id} className={`pick-card${active ? " active" : ""}`} onClick={() => pick(c)}>
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
                  <span className="chip" style={{ background: `color-mix(in srgb, ${tierColor} 12%, var(--surface))`, color: tierColor }}>
                    <span className="chip-dot" />
                    {c.risk_tier ?? "n/a"}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {loading && (
          <div className="panel">
            <p>Finding the best product matches...</p>
          </div>
        )}

        {view && !loading && (
          <div className="fade-in kg-layout">
            <div className="panel kg-panel">
              <div className="panel-title">Product map for {view.client_name}</div>
              <KnowledgeGraph nodes={view.nodes} edges={view.edges} />
              <div className="kg-legend">
                <span>
                  <span className="dot" style={{ background: "var(--accent)" }} />
                  Client
                </span>
                <span>
                  <span className="dot" style={{ background: "var(--text-faint)" }} />
                  Asset class
                </span>
                <span>
                  <span className="dot" style={{ background: "var(--border-strong)", opacity: 0.85 }} />
                  Held
                </span>
                <span>
                  <span className="dot" style={{ background: "var(--sev-elevated)" }} />
                  Suggested / best match
                </span>
              </div>
              {view.extra_holdings > 0 && (
                <p className="kg-note">
                  + {view.extra_holdings} more holding{view.extra_holdings !== 1 ? "s" : ""} not shown, to keep the
                  graph readable.
                </p>
              )}
            </div>

            <div className="panel kg-best-panel">
              <div className="panel-title">Perfect match</div>
              {view.best_match ? (
                <>
                  <div className="kg-best-head">
                    <span className="kg-best-name">{view.best_match.name}</span>
                    <span className="kg-best-tkr">{view.best_match.ticker}</span>
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "8px 0 12px" }}>
                    <span
                      className="chip"
                      style={{
                        background: `color-mix(in srgb, ${assetClassColor(view.best_match.asset_class)} 14%, var(--surface))`,
                        color: assetClassColor(view.best_match.asset_class),
                      }}
                    >
                      {view.best_match.asset_class}
                    </span>
                    <span className={`kg-source-badge kg-source-${view.best_match.source}`}>
                      {SOURCE_LABEL[view.best_match.source]}
                    </span>
                  </div>
                  <p className="kg-best-why">{view.best_match.rationale}</p>
                </>
              ) : (
                <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  No suitable product surfaced for this client today.
                </p>
              )}
              {!view.graph_enabled && (
                <p className="kg-graph-off-note">
                  Similar-client matching is not available right now; showing preference-based matches only.
                </p>
              )}
            </div>
          </div>
        )}

        <footer>
          Decision-support tool. Not investment advice. This shows how each suggestion was derived,
          never a directive to buy.
        </footer>
      </div>
    </>
  );
}
