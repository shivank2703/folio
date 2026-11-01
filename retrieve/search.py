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
from retrieve.spelling import correct
from retrieve.units import attach_units

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

FIELDS = ["company", "fiscal_year", "page", "chunk", "tokens", "scope", "text", "vector"]
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

# Company, period and statement scope already constrain the search. Repeating
# them in BM25 lets ubiquitous report headers outrank the requested row label.
# Instruction words ("summarise", "key", "tell me") go too: they are how a
# reader asks, not what the page prints, and "Summarise BEL's FY26 results"
# ranked a "Summarised Cash Flows" note first on the word alone.
QUESTION_WORDS = set("what were was is are how did does do the a an at end of for to from in on its their s as and by with please give state report filing standalone consolidated financial year "
                     "summarise summarize summarised summarized summary overview describe explain tell me about key main big much many have has can you "
                     "faces face".split())

# Broad questions name a section, not a row. These are the words annual
# reports print in the headings that answer them (MD&A "Financial
# performance", "Highlights", "Risks and concerns", "Threats", "Business
# overview"); they are added to the keyword query only, so a question's own
# words still decide the vector ranking.
SECTION_WORDS = [
    (re.compile(r"\b(summari[sz]ed?|summary|overview|performance|results|highlights|how did .{1,40} do)\b", re.I),
     "financial performance highlights"),
    (re.compile(r"\b(risks?|threats?|challenges|concerns)\b", re.I), "risks concerns threats"),
    (re.compile(r"^\s*what (?:does|do|is) .{1,40}(?: do| does)?\s*\??\s*$|\bbusiness (?:model|overview)\b|\bwhat business\b", re.I),
     "business overview products"),
]


# Financial-statement line items: a question naming one with no scope gets
# consolidated candidates as well (search()).
LINE_ITEM = re.compile(r"\b(revenues?|income|turnover|sales|profits?|loss|ebitda|assets|liabilities|equity|net worth|"
                       r"borrowings|debt|cash flows?|expenses?|eps|earnings|receivables|inventor(?:y|ies)|order book)\b", re.I)


# Readers' names for line items, and the labels statements print for them.
# "Reliance's net profit" never met "Profit for the year" in the keyword
# ranking, which found subsidiaries' summaries instead. Plain string work,
# like the fiscal-year expansion: these are the labels by Schedule III.
STATEMENT_LABELS = [
    (re.compile(r"\b(net profit|pat|net income|earnings)\b", re.I), "profit for the year profit after tax"),
    (re.compile(r"\b(revenues?|sales|turnover|top line)\b", re.I), "revenue from operations"),
    (re.compile(r"\bnet worth\b", re.I), "total equity"),
    (re.compile(r"\bdebt\b", re.I), "borrowings"),
]

# The statement a line item lives in, by the title it prints: added to the
# consolidated-only ranking's words so the statement itself outranks the
# subsidiaries' one-line summaries that repeat the same labels (L&T's,
# Infosys's and Tata Steel's consolidated statements reached the top two
# only with it).
STATEMENT_TITLES = [
    (re.compile(r"\b(revenues?|income|sales|turnover|profits?|loss|ebitda|expenses?|eps|earnings)\b", re.I),
     "statement of profit and loss"),
    (re.compile(r"\b(assets|liabilities|equity|net worth|borrowings|debt|receivables|inventor(?:y|ies))\b", re.I),
     "balance sheet"),
]

# Seeds reserved for the consolidated-only ranking on an unscoped line-item
# question. Fusion alone rarely admits them: a chunk ranked by one list
# cannot outscore one both lists found, and Infosys's unscoped revenue
# question packed eight accounting-policy chunks and no statement.
CONSOLIDATED_SEEDS = 2


def company_pattern(company: str) -> str:
    """The company code as a reader might type it: "LT" also matches "L&T" and "L-T"."""
    return r"\b" + r"[\s&.-]*".join(re.escape(c) for c in company) + r"\b"


def without_company(question: str, company: str | None, replacement: str = " ") -> str:
    """A selected filing supplies identity; avoid rewarding incidental short names."""
    if not company:
        return question
    return re.sub(company_pattern(company), replacement, question, flags=re.I)


