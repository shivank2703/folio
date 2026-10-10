"""Streamlit UI: ask a question, read a cited answer, open the pages it cites.

Stage 8 (SPEC.md §4). The sources panel is not decoration. The citation layer
is the product (§1), so every page an answer cites is one click from the chunk
it came from, shown exactly as the model saw it — inherited statement title,
unit line and all. A reader who distrusts a figure can check it here before
opening the filing.

The model and the index load once per session rather than once per question
(st.cache_resource). A fresh 64 MB model load per keystroke would dominate the
answer time, and the index is read-only, so sharing one handle is safe
(SPEC.md §5).

Run it with: streamlit run streamlit_app.py (from the repo root)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import anthropic
import streamlit as st

from gen.answer import build_client, guarded_answer
from gen.guardrails import CITATION, cited_pages, has_enough_context
from retrieve.embed import load_model
from retrieve.search import DEFAULT_K, EXPANSION_SEEDS, open_index, page_context, search
from retrieve.store import ensure_index
from ui.limits import DailyLimiter, is_owner, visitor_address

DB_PATH = Path("data/lancedb")

EXAMPLE = "How did HCC's standalone total assets change from FY24 to FY25?"

# The public demo spends the maintainer's key. Ten questions is enough to try
# an answer, a refusal and a scope trap; it is a courtesy limit, not a wall,
# because session state lives in the browser tab and a refresh resets it. The
# hard ceiling is the monthly spend limit on the key itself.
MAX_QUESTIONS = 10

# Community Cloud picks Python in the deploy dialog, defaults to 3.12, and reads
# no version file; the choice cannot be changed without deleting the app. Every
# pinned wheel was resolved on 3.13 and the committed index was built by them, so
# a wrong pick is stopped here, visibly, instead of serving from a runtime the
# index was never tested against.
PYTHON = (3, 13)


@st.cache_resource(show_spinner="Loading the index and the embedding model...")
def load_retrieval():
    """Fetch the published index if needed, then open it and the embedding model, once per container.

    The index is no longer in git (retrieve/store.py): a fresh container
    downloads the tarball corpus/index.json names and checks its SHA-256
    before opening anything, so the app still serves exactly the index its
    commit was tested with.
    """
    ensure_index(DB_PATH)
    return open_index(DB_PATH), load_model()


def adopt_streamlit_secret() -> None:
    """Move Streamlit's secret into the environment if that is where the key lives.

    Community Cloud hands secrets to the app through st.secrets, while the SDK
    and the local .env path both read the environment. Bridging once, here,
    keeps a single code path reading the key and leaves the hosting mechanism a
    detail of the UI. Reading st.secrets raises when no secrets file exists at
    all — the normal local case — so the miss is caught rather than predicted.
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        return
    try:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return


@st.cache_resource(show_spinner=False)
def load_filings() -> list[dict]:
    """The filings in the index, with the display names from the corpus manifest."""
    return json.loads(Path("corpus/corpus.json").read_text(encoding="utf-8"))


@st.cache_resource(show_spinner=False)
def load_client():
    """Build the API client once, or report why it could not be built.

    A missing key is a configuration problem, not a question the user asked
    badly, so it is returned rather than raised: retrieval still works and the
    page can say exactly what is wrong.
    """
    try:
        return build_client(), ""
    except RuntimeError as error:
        return None, str(error)


def page_link(url: str, page: int) -> str:
    """The filing's own PDF, opened at one page.

    Browser PDF viewers honour #page=N, and all three issuers serve their
    reports inline rather than as downloads (checked 2026-10-04), so a
    citation lands the reader on the page it names.
    """
    return f"{url}#page={page}"


def link_citations(text: str, url: str) -> str:
    """Turn every [page N] in an answer into a link to that page of the filing."""
    return CITATION.sub(lambda m: f"[page {m.group(1)}]({page_link(url, int(m.group(1)))})", text)


@st.cache_resource(show_spinner=False)
def daily_limiter() -> DailyLimiter:
    """One counter for the whole server process, shared by every visitor's session."""
    return DailyLimiter()


