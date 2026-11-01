"""The maintainer's own holdings, beside the filings and fund disclosures Folio has indexed.

Owner sessions only (ui/limits.py decides who is the owner); a visitor never
sees the mode, and nothing about the holdings is written to disk, logged or
sent anywhere. They are read from the FOLIO_PORTFOLIO secret (Streamlit's
secrets on the deployed app) or, locally, from portfolio.txt, which is
gitignored: real holdings never enter the repository (SPEC.md §7).

Format, one holding per line: an NSE symbol ("INFY") or a fund name as Folio
lists it ("HDFC Defence Fund"), optionally followed by a comma and a weight
that is shown back to the owner and used for nothing else. Blank lines and
lines starting with # are ignored.

Facts only (SPEC.md §2): each stock gets its filing's stored overview and the
indexed funds that disclose it, each fund its cited costs and which of the
stocks it holds. Nothing here calls the model, scores or ranks a holding.
"""

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from funds.data import fact_citation, row_citation
from ui import company

LOCAL_FILE = Path("portfolio.txt")


def read_portfolio() -> str:
    """The holdings text: the FOLIO_PORTFOLIO secret, else the gitignored local file, else nothing."""
    try:
        secret = st.secrets.get("FOLIO_PORTFOLIO")
    except Exception:
        # No secrets file at all: the normal local case.
        secret = None
    if secret:
        return str(secret)
    return LOCAL_FILE.read_text(encoding="utf-8") if LOCAL_FILE.exists() else ""


def parse(text: str) -> list[dict]:
    """[{"entry", "weight"}] from the holdings text; the weight stays a string, as typed."""
    holdings = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        entry, _, weight = line.partition(",")
        holdings.append({"entry": entry.strip(), "weight": weight.strip()})
    return holdings


def normalised(name: str) -> str:
    """"infosys" for "Infosys Ltd." and "INFOSYS LIMITED": a company name without its suffix and punctuation."""
    name = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    return " ".join(w for w in name.split() if w not in {"ltd", "limited", "the", "co", "company"})


def filing_for(symbol: str, filings: list[dict]) -> dict | None:
    """The indexed filing for an NSE symbol: Folio's code, or a listing that names the symbol."""
    symbol = symbol.upper()
    return next((f for f in filings if f["company"] == symbol
                 or re.search(rf"\bNSE\s+{re.escape(symbol)}\b", f.get("listing", ""))), None)


def fund_for(name: str, funds: list[dict]) -> dict | None:
    wanted = normalised(name)
    return next((f for f in funds if wanted and (wanted in normalised(f["name"]) or normalised(f["name"]) in wanted)), None)


def disclosures(filing: dict, funds: list[dict]) -> list[dict]:
    """Every indexed fund row that is this company: by reviewed mapping where one exists, else by exact name."""
    found = []
    for fund in funds:
        for row in fund["holdings"]:
            if row.get("company") == filing["company"]:
                how = "reviewed mapping"
            elif row["asset_type"] == "domestic equity" and normalised(row["name"]) == normalised(filing["name"]):
                how = "matched by name"
            else:
                continue
            found.append({"fund": fund, "row": row, "how": how})
    return found


# An NSE symbol as people write one: "INFY", "M&M", "BAJAJ-AUTO". An entry of
# this shape is only ever a stock, so "HDFC" can never match "HDFC Defence Fund".
SYMBOL = re.compile(r"[A-Za-z0-9&-]{1,20}")


def resolve(holdings: list[dict], filings: list[dict], funds: list[dict]) -> list[dict]:
    """Each holding as a stock (with its filing, if indexed), a fund, or unrecognised."""
    resolved = []
    for holding in holdings:
        entry = holding["entry"]
        filing = fund = None
        if SYMBOL.fullmatch(entry):
            filing = filing_for(entry, filings)
            kind = "stock" if filing or entry.isupper() else "unrecognised"
        else:
            fund = fund_for(entry, funds)
            kind = "fund" if fund else "unrecognised"
        resolved.append({**holding, "kind": kind, "filing": filing, "fund": fund})
    return resolved


def render(filings: list[dict], funds: list[dict], overviews: dict) -> None:
    st.subheader("My portfolio")
    st.caption("Maintainer only. Read from the FOLIO_PORTFOLIO secret (or the gitignored portfolio.txt "
               "locally); never stored, logged or sent anywhere. Facts from the indexed filings and fund "
               "disclosures only.")
    holdings = resolve(parse(read_portfolio()), filings, funds)
    if not holdings:
        st.info("No holdings configured. Add FOLIO_PORTFOLIO to the app's secrets: one NSE symbol or fund "
                "name per line, optionally followed by a comma and a weight.")
        return

    stocks = [h for h in holdings if h["kind"] == "stock"]
    rows = []
    for h in holdings:
        filing, fund = h["filing"], h["fund"]
        held_by = sorted({d["fund"]["name"] for d in disclosures(filing, funds)}) if filing else []
        rows.append({"Holding": h["entry"], "Weight": h["weight"] or "–",
                     "Type": h["kind"], "Indexed filing": f"{filing['name']} · {filing['fiscal_year']}" if filing
                     else (fund["name"] if fund else "not indexed"),
                     "Overview": "yes" if filing and overviews.get(filing["company"]) else "–",
                     "In indexed funds": ", ".join(held_by) or "–"})
    st.dataframe(rows, hide_index=True, width="stretch")

    for h in stocks:
        filing = h["filing"]
        with st.expander(f"{h['entry']} · " + (filing["name"] if filing else "not indexed")):
            if not filing:
                st.caption("Not indexed. The maintainer panel above adds a company's latest annual report.")
                continue
            company.render_overview(filing, overviews.get(filing["company"]),
                                    empty="No overview has been built for this filing yet.")
            found = disclosures(filing, funds)
            if not found:
                st.caption("Not in any indexed fund's disclosed holdings.")
            for d in found:
                fund, row = d["fund"], d["row"]
                st.markdown(f"Held by **{fund['name']}**: {row['weight_display']} of the fund in its disclosure "
                            f"of {fund['portfolio_date']} ({row_citation(fund, row)}; {d['how']}).")

    for h in (h for h in holdings if h["kind"] == "fund"):
        fund = h["fund"]
        with st.expander(f"{fund['name']} · {fund['plan']}"):
            st.markdown(f"**Expense ratio:** {fund['expense_ratio']['value']} {fact_citation(fund, fund['expense_ratio'])}  \n"
                        f"**Benchmark:** {fund['benchmark']['value']} {fact_citation(fund, fund['benchmark'])}")
            overlap = [(s, d) for s in stocks if s["filing"] for d in disclosures(s["filing"], [fund])]
            if not overlap:
                st.caption("None of the stocks above is in this fund's disclosed holdings.")
            for stock, d in overlap:
                st.markdown(f"Also held directly: **{stock['filing']['name']}**, {d['row']['weight_display']} of "
                            f"this fund on {fund['portfolio_date']} ({row_citation(fund, d['row'])}; {d['how']}).")

    unknown = [h["entry"] for h in holdings if h["kind"] == "unrecognised"]
    if unknown:
        st.caption("Not recognised as an NSE symbol or an indexed fund: " + ", ".join(unknown))
