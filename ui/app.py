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

Run it with: streamlit run ui/app.py
"""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from gen.answer import build_client, guarded_answer
from gen.guardrails import cited_pages, has_enough_context
from retrieve.embed import load_model
from retrieve.search import DEFAULT_K, open_index, search

DB_PATH = Path("data/lancedb")

EXAMPLE = "How did HCC's standalone total assets change from FY24 to FY25?"


@st.cache_resource(show_spinner="Loading the index and the embedding model...")
def load_retrieval():
    """Open the committed index and the embedding model, once per session."""
    return open_index(DB_PATH), load_model()


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


def render_sources(hits: list[dict], cited: set[int]) -> None:
    """Show every retrieved chunk, the cited ones first and already open.

    Uncited chunks are shown too: what retrieval offered and the answer did
    not use is part of judging the answer.
    """
    st.subheader("Sources")
    for hit in sorted(hits, key=lambda hit: (hit["page"] not in cited, -hit["score"])):
        was_cited = hit["page"] in cited
        label = f"{'cited · ' if was_cited else ''}page {hit['page']} · chunk {hit['chunk']} · similarity {hit['score']:.3f}"
        with st.expander(label, expanded=was_cited):
            st.text(hit["text"])


def main() -> None:
    st.set_page_config(page_title="Praman", page_icon="📄", layout="centered")
    st.title("Praman")
    st.caption("Cited answers from an annual report. Every claim carries the page it came from.")

    table, model = load_retrieval()
    client, client_error = load_client()

    # A form so Enter submits: the question box is the whole interface, and
    # reaching for the mouse to ask is friction the demo does not need.
    with st.form("ask"):
        question = st.text_input("Question", placeholder=EXAMPLE)
        submitted = st.form_submit_button("Ask", type="primary")
    if not submitted or not question.strip():
        st.stop()

    started = time.perf_counter()
    hits = search(table, model, question, DEFAULT_K)
    if has_enough_context(hits) and client is None:
        # The model is only needed when the gate passes: a question nothing in
        # the filing resembles is refused without it. Retrieval worked either
        # way, so the chunks are shown and the failure costs the reader
        # nothing they already had.
        st.error(client_error)
        render_sources(hits, cited=set())
        st.stop()

    verdict = guarded_answer(question, hits, client)
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
    st.caption(f"answered in {elapsed:.2f}s")
    render_sources(hits, cited=set(cited_pages(verdict["text"])))


if __name__ == "__main__":
    main()
