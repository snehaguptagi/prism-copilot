"""
Tests for the deterministic roll-up engines: compute_portfolio_impact,
attach_reference_comparison, compute_factor_impact,
detect_cross_desk_contradictions, compute_scenario_impact.

Uses a small synthetic dataset (not the real prism_data.json) so these are
fast, isolated, and exercise edge cases the real data may not happen to hit.
The reference portfolio is deliberately named "pf_reference_balanced" to
match insight_lens.REFERENCE_PORTFOLIO_ID, since that constant is hardcoded.
"""

import pytest

from insight_lens import (
    attach_reference_comparison,
    compute_factor_impact,
    compute_portfolio_impact,
    compute_scenario_impact,
    detect_cross_desk_contradictions,
)


@pytest.fixture
def data():
    return {
        "securities": [
            {"security_id": "sec_bank_a", "factor_sensitivities": {"interest_rates_india": "positive"}},
            {"security_id": "sec_bond_a", "factor_sensitivities": {"interest_rates_india": "negative"}},
            {"security_id": "sec_gold_a", "factor_sensitivities": {"gold": "same_direction"}},
            {"security_id": "sec_plain", "factor_sensitivities": {}},
        ],
        "portfolios": [
            {"portfolio_id": "pf_bank", "name": "Bank Fund", "risk_driver": "Rate-sensitive banks"},
            {"portfolio_id": "pf_bond", "name": "Bond Fund", "risk_driver": "Rate-sensitive bonds"},
            {"portfolio_id": "pf_gold", "name": "Gold Fund", "risk_driver": "Gold hedge"},
            {"portfolio_id": "pf_reference_balanced", "name": "Reference 60/40", "is_reference": True},
        ],
        "holdings": [
            {"holding_id": "h1", "portfolio_id": "pf_bank", "security_id": "sec_bank_a", "weight": 1.0},
            {"holding_id": "h2", "portfolio_id": "pf_bond", "security_id": "sec_bond_a", "weight": 1.0},
            {"holding_id": "h3", "portfolio_id": "pf_gold", "security_id": "sec_gold_a", "weight": 1.0},
            {"holding_id": "h4", "portfolio_id": "pf_reference_balanced", "security_id": "sec_bank_a", "weight": 0.2},
            {"holding_id": "h5", "portfolio_id": "pf_reference_balanced", "security_id": "sec_plain", "weight": 0.8},
        ],
    }


# --------------------------------------------------------------------------
# compute_portfolio_impact (entity-linked NAV roll-up)
# --------------------------------------------------------------------------

def test_portfolio_impact_sums_matched_weight(data):
    linked = [{"linked_security_ids": ["sec_bank_a"]}]
    result = compute_portfolio_impact(data, linked)
    by_id = {r["portfolio_id"]: r for r in result}
    assert by_id["pf_bank"]["pct_nav_touched"] == 100.0
    assert by_id["pf_reference_balanced"]["pct_nav_touched"] == 20.0


def test_portfolio_impact_untouched_portfolios_absent(data):
    linked = [{"linked_security_ids": ["sec_gold_a"]}]
    result = compute_portfolio_impact(data, linked)
    ids = {r["portfolio_id"] for r in result}
    assert "pf_bank" not in ids
    assert "pf_bond" not in ids
    assert "pf_gold" in ids


def test_portfolio_impact_empty_citations_returns_empty(data):
    assert compute_portfolio_impact(data, []) == []


def test_portfolio_impact_sorted_descending(data):
    linked = [{"linked_security_ids": ["sec_bank_a"]}]  # touches pf_bank (100%) and reference (20%)
    result = compute_portfolio_impact(data, linked)
    pcts = [r["pct_nav_touched"] for r in result]
    assert pcts == sorted(pcts, reverse=True)


# --------------------------------------------------------------------------
# attach_reference_comparison ("you vs. a normal book" lens)
# --------------------------------------------------------------------------

def test_reference_comparison_excludes_reference_itself(data):
    linked = [{"linked_security_ids": ["sec_bank_a"]}]
    impact = compute_portfolio_impact(data, linked)
    compared = attach_reference_comparison(impact)
    assert all(r["portfolio_id"] != "pf_reference_balanced" for r in compared)


def test_reference_comparison_computes_correct_multiple(data):
    linked = [{"linked_security_ids": ["sec_bank_a"]}]
    impact = compute_portfolio_impact(data, linked)
    compared = attach_reference_comparison(impact)
    bank = next(r for r in compared if r["portfolio_id"] == "pf_bank")
    # pf_bank = 100%, reference = 20% -> 5.0x
    assert bank["vs_reference_pct"] == 20.0
    assert bank["vs_reference_multiple"] == 5.0


def test_reference_comparison_caps_multiple_at_10x(data):
    data["holdings"][3]["weight"] = 0.01  # reference exposure now tiny (1%... but still >= floor edge)
    data["holdings"][4]["weight"] = 0.99
    linked = [{"linked_security_ids": ["sec_bank_a"]}]
    impact = compute_portfolio_impact(data, linked)
    compared = attach_reference_comparison(impact)
    bank = next(r for r in compared if r["portfolio_id"] == "pf_bank")
    # own=100%, ref=1% -> raw multiple 100x, must cap
    assert bank["vs_reference_multiple"] == "10x+"


def test_reference_comparison_drops_multiple_below_materiality_floor(data):
    """A fund's own exposure below 5% NAV should show the fact but no multiple."""
    data["holdings"][0]["weight"] = 0.03  # pf_bank now only 3% exposed
    linked = [{"linked_security_ids": ["sec_bank_a"]}]
    impact = compute_portfolio_impact(data, linked)
    compared = attach_reference_comparison(impact)
    bank = next(r for r in compared if r["portfolio_id"] == "pf_bank")
    assert bank["pct_nav_touched"] == 3.0
    assert bank["vs_reference_multiple"] is None


