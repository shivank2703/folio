# Funds step: logged during Ingest

Things that came up on Sun 04 Oct while building Ingest and belong to Funds
(Sat 17 Oct) or later. Each entry: what, the evidence, where it goes.

## Carried, not done (by instruction)

- **Standalone/consolidated scope tag** (SPEC.md §3.4). Still owed; notes
  pages and some statement pages carry no scope. See notes/ingest-step.md.
- **A computed figure stated twice**, once unlabelled, flagged by the guard
  beside a right answer. One prompt line and one eval run. See
  notes/ingest-step.md.

## Two-page spreads are a new layout

Unihealth's FY26 report prints two pages on every PDF page (printed 194-195 on
PDF page 98). Extraction reads across both halves, so a left-hand table and a
right-hand table interleave row by row (p118: trade payables beside segment
information). The fix made in Ingest is narrow: a first row repeating one
statement title across both halves is that title. A spread pairing two
different documents (p65: the auditor's annexure beside the standalone balance
sheet) stays untitled. The real fix splits each spread into two reading regions
before preprocessing, keeping the PDF page as the citation (SPEC.md §3.3). Every
fund's top holdings will bring new report layouts; detect spreads (page wider
than tall, a gutter down the middle) at ingest and report them.

## pymupdf4llm leaves markdown italics in cells

Accepted table pages can carry "_Total Outstanding Dues of Micro Enterprises_"
with underscores. Harmless to the model so far; strip `_..._` in
ingest/tables.py `to_rows` at the next re-index, not before (it changes chunk
text, so it needs its own eval run).

## The exchange copy and the company copy differ

Unihealth FY26 from NSE's archive is 133 pages; the company site's copy is
132 (no cover letter to the exchange) with a different SHA-256. Folio indexes
the company copy because the investor page is what it can discover. Citations
are PDF page numbers, so the two copies' page numbers differ by one. If a
filing is ever re-sourced from the exchange, its citations shift: corpus.json
records the source URL for exactly this reason.

## Release assets accumulate

Each `ingest.publish` adds a tarball (~11-14 MB) to the "index" release and
keeps the old ones, so older commits still find their index. With 20-30
filings and frequent rebuilds, prune assets that no commit on main names.

## Regression: hcc-fy25-006 lost to the context budget

Ingest's full eval: the SOCIE question fell from 3/3 to 0/3. p118 is a seed,
six of its seven chunks reach the model, but chunk 4 (holding (1,965.62)) is
cut when the 6,000-token budget fills. Since table pages now carry their year
header into every chunk, HCC's table pages are longer and the budget fills
sooner. Candidate fixes, each needing its own before/after: fill a seed page's
chunks in reading order outward from the seed chunk before moving to the next
seed; or give the top seed's page priority over lower seeds' siblings. Do not
just raise the budget: it costs every question and dilutes attention.

## Haiku 5.5: latency and two judge disagreements

Generation moved to Claude Haiku 5.5 on 11 Oct. Mean answer latency is 3.3 s
but the worst measured was 9.7 s, just inside SPEC.md §6's ~10 s bar, because
it thinks before answering. If fund questions (longer contexts) push past it,
try effort "low" again now that the prompt rules exist (it was 37/54 before
them). The judge (still Haiku 4.5) marks two honest behaviours wrong: an
answer saying "the page does not state whether this is standalone or
consolidated" (hcc-003, hcc-008), and "150 beds is the sum of 120 and 30"
(unihealth-002) as an unlabelled computation. The scope tag fixes the first;
the second is a prompt or judge decision.

## Charging others to add a company: legal review before building

Asked 11 Oct. Not built; the in-app panel is owner-only. Before any paid
tier: (1) SEBI (Research Analysts) Regulations, 2014: whether a paid tool
over listed companies' filings, even facts-only, is research-analyst
activity needing registration (the largest risk); (2) copyright in the
reports' text, where India's fair dealing (s.52) is narrower than fair use,
especially for commercial use; (3) the maintainer's employment terms (SPEC.md
§7 clean-room note); (4) Streamlit Community Cloud's and NSE's terms for
commercial use; (5) payments through a provider (Razorpay/Stripe), GST, a
refund policy. AGPL-3.0 permits charging while the source stays public.

