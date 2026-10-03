---
name: rag-eval
description: How to build and run Folio's retrieval evaluation. Use whenever creating eval Q&A pairs, running RAGAS, measuring faithfulness/relevance/context-recall, testing the reranker, or whenever ANY change touches retrieval, chunking, or prompts — always propose a before/after eval run for such changes.
---

# rag-eval

Folio's retrieval eval. The eval set formally lands in v2 (SPEC.md §4
v2.3–4); this skill is the standing contract for how it is built and used.

## The eval set
- **20 Q&A pairs**, each tagged by type:
  - `numeric-lookup` — one figure read straight off a page
  - `multi-hop` — needs two or more pages combined
  - `not-in-filing` — the honest answer is "not in the filing"
  - at least **one `units-in-crores` trap** — the value is wrong if the
    ₹-crore / lakh header unit is dropped (§3.2)
- Record **expected pages** (viewer / 1-based, §3.3) for every answerable pair.
- Questions use FY convention (FY25 = Apr 2024–Mar 2025, §3.1).
- Zero buy/sell/recommendation phrasing in questions or answers (§2).

## RAGAS metrics (one line each)
- **Faithfulness** — is every claim in the answer supported by the
  retrieved context? (catches hallucination)
- **Answer relevance** — does the answer actually address the question asked?
- **Context recall** — did retrieval pull the pages that contain the answer?

## The rule
No change to retrieval, chunking, or prompts lands without a
**before/after** eval run. Propose the run as part of the change, not after
it. This is how the cross-encoder reranker (§4 v2.5) earns or loses its place.

## Bundled
`references/eval-template.jsonl` — 3 example pairs showing the schema.
Expected answers/pages there are placeholders to fill against the real filing.
