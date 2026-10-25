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

**Annual reports** of Indian listed companies — statutory filings, typically 70–400 pages. Public shipped three FY25 reports (Hindustan Construction Company, Chambal Fertilisers, Navneet Education); Ingest added Unihealth Hospitals FY26, an NSE SME listing, through `ingest.add`. One filing per company, the latest; multi-year ingest is on the "later, maybe" list.

Report anatomy the pipeline serves: Management Discussion & Analysis, Directors'/Governance/BRSR reports, financial statements (standalone **and** consolidated), notes to accounts, auditor's report.

**Funds step: mutual fund disclosures** — each fund's monthly portfolio disclosure (holdings and weights; often a spreadsheet, read as a table and never chunked) and its factsheet (expense ratio, benchmark, exit load). Citations point to the sheet and row, or the factsheet page.

### Corpus rules (the pipeline must respect these)

1. **Fiscal year = April–March.** FY25 means Apr 2024–Mar 2025. All year tags and eval questions use FY convention.
2. **Units are declared at table headers** ("₹ in crore" / "in lakhs"). Chunking must never orphan values from their unit declaration.
3. **Citations use the PDF page number** (as displayed by a PDF viewer), not the printed page number. Decided; do not revisit.
4. **Standalone vs consolidated** statements repeat the same line items with different numbers. Every chunk carries a scope tag from explicit financial headings: standalone, consolidated, mixed or unstated. Statement titles remain in chunk text where available. Never infer a missing scope.
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
   half. **Outcome: not shipped** — it lost answers on the held-out half (§5)
5. LanceDB deprecations, a full lock file, sources panel in page order,
   `#page=N` deep links
6. Eval re-run after 3 and after 4, so each change has its own before/after

### Ingest · Sun 04 Oct 2026 (pulled forward from Sat 10 Oct)

One offline command: give it a listed company and it finds the latest annual
report, downloads it, checks it is born-digital (scanned reports are skipped —
no OCR, §3.5), records the source URL and SHA-256 in `corpus/SOURCES.md`, runs
extract → chunk → embed → index, and adds the company to `corpus/corpus.json`
so it appears in the app. Idempotent; a batch mode takes a list of companies.

1. First: find out whether BSE/NSE permit automated downloads. Fallback: a
   maintained list of investor-relations URLs
2. Decide where the index lives once it outgrows git (~30 filings): a GitHub
   release asset or a Hugging Face dataset, downloaded at startup
3. No in-app "add any company" button for now. **Reversed 11 Oct 2026:** an
   owner-only "Add a company" panel in the deployed app runs the same
   `ingest.add`, uploads the index and commits the record files through the
   GitHub API. Visitors never see it. A paid version for others is not built:
   it needs legal review first (notes/funds-step.md)

**Outcome:** `python -m ingest.add CODE [CODE ...]`, `--verify`, `--force`, and
`python -m ingest.publish`. Sources (§5): company investor pages, plus
hand-listed URLs for NSE's file archive; NSE's site/API and BSE's API refuse
scripted clients and are not used. Index moved to a GitHub release asset.

Funds depends on Ingest: its top-holdings drill-down needs those companies'
annual reports indexed.

### Funds · Sat 17 Oct 2026

Mutual fund mode. This reverses the earlier decision to stay out of mutual
funds.

1. Read a fund's monthly portfolio disclosure (holdings + weights). It is often
   a spreadsheet: read it as a table, don't chunk it
2. Read the fund's factsheet: expense ratio, benchmark, exit load
3. Drill into exactly the top 10 domestic equity holdings per fund through
   annual-report Q&A; index their deduplicated union using Ingest
4. Every claim cited; no buy/sell language (§2)
5. Public demo on popular funds

**Funds implementation (17–19 Oct 2026):** Kotak Manufacture in India Direct,
HDFC Defence Direct, and Motilal Oswal Nifty 500 Index Direct Growth. September
portfolios contribute 588 instrument rows and 28 distinct top-ten companies.
Each original row keeps its weight, asset class, rank, source sheet and row;
only top-ten domestic equities are eligible. All other instruments remain
visible as not indexed, including a company covered through another fund.
Portfolio and factsheet dates remain separate: Motilal's latest linked
factsheet was August when rechecked on 18 October; the others were September.
BER/TER definitions remain attached to the disclosed percentages.

The Funds reader answers bounded factual lookups deterministically and returns
a selected annual report to the existing Q&A path. No orchestration loop is
introduced. All chunks carry explicit-heading scope (standalone, consolidated,
mixed or unstated). Search excludes an explicitly opposite scope; context
packing reserves ranked seed chunks, then prioritizes the strongest page's
continuations within the existing 6,000-token budget. Known scrambled prose
pages are excluded and recorded rather than embedded. Release status and
verification evidence are tracked in `notes/funds-step.md`.

