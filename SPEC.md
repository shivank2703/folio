# Praman — Project Specification

*praman (प्रमाण): proof, evidence. Every claim carries its source.*

**Status:** spec finalized 14 Jul 2026 · roadmap reset 03 Oct 2026 (§4) · single maintainer
**License:** AGPL-3.0 (see §7)

---

## 1. What this is

A cited research workbench over Indian listed-company filings. Ask a question, get an answer grounded **only** in the source documents, with every claim cited to the exact page it came from.

Two modes, one engine:

- **Companies** — any covered company: cited Q&A over its annual report, and (Agent step) one-page cited research memos. The user reviews the evidence and draws their own conclusions.
- **Funds** (Funds step) — a mutual fund's holdings and weights from its monthly portfolio disclosure, its costs and benchmark from its factsheet, and a drill-down into its top holdings through the company Q&A. Every claim cited.

The differentiator is the citation layer. Aggregate stats and screening are a solved problem (screener.in, Tickertape, Value Research); Praman's value is that every number and memo sentence is one click from the page that proves it.

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

Four steps, one per Saturday sitting. A step's scope is never expanded
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

### Accurate · Sat 10 Oct 2026

1. Tables via pymupdf4llm (classic table strategies, §5)
2. Eval grown to 20 questions with answer-quality scoring: a local script,
   Haiku as judge
3. Cross-encoder reranker; its score replaces the 0.67 similarity floor as the
   refusal gate (the floor stopped separating once every filing had a
   negative — `notes/v2-ideas.md`)

### Funds · Sat 17 Oct 2026

Mutual fund mode. This reverses the earlier decision to stay out of mutual
funds.

1. Read a fund's monthly portfolio disclosure (holdings + weights). It is often
   a spreadsheet: read it as a table, don't chunk it
2. Read the fund's factsheet: expense ratio, benchmark, exit load
3. Drill into the top 10–15 holdings through the annual-report Q&A
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

Trend charts (click a bar → source page), multi-year ingest, Sentinel (daily
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
| Tables | Accurate | pymupdf4llm **classic table strategies** (`page_chunks=True` preserves page numbers) | Open-source path; strong on gridlined, born-digital financial tables | Classic strategies fail on target docs |
| Table escalation | Accurate | Public table-structure models (e.g. Table Transformer) | Keeps the stack open-source | Only if triggered |
| Evaluation | Accurate | 20-question eval set, answer quality scored by a local script with Haiku as judge (RAGAS in CI cut) | No retrieval/chunking/prompt change lands without before/after scores | — |
| Reranker | Accurate | Cross-encoder; its score replaces the 0.67 similarity floor as the refusal gate | Similarity stopped separating answerable from not-in-filing questions | Eval results |
| Fund data | Funds | Portfolio disclosure read as a table (spreadsheet rows, not chunks); factsheet through the PDF path | Holdings and weights are already structured; chunking them would only lose that | — |
| Orchestration | Agent | One plain Anthropic tool-use loop over company and fund tools (LangGraph cut) | Every layer stays visible; the loop is a few dozen lines | — |

**Explicitly excluded:** PyMuPDF-Layout (the GNN/ONNX layout model) — proprietary component with its own license; excluded unless its terms are reviewed and found compatible with public distribution. LangChain, LlamaIndex, LangGraph. OCR engines (see §3.5).

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
