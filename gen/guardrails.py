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

# Calibrated on the Stage 5 smoke set: the weakest answerable question's best
# similarity was 0.732 and the not-in-the-filing question's was 0.644, so the
# midpoint leaves room on both sides. That is five questions, not an eval:
# v2's 20-pair set (SPEC.md §4 v2.3) is what validates this number or moves
# it, and it should move on evidence rather than on taste.
MIN_SIMILARITY = 0.69

CITATION = re.compile(r"\[page (\d+)\]")

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
