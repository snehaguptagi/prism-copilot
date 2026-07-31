"""
PRISM API — thin FastAPI layer over insight_lens.py, matching the REST
surface already specified in docs/LLD.md §13. Adds no new business logic:
every endpoint just calls the same functions already covered by tests/.

No auth — single-PM demo, open API. Add real authentication before this
ever touches real client data.

Run:
  pip install -r requirements.txt
  uvicorn api:app --reload --port 8000
"""

import json
import os
import re
import tempfile
import time
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import graph
from insight_lens import (
    DATA_PATH,
    NEWS_FEED_CATEGORIES,
    build_query_context,
    compute_factor_impact,
    compute_portfolio_impact,
    compute_scenario_impact,
    attach_reference_comparison,
    detect_cross_desk_contradictions,
    detect_factor_signals,
    extract_citations_and_narrative,
    generate_news_briefing,
    generate_talking_points,
    link_citations_to_securities,
    load_data,
    run_news_feed,
    run_search,
    securities_in_sector,
)
from portfolio_risk import compute_portfolio_risk

app = FastAPI(title="PRISM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PM_NAME = os.environ.get("PM_NAME", "Ananya Rao")
PM_ROLE = os.environ.get("PM_ROLE", "Portfolio Manager")
PM_FIRM = os.environ.get("PM_FIRM", "PwC India")


@app.get("/me")
def get_me():
    return {
        "manager_name": PM_NAME,
        "role": PM_ROLE,
        "firm": PM_FIRM,
    }


class LensRequest(BaseModel):
    sector: str


def sector_breakdown(portfolio_id, data):
    """Ranked list of {sector, weight_pct} for one portfolio — used to show a
    book's exposure and to default the market-analysis flow to the sector the
    portfolio is most exposed to."""
    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    by_sector = {}
    for h in data["holdings"]:
        if h["portfolio_id"] != portfolio_id:
            continue
        sec = sec_by_id.get(h["security_id"])
        if not sec:
            continue
        by_sector[sec["sector"]] = by_sector.get(sec["sector"], 0.0) + h["weight"] * 100
    ranked = sorted(
        ({"sector": s, "weight_pct": round(w, 1)} for s, w in by_sector.items()),
        key=lambda x: x["weight_pct"],
        reverse=True,
    )
    return ranked


def _is_removable_portfolio(portfolio):
    """Only user-created client records are removable from the demo workspace."""
    return (
        portfolio.get("created_via") == "client_form"
        or portfolio.get("portfolio_id", "").startswith("pf_custom_")
    )


def _persist_data(data):
    """Write the dataset atomically so an interrupted mutation cannot corrupt it."""
    data_dir = os.path.dirname(DATA_PATH)
    fd, temp_path = tempfile.mkstemp(prefix=".prism_data_", suffix=".json", dir=data_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(data, temp_file, indent=2)
            temp_file.write("\n")
        os.replace(temp_path, DATA_PATH)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


FACTOR_LABELS = {
    "gold": "Gold price",
    "oil": "Oil price",
    "interest_rates_india": "India interest rates",
    "interest_rates_us": "US interest rates",
    "usd_inr": "Rupee / dollar",
}


def portfolio_insights(portfolio_id, data, risk_block, holdings_out, breakdown):
    """Deterministic, at-a-glance portfolio insight metrics for a client's
    detail page. All computed from the actual holdings, nothing estimated."""
    sec_by_id = {s["security_id"]: s for s in data["securities"]}

    # macro-factor exposure: sum weights of holdings tagged sensitive to each factor
    factor_exposure = {}
    for h in data["holdings"]:
        if h["portfolio_id"] != portfolio_id:
            continue
        sec = sec_by_id.get(h["security_id"])
        if not sec:
            continue
        for factor in sec.get("factor_sensitivities", {}):
            factor_exposure[factor] = factor_exposure.get(factor, 0.0) + h["weight"] * 100
    factor_exposures = sorted(
        ({"factor": FACTOR_LABELS.get(f, f), "pct": round(w, 1)} for f, w in factor_exposure.items()),
        key=lambda x: x["pct"], reverse=True,
    )

    top1_pct = risk_block.get("top1_pct", 0.0)
    if top1_pct >= 40:
        concentration = "High"
    elif top1_pct >= 22:
        concentration = "Moderate"
    else:
        concentration = "Low"

    return {
        "num_holdings": len(holdings_out),
        "num_sectors": len(breakdown),
        "est_vol": risk_block.get("est_vol"),
        "wtd_beta": risk_block.get("wtd_beta"),
        "top_position_name": risk_block.get("top1_name"),
        "top_position_pct": top1_pct,
        "largest_sector": breakdown[0]["sector"] if breakdown else None,
        "largest_sector_pct": breakdown[0]["weight_pct"] if breakdown else None,
        "concentration": concentration,
        "factor_exposures": factor_exposures,
    }


def build_performance(perf, aum, benchmark):
    """Attach the trailing-return figures plus the rupee gain over the last year
    (derived from current AUM and the 1-year return) and the delta versus the
    Nifty 50 benchmark. All arithmetic, no model."""
    if not perf:
        return None
    one_yr = perf.get("one_year_pct", 0.0)
    # value a year ago implied by the 1-year return, so 1y gain in rupees is exact
    value_year_ago = aum / (1 + one_yr / 100) if one_yr > -100 else aum
    gain_1y = aum - value_year_ago
    b = benchmark or {}
    bench_1y = b.get("one_year_pct")
    return {
        "ytd_pct": perf.get("ytd_pct"),
        "one_year_pct": one_yr,
        "three_year_cagr_pct": perf.get("three_year_cagr_pct"),
        "since_inception_cagr_pct": perf.get("since_inception_cagr_pct"),
        "gain_1y": round(gain_1y, 2),
        "benchmark_one_year_pct": bench_1y,
        "vs_benchmark_1y": round(one_yr - bench_1y, 1) if bench_1y is not None else None,
        "horizons": [
            {"label": "YTD", "book": perf.get("ytd_pct"), "benchmark": b.get("ytd_pct")},
            {"label": "1Y", "book": one_yr, "benchmark": bench_1y},
            {"label": "3Y", "book": perf.get("three_year_cagr_pct"), "benchmark": b.get("three_year_cagr_pct")},
        ],
    }


# Which risk tiers are appropriate for each mandate keyword. Used to flag a
# book that has drifted more aggressive or more conservative than the client
# actually signed up for, a genuine suitability / compliance check.
_TIER_RANK = {"Low": 0, "Moderate": 1, "Elevated": 2, "High": 3, "Very High": 4}
_MANDATE_MAX_TIER = {
    "conservative": 1, "conservative-moderate": 2, "conservative-growth": 2, "conservative-income": 2,
    "moderate": 2, "moderate-income": 2, "moderate-passive": 3, "moderate-growth": 3,
    "growth-stable": 3, "growth": 4, "growth-concentrated": 4, "balanced-diversified": 2,
    "aggressive": 4, "aggressive-growth": 4, "aggressive-concentrated": 4,
}
_MANDATE_MIN_TIER = {
    "conservative": 0, "conservative-moderate": 0, "conservative-growth": 0, "conservative-income": 0,
    "moderate": 1, "moderate-income": 1, "moderate-passive": 1, "moderate-growth": 2,
    "growth-stable": 2, "growth": 1, "growth-concentrated": 3, "balanced-diversified": 0,
    "aggressive": 3, "aggressive-growth": 3, "aggressive-concentrated": 4,
}


def check_suitability(mandate, tier):
    """Compare the portfolio's actual risk tier against the client's stated risk
    mandate, and flag mismatches. Deterministic."""
    if not mandate or not tier or tier not in _TIER_RANK:
        return {"status": "unknown", "label": "Not assessed"}
    key = mandate.strip().lower()
    lo = _MANDATE_MIN_TIER.get(key)
    hi = _MANDATE_MAX_TIER.get(key)
    rank = _TIER_RANK[tier]
    if lo is None or hi is None:
        return {"status": "unknown", "label": "Not assessed"}
    if rank > hi:
        return {"status": "aggressive", "label": "More aggressive than mandate", "detail": f"Book is {tier} risk versus a {mandate} mandate. Worth a suitability review."}
    if rank < lo:
        return {"status": "conservative", "label": "More conservative than mandate", "detail": f"Book is {tier} risk versus a {mandate} mandate. May be underinvested for the goal."}
    return {"status": "matched", "label": "Well matched", "detail": f"{tier} risk fits the {mandate} mandate."}


# ---------------------------------------------------------------------------
# Product cross-sell: which sellable securities suit a client and fill a gap.
# Deterministic and suitability-first. This is sales enablement for the RM
# (what fits and is worth raising), NOT advice: it never times the market and
# never tells the client to buy. Same division of labor as everything else.
# ---------------------------------------------------------------------------
_ASSET_CLASS_LABEL = {
    "Equity": "equity",
    "Fixed Income": "fixed income",
    "Commodity": "gold and commodities",
    "Real Estate": "real estate (REIT)",
    "Cash": "cash",
}

PRODUCT_FAMILY_ORDER = ("Gold", "Commodities", "Mutual Funds")


def _product_family(security):
    """Map the wider security master to PRISM's client-facing product shelf."""
    if security.get("instrument_type") == "Mutual Fund":
        return "Mutual Funds"
    if security.get("asset_class") == "Commodity":
        searchable = f"{security.get('name', '')} {security.get('primary_ticker', '')}".lower()
        return "Gold" if "gold" in searchable or security.get("primary_ticker") == "SGB" else "Commodities"
    return None


def _normalise_graph_suggestions(data, suggestions):
    """Keep graph recommendations on the same approved product shelf."""
    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    offered = []
    for suggestion in suggestions:
        security = sec_by_id.get(suggestion["security_id"])
        family = _product_family(security) if security else None
        if family:
            offered.append({**suggestion, "asset_class": family})
    return offered


def _vol_band_rank(vol):
    """Map a security's volatility to the same 0 to 4 risk ladder used for
    portfolios, so a product can be checked against a client's mandate ceiling."""
    if vol is None:
        return 1
    if vol < 5:
        return 0   # Low
    if vol < 12:
        return 1   # Moderate
    if vol < 20:
        return 2   # Elevated
    if vol < 28:
        return 3   # High
    return 4       # Very High


def _preference_profile(client):
    """Turn a client's stated preferences (goal, horizon, loss aversion, life
    stage, persona) into a per-asset-class affinity score plus a short reason
    for each class we lean toward. Deterministic keyword rules, no model."""
    psy = client.get("psychographics", {}) or {}
    goal = (psy.get("primary_goal") or "").lower()
    horizon = (psy.get("time_horizon") or "").lower()
    loss = (psy.get("loss_aversion") or "").lower()
    stage = (psy.get("life_stage") or "").lower()
    text = " ".join([goal, (client.get("persona") or "").lower()])

    aff = {"Equity": 0.0, "Fixed Income": 0.0, "Commodity": 0.0, "Real Estate": 0.0}
    reasons = {}

    def bump(cls, amt, reason):
        aff[cls] = aff.get(cls, 0.0) + amt
        if amt > 0 and cls not in reasons:
            reasons[cls] = reason

    if any(k in text for k in ["income", "withdraw", "wedding", "predictable", "rental", "distribution"]):
        bump("Fixed Income", 2.5, "their focus on steady, predictable income")
        bump("Real Estate", 1.5, "their preference for rental-style income")
    if any(k in text for k in ["preserve", "safety", "protect", "preservation", "medical", "capital safety"]):
        bump("Fixed Income", 2.0, "their capital-preservation goal")
    if any(k in text for k in ["inflation", "hedge", "gold", "depreciation"]):
        bump("Commodity", 2.5, "their inflation-hedge preference")
    if any(k in text for k in ["growth", "compound", "wealth", "long-term", "aggressive"]):
        bump("Equity", 2.0, "their long-term growth focus")
    if any(k in text for k in ["index", "low-cost", "market return", "passive", "diversified"]):
        bump("Equity", 1.5, "their preference for broad, low-cost market exposure")

    if "short" in horizon:
        bump("Fixed Income", 1.5, "their short time horizon")
        aff["Equity"] -= 1.0
    if "long" in horizon or "10 year" in horizon or "generational" in horizon:
        bump("Equity", 1.0, "their long time horizon")

    if "high" in loss:  # covers "high" and "very high"
        bump("Fixed Income", 1.0, "their high loss aversion")
        bump("Commodity", 0.5, "their caution around drawdowns")
        aff["Equity"] -= 0.5
    if "low" in loss:
        bump("Equity", 1.0, "their comfort with volatility")

    if "retired" in stage:
        bump("Fixed Income", 1.0, "their retirement life stage")
    if "early" in stage:
        bump("Equity", 1.0, "their early-career stage and long runway")

    return aff, reasons


def suggest_products(data, portfolio, max_n=3):
    """Sellable securities the client does not already hold, ranked by how well
    they match the client's stated PREFERENCES (goal, horizon, loss aversion,
    life stage), gated by their risk mandate and nudged toward asset-class gaps.
    Each carries a plain, preference-referencing rationale. Fully deterministic.
    Sales enablement, never a market-timing buy call."""
    client = portfolio.get("client", {})
    mandate = (client.get("risk_mandate") or "").strip()
    max_band = _MANDATE_MAX_TIER.get(mandate.lower(), 2)
    aff, reasons = _preference_profile(client)

    pid = portfolio["portfolio_id"]
    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    held = {h["security_id"] for h in data["holdings"] if h["portfolio_id"] == pid}

    class_weight = {}
    for h in data["holdings"]:
        if h["portfolio_id"] != pid:
            continue
        s = sec_by_id.get(h["security_id"])
        if s:
            class_weight[s["asset_class"]] = class_weight.get(s["asset_class"], 0.0) + h["weight"]

    client_pids = {p["portfolio_id"] for p in data["portfolios"] if p.get("client") and not p.get("is_reference")}
    held_count = {}
    for h in data["holdings"]:
        if h["portfolio_id"] in client_pids:
            held_count[h["security_id"]] = held_count.get(h["security_id"], 0) + 1

    candidates = []
    for s in data["securities"]:
        sid = s["security_id"]
        if sid in held:
            continue
        family = _product_family(s)
        if not family:
            continue  # PRISM currently offers Gold, Commodities, and Mutual Funds
        if _vol_band_rank(s.get("vol")) > max_band:
            continue  # too risky for this client's mandate
        cls = s["asset_class"]
        gap = class_weight.get(cls, 0.0)
        gap_bonus = 1.0 if gap < 0.05 else 0.3  # nudge toward diversification
        established = 0.05 * held_count.get(sid, 0)
        score = aff.get(cls, 0.0) + gap_bonus + established
        candidates.append((score, s))

    candidates.sort(key=lambda t: t[0], reverse=True)

    article = "an" if mandate[:1].lower() in "aeiou" else "a"

    def _entry(s):
        cls = s["asset_class"]
        family = _product_family(s)
        label = _ASSET_CLASS_LABEL.get(cls, cls.lower())
        if cls in reasons:
            why = f"Matches {reasons[cls]}, and fits {article} {mandate} mandate."
        elif class_weight.get(cls, 0.0) <= 0.001:
            why = f"Adds {label} exposure the book currently lacks, within {article} {mandate} mandate."
        else:
            why = f"Rounds out the book with more {label}, within {article} {mandate} mandate."
        return {
            "security_id": s["security_id"],
            "name": s["name"],
            "ticker": s["primary_ticker"],
            "sector": s["sector"],
            "asset_class": family,
            "instrument_type": s["instrument_type"],
            "rationale": why,
        }

    # Lead with the best preference matches, but cap at 2 of any one product family
    # so a strong preference dominates without becoming monotonous.
    out, per_class = [], {}
    for _score, s in candidates:
        family = _product_family(s)
        if per_class.get(family, 0) >= 2:
            continue
        per_class[family] = per_class.get(family, 0) + 1
        out.append(_entry(s))
        if len(out) >= max_n:
            break
    return out


def compute_ranked_matches(rule_suggestions, graph_suggestions, max_n=4):
    """Combine the two recommendation layers into ONE ranked list, not a single
    pick: a client should see several worthwhile products, not just one.
    Ranking: securities both layers independently name come first (the
    strongest signal, a preference fit AND peer validation), ranked among
    themselves by similar-client support; then remaining similar-client-only
    picks by peer count; then remaining preference-only picks in their
    existing preference order. Shared by the per-client and firm-wide views so
    neither can ever disagree with the other."""
    rule_ids = {s["security_id"] for s in rule_suggestions}
    graph_ids = {s["security_id"] for s in graph_suggestions}
    rule_by_id = {s["security_id"]: s for s in rule_suggestions}
    graph_by_id = {s["security_id"]: s for s in graph_suggestions}
    common = rule_ids & graph_ids

    ranked = []

    def _both_entry(sid):
        r, g = rule_by_id[sid], graph_by_id[sid]
        return {
            "security_id": sid, "name": r["name"], "ticker": r["ticker"],
            "asset_class": r["asset_class"], "source": "both", "peers": g.get("peers"),
            "rationale": f"{r['rationale']} Clients with a similar profile independently confirm it: {g['rationale'][0].lower()}{g['rationale'][1:]}",
        }

    for sid in sorted(common, key=lambda s: graph_by_id[s].get("peers", 0), reverse=True):
        ranked.append(_both_entry(sid))
    for s in sorted(graph_suggestions, key=lambda x: x.get("peers", 0), reverse=True):
        if s["security_id"] not in common:
            ranked.append({**s, "source": "graph"})
    for s in rule_suggestions:
        if s["security_id"] not in common:
            ranked.append({**s, "source": "rule"})

    return ranked[:max_n]


def compute_best_match(rule_suggestions, graph_suggestions):
    """The single strongest pick, i.e. the first entry of compute_ranked_matches.
    Kept as its own function since several call sites only need the one pick."""
    ranked = compute_ranked_matches(rule_suggestions, graph_suggestions, max_n=1)
    return ranked[0] if ranked else None


def build_graph_view(data, portfolio, max_held=6):
    """Assemble a small, renderable node/edge graph for one client, for the
    Product Fit tab: the client, their largest holdings, the asset classes
    those touch, and both recommendation layers (preference-based and, if
    configured, similar-client) as candidate nodes, plus a ranked list of
    recommended products (not just one). Fully deterministic, reuses the same
    suggest_products / graph.recommend_products the rest of the app already
    calls, so this tab can never disagree with the suggestion lists shown
    elsewhere."""
    pid = portfolio["portfolio_id"]
    client = portfolio["client"]
    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    pf_holdings = [h for h in data["holdings"] if h["portfolio_id"] == pid]
    top_holdings = sorted(pf_holdings, key=lambda h: h["weight"], reverse=True)[:max_held]

    rule_suggestions = suggest_products(data, portfolio, max_n=4)
    graph_enabled = graph.graph_enabled()
    raw_graph_suggestions = graph.recommend_products(pid, max_n=8) if graph_enabled else []
    graph_suggestions = _normalise_graph_suggestions(data, raw_graph_suggestions)[:4]
    top_matches = compute_ranked_matches(rule_suggestions, graph_suggestions, max_n=4)
    best_match = top_matches[0] if top_matches else None

    nodes, edges, seen_classes = [], [], set()
    nodes.append({"id": "client", "type": "client", "label": client["name"], "sub": client.get("risk_mandate")})

    def ensure_class(cls):
        node_id = f"class:{cls}"
        if cls not in seen_classes:
            seen_classes.add(cls)
            nodes.append({"id": node_id, "type": "asset_class", "label": cls})
        return node_id

    for h in top_holdings:
        s = sec_by_id.get(h["security_id"])
        if not s:
            continue
        node_id = f"held:{s['security_id']}"
        nodes.append({
            "id": node_id, "type": "held", "label": s["name"], "sub": s["primary_ticker"],
            "asset_class": s["asset_class"], "weight_pct": round(h["weight"] * 100, 1),
        })
        edges.append({"source": "client", "target": node_id, "kind": "holds"})
        cls_id = ensure_class(s["asset_class"])
        edges.append({"source": node_id, "target": cls_id, "kind": "in_class"})

    extra_holdings = max(len(pf_holdings) - len(top_holdings), 0)

    def add_suggestion(s, source):
        node_id = f"sugg:{s['security_id']}"
        existing = next((n for n in nodes if n["id"] == node_id), None)
        if existing:
            existing["source"] = "both"
        else:
            nodes.append({
                "id": node_id, "type": "suggested", "label": s["name"], "sub": s["ticker"],
                "asset_class": s["asset_class"], "source": source,
                "peers": s.get("peers"), "rationale": s["rationale"],
                "best": bool(best_match and best_match["security_id"] == s["security_id"]),
            })
            edges.append({"source": "client", "target": node_id, "kind": "suggests"})
            cls_id = ensure_class(s["asset_class"])
            edges.append({"source": node_id, "target": cls_id, "kind": "in_class"})

    for s in rule_suggestions:
        add_suggestion(s, "rule")
    for s in graph_suggestions:
        add_suggestion(s, "graph")

    return {
        "portfolio_id": pid,
        "client_name": client["name"],
        "graph_enabled": graph_enabled,
        "extra_holdings": extra_holdings,
        "nodes": nodes,
        "edges": edges,
        "best_match": best_match,
        "top_matches": top_matches,
    }


def build_overview_graph_view(data):
    """Firm-wide product-fit picture: every client's single best-match product,
    flowing client -> asset class -> product, so the RM can see cross-sell
    concentration across the whole book at a glance (which products would suit
    the most clients right now) rather than one client at a time. Each client
    contributes exactly the same best_match computed by build_graph_view, via
    the shared compute_best_match helper, so this view can never disagree with
    the per-client one. Deterministic aside from the optional similar-client
    lookups, each of which already fails closed to an empty list."""
    graph_enabled = graph.graph_enabled()
    client_nodes, class_nodes, product_nodes = [], {}, {}
    edges_client_class, edges_class_product = [], []
    unmatched_clients = 0

    for p in data["portfolios"]:
        if p.get("is_reference") or not p.get("client"):
            continue
        pid = p["portfolio_id"]
        client = p["client"]
        rule_suggestions = suggest_products(data, p, max_n=4)
        raw_graph_suggestions = graph.recommend_products(pid, max_n=8) if graph_enabled else []
        graph_suggestions = _normalise_graph_suggestions(data, raw_graph_suggestions)[:4]
        best = compute_best_match(rule_suggestions, graph_suggestions)

        client_nodes.append({
            "id": f"client:{pid}", "portfolio_id": pid, "label": client["name"],
            "best_match": best["name"] if best else None,
        })
        if not best:
            unmatched_clients += 1
            continue

        cls = best["asset_class"]
        class_id = f"class:{cls}"
        class_nodes.setdefault(class_id, {"id": class_id, "label": cls})
        edges_client_class.append({"source": f"client:{pid}", "target": class_id})

        prod_id = f"product:{best['security_id']}"
        entry = product_nodes.setdefault(prod_id, {
            "id": prod_id, "label": best["name"], "ticker": best["ticker"],
            "asset_class": cls, "client_names": [], "sources": set(),
        })
        entry["client_names"].append(client["name"])
        entry["sources"].add(best["source"])
        edges_class_product.append({"source": class_id, "target": prod_id})

    products = sorted(
        [
            {
                "id": e["id"], "label": e["label"], "ticker": e["ticker"], "asset_class": e["asset_class"],
                "client_count": len(e["client_names"]), "client_names": e["client_names"],
                "confirmed": "both" in e["sources"],
            }
            for e in product_nodes.values()
        ],
        key=lambda x: x["client_count"],
        reverse=True,
    )
    # dedupe class->product edges, keep a weight (how many clients flow through it)
    class_product_weight = {}
    for e in edges_class_product:
        key = (e["source"], e["target"])
        class_product_weight[key] = class_product_weight.get(key, 0) + 1
    edges_class_product_deduped = [
        {"source": s, "target": t, "weight": w} for (s, t), w in class_product_weight.items()
    ]

    return {
        "graph_enabled": graph_enabled,
        "client_count": len(client_nodes),
        "unmatched_clients": unmatched_clients,
        "clients": client_nodes,
        "classes": list(class_nodes.values()),
        "products": products,
        "edges_client_class": edges_client_class,
        "edges_class_product": edges_class_product_deduped,
        "top_products": products[:8],
    }


# Sectors that have a live market-research lens (i.e. real equities/commodities
# to search on). Cash/Fixed Income holdings don't have a meaningful company-news
# lens, so the analysis flow defaults to the top *researchable* sector.
RESEARCHABLE_SECTORS = {
    "Financials", "Information Technology", "Energy", "Commodity",
    "Consumer Staples", "Consumer Discretionary", "Industrials",
    "Materials", "Health Care", "Communication Services", "Real Estate", "Utilities",
}


@app.get("/sectors")
def get_sectors():
    data = load_data()
    return sorted({s["sector"] for s in data["securities"]})


@app.get("/portfolios")
def get_portfolios():
    data = load_data()
    risk = data["risk"]
    out = []
    for p in data["portfolios"]:
        if p.get("is_reference"):
            continue
        r = risk.get(p["portfolio_id"], {})
        out.append({
            "portfolio_id": p["portfolio_id"],
            "name": p["name"],
            "mandate": p["mandate"],
            "manager_name": p.get("manager_name"),
            "manager_bio": p.get("manager_bio"),
            "risk_driver": p["risk_driver"],
            "risk_tier": r.get("risk_tier"),
            "est_vol": r.get("est_vol"),
            "num_holdings": r.get("num_holdings"),
            "largest_class": r.get("largest_class"),
            "largest_class_pct": r.get("largest_class_pct"),
        })
    return out


@app.get("/clients")
def get_clients():
    """The PM-facing client roster: who owns each portfolio, their contact
    and contract info, and a summary of their actual holdings. Each real
    (non-reference) portfolio belongs to one client persona."""
    data = load_data()
    risk = data["risk"]
    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    holdings_by_portfolio = {}
    for h in data["holdings"]:
        holdings_by_portfolio.setdefault(h["portfolio_id"], []).append(h)

    out = []
    for p in data["portfolios"]:
        if p.get("is_reference") or not p.get("client"):
            continue
        pid = p["portfolio_id"]
        r = risk.get(pid, {})
        pf_holdings = holdings_by_portfolio.get(pid, [])
        aum = sum(h["market_value"] for h in pf_holdings)
        holdings_out = sorted(
            [
                {
                    "security_id": h["security_id"],
                    "name": sec_by_id[h["security_id"]]["name"],
                    "ticker": sec_by_id[h["security_id"]]["primary_ticker"],
                    "weight_pct": round(h["weight"] * 100, 1),
                    "market_value": h["market_value"],
                }
                for h in pf_holdings
            ],
            key=lambda x: x["weight_pct"],
            reverse=True,
        )
        breakdown = sector_breakdown(pid, data)
        suggested = next(
            (b["sector"] for b in breakdown if b["sector"] in RESEARCHABLE_SECTORS),
            None,
        )
        insights = portfolio_insights(pid, data, r, holdings_out, breakdown)
        perf = build_performance(p.get("performance"), aum, data.get("benchmark"))
        suitability = check_suitability(p["client"].get("risk_mandate"), r.get("risk_tier"))
        # asset-class mix for this client's book (for the detail-page donut)
        class_val = {}
        for h in pf_holdings:
            cls = sec_by_id[h["security_id"]]["asset_class"]
            class_val[cls] = class_val.get(cls, 0.0) + h["market_value"]
        asset_class_allocation = sorted(
            [
                {"asset_class": c, "value": round(v, 2), "pct": round(v / aum * 100, 1) if aum else 0.0}
                for c, v in class_val.items()
            ],
            key=lambda x: x["pct"],
            reverse=True,
        )
        out.append({
            "portfolio_id": pid,
            "portfolio_name": p["name"],
            "can_delete": _is_removable_portfolio(p),
            "mandate": p["mandate"],
            "risk_driver": p["risk_driver"],
            "risk_tier": r.get("risk_tier"),
            "est_vol": r.get("est_vol"),
            "aum": aum,
            "client": p["client"],
            "holdings": holdings_out,
            "sector_breakdown": breakdown,
            "asset_class_allocation": asset_class_allocation,
            "suggested_sector": suggested,
            "insights": insights,
            "performance": perf,
            "suitability": suitability,
            "product_suggestions": suggest_products(data, p),
        })
    return out


class AddClientRequest(BaseModel):
    name: str
    occupation: str
    city: str
    risk_mandate: str
    initial_aum: float
    template_portfolio_id: str
    age: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None


def _unique_portfolio_id(name, existing_ids):
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_") or "client"
    candidate = f"pf_custom_{slug}"
    n = 2
    while candidate in existing_ids:
        candidate = f"pf_custom_{slug}_{n}"
        n += 1
    return candidate


@app.post("/clients")
def add_client(req: AddClientRequest):
    """Add a new client at runtime. Clones an existing portfolio's asset mix as
    a starting allocation (scaled to the new client's own AUM) and computes
    risk with the exact same compute_portfolio_risk formula every seeded
    client's risk is computed with, then persists straight into
    prism_data.json. Because load_data() always re-reads that file from disk,
    the new client shows up in every endpoint immediately, no restart needed,
    and survives one. Deliberately does NOT fabricate psychographics, a
    communications log, or trailing performance for a client just added; the
    frontend already renders those as an empty state when absent rather than
    crashing, since existing code paths (build_performance, the Profile tab)
    were already written to tolerate a client with no history."""
    data = load_data()

    name = req.name.strip()
    occupation = req.occupation.strip()
    city = req.city.strip()
    if not name or not occupation or not city:
        raise HTTPException(status_code=400, detail="Name, occupation, and city are required.")
    if req.risk_mandate.strip().lower() not in _MANDATE_MAX_TIER:
        raise HTTPException(status_code=400, detail=f"Unknown risk mandate '{req.risk_mandate}'.")
    if req.initial_aum <= 0:
        raise HTTPException(status_code=400, detail="initial_aum must be positive.")
    if req.age is not None and not 18 <= req.age <= 100:
        raise HTTPException(status_code=400, detail="age must be between 18 and 100.")
    template = next((p for p in data["portfolios"] if p["portfolio_id"] == req.template_portfolio_id), None)
    if not template or template.get("is_reference") or not template.get("client"):
        raise HTTPException(status_code=404, detail=f"No template portfolio '{req.template_portfolio_id}'.")

    template_weights = {
        h["security_id"]: h["weight"] for h in data["holdings"] if h["portfolio_id"] == req.template_portfolio_id
    }
    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    norm_holdings, market_values, risk_block = compute_portfolio_risk(req.initial_aum, template_weights, sec_by_id)

    existing_ids = {p["portfolio_id"] for p in data["portfolios"]}
    new_pid = _unique_portfolio_id(name, existing_ids)
    today = date.today().isoformat()

    data["portfolios"].append({
        "portfolio_id": new_pid,
        "created_via": "client_form",
        "desk_id": template["desk_id"],
        "name": f"{name}'s Portfolio",
        "base_ccy": "INR",
        "risk_driver": template["risk_driver"],
        "mandate": f"Custom mandate, initial allocation modeled on the {template['name']} strategy.",
        "manager_name": PM_NAME,
        "manager_bio": f"{PM_ROLE} at {PM_FIRM}.",
        "client": {
            "name": name,
            "age": req.age,
            "occupation": occupation,
            "persona": "New client. Full behavioral profile to be added by the relationship manager.",
            "email": req.email,
            "phone": req.phone,
            "city": city,
            "relationship_since": today,
            "aum_fee_pct": 1.0,
            "risk_mandate": req.risk_mandate,
        },
    })

    hid_nums = [int(h["holding_id"].split("_")[1]) for h in data["holdings"] if h["holding_id"].startswith("hld_")]
    next_hid = max(hid_nums, default=0) + 1
    for sec_id, weight in norm_holdings.items():
        data["holdings"].append({
            "holding_id": f"hld_{next_hid:04d}",
            "portfolio_id": new_pid,
            "security_id": sec_id,
            "weight": weight,
            "market_value": market_values[sec_id],
            "as_of_date": today,
        })
        next_hid += 1

    data["risk"][new_pid] = risk_block
    _persist_data(data)
    globals().get("_NEWS_CACHE", {}).clear()

    return {"portfolio_id": new_pid, "client_name": name, "risk_tier": risk_block["risk_tier"]}


@app.delete("/clients/{portfolio_id}")
def delete_client(portfolio_id: str):
    """Remove a client created through PRISM, including its holdings and risk data."""
    data = load_data()
    portfolio = next((p for p in data["portfolios"] if p["portfolio_id"] == portfolio_id), None)
    if not portfolio or not portfolio.get("client"):
        raise HTTPException(status_code=404, detail=f"No client portfolio found for '{portfolio_id}'.")
    if not _is_removable_portfolio(portfolio):
        raise HTTPException(status_code=403, detail="Seeded demonstration clients cannot be removed.")

    client_name = portfolio["client"]["name"]
    removed_holdings = sum(1 for h in data["holdings"] if h["portfolio_id"] == portfolio_id)
    data["portfolios"] = [p for p in data["portfolios"] if p["portfolio_id"] != portfolio_id]
    data["holdings"] = [h for h in data["holdings"] if h["portfolio_id"] != portfolio_id]
    data["risk"].pop(portfolio_id, None)
    _persist_data(data)
    globals().get("_NEWS_CACHE", {}).clear()

    return {
        "portfolio_id": portfolio_id,
        "client_name": client_name,
        "removed_holdings": removed_holdings,
    }


@app.get("/overview")
def get_overview():
    """Firm-wide book summary for the PM landing page. Everything here is a
    deterministic aggregation of the actual holdings, weighted by market value,
    no model in the loop and no estimated figures."""
    data = load_data()
    risk = data["risk"]
    sec_by_id = {s["security_id"]: s for s in data["securities"]}

    client_portfolios = [p for p in data["portfolios"] if p.get("client") and not p.get("is_reference")]
    client_pids = {p["portfolio_id"] for p in client_portfolios}
    aum_by_portfolio = {}
    for h in data["holdings"]:
        if h["portfolio_id"] in client_pids:
            aum_by_portfolio[h["portfolio_id"]] = aum_by_portfolio.get(h["portfolio_id"], 0.0) + h["market_value"]
    total_aum = sum(aum_by_portfolio.values())

    # aggregate exposure across the whole book, by market value
    by_asset_class = {}
    by_sector = {}
    by_security = {}
    for h in data["holdings"]:
        if h["portfolio_id"] not in client_pids:
            continue
        sec = sec_by_id.get(h["security_id"])
        if not sec:
            continue
        mv = h["market_value"]
        by_asset_class[sec["asset_class"]] = by_asset_class.get(sec["asset_class"], 0.0) + mv
        by_sector[sec["sector"]] = by_sector.get(sec["sector"], 0.0) + mv
        agg = by_security.setdefault(h["security_id"], {"value": 0.0, "held_by": set()})
        agg["value"] += mv
        agg["held_by"].add(h["portfolio_id"])

    def pct(v):
        return round(v / total_aum * 100, 1) if total_aum else 0.0

    asset_class_allocation = sorted(
        ({"asset_class": k, "value": v, "pct": pct(v)} for k, v in by_asset_class.items()),
        key=lambda x: x["value"], reverse=True,
    )
    sector_allocation = sorted(
        ({"sector": k, "value": v, "pct": pct(v)} for k, v in by_sector.items()),
        key=lambda x: x["value"], reverse=True,
    )
    top_holdings = sorted(
        (
            {
                "security_id": sid,
                "name": sec_by_id[sid]["name"],
                "ticker": sec_by_id[sid]["primary_ticker"],
                "sector": sec_by_id[sid]["sector"],
                "value": agg["value"],
                "pct_of_book": pct(agg["value"]),
                "held_by_count": len(agg["held_by"]),
            }
            for sid, agg in by_security.items()
        ),
        key=lambda x: x["value"], reverse=True,
    )[:10]

    tier_order = ["Low", "Moderate", "Elevated", "High", "Very High"]
    risk_distribution = []
    for tier in tier_order:
        pids = [p["portfolio_id"] for p in client_portfolios if risk.get(p["portfolio_id"], {}).get("risk_tier") == tier]
        risk_distribution.append({
            "tier": tier,
            "count": len(pids),
            "aum": sum(aum_by_portfolio.get(pid, 0.0) for pid in pids),
        })

    largest_clients = sorted(
        (
            {
                "portfolio_id": p["portfolio_id"],
                "client_name": p["client"]["name"],
                "portfolio_name": p["name"],
                "risk_tier": risk.get(p["portfolio_id"], {}).get("risk_tier"),
                "aum": aum_by_portfolio.get(p["portfolio_id"], 0.0),
            }
            for p in client_portfolios
        ),
        key=lambda x: x["aum"], reverse=True,
    )

    fees = [p["client"]["aum_fee_pct"] for p in client_portfolios]
    # blended fee = fee-weighted by AUM (a true blended rate, not a naive mean)
    blended_fee = (
        round(sum(aum_by_portfolio.get(p["portfolio_id"], 0.0) * p["client"]["aum_fee_pct"]
                  for p in client_portfolios) / total_aum, 2)
        if total_aum else 0.0
    )
    annual_fee_revenue = sum(
        aum_by_portfolio.get(p["portfolio_id"], 0.0) * p["client"]["aum_fee_pct"] / 100
        for p in client_portfolios
    )

    # action items: each client's next action, soonest due first, so the PM
    # lands on "what needs attention". "today" is the demo's fixed date.
    today = date(2026, 7, 24)
    prio_rank = {"High": 0, "Normal": 1, "Low": 2}
    action_items = []
    for p in client_portfolios:
        na = p["client"].get("next_action")
        if not na:
            continue
        try:
            due = date.fromisoformat(na["due"])
            days = (due - today).days
        except (ValueError, KeyError):
            days = None
        action_items.append({
            "portfolio_id": p["portfolio_id"],
            "client_name": p["client"]["name"],
            "action": na["action"],
            "due": na.get("due"),
            "priority": na.get("priority", "Normal"),
            "days_until_due": days,
            "overdue": days is not None and days < 0,
        })
    action_items.sort(key=lambda a: (
        a["days_until_due"] if a["days_until_due"] is not None else 9999,
        prio_rank.get(a["priority"], 1),
    ))

    # book performance: AUM-weighted returns across horizons, plus best/worst books
    perf_rows = []
    weighted = {"ytd_pct": 0.0, "one_year_pct": 0.0, "three_year_cagr_pct": 0.0}
    for p in client_portfolios:
        perf = p.get("performance")
        w = aum_by_portfolio.get(p["portfolio_id"], 0.0)
        if not perf:
            continue
        for k in weighted:
            weighted[k] += (perf.get(k) or 0.0) * w
        perf_rows.append({
            "portfolio_id": p["portfolio_id"],
            "client_name": p["client"]["name"],
            "portfolio_name": p["name"],
            "one_year_pct": perf["one_year_pct"],
        })
    book_ytd = round(weighted["ytd_pct"] / total_aum, 1) if total_aum else 0.0
    book_1y = round(weighted["one_year_pct"] / total_aum, 1) if total_aum else 0.0
    book_3y = round(weighted["three_year_cagr_pct"] / total_aum, 1) if total_aum else 0.0
    perf_sorted = sorted(perf_rows, key=lambda x: x["one_year_pct"], reverse=True)
    bench = data.get("benchmark", {})

    return {
        "kpis": {
            "total_aum": total_aum,
            "client_count": len(client_portfolios),
            "holdings_count": sum(1 for h in data["holdings"] if h["portfolio_id"] in client_pids),
            "distinct_securities": len(by_security),
            "blended_fee_pct": blended_fee,
            "annual_fee_revenue": annual_fee_revenue,
        },
        "performance": {
            "book_ytd_pct": book_ytd,
            "book_one_year_pct": book_1y,
            "book_three_year_cagr_pct": book_3y,
            "benchmark_name": bench.get("name", "Nifty 50"),
            "benchmark_ytd_pct": bench.get("ytd_pct"),
            "benchmark_one_year_pct": bench.get("one_year_pct"),
            "benchmark_three_year_cagr_pct": bench.get("three_year_cagr_pct"),
            "vs_benchmark_1y": round(book_1y - bench.get("one_year_pct", 0), 1) if bench.get("one_year_pct") is not None else None,
            "horizons": [
                {"label": "YTD", "book": book_ytd, "benchmark": bench.get("ytd_pct")},
                {"label": "1Y", "book": book_1y, "benchmark": bench.get("one_year_pct")},
                {"label": "3Y", "book": book_3y, "benchmark": bench.get("three_year_cagr_pct")},
            ],
            "best": perf_sorted[0] if perf_sorted else None,
            "worst": perf_sorted[-1] if perf_sorted else None,
        },
        "action_items": action_items,
        "risk_distribution": risk_distribution,
        "asset_class_allocation": asset_class_allocation,
        "sector_allocation": sector_allocation,
        "top_holdings": top_holdings,
        "largest_clients": largest_clients,
    }


@app.get("/products")
def get_products():
    """The approved PRISM product shelf: Gold, Commodities, and Mutual Funds."""
    data = load_data()
    client_pids = {p["portfolio_id"] for p in data["portfolios"] if p.get("client") and not p.get("is_reference")}
    held_count = {}
    for h in data["holdings"]:
        if h["portfolio_id"] in client_pids:
            held_count.setdefault(h["security_id"], set()).add(h["portfolio_id"])

    by_class = {}
    for s in data["securities"]:
        family = _product_family(s)
        if not family:
            continue
        item = {
            "security_id": s["security_id"],
            "name": s["name"],
            "ticker": s["primary_ticker"],
            "sector": s["sector"],
            "instrument_type": s["instrument_type"],
            "asset_class": family,
            "vol": s.get("vol"),
            "beta": s.get("beta"),
            "credit_quality": s.get("credit_quality"),
            "held_by_count": len(held_count.get(s["security_id"], set())),
        }
        by_class.setdefault(family, []).append(item)

    # Keep the three client-facing product lines in a predictable order.
    groups = []
    for asset_class in PRODUCT_FAMILY_ORDER:
        if asset_class not in by_class:
            continue
        items = sorted(by_class[asset_class], key=lambda x: (-x["held_by_count"], x["name"]))
        groups.append({"asset_class": asset_class, "count": len(items), "items": items})

    return {
        "total": sum(g["count"] for g in groups),
        "groups": groups,
    }


@app.get("/graph/status")
def graph_status():
    """Whether the Neo4j knowledge graph is configured and reachable, so the UI
    can decide whether to show graph-powered suggestions."""
    return {"enabled": graph.graph_enabled(), "connected": graph.ping()}


@app.get("/clients/{portfolio_id}/graph-suggestions")
def client_graph_suggestions(portfolio_id: str):
    """Knowledge-graph product suggestions for one client: products in an asset
    class they prefer, not already held, within their risk mandate, ranked by how
    many similar clients hold each. Returns an empty list (never an error) when
    the graph is not configured, so the page degrades gracefully."""
    data = load_data()
    portfolio = next((p for p in data["portfolios"] if p["portfolio_id"] == portfolio_id), None)
    if not portfolio or not portfolio.get("client"):
        raise HTTPException(status_code=404, detail=f"No client portfolio found for '{portfolio_id}'.")
    raw_suggestions = graph.recommend_products(portfolio_id, max_n=8)
    return {
        "enabled": graph.graph_enabled(),
        "suggestions": _normalise_graph_suggestions(data, raw_suggestions)[:4],
    }


@app.get("/clients/{portfolio_id}/graph-view")
def client_graph_view(portfolio_id: str):
    """Renderable graph (nodes + edges) for the visual Graph tab: this client,
    their largest holdings, the asset classes touched, both recommendation
    layers, and the single best product to highlight. Works with or without
    Neo4j configured; the graph-specific nodes/edges are simply absent when
    it is not."""
    data = load_data()
    portfolio = next((p for p in data["portfolios"] if p["portfolio_id"] == portfolio_id), None)
    if not portfolio or not portfolio.get("client"):
        raise HTTPException(status_code=404, detail=f"No client portfolio found for '{portfolio_id}'.")
    return build_graph_view(data, portfolio)


@app.get("/graph/overview")
def graph_overview():
    """Firm-wide Product Fit view: every client's best-match product, flowing
    client -> asset class -> product, plus a top-products leaderboard, so the
    RM can see cross-sell concentration across the whole book at a glance."""
    data = load_data()
    return build_overview_graph_view(data)


@app.get("/news/categories")
def get_news_categories():
    return list(NEWS_FEED_CATEGORIES.keys())


FACTOR_MATERIALITY_PCT = 15.0
# The briefing surfaces the clients a story MOST affects, not every book with
# some diffuse macro exposure. Cap keeps the "what to tell your clients" list
# focused and the per-client LLM call bounded.
NEWS_MAX_AFFECTED = 8

# Human-readable names for the macro factors, for the "how affected" line.
_FACTOR_LABEL = {
    "gold": "gold prices",
    "oil": "oil prices",
    "interest_rates_india": "Indian interest rates",
    "interest_rates_us": "US interest rates",
    "usd_inr": "the rupee",
}


def _material_factors(factor_entry, min_pct=FACTOR_MATERIALITY_PCT):
    """Return EVERY macro factor (not just the single largest) whose exposure
    clears the materiality threshold, as a list of {factor, label, effect, pct}
    sorted by pct desc. A client can be genuinely, materially exposed to more
    than one distinct driver in the same day's news (e.g. a rate headwind on
    their bonds AND a gold tailwind on their commodity sleeve); both deserve
    their own line rather than only ever keeping the single largest. Each
    holding has one fixed effect (tailwind or headwind) per factor, so a given
    factor is reported once, in whichever direction its own exposure nets to."""
    per_factor_effect = {}  # (factor, effect) -> {security_id: weight_pct}, dedup within a factor+effect
    for m in factor_entry.get("matched", []):
        key = (m["factor"], m["effect"])
        per_factor_effect.setdefault(key, {})[m["security_id"]] = m["weight_pct"]

    per_factor_totals = {}  # factor -> (effect, pct), keep the larger-exposure effect per factor
    for (factor, effect), weights in per_factor_effect.items():
        pct = round(min(sum(weights.values()), 100.0), 1)
        existing = per_factor_totals.get(factor)
        if not existing or pct > existing[1]:
            per_factor_totals[factor] = (effect, pct)

    out = [
        {"factor": factor, "label": _FACTOR_LABEL.get(factor, "macro moves"), "effect": effect, "pct": pct}
        for factor, (effect, pct) in per_factor_totals.items()
        if pct >= min_pct
    ]
    out.sort(key=lambda x: x["pct"], reverse=True)
    return out


_STAT_RE = re.compile(
    r"(?:[+-]?\d[\d,.]*\s?%|₹\s?[\d,.]+\s?(?:crore|cr|lakh|trillion|billion)?|"
    r"\$\s?[\d,.]+\s?(?:trillion|billion|million|bn|mn)?)",
    re.IGNORECASE,
)


def _extract_key_stats(narrative, limit=4):
    """A few salient numeric callouts from the narrative for the infographic
    row. Deterministic regex, deduped, short ones only."""
    seen, out = set(), []
    for m in _STAT_RE.findall(narrative or ""):
        s = " ".join(m.split()).strip()
        if len(s) > 16 or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return out


# In-process news cache: category -> {"at": epoch_seconds, "payload": {...}}.
# A briefing is expensive (three model calls), so we serve a cached copy until
# it ages past NEWS_CACHE_TTL or the caller forces a refresh. Survives across
# requests for the life of the server process.
_NEWS_CACHE: dict[str, dict] = {}
NEWS_CACHE_TTL = 6 * 3600  # 6 hours


@app.get("/news/feed")
def get_news_feed(category: str, force: bool = False):
    """Manager-facing news briefing. Rather than a wall of stories, it returns a
    one-line TL;DR, clean key-point bullets, and, for each client the news
    actually affects (by direct holding OR by macro/commodity factor), a
    tailored talking point. Cached per category so opening the tab does not
    re-run the pipeline; pass force=true to refresh."""
    if category not in NEWS_FEED_CATEGORIES:
        raise HTTPException(status_code=404, detail=f"Unknown news category '{category}'. Valid: {list(NEWS_FEED_CATEGORIES.keys())}")

    cached = _NEWS_CACHE.get(category)
    if not force and cached and (time.time() - cached["at"]) < NEWS_CACHE_TTL:
        return {**cached["payload"], "cached": True, "fetched_at": cached["at"]}

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set on the server.")

    data = load_data()
    portfolio_meta = {
        p["portfolio_id"]: {"portfolio_name": p["name"], "client": p["client"]}
        for p in data["portfolios"]
        if p.get("client")
    }

    response = run_news_feed(category)
    extracted = extract_citations_and_narrative(response)
    narrative = extracted["narrative"]
    linked = link_citations_to_securities(extracted["citations"], data["securities"])

    # Two independent ways the news can touch a client: a held name is in the
    # news (entity link), or a macro factor moved (factor sensitivity).
    portfolio_impact = compute_portfolio_impact(data, linked)
    direct_pct = {p["portfolio_id"]: p["pct_nav_touched"] for p in portfolio_impact}

    factor_signals = detect_factor_signals(narrative)
    factor_impact = compute_factor_impact(data, factor_signals)
    factor_by_pid = {p["portfolio_id"]: p for p in factor_impact}

    # union of affected client portfolios, each with a plain "how_affected" line.
    # A materiality score ranks them so the tab leads with the clients a story
    # touches MOST: a name held directly in the news weighs more than diffuse
    # macro exposure that half the book shares.
    affected_pids = set(direct_pct) | set(factor_by_pid)
    affected = []
    for pid in affected_pids:
        if pid not in portfolio_meta:
            continue
        how = []
        material = 0.0
        material_factors = []
        if direct_pct.get(pid, 0) > 0:
            how.append(f"{direct_pct[pid]}% of NAV in names directly in the news")
            material += direct_pct[pid] * 2.0  # a directly-named holding is the strongest signal
        fi = factor_by_pid.get(pid)
        if fi:
            material_factors = _material_factors(fi)
            for f in material_factors:
                how.append(f"{f['pct']}% of NAV is a {f['effect']} from {f['label']}")
                material += f["pct"]
        if not how:
            continue
        meta = portfolio_meta[pid]
        if len(how) == 1:
            how_text = how[0]
        elif len(how) == 2:
            how_text = " and ".join(how)
        else:
            how_text = ", ".join(how[:-1]) + f", and {how[-1]}"
        affected.append({
            "portfolio_id": pid,
            "portfolio_name": meta["portfolio_name"],
            "client_name": meta["client"]["name"],
            "material_factors": material_factors,
            "persona": meta["client"]["persona"],
            "how_affected": how_text,
            "direct_pct": direct_pct.get(pid, 0.0),
            "material": material,
            "factor": factor_by_pid.get(pid),
        })
    affected.sort(key=lambda a: a["material"], reverse=True)
    affected = affected[:NEWS_MAX_AFFECTED]  # focus: the most-affected clients only

    briefing = generate_news_briefing(category, narrative, affected)

    affected_clients = [
        {
            "portfolio_id": a["portfolio_id"],
            "portfolio_name": a["portfolio_name"],
            "client_name": a["client_name"],
            "how_affected": a["how_affected"],
            "talking_point": briefing["points"].get(a["portfolio_id"], ""),
        }
        for a in affected
    ]

    # a few key numeric callouts pulled from the narrative for the infographic row
    key_stats = _extract_key_stats(narrative)

    payload = {
        "category": category,
        "tldr": briefing["tldr"],
        "key_points": briefing.get("key_points", []),
        "key_stats": key_stats,
        "affected_clients": affected_clients,
        "narrative": narrative,
        "citations": linked,
        "note": "Observational output only. No buy/sell/hold guidance is generated at any stage.",
    }
    now = time.time()
    _NEWS_CACHE[category] = {"at": now, "payload": payload}
    return {**payload, "cached": False, "fetched_at": now}


@app.post("/lens/run")
def run_lens(req: LensRequest):
    # Validate the request (404) before checking for the key (500), so a bad
    # request is rejected the same way whether or not the server has a key.
    data = load_data()
    sector_secs = securities_in_sector(data, req.sector)
    if not sector_secs:
        raise HTTPException(status_code=404, detail=f"No securities found for sector '{req.sector}'.")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set on the server.")

    company_names = build_query_context(sector_secs)
    response = run_search(req.sector, company_names)
    extracted = extract_citations_and_narrative(response)
    linked = link_citations_to_securities(extracted["citations"], data["securities"])
    portfolio_impact = compute_portfolio_impact(data, linked)
    portfolio_impact_vs_ref = attach_reference_comparison(portfolio_impact)
    factor_signals = detect_factor_signals(extracted["narrative"])
    factor_impact = compute_factor_impact(data, factor_signals)
    cross_desk = detect_cross_desk_contradictions(data, factor_impact)
    scenario = compute_scenario_impact(data, factor_signals)

    return {
        "sector": req.sector,
        "narrative": extracted["narrative"],
        "citations": linked,
        "portfolio_impact": portfolio_impact_vs_ref,
        "factor_signals": factor_signals,
        "factor_impact": factor_impact,
        "cross_desk_contradictions": cross_desk,
        "scenario_impact": scenario,
        "note": "Observational output only. No buy/sell/hold guidance is generated at any stage.",
    }


class TalkingPointsRequest(BaseModel):
    portfolio_id: str
    sector: str


@app.post("/talking-points")
def talking_points(req: TalkingPointsRequest):
    """Runs the same sector lens as /lens/run, then has an LLM phrase the
    already-computed numbers for ONE specific client's portfolio as natural
    talking points for a relationship-manager call. The LLM only narrates
    the numbers produced below — it never computes exposure itself."""
    # Validate the request (404) before checking for the key (500).
    data = load_data()
    portfolio = next((p for p in data["portfolios"] if p["portfolio_id"] == req.portfolio_id), None)
    if not portfolio or not portfolio.get("client"):
        raise HTTPException(status_code=404, detail=f"No client portfolio found for '{req.portfolio_id}'.")

    sector_secs = securities_in_sector(data, req.sector)
    if not sector_secs:
        raise HTTPException(status_code=404, detail=f"No securities found for sector '{req.sector}'.")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set on the server.")

    company_names = build_query_context(sector_secs)
    response = run_search(req.sector, company_names)
    extracted = extract_citations_and_narrative(response)
    linked = link_citations_to_securities(extracted["citations"], data["securities"])
    portfolio_impact = compute_portfolio_impact(data, linked)
    portfolio_impact_vs_ref = attach_reference_comparison(portfolio_impact)
    factor_signals = detect_factor_signals(extracted["narrative"])
    factor_impact = compute_factor_impact(data, factor_signals)

    impact_entry = next((p for p in portfolio_impact_vs_ref if p["portfolio_id"] == req.portfolio_id), None)
    factor_entry = next((p for p in factor_impact if p["portfolio_id"] == req.portfolio_id), None)

    tp = generate_talking_points(
        client=portfolio["client"],
        portfolio_name=portfolio["name"],
        mandate=portfolio["mandate"],
        sector=req.sector,
        narrative=extracted["narrative"],
        impact_entry=impact_entry,
        factor_entry=factor_entry,
    )

    return {
        "portfolio_id": req.portfolio_id,
        "portfolio_name": portfolio["name"],
        "client_name": portfolio["client"]["name"],
        "sector": req.sector,
        "market_insights": tp["market_insights"],
        "citations": linked,
        "impact": impact_entry,
        "factor_impact": factor_entry,
        "points": tp["points"],
        "product_suggestions": suggest_products(data, portfolio),
        "note": "Observational output only. No buy/sell/hold guidance is generated at any stage.",
    }
