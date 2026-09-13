# v1 handoffs

Decisions made in one v1 stage that a later v1 stage must honour. Each entry:
the decision, the evidence, and the stage that has to act on it.

## Stage 3 -> Stage 6: unit and period across page breaks (measured, not built)

Question: when a table runs onto the next page without repeating its unit
line or period header, should chunks carry that context across the break?

Measured on HCC FY25 (2026-09-13):
- Pages that begin with table rows while no unit or period header is in
  force: 1 (p293, a director-profile table in the AGM notice, not financial).
- Pages whose first figures lack context that the previous page ends with:
  17. None begins directly with table rows in the previous page's column
  shape. A carry would mislabel most of them: the statements of changes in
  equity (p118, p198) would inherit the cash-flow statement's "Year ended"
  header, and new notes or sub-tables (p133, p215, p216, p223, p238, p255,
  p259) would inherit a two-year header their columns do not have.

Decision: no cross-page carry, in text or in metadata. A chunk carries only
context printed on its own page.

Stage 6 must take units and periods only from lines inside the retrieved
chunk. When a chunk's figures have no unit or period line, the answer says
the figure is reported without one on that page; it never supplies one.
Revisit with `unit`/`period` chunk metadata if a later report shows real
continuation tables.

## Stage 4: chunk length under candidate tokenizers

Chunks are capped at 200 cl100k tokens. Measured maxima (special tokens
included): 393 for bge-small-en-v1.5 and nomic-embed-text-v1.5 (WordPiece,
limit 512), 225 for granite-embedding-small-english-r2, 298 for voyage-4-lite
(limit 32,000). No candidate truncates a chunk.

## Stage 9: one clean file in, one chunks file out

`ingest/chunk.py` reads a single clean file and overwrites
`data/chunks.jsonl`. A second company needs several inputs or per-company
output.

## Stage 8/10: Hugging Face Spaces now need a paid plan for app Spaces

Hugging Face docs (checked 2026-09-13): creating a Gradio or Docker Space
requires a paid plan (PRO for personal accounts); static Spaces stay free;
free personal accounts may host up to two Gradio Spaces on ZeroGPU. Streamlit
is not a native SDK and runs as a Docker Space. CPU Basic hardware itself
(2 vCPU, 16 GB) still has no hourly cost. SPEC.md §5's "Streamlit on HF
Spaces, free tier" needs a decision before Stage 8.
