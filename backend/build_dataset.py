"""
Builds prism_data.json for the India-only MVP: real NSE-listed securities,
8 India portfolios (no US, no crypto), each with a named manager persona,
and a computed risk block per portfolio.

Run:
  python build_dataset.py
"""

import json
import os

from portfolio_risk import compute_portfolio_risk

OUT_PATH = os.path.join(os.path.dirname(__file__), "prism_data.json")

# ---------------------------------------------------------------------------
# Desks
# ---------------------------------------------------------------------------
DESKS = [
    {"desk_id": "desk_equity", "tenant_id": "tnt_001", "name": "Equity Desk"},
    {"desk_id": "desk_income", "tenant_id": "tnt_001", "name": "Fixed Income & Treasury Desk"},
    {"desk_id": "desk_real", "tenant_id": "tnt_001", "name": "Real Assets & Alternatives Desk"},
    {"desk_id": "desk_benchmark", "tenant_id": "tnt_001", "name": "Benchmark (non-desk, reference only)"},
]

# ---------------------------------------------------------------------------
# Securities master — all India-domiciled (country "IN"), no crypto.
# fields match the existing schema exactly so insight_lens.py needs no changes.
# ---------------------------------------------------------------------------
def sec(security_id, ticker, name, aliases, sector, industry, asset_class, instrument_type,
        vol, beta, cap_tier=None, credit_quality=None, parent_id=None, adr_of=None,
        country="IN", isin_suffix=None, factor_sensitivities=None):
    return {
        "security_id": security_id,
        "primary_ticker": ticker,
        "name": name,
        "aliases": aliases,
        "isin": f"ZZ{country}0000{isin_suffix or ticker}1",
        "parent_id": parent_id,
        "adr_of": adr_of,
        "sector": sector,
        "industry": industry,
        "country": country,
        "asset_class": asset_class,
        "instrument_type": instrument_type,
        # Minimal stand-in for the LLD's full sensitivity matrix (§7): explicit,
        # hand-tagged factor -> sign mapping per security, so a macro/commodity
        # event that never names this security by ticker can still be matched
        # to it and given a direction. "same_direction" means the holding's
        # value moves the same way as the reported factor move (e.g. a gold
        # ETF when gold itself moves); "positive"/"negative" means the factor
        # moving up is good/bad for this holding.
        "factor_sensitivities": factor_sensitivities or {},
        "vol": vol,
        "beta": beta,
        "cap_tier": cap_tier,
        "credit_quality": credit_quality,
    }

