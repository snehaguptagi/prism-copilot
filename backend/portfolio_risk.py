"""Shared per-portfolio risk computation.

Used by both the seed dataset generator (build_dataset.py, at build time for
every demo client) and the runtime Add Client endpoint (api.py, when an RM
adds a new client), so a client added at runtime gets a risk tier computed by
the exact same formula as every seeded client. Deterministic, no model.
"""


def compute_portfolio_risk(nav, raw_holdings, sec_by_id):
    """raw_holdings: {security_id: raw_weight}, not necessarily normalized to 1
    (realistic non-round weights are normalized here, same as the seed data).
    Returns (normalized_holdings, market_values, risk):
      normalized_holdings: {security_id: weight}, sums to 1.0
      market_values: {security_id: value}, value = nav * weight
      risk: the same risk block shape stored in data["risk"][portfolio_id]
    """
    raw_total = sum(raw_holdings.values())
    norm_holdings = {sid: w / raw_total for sid, w in raw_holdings.items()}

    asset_mix = {}
    sum_beta = 0.0
    sum_vol = 0.0
    sum_sq_weight = 0.0
    top = (None, 0.0)
    market_values = {}
    for sec_id, weight in norm_holdings.items():
        s = sec_by_id[sec_id]
        market_values[sec_id] = round(nav * weight, 2)
        asset_mix[s["asset_class"]] = asset_mix.get(s["asset_class"], 0.0) + weight * 100
        sum_beta += s["beta"] * weight
        sum_vol += s["vol"] * weight
        sum_sq_weight += weight ** 2
        if weight > top[1]:
            top = (s["name"], weight)

    largest_class = max(asset_mix, key=asset_mix.get)
    est_vol = round(sum_vol, 1)
    eq_hhi = round(sum_sq_weight * 10000, 0)
    # Concentration bump: 1.0x (perfectly diversified) up to 1.5x (single holding).
    concentration_factor = 1 + (eq_hhi / 10000) * 0.5
    risk_score = round(est_vol * concentration_factor, 1)
    # Thresholds tuned to spread books across the full risk ladder rather than
    # bunching most into one tier (see build_dataset.py history for tuning notes).
    if risk_score < 8:
        tier = "Low"
    elif risk_score < 15:
        tier = "Moderate"
    elif risk_score < 20:
        tier = "Elevated"
    elif risk_score < 24:
        tier = "High"
    else:
        tier = "Very High"

    risk = {
        "risk_score": risk_score,
        "risk_tier": tier,
        "est_vol": est_vol,
        "asset_mix": {k: round(v, 1) for k, v in asset_mix.items()},
        "largest_class": largest_class,
        "largest_class_pct": round(asset_mix[largest_class], 1),
        "top1_pct": round(top[1] * 100, 1),
        "top1_name": top[0],
        "eq_hhi": eq_hhi,
        "em_pct": 100.0,  # all-India book; India is classified an emerging market
        "hy_credit_pct": 0.0,  # no sub-investment-grade credit held
        "wtd_beta": round(sum_beta, 2),
        "num_holdings": len(raw_holdings),
    }
    return norm_holdings, market_values, risk
