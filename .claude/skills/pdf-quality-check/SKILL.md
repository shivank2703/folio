---
name: pdf-quality-check
description: Checklist for verifying PDF extraction quality on Indian annual reports. Use whenever extracting, parsing, chunking, or eyeballing PDF output, whenever tables look wrong, and before trusting any extracted text for embedding.
---

# PDF quality check

Run this before any extracted text is trusted for chunking or embedding,
and any time a table looks wrong. Corpus rules live in SPEC.md §3.

## (a) Reading-order sanity
- Do paragraphs flow in the order a human reads them?
- Two-column narrative pages (§3.6) can interleave columns — check a
  known two-column page, not just clean prose.
- Are running headers/footers (company name, page furniture) polluting
  the body text? They will pollute chunks and citations if left in.

## (b) Financial-table test
- Open a real financial-statement page (balance sheet / P&L).
- Is it **real text or a scanned image**? An image means the born-digital
  assumption has broken (§3.5).
- Do merged cells scramble rows, or orphan a number from its column?
- Is the unit declaration ("₹ in crore" / "in lakhs") captured with the
  table (§3.2)? A value without its unit is a wrong answer waiting to happen.

## (c) Escalation
If tables are images, or heavily merged/scrambled:
1. **STOP.** Do not embed the page.
2. Flag it against SPEC.md §3.5 (born-digital only — no OCR path).
3. Re-estimate the stage before proceeding; this is the v2 table-risk
   check surfacing early.

## (d) Tooling
`scripts/dump_page.py <pdf> <viewer-page>` prints one page's raw text
blocks with coordinates and image/text flags. The page number is the
viewer's 1-based number — the citation convention (§3.3).
