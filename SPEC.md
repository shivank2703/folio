# Folio — Project Specification

*folio: a numbered page of a book or filing. Every claim carries the folio it came from.*

*Renamed from Praman on 03 Oct 2026; the history before that date uses the old name.*

**Status:** spec finalized 14 Jul 2026 · roadmap reset 03 Oct 2026 (§4) · single maintainer
**License:** AGPL-3.0 (see §7)

---

## 1. What this is

A cited research workbench over Indian listed-company filings. Ask a question, get an answer grounded **only** in the source documents, with every claim cited to the exact page it came from.

Two modes, one engine:

- **Companies** — any covered company: cited Q&A over its annual report, and (Agent step) one-page cited research memos. The user reviews the evidence and draws their own conclusions.
- **Funds** (Funds step) — a mutual fund's holdings and weights from its monthly portfolio disclosure, its costs and benchmark from its factsheet, and a drill-down into its top holdings through the company Q&A. Every claim cited.

The differentiator is the citation layer. Aggregate stats and screening are a solved problem (screener.in, Tickertape, Value Research); Folio's value is that every number and memo sentence is one click from the page that proves it.

## 2. What this is not (guardrails)

- **No recommendations.** Zero buy/sell/hold/target-price language anywhere — answers, memos, flags, prompts, README copy.
- **No guessing.** Low retrieval confidence returns "not in the filing." The system prefers silence to speculation.
- **Facts, not advice.** A fund's holdings, costs and benchmark are reported as disclosed; nothing says whether to buy, hold, switch or exit it. The user decides.
- **Not a screener.** No aggregate rankings, scores, or "top stocks" features.

## 3. Corpus

**Annual reports** of Indian listed companies — statutory filings, typically 200–400 pages. Public ships three FY25 reports: Hindustan Construction Company (HCC), Chambal Fertilisers and Navneet Education. Multi-year ingest is on the "later, maybe" list.

Report anatomy the pipeline serves: Management Discussion & Analysis, Directors'/Governance/BRSR reports, financial statements (standalone **and** consolidated), notes to accounts, auditor's report.

**Funds step: mutual fund disclosures** — each fund's monthly portfolio disclosure (holdings and weights; often a spreadsheet, read as a table and never chunked) and its factsheet (expense ratio, benchmark, exit load). Citations point to the sheet and row, or the factsheet page.

### Corpus rules (the pipeline must respect these)

1. **Fiscal year = April–March.** FY25 means Apr 2024–Mar 2025. All year tags and eval questions use FY convention.
2. **Units are declared at table headers** ("₹ in crore" / "in lakhs"). Chunking must never orphan values from their unit declaration.
3. **Citations use the PDF page number** (as displayed by a PDF viewer), not the printed page number. Decided; do not revisit.
4. **Standalone vs consolidated** statements repeat the same line items with different numbers. Chunks carry a statement-scope tag once table work (Accurate) lands; until then a statement page's title is inherited by every chunk on it.
5. **Born-digital only.** Recent-year filings are text-based; there is no OCR path. If a target-year document turns out to be scanned, it is out of scope until this decision is revisited.
6. **Two-column narrative layouts** can scramble extraction order. Every new document format gets an eyeball check before its text is trusted.

## 4. Roadmap

Five steps, roughly one per Saturday sitting. A step's scope is never expanded
mid-flight; anything that comes up for a later step is logged in that step's
notes file, not built. Dates are targets; scope moves before dates do.

**Every ship:** secrets scan (including git history) → confirm no real
holdings data and no corpus PDFs → README current (what/why, architecture,
demo GIF, run-locally, roadmap) → deploy + one answerable and one
not-in-filing question on the live app → license check → git tag.

### Public · Sat 03 Oct 2026 — done when the demo is live

Cited Q&A over three FY25 annual reports (HCC, Chambal Fertilisers, Navneet
Education), built in v1 Stages 1–9 (history in `notes/v1-handoffs.md`).

1. Rename to Folio (repo, package, UI, docs); history kept
2. API key in place; generation run on all 11 eval questions; fix only what
   blocks a correct answer