## Funds implementation · 17–18 October 2026

The carried scope and context-budget work is implemented. Fund data is a
reviewed public snapshot, not a personal portfolio or a live data feed.

### Disclosures and coverage

| Fund | Portfolio | Factsheet | Rows | Direct expense field | Viewer page |
|---|---|---|---:|---|---:|
| Kotak Manufacture in India | 30 Sep 2026 | 30 Sep 2026 | 62 | 0.65% BER including specified levies | 20 |
| HDFC Defence | 30 Sep 2026 | 30 Sep 2026 | 26 | 0.82% BER including specified levies | 29 |
| Motilal Oswal Nifty 500 Index | 30 Sep 2026 | 31 Aug 2026 | 500 | 0.23% total TER; 0.13% base | 5 |

The Motilal product page was checked again on 18 October and continued to link
the August passive factsheet. Its September portfolio was separately available.
The table uses disclosure dates, not download-directory names. Kotak's viewer
says October factsheet while its data and downloaded document are September.

Original XLSX cells and rendered factsheet pages were inspected. The exact
URLs, hashes, original sheet names, source row ranges, title/header/grand-total
checks and reviewed ISIN-to-company mappings live in `corpus/funds-sources.json`.
`funds.build` recreates `corpus/funds.json` from the ignored originals. No formula
is executed, no spreadsheet is chunked, and no disclosure fact is generated.
The row counts are 59 + 24 + 498 domestic equities, plus seven other rows.
Motilal's `$0.00` notation is retained as `<0.005%`; HDFC's -0.60% net current
assets remain negative. Rounded row totals use a per-row rounding tolerance.

The three top-ten selections overlap in Reliance and Mahindra, leaving 28
companies. Coverage is evaluated per fund and requires an existing corpus
entry. BEL is HDFC's largest holding but Kotak's rank 11; it remains not indexed
in Kotak. Money-market, mutual-fund and net-current-asset rows stay visible.
No Agent orchestration, personal holdings or extra report coverage was added.

### PDF quality checks

One financial-statement page and narrative reading order were inspected for
every new report. The table below records the viewer pages used, not printed
page labels. Prose checks found interleaving in several layouts; known cases
are excluded explicitly. A conservative repeated-prose-cell check excludes
other suspect pages after the ruled-table pass. The manifest records each
excluded viewer page and reason. Some valid narrative tables can be omitted;
this is a coverage limitation, not a layout repair or OCR path.

| Report | Financial table checked | Unit |
|---|---:|---|
| ASTRAMICRO | 206 | lakh |
| AXISBANK | 347 | thousand |
| BDL | 110 | lakh |
| BEL | 98 standalone; 145 consolidated | lakh |
| BEML | 197 | lakh |
| BHARATFORG | 103 | million |
| BHARTIARTL | 340 | million |
| BOSCHLTD | 276 | million |
| DEEDEV | 157 | lakh |
| DIVISLAB | 78 | crore |
| EICHERMOT | 209 | crore |
| HDFCBANK | 353 | thousand |
| HEROMOTOCO | 175 | crore |
| ICICIBANK | 145 | thousand |
| INDOMIM | 129 | INR million |
| INFY | 285 | crore |
| KOTAKBANK | 61 | thousand |
| LT | 496 | crore |
| MAHINDRA | 316 | crore |
| MTARTECH | 257 | million |
| RELIANCE | 58 | crore |
| RUBICON | 137 | million |
| SBIN | 200 | thousand, printed as 000s omitted |
| SOLARINDS | 176 | crore |
| SUNPHARMA | 161 | million |
| TATASTEEL | 302 | crore |
| TVSMOTOR | 128 | crore |
| HAL | 319 | lakh |

Indo-MIM uses the NSE copy including its exchange cover letter: 312 PDF pages.
Its standalone assets are INR40,808.66 million on viewer page 129. The
company-hosted URL redirected to its home page and was not indexed as a PDF.
The exact NSE URL and SHA-256 pin the page convention. Its narrative check was
page 4, a single-column layout. BEL's consolidated page 145 was additionally
rendered and compared for the new standalone/consolidated evaluation pair.

