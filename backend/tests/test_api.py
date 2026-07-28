"""
Smoke tests for the FastAPI layer (api.py). Only exercises the endpoints that
don't require a live LLM call (/sectors, /portfolios, /clients, /me,
/news/categories) plus validation paths on the LLM-backed endpoints —
/lens/run, /news/feed, and /talking-points' actual research/narration calls
are covered by the manual live runs already done directly against
insight_lens.py, since mocking a full Anthropic response would test the
mock, not the app. No auth — this is an open, single-PM demo API.
"""

import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def test_me_returns_manager_name():
    response = client.get("/me")
    assert response.status_code == 200
    assert response.json()["manager_name"]


def test_sectors_endpoint_returns_known_sector():
    response = client.get("/sectors")
    assert response.status_code == 200
    sectors = response.json()
    assert "Financials" in sectors
    assert "Information Technology" in sectors


def test_sectors_endpoint_excludes_nothing_odd():
    response = client.get("/sectors")
    sectors = response.json()
    assert sectors == sorted(sectors)  # returned sorted
    assert len(sectors) == len(set(sectors))  # no duplicates


def test_portfolios_endpoint_excludes_reference_book():
    response = client.get("/portfolios")
    assert response.status_code == 200
    portfolios = response.json()
    names = [p["name"] for p in portfolios]
    assert "Reference Balanced 60/40 Fund" not in names


def test_portfolios_endpoint_includes_manager_personas():
    response = client.get("/portfolios")
    portfolios = response.json()
    assert len(portfolios) == 12
    assert all(p["manager_name"] for p in portfolios)


def test_portfolios_endpoint_includes_risk_tier():
    response = client.get("/portfolios")
    portfolios = response.json()
    tiers = {p["risk_tier"] for p in portfolios}
    assert tiers.issubset({"Low", "Moderate", "Elevated", "High", "Very High"})


def test_lens_run_rejects_unknown_sector():
    response = client.post("/lens/run", json={"sector": "Not A Real Sector"})
    assert response.status_code == 404


def test_clients_endpoint_returns_one_per_real_portfolio():
    response = client.get("/clients")
    assert response.status_code == 200
    clients = response.json()
    assert len(clients) == 12


def test_clients_endpoint_excludes_reference_book():
    response = client.get("/clients")
    clients = response.json()
    names = [c["portfolio_name"] for c in clients]
    assert "Reference Balanced 60/40 Fund" not in names


def test_clients_endpoint_aum_matches_holdings_sum():
    response = client.get("/clients")
    clients = response.json()
    for c in clients:
        assert c["aum"] == pytest.approx(sum(h["market_value"] for h in c["holdings"]))


def test_clients_endpoint_holdings_sorted_by_weight_desc():
    response = client.get("/clients")
    clients = response.json()
    for c in clients:
        weights = [h["weight_pct"] for h in c["holdings"]]
        assert weights == sorted(weights, reverse=True)


def test_clients_endpoint_includes_contact_and_contract_info():
    response = client.get("/clients")
    clients = response.json()
    for c in clients:
        assert c["client"]["name"]
        assert c["client"]["email"]
        assert c["client"]["relationship_since"]
        assert c["client"]["risk_mandate"]


def test_clients_endpoint_has_performance_and_suitability():
    clients = client.get("/clients").json()
    for c in clients:
        p = c["performance"]
        assert p["one_year_pct"] is not None
        assert p["vs_benchmark_1y"] == pytest.approx(p["one_year_pct"] - p["benchmark_one_year_pct"], abs=0.15)
        assert c["suitability"]["status"] in ("matched", "aggressive", "conservative", "unknown")


def test_overview_book_performance_present():
    perf = client.get("/overview").json()["performance"]
    assert perf["book_one_year_pct"] is not None
    assert perf["best"]["one_year_pct"] >= perf["worst"]["one_year_pct"]


def test_clients_endpoint_sector_breakdown_sums_to_100():
    response = client.get("/clients")
    clients = response.json()
    for c in clients:
        total = sum(b["weight_pct"] for b in c["sector_breakdown"])
        assert total == pytest.approx(100.0, abs=0.5)


def test_clients_endpoint_sector_breakdown_ranked_desc():
    response = client.get("/clients")
    clients = response.json()
    for c in clients:
        weights = [b["weight_pct"] for b in c["sector_breakdown"]]
        assert weights == sorted(weights, reverse=True)


def test_clients_endpoint_suggested_sector_is_researchable_or_none():
    from api import RESEARCHABLE_SECTORS
    response = client.get("/clients")
    clients = response.json()
    for c in clients:
        if c["suggested_sector"] is not None:
            assert c["suggested_sector"] in RESEARCHABLE_SECTORS