def test_reference_comparison_handles_zero_reference_exposure(data):
    """If the reference book has zero exposure, dividing by zero must not crash."""
    linked = [{"linked_security_ids": ["sec_gold_a"]}]  # reference holds none of this
    impact = compute_portfolio_impact(data, linked)
    compared = attach_reference_comparison(impact)
    gold = next(r for r in compared if r["portfolio_id"] == "pf_gold")
    assert gold["vs_reference_pct"] == 0.0
    assert gold["vs_reference_multiple"] is None


# --------------------------------------------------------------------------
# compute_factor_impact (direction engine)
# --------------------------------------------------------------------------

def test_factor_impact_same_direction_sensitivity(data):
    signals = [{"factor": "gold", "direction": "down"}]
    result = compute_factor_impact(data, signals)
    gold = next(r for r in result if r["portfolio_id"] == "pf_gold")
    assert gold["headwind_pct"] == 100.0
    assert gold["tailwind_pct"] == 0.0


def test_factor_impact_positive_sensitivity(data):
    signals = [{"factor": "interest_rates_india", "direction": "up"}]
    result = compute_factor_impact(data, signals)
    bank = next(r for r in result if r["portfolio_id"] == "pf_bank")
    assert bank["tailwind_pct"] == 100.0


def test_factor_impact_negative_sensitivity_is_inverted(data):
    signals = [{"factor": "interest_rates_india", "direction": "up"}]
    result = compute_factor_impact(data, signals)
    bond = next(r for r in result if r["portfolio_id"] == "pf_bond")
    assert bond["headwind_pct"] == 100.0
    assert bond["tailwind_pct"] == 0.0


def test_factor_impact_mixed_direction_is_ignored(data):
    """A 'mixed' direction signal shouldn't be forced into tailwind or headwind."""
    signals = [{"factor": "interest_rates_india", "direction": "mixed"}]
    result = compute_factor_impact(data, signals)
    assert result == []


def test_factor_impact_empty_signals_returns_empty(data):
    assert compute_factor_impact(data, []) == []


def test_factor_impact_untagged_security_ignored(data):
    signals = [{"factor": "usd_inr", "direction": "up"}]  # nothing in fixture is tagged usd_inr
    result = compute_factor_impact(data, signals)
    assert result == []


# --------------------------------------------------------------------------
# detect_cross_desk_contradictions (ADVANCED.md #4)
# --------------------------------------------------------------------------

def test_contradiction_detected_between_bank_and_bond(data):
    signals = [{"factor": "interest_rates_india", "direction": "up"}]
    factor_impact = compute_factor_impact(data, signals)
    contradictions = detect_cross_desk_contradictions(data, factor_impact, min_material_pct=10.0)
    assert len(contradictions) == 1
    c = contradictions[0]
    assert c["factor"] == "interest_rates_india"
    assert c["tailwind_fund"] == "Bank Fund"
    assert c["headwind_fund"] == "Bond Fund"


def test_reference_portfolio_never_flagged_as_contradiction(data):
    signals = [{"factor": "interest_rates_india", "direction": "up"}]
    factor_impact = compute_factor_impact(data, signals)
    contradictions = detect_cross_desk_contradictions(data, factor_impact)
    names = [c["tailwind_fund"] for c in contradictions] + [c["headwind_fund"] for c in contradictions]
    assert "Reference 60/40" not in names


def test_no_contradiction_below_materiality_threshold(data):
    data["holdings"][0]["weight"] = 0.05  # pf_bank only 5% exposed, below default 10% floor
    signals = [{"factor": "interest_rates_india", "direction": "up"}]
    factor_impact = compute_factor_impact(data, signals)
    contradictions = detect_cross_desk_contradictions(data, factor_impact)
    assert contradictions == []


def test_no_contradiction_across_unrelated_factors(data):
    """A gold signal and nothing else shouldn't produce any contradiction —
    only one side (headwind on pf_gold) exists for that factor."""
    signals = [{"factor": "gold", "direction": "down"}]
    factor_impact = compute_factor_impact(data, signals)
    contradictions = detect_cross_desk_contradictions(data, factor_impact)
    assert contradictions == []


# --------------------------------------------------------------------------
# compute_scenario_impact (ADVANCED.md #2)
# --------------------------------------------------------------------------

def test_scenario_impact_signs_match_sensitivity(data):
    signals = [{"factor": "interest_rates_india", "direction": "up"}]
    result = compute_scenario_impact(data, signals)
    bank = next(r for r in result if r["portfolio_id"] == "pf_bank")
    bond = next(r for r in result if r["portfolio_id"] == "pf_bond")
    assert bank["bands"]["mild"] > 0  # positive sensitivity, factor up -> positive impact
    assert bond["bands"]["mild"] < 0  # negative sensitivity, factor up -> negative impact


def test_scenario_impact_severity_ordering(data):
    signals = [{"factor": "interest_rates_india", "direction": "up"}]
    result = compute_scenario_impact(data, signals)
    bank = next(r for r in result if r["portfolio_id"] == "pf_bank")
    assert abs(bank["bands"]["mild"]) < abs(bank["bands"]["moderate"]) < abs(bank["bands"]["severe"])


def test_scenario_impact_no_directional_signal_returns_empty(data):
    signals = [{"factor": "interest_rates_india", "direction": "mixed"}]
    assert compute_scenario_impact(data, signals) == []


def test_scenario_impact_empty_signals_returns_empty(data):
    assert compute_scenario_impact(data, []) == []