3. Demo safety: at most 10 questions per visitor session
4. Deploy on Streamlit Community Cloud (Python 3.13), repo public
5. README with live link, demo GIF and roadmap → tag **v1.0**

### Accurate · Sun 04 Oct 2026 (pulled forward from Sat 10 Oct)

1. Eval first: 20 questions (the 11, plus multi-hop, a units trap, a computed
   figure, and tables from the known-bad pages), scored by a local script with
   Haiku as judge — faithfulness to the cited pages, correctness against the
   expected answer, refusal correctness. Baseline committed before any change.
2. Computed figures only when labelled as computed with every input cited
   ("an increase of ₹605.34 crore (computed from [page 114])"). Refusals are
   strict: exactly "Not in the filing."; anything after it is stripped, and the
   eval fails a non-bare refusal.
3. Tables via pymupdf4llm (classic table strategies, §5); all filings
   re-indexed; known-bad pages checked by eye
4. Cross-encoder reranker; its score replaces the 0.67 similarity floor as the
   refusal gate. Threshold fitted on half the questions, reported on the other
   half
5. LanceDB deprecations, a full lock file, sources panel in page order,
   `#page=N` deep links
6. Eval re-run after 3 and after 4, so each change has its own before/after

### Ingest · Sat 10 Oct 2026

One offline command: give it a listed company and it finds the latest annual
report, downloads it, checks it is born-digital (scanned reports are skipped —
no OCR, §3.5), records the source URL and SHA-256 in `corpus/SOURCES.md`, runs
extract → chunk → embed → index, and adds the company to `corpus/corpus.json`
so it appears in the app. Idempotent; a batch mode takes a list of companies.

1. First: find out whether BSE/NSE permit automated downloads. Fallback: a
   maintained list of investor-relations URLs
2. Decide where the index lives once it outgrows git (~30 filings): a GitHub
   release asset or a Hugging Face dataset, downloaded at startup
3. No in-app "add any company" button for now

Funds depends on Ingest: its top-holdings drill-down needs those companies'
annual reports indexed.

### Funds · Sat 17 Oct 2026

Mutual fund mode. This reverses the earlier decision to stay out of mutual
funds.

1. Read a fund's monthly portfolio disclosure (holdings + weights). It is often
   a spreadsheet: read it as a table, don't chunk it
2. Read the fund's factsheet: expense ratio, benchmark, exit load
3. Drill into the top 10–15 holdings through the annual-report Q&A, using
   companies indexed by Ingest
4. Every claim cited; no buy/sell language (§2)
5. Public demo on popular funds

### Agent · Sat 24 Oct 2026

1. One plain Anthropic tool-use loop (no LangGraph) over company and fund tools
2. Cited memo: one page, every sentence cited
3. Demo video and write-up

### Cut

RAGAS in CI, LangGraph, Langfuse, further work on the text-geometry table
heuristic.

### Later, maybe

Trend charts (click a bar → source page), multi-year ingest, an in-app
"add any company" button, Sentinel (daily
exchange-disclosure flags for a watchlist).

## 5. Architecture & tool decisions

