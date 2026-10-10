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
