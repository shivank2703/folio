# CLAUDE.md — how we work on Praman

SPEC.md is the source of truth: scope (§1–2), corpus rules
(§3 — fiscal years, units, page-cite convention, standalone vs
consolidated, born-digital only), roadmap (§4), and tool
decisions (§5). Consult it before proposing any design. We are
in v1. NEVER build ahead of the current stage or version — flag
future-impacting decisions instead (e.g. chunk metadata carries
company + fiscal_year + page from day one because v2/v4 need it).

## Teaching mode (non-negotiable)
- Before each stage: the plan in plain English — the 1–2 design
  decisions, the alternatives, why this choice.
- Comments teach, don't narrate. "# loop over pages" is banned;
  "# PyMuPDF returns blocks in reading order, so page text stays
  coherent for chunking" is the standard. Docstrings explain
  WHY. Type hints, small functions, no premature abstraction.
- After each file: walk me through it top to bottom, ask 2–3
  comprehension questions, and WAIT for my answers.
- ONE stage per session; STOP at stage end. I work in 25–45 min
  sittings.
- Raw Python in v1 — no LangChain/LlamaIndex until v3. I need
  to see every layer.
- Suggest a git commit message after each stage.

## Hard constraints
- Python 3.11+, python-dotenv; keys never in code or git
- If it can't be cited to a page, the model doesn't say it
- Zero buy/sell/recommendation language anywhere, incl. prompts
- License is AGPL-3.0; never add PyMuPDF-Layout or any other
  proprietary component (SPEC.md §7)
- Born-digital PDFs only — no OCR path
- Real watchlist/holdings data is never committed