def as_subject(question: str, company: str | None) -> str:
    """The question with the company named generically, for the vector query.

    Deleting the name, as the keyword query does, left "What does Tata Steel
    do?" as "What does do?", a vector that resembles nothing. "The company"
    keeps the sentence's shape without rewarding pages that repeat the name.
    """
    return re.sub(r"\s+", " ", without_company(question, company, "the company")).strip()


def keyword_query(question: str, company: str | None) -> str:
    text = FISCAL_YEAR.sub(" ", without_company(question, company)).lower()
    words = [word for word in re.findall(r"\b\w+\b", text) if word not in QUESTION_WORDS]
    words += [extra for pattern, extra in SECTION_WORDS if pattern.search(question) for extra in extra.split()]
    words += [label for pattern, labels in STATEMENT_LABELS if pattern.search(question) for label in labels.split()]
    return " ".join(words) or question


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
    if "scope" not in table.schema.names:
        raise RuntimeError("This index predates statement-scope metadata; rebuild it with python -m ingest.build")
    return table


def scoped(query, company: str | None, scope: str | None = None, strict: bool = False):
    """Restrict a query to one filing.

    Page numbers are only unique within a document: every filing in the index
    has a page 114. Without this filter a question about total assets returns
    three balance sheets, each citation correct for a company nobody asked
    about. Comparing companies is a v3 tool, not an accident of search.
    """
    clauses = []
    if company is not None:
        clauses.append("company = '" + company.replace("'", "''") + "'")
    if scope:
        if scope not in {"standalone", "consolidated"}:
            raise ValueError("Scope must be standalone or consolidated")
        clauses.append(f"scope = '{scope}'" if strict else f"scope IN ('{scope}', 'unstated', 'mixed')")
    return query.where(" AND ".join(clauses)) if clauses else query


def vector_hits(table: lancedb.table.Table, vector: np.ndarray, company: str | None, scope: str | None = None) -> list[dict]:
    """The chunks nearest the question's vector, closest first."""
    # LanceDB is deprecating the silent addition of its score columns to a
    # selection. Naming them keeps today's output and stops a future release
    # from changing it underneath us; the ranking itself never reads them.
    query = scoped(table.search(vector).distance_type("cosine"), company, scope)
    return query.limit(FUSION_DEPTH).select([*FIELDS, "_distance"]).to_list()


def keyword_hits(table: lancedb.table.Table, text: str, company: str | None, scope: str | None = None,
                 strict: bool = False) -> list[dict]:
    """The chunks whose words best match the question, from LanceDB's full-text index."""
    query = scoped(table.search(text, query_type="fts"), company, scope, strict)
    return query.limit(FUSION_DEPTH).select([*FIELDS, "_score"]).to_list()


def fuse(rankings: list[list[dict]]) -> list[dict]:
    """Merge rankings by reciprocal rank fusion, best first.

    Each list votes with 1/(RRF_K + rank), so no shared score scale is needed.
    Cosine similarity and a full-text relevance score are not comparable, and
    rescaling them would invent a comparison the numbers do not support; their
    orderings, though, are directly comparable.
    """
    fused: dict[tuple[str, str, int, int], dict] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            key = (hit["company"], hit["fiscal_year"], hit["page"], hit["chunk"])
            entry = fused.setdefault(key, {field: hit[field] for field in FIELDS} | {"rrf": 0.0})
            entry["rrf"] += 1 / (RRF_K + rank)
    return sorted(fused.values(), key=lambda hit: -hit["rrf"])


