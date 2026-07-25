"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getClients } from "@/lib/api";
import { ClientAccount } from "@/lib/types";
import { avatarColor, initials, sectorColor, severityColor } from "@/lib/colors";
import Topbar from "@/components/Topbar";

function formatCrore(value: number): string {
  return `₹${(value / 1e7).toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`;
}

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

  useEffect(() => {
    getClients()
      .then((clients) => {
        const found = clients.find((c) => c.portfolio_id === params.id);
        if (!found) setError("Client not found.");
        else setAccount(found);
      })
      .catch((e) => setError(String(e)));
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
              <div className="kpi-v">{formatCrore(account.aum)}</div>
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
            <div className="metric-row">
              <Metric v={`${ins.est_vol ?? "n/a"}%`} l="Est. volatility" />
              <Metric v={ins.wtd_beta != null ? ins.wtd_beta.toFixed(2) : "n/a"} l="Weighted beta" />
              <Metric v={String(ins.num_holdings)} l="Holdings" />
              <Metric v={String(ins.num_sectors)} l="Sectors" />
              <Metric v={ins.concentration} l="Concentration" color={ins.concentration === "High" ? "var(--sev-high)" : ins.concentration === "Moderate" ? "var(--sev-elevated)" : "var(--sev-low)"} />
            </div>

            <div className="panel">
              <div className="panel-title">Sector allocation</div>
              <div className="alloc-bar">
                {account.sector_breakdown.map((s) => (
                  <span key={s.sector} style={{ width: `${s.weight_pct}%`, background: sectorColor(s.sector) }} title={`${s.sector} ${s.weight_pct}%`} />
                ))}
              </div>
              <div className="alloc-legend" style={{ marginTop: 12 }}>
                {account.sector_breakdown.map((s) => (
                  <div key={s.sector} className="alloc-legend-item">
                    <span className="dot" style={{ background: sectorColor(s.sector) }} />
                    <span className="alloc-name">{s.sector}</span>
                    <span className="alloc-pct">{s.weight_pct}%</span>
                  </div>
                ))}
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
                    <td className="num">{formatCrore(h.market_value)}</td>
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

function Metric({ v, l, color }: { v: string; l: string; color?: string }) {
  return (
    <div className="metric">
      <div className="metric-v" style={color ? { color } : undefined}>{v}</div>
      <div className="metric-l">{l}</div>
    </div>
  );
}