SECURITIES = [
    # Cash & short-term debt
    # Ticker/aliases deliberately avoid the bare word "cash" — it's a common
    # English word (e.g. "cash burn" in unrelated articles) and produced a
    # real false-positive link via plain word-boundary matching.
    sec("sec_cash_inr", "INRCASH", "INR Cash & Equivalents", ["Money Market Cash"],
        "Cash", "Cash & Equivalents", "Cash", "Cash", 0.3, 0.0, credit_quality="Govt"),
    sec("sec_tbill_91d", "TBILL91", "GoI 91-Day Treasury Bill", ["T-Bill", "Treasury Bill", "91-day T-bill"],
        "Fixed Income", "Treasury Bill", "Fixed Income", "T-Bill", 0.5, 0.0, credit_quality="Govt"),
    sec("sec_liquid_fund", "ICICILIQ", "ICICI Prudential Liquid Fund", ["ICICI Liquid Fund", "Liquid Fund"],
        "Fixed Income", "Liquid Fund", "Fixed Income", "Mutual Fund", 0.6, 0.0, credit_quality="AAA"),
    sec("sec_gsec_10y", "GSEC10Y", "GoI 10-Year Government Security", ["10-Year G-Sec", "GoI 10Y", "G-Sec"],
        "Fixed Income", "Government Bond", "Fixed Income", "Government Bond", 4.5, 0.0, credit_quality="Govt",
        factor_sensitivities={"interest_rates_india": "negative"}),
    sec("sec_gsec_5y", "GSEC5Y", "GoI 5-Year Government Security", ["5-Year G-Sec", "GoI 5Y"],
        "Fixed Income", "Government Bond", "Fixed Income", "Government Bond", 3.0, 0.0, credit_quality="Govt",
        factor_sensitivities={"interest_rates_india": "negative"}),
    sec("sec_corp_bond_aaa", "HDFCAAA", "HDFC AAA Corporate Bond Fund", ["HDFC Corporate Bond Fund", "AAA Bond Fund"],
        "Fixed Income", "Corporate Bond Fund", "Fixed Income", "Mutual Fund", 3.8, 0.0, credit_quality="AAA",
        factor_sensitivities={"interest_rates_india": "negative"}),
    sec("sec_psu_bond", "SBIPSU", "SBI PSU Bond Fund", ["PSU Bond Fund", "SBI PSU"],
        "Fixed Income", "PSU Bond Fund", "Fixed Income", "Mutual Fund", 4.2, 0.0, credit_quality="AA+",
        factor_sensitivities={"interest_rates_india": "negative"}),

    # Large-cap equity
    sec("sec_reliance", "RELIANCE", "Reliance Industries Ltd", ["Reliance", "RIL", "Reliance Industries"],
        "Energy", "Refining, Petrochemicals, Retail & Telecom", "Equity", "Single Stock", 22.0, 1.0, cap_tier="large",
        factor_sensitivities={"oil": "positive"}),
    sec("sec_hdfcbank", "HDFCBANK", "HDFC Bank Ltd", ["HDFC Bank"],
        "Financials", "Private Sector Bank", "Equity", "Single Stock", 20.0, 1.05, cap_tier="large",
        factor_sensitivities={"interest_rates_india": "positive"}),
    sec("sec_icicibank", "ICICIBANK", "ICICI Bank Ltd", ["ICICI Bank"],
        "Financials", "Private Sector Bank", "Equity", "Single Stock", 21.0, 1.1, cap_tier="large",
        factor_sensitivities={"interest_rates_india": "positive"}),
    sec("sec_kotakbank", "KOTAKBANK", "Kotak Mahindra Bank Ltd", ["Kotak Mahindra Bank", "Kotak Bank"],
        "Financials", "Private Sector Bank", "Equity", "Single Stock", 20.0, 1.0, cap_tier="large",
        factor_sensitivities={"interest_rates_india": "positive"}),
    sec("sec_sbin", "SBIN", "State Bank of India", ["State Bank of India", "SBI"],
        "Financials", "Public Sector Bank", "Equity", "Single Stock", 24.0, 1.2, cap_tier="large",
        factor_sensitivities={"interest_rates_india": "positive"}),
    sec("sec_bajfinance", "BAJFINANCE", "Bajaj Finance Ltd", ["Bajaj Finance"],
        "Financials", "NBFC", "Equity", "Single Stock", 28.0, 1.3, cap_tier="large"),
    sec("sec_jiofin", "JIOFIN", "Jio Financial Services Ltd", ["Jio Financial Services", "Jio Financial"],
        "Financials", "NBFC", "Equity", "Single Stock", 26.0, 1.15, cap_tier="large", parent_id="sec_reliance"),
    sec("sec_infosys", "INFY", "Infosys Ltd", ["Infosys"],
        "Information Technology", "IT Services", "Equity", "Single Stock", 19.0, 0.9, cap_tier="large",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_infosys_adr", "INFY", "Infosys Ltd (ADR)", ["Infosys ADR"],
        "Information Technology", "IT Services", "Equity", "Single Stock", 19.0, 0.9, cap_tier="large",
        adr_of="sec_infosys", isin_suffix="INFYADR", factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_tcs", "TCS", "Tata Consultancy Services Ltd", ["TCS", "Tata Consultancy Services"],
        "Information Technology", "IT Services", "Equity", "Single Stock", 17.0, 0.85, cap_tier="large",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_wipro", "WIPRO", "Wipro Ltd", ["Wipro"],
        "Information Technology", "IT Services", "Equity", "Single Stock", 20.0, 0.95, cap_tier="large",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_hcltech", "HCLTECH", "HCL Technologies Ltd", ["HCL Technologies", "HCLTech", "HCL Tech"],
        "Information Technology", "IT Services", "Equity", "Single Stock", 19.0, 0.9, cap_tier="large",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_techm", "TECHM", "Tech Mahindra Ltd", ["Tech Mahindra"],
        "Information Technology", "IT Services", "Equity", "Single Stock", 22.0, 1.0, cap_tier="large",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_ltim", "LTIM", "LTIMindtree Ltd", ["LTIMindtree"],
        "Information Technology", "IT Services", "Equity", "Single Stock", 23.0, 1.05, cap_tier="large",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_lt", "LT", "Larsen & Toubro Ltd", ["Larsen & Toubro", "L&T"],
        "Industrials", "Engineering & Construction", "Equity", "Single Stock", 24.0, 1.15, cap_tier="large"),
    sec("sec_bhartiartl", "BHARTIARTL", "Bharti Airtel Ltd", ["Bharti Airtel", "Airtel"],
        "Communication Services", "Telecom", "Equity", "Single Stock", 20.0, 0.9, cap_tier="large"),
    sec("sec_itc", "ITC", "ITC Ltd", ["ITC"],
        "Consumer Staples", "FMCG & Tobacco", "Equity", "Single Stock", 15.0, 0.6, cap_tier="large"),
    sec("sec_asianpaint", "ASIANPAINT", "Asian Paints Ltd", ["Asian Paints"],
        "Materials", "Paints", "Equity", "Single Stock", 18.0, 0.8, cap_tier="large"),
    sec("sec_titan", "TITAN", "Titan Company Ltd", ["Titan Company", "Titan"],
        "Consumer Discretionary", "Jewellery & Watches", "Equity", "Single Stock", 21.0, 1.0, cap_tier="large"),
    sec("sec_sunpharma", "SUNPHARMA", "Sun Pharmaceutical Industries Ltd", ["Sun Pharma", "Sun Pharmaceutical"],
        "Health Care", "Pharmaceuticals", "Equity", "Single Stock", 17.0, 0.7, cap_tier="large"),

    # Additional Nifty 50 constituents (breadth for the index / large-cap books)
    sec("sec_axisbank", "AXISBANK", "Axis Bank Ltd", ["Axis Bank"],
        "Financials", "Private Sector Bank", "Equity", "Single Stock", 23.0, 1.15, cap_tier="large",
        factor_sensitivities={"interest_rates_india": "positive"}),
    sec("sec_bajajfinsv", "BAJAJFINSV", "Bajaj Finserv Ltd", ["Bajaj Finserv"],
        "Financials", "Financial Services", "Equity", "Single Stock", 26.0, 1.2, cap_tier="large",
        factor_sensitivities={"interest_rates_india": "positive"}),
    sec("sec_hdfclife", "HDFCLIFE", "HDFC Life Insurance Co Ltd", ["HDFC Life"],
        "Financials", "Life Insurance", "Equity", "Single Stock", 21.0, 0.85, cap_tier="large"),
    sec("sec_sbilife", "SBILIFE", "SBI Life Insurance Co Ltd", ["SBI Life"],
        "Financials", "Life Insurance", "Equity", "Single Stock", 21.0, 0.85, cap_tier="large"),
    sec("sec_shriramfin", "SHRIRAMFIN", "Shriram Finance Ltd", ["Shriram Finance"],
        "Financials", "NBFC", "Equity", "Single Stock", 27.0, 1.25, cap_tier="large"),
    sec("sec_maruti", "MARUTI", "Maruti Suzuki India Ltd", ["Maruti", "Maruti Suzuki"],
        "Consumer Discretionary", "Automobiles", "Equity", "Single Stock", 22.0, 0.95, cap_tier="large"),
    sec("sec_mm", "M&M", "Mahindra & Mahindra Ltd", ["Mahindra & Mahindra", "M and M"],
        "Consumer Discretionary", "Automobiles", "Equity", "Single Stock", 24.0, 1.1, cap_tier="large"),
    sec("sec_tatamotors", "TATAMOTORS", "Tata Motors Ltd", ["Tata Motors"],
        "Consumer Discretionary", "Automobiles", "Equity", "Single Stock", 30.0, 1.35, cap_tier="large"),
    sec("sec_eichermot", "EICHERMOT", "Eicher Motors Ltd", ["Eicher Motors", "Eicher"],
        "Consumer Discretionary", "Automobiles", "Equity", "Single Stock", 25.0, 1.05, cap_tier="large"),
    sec("sec_herohonda", "HEROMOTOCO", "Hero MotoCorp Ltd", ["Hero MotoCorp", "Hero Honda"],
        "Consumer Discretionary", "Two-Wheelers", "Equity", "Single Stock", 24.0, 0.95, cap_tier="large"),
    sec("sec_bajajauto", "BAJAJ-AUTO", "Bajaj Auto Ltd", ["Bajaj Auto"],
        "Consumer Discretionary", "Two-Wheelers", "Equity", "Single Stock", 23.0, 0.9, cap_tier="large"),
    sec("sec_hindunilvr", "HINDUNILVR", "Hindustan Unilever Ltd", ["Hindustan Unilever", "HUL"],
        "Consumer Staples", "FMCG", "Equity", "Single Stock", 15.0, 0.5, cap_tier="large"),
    sec("sec_nestle", "NESTLEIND", "Nestle India Ltd", ["Nestle India", "Nestle"],
        "Consumer Staples", "FMCG", "Equity", "Single Stock", 15.0, 0.5, cap_tier="large"),
    sec("sec_britannia", "BRITANNIA", "Britannia Industries Ltd", ["Britannia"],
        "Consumer Staples", "FMCG", "Equity", "Single Stock", 17.0, 0.6, cap_tier="large"),
    sec("sec_tataconsum", "TATACONSUM", "Tata Consumer Products Ltd", ["Tata Consumer"],
        "Consumer Staples", "FMCG", "Equity", "Single Stock", 19.0, 0.7, cap_tier="large"),
    sec("sec_ntpc", "NTPC", "NTPC Ltd", ["NTPC"],
        "Utilities", "Power Generation", "Equity", "Single Stock", 20.0, 0.9, cap_tier="large",
        factor_sensitivities={"interest_rates_india": "negative"}),
    sec("sec_powergrid", "POWERGRID", "Power Grid Corp of India Ltd", ["Power Grid", "PowerGrid"],
        "Utilities", "Power Transmission", "Equity", "Single Stock", 18.0, 0.75, cap_tier="large",
        factor_sensitivities={"interest_rates_india": "negative"}),
    sec("sec_ongc", "ONGC", "Oil & Natural Gas Corp Ltd", ["ONGC", "Oil and Natural Gas"],
        "Energy", "Oil & Gas Exploration", "Equity", "Single Stock", 26.0, 1.1, cap_tier="large",
        factor_sensitivities={"oil": "positive"}),
    sec("sec_bpcl", "BPCL", "Bharat Petroleum Corp Ltd", ["BPCL", "Bharat Petroleum"],
        "Energy", "Oil Refining & Marketing", "Equity", "Single Stock", 27.0, 1.05, cap_tier="large",
        factor_sensitivities={"oil": "negative"}),
    sec("sec_coalindia", "COALINDIA", "Coal India Ltd", ["Coal India"],
        "Energy", "Coal Mining", "Equity", "Single Stock", 25.0, 0.95, cap_tier="large"),
    sec("sec_tatasteel", "TATASTEEL", "Tata Steel Ltd", ["Tata Steel"],
        "Materials", "Steel", "Equity", "Single Stock", 32.0, 1.4, cap_tier="large"),
    sec("sec_jswsteel", "JSWSTEEL", "JSW Steel Ltd", ["JSW Steel"],
        "Materials", "Steel", "Equity", "Single Stock", 30.0, 1.3, cap_tier="large"),
    sec("sec_hindalco", "HINDALCO", "Hindalco Industries Ltd", ["Hindalco"],
        "Materials", "Aluminium & Metals", "Equity", "Single Stock", 31.0, 1.35, cap_tier="large"),
    sec("sec_ultracemco", "ULTRACEMCO", "UltraTech Cement Ltd", ["UltraTech Cement", "UltraTech"],
        "Materials", "Cement", "Equity", "Single Stock", 22.0, 1.0, cap_tier="large"),
    sec("sec_grasim", "GRASIM", "Grasim Industries Ltd", ["Grasim"],
        "Materials", "Cement & Diversified", "Equity", "Single Stock", 23.0, 1.05, cap_tier="large"),
    sec("sec_drreddy", "DRREDDY", "Dr Reddy's Laboratories Ltd", ["Dr Reddy's", "Dr Reddy", "DRL"],
        "Health Care", "Pharmaceuticals", "Equity", "Single Stock", 20.0, 0.7, cap_tier="large",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_cipla", "CIPLA", "Cipla Ltd", ["Cipla"],
        "Health Care", "Pharmaceuticals", "Equity", "Single Stock", 19.0, 0.7, cap_tier="large",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_apollohosp", "APOLLOHOSP", "Apollo Hospitals Enterprise Ltd", ["Apollo Hospitals", "Apollo"],
        "Health Care", "Healthcare Services", "Equity", "Single Stock", 25.0, 1.0, cap_tier="large"),
    sec("sec_adanient", "ADANIENT", "Adani Enterprises Ltd", ["Adani Enterprises"],
        "Industrials", "Diversified / Incubator", "Equity", "Single Stock", 38.0, 1.5, cap_tier="large"),
    sec("sec_adaniports", "ADANIPORTS", "Adani Ports & SEZ Ltd", ["Adani Ports", "APSEZ"],
        "Industrials", "Ports & Logistics", "Equity", "Single Stock", 30.0, 1.3, cap_tier="large"),
    sec("sec_trent", "TRENT", "Trent Ltd", ["Trent"],
        "Consumer Discretionary", "Retail", "Equity", "Single Stock", 33.0, 1.25, cap_tier="large"),
    sec("sec_bel", "BEL", "Bharat Electronics Ltd", ["Bharat Electronics", "BEL"],
        "Industrials", "Defence Electronics", "Equity", "Single Stock", 30.0, 1.15, cap_tier="large"),

    # Small / midcap equity
    sec("sec_persistent", "PERSISTENT", "Persistent Systems Ltd", ["Persistent Systems"],
        "Information Technology", "IT Services", "Equity", "Single Stock", 32.0, 1.2, cap_tier="mid",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_coforge", "COFORGE", "Coforge Ltd", ["Coforge"],
        "Information Technology", "IT Services", "Equity", "Single Stock", 34.0, 1.25, cap_tier="mid",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_kpit", "KPITTECH", "KPIT Technologies Ltd", ["KPIT Technologies", "KPIT"],
        "Information Technology", "Auto-tech / Engineering R&D", "Equity", "Single Stock", 35.0, 1.3, cap_tier="mid",
        factor_sensitivities={"usd_inr": "positive"}),
    sec("sec_dixon", "DIXON", "Dixon Technologies Ltd", ["Dixon Technologies", "Dixon"],
        "Industrials", "Electronics Manufacturing Services", "Equity", "Single Stock", 40.0, 1.4, cap_tier="mid"),
    sec("sec_cumminsind", "CUMMINSIND", "Cummins India Ltd", ["Cummins India"],
        "Industrials", "Industrial Engines & Equipment", "Equity", "Single Stock", 26.0, 1.1, cap_tier="mid"),
    sec("sec_voltas", "VOLTAS", "Voltas Ltd", ["Voltas"],
        "Consumer Discretionary", "Air Conditioning & Engineering", "Equity", "Single Stock", 28.0, 1.2, cap_tier="mid"),

    # Gold
    sec("sec_gold_etf", "GOLDBEES", "Nippon India Gold ETF", ["Gold ETF", "Gold BeES", "GoldBeES"],
        "Commodity", "Gold ETF", "Commodity", "ETF", 13.0, 0.0,
        factor_sensitivities={"gold": "same_direction"}),
    sec("sec_sgb", "SGB", "Sovereign Gold Bond (RBI)", ["Sovereign Gold Bond", "SGB"],
        "Commodity", "Gold-linked Government Bond", "Commodity", "Government Bond", 12.5, 0.0, credit_quality="Govt",
        factor_sensitivities={"gold": "same_direction"}),

    # REITs
    sec("sec_embassy_reit", "EMBASSY", "Embassy Office Parks REIT", ["Embassy REIT", "Embassy Office Parks"],
        "Real Estate", "Office REIT", "Real Estate", "REIT", 16.0, 0.6),
    sec("sec_mindspace_reit", "MINDSPACE", "Mindspace Business Parks REIT", ["Mindspace REIT", "Mindspace Business Parks"],
        "Real Estate", "Office REIT", "Real Estate", "REIT", 15.0, 0.55),

    # Diversified equity mutual funds. A realistic RM shelf leans heavily on
    # these rather than only single stocks, spanning the full cap spectrum.
    sec("sec_mf_largecap", "MIRAELCF", "Mirae Asset Large Cap Fund", ["Mirae Large Cap Fund", "Mirae Asset Large Cap"],
        "Diversified Equity", "Large Cap Fund", "Equity", "Mutual Fund", 16.0, 0.95, cap_tier="large"),
    sec("sec_mf_flexicap", "PPFCF", "Parag Parikh Flexi Cap Fund", ["Parag Parikh Flexi Cap", "PPFAS Flexi Cap"],
        "Diversified Equity", "Flexi Cap Fund", "Equity", "Mutual Fund", 17.5, 0.9, cap_tier="large"),
    sec("sec_mf_midcap", "KOTAKEEF", "Kotak Emerging Equity Fund", ["Kotak Emerging Equity", "Kotak Mid Cap Fund"],
        "Diversified Equity", "Mid Cap Fund", "Equity", "Mutual Fund", 21.0, 1.0, cap_tier="mid"),
    sec("sec_mf_smallcap", "SBISCF", "SBI Small Cap Fund", ["SBI Small Cap"],
        "Diversified Equity", "Small Cap Fund", "Equity", "Mutual Fund", 26.0, 1.1, cap_tier="small"),

    # More fixed income: duration and credit variety beyond the existing AAA
    # corporate bond fund and PSU bond fund, so the shelf isn't gold-plated-only.
    sec("sec_mf_shortterm", "AXISSTF", "Axis Short Term Fund", ["Axis Short Term Fund", "Axis Short Duration Fund"],
        "Fixed Income", "Short Duration Fund", "Fixed Income", "Mutual Fund", 1.5, 0.0, credit_quality="AAA",
        factor_sensitivities={"interest_rates_india": "negative"}),
    sec("sec_mf_gilt", "SBIGILT", "SBI Magnum Gilt Fund", ["SBI Magnum Gilt Fund", "SBI Gilt Fund"],
        "Fixed Income", "Gilt Fund", "Fixed Income", "Mutual Fund", 5.5, 0.0, credit_quality="Govt",
        factor_sensitivities={"interest_rates_india": "negative"}),
    sec("sec_mf_dynamicbond", "ICICIASB", "ICICI Prudential All Seasons Bond Fund", ["ICICI All Seasons Bond Fund", "ICICI Prudential Dynamic Bond"],
        "Fixed Income", "Dynamic Bond Fund", "Fixed Income", "Mutual Fund", 3.0, 0.0, credit_quality="AA+",
        factor_sensitivities={"interest_rates_india": "negative"}),
    sec("sec_mf_creditrisk", "ABSLCRF", "Aditya Birla Sun Life Credit Risk Fund", ["Aditya Birla Credit Risk Fund", "ABSL Credit Risk Fund"],
        "Fixed Income", "Credit Risk Fund", "Fixed Income", "Mutual Fund", 4.5, 0.0, credit_quality="A+",
        factor_sensitivities={"interest_rates_india": "negative"}),
    sec("sec_corp_bond_aa", "RECAABOND", "REC Ltd AA Bond", ["REC Bond", "Rural Electrification Corporation Bond"],
        "Fixed Income", "Corporate Bond", "Fixed Income", "Corporate Bond", 4.0, 0.0, credit_quality="AA",
        factor_sensitivities={"interest_rates_india": "negative"}),

    # Second commodity sleeve, so it isn't gold-only.
    sec("sec_silver_etf", "SILVERBEES", "Nippon India Silver ETF", ["Silver ETF", "SilverBeES"],
        "Commodity", "Silver ETF", "Commodity", "ETF", 18.0, 0.0,
        factor_sensitivities={"gold": "same_direction"}),

    # Hybrid (balanced) funds, extremely common on a real RM shelf, blending
    # equity and debt in one product; absent from the shelf until now.
    sec("sec_mf_bafund", "ICICIBAF", "ICICI Prudential Balanced Advantage Fund", ["ICICI Balanced Advantage Fund", "ICICI BAF"],
        "Multi-Asset", "Balanced Advantage Fund", "Hybrid", "Mutual Fund", 9.0, 0.5),
    sec("sec_mf_hybrid", "HDFCHEF", "HDFC Hybrid Equity Fund", ["HDFC Hybrid Equity", "HDFC Balanced Fund"],
        "Multi-Asset", "Aggressive Hybrid Fund", "Hybrid", "Mutual Fund", 12.0, 0.65),
]

