"""
PRISM insight lens — first working slice of the no-scraping market-insight pipeline.

What this proves end to end:
  1. Fetch market content via Claude's built-in, hosted web_search tool (not a
     scraper — Anthropic runs the fetch under its own terms and returns
     citations natively). One "lens" = one focused sector/topic search.
  2. Every finding keeps its source url, title, and the exact cited snippet
     (Anthropic's citation format), so nothing is presented without a source.
  3. A lightweight entity linker matches each citation's text against our
     securities master (tickers, aliases, company names).
  4. A deterministic roll-up (plain arithmetic, no LLM) computes what % of
     each portfolio's NAV is touched by the matched securities.
  5. Claude is explicitly instructed NOT to give buy/sell/hold advice — only
     to report what is happening and what it touches. This is enforced in
     the system prompt, not left to hope.

Run:
  pip install anthropic python-dotenv
  # then set your key one of two ways:
  #   PowerShell (persists across new terminals): setx ANTHROPIC_API_KEY "sk-ant-..."
  #   PowerShell (current session only):          $env:ANTHROPIC_API_KEY = "sk-ant-..."
  #   or: copy .env.example to .env and paste the key there
  python insight_lens.py --sector "Information Technology"
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    load_dotenv()  # picks up a local .env if present; harmless if it's not
except ImportError:
    pass

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic python-dotenv")
    sys.exit(1)

DATA_PATH = os.path.join(os.path.dirname(__file__), "prism_data.json")
# Tiered models to keep latency down without sacrificing the parts that need
# judgment. Search + narration go to Sonnet (fast, strong); pure classification
# goes to Haiku (fastest). None of these compute exposure numbers; that is all
# deterministic Python.
MODEL = "claude-sonnet-5"          # default / narration
SEARCH_MODEL = "claude-sonnet-5"   # web-search grounded research
CLASSIFY_MODEL = "claude-haiku-4-5-20251001"  # factor classification
MAX_SEARCHES = 4

NO_ADVICE_SYSTEM_PROMPT = """You are a market-research assistant for a portfolio management desk.

Your job is strictly observational: research recent, real developments on the given
sector or companies using web search, and report what is happening.

Hard rules:
- Never say what someone should buy, sell, hold, or how to change a portfolio.
- Never use words like "recommend," "should invest," "opportunity to buy," or similar.
- State facts and their source. If something is uncertain or contested, say so.
- Write 3 to 6 short, distinct findings. Each finding should be a separate real
  development (not the same story rephrased), grounded in a search result.
- Prefer the most recent material you can find.
- Never use em dashes. Use commas, periods, or "to" for ranges instead.

