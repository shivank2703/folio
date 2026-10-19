"""Public fund reader with explicit, bounded annual-report drill-down."""

from __future__ import annotations

import streamlit as st

from funds.answer import answer
from funds.data import coverage, fact_citation, load_funds
from gen.guardrails import REFUSAL


def render(filings: list[dict]) -> dict | None:
    """Return a selected indexed filing for the shared company answer form."""
    funds = load_funds()
    if not funds:
        st.info("Fund disclosures are awaiting verification.")
        return None
    by_name = {f["name"]: f for f in funds}
    fund = by_name[st.selectbox("Fund", list(by_name))]
    st.subheader(f"{fund['name']} · {fund['plan']}")
    st.caption(f"Portfolio: {fund['portfolio_date']} · Factsheet: {fund['factsheet_date']}")
    for key, label in (("benchmark", "Benchmark"), ("expense_ratio", "Direct-plan expense ratio"),
                       ("exit_load", "Exit load")):
        fact = fund[key]
        st.markdown(f"**{label}:** {fact['value']} {fact_citation(fund, fact)}")
        if fact.get("definition"):
            st.caption(fact["definition"])
    st.caption("The monthly portfolio is scheme-wide. Plan-specific costs come from the factsheet.")
    with st.form("fund-question"):
        question = st.text_input("Fund question", placeholder="What is the Direct-plan expense ratio?")
        submitted = st.form_submit_button("Ask about this fund")
    if submitted and question.strip():
        result = answer(question, fund)
        if result == REFUSAL:
            st.warning(REFUSAL)
        else:
            st.markdown(result)
    st.subheader("Disclosed holdings")
    st.caption("Annual-report Q&A covers only the top 10 domestic equity holdings by disclosed weight. "
               "All other rows are not indexed. Source rows use the original spreadsheet numbering.")
    rows = []
    for holding in fund["holdings"]:
        filing = coverage(holding, filings)
        rows.append({"Equity rank": holding["rank"], "Instrument": holding["name"],
                     "Weight": holding["weight_display"], "Asset type": holding["asset_type"],
                     "Coverage": "Indexed" if filing else "Not indexed",
                     "Source row": f"{holding['sheet']} row {holding['row']}",
                     "Source": fund["sources"]["portfolio"]["url"]})
    st.dataframe(rows, hide_index=True, width="stretch",
                 column_config={"Source": st.column_config.LinkColumn("Disclosure", display_text="Open source")})
    candidates = {r["name"]: coverage(r, filings) for r in fund["holdings"] if r["eligible"]}
    chosen = st.selectbox("Top-holding annual report", ["Choose a holding", *candidates])
    if chosen == "Choose a holding":
        return None
    filing = candidates[chosen]
    if filing is None:
        st.info("Not indexed. Annual-report Q&A is unavailable for this holding.")
    return filing
