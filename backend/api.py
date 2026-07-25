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

import os
import re
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from insight_lens import (
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

app = FastAPI(title="PRISM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PM_NAME = os.environ.get("PM_NAME", "Ananya Rao")


@app.get("/me")
def get_me():
    return {"manager_name": PM_NAME}


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
        out.append({
            "portfolio_id": pid,
            "portfolio_name": p["name"],
            "mandate": p["mandate"],
            "risk_driver": p["risk_driver"],
            "risk_tier": r.get("risk_tier"),
            "est_vol": r.get("est_vol"),
            "aum": aum,
            "client": p["client"],
            "holdings": holdings_out,
            "sector_breakdown": breakdown,
            "suggested_sector": suggested,
            "insights": insights,
        })
    return out


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

    return {
        "kpis": {
            "total_aum": total_aum,
            "client_count": len(client_portfolios),
            "holdings_count": sum(1 for h in data["holdings"] if h["portfolio_id"] in client_pids),
            "distinct_securities": len(by_security),
            "blended_fee_pct": blended_fee,
            "annual_fee_revenue": annual_fee_revenue,
        },
        "risk_distribution": risk_distribution,
        "asset_class_allocation": asset_class_allocation,
        "sector_allocation": sector_allocation,
        "top_holdings": top_holdings,
        "largest_clients": largest_clients,
    }


@app.get("/products")
def get_products():
    """The investable universe the desk can offer clients: every security in
    the securities master, grouped by asset class, with how many client books
    currently hold each (so the manager sees what is already in use vs. idle).
    Deterministic, no model."""
    data = load_data()
    client_pids = {p["portfolio_id"] for p in data["portfolios"] if p.get("client") and not p.get("is_reference")}
    held_count = {}
    for h in data["holdings"]:
        if h["portfolio_id"] in client_pids:
            held_count.setdefault(h["security_id"], set()).add(h["portfolio_id"])

    by_class = {}
    for s in data["securities"]:
        item = {
            "security_id": s["security_id"],
            "name": s["name"],
            "ticker": s["primary_ticker"],
            "sector": s["sector"],
            "instrument_type": s["instrument_type"],
            "asset_class": s["asset_class"],
            "vol": s.get("vol"),
            "beta": s.get("beta"),
            "credit_quality": s.get("credit_quality"),
            "held_by_count": len(held_count.get(s["security_id"], set())),
        }
        by_class.setdefault(s["asset_class"], []).append(item)

    # order groups by size, names within a group by usage then name
    groups = []
    for asset_class in sorted(by_class, key=lambda k: len(by_class[k]), reverse=True):
        items = sorted(by_class[asset_class], key=lambda x: (-x["held_by_count"], x["name"]))
        groups.append({"asset_class": asset_class, "count": len(items), "items": items})

    return {
        "total": sum(g["count"] for g in groups),
        "groups": groups,
    }


@app.get("/news/categories")
def get_news_categories():
    return list(NEWS_FEED_CATEGORIES.keys())


FACTOR_MATERIALITY_PCT = 15.0

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

    # union of affected client portfolios, each with a plain "how_affected" line
    affected_pids = set(direct_pct) | set(factor_by_pid)
    affected = []
    for pid in affected_pids:
        if pid not in portfolio_meta:
            continue
        how = []
        if direct_pct.get(pid, 0) > 0:
            how.append(f"{direct_pct[pid]}% of NAV in names directly in the news")
        fi = factor_by_pid.get(pid)
        if fi and (fi["tailwind_pct"] >= FACTOR_MATERIALITY_PCT or fi["headwind_pct"] >= FACTOR_MATERIALITY_PCT):
            if fi["tailwind_pct"] >= fi["headwind_pct"]:
                how.append(f"{fi['tailwind_pct']}% of NAV a tailwind from macro factors")
            else:
                how.append(f"{fi['headwind_pct']}% of NAV a headwind from macro factors")
        if not how:
            continue
        meta = portfolio_meta[pid]
        affected.append({
            "portfolio_id": pid,
            "portfolio_name": meta["portfolio_name"],
            "client_name": meta["client"]["name"],
            "persona": meta["client"]["persona"],
            "how_affected": "; ".join(how),
            "direct_pct": direct_pct.get(pid, 0.0),
            "factor": factor_by_pid.get(pid),
        })
    affected.sort(key=lambda a: a["direct_pct"], reverse=True)

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
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set on the server.")

    data = load_data()
    sector_secs = securities_in_sector(data, req.sector)
    if not sector_secs:
        raise HTTPException(status_code=404, detail=f"No securities found for sector '{req.sector}'.")

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
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set on the server.")

    data = load_data()
    portfolio = next((p for p in data["portfolios"] if p["portfolio_id"] == req.portfolio_id), None)
    if not portfolio or not portfolio.get("client"):
        raise HTTPException(status_code=404, detail=f"No client portfolio found for '{req.portfolio_id}'.")

    sector_secs = securities_in_sector(data, req.sector)
    if not sector_secs:
        raise HTTPException(status_code=404, detail=f"No securities found for sector '{req.sector}'.")

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

    points = generate_talking_points(
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
        "narrative_summary": extracted["narrative"],
        "citations": linked,
        "impact": impact_entry,
        "factor_impact": factor_entry,
        "points": points,
        "note": "Observational output only. No buy/sell/hold guidance is generated at any stage.",
    }