SEC_BY_ID = {s["security_id"]: s for s in SECURITIES}

# ---------------------------------------------------------------------------
# Portfolios — 12 India-only individual-client portfolios (HNI accounts, sized
# realistically from ~₹38 lakh to ~₹13.5 crore), plus one reference benchmark.
# ---------------------------------------------------------------------------
PORTFOLIOS = [
    {
        "portfolio_id": "pf_cap_preservation", "desk_id": "desk_income",
        "name": "Capital Preservation Portfolio", "base_ccy": "INR",
        "risk_driver": "Cash & short-term rates",
        "mandate": "Park capital with near-zero drawdown in T-bills, liquid funds, and cash. Return of capital before return on capital.",
        "manager_name": "Kavita Iyer",
        "manager_bio": "18 years managing liquid and ultra-short debt funds. Prioritizes capital safety over yield, even at the cost of underperforming in rallies.",
        "nav": 13_500_000,
        "holdings": {"sec_tbill_91d": 0.55, "sec_liquid_fund": 0.35, "sec_cash_inr": 0.10},
        "client": {
            "name": "Meena Iyer", "age": 68, "occupation": "Retired schoolteacher",
            "persona": "Retired, living off savings and a small pension. Capital safety is non-negotiable — this money has to cover medical expenses, not chase returns. Checks her balance once a month, gets anxious about anything volatile.",
            "email": "meena.iyer68@gmail.com", "phone": "+91 98200 11234", "city": "Pune",
            "relationship_since": "2019-03-14", "aum_fee_pct": 0.5, "risk_mandate": "Conservative",
        },
    },
    {
        "portfolio_id": "pf_bond_ladder", "desk_id": "desk_income",
        "name": "Government & Corporate Bond Ladder", "base_ccy": "INR",
        "risk_driver": "Interest rate & credit duration",
        "mandate": "Laddered exposure across GoI securities and high-grade corporate bonds for steady income with controlled duration risk.",
        "manager_name": "Rohan Deshpande",
        "manager_bio": "Fixed-income specialist who watches RBI policy meetings closely. Wary of duration risk if rates stay higher for longer.",
        "nav": 9_200_000,
        "holdings": {"sec_gsec_10y": 0.30, "sec_gsec_5y": 0.25, "sec_corp_bond_aaa": 0.25,
                     "sec_psu_bond": 0.15, "sec_cash_inr": 0.05},
        "client": {
            "name": "Suresh Nair", "age": 45, "occupation": "Branch manager, private sector bank",
            "persona": "Salaried, steady 9-to-5, no time or appetite to track markets daily. Investing specifically to fund his daughter's wedding in ~3 years — wants predictable income, not surprises. Reviews his statement quarterly.",
            "email": "suresh.nair45@yahoo.in", "phone": "+91 98450 22987", "city": "Kochi",
            "relationship_since": "2021-06-02", "aum_fee_pct": 0.75, "risk_mandate": "Conservative-Moderate",
        },
    },
    {
        "portfolio_id": "pf_largecap_growth", "desk_id": "desk_equity",
        "name": "Large-Cap Equity Growth Portfolio", "base_ccy": "INR",
        "risk_driver": "Broad market beta, large-cap concentration",
        "mandate": "Core Nifty-heavyweight exposure across financials, energy, IT, and consumer names for long-term capital growth.",
        "manager_name": "Aarav Mehta",
        "manager_bio": "Bullish on capex-led industrials and financials, cautious on IT services margins given global client budget pressure.",
        "nav": 26_000_000,
        # Active large-cap fund: ~22 names, overweight financials and capex vs
        # the index, underweight IT, with conviction-sized but non-round weights.
        "holdings": {
            "sec_hdfcbank": 9.4, "sec_icicibank": 8.1, "sec_reliance": 7.2, "sec_lt": 6.3, "sec_axisbank": 5.1,
            "sec_infosys": 4.8, "sec_bhartiartl": 4.6, "sec_sbin": 4.4, "sec_tcs": 4.1, "sec_mm": 3.9,
            "sec_bajfinance": 3.7, "sec_ultracemco": 3.4, "sec_maruti": 3.2, "sec_ntpc": 3.1, "sec_titan": 2.9,
            "sec_sunpharma": 2.8, "sec_hindunilvr": 2.7, "sec_bel": 2.6, "sec_adaniports": 2.4, "sec_trent": 2.3,
            "sec_hcltech": 2.1, "sec_asianpaint": 1.9,
        },
        "client": {
            "name": "Priya Sharma", "age": 34, "occupation": "Senior product manager, tech company",
            "persona": "Full-time job with a demanding schedule — investing is entirely hands-off by design. Wants a diversified, long-term core holding she can forget about for years, not something she has to actively manage alongside her career.",
            "email": "priya.sharma34@outlook.com", "phone": "+91 99870 45611", "city": "Bengaluru",
            "relationship_since": "2020-11-20", "aum_fee_pct": 1.0, "risk_mandate": "Moderate-Growth",
        },
    },
    {
        "portfolio_id": "pf_banking_financials", "desk_id": "desk_equity",
        "name": "Banking & Financials Concentrated Portfolio", "base_ccy": "INR",
        "risk_driver": "Financial-sector concentration, credit cycle & NIM sensitivity",
        "mandate": "High-conviction, concentrated bets on India's private and public banks plus leading NBFCs.",
        "manager_name": "Meera Nair",
        "manager_bio": "Former credit analyst, deliberately concentrated. Believes India's private banks are underappreciated versus global peers.",
        "nav": 135_000_000,
        "holdings": {"sec_hdfcbank": 21.4, "sec_icicibank": 19.6, "sec_axisbank": 12.8,
                     "sec_kotakbank": 11.2, "sec_sbin": 10.7, "sec_bajfinance": 9.3,
                     "sec_bajajfinsv": 7.6, "sec_jiofin": 4.2, "sec_shriramfin": 3.2},
        "client": {
            "name": "Vikram Oberoi", "age": 52, "occupation": "Ex-banker, now angel investor",
            "persona": "Spent 20 years in banking before retiring to angel-invest full time. Has strong, informed conviction that Indian private banks are underpriced and explicitly wants concentrated exposure, not a diversified index-hugger. Pushes back if the book gets too diluted.",
            "email": "v.oberoi.investments@gmail.com", "phone": "+91 98200 77341", "city": "Mumbai",
            "relationship_since": "2018-01-09", "aum_fee_pct": 1.25, "risk_mandate": "Aggressive-Concentrated",
        },
    },
    {
        "portfolio_id": "pf_it_services", "desk_id": "desk_equity",
        "name": "IT & Technology Services Portfolio", "base_ccy": "INR",
        "risk_driver": "Export/currency sensitivity, US & EU client discretionary IT spend",
        "mandate": "Concentrated exposure to India's IT services exporters; returns depend heavily on US/EU enterprise tech budgets and INR/USD movement.",
        "manager_name": "Vikram Rao",
        "manager_bio": "Ex-IT-sector research analyst. Watches US mega-cap tech earnings closely, since client-budget commentary from firms like Microsoft foreshadows Indian IT services demand.",
        "nav": 15_500_000,
        "holdings": {"sec_tcs": 24.3, "sec_infosys": 21.7, "sec_hcltech": 15.2,
                     "sec_wipro": 11.4, "sec_techm": 10.6, "sec_ltim": 9.1, "sec_coforge": 7.7},
        "client": {
            "name": "Rohan Mehta", "age": 29, "occupation": "Software engineer, US-based MNC (Bengaluru office)",
            "persona": "Deliberately invests only in what he understands — IT services — because he lives it day to day and reads every earnings call transcript for fun. Confident, opinionated, wants a research partner who can keep up, not simplify things for him.",
            "email": "rohan.mehta.dev@gmail.com", "phone": "+91 90080 33456", "city": "Bengaluru",
            "relationship_since": "2022-08-15", "aum_fee_pct": 1.0, "risk_mandate": "Growth-Concentrated",
        },
    },
    {
        "portfolio_id": "pf_gold_hedge", "desk_id": "desk_real",
        "name": "Gold & Inflation Hedge Portfolio", "base_ccy": "INR",
        "risk_driver": "Real rates, inflation, INR depreciation",
        "mandate": "Physical-gold-linked exposure via ETFs and Sovereign Gold Bonds, held as a portfolio-level inflation and currency hedge.",
        "manager_name": "Ananya Krishnan",
        "manager_bio": "Manages the firm's only non-equity, non-debt sleeve. Treats the gold allocation as insurance, not a return driver.",
        "nav": 54_000_000,
        "holdings": {"sec_gold_etf": 0.55, "sec_sgb": 0.35, "sec_cash_inr": 0.10},
        "client": {
            "name": "Kamala Devi", "age": 58, "occupation": "Homemaker",
            "persona": "Manages the family's wealth the way her mother did — gold has always been the trusted store of value, not an asset class to be argued about. Came to this account through her son, still prefers a phone call over an app. Deeply inflation-conscious from having lived through past rupee depreciation.",
            "email": "kamala.devi.family@gmail.com", "phone": "+91 98450 66120", "city": "Chennai",
            "relationship_since": "2017-05-30", "aum_fee_pct": 0.6, "risk_mandate": "Conservative",
        },
    },
    {
        "portfolio_id": "pf_smallcap_value", "desk_id": "desk_equity",
        "name": "Small & Midcap Value Portfolio", "base_ccy": "INR",
        "risk_driver": "Small/midcap liquidity & earnings volatility",
        "mandate": "Higher-risk, higher-reward bets on midcap IT, industrials, and engineering names below the large-cap universe.",
        "manager_name": "Devika Menon",
        "manager_bio": "Youngest PM on the desk, explicitly mandated to take more risk than the rest of the book for higher return potential.",
        "nav": 3_800_000,
        "holdings": {"sec_dixon": 19.2, "sec_persistent": 17.6, "sec_kpit": 16.3,
                     "sec_coforge": 15.1, "sec_cumminsind": 16.8, "sec_voltas": 15.0},
        "client": {
            "name": "Arjun Verma", "age": 22, "occupation": "Full-time trader (college dropout)",
            "persona": "Dropped out of college to trade markets full time, against his family's wishes — this account is effectively his career, not a side hobby. High risk appetite by choice, checks prices multiple times a day, wants a portfolio that can compound aggressively while he's young enough to absorb the swings.",
            "email": "arjunv.trades@gmail.com", "phone": "+91 89390 12873", "city": "Indore",
            "relationship_since": "2023-02-11", "aum_fee_pct": 1.5, "risk_mandate": "Aggressive",
        },
    },
    {
        "portfolio_id": "pf_reit_income", "desk_id": "desk_real",
        "name": "Real Estate & REIT Income Portfolio", "base_ccy": "INR",
        "risk_driver": "Office real estate demand, rate sensitivity via yield competition",
        "mandate": "Income-focused exposure to listed Indian REITs (office/commercial real estate) for stable distributions.",
        "manager_name": "Sanjay Bhatt",
        "manager_bio": "Real-assets specialist. Watches commercial office leasing and vacancy trends closely, since REIT yields compete directly with bond yields.",
        "nav": 31_000_000,
        "holdings": {"sec_embassy_reit": 0.60, "sec_mindspace_reit": 0.40},
        "client": {
            "name": "Deepak & Ritu Kapoor", "age": 41, "occupation": "Dual-income couple (marketing exec + doctor)",
            "persona": "Two demanding careers, no time to be landlords. Always liked the idea of rental income from commercial property but didn't want the hassle of actually owning and managing real estate — REITs were pitched to them as exactly that, minus the tenants and repairs.",
            "email": "kapoor.household@gmail.com", "phone": "+91 97690 55210", "city": "Gurugram",
            "relationship_since": "2022-04-03", "aum_fee_pct": 0.9, "risk_mandate": "Moderate-Income",
        },
    },
    {
        "portfolio_id": "pf_nifty_index", "desk_id": "desk_equity",
        "name": "Nifty 50 Index Portfolio", "base_ccy": "INR",
        "risk_driver": "Broad market beta, no active stock selection",
        "mandate": "Passive, broadly diversified exposure across large-cap India equity at index-like weights. No concentrated bets, no active selection — designed to track the market, not beat it.",
        "manager_name": "Ishaan Kapoor",
        "manager_bio": "Runs the passive sleeve. Believes most active managers don't beat the index after fees, and built this fund to prove it.",
        "nav": 10_500_000,
        # ~49 Nifty 50 constituents at approximate real index weights (raw,
        # normalized at build time). HDFC Bank is the largest post-merger, then
        # Reliance and ICICI; a genuine long tail below the megacaps.
        "holdings": {
            "sec_hdfcbank": 13.1, "sec_reliance": 8.5, "sec_icicibank": 8.3, "sec_infosys": 5.6,
            "sec_itc": 4.1, "sec_tcs": 4.0, "sec_lt": 3.9, "sec_bhartiartl": 3.4, "sec_axisbank": 3.1,
            "sec_kotakbank": 2.9, "sec_sbin": 2.8, "sec_mm": 2.3, "sec_bajfinance": 2.3, "sec_hindunilvr": 2.2,
            "sec_maruti": 2.0, "sec_tatamotors": 1.9, "sec_sunpharma": 1.8, "sec_ntpc": 1.7, "sec_hcltech": 1.6,
            "sec_titan": 1.4, "sec_ultracemco": 1.3, "sec_powergrid": 1.3, "sec_tatasteel": 1.3, "sec_asianpaint": 1.2,
            "sec_bajajfinsv": 1.2, "sec_nestle": 1.1, "sec_adaniports": 1.1, "sec_coalindia": 1.1, "sec_hindalco": 1.0,
            "sec_grasim": 1.0, "sec_hdfclife": 1.0, "sec_jswsteel": 1.0, "sec_techm": 1.0, "sec_ongc": 0.9,
            "sec_sbilife": 0.9, "sec_wipro": 0.9, "sec_trent": 0.9, "sec_bel": 0.9, "sec_adanient": 0.9,
            "sec_bajajauto": 0.8, "sec_drreddy": 0.8, "sec_cipla": 0.8, "sec_shriramfin": 0.8, "sec_apollohosp": 0.7,
            "sec_britannia": 0.7, "sec_eichermot": 0.7, "sec_tataconsum": 0.7, "sec_herohonda": 0.6, "sec_bpcl": 0.6,
        },
        "client": {
            "name": "Kabir Anand", "age": 31, "occupation": "Data scientist",
            "persona": "Read enough about index investing to become mildly evangelical about it. Explicitly does not want to pay for active stock-picking he doesn't believe beats the market after fees — wants the broad India growth story, nothing more, nothing less. The most hands-off, lowest-maintenance client on the book.",
            "email": "kabir.anand.ds@gmail.com", "phone": "+91 91234 55667", "city": "Hyderabad",
            "relationship_since": "2023-09-01", "aum_fee_pct": 0.3, "risk_mandate": "Moderate-Passive",
        },
    },
    {
        "portfolio_id": "pf_balanced_hybrid", "desk_id": "desk_equity",
        "name": "Balanced Advantage Hybrid Portfolio", "base_ccy": "INR",
        "risk_driver": "Blended equity/debt allocation, moderate volatility by design",
        "mandate": "A single all-weather blend of large-cap equity and high-grade debt, roughly 65/35, designed so the client never has to think about rebalancing between asset classes themselves.",
        "manager_name": "Farah Sheikh",
        "manager_bio": "Manages the firm's all-weather blended fund. Rebalances mechanically on a schedule, not on emotion or market calls.",
        "nav": 18_500_000,
        "holdings": {"sec_corp_bond_aaa": 19.6, "sec_gsec_10y": 15.4, "sec_hdfcbank": 12.3,
                     "sec_reliance": 9.8, "sec_icicibank": 8.1, "sec_infosys": 7.4, "sec_lt": 6.9,
                     "sec_tcs": 6.2, "sec_hindunilvr": 4.8, "sec_gsec_5y": 9.5},
        "client": {
            "name": "Neha Kulkarni", "age": 38, "occupation": "Small business owner (boutique retail)",
            "persona": "Runs her own store and already has enough decisions to make in a day. Explicitly asked for 'one fund that just handles the equity/debt split for me' — doesn't want to be called every time the market moves, wants moderate, steady growth she can mostly ignore.",
            "email": "neha.kulkarni.retail@gmail.com", "phone": "+91 90210 44982", "city": "Nagpur",
            "relationship_since": "2021-02-18", "aum_fee_pct": 1.1, "risk_mandate": "Moderate",
        },
    },
    {
        "portfolio_id": "pf_nri_growth", "desk_id": "desk_equity",
        "name": "NRI Growth Portfolio", "base_ccy": "INR",
        "risk_driver": "Blue-chip compounding, long time horizon, low turnover",
        "mandate": "Long-horizon, blue-chip-only exposure for an overseas client planning an eventual return to India; prioritizes liquidity and stability over short-term alpha, mindful of eventual repatriation needs.",
        "manager_name": "Rajesh Iyer",
        "manager_bio": "Specializes in NRI-focused mandates. Prioritizes liquidity and blue-chip stability given clients' long-distance, lower-touch relationship with the market.",
        "nav": 72_000_000,
        "holdings": {"sec_hdfcbank": 16.8, "sec_reliance": 14.2, "sec_tcs": 12.6,
                     "sec_icicibank": 11.3, "sec_infosys": 9.7, "sec_hindunilvr": 8.4,
                     "sec_itc": 7.9, "sec_lt": 7.1, "sec_asianpaint": 6.5, "sec_titan": 5.5},
        "client": {
            "name": "Arvind & Sunita Rao", "age": 53, "occupation": "NRI couple, engineers based in Dubai",
            "persona": "Both work in the Gulf and have been sending money home to invest for over a decade, with an eye on eventually returning to India. Communicates mostly over WhatsApp and the occasional call across time zones. Cares more about not losing money on something exotic than beating the market — wants names they'd recognize from back home.",
            "email": "arvind.rao.dxb@gmail.com", "phone": "+971 50 445 8821", "city": "Dubai (NRI)",
            "relationship_since": "2016-11-05", "aum_fee_pct": 0.85, "risk_mandate": "Growth-Stable",
        },
    },
    {
        "portfolio_id": "pf_retirement_income", "desk_id": "desk_income",
        "name": "Retirement Income (SWP) Portfolio", "base_ccy": "INR",
        "risk_driver": "Dividend/income stability, sequence-of-return risk in retirement",
        "mandate": "Income-first allocation blending dividend-paying equity, high-grade debt, and REIT distributions to support a monthly systematic withdrawal without eroding capital in a downturn.",
        "manager_name": "Sunita Ramesh",
        "manager_bio": "Manages income-focused retirement mandates. Obsessive about downside protection since these clients can't simply wait out a bad year.",
        "nav": 24_000_000,
        "holdings": {"sec_itc": 0.15, "sec_hdfcbank": 0.10, "sec_corp_bond_aaa": 0.25,
                     "sec_gsec_10y": 0.20, "sec_psu_bond": 0.15, "sec_embassy_reit": 0.15},
        "client": {
            "name": "Prakash Iyer", "age": 66, "occupation": "Retired PSU engineer",
            "persona": "Spent 35 years at a public-sector company and retired on a pension plus provident fund payout, previously kept everything in fixed deposits. Cautiously agreed to diversify a portion into this account on his relationship manager's advice, but still needs a predictable monthly withdrawal to feel comfortable — capital loss is his single biggest fear.",
            "email": "prakash.iyer.retd@gmail.com", "phone": "+91 98200 33119", "city": "Thiruvananthapuram",
            "relationship_since": "2019-10-22", "aum_fee_pct": 0.7, "risk_mandate": "Conservative-Income",
        },
    },
    {
        "portfolio_id": "pf_promoter_equity", "desk_id": "desk_equity",
        "name": "Diversified Equity (Promoter Wealth) Portfolio", "base_ccy": "INR",
        "risk_driver": "Large-cap equity beta with an industrials & auto tilt",
        "mandate": "Diversified large-cap equity for a business promoter who took money off the table, tilted toward the industrials, auto, and capex names he understands from running his own factory, with a bond sleeve for ballast.",
        "manager_name": "Nikhil Sharma",
        "manager_bio": "Manages large UHNI equity mandates. Comfortable working with self-made promoter clients who hold strong, informed sector views of their own.",
        "nav": 460_000_000,
        "holdings": {
            "sec_reliance": 8.6, "sec_hdfcbank": 8.2, "sec_lt": 7.4, "sec_icicibank": 6.8, "sec_mm": 6.1,
            "sec_maruti": 5.4, "sec_infosys": 4.9, "sec_bhartiartl": 4.6, "sec_tcs": 4.2, "sec_ultracemco": 3.8,
            "sec_bel": 3.6, "sec_cumminsind": 3.4, "sec_ntpc": 3.3, "sec_sbin": 3.1, "sec_titan": 2.8,
            "sec_sunpharma": 2.6, "sec_asianpaint": 2.3, "sec_corp_bond_aaa": 6.0,
        },
        "client": {
            "name": "Rajiv Malhotra", "age": 59, "occupation": "Promoter & MD, auto-components manufacturer",
            "persona": "Built an auto-components business in Ludhiana over three decades and recently sold a partial stake to a PE fund, freeing up a large corpus to invest outside the company for the first time. Reads a balance sheet better than most analysts and has firm views on manufacturing and capex, but leans on the desk for everything outside his own industry. Wants his money working, not idle, but has no interest in speculative bets.",
            "email": "rajiv.malhotra.md@gmail.com", "phone": "+91 98140 55210", "city": "Ludhiana",
            "relationship_since": "2024-02-19", "aum_fee_pct": 0.65, "risk_mandate": "Growth",
        },
    },
    {
        "portfolio_id": "pf_family_office", "desk_id": "desk_equity",
        "name": "Multi-Asset Family Office Portfolio", "base_ccy": "INR",
        "risk_driver": "Blended equity, debt, gold, and REIT allocation across one household",
        "mandate": "A single multi-asset mandate for a second-generation family office: roughly half large-cap equity, a third high-grade debt, plus gold and REIT sleeves, run as one coordinated book so the family sees their whole balance sheet in one place.",
        "manager_name": "Ritika Bajaj",
        "manager_bio": "Runs multi-asset family-office mandates. Coordinates the equity, debt, gold, and real-assets sleeves under one roof so the client never has to stitch statements together.",
        "nav": 380_000_000,
        "holdings": {
            "sec_hdfcbank": 6.4, "sec_reliance": 5.8, "sec_icicibank": 5.2, "sec_infosys": 4.6, "sec_tcs": 3.9,
            "sec_lt": 3.4, "sec_bhartiartl": 3.1, "sec_hindunilvr": 2.8, "sec_bajfinance": 2.4, "sec_itc": 2.6,
            "sec_titan": 2.2, "sec_gsec_10y": 11.0, "sec_corp_bond_aaa": 10.5, "sec_gsec_5y": 6.5, "sec_psu_bond": 3.5,
            "sec_gold_etf": 7.2, "sec_sgb": 4.0, "sec_embassy_reit": 4.2, "sec_mindspace_reit": 2.8,
        },
        "client": {
            "name": "Anjali Bhandari", "age": 46, "occupation": "Head of family office (2nd-generation wealth)",
            "persona": "Runs the family office for a Mumbai business family whose founding generation built and exited a consumer brand. Thinks in terms of preserving and growing capital across generations, not chasing any single year's return. Wants diversification across asset classes as a matter of principle and expects a single, clear view of the entire household balance sheet rather than a dozen scattered products.",
            "email": "anjali.bhandari.fo@gmail.com", "phone": "+91 98670 44120", "city": "Mumbai",
            "relationship_since": "2020-07-14", "aum_fee_pct": 0.55, "risk_mandate": "Balanced-Diversified",
        },
    },
    {
        "portfolio_id": "pf_founder_growth", "desk_id": "desk_equity",
        "name": "Founder Growth Equity Portfolio", "base_ccy": "INR",
        "risk_driver": "Growth-tilted large-cap plus quality midcap, higher volatility by design",
        "mandate": "Growth-oriented equity for a technology founder with a high risk appetite and a long horizon: quality large-cap tech and financials anchored by a deliberate sleeve of high-conviction midcap names.",
        "manager_name": "Karan Nair",
        "manager_bio": "Growth-equity specialist for founder and new-economy wealth. Comfortable carrying concentrated technology and midcap risk for clients with the horizon and stomach for it.",
        "nav": 300_000_000,
        "holdings": {
            "sec_infosys": 8.2, "sec_hdfcbank": 6.6, "sec_tcs": 6.8, "sec_reliance": 6.2, "sec_icicibank": 5.8,
            "sec_hcltech": 5.4, "sec_bhartiartl": 5.1, "sec_bajfinance": 4.8, "sec_trent": 4.6, "sec_persistent": 4.4,
            "sec_dixon": 4.2, "sec_titan": 4.2, "sec_kpit": 3.9, "sec_ltim": 3.8,
        },
        "client": {
            "name": "Suhas Kamath", "age": 44, "occupation": "Tech founder (post-exit)",
            "persona": "Sold his SaaS company to a larger acquirer and now has real liquidity for the first time after years of everything being tied up in equity. Understands compounding and volatility intuitively, is comfortable with drawdowns that would scare most clients, and explicitly wants growth over safety while he is still decades from needing the money. Sharp, busy, prefers a crisp thesis over hand-holding.",
            "email": "suhas.kamath.founder@gmail.com", "phone": "+91 99020 33418", "city": "Bengaluru",
            "relationship_since": "2023-11-08", "aum_fee_pct": 0.75, "risk_mandate": "Aggressive-Growth",
        },
    },
    {
        "portfolio_id": "pf_physician_wealth", "desk_id": "desk_income",
        "name": "Blue-Chip Conservative Wealth Portfolio", "base_ccy": "INR",
        "risk_driver": "Blue-chip equity and high-grade debt blend, downside-protected",
        "mandate": "Capital-protective wealth for a senior physician couple: blue-chip, dividend-oriented equity paired with a large high-grade debt and gold allocation, built to grow steadily without the swings a demanding medical practice leaves no time to watch.",
        "manager_name": "Lakshmi Menon",
        "manager_bio": "Conservative wealth manager for established professionals and retirees. Prioritizes capital protection and steady, predictable income over chasing the market.",
        "nav": 220_000_000,
        "holdings": {
            "sec_hdfcbank": 6.2, "sec_reliance": 5.4, "sec_tcs": 4.8, "sec_hindunilvr": 4.6, "sec_itc": 4.4,
            "sec_infosys": 4.2, "sec_sunpharma": 3.6, "sec_bhartiartl": 3.2, "sec_corp_bond_aaa": 14.0,
            "sec_gsec_10y": 12.0, "sec_gsec_5y": 8.0, "sec_psu_bond": 5.0, "sec_gold_etf": 4.0,
        },
        "client": {
            "name": "Dr. Venkat & Latha Reddy", "age": 61, "occupation": "Senior cardiologist couple, part-owners of a hospital",
            "persona": "Both are practising doctors in Hyderabad with a stake in the hospital chain they helped build, and almost no free time to think about markets. Their biggest fear is a large loss close to retirement, so capital protection comes first, with steady growth a close second. They defer to the desk on structure but want plain-language explanations and no exotic products they cannot understand.",
            "email": "reddy.family.hyd@gmail.com", "phone": "+91 99490 22781", "city": "Hyderabad",
            "relationship_since": "2019-12-03", "aum_fee_pct": 0.6, "risk_mandate": "Conservative-Growth",
        },
    },
    {
        "portfolio_id": "pf_reference_balanced", "desk_id": "desk_benchmark",
        "name": "Reference Balanced 60/40 Fund", "base_ccy": "INR",
        "risk_driver": "N/A — fixed benchmark, not actively managed",
        "mandate": "A fixed, broadly diversified 60% equity / 40% debt reference book computed by the exact same engine as every other fund. Exists only so any signal's impact on a real fund can be compared against what a normal, unconcentrated book would show — the 'you vs. a normal book' lens (LLD §12). Not a real desk; no active manager.",
        "manager_name": None,
        "manager_bio": "N/A — fixed benchmark, not actively managed by anyone.",
        "is_reference": True,
        "nav": 20_000_000_000,
        # A textbook 60/40: ~60% broad large-cap equity, ~40% high-grade debt.
        "holdings": {"sec_hdfcbank": 7.8, "sec_reliance": 5.1, "sec_icicibank": 5.0, "sec_infosys": 3.4,
                     "sec_tcs": 2.4, "sec_lt": 2.3, "sec_bhartiartl": 2.0, "sec_itc": 2.5, "sec_sbin": 1.7,
                     "sec_mm": 1.4, "sec_axisbank": 1.9, "sec_hindunilvr": 1.3, "sec_maruti": 1.2,
                     "sec_sunpharma": 1.1, "sec_ntpc": 1.0, "sec_titan": 0.9, "sec_ultracemco": 0.8,
                     "sec_asianpaint": 0.7, "sec_bajfinance": 1.4,
                     "sec_gsec_10y": 15.0, "sec_corp_bond_aaa": 14.0, "sec_gsec_5y": 8.0, "sec_psu_bond": 3.0},
    },
]

