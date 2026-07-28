"""Neo4j knowledge-graph product recommender.

Optional layer over the deterministic recommender in api.py. When NEO4J_URI and
NEO4J_PASSWORD are set (see .env.example), this queries a graph of clients,
products, asset classes, and preferences to recommend products the way a graph
does best: follow a client to their preferred asset classes, then to products
there they do not already hold and that fit their risk mandate, ranked by how
many similar clients hold each (collaborative filtering).

Everything here degrades gracefully. If the driver is missing, the graph is
unset, or the database is unreachable, callers get an empty list and the app
falls back to the rule-based suggestions. This module never imports api.py, so
there is no circular dependency: all the reasoning is baked into the graph at
build time (see build_graph.py).
"""
import os

_driver = None


def graph_enabled() -> bool:
    """True if the graph is configured (env present). Does not open a connection."""
    return bool(os.environ.get("NEO4J_URI") and os.environ.get("NEO4J_PASSWORD"))


def _get_driver():
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase  # lazy: importing this module must not require the driver
        _driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), os.environ["NEO4J_PASSWORD"]),
        )
    return _driver


def close():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def ping() -> bool:
    """Best-effort connectivity check for a /graph/status endpoint."""
    if not graph_enabled():
        return False
    try:
        _get_driver().verify_connectivity()
        return True
    except Exception:
        return False


# Preference + collaborative-filtering recommendation. Products in a class the
# client prefers, not already held, within their mandate risk ceiling, ranked by
# how many similar clients (same life stage or risk tier) hold each.
_RECOMMEND_CYPHER = """
MATCH (me:Client {portfolio_id: $pid})
MATCH (me)-[pref:PREFERS]->(ac:AssetClass)<-[:IN_CLASS]-(p:Product)
WHERE NOT (me)-[:HOLDS]->(p)
  AND p.band <= me.max_band
  AND p.asset_class <> 'Cash'
OPTIONAL MATCH (peer:Client)-[:HOLDS]->(p)
  WHERE peer.portfolio_id <> me.portfolio_id
    AND (peer.life_stage = me.life_stage OR peer.risk_tier = me.risk_tier)
WITH p, ac, pref.score AS pref_score, count(DISTINCT peer) AS peers
RETURN p.security_id AS security_id, p.name AS name, p.ticker AS ticker,
       p.sector AS sector, p.asset_class AS asset_class,
       p.instrument_type AS instrument_type, ac.name AS via_class,
       pref_score, peers
ORDER BY peers DESC, pref_score DESC, name
LIMIT $limit
"""


def recommend_products(portfolio_id: str, max_n: int = 4):
    """Graph-based product suggestions for one client. Returns a list of dicts
    (same shape as the rule-based recommender plus `peers`), or [] if the graph
    is unavailable for any reason."""
    if not graph_enabled():
        return []
    try:
        driver = _get_driver()
        with driver.session() as session:
            rows = session.run(_RECOMMEND_CYPHER, pid=portfolio_id, limit=max_n).data()
    except Exception:
        return []  # unreachable / query error: fall back silently

    out = []
    for r in rows:
        peers = r.get("peers") or 0
        via = r.get("via_class", "").lower()
        if peers > 0:
            why = f"In {via}, which suits this client, and held by {peers} client{'s' if peers != 1 else ''} with a similar profile."
        else:
            why = f"In {via}, which matches this client's preferences, and fits their mandate."
        out.append({
            "security_id": r["security_id"],
            "name": r["name"],
            "ticker": r["ticker"],
            "sector": r["sector"],
            "asset_class": r["asset_class"],
            "instrument_type": r["instrument_type"],
            "peers": peers,
            "rationale": why,
        })
    return out
