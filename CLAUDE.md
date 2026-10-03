# CLAUDE.md — how we work on Folio

SPEC.md is the source of truth: scope (§1–2), corpus rules
(§3 — fiscal years, units, page-cite convention, standalone vs
consolidated, born-digital only), roadmap (§4), and tool
decisions (§5). Consult it before proposing any design. Work
proceeds one roadmap step at a time (Public → Accurate → Funds →
Agent). NEVER build ahead of the current step — flag
future-impacting decisions instead, and log anything out of
scope in the next step's notes file (e.g. notes/accurate-step.md).

## Working agreement: build first, explain after
- Build the whole step without stopping to teach. No line-by-line
  walkthroughs or comprehension questions mid-build; stop only at
  steps the plan marks as mine ([ME]).
- At the end of each sitting, run a review: walk me through what
  changed until I can explain it. Queued comprehension questions
  live in notes/review-queue.md; they never block work.
- Comments still teach, don't narrate. "# loop over pages" is
  banned; "# PyMuPDF returns blocks in reading order, so page text
  stays coherent for chunking" is the standard. Docstrings explain
  WHY. Type hints, small functions, no premature abstraction.
- Raw Python, no LangChain/LlamaIndex/LangGraph. The Agent step is
  one plain Anthropic tool-use loop.
- Suggest a git commit message after each step.

## Hard constraints
- Python 3.13, python-dotenv; keys never in code or git
- If it can't be cited to a page, the model doesn't say it
- Zero buy/sell/recommendation language anywhere, incl. prompts
- License is AGPL-3.0; never add PyMuPDF-Layout or any other
  proprietary component (SPEC.md §7)
- Born-digital PDFs only — no OCR path
- Real watchlist/holdings data is never committed
