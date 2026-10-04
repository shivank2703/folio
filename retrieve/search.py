"""Search: a question in, the top-k chunks out, each with the page it cites.

Stage 5 (SPEC.md §4), with the two findings its smoke test produced folded in.

The query side must mirror the index side exactly, so this file borrows the
model and the embedding function from embed.py rather than restating them, and
refuses to search an index built with another model.

Fiscal years are expanded into the dates the filing prints. Questions follow
the FY convention (SPEC.md §3.1) while the statements say "As at March 31,
2025" and "Year ended March 31, 2025", so the words never met and a question
about the balance sheet's headline figure ranked it 23rd. The expansion is
plain string work, never a model call: FY25 ends on 31 March 2025 by
definition, a rule rather than a judgement.

Retrieval is hybrid. A question's phrasing resembles prose, while a table row
answers through labels ("TOTAL ASSETS") that keyword search matches exactly.
LanceDB's own full-text index supplies the keyword side, so no BM25 dependency
is added, and the two rankings merge by reciprocal rank fusion: a chunk ranked
well by either method rises, and one ranked well by both rises fastest.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import lancedb
import numpy as np
from fastembed import TextEmbedding

from retrieve.embed import MODEL_NAME, TABLE_NAME, embed_texts, load_model

# bge-small-en-v1.5 was trained with this instruction in front of queries and
# nothing in front of passages. Chunks were embedded bare, so every question
# gets it here; fastembed does not add it for this model.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

DEFAULT_K = 5

# How deep each ranking runs before the two are merged: deeper than any k a
# caller asks for, so a chunk that only one method ranks well still competes.
FUSION_DEPTH = 50

# Reciprocal rank fusion's damping constant. At 60, rank 1 contributes 1/61 and
# rank 10 contributes 1/70: the head of each list matters, and neither list can
# dictate the result alone.
RRF_K = 60

# "FY25", "FY 25", "FY2025", "FY24-25", "FY 2024-25".
FISCAL_YEAR = re.compile(r"\bFY\s?(\d{4}|\d{2})(?:\s*[-–]\s*(\d{4}|\d{2}))?\b", re.IGNORECASE)

FIELDS = ["company", "fiscal_year", "page", "chunk", "tokens", "text", "vector"]
TEXT_FIELDS = [field for field in FIELDS if field != "vector"]

# How many tokens of chunk text the model may be given, and how far down the
# ranking the pages worth widening are looked for.
#
# Seeding only from the chunks shown was too narrow once the index held three
# filings: full-text scores are computed over the whole collection, so adding
# two annual reports shifted the keyword ranking of the first one, and a
# balance sheet that had ranked fifth ranked sixth — outside the seeds, so its
# answer never entered the context however large the budget grew.
#
# Swept over all eight answerable smoke questions: 5 seeds reached 6/8 at any
# budget, 8 seeds reached 7/8 at 4,000 tokens and 8/8 at 6,000. That costs
# about 32 chunks of context per question. The sharper fix is ranking that
# puts the answer-bearing chunk first, which v2's eval set is there to drive.
CONTEXT_TOKENS = 6000
EXPANSION_SEEDS = 8


def expand_fiscal_years(question: str) -> str:
    """Append the period-end dates for every fiscal year the question names.

    SPEC.md §3.1 fixes the convention: FY25 runs April 2024 to March 2025, so
    it ends on 31 March 2025, which the filing prints as "As at March 31,
    2025". One phrase per year, and no more: appending the profit-and-loss
    form ("year ended ...") as well was measured and was worse, because two
    date phrases per year outweigh the question's own words — the balance
    sheet question fell from rank 5 to outside the top 20. The question's own
    wording is kept, so nothing that already matched stops matching.
    """
    years: list[int] = []
    for match in FISCAL_YEAR.finditer(question):
        digits = match.group(2) or match.group(1)
        year = int(digits) + 2000 if len(digits) == 2 else int(digits)
        if year not in years:
            years.append(year)
    dates = " ".join(f"as at March 31, {year}" for year in years)
    return f"{question} {dates}" if dates else question


def open_index(db_path: Path) -> lancedb.table.Table:
    """Open the chunks table, refusing one built with a different model.

    Vectors from two models share no geometry. A question embedded with one and
    searched against the other still returns k chunks with ordinary-looking
    scores, none of them relevant. The model name stored at embed time turns
    that silent failure into an error.
    """
    table = lancedb.connect(str(db_path)).open_table(TABLE_NAME)
    built_with = (table.schema.metadata or {}).get(b"embedding_model", b"").decode()
    if built_with != MODEL_NAME:
        raise RuntimeError(
            f"{db_path} was embedded with {built_with or 'an unrecorded model'}, not {MODEL_NAME}; "
            "re-run python -m retrieve.embed"
        )
    return table


def scoped(query, company: str | None):
    """Restrict a query to one filing.

    Page numbers are only unique within a document: every filing in the index
    has a page 114. Without this filter a question about total assets returns
    three balance sheets, each citation correct for a company nobody asked
    about. Comparing companies is a v3 tool, not an accident of search.
    """
    return query if company is None else query.where(f"company = '{company}'")


def vector_hits(table: lancedb.table.Table, vector: np.ndarray, company: str | None) -> list[dict]:
    """The chunks nearest the question's vector, closest first."""
    # LanceDB is deprecating the silent addition of its score columns to a
    # selection. Naming them keeps today's output and stops a future release
    # from changing it underneath us; the ranking itself never reads them.
    query = scoped(table.search(vector).distance_type("cosine"), company)
    return query.limit(FUSION_DEPTH).select([*FIELDS, "_distance"]).to_list()


