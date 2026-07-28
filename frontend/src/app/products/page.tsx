"use client";

import { useEffect, useMemo, useState } from "react";
import { getProducts } from "@/lib/api";
import { Products } from "@/lib/types";
import { assetClassColor, sectorColor } from "@/lib/colors";
import Topbar from "@/components/Topbar";
import Donut from "@/components/Donut";

export default function ProductsPage() {
  const [data, setData] = useState<Products | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState<string>("All");

  useEffect(() => {
    getProducts().then(setData).catch((e) => setError(String(e)));
  }, []);

  const groups = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data.groups
      .filter((g) => group === "All" || g.asset_class === group)
      .map((g) => ({
        ...g,
        items: g.items.filter(
          (i) => !q || i.name.toLowerCase().includes(q) || i.ticker.toLowerCase().includes(q) || i.sector.toLowerCase().includes(q)
        ),
      }))
      .filter((g) => g.items.length > 0);
  }, [data, query, group]);

  const idleCount = useMemo(
    () => data?.groups.flatMap((g) => g.items).filter((i) => i.held_by_count === 0).length ?? 0,
    [data]
  );

  return (
    <>
      <Topbar />
      <div className="wrap">
        <header className="hero hero-tight">
          <p className="eyebrow">Investable universe</p>
          <h1>Products you can offer</h1>
          <p className="lede">
            Every security and fund on the desk&apos;s shelf, grouped by asset class, with how many
            client books already hold each. Idle products are ones no client holds yet.
          </p>

          {data && (
            <div className="stats">
              <div className="stat-tile">
                <div className="v">{data.total}</div>
                <div className="l">Products on the shelf</div>
              </div>
              <div className="stat-tile">
                <div className="v">{data.groups.length}</div>
                <div className="l">Asset classes</div>
              </div>
              <div className="stat-tile">
                <div className="v">{idleCount}</div>
                <div className="l">Not yet held by any client</div>
              </div>
            </div>
          )}
        </header>

        {error && (
          <div className="panel" style={{ borderLeft: "3px solid var(--negative)" }}>
            <p style={{ color: "var(--negative)" }}>{error}</p>
          </div>
        )}

        {data && (
          <>
            <div className="ov-grid" style={{ marginBottom: 16 }}>
              {/* shelf composition donut */}
              <div className="panel">
                <div className="panel-title">Shelf composition by asset class</div>
                <div className="donut-wrap">
                  <Donut
                    size={140}
                    segments={data.groups.map((g) => ({
                      label: g.asset_class,
                      pct: (g.count / data.total) * 100,
                      color: assetClassColor(g.asset_class),
                    }))}
                    centerTop={String(data.total)}
                    centerSub="products"
                  />
                  <div className="donut-legend">
                    {data.groups.map((g) => (
                      <div key={g.asset_class} className="donut-legend-row">
                        <span className="donut-dot" style={{ background: assetClassColor(g.asset_class) }} />
                        <span className="donut-legend-name">{g.asset_class}</span>
                        <span className="donut-legend-pct">{g.count}</span>
                        <span className="donut-legend-val">{Math.round((g.count / data.total) * 100)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* most widely held across the book */}
              <div className="panel">
                <div className="panel-title">Most widely held across the book</div>
                {(() => {
                  const items = data.groups.flatMap((g) => g.items);
                  const top = [...items].sort((a, b) => b.held_by_count - a.held_by_count).slice(0, 8);
                  const max = Math.max(...top.map((i) => i.held_by_count), 1);
                  return (
                    <div className="sector-bars" style={{ gridTemplateColumns: "1fr" }}>
                      {top.map((i) => (
                        <div key={i.security_id} className="sector-bar-row" title={`${i.name}: held by ${i.held_by_count} client books`}>
                          <span className="sector-bar-name">{i.name}</span>
                          <span className="sector-bar-track">
                            <span className="sector-bar-fill" style={{ width: `${(i.held_by_count / max) * 100}%`, background: sectorColor(i.sector) }} />
                          </span>
                          <span className="sector-bar-val">{i.held_by_count}</span>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>
            </div>

            <div className="controls" style={{ marginBottom: 16 }}>
              <input
                type="text"
                className="text-input"
                placeholder="Search by name, ticker, or sector..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={{ flex: 1, minWidth: 200 }}
              />
              <div className="select-wrap">
                <select value={group} onChange={(e) => setGroup(e.target.value)}>
                  <option value="All">All asset classes</option>
                  {data.groups.map((g) => (
                    <option key={g.asset_class} value={g.asset_class}>{g.asset_class}</option>
                  ))}
                </select>
              </div>
            </div>

            {groups.map((g) => (
              <div key={g.asset_class} className="fade-in" style={{ marginBottom: 22 }}>
                <div className="shead" style={{ marginTop: 8 }}>
                  <span className="chip-dot" style={{ background: assetClassColor(g.asset_class), width: 8, height: 8, marginRight: 8, display: "inline-block", borderRadius: 2 }} />
                  {g.asset_class}
                  <span className="shead-count">{g.items.length}</span>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th>Type</th>
                        <th>Sector</th>
                        <th style={{ textAlign: "right" }}>Vol</th>
                        <th style={{ textAlign: "right" }}>Held by</th>
                      </tr>
                    </thead>
                    <tbody>
                      {g.items.map((i) => (
                        <tr key={i.security_id}>
                          <td>
                            <div className="holding-cell">
                              <span className="holding-name">{i.name}</span>
                              <span className="holding-tkr">{i.ticker}</span>
                            </div>
                          </td>
                          <td><span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{i.instrument_type}</span></td>
                          <td>
                            <span className="sector-chip" style={{ padding: "3px 8px" }}>
                              <span className="sector-chip-dot" style={{ background: sectorColor(i.sector) }} />
                              <span className="sector-chip-name">{i.sector}</span>
                            </span>
                          </td>
                          <td className="num">{i.vol != null ? `${i.vol}%` : "n/a"}</td>
                          <td className="num">
                            {i.held_by_count === 0 ? (
                              <span className="idle-tag">idle</span>
                            ) : (
                              <span className="held-tag">{i.held_by_count}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </>
        )}

        {!data && !error && <div className="panel"><p>Loading product shelf...</p></div>}

        <footer>Decision-support tool. Not investment advice, not a trading system.</footer>
      </div>
    </>
  );
}
