"""Chunking: clean page records in, ~200-token chunks out, each tied to one page.

The page is the citation unit (SPEC.md §3.3), so a chunk never spans two
pages: a chunk holding the foot of page 114 and the head of page 115 could be
cited to only one of them, and every claim from the other half would cite
the wrong page. Within a page, chunks are packed from whole rows — the lines
preprocess.py rebuilt — so a table row is never cut between its label and its
figures.

A chunk that starts part-way down a table has lost the lines that give its
numbers meaning: the unit declaration and the period header. preprocess.py
left those lines in place and listed them, so this file tracks which ones are
in force at each row and gives a chunk the ones it does not state itself
(SPEC.md §3.2: a value is never orphaned from its unit).

Output: data/chunks.jsonl, one record per chunk:

    {"company": "HCC", "fiscal_year": "FY25", "page": 114, "chunk": 1,
     "tokens": 196, "text": "(Amount in ₹ crore, ...)\\nParticulars | ...\\n..."}
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import tiktoken

from ingest.extract import write_jsonl
from ingest.preprocess import VALUE

# Tokens per chunk, context lines included: they are embedded with the rows,
# so they spend the same budget.
TARGET_TOKENS = 200

# Prose rows repeated from the end of one chunk at the start of the next, so a
# sentence cut by a chunk boundary is whole in at least one of the two.
OVERLAP_TOKENS = 40

# cl100k_base is a ruler for sizing chunks, not the embedding model's own
# tokenizer — that model is chosen at Stage 4 (SPEC.md §5), and Stage 4 must
# check the largest chunk against its limit, since figures like "30,41,20,351"
# split into more pieces under some tokenizers than others.
ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


def cells(row: str) -> list[str]:
    """Split a row back into the cells preprocess.py joined with " | "."""
    return row.split(" | ")


def has_figures(row: str) -> bool:
    """A table row: at least one cell is a bare figure."""
    return any(VALUE.match(cell) for cell in cells(row))


def context_kind(row: str, page: dict) -> str | None:
    """Return "header" or "unit" if preprocess.py listed this row as context, else None."""
    if row in page["headers"]:
        return "header"
    if any(cell in page["units"] for cell in cells(row)):
        return "unit"
    return None


def with_context(body: list[str], in_force: dict[str, str], page: dict) -> str:
    """Chunk text: the context in force that the chunk does not state, then its rows.

    Checked per kind. A chunk holding its own header row needs no copy of an
    earlier one — prefixing "As at March 31, 2025" above a table headed "As
    at March 31, 2024" would label every figure with the wrong year — but it
    still inherits the page's unit line if it doesn't restate it.
    """
    stated = {context_kind(row, page) for row in body}
    prefix = [in_force[kind] for kind in ("unit", "header") if kind in in_force and kind not in stated]
    return "\n".join(prefix + body)


def overlap(body: list[str]) -> list[str]:
    """The trailing prose rows to repeat at the start of the next chunk.

    A sentence runs across rows, so a boundary can cut it in half. Table rows
    are never repeated: each row stands on its own, and a figure appearing in
    two chunks only adds a duplicate search hit.
    """
    carried: list[str] = []
    for row in reversed(body):
        if has_figures(row) or count_tokens("\n".join([row, *carried])) > OVERLAP_TOKENS:
            break
        carried.insert(0, row)
    return carried


def chunk_page(page: dict) -> list[str]:
    """Split one clean page into chunk texts made of whole rows.

    A chunk closes for one of three reasons. The budget: the next row would
    take it past TARGET_TOKENS. A new table: a unit or header row arriving
    after figures closes the chunk, so rows under one period header never
    share a chunk with rows under another. The page end: chunks never cross
    pages.
    """
    rows = [row for row in page["text"].split("\n") if row.strip()]
    texts: list[str] = []
    body: list[str] = []
    in_force: dict[str, str] = {}  # context kind -> the row currently in force

    for row in rows:
        kind = context_kind(row, page)
        if body and kind and any(has_figures(r) for r in body):
            texts.append(with_context(body, in_force, page))
            body = []
        elif body and count_tokens(with_context(body + [row], in_force, page)) > TARGET_TOKENS:
            texts.append(with_context(body, in_force, page))
            body = overlap(body)
            # Carried rows are a courtesy; if they plus this row already
            # overflow, the new chunk starts clean.
            if count_tokens(with_context(body + [row], in_force, page)) > TARGET_TOKENS:
                body = []
        # Context updates only after any close above, so a closing chunk is
        # labelled with the unit and header its own rows sat under.
        if kind:
            in_force[kind] = row
        body.append(row)

    if body:
        texts.append(with_context(body, in_force, page))
    return texts


def chunk_report(pages: list[dict]) -> list[dict]:
    """Chunk every included page, carrying the metadata the citation needs.

    {company, fiscal_year, page} rides on every chunk from day one (CLAUDE.md):
    the page is what gets cited, and v2's multi-year corpus needs the rest.
    """
    chunks = []
    for page in pages:
        if page["excluded"]:
            continue
        for index, text in enumerate(chunk_page(page)):
            chunks.append(
                {
                    "company": page["company"],
                    "fiscal_year": page["fiscal_year"],
                    "page": page["page"],
                    "chunk": index,
                    "tokens": count_tokens(text),
                    "text": text,
                }
            )
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Pack clean page records into ~200-token chunks.")
    parser.add_argument("clean", type=Path, help="clean page records from ingest.preprocess (data/)")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/chunks.jsonl"),
        help="generated artifact; disposable and gitignored",
    )
    args = parser.parse_args()

    with args.clean.open(encoding="utf-8") as f:
        pages = [json.loads(line) for line in f]
    chunks = chunk_report(pages)
    write_jsonl(chunks, args.out)

    sizes = [chunk["tokens"] for chunk in chunks]
    print(f"{len(chunks)} chunks from {len({c['page'] for c in chunks})} pages -> {args.out}")
    print(f"  tokens: min {min(sizes)}, median {statistics.median(sizes):.0f}, max {max(sizes)}")
    print(f"  over {TARGET_TOKENS} tokens: {sum(1 for s in sizes if s > TARGET_TOKENS)}")


if __name__ == "__main__":
    main()