You are not a financial advisor and this is not investment advice. You are a research
grounding layer that a separate, deterministic system will use to compute portfolio
exposure — that system decides impact, not you."""


def load_data():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def securities_in_sector(data, sector):
    return [s for s in data["securities"] if s.get("sector", "").lower() == sector.lower()]


def build_query_context(securities):
    names = [s["name"] for s in securities if s["instrument_type"] == "Single Stock"][:8]
    return names


def run_search(sector, company_names):
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    company_list = ", ".join(company_names) if company_names else "no specific names on file"
    user_prompt = (
        f"Research recent developments (last 1 to 2 weeks if possible) in the INDIAN "
        f"{sector} market specifically, with particular attention to any of these India-listed "
        f"companies if relevant: {company_list}. "
        f"Focus on India: Indian companies, the RBI, Indian government bonds and G-secs, the NSE/BSE, "
        f"SEBI, and the rupee. If you cite a global development (Fed, US Treasuries, oil, global rates), "
        f"only do so through its read-through to Indian markets, and never let US or global-only stories "
        f"dominate the findings. Cover a genuinely varied set of angles and outlets."
    )

    response = client.messages.create(
        model=SEARCH_MODEL,
        max_tokens=2048,
        system=NO_ADVICE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_SEARCHES}],
    )
    return response


NEWS_FEED_CATEGORIES = {
    "India Markets": (
        "Research the most significant Indian stock market and macroeconomic developments from the "
        "last few days: RBI policy, major listed companies' news, sector-moving events, FII/DII flows, "
        "and broad index-level developments."
    ),
    "Global Markets": (
        "Research the most significant global market-moving developments from the last few days: "
        "major economies, central bank policy (Fed, ECB, BoJ, etc.), and geopolitical events with real "
        "market impact worldwide, especially anything with a read-through to Indian markets."
    ),
    "Commodities & Energy": (
        "Research recent commodity and energy market developments from the last few days: crude oil, "
        "natural gas, gold, industrial metals, and agricultural commodities, with attention to price "
        "moves and supply/demand drivers that affect Indian companies and inflation."
    ),
    "Currency & Rates": (
        "Research recent developments in currencies and interest rates from the last few days: the "
        "Indian rupee versus the dollar, RBI and US Federal Reserve rate decisions and commentary, "
        "bond yields, and anything shifting the rate or currency outlook relevant to Indian portfolios."
    ),
    "Corporate Earnings": (
        "Research recent quarterly earnings and major corporate developments from large Indian listed "
        "companies in the last few days: results, guidance changes, management commentary, deals, and "
        "capital actions that move individual stocks."
    ),
    "Policy & Regulation": (
        "Research recent Indian government policy and regulatory developments from the last few days "
        "that are relevant to markets, business, or the economy: budget and tax measures, sector "
        "policies, SEBI and RBI regulation, trade policy, and legislation with business consequence. "
        "Skip pure politics with no economic angle."
    ),
    "India Startups": (
        "Research recent developments in the Indian startup and technology ecosystem from the last few "
        "days: funding rounds, IPOs, acquisitions, new-age tech and consumer-internet companies, and "
        "regulatory news specifically affecting startups."
    ),
}


def run_news_feed(category):
    """Same mechanism as run_search (Claude's hosted web_search, cited,
    no-advice), but keyed to a broad news category rather than a GICS sector
    + company list. Powers the general-awareness news feed, separate from
    the portfolio-specific sector lens."""
    if category not in NEWS_FEED_CATEGORIES:
        raise ValueError(f"Unknown news category: {category}")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=SEARCH_MODEL,
        max_tokens=2048,
        system=NO_ADVICE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": NEWS_FEED_CATEGORIES[category]}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_SEARCHES}],
    )
    return response


def extract_citations_and_narrative(response):
    """Pull queries used, distinct source citations, and the narrative text
    straight out of the response content blocks (per Anthropic's documented
    web_search_tool_result / citations shape), no reliance on Claude
    self-reporting sources in prose."""
    queries = []
    citations = {}  # keyed by url, deduped
    narrative_parts = []

    for block in response.content:
        btype = getattr(block, "type", None)
        if btype == "server_tool_use" and getattr(block, "name", None) == "web_search":
            queries.append(block.input.get("query", ""))
        elif btype == "text":
            narrative_parts.append(block.text)
            for c in (getattr(block, "citations", None) or []):
                if getattr(c, "type", None) == "web_search_result_location":
                    citations[c.url] = {
                        "url": c.url,
                        "title": c.title,
                        "cited_text": c.cited_text,
                    }

    return {
        "queries_used": queries,
        "citations": list(citations.values()),
        "narrative": "".join(narrative_parts).strip(),
    }


def link_citations_to_securities(citations, all_securities):
    """Lightweight entity linker for this first slice: match each citation's
    title + cited_text against ticker / name / aliases using word-boundary
    regex (not raw substring — a short alias like "RIL" is a substring of the
    ordinary word "primarily", which produced real false positives). Confidence
    is still coarse on purpose — this is the seam where the fuller hybrid
    linker (gazetteer + LLM disambiguation) from the LLD plugs in later."""
    linked = []
    for c in citations:
        haystack = f"{c['title']} {c['cited_text']}".lower()
        matches = []
        for s in all_securities:
            needles = [s["name"], s["primary_ticker"]] + s.get("aliases", [])
            for needle in needles:
                if needle and len(needle) > 2 and re.search(
                    rf"\b{re.escape(needle.lower())}\b", haystack
                ):
                    matches.append(s["security_id"])
                    break
        linked.append({**c, "linked_security_ids": sorted(set(matches))})
    return linked


def compute_portfolio_impact(data, linked_citations):
    """Deterministic roll-up: for every security any citation touched, find
    every portfolio holding it and sum the NAV weight affected. Plain
    arithmetic — no LLM involved in this step, matching the design principle
    that impact math must be exact and auditable, not guessed."""
    touched_security_ids = set()
    for c in linked_citations:
        touched_security_ids.update(c["linked_security_ids"])

    if not touched_security_ids:
        return []

    port_by_id = {p["portfolio_id"]: p for p in data["portfolios"]}
    impact = defaultdict(lambda: {"pct_nav_touched": 0.0, "matched_holdings": []})

    for h in data["holdings"]:
        if h["security_id"] in touched_security_ids:
            impact[h["portfolio_id"]]["pct_nav_touched"] += h["weight"] * 100
            impact[h["portfolio_id"]]["matched_holdings"].append(
                {"security_id": h["security_id"], "weight_pct": round(h["weight"] * 100, 1)}
            )

    results = []
    for pid, v in impact.items():
        p = port_by_id.get(pid, {})
        results.append({
            "portfolio_id": pid,
            "portfolio_name": p.get("name", pid),
            "risk_tier": p.get("risk_driver", ""),
            "pct_nav_touched": round(v["pct_nav_touched"], 1),
            "matched_holdings": v["matched_holdings"],
        })
    results.sort(key=lambda r: r["pct_nav_touched"], reverse=True)
    return results


FACTOR_KEYS = ["gold", "oil", "interest_rates_india", "interest_rates_us", "usd_inr"]

FACTOR_CLASSIFIER_SYSTEM_PROMPT = """You classify macro/commodity factor events in a market
research narrative. Use ONLY these factor keys:
- gold
- oil
- interest_rates_india (RBI monetary policy / India rates specifically)
- interest_rates_us (US Federal Reserve policy specifically — NOT the same factor as India rates)
- usd_inr (the rupee/dollar exchange rate)