def keyword_hits(table: lancedb.table.Table, text: str, company: str | None) -> list[dict]:
    """The chunks whose words best match the question, from LanceDB's full-text index."""
    query = scoped(table.search(text, query_type="fts"), company)
    return query.limit(FUSION_DEPTH).select([*FIELDS, "_score"]).to_list()


def fuse(rankings: list[list[dict]]) -> list[dict]:
    """Merge rankings by reciprocal rank fusion, best first.

    Each list votes with 1/(RRF_K + rank), so no shared score scale is needed.
    Cosine similarity and a full-text relevance score are not comparable, and
    rescaling them would invent a comparison the numbers do not support; their
    orderings, though, are directly comparable.
    """
    fused: dict[tuple[int, int], dict] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            key = (hit["page"], hit["chunk"])
            entry = fused.setdefault(key, {field: hit[field] for field in FIELDS} | {"rrf": 0.0})
            entry["rrf"] += 1 / (RRF_K + rank)
    return sorted(fused.values(), key=lambda hit: -hit["rrf"])


def search(
    table: lancedb.table.Table,
    model: TextEmbedding,
    question: str,
    k: int = DEFAULT_K,
    company: str | None = None,
    expand: bool = True,
    hybrid: bool = True,
) -> list[dict]:
    """Return the k chunks most likely to answer the question, best first.

    Every result carries both scores it was judged by: "rrf" orders the list,
    while "score" is cosine similarity to the question, which stays comparable
    across questions — the number Stage 7 needs when deciding that the filing
    does not answer at all. The expand and hybrid switches exist so a change
    here can be measured against the retrieval it replaces (rag-eval).
    """
    text_query = expand_fiscal_years(question) if expand else question
    vector = embed_texts(model, [QUERY_INSTRUCTION + text_query])[0]
    rankings = [vector_hits(table, vector, company)]
    if hybrid:
        rankings.append(keyword_hits(table, text_query, company))

    results = []
    for hit in fuse(rankings)[:k]:
        stored = np.asarray(hit.pop("vector"), dtype=np.float32)
        results.append({**hit, "score": float(stored @ vector)})
    return results


def page_context(
    table: lancedb.table.Table,
    hits: list[dict],
    budget: int = CONTEXT_TOKENS,
    seeds: int = EXPANSION_SEEDS,
) -> list[dict]:
    """Widen the ranked chunks to their page siblings, nearest first, within a budget.

    SPEC.md §3.3 makes the page the citation unit, so the other chunks of a
    retrieved page are the same citable source — already trusted, already
    cite-able to the same number. They are also where the answer often sits: a
    question about total assets matched the balance sheet's opening chunk while
    the TOTAL ASSETS row was two chunks further down, and a page that is
    retrieved but cannot answer is no better than a miss.

    Pages are widened in the order their best chunk ranked, so a weak page never
    crowds out a strong one, and the result reads in page order: page by page,
    chunks in the order the page prints them. Seeds reach deeper than the
    chunks a caller shows, because the page holding the answer is often ranked
    just below them.
    """
    hits = hits[:seeds]
    context = {(hit["page"], hit["chunk"]): {**hit, "sibling": False} for hit in hits}
    spent = sum(hit["tokens"] for hit in context.values())
    first_seen: dict[int, int] = {}
    for position, hit in enumerate(hits):
        first_seen.setdefault(hit["page"], position)

    # Candidates are ordered by distance first and rank second: every hit gets
    # its immediate neighbours before any hit gets its far ends. Ordering by
    # page instead let the first page swallow the budget, and the page ranked
    # fifth - the one holding the answer - never got its turn.
    candidates: list[tuple[int, int, dict]] = []
    for hit in hits:
        # Scoped to the hit's own filing: page 114 exists in every document.
        siblings = (
            table.search()
            .where(f"company = '{hit['company']}' AND page = {hit['page']}")
            .limit(100)
            .select(TEXT_FIELDS)
            .to_list()
        )
        for row in siblings:
            distance = abs(row["chunk"] - hit["chunk"])
            if distance:
                candidates.append((distance, first_seen[row["page"]], row))
    candidates.sort(key=lambda candidate: candidate[:2])

    for _, _, row in candidates:
        key = (row["page"], row["chunk"])
        if key in context or spent + row["tokens"] > budget:
            continue
        # A sibling was never ranked, so it carries no similarity of its own.
        context[key] = {**row, "score": None, "sibling": True}
        spent += row["tokens"]
    return sorted(context.values(), key=lambda row: (first_seen[row["page"]], row["chunk"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Top-k hybrid search over the chunk index.")
    parser.add_argument("question", help="a question about the filing, in plain English")
    parser.add_argument("-k", type=int, default=DEFAULT_K, help="how many chunks to return")
    parser.add_argument("--db", type=Path, default=Path("data/lancedb"), help="LanceDB directory from retrieve.embed")
    parser.add_argument("--company", help="restrict the search to one filing, e.g. HCC")
    parser.add_argument("--no-expand", action="store_true", help="skip fiscal-year expansion")
    parser.add_argument("--vector-only", action="store_true", help="skip the keyword ranking")
    args = parser.parse_args()

    table = open_index(args.db)
    hits = search(
        table, load_model(), args.question, args.k, args.company,
        expand=not args.no_expand, hybrid=not args.vector_only,
    )
    for rank, hit in enumerate(hits, start=1):
        opening = hit["text"].split("\n")[0]
        print(f"{rank}. {hit['company']} p{hit['page']} chunk {hit['chunk']}  cos {hit['score']:.3f}  {opening[:72]}")


if __name__ == "__main__":
    main()
