"""Guardrails: three checks between a question and an answer worth trusting.

Stage 7 (SPEC.md §4). The system prefers silence to speculation (§2), and no
single check delivers that:

1. A similarity gate, before the model is called. If nothing retrieved
   resembles the question, the filing probably does not answer it, and the
   cheapest refusal is the one that never reaches the model.
2. The prompt's refusal contract, inside the call. Retrieval can return five
   plausible chunks that still do not answer; only something that reads them
   can tell.
3. Citation validation, after the model has spoken. Every [page N] must be a
   page that was actually in front of the model. A fabricated page number is
   the worst failure this product has: the citation is the whole promise
   (§1), and a reader cannot check it without the filing open beside them.

Since the Accurate step, the citation check also reads the figures: a page
that was shown is not enough, the number has to be printed on it. A correct
capacity cited to the page before the one that prints it passed every check
and was shown as an answer (chambal-fy25-002, evals/RESULTS.md).

A recommendation scrub runs alongside, because the project states zero
buy-or-sell language anywhere (§2) and a model that has just read a
chairman's letter can drift into it.
"""

from __future__ import annotations

import re

# What the system says when it will not answer. One wording, used by the
# prompt, by the gate, and by the checks below, so callers can recognise a
# refusal by equality instead of by guessing at phrasing.
REFUSAL = "Not in the filing."

# Calibrated twice, both times on the smoke set rather than on an eval.
# With one filing and five questions the weakest answerable question scored
# 0.732 against the not-in-the-filing question's 0.644, and the floor sat at
# their midpoint, 0.69. With three filings and nine questions the weakest
# answerable is 0.702 — a narrative page, not a statement — so the midpoint
# moved to 0.673 and the floor follows it down.
#
# The direction is the thing to watch: more documents compress the gap, which
# is the failure mode this number has. Nine questions cannot settle it; v2's
# 20-pair set (SPEC.md §4 v2.3) is what validates it or moves it again.
MIN_SIMILARITY = 0.67

CITATION = re.compile(r"\[page (\d+)\]")

# One or more adjacent citations close a claim: "... 8,743.37 crore [page 114]".
# Everything since the previous run is the claim those pages must support.
CITATION_RUN = re.compile(r"(?:\s*\[page \d+\])+")

# Figures as filings print them: Indian grouping (2,28,299), decimals, and
# parenthesised negatives, whose parentheses the comparison ignores.
FIGURE = re.compile(r"(?<![\w.])\d(?:[\d,]*\d)?(?:\.\d+)?(?![\w])")

# References written out in prose are not figures: "Based on extract [2] from
# page 220" or "Note 6.6" must not be checked as amounts the page should print.
REFERENCE = re.compile(r"\b(?:pages?|extracts?|chunks?|notes?)\s*\[?\d+(?:\.\d+)*\]?", re.IGNORECASE)

# A claim labelled this way may state a figure no page prints; the prompt
# requires the label, and the judge checks the arithmetic behind it.
COMPUTED = re.compile(r"\b(?:computed|calculated)\b", re.IGNORECASE)

# Language this project never produces (SPEC.md §2). The patterns target
# advice, not vocabulary: a filing legitimately says "the Board recommended a
# dividend", so the word "recommend" alone is not a match, while "we recommend
# buying" is.
ADVICE = re.compile(
    r"\b(?:buy|sell|short)\s+(?:the\s+)?(?:stock|shares?|scrip)\b"
    r"|\b(?:price\s+target|target\s+price)\b"
    r"|\b(?:strong\s+)?(?:buy|sell|hold)\s+(?:rating|call|recommendation)\b"
    r"|\bwe\s+recommend\s+(?:buying|selling|holding|investing)\b"
    r"|\b(?:over|under)weight\s+(?:the\s+)?(?:stock|shares)\b"
    r"|\b(?:under|over)valued\b"
    r"|\binvestment\s+advice\b",
    re.IGNORECASE,
)


def best_similarity(hits: list[dict]) -> float:
    """The closest any retrieved chunk came to the question."""
    return max((hit["score"] for hit in hits), default=0.0)


def has_enough_context(hits: list[dict]) -> bool:
    """True if anything retrieved is close enough to be worth reading.

    The gate is deliberately blunt. It cannot tell a hard question from an
    unanswerable one — only that nothing in the filing looks like this
    question, which is when an answer would be invention.
    """
    return best_similarity(hits) >= MIN_SIMILARITY


def cited_pages(text: str) -> list[int]:
    """Every page number the answer cites, in the order it cites them."""
    return [int(page) for page in CITATION.findall(text)]


def validate_citations(text: str, retrieved: set[int]) -> tuple[str, list[int]]:
    """Flag every citation to a page the model was not shown.

    The flag is left in the text rather than quietly deleted: a sentence that
    lost its citation still makes a claim, and the reader has to see that its
    support was invented. The caller decides what a flagged answer is worth.
    """
    invalid: list[int] = []

    def check(match: re.Match[str]) -> str:
        page = int(match.group(1))
        if page in retrieved:
            return match.group(0)
        invalid.append(page)
        return f"[unverified citation to page {page} — not in the retrieved context]"

    return CITATION.sub(check, text), invalid


