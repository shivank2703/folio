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
from gen.guardrails import cited_pages, has_enough_context
from retrieve.embed import load_model
from retrieve.search import DEFAULT_K, EXPANSION_SEEDS, open_index, page_context, search

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
    """Open the committed index and the embedding model, once per session."""
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


def render_sources(context: list[dict], cited: set[int]) -> None:
    """Show every chunk the model read, in page order, cited ones already open.

    Chunks the answer did not use are shown too: what the model could have
    used and did not is part of judging the answer. A chunk pulled in because
    its page was retrieved carries no similarity of its own and says so,
    rather than borrowing its page's score.
    """
    st.subheader("Sources")
    for chunk in context:
        was_cited = chunk["page"] in cited
        score = "same page as a hit" if chunk.get("sibling") else f"similarity {chunk['score']:.3f}"
        label = f"{'cited · ' if was_cited else ''}page {chunk['page']} · chunk {chunk['chunk']} · {score}"
        with st.expander(label, expanded=was_cited):
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

    # Counted on submit, refusals included: a question is a question to the
    # reader, and counting only model calls would make the limit unpredictable.
    asked = st.session_state.get("asked", 0)
    if asked >= MAX_QUESTIONS:
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
        render_sources(context, cited=set())
        st.stop()

    try:
        verdict = guarded_answer(question, hits, client, context)
    except anthropic.APIError:
        # Spend limit reached, rate limited or the API is down: none of these
        # is the reader's fault, and a traceback on a public page explains
        # nothing. Retrieval still worked, so the sources are still shown.
        st.error("The answer service is unavailable right now, so this question was not answered. "
                 "The extracts retrieval found are below.")
        render_sources(context, cited=set())
        st.stop()
    elapsed = time.perf_counter() - started

    if verdict["refused"]:
        # A refusal is an answer: it must read as a deliberate decision, not
        # as an empty box or an error.
        st.warning(f"**{verdict['text']}**\n\nWhy: {verdict['reason']}")
    else:
        st.markdown(verdict["text"])
        if verdict["invalid_citations"]:
            st.error(
                "This answer cited pages that were never retrieved: "
                f"{verdict['invalid_citations']}. They are marked in the text above."
            )
        if verdict["scrubbed"]:
            st.info(f"Removed {len(verdict['scrubbed'])} sentence(s) that strayed into investment advice.")

    # Two decimals, because a refusal costs retrieval only and rounds to 0.0s
    # at one: the number is there to show where the time actually goes.
    st.caption(
        f"answered in {elapsed:.2f}s · {filing['name']} {filing['fiscal_year']}"
        f" · question {asked + 1} of {MAX_QUESTIONS} this session"
    )
    render_sources(verdict["context"], cited=set(cited_pages(verdict["text"])))


if __name__ == "__main__":
    main()