Rules:
- Only report a factor if the narrative gives it a real, substantive directional move or stance.
  Do not report a factor for a passing, non-directional mention.
- Give the direction ("up", "down", or "mixed") based on the SUBSTANTIVE meaning of the news, not
  surface keywords. Example: "the Fed signaled fewer cuts than expected" means rates are more
  likely to stay HIGHER than markets hoped — that is direction "up" (hawkish), not "down", even
  though the word "cut" appears in the sentence.
- Keep interest_rates_india and interest_rates_us strictly separate. A Federal Reserve story is
  interest_rates_us, never interest_rates_india, even if the narrative also discusses India.
- Quote the exact supporting sentence/clause from the narrative in "snippet".
- If no factors are substantively discussed, return an empty list."""

FACTOR_CLASSIFIER_TOOL = {
    "name": "record_factor_signals",
    "description": "Record each distinct macro/commodity factor event found in the narrative, with its real direction.",
    "input_schema": {
        "type": "object",
        "properties": {
            "signals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "factor": {"type": "string", "enum": FACTOR_KEYS},
                        "direction": {"type": "string", "enum": ["up", "down", "mixed"]},
                        "snippet": {"type": "string"},
                    },
                    "required": ["factor", "direction", "snippet"],
                },
            }
        },
        "required": ["signals"],
    },
}


def detect_factor_signals(narrative):
    """Stand-in for the LLD's Event classifier + direction engine (§2, §7): an
    actual LLM classification pass, replacing an earlier keyword/sign-word
    version that got real cases wrong — e.g. reading "fewer rate cuts than
    expected" as a rate-cut-down signal (it means the opposite), and
    conflating US Federal Reserve news with India's own RBI policy. The LLM
    only classifies; compute_factor_impact still does the deterministic
    roll-up math, keeping the same division of labor as the rest of PRISM."""
    if not narrative.strip():
        return []

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=CLASSIFY_MODEL,
        max_tokens=1024,
        system=FACTOR_CLASSIFIER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Narrative:\n\n{narrative}"}],
        tools=[FACTOR_CLASSIFIER_TOOL],
        tool_choice={"type": "tool", "name": "record_factor_signals"},
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_factor_signals":
            return block.input.get("signals", [])
    return []


def compute_factor_impact(data, factor_signals):
    """For each detected factor signal, find every holding explicitly tagged
    with a sensitivity to that factor (a hand-tagged stand-in for the LLD's
    full sensitivity matrix over beta/sector/credit_quality) and roll up
    tailwind/headwind exposure per portfolio. Deterministic — no LLM involved,
    matching the same division of labor as compute_portfolio_impact."""
    if not factor_signals:
        return []

    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    port_by_id = {p["portfolio_id"]: p for p in data["portfolios"]}
    impact = defaultdict(lambda: {"tailwind_pct": 0.0, "headwind_pct": 0.0, "matched": []})

    for h in data["holdings"]:
        s = sec_by_id.get(h["security_id"])
        if not s:
            continue
        sensitivities = s.get("factor_sensitivities", {})
        for signal in factor_signals:
            sensitivity = sensitivities.get(signal["factor"])
            if not sensitivity or signal["direction"] not in ("up", "down"):
                continue
            if sensitivity == "same_direction":
                effect = "tailwind" if signal["direction"] == "up" else "headwind"
            elif sensitivity == "positive":
                effect = "tailwind" if signal["direction"] == "up" else "headwind"
            elif sensitivity == "negative":
                effect = "headwind" if signal["direction"] == "up" else "tailwind"
            else:
                continue
            impact[h["portfolio_id"]][f"{effect}_pct"] += h["weight"] * 100
            impact[h["portfolio_id"]]["matched"].append({
                "security_id": h["security_id"], "factor": signal["factor"],
                "effect": effect, "weight_pct": round(h["weight"] * 100, 1),
            })

    results = []
    for pid, v in impact.items():
        p = port_by_id.get(pid, {})
        results.append({
            "portfolio_id": pid,
            "portfolio_name": p.get("name", pid),
            "tailwind_pct": round(v["tailwind_pct"], 1),
            "headwind_pct": round(v["headwind_pct"], 1),
            "matched": v["matched"],
        })
    results.sort(key=lambda r: r["tailwind_pct"] + r["headwind_pct"], reverse=True)
    return results


CONTRADICTION_MATERIALITY_PCT = 10.0


def detect_cross_desk_contradictions(data, factor_impact, min_material_pct=CONTRADICTION_MATERIALITY_PCT):
    """ADVANCED.md #4 — cross-desk contradiction flagging, the recommended
    first advanced feature: reuses the factor_impact breakdown already
    computed above (no new data, no new model) to flag when two funds hold
    materially opposing exposure to the SAME factor event — one tailwind, one
    headwind. Pure oversight: reports the opposing exposure, gives neither
    desk any buy/sell/hold guidance. Regroups by individual factor first,
    since comparing one fund's oil exposure against another fund's unrelated
    gold exposure would be meaningless."""
    by_factor = defaultdict(lambda: defaultdict(lambda: {"tailwind_pct": 0.0, "headwind_pct": 0.0}))
    for p in factor_impact:
        for m in p["matched"]:
            by_factor[m["factor"]][p["portfolio_id"]][f"{m['effect']}_pct"] += m["weight_pct"]

    port_by_id = {p["portfolio_id"]: p for p in data["portfolios"] if not p.get("is_reference")}
    contradictions = []
    for factor, per_portfolio in by_factor.items():
        tailwind_funds = [(pid, v["tailwind_pct"]) for pid, v in per_portfolio.items()
                          if v["tailwind_pct"] >= min_material_pct and pid in port_by_id]
        headwind_funds = [(pid, v["headwind_pct"]) for pid, v in per_portfolio.items()
                          if v["headwind_pct"] >= min_material_pct and pid in port_by_id]
        for t_pid, t_pct in tailwind_funds:
            for h_pid, h_pct in headwind_funds:
                contradictions.append({
                    "factor": factor,
                    "tailwind_fund": port_by_id[t_pid]["name"],
                    "tailwind_pct": round(t_pct, 1),
                    "headwind_fund": port_by_id[h_pid]["name"],
                    "headwind_pct": round(h_pct, 1),
                })
    return contradictions


SEVERITY_BANDS = {"mild": 0.05, "moderate": 0.15, "severe": 0.30}


def compute_scenario_impact(data, factor_signals):
    """ADVANCED.md #2 — scenario / counterfactual roll-up. For each detected
    factor signal with a clear direction, simulates 'what if this factor move
    continues/escalates' across three severity bands (assumed price moves of
    5% / 15% / 30%), reusing the same weight-sum arithmetic as the rest of the
    roll-up engine. Every number is a labeled ASSUMPTION applied to a holding's
    weight — never a forecast, never a probability, never 'likely'."""
    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    port_by_id = {p["portfolio_id"]: p for p in data["portfolios"]}
    signal_by_factor = {s["factor"]: s for s in factor_signals if s["direction"] in ("up", "down")}
    if not signal_by_factor:
        return []

    scenario = defaultdict(lambda: defaultdict(float))
    for h in data["holdings"]:
        s = sec_by_id.get(h["security_id"])
        if not s:
            continue
        for factor, sensitivity in s.get("factor_sensitivities", {}).items():
            signal = signal_by_factor.get(factor)
            if not signal or sensitivity not in ("same_direction", "positive", "negative"):
                continue
            if sensitivity == "negative":
                sign = -1 if signal["direction"] == "up" else 1
            else:
                sign = 1 if signal["direction"] == "up" else -1
            for band, move in SEVERITY_BANDS.items():
                scenario[h["portfolio_id"]][band] += sign * move * h["weight"] * 100

    results = []
    for pid, bands in scenario.items():
        p = port_by_id.get(pid, {})
        results.append({
            "portfolio_id": pid,
            "portfolio_name": p.get("name", pid),
            "bands": {band: round(v, 2) for band, v in bands.items()},
        })
    results.sort(key=lambda r: abs(r["bands"].get("severe", 0)), reverse=True)
    return results


REFERENCE_PORTFOLIO_ID = "pf_reference_balanced"
MATERIALITY_FLOOR_PCT = 5.0
MULTIPLE_CAP = 10.0


def attach_reference_comparison(impact_list, value_key="pct_nav_touched"):
    """Lens 2 from the LLD (§12) — the centerpiece 'you vs. a normal book'
    comparison. Compares each real fund's exposure against the fixed reference
    60/40 book, computed by the exact same deterministic engine (same
    function, just also given the reference portfolio's holdings). Absolute
    exposure is primary; the multiple is secondary, capped at "10x+" rather
    than a false-precise number, and dropped entirely below a 5% materiality
    floor or when the reference has zero exposure — a multiple against near-
    zero is noise, not signal."""
    ref_value = next((r[value_key] for r in impact_list if r["portfolio_id"] == REFERENCE_PORTFOLIO_ID), 0.0)
    results = []
    for r in impact_list:
        if r["portfolio_id"] == REFERENCE_PORTFOLIO_ID:
            continue  # the reference book is the ruler, not something measured against itself
        entry = dict(r)
        entry["vs_reference_pct"] = ref_value
        own_value = r[value_key]
        if own_value < MATERIALITY_FLOOR_PCT or ref_value == 0:
            entry["vs_reference_multiple"] = None
        else:
            multiple = own_value / ref_value
            entry["vs_reference_multiple"] = f"{MULTIPLE_CAP:.0f}x+" if multiple > MULTIPLE_CAP else round(multiple, 1)
        results.append(entry)
    return results


TALKING_POINTS_SYSTEM_PROMPT = """You help a relationship manager prepare for a client conversation.

You will be given: the client's persona, their portfolio's mandate, a piece of grounded
market research, and a set of ALREADY-COMPUTED numbers (NAV exposure, comparison to a
reference book, factor tailwind/headwind). Produce two things:

1. "market_insights": 3 to 4 short bullets summarizing what is happening in the market that
   matters to THIS book. Each bullet is ONE plain sentence, max 20 words, leading with the
   concrete fact. These replace any long prose, so they must stand alone and be scannable.
2. "points": 3 to 4 talking points the manager could say on a call with this specific client.

Hard rules:
- BE SHORT. Every bullet and point is ONE sentence, max 20 to 25 words. No preamble, no filler.
- LEAD WITH THE NUMBER OR FACT, then the plain-English read for this client.
- Plain text only. NEVER use markdown, asterisks, bold, or bullet characters. Just sentences.
- Never say what the client should buy, sell, hold, or how to change their portfolio.
- Never use words like "recommend," "should invest," "opportunity," or similar.
- Use ONLY the numbers you are given. Do not invent or estimate any number yourself.
- Tailor the tone to the persona (anxious client gets reassurance, expert gets the nuance).
- If the data shows no material impact, say exactly that in one short sentence.
- Never use em dashes. Use commas, periods, or "to" for ranges instead.
- You are not a financial advisor and this is not investment advice."""

TALKING_POINTS_TOOL = {
    "name": "record_talking_points",
    "description": "Record scannable market-insight bullets plus natural talking points for a client call.",
    "input_schema": {
        "type": "object",
        "properties": {
            "market_insights": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 4,
            },
            "points": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 5,
            },
        },
        "required": ["market_insights", "points"],
    },
}


def generate_talking_points(client, portfolio_name, mandate, sector, narrative, impact_entry, factor_entry):
    """LLM narrates, never computes: takes the client persona plus numbers
    already produced by compute_portfolio_impact / attach_reference_comparison
    / compute_factor_impact and phrases them as spoken talking points. No new
    figures are generated here — only wording."""
    facts = [f"Sector researched: {sector}", f"Portfolio: {portfolio_name}", f"Mandate: {mandate}"]
    if impact_entry:
        facts.append(
            f"NAV exposure: {impact_entry['pct_nav_touched']}% of this portfolio is touched by "
            f"today's research, versus {impact_entry['vs_reference_pct']}% for a normal reference book"
            + (f" ({impact_entry['vs_reference_multiple']}x)." if impact_entry.get("vs_reference_multiple") else ".")
        )
    else:
        facts.append("NAV exposure: no held security in this portfolio was directly named in today's citations.")
    if factor_entry:
        facts.append(
            f"Factor exposure: {factor_entry['tailwind_pct']}% tailwind, {factor_entry['headwind_pct']}% "
            f"headwind from macro/commodity factors detected today."
        )

    user_prompt = (
        f"Client persona: {client['name']}, {client['age']}, {client['occupation']}. {client['persona']}\n"
        f"Risk mandate: {client['risk_mandate']}\n\n"
        f"Facts (already computed, do not alter):\n- " + "\n- ".join(facts) + "\n\n"
        f"Grounded research narrative:\n{narrative}"
    )

    api_client = anthropic.Anthropic()
    response = api_client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=TALKING_POINTS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        tools=[TALKING_POINTS_TOOL],
        tool_choice={"type": "tool", "name": "record_talking_points"},
    )
    def _clean(items):
        # belt-and-suspenders: strip any stray markdown the model slips in
        out = []
        for s in items or []:
            s = s.replace("**", "").replace("*", "").replace("—", ", ").strip()
            s = s.lstrip("-•").strip()
            if s:
                out.append(s)
        return out

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_talking_points":
            return {
                "market_insights": _clean(block.input.get("market_insights", [])),
                "points": _clean(block.input.get("points", [])),
            }
    return {"market_insights": [], "points": []}


NEWS_BRIEFING_SYSTEM_PROMPT = """You brief a relationship manager on what today's news means
for their clients. The manager is busy and cannot read a wall of text.

You are given a category of news, a grounded research narrative, and a list of the manager's
clients that today's news actually touches (each with a persona and how they are affected,
already computed). Produce:
1. A single-sentence "tldr" of the most important thing in this news for the book. Plain,
   concrete, no fluff.
