# Ingest step: logged during Accurate

Things that came up on Sun 04 Oct while doing the Accurate step and belong to
Ingest (Sat 10 Oct) or later. Each entry: what, the evidence, where it goes.

## Table reading costs ~0.5 s a page

pymupdf4llm's `lines` strategy takes 0.2-1.3 s per page (median ~0.4 s) with
`hdr_info=False`; without it, every single-page call rescanned the whole
document for heading sizes and one filing ran past ten minutes. The full
three-filing rebuild is now 8m50s (ingest 372 s, embed 154 s), against 2m37s
before tables. At ~30 filings, tables alone are ~75 minutes. Ingest's batch
mode should report per-filing time, and a page over 10 s is already skipped
(`MAX_SECONDS_PER_PAGE` in ingest/tables.py).

## Most statement pages in two of three filings are refused by the gates

Accepted pages: HCC 101, Chambal 63, Navneet 38. Chambal's and Navneet's
statements are shaded, not ruled, and the `lines` strategy merges a whole
column into one cell (gate: "a cell swallowed a column": Chambal 125 pages,
Navneet 100). Those pages keep preprocess's text, which reads core statements
well. A new filing's acceptance rate is worth printing at ingest time: a filing
where nothing is accepted is not an error, but it is worth knowing.

## The index grows the repository on every rebuild

Each re-index replaces ~10 MB of LanceDB files; git keeps the old ones. Two
rebuilds so far. This is the "where does the index live" decision (a release
asset or a Hugging Face dataset) arriving early: decide it before the corpus
grows, not after.

## Statement-title detection misses some statement pages

Navneet's standalone statement of profit and loss (p191) has no detected
title, so its chunks do not say "standalone". Notes pages never have one
(v2-ideas.md). hcc-fy25-003 was answered once with the consolidated p220
figure for a standalone question. The scope tag (SPEC.md §3.4) is still owed;
Ingest is where every new filing would need it.

## Carried from Accurate: a computed figure stated twice

Live check, 04 Oct (chambal-fy25-004): the answer opened "decreased by
₹146.98 crore" unlabelled, then gave the inputs and ended "(computed from
[page 98])". The grounding guard flags the first mention, correctly by the
rule, so the reader sees a warning beside a right answer. Seen in 1 of 3 eval
samples too. A prompt line ("state a computed figure once, where you label
it") is the likely fix; it needs its own eval run, so it waits.