# ---------------------------------------------------------------------------
# Assemble holdings list + risk block
# ---------------------------------------------------------------------------
def build_holdings_and_risk():
    """Per-portfolio math (normalize weights, compute risk tier) is shared with
    the runtime Add Client endpoint via portfolio_risk.compute_portfolio_risk,
    so a client added at runtime gets a risk tier computed identically to every
    seeded client. This function just handles the seed-specific bookkeeping:
    assembling holding_id / as_of_date and the full holdings list."""
    holdings = []
    risk = {}
    hid = 1
    for p in PORTFOLIOS:
        norm_holdings, market_values, risk_block = compute_portfolio_risk(p["nav"], p["holdings"], SEC_BY_ID)
        for sec_id, weight in norm_holdings.items():
            holdings.append({
                "holding_id": f"hld_{hid:04d}",
                "portfolio_id": p["portfolio_id"],
                "security_id": sec_id,
                "weight": weight,
                "market_value": market_values[sec_id],
                "as_of_date": "2026-07-23",
            })
            hid += 1
        risk[p["portfolio_id"]] = risk_block
    return holdings, risk


# Behavioral / psychographic profile per client, keyed by portfolio_id. Kept
# separate from the inline persona so it is easy to audit and extend. These
# describe how the client thinks and behaves, which drives how the manager
# should communicate, not just what they hold.
PSYCHOGRAPHICS = {
    "pf_cap_preservation": {
        "decision_style": "Delegates fully, defers to advisor",
        "loss_aversion": "Very high", "financial_literacy": "Basic",
        "engagement": "Checks monthly", "comms_pref": "Phone call",
        "primary_goal": "Preserve capital for medical and living costs",
        "time_horizon": "Short, under 3 years", "life_stage": "Retired",
    },
    "pf_bond_ladder": {
        "decision_style": "Deliberate, asks questions before acting",
        "loss_aversion": "Moderate to high", "financial_literacy": "Intermediate",
        "engagement": "Reviews quarterly", "comms_pref": "Email",
        "primary_goal": "Fund daughter's wedding in about 3 years",
        "time_horizon": "Medium, 3 to 5 years", "life_stage": "Mid-career",
    },
    "pf_largecap_growth": {
        "decision_style": "Hands-off by design, wants set-and-forget",
        "loss_aversion": "Moderate", "financial_literacy": "Intermediate",
        "engagement": "Reviews quarterly", "comms_pref": "WhatsApp",
        "primary_goal": "Long-term wealth building",
        "time_horizon": "Long, 10 years plus", "life_stage": "Early to mid career",
    },
    "pf_banking_financials": {
        "decision_style": "Self-directed, high conviction, pushes back",
        "loss_aversion": "Low", "financial_literacy": "Expert",
        "engagement": "Tracks weekly", "comms_pref": "In-person or call",
        "primary_goal": "Concentrated conviction growth",
        "time_horizon": "Medium to long, 5 to 10 years", "life_stage": "Pre-retirement",
    },
    "pf_it_services": {
        "decision_style": "Opinionated, reads every earnings call",
        "loss_aversion": "Low to moderate", "financial_literacy": "Advanced",
        "engagement": "Checks daily", "comms_pref": "Detailed email",
        "primary_goal": "Sector-conviction growth in what he knows",
        "time_horizon": "Long, 10 years plus", "life_stage": "Early career",
    },
    "pf_gold_hedge": {
        "decision_style": "Traditional, decides through her son",
        "loss_aversion": "High", "financial_literacy": "Basic",
        "engagement": "Rarely checks directly", "comms_pref": "Phone call",
        "primary_goal": "Inflation protection and preserving family wealth",
        "time_horizon": "Medium to long", "life_stage": "Pre-retirement",
    },
    "pf_smallcap_value": {
        "decision_style": "Aggressive, hands-on, high urgency",
        "loss_aversion": "Very low", "financial_literacy": "Advanced",
        "engagement": "Checks several times a day", "comms_pref": "WhatsApp and app",
        "primary_goal": "Aggressive compounding while young",
        "time_horizon": "Long, but trades actively", "life_stage": "Early career",
    },
    "pf_reit_income": {
        "decision_style": "Delegates, values convenience",
        "loss_aversion": "Moderate", "financial_literacy": "Intermediate",
        "engagement": "Reviews quarterly", "comms_pref": "Email",
        "primary_goal": "Passive property-style rental income",
        "time_horizon": "Medium to long", "life_stage": "Mid-career",
    },
    "pf_nifty_index": {
        "decision_style": "Rational, evidence-driven, cost-conscious",
        "loss_aversion": "Moderate", "financial_literacy": "Advanced",
        "engagement": "Reviews quarterly", "comms_pref": "Email",
        "primary_goal": "Low-cost market returns",
        "time_horizon": "Long, 10 years plus", "life_stage": "Early to mid career",
    },
    "pf_balanced_hybrid": {
        "decision_style": "Pragmatic, time-poor, wants balance",
        "loss_aversion": "Moderate", "financial_literacy": "Intermediate",
        "engagement": "Reviews a few times a year", "comms_pref": "WhatsApp",
        "primary_goal": "Steady growth with a smoother ride",
        "time_horizon": "Medium to long", "life_stage": "Mid-career",
    },
    "pf_nri_growth": {
        "decision_style": "Diligent, remote, currency-aware",
        "loss_aversion": "Moderate", "financial_literacy": "Advanced",
        "engagement": "Reviews monthly", "comms_pref": "Email and video call",
        "primary_goal": "Build India-based wealth for eventual return",
        "time_horizon": "Medium to long", "life_stage": "Pre-retirement",
    },
    "pf_retirement_income": {
        "decision_style": "Careful, income-focused, methodical",
        "loss_aversion": "High", "financial_literacy": "Intermediate",
        "engagement": "Reviews monthly", "comms_pref": "Phone call",
        "primary_goal": "Regular retirement income through withdrawals",
        "time_horizon": "Short to medium", "life_stage": "Retired",
    },
    "pf_promoter_equity": {
        "decision_style": "Decisive, informed on his sectors, delegates the rest",
        "loss_aversion": "Low to moderate", "financial_literacy": "Advanced",
        "engagement": "Reviews monthly", "comms_pref": "In-person or call",
        "primary_goal": "Grow proceeds from a partial business exit",
        "time_horizon": "Long, 10 years plus", "life_stage": "Pre-retirement",
    },
    "pf_family_office": {
        "decision_style": "Institutional, process-driven, diversification-first",
        "loss_aversion": "Moderate", "financial_literacy": "Expert",
        "engagement": "Reviews monthly", "comms_pref": "Formal review meetings",
        "primary_goal": "Preserve and grow multi-generational family wealth",
        "time_horizon": "Very long, generational", "life_stage": "Established",
    },
    "pf_founder_growth": {
        "decision_style": "Fast, conviction-led, comfortable with risk",
        "loss_aversion": "Very low", "financial_literacy": "Expert",
        "engagement": "Reviews monthly, low-touch", "comms_pref": "Concise email",
        "primary_goal": "Aggressive long-horizon growth of exit proceeds",
        "time_horizon": "Long, 10 years plus", "life_stage": "Mid-career",
    },
    "pf_physician_wealth": {
        "decision_style": "Cautious, defers on structure, wants clarity",
        "loss_aversion": "High", "financial_literacy": "Intermediate",
        "engagement": "Reviews a few times a year", "comms_pref": "Phone call",
        "primary_goal": "Protect capital into retirement with steady growth",
        "time_horizon": "Medium, 5 to 10 years", "life_stage": "Pre-retirement",
    },
}