Verified currency-font substitutions are restricted to complete unit labels.
Long explicit "All amounts..." declarations and "000s omitted" now survive
chunking. No magnitude is inferred from the size of a financial value.

### Retrieval and answers

Every chunk stores standalone/consolidated/mixed/unstated scope, obtained from
explicit financial headings before page furniture is removed. Repeated notes
headings count; incidental prose mentions do not. Scope is shown in the source
panel and answer context. A requested scope removes the opposite explicit
scope from both vector and keyword search; mixed and unstated pages remain.

The 6,000-token budget and eight seeds are unchanged. Seed chunks are reserved
first, then the best-ranked page's continuations are completed before weaker
pages' siblings. Rank fusion includes company and fiscal year in chunk identity;
page expansion rejects mixed filings. The existing single labelled computed
figure rule is retained and evaluated; it was already present in v1.2.

Fund questions use deterministic field and holding lookups, with original
source citations. Wrong plans, incompatible dates, unsupported company-financial
questions and guidance requests return the strict refusal. Report drill-down
returns a filing to the same generation and guardrail path as Companies mode.

### Validation and release record

- Saved v1.2 baseline preserved: 44/54 answerable passed, 51/54 correct,
  49/54 faithful, 18/18 bare refusals.
- Intermediate retrieval candidate: 50/54 passed, 54/54 correct, 50/54 faithful,
  18/18 bare refusals. This is not the final expanded-corpus score.
- Local regression tests: 18 passed. Final disclosure/coverage checks: 24/24.
- Snapshot rebuild reproduced all 588 rows; compile and whitespace checks passed.
- Credential-format scan: 99 candidate files and 285 reachable history blobs,
  no detected credential values. No tracked PDFs/XLSX, `.env`, secrets file or
  real watchlist; AGPL-3.0 present; excluded proprietary/OCR dependencies absent.
- Final expanded-corpus evaluation passed 53/54 answerable samples, 54/54
  correct, 53/54 faithful and 18/18 bare refusals. Public deployed smoke tests passed. Owner-session verification and
  GitHub profile pinning remain release gates. No v1.3 tag has been created yet.
- GitHub reports the repository public. Profile currently has no pinned repos;
  pinning still needs verification through the signed-in profile interface.

### LinkedIn draft — do not publish

A number in an annual report is only useful if I can get back to the page that
supports it. I extended Folio with a public mutual-fund reader: complete
portfolio tables, cited costs and benchmarks, and annual-report Q&A for the
union of three funds' top-ten domestic equity holdings.

The interesting work was preserving evidence: spreadsheet row numbers,
independent disclosure dates, BER versus TER, financial units, and standalone
versus consolidated scope. I also fixed a retrieval-budget failure that dropped
a continuation from a page the system had already found.

The source code and measured evaluation results are public:
https://github.com/shivank2703/folio
Demo: https://folio-india.streamlit.app

Résumé bullet: Built a cited financial-document workbench with 588 public fund
portfolio rows and a 28-company annual-report drill-down, preserving original
spreadsheet-row and PDF-page provenance with deterministic disclosure checks.

### Expanded-corpus findings and fixes · 19 October

The first complete 32-filing evaluation (`funds-final.json`) passed 47/54
answerable samples, 52/54 correct, 50/54 faithful and 18/18 bare refusals.
The first new report set (`funds-reports.json`) passed only 3/12: BEL's two
balance sheets and Indo-MIM's balance sheet were outside the context.
These results were retained and blocked deployment.

BM25 was matching repeated company/scope/year headings instead of the account
label. Keyword queries now remove selected-company identity, FY tags and common
question/header words; vector ranking removes the selected code and adds the
balance-sheet context for explicit total-assets/liabilities/equity questions.
The original question representation still supplies the similarity score used
by the existing 0.67 refusal floor. Reusing the ranking rewrite for that score
incorrectly rejected Navneet's title-count question. That run was stopped and
recorded in `funds-release-interrupted.json`, rather than silently changing the
floor or discarding the evidence.