def reserve(ranked: list[dict], wanted: list[dict], k: int) -> list[dict]:
    """The fused ranking with `wanted` guaranteed a place in its first k, at the bottom of them.

    The reserved hits keep their own fused score; what they displace are the
    weakest of the top k, which move just below the cut rather than vanish.
    """
    ids = lambda h: (h["company"], h["fiscal_year"], h["page"], h["chunk"])
    want = {ids(h) for h in wanted}
    reserved = [h for h in ranked if ids(h) in want]
    others = [h for h in ranked if ids(h) not in want]
    keep = k - len(reserved)
    return others[:keep] + reserved + others[keep:]


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
    # Misspellings are corrected against the filing's own words first, for
    # ranking and gate alike: "totla assets" matches no page and resembles
    # none (retrieve/spelling.py).
    question = correct(question, table, company)
    neutral = as_subject(question, company)
    text_query = expand_fiscal_years(neutral) if expand else neutral
    if re.search(r"\btotal (?:assets|liabilities|equity)\b", neutral, re.I) and 'balance sheet' not in neutral.lower():
        text_query += " balance sheet"
    # Keep the refusal floor on the question's own representation, not the
    # ranking rewrite: rewrites depress ordinary prose questions (a
    # publisher's title count) below the floor it is calibrated against.
    gate_query = expand_fiscal_years(question) if expand else question
    vector, gate_vector = embed_texts(model, [QUERY_INSTRUCTION + text_query,
                                             QUERY_INSTRUCTION + gate_query])
    scopes = set(re.findall(r"\b(standalone|consolidated)\b", question.lower()))
    requested_scope = next(iter(scopes)) if len(scopes) == 1 else None
    rankings = [vector_hits(table, vector, company, requested_scope)]
    if hybrid:
        keywords = keyword_query(question, company)
        rankings.append(keyword_hits(table, keywords, company, requested_scope))
        # A line item asked for with no scope should be answered from the
        # consolidated statements when the filing has them (the generator is
        # told to prefer them), so they must reach the context: "Reliance's net
        # profit" was answered standalone-only because no consolidated page
        # ranked. A third ranking over consolidated chunks alone lets them
        # compete without displacing what the question's own words found.
        titles = " ".join(title for pattern, title in STATEMENT_TITLES if pattern.search(question))
        consolidated = (keyword_hits(table, f"{keywords} {titles}".strip(), company, "consolidated", strict=True)
                        if requested_scope is None and LINE_ITEM.search(question) else [])
        if consolidated:
            rankings.append(consolidated)

    # The refusal floor's statistic: how close the nearest chunk anywhere in
    # the filing comes to the question, whatever the fused ranking kept
    # (gen/guardrails.py). One more vector query, unscoped by statement.
    nearest = scoped(table.search(gate_vector).distance_type("cosine"), company).limit(1).select(["_distance"]).to_list()
    gate = 1 - nearest[0]["_distance"] if nearest else 0.0

    ranked = fuse(rankings)
    if hybrid and consolidated:
        ranked = reserve(ranked, consolidated[:CONSOLIDATED_SEEDS], k)
    results = []
    for hit in ranked[:k]:
        stored = np.asarray(hit.pop("vector"), dtype=np.float32)
        score = float(stored @ gate_vector)
        results.append({**hit, "score": score, "gate": max(gate, score)})
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
    if len({(h['company'], h['fiscal_year']) for h in hits}) > 1:
        raise ValueError("Page context must belong to one filing")
    context = {}
    spent = 0
    for hit in hits:
        key = (hit["page"], hit["chunk"])
        if key not in context and spent + hit["tokens"] <= budget:
            context[key] = {**hit, "sibling": False}
            spent += hit["tokens"]
    spent = sum(hit["tokens"] for hit in context.values())
    first_seen: dict[int, int] = {}
    for position, hit in enumerate(hits):
        first_seen.setdefault(hit["page"], position)

    # Reserve ranked seeds first, then finish the strongest page before
    # spending on weaker pages' continuations. Distance-first expansion lost
    # HCC's SOCIE continuation even though its page was highly ranked.
    candidates: list[tuple[int, int, dict]] = []
    for hit in hits:
        # Scoped to the hit's own filing: page 114 exists in every document.
        siblings = (
            table.search()
            .where("company = '" + hit["company"].replace("'", "''") + f"' AND page = {int(hit['page'])}")
            .limit(100)
            .select(TEXT_FIELDS)
            .to_list()
        )
        for row in siblings:
            distance = abs(row["chunk"] - hit["chunk"])
            if distance:
                candidates.append((first_seen[row["page"]], distance, row))
    candidates.sort(key=lambda candidate: candidate[:2])

    for _, _, row in candidates:
        key = (row["page"], row["chunk"])
        if key in context or spent + row["tokens"] > budget:
            continue
        # A sibling was never ranked, so it carries no similarity of its own.
        context[key] = {**row, "score": None, "sibling": True}
        spent += row["tokens"]
    packed = sorted(context.values(), key=lambda row: (first_seen[row["page"]], row["chunk"]))
    # A unit declared once at a page's top belongs to every figure on it,
    # including chunks the chunker could not label (retrieve/units.py).
    return attach_units(table, packed)


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
