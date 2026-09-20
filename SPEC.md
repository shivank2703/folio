# Praman — Project Specification

*praman (प्रमाण): proof, evidence. Every claim carries its source.*

**Status:** spec finalized 14 Jul 2026 · pre-v1 · single maintainer
**License:** AGPL-3.0 (see §7)

---

## 1. What this is

A cited research workbench over Indian listed-company filings. Ask a question, get an answer grounded **only** in the source documents, with every claim cited to the exact page it came from.

Two modes, one engine:

- **Research** — any covered company: cited Q&A, multi-year trend charts, one-page cited research memos. The user reviews the evidence and draws their own conclusions.
- **Sentinel (watchlist)** — companies the user holds: material exchange disclosures are fetched daily and flagged by category and direction, every flag cited to its source document.

The differentiator is the citation layer. Aggregate stats and screening are a solved problem (screener.in, Tickertape); Praman's value is that every number, chart bar, and memo sentence is one click from the page that proves it.

## 2. What this is not (guardrails)

- **No recommendations.** Zero buy/sell/hold/target-price language anywhere — answers, memos, flags, prompts, README copy.
- **No guessing.** Low retrieval confidence returns "not in the filing." The system prefers silence to speculation.
- **Facts, not advice.** Sentinel's directional flags describe the disclosure (a rating downgrade is negative on its face); they never suggest action. The user decides.
- **Not a screener.** No aggregate rankings, scores, or "top stocks" features.

## 3. Corpus

**v1–v3: annual reports** of Indian listed companies — statutory filings, typically 200–400 pages. First company: Hindustan Construction Company (HCC). v1 scales to 3 companies; v2 adds 3+ fiscal years per company.

Report anatomy the pipeline serves: Management Discussion & Analysis, Directors'/Governance/BRSR reports, financial statements (standalone **and** consolidated), notes to accounts, auditor's report.

**v4: BSE corporate announcements and quarterly results** for watchlist companies. BSE-first: SEBI's simultaneous-disclosure rules make it sufficient for dual-listed companies, and it is more tolerant of polite automated access than NSE.

### Corpus rules (the pipeline must respect these)

1. **Fiscal year = April–March.** FY25 means Apr 2024–Mar 2025. All year tags and eval questions use FY convention.
2. **Units are declared at table headers** ("₹ in crore" / "in lakhs"). Chunking must never orphan values from their unit declaration.
3. **Citations use the PDF page number** (as displayed by a PDF viewer), not the printed page number. Decided; do not revisit.
4. **Standalone vs consolidated** statements repeat the same line items with different numbers. Chunks carry a statement-scope tag from v2 onward.
5. **Born-digital only.** Recent-year filings are text-based; there is no OCR path. If a target-year document turns out to be scanned, it is out of scope until this decision is revisited.
6. **Two-column narrative layouts** can scramble extraction order. Every new document format gets an eyeball check before its text is trusted.

## 4. Roadmap

Work proceeds strictly in order, one stage per session. The current version's scope is never expanded mid-flight; future-impacting decisions are flagged, not implemented early.

### v1 — "usable" · ships Sun 09 Aug 2026
Deployed cited Q&A over one HCC annual report.

1. Scaffold: venv, folders `ingest/ retrieve/ gen/ ui/ data/`, requirements, `.env`, `.gitignore` · ~30m
2. Extract: PyMuPDF page-wise text dump; eyeball sample pages **including one financial-table page** (real text or scan? merged cells?) — this is the v2 risk check · ~40m
3. Chunk: ~200-token windows with `{company, fiscal_year, page}` metadata → `chunks.jsonl` · ~40m
4. Embed: choose local vs API embeddings (decision gate, see §5), batch-embed → LanceDB · ~40m
5. Retrieve: top-k search + CLI smoke test on 5 real questions · ~40m
6. Generate: Anthropic API, cite-every-claim prompt → answer + [page] cites · ~45m
7. Guardrails: low-score → "not in the filing"; scrub recommendation language · ~30m
8. UI: Streamlit question box → answer + expandable cited-sources panel · ~45m
9. Scale: batch-ingest 2 more companies' filings · ~40m
10. Deploy: Streamlit Community Cloud from the GitHub repo + README with demo GIF → **ship v1** · ~45m

### v2 — "good" · ships Sun 13 Sep 2026

1. Table extraction → structured rows (target Sun 16 Aug)
2. Multi-year ingest with fiscal-year tags (Sat 22 Aug)
3. Eval set: 20 tagged Q&A pairs — numeric-lookup / multi-hop / not-in-filing / one units-in-crores trap — with expected pages recorded (Sat 29 Aug)
4. RAGAS harness in CI: faithfulness, answer relevance, context recall (Sat 05 Sep)
5. Cross-encoder reranker — **sacrificial: cut if table extraction overruns** (Wed 09 Sep)
6. Public repo: architecture diagram + writeup + license → **ship v2** (Sun 13 Sep)

### v3 — "crazy good" · ships Wed 07 Oct 2026 · **HARD DATE**

1. Agent tools: compare-companies, fetch-filing (Sat 19 Sep)
2. LangGraph loop: picks tools, always cites (Sat 26 Sep)
3. Cited memo generator: one page, every claim cited (Wed 30 Sep)
4. Cited trend charts: revenue/profit/debt + promoter holding (from shareholding-pattern disclosures); **click a bar → source page** (Sat 03 Oct)
5. Static eval-results table in README; Langfuse if time; buffer → **ship v3** (Wed 07 Oct)

