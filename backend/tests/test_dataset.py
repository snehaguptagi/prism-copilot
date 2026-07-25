"""
Data-integrity tests for prism_data.json. These catch the class of bug that
doesn't show up as a crash: a portfolio whose weights don't sum to 1.0, a
holding pointing at a security that doesn't exist, a factor tag with a typo'd
key that silently never matches anything.
"""

import json
import os

import pytest

from insight_lens import REFERENCE_PORTFOLIO_ID

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "prism_data.json")
VALID_FACTOR_KEYS = {"gold", "oil", "interest_rates_india", "interest_rates_us", "usd_inr"}
VALID_SENSITIVITIES = {"same_direction", "positive", "negative"}


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_holding_weights_sum_to_one_per_portfolio(data):
    totals = {}
    for h in data["holdings"]:
        totals[h["portfolio_id"]] = totals.get(h["portfolio_id"], 0.0) + h["weight"]
    for pid, total in totals.items():
        assert total == pytest.approx(1.0, abs=1e-6), f"{pid} weights sum to {total}, not 1.0"


def test_every_holding_points_at_a_real_security(data):
    security_ids = {s["security_id"] for s in data["securities"]}
    for h in data["holdings"]:
        assert h["security_id"] in security_ids, f"holding {h['holding_id']} references unknown security {h['security_id']}"


def test_every_holding_points_at_a_real_portfolio(data):
    portfolio_ids = {p["portfolio_id"] for p in data["portfolios"]}
    for h in data["holdings"]:
        assert h["portfolio_id"] in portfolio_ids, f"holding {h['holding_id']} references unknown portfolio {h['portfolio_id']}"


def test_no_duplicate_security_ids(data):
    ids = [s["security_id"] for s in data["securities"]]
    assert len(ids) == len(set(ids)), "duplicate security_id in securities master"


def test_no_duplicate_portfolio_ids(data):
    ids = [p["portfolio_id"] for p in data["portfolios"]]
    assert len(ids) == len(set(ids)), "duplicate portfolio_id"


def test_no_duplicate_holding_ids(data):
    ids = [h["holding_id"] for h in data["holdings"]]
    assert len(ids) == len(set(ids)), "duplicate holding_id"


def test_parent_id_references_resolve(data):
    security_ids = {s["security_id"] for s in data["securities"]}
    for s in data["securities"]:
        if s.get("parent_id"):
            assert s["parent_id"] in security_ids, f"{s['security_id']} has dangling parent_id {s['parent_id']}"


def test_adr_of_references_resolve(data):
    security_ids = {s["security_id"] for s in data["securities"]}
    for s in data["securities"]:
        if s.get("adr_of"):
            assert s["adr_of"] in security_ids, f"{s['security_id']} has dangling adr_of {s['adr_of']}"


def test_factor_sensitivity_keys_are_known(data):
    for s in data["securities"]:
        for factor_key in s.get("factor_sensitivities", {}):
            assert factor_key in VALID_FACTOR_KEYS, (
                f"{s['security_id']} tags unknown factor '{factor_key}' — "
                f"a typo here silently never matches any detected signal"
            )


def test_factor_sensitivity_values_are_known(data):
    for s in data["securities"]:
        for factor_key, sensitivity in s.get("factor_sensitivities", {}).items():
            assert sensitivity in VALID_SENSITIVITIES, (
                f"{s['security_id']}['{factor_key}'] = '{sensitivity}' is not a recognized "
                f"sensitivity value; compute_factor_impact silently ignores anything else"
            )


def test_exactly_one_reference_portfolio(data):
    reference_portfolios = [p for p in data["portfolios"] if p.get("is_reference")]
    assert len(reference_portfolios) == 1, (
        f"expected exactly 1 reference portfolio, found {len(reference_portfolios)} — "
        f"attach_reference_comparison hardcodes a single REFERENCE_PORTFOLIO_ID"
    )


def test_reference_portfolio_id_constant_matches_data(data):
    """insight_lens.REFERENCE_PORTFOLIO_ID is a hardcoded string, not derived
    from the data file. If prism_data.json's reference portfolio id ever
    changes without updating that constant, attach_reference_comparison would
    silently compare every fund against a reference value of 0 instead of
    raising an error — this test is the tripwire for that."""
    reference_portfolios = [p for p in data["portfolios"] if p.get("is_reference")]
    assert reference_portfolios[0]["portfolio_id"] == REFERENCE_PORTFOLIO_ID


def test_no_us_or_crypto_securities(data):
    """Regression guard for the explicit 'India only, no US, no crypto' requirement."""
    for s in data["securities"]:
        assert s["country"] == "IN", f"{s['security_id']} has country={s['country']}, expected IN-only book"
        assert s["asset_class"] != "Digital Assets", f"{s['security_id']} is a Digital Assets holding — crypto was explicitly excluded"


def test_all_aliases_are_at_least_three_chars(data):
    """The entity linker skips needles of length <= 2 to avoid noise; an alias
    shorter than that is silently useless and probably a mistake."""
    for s in data["securities"]:
        for alias in s.get("aliases", []):
            assert len(alias) > 2, f"{s['security_id']} has alias '{alias}' too short to ever match (linker requires len > 2)"