def resolve_owner() -> bool:
    """Whether this session belongs to the maintainer, who is never rate-limited.

    Decided once per session: a local run, or ?owner=<FOLIO_OWNER_KEY> on the
    first visit. The key is removed from the address bar straight away, so a
    copied link or a screenshot does not carry it.
    """
    if st.session_state.get("owner"):
        return True
    offered = st.query_params.get("owner")
    try:
        owner_key = st.secrets.get("FOLIO_OWNER_KEY")
    except Exception:
        # No secrets file at all: the normal local case, decided by URL below.
        owner_key = None
    owner = is_owner(st.context.url, offered, owner_key)
    if offered is not None:
        del st.query_params["owner"]
    st.session_state["owner"] = owner
    return owner


def render_sources(context: list[dict], cited: set[int], url: str) -> None:
    """Show every chunk the model read, in page order, cited ones already open.

    Chunks the answer did not use are shown too: what the model could have
    used and did not is part of judging the answer. A chunk pulled in because
    its page was retrieved carries no similarity of its own and says so,
    rather than borrowing its page's score. The context arrives in retrieval
    order; it is sorted here because a reader checking a citation looks for a
    page number, not a rank.
    """
    st.subheader("Sources")
    for chunk in sorted(context, key=lambda c: (c["page"], c["chunk"])):
        was_cited = chunk["page"] in cited
        score = "same page as a hit" if chunk.get("sibling") else f"similarity {chunk['score']:.3f}"
        label = f"{'cited · ' if was_cited else ''}page {chunk['page']} · chunk {chunk['chunk']} · {score}"
        with st.expander(label, expanded=was_cited):
            st.markdown(f"[Open page {chunk['page']} of the filing]({page_link(url, chunk['page'])})")
            st.text(chunk["text"])


