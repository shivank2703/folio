"""Cited answers: a question in, an answer whose every claim carries its page.

Stage 6 (SPEC.md §4). The retrieval side already decides which five chunks the
model may read; this file decides what may be said about them. Three rules
carry the product's promise (SPEC.md §1, §2, §3.2):

Citations come from metadata. Each extract is labelled with the page number
its chunk record carries, and the model is told to copy that label. Page text
is full of numbers — note references, years, figures — and any of them could
pass for a page number, so the number a citation may use is the one the
pipeline knows, never one the model reads out of the text.

Units come from the page. A figure means nothing without "(Amount in ₹ crore,
unless otherwise stated)" or a column header naming its unit, and chunk.py
carries that line into every chunk that needs it. If a chunk has no unit line,
the answer says so rather than assuming the report's usual crore.

Scope comes from the page. chunk.py carries a statement title into every chunk
of a statement page, so the model can say "standalone" when the page says it —
and must not guess otherwise: the consolidated twin of a figure sits 80 pages
away with different numbers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from gen.guardrails import (
    MIN_SIMILARITY,
    REFUSAL,
    best_similarity,
    cited_pages,
    has_enough_context,
    is_refusal,
    recite,
    scrub_advice,
    strip_after_refusal,
    ungrounded_figures,
    validate_citations,
)
from retrieve.embed import load_model
from retrieve.search import DEFAULT_K, EXPANSION_SEEDS, open_index, page_context, search

# The public demo spends the maintainer's key, so the cheapest current model
# answers: this is extraction and quotation from five short extracts, not
# open-ended reasoning. Exact ID, no date suffix.
MODEL = "claude-haiku-4-5"

# Answers are two or three sentences with citations. A low ceiling keeps a
# runaway response from spending the demo's budget; it is a cost cap, not a
# length target.
MAX_TOKENS = 1024

SYSTEM_PROMPT = f"""You answer questions about an Indian listed company's annual \
report, using only the extracts you are given.

Rules:
- Every extract comes from the one filing named on the first line of the \
message. A company named in the question by a short name ("Unihealth", "HCC") \
is that filing's company; its figures, standalone or consolidated, are that \
company's figures.
- Use only the extracts below. Nothing you know about the company from \
elsewhere may enter the answer.
- End every sentence that states a fact from the filing with its page marker, \
written exactly as [page N]. Take N from the "extract from page N" label \
above the extract. Never take a page number from the body of an extract (note \
numbers, years and printed page numbers look the same), and never cite a page \
that is not among the extracts.
- State a figure's unit only when the extract states it, for example in a line \
such as "(Amount in ₹ crore, unless otherwise stated)" or in a column header. \
If an extract gives a figure with no unit on the page, give the figure and say \
the page does not state its unit. Never assume crore, lakh or rupees.
- Call a figure standalone or consolidated only when the extract says so, for \
example in a statement title. Never infer which one it is.
- Report what the filing says. Do not offer investment advice, views on the \
share price, or suggestions about what an investor should do.
- If you state a figure that no extract prints (a difference, a total, a \
ratio, a percentage change, a unit conversion), give the printed figures it \
comes from with their citations, then write the result followed by \
"(computed from [page N])", naming every page its inputs come from. Never \
present a computed figure as if the filing printed it.
- If the extracts do not answer the question, reply with exactly: {REFUSAL} \
Add nothing else: no explanation, no related figure, no partial answer. A \
hedged half-answer is worse than that one sentence.
- Be brief: two or three sentences unless the question needs more."""


def build_client() -> anthropic.Anthropic:
    """Return an API client, with the key loaded from .env and never written in code.

    The SDK resolves credentials in its own order — an API key, an auth token,
    a signed-in CLI profile — so the check is for whatever it resolved rather
    than for one environment variable, and it happens here, before a question
    is embedded, so a missing key fails in one obvious place.
    """
    load_dotenv()
    client = anthropic.Anthropic()
    if not (client.api_key or client.auth_token):
        raise RuntimeError(
            "No Anthropic API key, so answers cannot be generated — retrieval and the "
            "sources below still work. Locally: put your key after ANTHROPIC_API_KEY= in "
            ".env (copy .env.example). Deployed: add ANTHROPIC_API_KEY in the app's "
            "Secrets settings (see .streamlit/secrets.toml.example)."
        )
    return client


def build_prompt(question: str, hits: list[dict], filing: str | None = None) -> str:
    """Lay out the filing, the question and the extracts, each headed by the page it came from.

    The filing's name comes first because the extracts rarely say whose they
    are: asked about "Unihealth", the model refused a consolidated figure from
    Unihealth Hospitals Limited's own balance sheet as being "the group's, not
    Unihealth's".

    The header line is the only place a page number is offered as a citation,
    and it is written from the chunk's metadata. The extract's own text follows
    untouched, inherited title and unit lines included, because those lines are
    what let the answer name a unit or a statement without guessing.
    """
    extracts = []
    # No running number on the extracts. They used to open "[2] page 190", and
    # with thirty extracts in front of it the model cited [page 2]: a bracketed
    # small number is exactly what a citation looks like. The page is now the
    # only number in the label.
    for hit in hits:
        extracts.append(f"--- extract from page {hit['page']} (chunk {hit['chunk']}) ---\n{hit['text']}")
    heading = f"Filing: {filing}\n\n" if filing else ""
    return f"{heading}Question: {question}\n\nExtracts:\n\n" + "\n\n".join(extracts)


def generate(client: anthropic.Anthropic, question: str, hits: list[dict], filing: str | None = None) -> str:
    """Ask the model for an answer grounded in these extracts, and return its text."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(question, hits, filing)}],
    )
    return "".join(block.text for block in message.content if block.type == "text").strip()


