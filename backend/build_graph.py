"""Build the Neo4j knowledge graph from prism_data.json.

Run once after build_dataset.py, and again whenever the dataset changes:

    python build_graph.py

Requires NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD in the environment (.env).
Idempotent: it clears the PRISM nodes it owns and rebuilds them, so re-running is
safe. The graph it writes is what graph.py queries at request time.

Graph shape
-----------
  (:Client {portfolio_id, name, risk_tier, max_band, life_stage, ...})
  (:Product {security_id, name, ticker, asset_class, sector, band, ...})
  (:AssetClass {name})   (:Sector {name})

  (:Client)-[:HOLDS {weight}]->(:Product)
  (:Client)-[:PREFERS {score}]->(:AssetClass)     # from the preference profile
  (:Product)-[:IN_CLASS]->(:AssetClass)
  (:Product)-[:IN_SECTOR]->(:Sector)
"""
import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from neo4j import GraphDatabase

# Reuse the exact same suitability + preference logic the rest of the app uses,
# so the graph and the rule-based recommender agree on risk bands and affinities.
from api import _preference_profile, _vol_band_rank, _MANDATE_MAX_TIER

DATA_PATH = Path(__file__).with_name("prism_data.json")

CONSTRAINTS = [
    "CREATE CONSTRAINT client_pid IF NOT EXISTS FOR (c:Client) REQUIRE c.portfolio_id IS UNIQUE",
    "CREATE CONSTRAINT product_sid IF NOT EXISTS FOR (p:Product) REQUIRE p.security_id IS UNIQUE",
    "CREATE CONSTRAINT class_name IF NOT EXISTS FOR (a:AssetClass) REQUIRE a.name IS UNIQUE",
    "CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE",
]


def _client_props(portfolio, risk):
    c = portfolio["client"]
    psy = c.get("psychographics", {}) or {}
    mandate = (c.get("risk_mandate") or "").strip().lower()
    return {
        "portfolio_id": portfolio["portfolio_id"],
        "name": c["name"],
        "risk_mandate": c.get("risk_mandate"),
        "risk_tier": risk.get("risk_tier"),
        "max_band": _MANDATE_MAX_TIER.get(mandate, 2),
        "life_stage": psy.get("life_stage"),
        "time_horizon": psy.get("time_horizon"),
        "loss_aversion": psy.get("loss_aversion"),
        "primary_goal": psy.get("primary_goal"),
    }


def build(session, data):
    # products
    for s in data["securities"]:
        session.run(
            """
            MERGE (p:Product {security_id: $sid})
            SET p.name=$name, p.ticker=$ticker, p.asset_class=$ac,
                p.sector=$sector, p.instrument_type=$itype, p.vol=$vol, p.band=$band
            MERGE (ac:AssetClass {name: $ac})
            MERGE (sec:Sector {name: $sector})
            MERGE (p)-[:IN_CLASS]->(ac)
            MERGE (p)-[:IN_SECTOR]->(sec)
            """,
            sid=s["security_id"], name=s["name"], ticker=s["primary_ticker"],
            ac=s["asset_class"], sector=s["sector"], itype=s["instrument_type"],
            vol=s.get("vol"), band=_vol_band_rank(s.get("vol")),
        )

    risk = data.get("risk", {})
    holdings_by_pid = {}
    for h in data["holdings"]:
        holdings_by_pid.setdefault(h["portfolio_id"], []).append(h)

    # clients + holdings + preferences
    for p in data["portfolios"]:
        if p.get("is_reference") or not p.get("client"):
            continue
        pid = p["portfolio_id"]
        session.run(
            "MERGE (c:Client {portfolio_id: $portfolio_id}) SET c += $props",
            portfolio_id=pid, props=_client_props(p, risk.get(pid, {})),
        )
        for h in holdings_by_pid.get(pid, []):
            session.run(
                """
                MATCH (c:Client {portfolio_id: $pid}), (p:Product {security_id: $sid})
                MERGE (c)-[r:HOLDS]->(p) SET r.weight = $w
                """,
                pid=pid, sid=h["security_id"], w=round(h["weight"], 4),
            )
        # preference edges from the shared preference profile (affinity > 0)
        aff, _reasons = _preference_profile(p["client"])
        for cls, score in aff.items():
            if score > 0:
                session.run(
                    """
                    MATCH (c:Client {portfolio_id: $pid})
                    MERGE (ac:AssetClass {name: $cls})
                    MERGE (c)-[r:PREFERS]->(ac) SET r.score = $score
                    """,
                    pid=pid, cls=cls, score=round(score, 2),
                )


def main():
    uri = os.environ.get("NEO4J_URI")
    pwd = os.environ.get("NEO4J_PASSWORD")
    if not uri or not pwd:
        raise SystemExit("NEO4J_URI and NEO4J_PASSWORD must be set (see .env.example).")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    driver = GraphDatabase.driver(uri, auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), pwd))
    try:
        driver.verify_connectivity()
        with driver.session() as session:
            for c in CONSTRAINTS:
                session.run(c)
            # clear the graph we own, then rebuild
            session.run("MATCH (n) WHERE n:Client OR n:Product OR n:AssetClass OR n:Sector DETACH DELETE n")
            build(session, data)
            counts = session.run(
                "MATCH (c:Client) WITH count(c) AS clients "
                "MATCH (p:Product) WITH clients, count(p) AS products "
                "MATCH (:Client)-[h:HOLDS]->() WITH clients, products, count(h) AS holds "
                "MATCH (:Client)-[pr:PREFERS]->() RETURN clients, products, holds, count(pr) AS prefers"
            ).single()
        print(f"Graph built: {counts['clients']} clients, {counts['products']} products, "
              f"{counts['holds']} holdings, {counts['prefers']} preference edges.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