The computed-answer instruction now specifies cited inputs first and a separate
result sentence with an immediate computed label. The targeted Chambal run
passed 3/3, with no ungrounded-figure warnings; the guard was not weakened.

Decorative dotted leaders caused 268 chunks in the inspected corpus to exceed
BGE's input limit, despite fitting tiktoken's chunk budget. Dot runs of four or
more are now removed from chunk text, preserving the labels and figures. Six
filings were re-chunked; unchanged text reused its existing vector. The resulting
index has 56,112 chunks, 32 filings, 11,601 source pages, 10,015 included pages
and 1,974 included pages read by the ruled-table reader. The manifest records
1,299 quality exclusions; other excluded pages lack sufficient body text.

Ten whole rows still exceed BGE's 512-token limit (maximum 865): BDL p15,
BEL p36 (six chunks), RUBICON p70, SUNPHARMA p317 and DIVISLAB p44. Their full
text remains in keyword search and page context, but the vectors are truncated.
This limitation is recorded rather than claiming universal embedding coverage.

The new report evaluation after the query fix passed 12/12. A repeat after the
padding refresh (`funds-reports-release.json`) scored 12/12 correct and 11/12
faithful. The one disagreement: BEL's standalone total is explicitly printed
as ₹44,09,039 lakh; the answer also says ₹6,31,699 + ₹37,77,340 add up to it.
The judge called that an unlabelled computation even though the result is a
printed figure. All three values match rendered page 98. The automated failure
is retained; no manual override inflates the published score.


Final comparison (`funds-release-final.json`): 53/54 answerable passed (98%),
54/54 correct (100%), 53/54 faithful (98%), 18/18 bare refusals, zero leaks.
Against the saved v1.2 run: +9 passed, +3 correct, +4 faithful; refusals unchanged.
HCC continuation and Chambal computed cases each passed all three samples.
The remaining HCC two-column failure is retained: the judge claims the answer
contains “387 meters”, which it does not, and flags differently reported tunnel
figures that the answer attributes to separate report sections. The score has
not been manually overridden. Final retrieval smoke: 17/18 expected pages in
the top five; 16/18 exact answer strings in context. These string checks and
end-to-end judged correctness measure different things.


Deployment preparation: published the 93.1 MB checksum-pinned index asset
`folio-index-654edb14fd97.tar.gz`. A fresh anonymous download through the app's
own startup path verified the SHA-256, 56,112 chunks, all 32 filing identities
and valid scope values. The baseline file's original SHA-256 is unchanged.


### Live deployment · 19 October 2026

Deployment candidate `3281e0d` was pushed to main. Streamlit was sleeping;
waking it loaded the new Funds reader and scope-labelled index successfully.
Visitor mode showed no maintainer panel.

- Kotak: “What is the Direct-plan expense ratio?” returned 0.65% BER with
  its definition, 2026-09-30 date and factsheet viewer page 20.
- Kotak: “What is the Regular-plan expense ratio?” returned exactly
  “Not in the filing.”
- HDFC → Bharat Electronics: “What were BEL standalone total assets at the
  end of FY26?” returned ₹44,09,039 lakh on viewer page 98 in 2.39 seconds,
  with standalone-labelled source excerpts and visitor question counter.
- Additional wording probe “What were BEL standalone total assets at March
  31, 2026?” retrieved page 98 but was refused at similarity 0.663, below 0.67.
  This is a false-refusal limitation, not a deployment/index failure; the gate
  was not relaxed. The probe is retained here rather than omitted from the
  live record. A broader paraphrase evaluation is deferred in Agent notes.

Remaining user actions: privately open the live keyed owner session, let the
app remove the key from the URL, then verify its panel and no-limits status;
pin `shivank2703/folio` through the signed-in GitHub profile. The available
browser was signed out and GitHub reported zero pinned repositories. Neither
a key value nor a secret file was read for verification. Until these gates are
verified, v1.3 remains untagged. The LinkedIn draft above is not published.