def test_banking_fund_suggested_sector_is_financials():
    """The Banking & Financials Concentrated Fund is ~100% financials, so the
    analysis flow should default it to Financials."""
    response = client.get("/clients")
    clients = response.json()
    banking = next(c for c in clients if c["portfolio_id"] == "pf_banking_financials")
    assert banking["suggested_sector"] == "Financials"


# ---------------------------------------------------------------------------
# Overview (firm-wide summary — fully deterministic, so fully testable)
# ---------------------------------------------------------------------------

def test_overview_kpis_present_and_positive():
    kpis = client.get("/overview").json()["kpis"]
    assert kpis["client_count"] == 12
    assert kpis["total_aum"] > 0
    assert kpis["holdings_count"] > 0
    assert kpis["distinct_securities"] > 0
    assert kpis["blended_fee_pct"] > 0


def test_overview_total_aum_matches_clients_sum():
    overview = client.get("/overview").json()
    clients = client.get("/clients").json()
    assert overview["kpis"]["total_aum"] == pytest.approx(sum(c["aum"] for c in clients))


def test_overview_asset_class_allocation_sums_to_100():
    alloc = client.get("/overview").json()["asset_class_allocation"]
    assert sum(a["pct"] for a in alloc) == pytest.approx(100.0, abs=0.5)


def test_overview_sector_allocation_sums_to_100():
    alloc = client.get("/overview").json()["sector_allocation"]
    assert sum(a["pct"] for a in alloc) == pytest.approx(100.0, abs=0.5)


def test_overview_top_holdings_ranked_and_capped():
    top = client.get("/overview").json()["top_holdings"]
    assert len(top) <= 10
    values = [h["value"] for h in top]
    assert values == sorted(values, reverse=True)
    for h in top:
        assert 1 <= h["held_by_count"] <= 12


def test_overview_risk_distribution_covers_all_tiers():
    dist = client.get("/overview").json()["risk_distribution"]
    tiers = [d["tier"] for d in dist]
    assert tiers == ["Low", "Moderate", "Elevated", "High", "Very High"]
    assert sum(d["count"] for d in dist) == 12


def test_overview_action_items_sorted_soonest_first():
    items = client.get("/overview").json()["action_items"]
    assert len(items) >= 1
    dues = [i["days_until_due"] for i in items if i["days_until_due"] is not None]
    assert dues == sorted(dues)  # soonest / most overdue first
    for i in items:
        assert i["action"] and i["client_name"]
        assert i["priority"] in ("Low", "Normal", "High")


def test_overview_largest_clients_sorted_desc():
    largest = client.get("/overview").json()["largest_clients"]
    aums = [c["aum"] for c in largest]
    assert aums == sorted(aums, reverse=True)
    assert len(largest) == 12


# ---------------------------------------------------------------------------
# News feed (category listing + validation only — the live research call
# itself is covered by manual runs, same reasoning as /lens/run above)
# ---------------------------------------------------------------------------

def test_news_categories_returns_expected_set():
    response = client.get("/news/categories")
    assert response.status_code == 200
    categories = response.json()
    for expected in [
        "India Markets", "Global cues for India", "Commodities & Energy",
        "Currency & Rates", "Corporate Earnings", "Policy & Regulation", "India Startups",
    ]:
        assert expected in categories
    assert len(categories) >= 6


def test_products_groups_cover_all_securities():
    resp = client.get("/products").json()
    assert resp["total"] == sum(g["count"] for g in resp["groups"])
    # every group's items are ranked by usage then name
    for g in resp["groups"]:
        counts = [i["held_by_count"] for i in g["items"]]
        assert counts == sorted(counts, reverse=True)


def test_products_held_by_count_within_bounds():
    resp = client.get("/products").json()
    for g in resp["groups"]:
        for item in g["items"]:
            assert 0 <= item["held_by_count"] <= 12


def test_clients_include_communications_and_next_action():
    clients = client.get("/clients").json()
    for c in clients:
        assert "communications" in c["client"]
        assert c["client"]["next_action"]["action"]
        assert c["client"]["relationship"]["manager_note"]


def test_news_feed_rejects_unknown_category():
    response = client.get("/news/feed", params={"category": "Not A Real Category"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Talking points (validation only — the live LLM narration call itself is
# covered by manual runs, same reasoning as /lens/run and /news/feed above)
# ---------------------------------------------------------------------------

def test_talking_points_rejects_unknown_portfolio():
    response = client.post("/talking-points", json={"portfolio_id": "not-a-real-portfolio", "sector": "Financials"})
    assert response.status_code == 404


def test_talking_points_rejects_unknown_sector():
    response = client.post("/talking-points", json={"portfolio_id": "pf_banking_financials", "sector": "Not A Real Sector"})
    assert response.status_code == 404


def test_talking_points_rejects_reference_portfolio():
    """The reference book has no client — it should never be a valid target."""
    response = client.post("/talking-points", json={"portfolio_id": "pf_reference_balanced", "sector": "Financials"})
    assert response.status_code == 404