| Layer | Step | Decision | Why | Revisit when |
|---|---|---|---|---|
| Extraction | Public | Raw PyMuPDF page text | Own every layer first; simplest page→cite mapping | Tables move to pymupdf4llm in Accurate |
| Chunking | Public | Hand-rolled ~200-token windows (tiktoken counts) | Predictable, page-faithful; failure modes stay visible | Eval evidence in Accurate |
| Embeddings | Public | **Decided at Stage 4**: BAAI/bge-small-en-v1.5, local, via fastembed (ONNX Runtime, no PyTorch) | Public demo must run free on CPU; MIT; largest chunk (393 tokens) fits its 512 limit | Stage 5 smoke test misses relevant chunks → granite-embedding-small-english-r2 |
| Vector store | Public | LanceDB | Embedded, file-based, metadata beside vectors; nothing to host | Corpus outgrows the deploy host |
| Generation | Public | Anthropic API (Haiku), cite-every-claim prompt | Cheap model + a per-session question cap on the public app | — |
| UI / deploy | Public | Streamlit on Streamlit Community Cloud, deployed from the GitHub repo; the committed index is loaded read-only | Free; a public repo gives a public app; rebuilding on start would cost minutes on a platform that sleeps every 12h | The index outgrows what belongs in git, or the 2-core / 2.7 GB ceiling hurts the demo |
| Tables | Accurate | **pymupdf4llm 0.3.4**, `lines` strategy, accepted per page only when it passes four gates (a table found, no cell swallowing a column, no repeated rows, no figure lost against preprocess's text); every other page keeps preprocess's text. Pinned below 1.27, which hard-requires pymupdf_layout | Exact on ruled notes (ageing, borrowings, cash flow); fails on shaded or rotated statements and on `lines_strict`, so it cannot replace preprocess wholesale | A version without the layout dependency reads unruled statements |
| Table escalation | Accurate | Public table-structure models (e.g. Table Transformer) | Keeps the stack open-source | Only if triggered |
| Evaluation | Accurate | `evals.score`: 20 questions × 3 samples through the app's own answer path; two blind Haiku 4.5 calls at temperature 0 — correctness without the pages, faithfulness without the reference — plus mechanical refusal and citation checks (RAGAS in CI cut) | No retrieval/chunking/prompt change lands without before/after scores; one judge seeing both lets a wrong citation mark a right figure wrong | Judge disagreements on a re-read |
| Reranker | Accurate | Cross-encoder; its score replaces the 0.67 similarity floor as the refusal gate | Similarity stopped separating answerable from not-in-filing questions | Eval results |
| Fund data | Funds | Portfolio disclosure read as a table (spreadsheet rows, not chunks); factsheet through the PDF path | Holdings and weights are already structured; chunking them would only lose that | — |
| Orchestration | Agent | One plain Anthropic tool-use loop over company and fund tools (LangGraph cut) | Every layer stays visible; the loop is a few dozen lines | — |

**Explicitly excluded:** PyMuPDF-Layout (`pymupdf_layout`, the GNN/ONNX layout model) — proprietary component with its own license; excluded unless its terms are reviewed and found compatible with public distribution. pymupdf4llm 1.27+ requires it, so pymupdf4llm stays on 0.3.4, where it is an optional extra that is not installed. LangChain, LlamaIndex, LangGraph. OCR engines (see §3.5).

## 6. Quality bars

- A covered-filing question returns a correct answer with working page citations, or an honest "not in the filing" — never an uncited claim.
- Every memo sentence is click-traceable to its source page.
- The public app answers in roughly ≤10s on the free tier.
- Eval scores are published (static table in README from Accurate) and move only with evidence.

## 7. Licensing, IP & data policy

- **Repo license: AGPL-3.0.** PyMuPDF and pymupdf4llm are AGPL-dual-licensed and this app is network-served, so AGPL is the clean, compliant choice.
- **Clean-room policy.** The author works professionally in an adjacent domain. This project shares only public open-source libraries with that work — no code, configurations, heuristics, prompts, or models originate from any employer. Built entirely from public documentation, on personal time and hardware.
- **Data policy.** Annual reports are public statutory documents. Fund portfolio disclosures and factsheets are public documents published by each fund house. Source PDFs are not committed; `corpus/SOURCES.md` lists where to obtain them — the code ships, not the data. **Exception:** `data/lancedb/` ships, holding chunks of text derived from public statutory filings, so the demo loads an index instead of rebuilding one on a host that sleeps every 12 hours. The demo attributes each filing to the issuing company and links to the source document (`corpus/SOURCES.md`); the PDF itself stays out of git.
- **Privacy.** Real watchlists and holdings are never committed (`watchlist.yaml` stays gitignored). API keys live in `.env` and `.streamlit/secrets.toml`, both gitignored; the deployed key lives only in the host's secrets settings, with a monthly spend limit and a per-session question cap.
