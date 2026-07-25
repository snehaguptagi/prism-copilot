"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getNewsCategories, getNewsFeed } from "@/lib/api";
import { NewsFeedResult } from "@/lib/types";
import { sourceDomain } from "@/lib/news";
import { avatarColor, initials } from "@/lib/colors";
import CategoryIcon from "@/components/CategoryIcon";
import Topbar from "@/components/Topbar";

const NEWS_STORE_KEY = "prism_news_cache_v1";

type StoredEntry = { result: NewsFeedResult; fetchedAt: number };

function loadStore(): Record<string, StoredEntry> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(NEWS_STORE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveStore(store: Record<string, StoredEntry>) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(NEWS_STORE_KEY, JSON.stringify(store));
  } catch {
    /* quota or serialization issue: skip persisting, in-memory still works */
  }
}

export default function NewsFeedPage() {
  const router = useRouter();
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory] = useState<string>("");
  const [cache, setCache] = useState<Record<string, NewsFeedResult>>({});
  const [fetchedAt, setFetchedAt] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  async function loadCategory(cat: string, force = false) {
    setCategory(cat);
    setShowDetail(false);
    if (!force && cache[cat]) return; // already in memory this session
    setLoading(true);
    setError(null);
    try {
      const result = await getNewsFeed(cat, force);
      const now = Date.now();
      setCache((prev) => ({ ...prev, [cat]: result }));
      setFetchedAt((prev) => ({ ...prev, [cat]: now }));
      const store = loadStore();
      store[cat] = { result, fetchedAt: now };
      saveStore(store);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function timeAgo(ts?: number): string {
    if (!ts) return "";
    const mins = Math.round((Date.now() - ts) / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins} min ago`;
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return `${hrs} hr ago`;
    return `${Math.round(hrs / 24)} d ago`;
  }

  useEffect(() => {
    // hydrate everything we've ever fetched from localStorage so opening the
    // tab shows instantly and never re-fetches on its own
    const store = loadStore();
    const hydratedCache: Record<string, NewsFeedResult> = {};
    const hydratedAt: Record<string, number> = {};
    for (const [cat, entry] of Object.entries(store)) {
      hydratedCache[cat] = entry.result;
      hydratedAt[cat] = entry.fetchedAt;
    }
    setCache(hydratedCache);
    setFetchedAt(hydratedAt);

    getNewsCategories()
      .then((cats) => {
        setCategories(cats);
        const first = cats[0];
        if (!first) return;
        setCategory(first);
        // only fetch if we have nothing stored for the first category
        if (!hydratedCache[first]) loadCategory(first);
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const result = cache[category];

  return (
    <>
      <Topbar />
      <div className="wrap">
        <header className="hero hero-tight">
          <p className="eyebrow">Daily briefing</p>
          <h1>What today&apos;s news means for your clients</h1>
          <p className="lede">
            One read of the market, then straight to which clients it touches and what to tell them.
          </p>
        </header>

        <div className="news-toolbar">
          <div className="news-tabs">
            {categories.map((cat) => (
              <button
                key={cat}
                className={`news-tab${category === cat ? " active" : ""}`}
                onClick={() => loadCategory(cat)}
              >
                <CategoryIcon category={cat} size={14} />
                <span>{cat}</span>
              </button>
            ))}
          </div>
          <button
            className="reload-btn"
            onClick={() => loadCategory(category, true)}
            disabled={loading || !category}
            title="Fetch the latest news for this category"
          >
            <span className={`refresh-icon${loading ? " spinning" : ""}`}>↻</span>
            {loading ? "Reloading" : "Reload"}
          </button>
        </div>

        {result && !loading && (
          <div className="news-fresh-line">
            Last fetched {timeAgo(fetchedAt[category])}. Saved on this device, it will not reload on its own.
          </div>
        )}

        {error && (
          <div className="panel" style={{ borderLeft: "3px solid var(--negative)" }}>
            <p style={{ color: "var(--negative)" }}>{error}</p>
          </div>
        )}

        {loading && (
          <div className="news-loading">
            <span className="spinner" style={{ borderTopColor: "var(--accent)", borderColor: "var(--accent-soft)", borderTopWidth: 2 }} />
            Reading the latest {category} developments and mapping them to your book...
          </div>
        )}

        {result && !loading && (
          <div className="fade-in">
            {/* TL;DR + key-stat infographics */}
            <div className="tldr-card">
              <div className="tldr-kicker">
                <CategoryIcon category={category} size={15} />
                {category} · the one thing to know
              </div>
              <p className="tldr-text">{result.tldr || "No single dominant development in this category today."}</p>
              {result.key_stats.length > 0 && (
                <div className="tldr-stats">
                  {result.key_stats.map((s, i) => (
                    <span className="tldr-stat" key={i}>{s}</span>
                  ))}
                </div>
              )}
            </div>

            {/* key developments as scannable bullets */}
            {result.key_points.length > 0 && (
              <>
                <div className="shead">Key developments</div>
                <ul className="keypoint-list stagger">
                  {result.key_points.map((k, i) => (
                    <li className="keypoint" key={i}>
                      <span className="keypoint-dot" />
                      {k}
                    </li>
                  ))}
                </ul>
              </>
            )}

            {/* per-client talking points */}
            <div className="shead">
              What to tell your clients
              {result.affected_clients.length > 0 && (
                <span className="shead-count">{result.affected_clients.length} affected</span>
              )}
            </div>

            {result.affected_clients.length === 0 ? (
              <div className="panel">
                <p>None of your clients are materially affected by today&apos;s {category} news.</p>
              </div>
            ) : (
              <div className="tp-grid stagger">
                {result.affected_clients.map((c) => (
                  <div
                    className="tp-card"
                    key={c.portfolio_id}
                    role="button"
                    tabIndex={0}
                    onClick={() => router.push(`/clients/${c.portfolio_id}`)}
                    onKeyDown={(e) => e.key === "Enter" && router.push(`/clients/${c.portfolio_id}`)}
                  >
                    <div className="tp-card-head">
                      <div className="avatar" style={{ background: avatarColor(c.client_name) }}>
                        {initials(c.client_name)}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div className="tp-card-name">{c.client_name}</div>
                        <div className="tp-card-how">{c.how_affected}</div>
                      </div>
                    </div>
                    <p className="tp-card-point">{c.talking_point}</p>
                  </div>
                ))}
              </div>
            )}

            {/* progressive disclosure: sources only (the key points ARE the briefing) */}
            <button className="disclose-btn" onClick={() => setShowDetail((v) => !v)}>
              <span className={`disclose-caret${showDetail ? " open" : ""}`}>›</span>
              {showDetail ? "Hide" : "Show"} {result.citations.length} sources
            </button>

            {showDetail && (
              <div className="fade-in" style={{ marginTop: 12 }}>
                <div className="source-grid stagger">
                  {result.citations.map((c, i) => {
                    const domain = sourceDomain(c.url);
                    return (
                      <a className="source-card" href={c.url} target="_blank" rel="noreferrer" key={i}>
                        <span className="source-favi">{domain.charAt(0).toUpperCase()}</span>
                        <span className="source-body">
                          <span className="source-title">{c.title || domain}</span>
                          <span className="source-domain">{domain}</span>
                        </span>
                      </a>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        <footer>
          Decision-support tool. Not investment advice, not a trading system. Talking points are
          generated from computed exposure and grounded news, never buy/sell/hold guidance.
        </footer>
      </div>
    </>
  );
}