# Demo relationship data: past PM-to-client interactions, the next action due,
# and a few extra relationship insights. Dates are fixed (today in the demo is
# 2026-07-24). This is synthetic, for showing the workflow, not real records.
def _c(date, channel, direction, summary):
    return {"date": date, "channel": channel, "direction": direction, "summary": summary}


COMMUNICATIONS = {
    "pf_cap_preservation": {
        "relationship": {"referral_source": "Walk-in branch referral", "dependents": "Widow, one son abroad",
                         "satisfaction": "High", "manager_note": "Values reassurance over returns. Never lead with market volatility."},
        "history": [
            _c("2026-07-08", "Phone", "outbound", "Monthly reassurance call, walked her through why the balance is stable despite market noise."),
            _c("2026-06-30", "Phone", "inbound", "Called worried about a headline on markets falling, reassured, no action taken."),
            _c("2026-06-10", "Email", "outbound", "Sent a simple one-page monthly statement summary."),
        ],
        "next_action": {"due": "2026-08-08", "action": "Monthly reassurance call", "priority": "Normal"},
    },
    "pf_bond_ladder": {
        "relationship": {"referral_source": "Colleague referral", "dependents": "Wife, one daughter (wedding upcoming)",
                         "satisfaction": "High", "manager_note": "Goal-anchored to the wedding. Keep duration short as the date nears."},
        "history": [
            _c("2026-07-15", "Email", "outbound", "Quarterly review email with the laddered maturity schedule ahead of the wedding."),
            _c("2026-07-02", "Email", "inbound", "Asked whether to lock a longer maturity, explained the duration tradeoff."),
            _c("2026-04-14", "Video call", "outbound", "Q4 review, confirmed wedding timeline unchanged at about 3 years."),
        ],
        "next_action": {"due": "2026-10-15", "action": "Next quarterly review", "priority": "Normal"},
    },
    "pf_largecap_growth": {
        "relationship": {"referral_source": "Digital sign-up", "dependents": "Single, no dependents",
                         "satisfaction": "Medium", "manager_note": "Hands-off. A short WhatsApp line each quarter is enough, do not over-contact."},
        "history": [
            _c("2026-07-20", "WhatsApp", "outbound", "Sent the quarterly one-liner, book is up, nothing to do."),
            _c("2026-05-05", "WhatsApp", "inbound", "Quick thumbs-up, no questions."),
        ],
        "next_action": {"due": "2026-10-20", "action": "Quarterly check-in", "priority": "Low"},
    },
    "pf_banking_financials": {
        "relationship": {"referral_source": "Ex-colleague from banking", "dependents": "Married, two adult children",
                         "satisfaction": "High", "manager_note": "Expert and opinionated. Engage on the thesis, do not simplify."},
        "history": [
            _c("2026-07-22", "Phone", "inbound", "Debated HDFC Bank Q1 margins, wants to stay concentrated."),
            _c("2026-07-15", "In-person", "both", "Coffee meeting, reviewed the banking thesis, agreed to hold conviction."),
            _c("2026-07-08", "Email", "outbound", "Shared a broker note on NBFC asset quality."),
        ],
        "next_action": {"due": "2026-07-29", "action": "Weekly banking-sector catch-up call", "priority": "High"},
    },
    "pf_it_services": {
        "relationship": {"referral_source": "Digital sign-up", "dependents": "Single, supports parents",
                         "satisfaction": "High", "manager_note": "Reads every earnings call. Send primary-source detail, he will spot fluff."},
        "history": [
            _c("2026-07-23", "Email", "inbound", "Long email dissecting the Infosys guidance cut, wants a deep-dive on the read-through."),
            _c("2026-07-18", "Email", "outbound", "Sent TCS earnings-call transcript highlights."),
        ],
        "next_action": {"due": "2026-07-25", "action": "Reply with Infosys guidance deep-dive", "priority": "High"},
    },
    "pf_gold_hedge": {
        "relationship": {"referral_source": "Family (son is also a client)", "dependents": "Homemaker, decisions via son",
                         "satisfaction": "High", "manager_note": "Route substantive discussions through her son. Prefers phone, not app."},
        "history": [
            _c("2026-07-05", "Phone", "outbound", "Spoke with her son, explained gold's role as an inflation hedge."),
            _c("2026-06-01", "Phone", "inbound", "Son asked about adding to gold after the price rise, discussed."),
        ],
        "next_action": {"due": "2026-08-05", "action": "Monthly call via son", "priority": "Normal"},
    },
    "pf_smallcap_value": {
        "relationship": {"referral_source": "Social media / self-directed", "dependents": "Single, no dependents",
                         "satisfaction": "Medium", "manager_note": "High energy, impulsive. Reinforce position-sizing discipline every contact."},
        "history": [
            _c("2026-07-23", "WhatsApp", "inbound", "Asking about adding a new midcap IT name, reminded him of concentration limits."),
            _c("2026-07-21", "WhatsApp", "inbound", "Excited about Dixon's run, wants to increase exposure."),
            _c("2026-07-19", "App note", "outbound", "Flagged that smallcap volatility is elevated."),
        ],
        "next_action": {"due": "2026-07-24", "action": "Discuss position-sizing discipline", "priority": "High"},
    },
    "pf_reit_income": {
        "relationship": {"referral_source": "Wealth seminar", "dependents": "Married couple, one young child",
                         "satisfaction": "High", "manager_note": "Want convenience and income. Lead with distributions, not price moves."},
        "history": [
            _c("2026-07-12", "Email", "outbound", "Quarterly distribution summary from Embassy and Mindspace REITs."),
            _c("2026-04-10", "Email", "inbound", "Asked about office vacancy trends, shared leasing data."),
        ],
        "next_action": {"due": "2026-10-12", "action": "Quarterly distribution review", "priority": "Normal"},
    },
    "pf_nifty_index": {
        "relationship": {"referral_source": "Digital sign-up", "dependents": "Single",
                         "satisfaction": "High", "manager_note": "Cost-obsessed and rational. Always have expense ratio and tracking error ready."},
        "history": [
            _c("2026-07-16", "Email", "outbound", "Quarterly tracking-error and expense-ratio note."),
            _c("2026-07-10", "Email", "inbound", "Asked to confirm the fund's expense ratio versus a competitor."),
        ],
        "next_action": {"due": "2026-10-16", "action": "Quarterly index review", "priority": "Low"},
    },
    "pf_balanced_hybrid": {
        "relationship": {"referral_source": "Existing-client referral", "dependents": "Married, runs a family business",
                         "satisfaction": "Medium", "manager_note": "Time-poor business owner. Watch her seasonal cash needs around festivals."},
        "history": [
            _c("2026-07-19", "WhatsApp", "outbound", "Mid-year check-in, the balanced mix cushioned the IT drag."),
            _c("2026-03-22", "Phone", "inbound", "Discussed cash needs for her retail business seasonality."),
        ],
        "next_action": {"due": "2026-09-19", "action": "Pre-festival-season liquidity check", "priority": "Normal"},
    },
    "pf_nri_growth": {
        "relationship": {"referral_source": "NRI wealth webinar", "dependents": "Married couple, children studying abroad",
                         "satisfaction": "High", "manager_note": "Currency and repatriation-aware. Always pair reviews with an FX view."},
        "history": [
            _c("2026-07-17", "Video call", "both", "Monthly review, discussed rupee levels and repatriation timing."),
            _c("2026-07-03", "Email", "inbound", "Asked about tax implications of an eventual return to India."),
        ],
        "next_action": {"due": "2026-08-17", "action": "Monthly NRI review and FX update", "priority": "Normal"},
    },
    "pf_retirement_income": {
        "relationship": {"referral_source": "PSU retiree network", "dependents": "Wife, financially independent children",
                         "satisfaction": "High", "manager_note": "Income certainty is everything. Confirm each payout, avoid surprises."},
        "history": [
            _c("2026-07-14", "Phone", "outbound", "Confirmed the monthly SWP payout processed, income steady."),
            _c("2026-07-01", "Phone", "inbound", "Asked whether the payout can rise with inflation, explained the annual reset."),
        ],
        "next_action": {"due": "2026-08-14", "action": "Monthly SWP payout confirmation", "priority": "Normal"},
    },
    "pf_promoter_equity": {
        "relationship": {"referral_source": "Introduced by his PE deal advisor", "dependents": "Wife, son runs the business",
                         "satisfaction": "High", "manager_note": "Engage him on industrials and capex, defer to him there. Keep the rest simple and diversified."},
        "history": [
            _c("2026-07-18", "In-person", "both", "Reviewed the book at his office, discussed adding to capex and defence names."),
            _c("2026-07-05", "Phone", "inbound", "Asked for a view on cement demand, shared the desk's read."),
            _c("2026-06-12", "Email", "outbound", "Sent the half-yearly performance pack with sector attribution."),
        ],
        "next_action": {"due": "2026-08-05", "action": "Discuss deploying the remaining cash tranche", "priority": "High"},
    },
    "pf_family_office": {
        "relationship": {"referral_source": "Long-standing family relationship", "dependents": "Manages wealth for three households",
                         "satisfaction": "High", "manager_note": "Institutional counterpart. Bring structure, attribution, and a whole-balance-sheet view to every review."},
        "history": [
            _c("2026-07-16", "Formal review", "both", "Quarterly family-office review, walked through allocation drift and rebalancing plan."),
            _c("2026-06-28", "Email", "inbound", "Requested a consolidated cross-asset exposure report."),
            _c("2026-05-20", "Video call", "outbound", "Discussed trimming equity slightly after the run-up, agreed to stay balanced."),
        ],
        "next_action": {"due": "2026-08-16", "action": "Prepare quarterly consolidated review pack", "priority": "Normal"},
    },
    "pf_founder_growth": {
        "relationship": {"referral_source": "Referred by another founder client", "dependents": "Married, young children",
                         "satisfaction": "High", "manager_note": "Time-poor and sharp. Lead with a one-line thesis, skip the hand-holding, he will ask if he wants more."},
        "history": [
            _c("2026-07-19", "Email", "outbound", "Sent a crisp note on midcap IT valuations after the rally."),
            _c("2026-06-24", "Email", "inbound", "Asked whether to add to Trent, discussed position sizing."),
        ],
        "next_action": {"due": "2026-08-19", "action": "Monthly growth-book review note", "priority": "Normal"},
    },
    "pf_physician_wealth": {
        "relationship": {"referral_source": "Referred by their chartered accountant", "dependents": "Two children, both settled abroad",
                         "satisfaction": "High", "manager_note": "Capital protection first. Explain everything in plain language, never pitch anything they cannot easily understand."},
        "history": [
            _c("2026-07-11", "Phone", "outbound", "Half-yearly call, reassured them the debt and gold sleeve cushions any equity dip."),
            _c("2026-05-30", "Email", "outbound", "Sent a simple summary of the year's income and growth."),
        ],
        "next_action": {"due": "2026-09-11", "action": "Half-yearly capital-protection review", "priority": "Normal"},
    },
}


