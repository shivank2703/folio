"""The company page: find a filing, read its stored overview, ask a question.

Three things a first visit needs and the old page lacked. A search that
matches how people name a company (its name, its exchange symbol, the code
Folio files it under); an overview that is already there, cited page by page
and built offline (overviews/build.py), so reading it costs no API call; and
example questions that show what kind of question the filing can answer.

Layout is a single column throughout: Streamlit stacks columns on a phone
anyway, and a single column reads the same at 390 px as at 1,200.
"""

from __future__ import annotations

import re
from urllib.parse import quote

import streamlit as st

from gen.guardrails import CITATION

# Shown when nothing has been typed yet: one of each kind of question the
# eval measures (a business question, a figure, a risk question).
EXAMPLES = [
    "What does {short} do?",
    "What was {short}'s revenue from operations in {fy}?",
    "What were {short}'s total assets at the end of {fy}?",
    "What are the key risks {short} faces?",
]


def page_link(url: str, page: int) -> str:
    """The filing's own PDF, opened at one page.

    Browser PDF viewers honour #page=N, and the issuers serve their reports
    inline rather than as downloads (checked 2026-10-04), so a citation lands
    the reader on the page it names.
    """
    return f"{quote(url, safe=':/?&=%')}#page={page}"


def link_citations(text: str, url: str) -> str:
    """Turn every [page N] in a text into a link to that page of the filing."""
    return CITATION.sub(lambda m: f"[page {m.group(1)}]({page_link(url, int(m.group(1)))})", text)


def short_name(filing: dict) -> str:
    """"Infosys" for "Infosys Limited": the name a question would use."""
    name = re.sub(r"\b(limited|ltd\.?|industries india|india)\s*$", "", filing["name"], flags=re.I).strip(" .,")
    return name or filing["name"]


def searchable(filing: dict) -> str:
    return " ".join([filing["name"], filing["company"], filing.get("listing", "")]).lower()


def find_filings(query: str, filings: list[dict]) -> list[dict]:
    """Filings matching every word of the query in name, code or listing; exact codes first."""
    words = query.lower().split()
    if not words:
        return list(filings)
    matches = [f for f in filings if all(w in searchable(f) for w in words)]
    return sorted(matches, key=lambda f: (f["company"].lower() != query.strip().lower(),
                                          not f["name"].lower().startswith(words[0]), f["name"].lower()))


def label(filing: dict) -> str:
    return f"{filing['name']} ({filing['company']}) · {filing['fiscal_year']}"


def choose(filings: list[dict]) -> dict | None:
    """Search box and result list; the chosen filing, or None while nothing matches."""
    query = st.text_input("Find a company", placeholder="Name, NSE symbol or code, e.g. Infosys, INFY, L&T",
                          key="company_query")
    matches = find_filings(query.replace("&", ""), filings)
    if not matches:
        st.info(f"No indexed filing matches “{query}”. {len(filings)} companies are indexed; "
                "clear the search to see them all.")
        return None
    if query:
        st.caption(f"{len(matches)} of {len(filings)} filings match")
    by_label = {label(f): f for f in matches}
    return by_label[st.selectbox("Filing", list(by_label), key="company_choice")]


def header(filing: dict) -> None:
    st.subheader(f"{filing['name']} · {filing['fiscal_year']} annual report")
    listing = f"{filing['listing']} · " if filing.get("listing") else ""
    st.caption(f"{listing}[Source PDF]({quote(filing['source_url'], safe=':/?&=%')}), published by the company. "
               "Page numbers are the PDF's own.")


def render_overview(filing: dict, overview: dict | None) -> None:
    """The stored overview, every sentence linked to its page; or an honest note that there is none."""
    with st.expander("Overview", expanded=True):
        if not overview or overview.get("filing_sha256") != filing["sha256"]:
            st.caption("No overview has been built for this filing yet. Ask a question below; every answer "
                       "is cited to its page.")
            return
        shown = 0
        for section in overview["sections"].values():
            if not section["text"]:
                continue
            st.markdown(f"**{section['heading']}.** {link_citations(section['text'], filing['source_url'])}")
            shown += 1
        missing = [s["heading"] for s in overview["sections"].values() if not s["text"]]
        if not shown:
            st.caption("The overview questions found nothing they could cite in this filing.")
        st.caption(f"Built {overview['built']} from the filing alone; every sentence links to the page it comes "
                   "from." + (f" Not found in the filing: {', '.join(missing).lower()}." if missing else ""))


def examples(filing: dict) -> list[str]:
    return [e.format(short=short_name(filing), fy=filing["fiscal_year"]) for e in EXAMPLES]


def ask(filing: dict, placeholder: str | None = None) -> str | None:
    """Example questions and the question box; the question to answer this run, or None.

    Examples sit outside the form because Streamlit allows only a submit
    button inside one; clicking one asks it straight away, through the same
    limits as a typed question.
    """
    st.markdown("**Ask this filing**")
    clicked = None
    for i, example in enumerate(examples(filing)):
        # Full width so they line up as a list at any width and read as buttons on a phone.
        if st.button(example, key=f"example-{filing['company']}-{i}", width="stretch"):
            clicked = example
    # A form so Enter submits: the question box is the whole interface.
    with st.form("ask"):
        typed = st.text_input("Question", placeholder=placeholder or examples(filing)[1])
        submitted = st.form_submit_button("Ask", type="primary")
    if clicked:
        return clicked
    return typed.strip() if submitted and typed.strip() else None