def main() -> None:
    st.set_page_config(page_title="Folio", page_icon="📄", layout="centered")
    st.title("Folio")
    if sys.version_info[:2] != PYTHON:
        st.error(f"Folio needs Python {PYTHON[0]}.{PYTHON[1]}; this is {sys.version.split()[0]}. "
                 "On Streamlit Community Cloud, delete the app and redeploy it with Python "
                 f"{PYTHON[0]}.{PYTHON[1]} chosen under Advanced settings.")
        st.stop()
    st.caption("Cited answers from Indian annual reports. Every claim carries the page it came from.")

    adopt_streamlit_secret()
    owner = resolve_owner()
    table, model = load_retrieval()
    client, client_error = load_client()

    # A form so Enter submits: the question box is the whole interface, and
    # reaching for the mouse to ask is friction the demo does not need.
    with st.form("ask"):
        # One filing at a time. Page numbers repeat across annual reports, so a
        # question asked of "the filings" would return three balance sheets,
        # each citation right for a company nobody asked about.
        # The options are the labels themselves, not the records behind them:
        # Streamlit filters the dropdown on each option's own text, so passing
        # records made typing a company's name match nothing.
        filings = {f"{f['name']} — {f['fiscal_year']}": f for f in load_filings()}
        filing = filings[st.selectbox("Filing", list(filings))]
        question = st.text_input("Question", placeholder=EXAMPLE)
        submitted = st.form_submit_button("Ask", type="primary")
    if not submitted or not question.strip():
        st.stop()
    # The index ships text derived from these filings, so every result names
    # the issuer and links the exact document it came from (SPEC.md §7), the
    # same URL corpus/SOURCES.md verifies by checksum. It is drawn after submit
    # because widgets inside a form do not rerun the page: drawn above, it
    # kept linking the previous filing after the dropdown changed.
    st.caption(f"Source: [{filing['name']} annual report, {filing['fiscal_year']}]({filing['source_url']}), "
               "published by the company. Page numbers are the PDF's own.")

    # Counted on submit, refusals included: a question is a question to the
    # reader, and counting only model calls would make the limit unpredictable.
    asked = st.session_state.get("asked", 0)
    if asked >= MAX_QUESTIONS and not owner:
        st.info(
            f"That's the {MAX_QUESTIONS}-question limit for this demo session — thanks for trying Folio. "
            "It runs on a personal API key, so each visit gets a few questions. To keep going, "
            "clone the repo and run it locally with your own key: "
            "https://github.com/shivank2703/folio"
        )
        st.stop()
    st.session_state["asked"] = asked + 1

    started = time.perf_counter()
    hits = search(table, model, question, max(DEFAULT_K, EXPANSION_SEEDS), filing["company"])
    # The ranking decides whether to answer; the widened context is what the
    # model reads and what the panel below shows.
    context = page_context(table, hits)
    if has_enough_context(hits) and client is None:
        # The model is only needed when the gate passes: a question nothing in
        # the filing resembles is refused without it. Retrieval worked either
        # way, so the chunks are shown and the failure costs the reader
        # nothing they already had.
        st.error(client_error)
        render_sources(context, cited=set(), url=filing["source_url"])
        st.stop()

    if has_enough_context(hits) and not owner:
        # The daily limits guard spend, so they are taken only here, just
        # before the paid call: a question refused at the floor above costs
        # nothing and does not count.
        over = daily_limiter().take(daily_limiter().visitor(visitor_address(st.context.ip_address, st.context.headers)))
        if over:
            st.info(
                "Folio has answered as many questions as it can today"
                + (" for this connection" if over == "visitor" else " across all visitors")
                + ". It runs on a personal API key with a daily budget, which resets at midnight UTC. "
                "The extracts retrieval found are below, and the code is free to run with your own key: "
                "https://github.com/shivank2703/folio"
            )
            render_sources(context, cited=set(), url=filing["source_url"])
            st.stop()

    try:
        verdict = guarded_answer(question, hits, client, context, f"{filing['name']} annual report, {filing['fiscal_year']}")
    except anthropic.APIError:
        # Spend limit reached, rate limited or the API is down: none of these
        # is the reader's fault, and a traceback on a public page explains
        # nothing. Retrieval still worked, so the sources are still shown.
        st.error("The answer service is unavailable right now, so this question was not answered. "
                 "The extracts retrieval found are below.")
        render_sources(context, cited=set(), url=filing["source_url"])
        st.stop()
    elapsed = time.perf_counter() - started

    if verdict["refused"]:
        # A refusal is an answer: it must read as a deliberate decision, not
        # as an empty box or an error.
        st.warning(f"**{verdict['text']}**\n\nWhy: {verdict['reason']}")
    else:
        st.markdown(link_citations(verdict["text"], filing["source_url"]))
        if verdict["invalid_citations"]:
            st.error(
                "This answer cited pages that were never retrieved: "
                f"{verdict['invalid_citations']}. They are marked in the text above."
            )
        if verdict["recited"]:
            # Said out loud: the reader should know the page shown is the
            # guard's, taken from where the figure is printed, not the model's.
            moves = "; ".join(f"page {', '.join(map(str, old))} → page {new}" for old, new in verdict["recited"])
            st.caption(f"Citation corrected to the page that prints the figure: {moves}.")
        if verdict["ungrounded"]:
            # Shown, not hidden: the reader decides what a figure is worth once
            # told that the page it cites does not print it.
            listed = "; ".join(f"{fig} (cited to page {', '.join(map(str, pages))})" for fig, pages in verdict["ungrounded"])
            st.warning(f"Not found on the cited page, so check these before relying on them: {listed}.")
        if verdict["scrubbed"]:
            st.info(f"Removed {len(verdict['scrubbed'])} sentence(s) that strayed into investment advice.")

    # Two decimals, because a refusal costs retrieval only and rounds to 0.0s
    # at one: the number is there to show where the time actually goes.
    st.caption(
        f"answered in {elapsed:.2f}s · {filing['name']} {filing['fiscal_year']}"
        + (" · maintainer session, no limits" if owner else f" · question {asked + 1} of {MAX_QUESTIONS} this session")
    )
    render_sources(verdict["context"], cited=set(cited_pages(verdict["text"])), url=filing["source_url"])


if __name__ == "__main__":
    main()