# Demo performance per portfolio, keyed by portfolio_id: total returns for
# YTD, trailing 1 year, trailing 3-year CAGR, and since-inception CAGR. Numbers
# are illustrative but chosen to be realistic for each strategy in the current
# India market (cash near T-bill yields, IT soft, gold and smallcaps strong).
# The Nifty 50 benchmark is the yardstick shown next to each equity book.
NIFTY_BENCHMARK = {"ytd_pct": 8.4, "one_year_pct": 14.2, "three_year_cagr_pct": 13.8}

PERFORMANCE = {
    "pf_cap_preservation": {"ytd_pct": 3.8, "one_year_pct": 6.8, "three_year_cagr_pct": 6.5, "since_inception_cagr_pct": 6.6},
    "pf_bond_ladder": {"ytd_pct": 4.5, "one_year_pct": 8.2, "three_year_cagr_pct": 7.4, "since_inception_cagr_pct": 7.8},
    "pf_largecap_growth": {"ytd_pct": 9.2, "one_year_pct": 16.8, "three_year_cagr_pct": 15.2, "since_inception_cagr_pct": 14.5},
    "pf_banking_financials": {"ytd_pct": 11.4, "one_year_pct": 22.3, "three_year_cagr_pct": 18.6, "since_inception_cagr_pct": 17.2},
    "pf_it_services": {"ytd_pct": 2.1, "one_year_pct": 4.6, "three_year_cagr_pct": 9.8, "since_inception_cagr_pct": 12.4},
    "pf_gold_hedge": {"ytd_pct": 14.7, "one_year_pct": 26.5, "three_year_cagr_pct": 14.2, "since_inception_cagr_pct": 11.8},
    "pf_smallcap_value": {"ytd_pct": 13.5, "one_year_pct": 31.2, "three_year_cagr_pct": 24.8, "since_inception_cagr_pct": 21.5},
    "pf_reit_income": {"ytd_pct": 5.8, "one_year_pct": 11.2, "three_year_cagr_pct": 8.6, "since_inception_cagr_pct": 9.1},
    "pf_nifty_index": {"ytd_pct": 8.3, "one_year_pct": 14.0, "three_year_cagr_pct": 13.6, "since_inception_cagr_pct": 13.1},
    "pf_balanced_hybrid": {"ytd_pct": 6.2, "one_year_pct": 11.6, "three_year_cagr_pct": 10.4, "since_inception_cagr_pct": 10.8},
    "pf_nri_growth": {"ytd_pct": 7.8, "one_year_pct": 14.8, "three_year_cagr_pct": 13.2, "since_inception_cagr_pct": 12.9},
    "pf_retirement_income": {"ytd_pct": 5.1, "one_year_pct": 9.4, "three_year_cagr_pct": 8.2, "since_inception_cagr_pct": 8.6},
    "pf_promoter_equity": {"ytd_pct": 9.8, "one_year_pct": 17.6, "three_year_cagr_pct": 15.8, "since_inception_cagr_pct": 14.2},
    "pf_family_office": {"ytd_pct": 7.4, "one_year_pct": 13.4, "three_year_cagr_pct": 11.6, "since_inception_cagr_pct": 11.2},
    "pf_founder_growth": {"ytd_pct": 12.2, "one_year_pct": 24.6, "three_year_cagr_pct": 20.4, "since_inception_cagr_pct": 18.5},
    "pf_physician_wealth": {"ytd_pct": 6.4, "one_year_pct": 11.8, "three_year_cagr_pct": 10.2, "since_inception_cagr_pct": 10.5},
}