2. "key_points": 4 to 6 clear, scannable bullets covering the distinct developments in the
   news. Each bullet is ONE sentence, max 22 words, and MUST start with the single most
   concrete fact (a number, a name, a decision). No paragraphs. These replace the raw text,
   so they must stand on their own.
3. For EACH affected client given, one short talking point the manager could say to that
   specific client, tailored to their persona and how they are affected.

Hard rules:
- BE SHORT everywhere. The tldr is ONE sentence. Each key_point and talking point is ONE
  sentence, max 22 to 25 words.
- LEAD WITH THE CONCRETE FACT (number, name, decision), then the plain read.
- Never say what any client should buy, sell, hold, or how to change a portfolio.
- Never use words like "recommend," "should invest," "opportunity," or similar.
- Use ONLY the facts and computed impact you are given. Do not invent numbers.
- Tailor client talking points to the persona but keep them tight. No filler, no preamble.
- Never use em dashes. Use commas, periods, or "to" for ranges instead.
- You are not a financial advisor and this is not investment advice."""


def _news_briefing_tool(portfolio_ids):
    return {
        "name": "record_briefing",
        "description": "Record a TL;DR, scannable key-point bullets, and one talking point per affected client.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tldr": {"type": "string"},
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 3,
                    "maxItems": 6,
                },
                "client_points": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "portfolio_id": {"type": "string", "enum": portfolio_ids},
                            "talking_point": {"type": "string"},
                        },
                        "required": ["portfolio_id", "talking_point"],
                    },
                },
            },
            "required": ["tldr", "key_points", "client_points"],
        },
    }


def generate_news_briefing(category, narrative, affected_clients):
    """One batched LLM call: turns a news narrative plus the already-computed
    list of affected clients into a one-line TL;DR, scannable key-point bullets,
    and a per-client talking point. LLM only phrases; all impact numbers were
    computed deterministically upstream. Returns
    {"tldr": str, "key_points": [str], "points": {portfolio_id: talking_point}}."""
    if not narrative.strip():
        return {"tldr": "", "key_points": [], "points": {}}

    if affected_clients:
        client_lines = "\n".join(
            f"- portfolio_id={c['portfolio_id']} | {c['client_name']} ({c['persona']}) | "
            f"affected: {c['how_affected']}"
            for c in affected_clients
        )
        portfolio_ids = [c["portfolio_id"] for c in affected_clients]
    else:
        client_lines = "(No client is materially affected by this news today.)"
        portfolio_ids = ["__none__"]

    user_prompt = (
        f"News category: {category}\n\n"
        f"Grounded research narrative:\n{narrative}\n\n"
        f"Clients affected by this news (personas and computed impact):\n{client_lines}"
    )

    api_client = anthropic.Anthropic()
    response = api_client.messages.create(
        model=MODEL,
        max_tokens=1400,
        system=NEWS_BRIEFING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        tools=[_news_briefing_tool(portfolio_ids)],
        tool_choice={"type": "tool", "name": "record_briefing"},
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_briefing":
            data = block.input
            points = {
                cp["portfolio_id"]: cp["talking_point"]
                for cp in data.get("client_points", [])
                if cp["portfolio_id"] != "__none__"
            }
            return {"tldr": data.get("tldr", ""), "key_points": data.get("key_points", []), "points": points}
    return {"tldr": "", "key_points": [], "points": {}}


def main():
    parser = argparse.ArgumentParser(description="Run one PRISM insight lens end to end.")
    parser.add_argument("--sector", default="Information Technology",
                         help="GICS sector to research, e.g. 'Energy', 'Health Care', 'Financials'")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. See the docstring at the top of this file for how to set it.")
        sys.exit(1)

    data = load_data()
    sector_secs = securities_in_sector(data, args.sector)
    if not sector_secs:
        print(f"No securities found for sector '{args.sector}'. Check prism_data.json for valid sector names.")
        sys.exit(1)

    company_names = build_query_context(sector_secs)
    print(f"Lens: {args.sector}  |  watching: {', '.join(company_names) or '(fund-level exposure only)'}")
    print("Calling Claude with the web_search tool...\n")

    response = run_search(args.sector, company_names)
    extracted = extract_citations_and_narrative(response)
    linked = link_citations_to_securities(extracted["citations"], data["securities"])
    portfolio_impact = compute_portfolio_impact(data, linked)
    portfolio_impact_vs_ref = attach_reference_comparison(portfolio_impact)
    factor_signals = detect_factor_signals(extracted["narrative"])
    factor_impact = compute_factor_impact(data, factor_signals)
    cross_desk_contradictions = detect_cross_desk_contradictions(data, factor_impact)
    scenario_impact = compute_scenario_impact(data, factor_signals)

    record = {
        "lens": args.sector,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queries_used": extracted["queries_used"],
        "narrative": extracted["narrative"],
        "citations": linked,
        "portfolio_impact": portfolio_impact_vs_ref,
        "factor_signals": factor_signals,
        "factor_impact": factor_impact,
        "cross_desk_contradictions": cross_desk_contradictions,
        "scenario_impact": scenario_impact,
        "note": "Observational output only. No buy/sell/hold guidance is generated at any stage.",
    }

    out_path = os.path.join(os.path.dirname(__file__), f"insight_{args.sector.replace(' ', '_').lower()}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    print("=" * 70)
    print("NARRATIVE (Claude, cited, no recommendations)")
    print("=" * 70)
    print(extracted["narrative"] or "(no narrative text returned)")
    print()
    print("=" * 70)
    print(f"CITATIONS ({len(linked)})")
    print("=" * 70)
    for c in linked:
        tag = f"  -> linked to: {', '.join(c['linked_security_ids'])}" if c["linked_security_ids"] else "  (no security match)"
        print(f"- {c['title']}\n  {c['url']}{tag}")
    print()
    print("=" * 70)
    print("PORTFOLIO IMPACT vs. REFERENCE 60/40 BOOK (deterministic, not LLM-generated)")
    print("=" * 70)
    if not portfolio_impact_vs_ref:
        print("No held securities were matched in this run's citations.")
    for p in portfolio_impact_vs_ref:
        if p["vs_reference_multiple"] is None:
            comp = f"vs. reference book's {p['vs_reference_pct']}% (below materiality floor for a multiple)"
        else:
            mult = p["vs_reference_multiple"]
            mult_str = mult if isinstance(mult, str) else f"{mult}x"
            comp = f"vs. reference book's {p['vs_reference_pct']}% -> you are {mult_str} a normal book"
        print(f"- {p['portfolio_name']}: {p['pct_nav_touched']}% of NAV touched "
              f"via {len(p['matched_holdings'])} holding(s)  ({comp})")

    print()
    print("=" * 70)
    print("FACTOR SIGNALS (macro/commodity events, not tied to a named security)")
    print("=" * 70)
    if not factor_signals:
        print("No macro/commodity factor events detected in this run's narrative.")
    mapped_factors = {m["factor"] for p in factor_impact for m in p["matched"]}
    for fs in factor_signals:
        note = "" if fs["factor"] in mapped_factors else "  [no India holding is tagged for this factor yet]"
        print(f"- {fs['factor']}: {fs['direction']}{note}\n  \"{fs['snippet']}\"")

    print()
    print("=" * 70)
    print("FACTOR IMPACT (deterministic, tag-based — not entity-linked)")
    print("=" * 70)
    if not factor_impact:
        print("No portfolio holdings are tagged as sensitive to the detected factors.")
    for p in factor_impact:
        print(f"- {p['portfolio_name']}: tailwind {p['tailwind_pct']}% of NAV, "
              f"headwind {p['headwind_pct']}% of NAV")

    print()
    print("=" * 70)
    print("CROSS-DESK CONTRADICTIONS (ADVANCED.md #4 -- oversight, not advice)")
    print("=" * 70)
    if not cross_desk_contradictions:
        print("No two funds show materially opposing exposure to the same factor in this run.")
    for c in cross_desk_contradictions:
        print(f"- [{c['factor']}] {c['tailwind_fund']} (tailwind {c['tailwind_pct']}%) "
              f"vs. {c['headwind_fund']} (headwind {c['headwind_pct']}%)")

    print()
    print("=" * 70)
    print("SCENARIO / WHAT-IF ROLL-UP (ADVANCED.md #2 -- labeled assumptions, not a forecast)")
    print("=" * 70)
    if not scenario_impact:
        print("No directional factor signal to run a what-if scenario on in this run.")
    for s in scenario_impact:
        b = s["bands"]
        print(f"- {s['portfolio_name']}: if this factor move continues -- "
              f"mild {b['mild']:+.2f}%, moderate {b['moderate']:+.2f}%, severe {b['severe']:+.2f}% of NAV")

    print(f"\nFull structured record written to: {out_path}")


if __name__ == "__main__":
    main()
