"""
PRISM — Streamlit analyst view (Phase 2 of the roadmap in docs/PRD.md).

Thin UI layer over insight_lens.py: every number shown here is produced by
the exact same deterministic functions already covered by tests/. This file
adds no new business logic — it only renders what insight_lens.py computes.

Run:
  pip install -r requirements.txt
  streamlit run app.py
"""

import os

import streamlit as st

from insight_lens import (
    build_query_context,
    compute_factor_impact,
    compute_portfolio_impact,
    compute_scenario_impact,
    attach_reference_comparison,
    detect_cross_desk_contradictions,
    detect_factor_signals,
    extract_citations_and_narrative,
    link_citations_to_securities,
    load_data,
    run_search,
    securities_in_sector,
)

st.set_page_config(page_title="PRISM — Investment Research Copilot", layout="wide")

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error(
        "ANTHROPIC_API_KEY is not set. Create a `.env` file in this folder "
        "(see `.env.example`) with your key, then restart the app."
    )
    st.stop()

data = load_data()


def run_lens(sector):
    sector_secs = securities_in_sector(data, sector)
    company_names = build_query_context(sector_secs)
    response = run_search(sector, company_names)
    extracted = extract_citations_and_narrative(response)
    linked = link_citations_to_securities(extracted["citations"], data["securities"])
    portfolio_impact = compute_portfolio_impact(data, linked)
    portfolio_impact_vs_ref = attach_reference_comparison(portfolio_impact)
    factor_signals = detect_factor_signals(extracted["narrative"])
    factor_impact = compute_factor_impact(data, factor_signals)
    cross_desk = detect_cross_desk_contradictions(data, factor_impact)
    scenario = compute_scenario_impact(data, factor_signals)
    return {
        "sector": sector,
        "narrative": extracted["narrative"],
        "citations": linked,
        "portfolio_impact": portfolio_impact_vs_ref,
        "factor_signals": factor_signals,
        "factor_impact": factor_impact,
        "cross_desk": cross_desk,
        "scenario": scenario,
    }


with st.sidebar:
    st.markdown("### PRISM")
    st.caption("Investment Research & Portfolio Insight Copilot — India MVP")
    sectors = sorted({s["sector"] for s in data["securities"]})
    default_index = sectors.index("Financials") if "Financials" in sectors else 0
    sector = st.selectbox("Sector to research", sectors, index=default_index)
    run_clicked = st.button("Run insight lens", type="primary", use_container_width=True)
    st.divider()
    st.caption(
        "Decision-support tool. Not investment advice, not a trading system. "
        "Every claim above is citation-grounded; every number below is computed, not guessed."
    )

st.title("Portfolio book")
port_rows = []
for p in data["portfolios"]:
    if p.get("is_reference"):
        continue
    risk = data["risk"].get(p["portfolio_id"], {})
    port_rows.append({
        "Fund": p["name"],
        "Manager": p.get("manager_name") or "—",
        "Risk tier": risk.get("risk_tier", "—"),
        "Holdings": risk.get("num_holdings", "—"),
    })
st.dataframe(port_rows, use_container_width=True, hide_index=True)

if run_clicked:
    with st.spinner(f"Researching {sector} — calling Claude with web search..."):
        st.session_state["result"] = run_lens(sector)

result = st.session_state.get("result")

if not result:
    st.info("Pick a sector in the sidebar and click **Run insight lens** to fetch real, cited market research.")
    st.stop()

st.header(f"Lens: {result['sector']}")
st.markdown(result["narrative"] or "_(no narrative returned)_")

st.subheader("Portfolio impact vs. reference 60/40 book")
st.caption("Lens 2 from LLD §12 — absolute exposure first, the multiple against a normal book second.")
if not result["portfolio_impact"]:
    st.info("No held securities were matched in this run's citations.")
else:
    rows = []
    for p in result["portfolio_impact"]:
        mult = p["vs_reference_multiple"]
        mult_str = "—" if mult is None else (mult if isinstance(mult, str) else f"{mult}x")
        rows.append({
            "Fund": p["portfolio_name"],
            "% NAV touched": p["pct_nav_touched"],
            "Reference book %": p["vs_reference_pct"],
            "Your multiple": mult_str,
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

with st.expander(f"Citations ({len(result['citations'])})"):
    for c in result["citations"]:
        tag = f" → linked to `{', '.join(c['linked_security_ids'])}`" if c["linked_security_ids"] else " _(no security match)_"
        st.markdown(f"- [{c['title'] or c['url']}]({c['url']}){tag}")

if result["factor_signals"]:
    st.subheader("Macro / commodity factor signals")
    st.caption("Detected by an LLM classification pass (not entity linking) — see docs/ADVANCED.md.")
    mapped = {m["factor"] for p in result["factor_impact"] for m in p["matched"]}
    for fs in result["factor_signals"]:
        note = "" if fs["factor"] in mapped else " — _no India holding is tagged for this factor yet_"
        st.markdown(f"**{fs['factor']}**: {fs['direction']}{note}  \n> {fs['snippet']}")

if result["factor_impact"]:
    st.subheader("Factor impact (tailwind / headwind)")
    rows = [{
        "Fund": p["portfolio_name"],
        "Tailwind %": p["tailwind_pct"],
        "Headwind %": p["headwind_pct"],
    } for p in result["factor_impact"]]
    st.dataframe(rows, use_container_width=True, hide_index=True)

if result["cross_desk"]:
    st.subheader("Cross-desk contradictions")
    st.caption("ADVANCED.md #4 — oversight only, no advice to either desk.")
    for c in result["cross_desk"]:
        st.warning(
            f"**[{c['factor']}]** {c['tailwind_fund']} (tailwind {c['tailwind_pct']}%) "
            f"vs. **{c['headwind_fund']}** (headwind {c['headwind_pct']}%)"
        )

if result["scenario"]:
    st.subheader("Scenario / what-if roll-up")
    st.caption("ADVANCED.md #2 — labeled assumptions if this factor move continues, never a forecast.")
    rows = [{
        "Fund": s["portfolio_name"],
        "Mild": s["bands"]["mild"],
        "Moderate": s["bands"]["moderate"],
        "Severe": s["bands"]["severe"],
    } for s in result["scenario"]]
    st.dataframe(rows, use_container_width=True, hide_index=True)