### Agent · Sat 24 Oct 2026

1. One plain Anthropic tool-use loop (no LangGraph) over company and fund tools
2. Cited memo: one page, every sentence cited
3. Demo video and write-up

**Implementation (25 Oct 2026):** a bounded Messages API loop calls the
existing annual-report answer path and verified fund fields/rows. Final output
selects evidence IDs; Python renders their cited text against each filing's
own URL. A memo contains at most 450 words including source labels and eight
evidence selections. The UI exposes the tool trace and a Markdown download.
Six turns, eight tool calls and twelve API calls bound each request; nested
company generation and orchestration share the public daily limiter. Precise
company questions retain their original wording. Generated subquestions use
the catalog's company code in place of its legal name; dates and statement
scope are preserved. Release status is recorded in `notes/agent-step.md`.

### Cut

RAGAS in CI, LangGraph, Langfuse, further work on the text-geometry table
heuristic.

### Later, maybe

Trend charts (click a bar → source page), multi-year ingest,  Sentinel (daily
exchange-disclosure flags for a watchlist).

## 5. Architecture & tool decisions

| Layer | Step | Decision | Why | Revisit when |
|---|---|---|---|---|
| Extraction | Public | Raw PyMuPDF page text | Own every layer first; simplest page→cite mapping | Tables move to pymupdf4llm in Accurate |
| Chunking | Public | Hand-rolled ~200-token windows (tiktoken counts) | Predictable, page-faithful; failure modes stay visible | Eval evidence in Accurate |
| Embeddings | Public | **Decided at Stage 4**: BAAI/bge-small-en-v1.5, local, via fastembed (ONNX Runtime, no PyTorch) | Public demo must run free on CPU; MIT; original corpus fit its 512-token limit, with ten oversized rows recorded after Funds | Stage 5 smoke test misses relevant chunks → granite-embedding-small-english-r2 |
| Vector store | Public | LanceDB | Embedded, file-based, metadata beside vectors; nothing to host | Corpus outgrows the deploy host |
| Generation | Public → Ingest | Anthropic API, cite-every-claim prompt. **Claude Haiku 5.5** since Ingest (11 Oct 2026), effort `medium`, `max_tokens` 4,096 (thinking counts against it); was Haiku 4.5. The judge stays on Haiku 4.5 so evals stay comparable | Cheapest current model ($0.0012/question measured); at parity with 4.5 on the eval after three prompt rules (state scope as unstated rather than refuse; one labelled statement of a computed figure; answer only what was asked) | A new Haiku, or the scope tag landing |
| Report sources | Ingest | Company investor pages, read for PDF links; report URLs listed by hand in `corpus/urls.yaml` (NSE's file archive serves PDFs but cannot be listed). Plain requests with an honest User-Agent, robots.txt checked, 4 s between calls to a host | NSE's website and annual-report API reset scripted connections; BSE's API answers Access Denied. Imitating a browser to get past either is not done | An exchange publishes a documented, scriptable listing |
| Born-digital check | Ingest | Pages with no text layer are skipped and recorded; a report with more than 20% such pages is refused | A real report has a few image pages (covers, photos: 1% of HCC's); a scan has most. No OCR path (§3.5) | — |
| Two-page spreads | Ingest | A landscape page whose middle no text line crosses is read as two pages, left then right, under one PDF page number; a title is kept only if both halves name the same statement | Unihealth prints two pages per PDF page; read as one, two tables fused row by row | Spreads that pair unrelated documents need per-half titles |
| In-app add company | Ingest | Owner-only panel (owner key or localhost). Runs `ingest.add` in a background thread, then `ingest.publish` and one commit of `urls.yaml`, `corpus.json`, `SOURCES.md` and `index.json` to main via the GitHub API (a fine-grained token, this repo only, Contents: write, in the host's secrets). Refuses to commit if main's record files differ from the deployed ones; never force-pushes | The container's disk does not survive a restart, so a company added in-app must be saved to the repository to stay | Anyone else may add companies (needs payment, abuse controls and legal review) |
| Demo rate limits | Ingest → Agent | Per browser session 10 requests; per connection per day 25 model calls; all visitors per day 500. Each report generation or memo orchestration call counts; deterministic lookups and similarity-floor refusals do not. Counted in the server process; a visitor is a salted hash of their address. Local runs and a session opened with `?owner=<FOLIO_OWNER_KEY>` are exempt | The public demo spends the maintainer's prepaid credit; a multi-call memo must not bypass the shared budget | Traffic outgrows one process, or abuse comes from many addresses |
| Index storage | Ingest | A tarball on the repository's `index` release; `corpus/index.json` (committed) names it and its SHA-256; the app downloads and verifies it at startup. Not a Hugging Face dataset: `gh` is already authenticated and assets on a public repo need no credentials | Committed, every rebuild added ~10 MB to git history, and Funds adds 20–30 filings | Assets accumulate; prune those no commit names |
| Citation guard | Accurate | Every figure in a cited claim must be printed on the cited page; a computed figure must say "(computed from [page N])"; a citation is moved to the one page that prints all of a claim's figures when the cited page does not; anything after "Not in the filing." is stripped | "Shown to the model" was the only check, and a right figure cited to the wrong page passed it | — |
| UI / deploy | Public | Streamlit on Streamlit Community Cloud, deployed from the GitHub repo; the checksum-pinned release index is downloaded at startup and loaded read-only | Free; a public repo gives a public app; rebuilding on start would cost minutes on a platform that sleeps every 12h | The index outgrows what belongs in git, or the 2-core / 2.7 GB ceiling hurts the demo |
| Tables | Accurate | **pymupdf4llm 0.3.4**, `lines` strategy, accepted per page only when it passes four gates (a table found, no cell swallowing a column, no repeated rows, no figure lost against preprocess's text); every other page keeps preprocess's text. Pinned below 1.27, which hard-requires pymupdf_layout | Exact on ruled notes (ageing, borrowings, cash flow); fails on shaded or rotated statements and on `lines_strict`, so it cannot replace preprocess wholesale | A version without the layout dependency reads unruled statements |
| Table escalation | Accurate | Public table-structure models (e.g. Table Transformer) | Keeps the stack open-source | Only if triggered |
| Evaluation | Accurate | `evals.score`: 20 questions × 3 samples through the app's own answer path; two blind Haiku 4.5 calls at temperature 0 — correctness without the pages, faithfulness without the reference — plus mechanical refusal and citation checks (RAGAS in CI cut) | No retrieval/chunking/prompt change lands without before/after scores; one judge seeing both lets a wrong citation mark a right figure wrong | Judge disagreements on a re-read |
| Reranker | Accurate | **Evaluated and not shipped.** ONNX cross-encoders through fastembed (no PyTorch): ms-marco-MiniLM-L-6 and jina-reranker-v1-tiny. Gate threshold fitted on the fit half, scored on the test half: answerable test questions fell 26/27 → 19/27 end to end. The 0.67 similarity floor stays as a cheap pre-filter; refusal rests on the prompt contract and the strict-refusal guard (15/15) | A held-out half showed the fit was overfitted; reordering also lost a multi-hop page | A finance-tuned reranker, or an eval with enough negatives (≥10) to fit a threshold |
| Fund data | Funds | Verified cached XLSX cells, reviewed factsheet fields, deterministic lookups, original row/page citations; top 10 domestic equities per fund | Preserves exact weights and source dates without generating them; 28-company union feeds existing Q&A | A new public disclosure is reviewed |
| Statement scope | Funds | Explicit financial headings produce standalone/consolidated/mixed/unstated metadata on every chunk and source label | Repeated note headings survive furniture removal; unknown scope is never guessed | A verified layout needs finer per-table scope |
| Query representation | Funds | Remove selected-company and repeated metadata terms for ranking; retain the original FY-expanded question for the calibrated similarity floor | Repeated headings displaced account labels; rewriting the gate score rejected an answerable question | A separately evaluated retrieval change |
| Context packing | Funds | Reserve eight ranked seeds, then complete stronger pages before weaker continuations, within 6,000 tokens | HCC SOCIE continuation was previously omitted by distance-first expansion | Before/after retrieval evaluation reveals another coverage loss |
| Prose quality | Funds | Conservative repeated prose-cell detection and visually reviewed exclusions, recorded per viewer page | Avoid embedding visibly interleaved columns; may omit legitimate narrative tables | A separately evaluated open-source layout reader |
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
- **Data policy.** Annual reports are public statutory documents. Fund portfolio disclosures and factsheets are public documents published by each fund house. Source PDFs are not committed; `corpus/SOURCES.md` lists where to obtain them — the code ships, not the data. **Exception:** the search index, holding chunks of text derived from public statutory filings, is published (a release asset since the Ingest step; committed before) so the demo loads an index instead of rebuilding one on a host that sleeps every 12 hours. The demo attributes each filing to the issuing company and links to the source document (`corpus/SOURCES.md`); the PDF itself stays out of git. A second exception is `corpus/funds.json`: normalized **public scheme disclosures**, with exact source hashes, dates and page/row citations. Original fund PDFs and spreadsheets stay ignored; no personal holdings are included.
- **Privacy.** Real watchlists and holdings are never committed (`watchlist.yaml` stays gitignored). API keys live in `.env` and `.streamlit/secrets.toml`, both gitignored; the deployed key lives only in the host's secrets settings, with a monthly spend limit, a per-session question cap and daily per-visitor and total caps. Visitors are counted by a salted hash of their address, held in memory only.