Cut order if behind: Langfuse → charts. The agent loop and memo generator are never cut. The date never moves; scope does.

### v4 — "Sentinel" · ships ~Sun 22 Nov 2026 (soft)

1. Watchlist config (YAML) + private-instance mode — `watchlist.sample.yaml` ships, real watchlists are gitignored (Sat 17 Oct)
2. Disclosure fetcher: daily BSE announcements + quarterly-results pull, cached, rate-limited (Sat 31 Oct)
3. Materiality flags: category (results / litigation / rating change / pledge / order win / board change) + direction, every flag cited (Sat 07 Nov)
4. "What changed" digest: per-company timeline + quarterly-delta memo, reusing the memo generator (Sat 14 Nov)
5. Weekly Telegram/email digest → **ship v4** (Sun 22 Nov)

**Every ship:** secrets scan (including git history) → confirm no real watchlist data → README current (what/why, architecture, demo GIF, run-locally) → deploy + 3-question smoke test → license check → git tag.

## 5. Architecture & tool decisions

| Layer | Version | Decision | Why | Revisit when |
|---|---|---|---|---|
| Extraction | v1 | Raw PyMuPDF page text | Own every layer first; simplest page→cite mapping | Never for v1 |
| Chunking | v1 | Hand-rolled ~200-token windows (tiktoken counts) | Predictable, page-faithful; failure modes stay visible | Eval evidence in v2 |
| Embeddings | v1 | **Decided at Stage 4**: BAAI/bge-small-en-v1.5, local, via fastembed (ONNX Runtime, no PyTorch) | Public demo must run free on CPU; MIT; largest chunk (393 tokens) fits its 512 limit | Stage 5 smoke test misses relevant chunks → granite-embedding-small-english-r2 |
| Vector store | v1 | LanceDB | Embedded, file-based, metadata beside vectors; nothing to host | Corpus outgrows the deploy host |
| Generation | v1 | Anthropic API, cite-every-claim prompt | Cheap model + rate limit on the public app | — |
| UI / deploy | v1 | Streamlit on Streamlit Community Cloud, deployed from the GitHub repo; the committed index is loaded read-only | Free; a public repo gives a public app; rebuilding on start would cost minutes on a platform that sleeps every 12h | The index outgrows what belongs in git, or the 2-core / 2.7 GB ceiling hurts the demo |
| Tables | v2 | pymupdf4llm **classic table strategies** (`page_chunks=True` preserves page numbers) | Open-source path; strong on gridlined, born-digital financial tables | Classic strategies fail on target docs |
| Table escalation | v2 | Public table-structure models (e.g. Table Transformer) | Keeps the stack open-source | Only if triggered |
| Evaluation | v2 | RAGAS over the tagged eval set, run in CI | No retrieval/chunking/prompt change lands without before/after scores | — |
| Reranker | v2 | sentence-transformers cross-encoder | Kept only if the eval delta earns its latency | Eval results |
| Orchestration | v3 | LangGraph | Introduced only after the raw pipeline exists and is understood | — |
| Charts | v3 | Plotly in Streamlit | Click-through to source page is the requirement — charts are citation UI | — |
| Observability | v3 | Langfuse (if time) | First on the cut list | — |
| Fetch/schedule | v4 | requests + GitHub Actions cron | Daily, cached, polite; the fetcher ships, the data doesn't | — |
| Classification | v4 | One Claude call per disclosure → category + direction + citation | — | — |
| Digest | v4 | Telegram bot (SMTP fallback) | Avoids email-deliverability pain | — |

**Explicitly excluded:** PyMuPDF-Layout (the GNN/ONNX layout model) — proprietary component with its own license; excluded unless its terms are reviewed and found compatible with public distribution. LangChain/LlamaIndex before v3. OCR engines (see §3.5).

## 6. Quality bars

- A covered-filing question returns a correct answer with working page citations, or an honest "not in the filing" — never an uncited claim.
- Every chart datum and memo sentence is click-traceable to its source page.
- The public app answers in roughly ≤10s on the free tier.
- Eval scores are published (static table in README from v3) and move only with evidence.

## 7. Licensing, IP & data policy

- **Repo license: AGPL-3.0.** PyMuPDF and pymupdf4llm are AGPL-dual-licensed and this app is network-served, so AGPL is the clean, compliant choice.
- **Clean-room policy.** The author works professionally in an adjacent domain. This project shares only public open-source libraries with that work — no code, configurations, heuristics, prompts, or models originate from any employer. Built entirely from public documentation, on personal time and hardware.
- **Data policy.** Annual reports are public statutory documents. The v4 fetcher runs on each user's own instance against their own watchlist; this repository redistributes no exchange data. Source PDFs are not committed; `corpus/SOURCES.md` lists where to obtain them — the same principle as the v4 fetcher (the code ships, not the data). **v1 exception:** `data/lancedb/` ships, holding chunks of text derived from a public statutory filing, so the demo loads an index instead of rebuilding one on a host that sleeps every 12 hours. The demo attributes the filing to the issuing company and links to the source document (`corpus/SOURCES.md`); the PDF itself stays out of git.
- **Privacy.** Real watchlists and holdings are never committed (`watchlist.yaml` gitignored; only `watchlist.sample.yaml` ships). API keys live in `.env`, gitignored; the public demo uses a rate-limited key.
