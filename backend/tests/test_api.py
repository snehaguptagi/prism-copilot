"""
Smoke tests for the FastAPI layer (api.py). Only exercises the endpoints that
don't require a live LLM call (/sectors, /portfolios, /clients, /me,
/news/categories) plus validation paths on the LLM-backed endpoints —
/lens/run, /news/feed, and /talking-points' actual research/narration calls
are covered by the manual live runs already done directly against
insight_lens.py, since mocking a full Anthropic response would test the
mock, not the app. No auth — this is an open, single-PM demo API.
"""

import os

import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)

SEED_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "prism_data.json")


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
    assert len(portfolios) == 16
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
    assert len(clients) == 16


def test_add_client_creates_a_valid_persisted_client(preserve_dataset, clean_overlay):
    resp = client.post("/clients", json={
        "name": "Test Client Zzz",
        "occupation": "Software Engineer",
        "city": "Pune",
        "risk_mandate": "Moderate",
        "initial_aum": 3_000_000,
        "template_portfolio_id": "pf_largecap_growth",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["client_name"] == "Test Client Zzz"
    new_pid = body["portfolio_id"]

    # shows up immediately, no restart, because load_data() re-reads from disk
    clients = client.get("/clients").json()
    match = next((c for c in clients if c["portfolio_id"] == new_pid), None)
    assert match is not None
    assert match["aum"] == pytest.approx(3_000_000, abs=1)
    assert match["aum"] == pytest.approx(sum(h["market_value"] for h in match["holdings"]))
    assert match["risk_tier"] in ("Low", "Moderate", "Elevated", "High", "Very High")
    assert match["suitability"]["status"] in ("matched", "aggressive", "conservative")  # never "unknown"
    assert match["client"]["risk_mandate"] == "Moderate"

    overview = client.get("/overview").json()
    assert overview["kpis"]["client_count"] == 17  # 16 seeded + this one


def test_add_client_risk_tier_matches_shared_formula(preserve_dataset, clean_overlay):
    """The runtime endpoint must compute risk with the exact same formula the
    seed dataset uses (portfolio_risk.compute_portfolio_risk), so a client
    added live is never treated differently from a seeded one."""
    from api import load_data
    from portfolio_risk import compute_portfolio_risk

    resp = client.post("/clients", json={
        "name": "Formula Check Client",
        "occupation": "Consultant",
        "city": "Delhi",
        "risk_mandate": "Aggressive",
        "initial_aum": 1_000_000,
        "template_portfolio_id": "pf_smallcap_value",
    })
    new_pid = resp.json()["portfolio_id"]

    data = load_data()
    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    template_weights = {
        h["security_id"]: h["weight"] for h in data["holdings"] if h["portfolio_id"] == "pf_smallcap_value"
    }
    _, _, expected_risk = compute_portfolio_risk(1_000_000, template_weights, sec_by_id)
    assert data["risk"][new_pid]["risk_tier"] == expected_risk["risk_tier"]
    assert data["risk"][new_pid]["risk_score"] == expected_risk["risk_score"]


def test_add_client_rejects_unknown_mandate(preserve_dataset, clean_overlay):
    resp = client.post("/clients", json={
        "name": "Bad Mandate Client", "occupation": "X", "city": "Y",
        "risk_mandate": "Not A Real Mandate", "initial_aum": 1_000_000,
        "template_portfolio_id": "pf_largecap_growth",
    })
    assert resp.status_code == 400


def test_add_client_rejects_unknown_template(preserve_dataset, clean_overlay):
    resp = client.post("/clients", json={
        "name": "Bad Template Client", "occupation": "X", "city": "Y",
        "risk_mandate": "Moderate", "initial_aum": 1_000_000,
        "template_portfolio_id": "not-a-real-portfolio",
    })
    assert resp.status_code == 404


def test_add_client_rejects_non_positive_aum(preserve_dataset, clean_overlay):
    resp = client.post("/clients", json={
        "name": "Zero AUM Client", "occupation": "X", "city": "Y",
        "risk_mandate": "Moderate", "initial_aum": 0,
        "template_portfolio_id": "pf_largecap_growth",
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# The runtime-edit overlay: added clients, edited holdings, filled-in profiles.
# The contract is that all three persist in prism_overlay.json and NEVER touch
# prism_data.json, so `python build_dataset.py` cannot destroy an RM's work.
# ---------------------------------------------------------------------------

BASE_CLIENT = {
    "occupation": "Software Engineer",
    "city": "Pune",
    "risk_mandate": "Moderate",
    "initial_aum": 3_000_000,
    "template_portfolio_id": "pf_largecap_growth",
}


def _add(name, **extra):
    resp = client.post("/clients", json={"name": name, **BASE_CLIENT, **extra})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_add_client_leaves_the_seed_dataset_byte_identical(preserve_dataset, clean_overlay):
    """The whole reason the overlay exists. If this fails, regenerating the demo
    dataset silently deletes every client the RM added."""
    original = preserve_dataset
    _add("Overlay Only Client")
    with open(SEED_DATA_PATH, encoding="utf-8") as f:
        assert f.read() == original


def test_added_client_survives_a_seed_dataset_rebuild(preserve_dataset, clean_overlay):
    """Simulates `python build_dataset.py`: rewrite prism_data.json from the
    generator, then confirm the added client is still there afterwards."""
    import build_dataset

    new_pid = _add("Rebuild Survivor")["portfolio_id"]
    build_dataset.main()  # the exact thing that used to wipe added clients

    clients = client.get("/clients").json()
    assert any(c["portfolio_id"] == new_pid for c in clients)


def test_add_client_accepts_a_behavioral_profile_that_drives_product_fit(preserve_dataset, clean_overlay):
    """The gap this closes: without psychographics, _preference_profile scores
    every asset class at 0.0 and no suggestion can say "Matches ...". Supplying
    a preservation goal must produce a preference-matched suggestion, exactly
    like a seeded client gets."""
    body = _add(
        "Profiled New Client",
        risk_mandate="Conservative",
        psychographics={
            "primary_goal": "Preserve capital and avoid losses",
            "time_horizon": "Short, under 3 years",
            "loss_aversion": "Very high",
            "life_stage": "Retired",
        },
    )
    assert body["has_profile"] is True

    match = next(c for c in client.get("/clients").json() if c["portfolio_id"] == body["portfolio_id"])
    assert match["client"]["psychographics"]["primary_goal"] == "Preserve capital and avoid losses"
    matched = [s for s in match["product_suggestions"] if s["rationale"].startswith("Matches ")]
    assert matched, "a profiled client must get preference-matched suggestions"


def test_add_client_without_a_profile_still_works_but_has_no_preference_match(preserve_dataset, clean_overlay):
    """Documents the honest fallback: no profile means suggestions still appear
    (mandate-and-gap reasoning), they just cannot claim a preference match."""
    body = _add("Unprofiled New Client")
    assert body["has_profile"] is False
    match = next(c for c in client.get("/clients").json() if c["portfolio_id"] == body["portfolio_id"])
    assert match["product_suggestions"], "must still get suggestions"
    assert not [s for s in match["product_suggestions"] if s["rationale"].startswith("Matches ")]


def test_profile_update_makes_product_fit_work_for_an_added_client(preserve_dataset, clean_overlay):
    """Same outcome as supplying the profile up front, but filled in later,
    which is the realistic flow: add the client, learn about them, come back."""
    new_pid = _add("Later Profiled Client")["portfolio_id"]
    before = next(c for c in client.get("/clients").json() if c["portfolio_id"] == new_pid)
    assert not [s for s in before["product_suggestions"] if s["rationale"].startswith("Matches ")]

    resp = client.put(f"/clients/{new_pid}/profile", json={
        "psychographics": {"primary_goal": "Hedge against inflation with gold", "loss_aversion": "High"},
    })
    assert resp.status_code == 200
    assert [s for s in resp.json()["product_suggestions"] if s["rationale"].startswith("Matches ")]

    after = next(c for c in client.get("/clients").json() if c["portfolio_id"] == new_pid)
    assert after["client"]["psychographics"]["primary_goal"] == "Hedge against inflation with gold"


def test_profile_update_merges_rather_than_replaces(preserve_dataset, clean_overlay):
    new_pid = _add("Merge Profile Client")["portfolio_id"]
    client.put(f"/clients/{new_pid}/profile", json={"psychographics": {"primary_goal": "Long-term growth and compounding"}})
    resp = client.put(f"/clients/{new_pid}/profile", json={"psychographics": {"life_stage": "Early career"}})
    psy = resp.json()["psychographics"]
    assert psy["primary_goal"] == "Long-term growth and compounding"  # not blanked by the second call
    assert psy["life_stage"] == "Early career"


def test_profile_update_works_on_a_seeded_client_without_touching_seed_data(preserve_dataset, clean_overlay):
    original = preserve_dataset
    resp = client.put("/clients/pf_largecap_growth/profile", json={
        "psychographics": {"engagement": "Checks daily"},
    })
    assert resp.status_code == 200
    assert resp.json()["psychographics"]["engagement"] == "Checks daily"
    # the seeded fields it did not mention must survive
    assert resp.json()["psychographics"].get("primary_goal")
    with open(SEED_DATA_PATH, encoding="utf-8") as f:
        assert f.read() == original


def test_profile_update_rejects_unknown_and_clientless_portfolios(clean_overlay):
    assert client.put("/clients/nope/profile", json={"persona": "x"}).status_code == 404
    assert client.put("/clients/pf_reference_balanced/profile", json={"persona": "x"}).status_code == 400


def test_profile_update_rejects_an_empty_patch(clean_overlay):
    assert client.put("/clients/pf_largecap_growth/profile", json={}).status_code == 400


def test_edit_holdings_renormalizes_preserves_nav_and_recomputes_risk(preserve_dataset, clean_overlay):
    """Weights are raw input: 60/40 typed as 60 and 40 must normalize to 0.6/0.4,
    NAV must be preserved from the existing book, and the risk block must be
    recomputed by the shared formula rather than left stale."""
    from portfolio_risk import compute_portfolio_risk
    from api import load_data

    new_pid = _add("Holdings Edit Client")["portfolio_id"]
    before = next(c for c in client.get("/clients").json() if c["portfolio_id"] == new_pid)
    nav_before = before["aum"]

    resp = client.put(f"/clients/{new_pid}/holdings", json={
        "holdings": [
            {"security_id": "sec_hdfcbank", "weight": 60},
            {"security_id": "sec_gsec_10y", "weight": 40},
        ],
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["num_holdings"] == 2
    assert resp.json()["aum"] == pytest.approx(nav_before, abs=1)

    after = next(c for c in client.get("/clients").json() if c["portfolio_id"] == new_pid)
    weights = {h["security_id"]: h["weight_pct"] for h in after["holdings"]}
    assert weights == {"sec_hdfcbank": 60.0, "sec_gsec_10y": 40.0}
    assert after["aum"] == pytest.approx(nav_before, abs=1)
    assert sum(h["market_value"] for h in after["holdings"]) == pytest.approx(nav_before, abs=1)

    data = load_data()
    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    _, _, expected = compute_portfolio_risk(nav_before, {"sec_hdfcbank": 60, "sec_gsec_10y": 40}, sec_by_id)
    assert data["risk"][new_pid]["risk_tier"] == expected["risk_tier"]
    assert data["risk"][new_pid]["risk_score"] == expected["risk_score"]
    assert after["risk_tier"] == expected["risk_tier"]


def test_edit_holdings_actually_removes_dropped_positions(preserve_dataset, clean_overlay):
    """A replace, not a merge. If overlay holdings were appended instead of
    replacing, the dropped names would linger and weights would not sum to 1."""
    new_pid = _add("Position Drop Client")["portfolio_id"]
    before = next(c for c in client.get("/clients").json() if c["portfolio_id"] == new_pid)
    assert len(before["holdings"]) > 1

    client.put(f"/clients/{new_pid}/holdings", json={
        "holdings": [{"security_id": "sec_hdfcbank", "weight": 1}],
    })
    after = next(c for c in client.get("/clients").json() if c["portfolio_id"] == new_pid)
    assert [h["security_id"] for h in after["holdings"]] == ["sec_hdfcbank"]
    assert after["holdings"][0]["weight_pct"] == 100.0


def test_edit_holdings_accepts_an_explicit_nav(preserve_dataset, clean_overlay):
    new_pid = _add("Nav Override Client")["portfolio_id"]
    resp = client.put(f"/clients/{new_pid}/holdings", json={
        "holdings": [{"security_id": "sec_hdfcbank", "weight": 1}],
        "nav": 9_500_000,
    })
    assert resp.json()["aum"] == pytest.approx(9_500_000)
    after = next(c for c in client.get("/clients").json() if c["portfolio_id"] == new_pid)
    assert after["aum"] == pytest.approx(9_500_000, abs=1)


def test_edit_holdings_works_on_a_seeded_client_without_touching_seed_data(preserve_dataset, clean_overlay):
    original = preserve_dataset
    resp = client.put("/clients/pf_largecap_growth/holdings", json={
        "holdings": [
            {"security_id": "sec_hdfcbank", "weight": 50},
            {"security_id": "sec_tcs", "weight": 50},
        ],
    })
    assert resp.status_code == 200
    after = next(c for c in client.get("/clients").json() if c["portfolio_id"] == "pf_largecap_growth")
    assert len(after["holdings"]) == 2
    with open(SEED_DATA_PATH, encoding="utf-8") as f:
        assert f.read() == original


@pytest.mark.parametrize("payload,expected", [
    ({"holdings": []}, 400),                                                            # empty book
    ({"holdings": [{"security_id": "sec_nope", "weight": 1}]}, 404),                     # unknown security
    ({"holdings": [{"security_id": "sec_hdfcbank", "weight": 0}]}, 400),                 # zero weight
    ({"holdings": [{"security_id": "sec_hdfcbank", "weight": -5}]}, 400),                # negative weight
    ({"holdings": [{"security_id": "sec_hdfcbank", "weight": 1},
                   {"security_id": "sec_hdfcbank", "weight": 2}]}, 400),                 # duplicate
    ({"holdings": [{"security_id": "sec_hdfcbank", "weight": 1}], "nav": 0}, 400),       # bad nav
])
def test_edit_holdings_validation(payload, expected, preserve_dataset, clean_overlay):
    resp = client.put("/clients/pf_largecap_growth/holdings", json=payload)
    assert resp.status_code == expected


def test_edit_holdings_rejects_unknown_and_reference_portfolios(clean_overlay):
    body = {"holdings": [{"security_id": "sec_hdfcbank", "weight": 1}]}
    assert client.put("/clients/nope/holdings", json=body).status_code == 404
    assert client.put("/clients/pf_reference_balanced/holdings", json=body).status_code == 400


def test_delete_removes_an_added_client_but_refuses_a_seeded_one(preserve_dataset, clean_overlay):
    new_pid = _add("Deletable Client")["portfolio_id"]
    assert client.delete(f"/clients/{new_pid}").status_code == 200
    assert not any(c["portfolio_id"] == new_pid for c in client.get("/clients").json())
    assert client.get("/overview").json()["kpis"]["client_count"] == 16

    refused = client.delete("/clients/pf_largecap_growth")
    assert refused.status_code == 400
    assert any(c["portfolio_id"] == "pf_largecap_growth" for c in client.get("/clients").json())


def test_added_clients_are_flagged_custom_and_seeded_ones_are_not(preserve_dataset, clean_overlay):
    new_pid = _add("Flag Check Client")["portfolio_id"]
    by_id = {c["portfolio_id"]: c for c in client.get("/clients").json()}
    assert by_id[new_pid]["is_custom"] is True
    assert by_id["pf_largecap_growth"]["is_custom"] is False


def test_a_corrupt_overlay_is_ignored_rather_than_fatal(clean_overlay):
    """A hand-edited overlay must never be able to take the app down."""
    with open(clean_overlay, "w", encoding="utf-8") as f:
        f.write("{not valid json at all")
    assert client.get("/clients").status_code == 200
    assert len(client.get("/clients").json()) == 16


# Middle-of-the-road answers that are SUPPOSED to leave scoring untouched: a
# client with a medium horizon and moderate loss aversion has expressed no tilt,
# and inventing one would be dishonest. Listed explicitly so the test below can
# tell "deliberately neutral" apart from "silently broken wording".
NEUTRAL_PROFILE_OPTIONS = {
    ("time_horizon", "Medium, 3 to 7 years"),
    ("loss_aversion", "Moderate"),
    ("life_stage", "Mid career"),
    ("life_stage", "Peak earning years"),
    ("life_stage", "Near retirement"),
}


def test_profile_options_stay_aligned_with_the_preference_matcher():
    """The dropdown vocabulary is only useful if _preference_profile actually
    matches on it. Every option is either opinionated (moves at least one asset
    class) or listed above as deliberately neutral. Catches the real failure
    mode: someone rewords an option, the keyword stops matching, and the form
    goes on offering a choice that quietly does nothing."""
    from api import _preference_profile

    body = client.get("/profile-options").json()
    options, scoring = body["options"], body["scoring_fields"]
    assert set(scoring) <= set(options)

    for field in scoring:
        for value in options[field]:
            aff, _reasons = _preference_profile({"psychographics": {field: value}})
            moves = any(v != 0.0 for v in aff.values())
            if (field, value) in NEUTRAL_PROFILE_OPTIONS:
                assert not moves, f"{field}={value!r} was meant to be neutral but now scores"
            else:
                assert moves, f"{field}={value!r} scores nothing; wording no longer matches"

    # Every neutral entry must correspond to a real option, so the list cannot
    # rot into a silent exemption for an option that was renamed or removed.
    for field, value in NEUTRAL_PROFILE_OPTIONS:
        assert value in options[field], f"stale neutral exemption: {field}={value!r}"


def test_opinionated_goals_produce_a_quotable_reason():
    """A scored preference must also come with the phrasing the rationale uses,
    otherwise suggestions rank correctly but cannot explain themselves."""
    from api import PROFILE_OPTIONS, _preference_profile

    for goal in PROFILE_OPTIONS["primary_goal"]:
        _aff, reasons = _preference_profile({"psychographics": {"primary_goal": goal}})
        assert reasons, f"{goal!r} scores but has no reason text to quote"


def test_depositary_receipts_are_never_offered_as_products():
    """sec_infosys_adr exists so the entity linker can resolve "Infosys ADR" back
    to the domestic line. It is held by nobody and must never surface as a
    sellable product: on an India-only desk that means offering a US-listed
    wrapper around a name most clients already hold. It must still remain in the
    securities master, because /securities and the linker both need it."""
    from api import load_data, suggest_products, is_sellable_product

    data = load_data()
    adrs = [s for s in data["securities"] if s.get("adr_of")]
    assert adrs, "fixture gone: this test needs at least one ADR in the master"
    adr_ids = {s["security_id"] for s in adrs}

    assert all(not is_sellable_product(s) for s in adrs)

    # absent from the catalogue
    for group in client.get("/products").json()["groups"]:
        for item in group["items"]:
            assert item["security_id"] not in adr_ids

    # absent from every client's cross-sell suggestions
    for p in data["portfolios"]:
        if not p.get("client") or p.get("is_reference"):
            continue
        for s in suggest_products(data, p):
            assert s["security_id"] not in adr_ids

    # still in the master, so linking and the holdings editor keep working
    assert adr_ids <= {s["security_id"] for s in client.get("/securities").json()}


def test_securities_endpoint_lists_the_whole_universe():
    secs = client.get("/securities").json()
    from api import load_data
    assert len(secs) == len(load_data()["securities"])
    assert {"security_id", "name", "ticker", "sector", "asset_class"} <= set(secs[0])
    assert [s["name"] for s in secs] == sorted(s["name"] for s in secs)


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
        assert [h["label"] for h in p["horizons"]] == ["YTD", "1Y", "3Y"]
        assert c["suitability"]["status"] in ("matched", "aggressive", "conservative", "unknown")


def test_clients_endpoint_asset_class_allocation_sums_to_100():
    clients = client.get("/clients").json()
    for c in clients:
        alloc = c["asset_class_allocation"]
        assert alloc  # non-empty
        assert sum(a["pct"] for a in alloc) == pytest.approx(100.0, abs=0.5)
        assert [a["pct"] for a in alloc] == sorted([a["pct"] for a in alloc], reverse=True)


def test_every_client_mandate_is_mapped_for_suitability():
    """Every client's stated mandate should resolve to a real suitability verdict,
    never 'unknown' (which means the mandate string isn't in the tier maps)."""
    clients = client.get("/clients").json()
    unmapped = [c["client"]["name"] for c in clients if c["suitability"]["status"] == "unknown"]
    assert unmapped == [], f"Unmapped mandates: {unmapped}"


def test_overview_book_performance_present():
    perf = client.get("/overview").json()["performance"]
    assert perf["book_one_year_pct"] is not None
    assert perf["best"]["one_year_pct"] >= perf["worst"]["one_year_pct"]


def test_overview_book_performance_has_horizons():
    perf = client.get("/overview").json()["performance"]
    assert perf["book_ytd_pct"] is not None
    assert perf["book_three_year_cagr_pct"] is not None
    labels = [h["label"] for h in perf["horizons"]]
    assert labels == ["YTD", "1Y", "3Y"]
    for h in perf["horizons"]:
        assert h["book"] is not None and h["benchmark"] is not None


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
    assert kpis["client_count"] == 16
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
        assert 1 <= h["held_by_count"] <= 16


def test_overview_risk_distribution_covers_all_tiers():
    dist = client.get("/overview").json()["risk_distribution"]
    tiers = [d["tier"] for d in dist]
    assert tiers == ["Low", "Moderate", "Elevated", "High", "Very High"]
    assert sum(d["count"] for d in dist) == 16


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
    assert len(largest) == 16


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


def test_graph_status_shape():
    """Graph status is always answerable, even with no Neo4j configured."""
    body = client.get("/graph/status").json()
    assert set(body) == {"enabled", "connected"}
    assert isinstance(body["enabled"], bool)
    assert isinstance(body["connected"], bool)


def test_graph_suggestions_degrade_gracefully(monkeypatch):
    """With no graph configured, suggestions are an empty list, never an error.
    Force the env off with monkeypatch rather than assuming NEO4J_* is unset,
    since a developer's local .env may legitimately have real graph creds."""
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    resp = client.get("/clients/pf_gold_hedge/graph-suggestions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert body["suggestions"] == []


def test_graph_recommends_when_configured():
    """When a real graph is configured and reachable, suggestions are non-empty
    and well-shaped. Skips itself everywhere the graph isn't configured
    (including CI, which has no Neo4j secret), so it never fails there."""
    import graph
    if not graph.graph_enabled():
        pytest.skip("Neo4j not configured in this environment")
    resp = client.get("/clients/pf_it_services/graph-suggestions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert len(body["suggestions"]) > 0
    for s in body["suggestions"]:
        assert s["asset_class"] != "Cash"
        assert s["rationale"]


def test_graph_suggestions_unknown_client_404():
    resp = client.get("/clients/not-a-real-portfolio/graph-suggestions")
    assert resp.status_code == 404


def test_graph_view_shape():
    resp = client.get("/clients/pf_it_services/graph-view")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= {"portfolio_id", "client_name", "graph_enabled", "nodes", "edges", "best_match", "top_matches"}
    assert any(n["id"] == "client" for n in body["nodes"])
    assert len(body["edges"]) > 0


def test_graph_view_unknown_client_404():
    resp = client.get("/clients/not-a-real-portfolio/graph-view")
    assert resp.status_code == 404


def test_graph_view_best_match_for_every_client():
    """Every client should get a best_match to highlight (every client has at
    least one rule-based suggestion, per test_every_client_gets_a_preference_matched_suggestion,
    so the graph tab is never empty)."""
    data_resp = client.get("/portfolios").json()
    for p in data_resp:
        resp = client.get(f"/clients/{p['portfolio_id']}/graph-view")
        body = resp.json()
        assert body["best_match"] is not None, f"No best_match for {p['portfolio_id']}"
        assert body["best_match"]["source"] in ("rule", "graph", "both")


def test_graph_view_shows_more_than_one_recommendation():
    """A client should see several worthwhile products, not just the single
    strongest one: top_matches is a ranked list, its first entry always equals
    best_match, and every entry is a distinct security."""
    portfolios = client.get("/portfolios").json()
    multi_seen = False
    for p in portfolios:
        body = client.get(f"/clients/{p['portfolio_id']}/graph-view").json()
        matches = body["top_matches"]
        assert matches, f"No top_matches for {p['portfolio_id']}"
        assert matches[0]["security_id"] == body["best_match"]["security_id"]
        ids = [m["security_id"] for m in matches]
        assert len(ids) == len(set(ids)), f"Duplicate security in top_matches for {p['portfolio_id']}"
        if len(matches) > 1:
            multi_seen = True
    assert multi_seen, "No client anywhere received more than one recommendation"


def test_graph_overview_shape():
    resp = client.get("/graph/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= {"graph_enabled", "client_count", "clients", "classes", "products", "top_products"}
    assert body["client_count"] == 16
    assert len(body["clients"]) == 16


def test_graph_overview_products_sorted_by_client_count():
    products = client.get("/graph/overview").json()["products"]
    counts = [p["client_count"] for p in products]
    assert counts == sorted(counts, reverse=True)
    for p in products:
        assert len(p["client_names"]) == p["client_count"]


def test_graph_overview_agrees_with_per_client_best_match():
    """The firm-wide view's client_count for a product must reconcile with each
    client's own best_match from /clients/{id}/graph-view, so the two tabs
    never tell a different story."""
    overview = client.get("/graph/overview").json()
    portfolios = client.get("/portfolios").json()
    for p in portfolios:
        view = client.get(f"/clients/{p['portfolio_id']}/graph-view").json()
        client_entry = next(c for c in overview["clients"] if c["portfolio_id"] == p["portfolio_id"])
        expected_name = view["best_match"]["name"] if view["best_match"] else None
        assert client_entry["best_match"] == expected_name


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
            assert 0 <= item["held_by_count"] <= 16


def test_clients_include_communications_and_next_action():
    clients = client.get("/clients").json()
    for c in clients:
        assert "communications" in c["client"]
        assert c["client"]["next_action"]["action"]
        assert c["client"]["relationship"]["manager_note"]


def test_news_feed_rejects_unknown_category():
    response = client.get("/news/feed", params={"category": "Not A Real Category"})
    assert response.status_code == 404


def test_material_factors_surfaces_every_material_driver_not_just_one():
    """A client genuinely exposed to two or more distinct macro drivers at once
    (e.g. a rate headwind on bonds AND a gold tailwind on a commodity sleeve)
    must see both, not just whichever is largest. This is the fix for the bug
    where _dominant_factor kept only the single biggest driver across the
    whole entry and silently dropped the rest."""
    from api import _material_factors

    factor_entry = {
        "matched": [
            {"security_id": "sec_a", "factor": "interest_rates_india", "effect": "headwind", "weight_pct": 41.1},
            {"security_id": "sec_b", "factor": "gold", "effect": "tailwind", "weight_pct": 28.0},
            {"security_id": "sec_c", "factor": "oil", "effect": "tailwind", "weight_pct": 5.0},  # below materiality
        ]
    }
    result = _material_factors(factor_entry)
    factors = {f["factor"] for f in result}
    assert factors == {"interest_rates_india", "gold"}  # oil dropped, below the 15% threshold
    assert result[0]["factor"] == "interest_rates_india"  # sorted by pct desc
    assert result[0]["effect"] == "headwind"
    assert result[1]["effect"] == "tailwind"


def test_material_factors_reports_one_effect_per_factor():
    """If the same factor has both tailwind- and headwind-tagged holdings
    (different securities with opposing sensitivity to one factor), report
    only the larger side for that factor, not both."""
    from api import _material_factors

    factor_entry = {
        "matched": [
            {"security_id": "sec_a", "factor": "usd_inr", "effect": "tailwind", "weight_pct": 60.0},
            {"security_id": "sec_b", "factor": "usd_inr", "effect": "headwind", "weight_pct": 20.0},
        ]
    }
    result = _material_factors(factor_entry)
    assert len(result) == 1
    assert result[0]["effect"] == "tailwind"
    assert result[0]["pct"] == 60.0


# ---------------------------------------------------------------------------
# Talking points (validation only — the live LLM narration call itself is
# covered by manual runs, same reasoning as /lens/run and /news/feed above)
# ---------------------------------------------------------------------------

def test_product_suggestions_are_suitable_and_unheld():
    """Cross-sell suggestions must never include a name the client already holds,
    never exceed the client's mandate risk ceiling, and never be cash."""
    from api import load_data, suggest_products, _vol_band_rank, _MANDATE_MAX_TIER
    data = load_data()
    sec_by_id = {s["security_id"]: s for s in data["securities"]}
    for p in data["portfolios"]:
        if not p.get("client") or p.get("is_reference"):
            continue
        held = {h["security_id"] for h in data["holdings"] if h["portfolio_id"] == p["portfolio_id"]}
        mandate = (p["client"]["risk_mandate"] or "").strip().lower()
        max_band = _MANDATE_MAX_TIER.get(mandate, 2)
        suggestions = suggest_products(data, p)
        assert len(suggestions) <= 3
        seen = set()
        for item in suggestions:
            assert item["security_id"] not in held  # never already held
            assert item["security_id"] not in seen  # no duplicates
            seen.add(item["security_id"])
            s = sec_by_id[item["security_id"]]
            assert _vol_band_rank(s.get("vol")) <= max_band  # within the mandate ceiling
            assert s["asset_class"] != "Cash"
            assert item["rationale"]


def test_every_client_gets_a_preference_matched_suggestion():
    """Every client should get at least one product suggestion that matches their
    stated preferences (rationale starts with "Matches ..."), not only gap-fill
    fallbacks. Guards the preference engine against silently regressing to the
    old suitability-and-gap-only behavior."""
    from api import load_data, suggest_products
    data = load_data()
    for p in data["portfolios"]:
        if not p.get("client") or p.get("is_reference"):
            continue
        suggestions = suggest_products(data, p)
        matched = [s for s in suggestions if s["rationale"].startswith("Matches ")]
        assert matched, f"No preference-matched suggestion for {p['client']['name']}"


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