def guarded_answer(
    question: str, hits: list[dict], client: anthropic.Anthropic, context: list[dict] | None = None,
    filing: str | None = None,
) -> dict:
    """Gate, answer, then check what came back (Stage 7 over Stage 6).

    Order is the point. The similarity gate runs before the model is called,
    so a question the filing cannot answer costs nothing and cannot be talked
    into an answer. The citation check runs after, because only the model's
    own words can be checked against the pages it was shown. A refusal from
    either end reads the same to the caller.
    """
    # "hits" is the ranking the gate judges; "context" is what the model reads,
    # which page expansion may have widened. Citations are checked against the
    # context, whose pages are the same set either way: expansion only ever adds
    # siblings of pages that were already retrieved.
    context = hits if context is None else context
    verdict = {
        "question": question,
        "hits": hits,
        "context": context,
        "refused": True,
        "invalid_citations": [],
        "ungrounded": [],
        "recited": [],
        "scrubbed": [],
        "raw": "",
    }

    if not has_enough_context(hits):
        best = best_similarity(hits)
        return {**verdict, "text": REFUSAL, "reason": f"best similarity {best:.3f} is below the {MIN_SIMILARITY} floor"}

    raw = generate(client, question, context, filing)
    # The model's own words are kept beside what the reader is shown, so the
    # eval can grade the contract even where a guard has already repaired it.
    verdict["raw"] = raw
    text, trailed = strip_after_refusal(raw)
    if is_refusal(text):
        reason = "the model found no answer in the extracts"
        return {**verdict, "text": REFUSAL, "reason": reason + (" (text after the refusal removed)" if trailed else "")}

    # Re-citation runs before validation, so a [page 6] the model took from
    # "Note 6" is moved to the page that prints the figure instead of being
    # thrown away as a page that was never retrieved.
    text, recited = recite(text, context)
    text, invalid = validate_citations(text, {chunk["page"] for chunk in context})
    text, scrubbed = scrub_advice(text)
    ungrounded = ungrounded_figures(text, context)
    if not cited_pages(text):
        # Either every citation was invented, or none was given. An uncited
        # claim is exactly what this project promises never to publish (§6),
        # so the answer is withheld rather than shown with a warning.
        reason = f"every citation was to a page not retrieved ({invalid})" if invalid else "the answer carried no citation"
        return {**verdict, "text": REFUSAL, "reason": reason, "invalid_citations": invalid, "scrubbed": scrubbed}

    return {**verdict, "text": text, "refused": False, "reason": "", "invalid_citations": invalid,
            "ungrounded": ungrounded, "recited": recited, "scrubbed": scrubbed}


def filing_label(company: str | None, manifest: Path = Path("corpus/corpus.json")) -> str | None:
    """"Unihealth Hospitals annual report, FY26": the filing name the prompt opens with."""
    for entry in json.loads(manifest.read_text(encoding="utf-8")):
        if entry["company"] == company:
            return f"{entry['name']} annual report, {entry['fiscal_year']}"
    return None


def answer_question(question: str, db_path: Path, k: int = DEFAULT_K, company: str | None = None) -> dict:
    """The whole path from a question to a cited answer, or to an honest refusal."""
    table = open_index(db_path)
    # The ranking runs deeper than k: k is what a reader is shown, while the
    # context is built by widening every page near the top of the ranking.
    hits = search(table, load_model(), question, max(k, EXPANSION_SEEDS), company)
    return guarded_answer(question, hits, build_client(), page_context(table, hits), filing_label(company))


def main() -> None:
    parser = argparse.ArgumentParser(description="Answer a question about the filing, with page citations.")
    parser.add_argument("question", help="a question about the filing, in plain English")
    parser.add_argument("-k", type=int, default=DEFAULT_K, help="how many chunks to put in front of the model")
    parser.add_argument("--db", type=Path, default=Path("data/lancedb"), help="LanceDB directory from retrieve.embed")
    parser.add_argument("--company", help="which filing to answer from, e.g. HCC; pages repeat across filings")
    args = parser.parse_args()

    try:
        result = answer_question(args.question, args.db, args.k, args.company)
    except anthropic.AuthenticationError:
        raise SystemExit("the API key was rejected; check ANTHROPIC_API_KEY in .env")
    except anthropic.RateLimitError as error:
        raise SystemExit(f"rate limited by the API; retry shortly ({error.message})")
    except anthropic.APIStatusError as error:
        raise SystemExit(f"the API returned {error.status_code}: {error.message}")
    except anthropic.APIConnectionError:
        raise SystemExit("could not reach the API; check the network connection")

    print(result["text"])
    if result["refused"]:
        print(f"  (refused: {result['reason']})")
    if result["invalid_citations"]:
        print(f"  (citations to pages never retrieved: {result['invalid_citations']})")
    if result["scrubbed"]:
        print(f"  (removed {len(result['scrubbed'])} sentence(s) of investment advice)")
    print("\nContext the model read:")
    for chunk in result["context"]:
        score = "same page" if chunk.get("sibling") else f"cos {chunk['score']:.3f}"
        print(f"  {chunk['company']} page {chunk['page']} chunk {chunk['chunk']}  {score}")


if __name__ == "__main__":
    main()
