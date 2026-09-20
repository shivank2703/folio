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
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from retrieve.embed import load_model
from retrieve.search import DEFAULT_K, open_index, search

# The public demo spends the maintainer's key, so the cheapest current model
# answers: this is extraction and quotation from five short extracts, not
# open-ended reasoning. Exact ID, no date suffix.
MODEL = "claude-haiku-4-5"

# Answers are two or three sentences with citations. A low ceiling keeps a
# runaway response from spending the demo's budget; it is a cost cap, not a
# length target.
MAX_TOKENS = 1024

SYSTEM_PROMPT = """You answer questions about an Indian listed company's annual \
report, using only the extracts you are given.

Rules:
- Use only the numbered extracts below. Nothing you know about the company from \
elsewhere may enter the answer.
- End every sentence that states a fact from the filing with its page marker, \
written exactly as [page N]. Take N from the "page N" label on the extract's \
first line. Never take a page number from the body of an extract, and never \
cite a page that is not among the extracts.
- State a figure's unit only when the extract states it, for example in a line \
such as "(Amount in ₹ crore, unless otherwise stated)" or in a column header. \
If an extract gives a figure with no unit on the page, give the figure and say \
the page does not state its unit. Never assume crore, lakh or rupees.
- Call a figure standalone or consolidated only when the extract says so, for \
example in a statement title. Never infer which one it is.
- Report what the filing says. Do not offer investment advice, views on the \
share price, or suggestions about what an investor should do.
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
            "no Anthropic credentials found: put your key after ANTHROPIC_API_KEY= in .env "
            "(copy .env.example if it is missing)"
        )
    return client


def build_prompt(question: str, hits: list[dict]) -> str:
    """Lay out the question and the extracts, each headed by the page it came from.

    The header line is the only place a page number is offered as a citation,
    and it is written from the chunk's metadata. The extract's own text follows
    untouched, inherited title and unit lines included, because those lines are
    what let the answer name a unit or a statement without guessing.
    """
    extracts = []
    for number, hit in enumerate(hits, start=1):
        extracts.append(f"[{number}] page {hit['page']} (chunk {hit['chunk']})\n{hit['text']}")
    return f"Question: {question}\n\nExtracts:\n\n" + "\n\n".join(extracts)


def generate(client: anthropic.Anthropic, question: str, hits: list[dict]) -> str:
    """Ask the model for an answer grounded in these extracts, and return its text."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(question, hits)}],
    )
    return "".join(block.text for block in message.content if block.type == "text").strip()


def answer_question(question: str, db_path: Path, k: int = DEFAULT_K) -> dict:
    """Search, then answer: the whole path from a question to a cited answer."""
    table = open_index(db_path)
    hits = search(table, load_model(), question, k)
    client = build_client()
    return {"question": question, "hits": hits, "text": generate(client, question, hits)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Answer a question about the filing, with page citations.")
    parser.add_argument("question", help="a question about the filing, in plain English")
    parser.add_argument("-k", type=int, default=DEFAULT_K, help="how many chunks to put in front of the model")
    parser.add_argument("--db", type=Path, default=Path("data/lancedb"), help="LanceDB directory from retrieve.embed")
    args = parser.parse_args()

    try:
        result = answer_question(args.question, args.db, args.k)
    except anthropic.AuthenticationError:
        raise SystemExit("the API key was rejected; check ANTHROPIC_API_KEY in .env")
    except anthropic.RateLimitError as error:
        raise SystemExit(f"rate limited by the API; retry shortly ({error.message})")
    except anthropic.APIStatusError as error:
        raise SystemExit(f"the API returned {error.status_code}: {error.message}")
    except anthropic.APIConnectionError:
        raise SystemExit("could not reach the API; check the network connection")

    print(result["text"])
    print("\nRetrieved:")
    for rank, hit in enumerate(result["hits"], start=1):
        print(f"  {rank}. page {hit['page']} chunk {hit['chunk']}  cos {hit['score']:.3f}")


if __name__ == "__main__":
    main()