def main():
    holdings, risk = build_holdings_and_risk()
    portfolios_out = []
    for p in PORTFOLIOS:
        entry = {k: v for k, v in p.items() if k not in ("holdings", "nav")}
        if entry.get("client"):
            client = dict(entry["client"])
            # strip em dashes from the free-text persona (house style: no em dashes)
            if client.get("persona"):
                client["persona"] = client["persona"].replace(" — ", ", ").replace("—", ", ")
            psy = PSYCHOGRAPHICS.get(p["portfolio_id"])
            if psy:
                client["psychographics"] = psy
            comm = COMMUNICATIONS.get(p["portfolio_id"])
            if comm:
                client["relationship"] = comm.get("relationship", {})
                client["communications"] = comm.get("history", [])
                client["next_action"] = comm.get("next_action")
            entry["client"] = client
        perf = PERFORMANCE.get(p["portfolio_id"])
        if perf:
            entry["performance"] = perf
        portfolios_out.append(entry)
    data = {
        "desks": DESKS,
        "portfolios": portfolios_out,
        "securities": SECURITIES,
        "holdings": holdings,
        "risk": risk,
        "benchmark": {"name": "Nifty 50", **NIFTY_BENCHMARK},
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {len(SECURITIES)} securities, {len(portfolios_out)} portfolios, "
          f"{len(holdings)} holdings to {OUT_PATH}")


if __name__ == "__main__":
    main()