def checkable(figure: str) -> str | None:
    """The digits of a figure worth checking against a page, or None to skip it.

    Years and one- or two-digit numbers are skipped: "March 31, 2025", "25%"
    and "5 per share" would match almost any page, so checking them proves
    nothing, and the figures this check exists for are amounts.
    """
    digits = figure.replace(",", "")
    if "," not in figure and "." not in figure:
        if len(digits) < 3 or (len(digits) == 4 and 1900 <= int(digits) <= 2099):
            return None
    return digits


def printed_figures(context: list[dict]) -> dict[int, set[str]]:
    """Every checkable figure each page in the context prints, by page."""
    printed: dict[int, set[str]] = {}
    for chunk in context:
        found = {checkable(f) for f in FIGURE.findall(chunk["text"])}
        printed.setdefault(chunk["page"], set()).update(found - {None})
    return printed


def claim_figures(claim: str) -> set[str]:
    """The figures a claim states, with written-out page and note references removed."""
    return {d for d in (checkable(f) for f in FIGURE.findall(REFERENCE.sub(" ", claim))) if d}


def split_claims(text: str) -> tuple[list[tuple[str, re.Match[str]]], str]:
    """The answer as (claim, citation run) pairs, plus any text after the last run."""
    claims, start = [], 0
    for run in CITATION_RUN.finditer(text):
        claims.append((text[start:run.start()], run))
        start = run.end()
    return claims, text[start:]


def recite(text: str, context: list[dict]) -> tuple[str, list[tuple[list[int], int]]]:
    """Move a citation to the page that prints the claim's figures, when exactly one does.

    The model sometimes reads a note number or a nearby label as the page:
    "Note 6 Trade receivables" became [page 6], and a page-5 capacity was cited
    to page 4, while the figure itself was right. The page a figure came from
    is a fact the context can settle, so the guard settles it: if the cited
    pages do not print every figure in the claim, and exactly one page in front
    of the model prints all of them, that page is cited instead. Zero or
    several candidates leave the citation alone, for the checks after this one
    to flag. Labelled computations are left alone; their result is printed
    nowhere by design. Returns the text and each correction made.
    """
    printed = printed_figures(context)
    claims, tail = split_claims(text)
    out, corrections = [], []
    for claim, run in claims:
        cited = [int(p) for p in CITATION.findall(run.group(0))]
        figures = claim_figures(claim)
        on_cited = set().union(*(printed.get(p, set()) for p in cited))
        if figures and not COMPUTED.search(claim) and not figures <= on_cited:
            pages = [page for page, found in printed.items() if figures <= found]
            if len(pages) == 1:
                corrections.append((cited, pages[0]))
                leading = run.group(0)[: len(run.group(0)) - len(run.group(0).lstrip())]
                out.append(claim + f"{leading}[page {pages[0]}]")
                continue
        out.append(claim + run.group(0))
    return "".join(out) + tail, corrections


def ungrounded_figures(text: str, context: list[dict]) -> list[tuple[str, list[int]]]:
    """Figures the answer states that are not printed on the pages it cites for them.

    The answer is cut into claims, each ending at a run of citations, and each
    claim's figures are looked up in the text of exactly those pages. Text
    after the last citation is held to every page the answer cites. A claim
    labelled as computed is exempt: its result is printed nowhere by design.
    """
    printed = printed_figures(context)
    claims, tail = split_claims(text)
    pairs = [(claim, [int(p) for p in CITATION.findall(run.group(0))]) for claim, run in claims]
    every = [page for _, pages in pairs for page in pages]
    if tail.strip() and every:
        pairs.append((tail, every))

    missing: list[tuple[str, list[int]]] = []
    for claim, pages in pairs:
        if COMPUTED.search(claim):
            continue
        on_pages = set().union(*(printed.get(page, set()) for page in pages))
        for figure in FIGURE.findall(REFERENCE.sub(" ", claim)):
            digits = checkable(figure)
            if digits and digits not in on_pages and (figure, pages) not in missing:
                missing.append((figure, pages))
    return missing


def strip_after_refusal(text: str) -> tuple[str, bool]:
    """Cut a reply that opens with the refusal down to the refusal itself.

    The contract is one sentence. A refusal followed by "but the extracts show
    ..." is a hedged half-answer, which the prompt forbids, and it was shown to
    readers as an answer because it was neither a bare refusal nor uncited.
    Returns the text to show and whether anything was cut.
    """
    stripped = text.strip()
    if stripped.startswith(REFUSAL) and stripped != REFUSAL:
        return REFUSAL, True
    return text, False


def scrub_advice(text: str) -> tuple[str, list[str]]:
    """Remove any sentence that gives investment advice, and report what was removed."""
    removed: list[str] = []
    kept: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if ADVICE.search(sentence):
            removed.append(sentence.strip())
        else:
            kept.append(sentence)
    return " ".join(kept).strip(), removed


def is_refusal(text: str) -> bool:
    """True if the model declined, in the wording the prompt asked it to use."""
    return text.strip().rstrip(".").casefold() == REFUSAL.rstrip(".").casefold()
