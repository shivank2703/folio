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
(limit 32,000). No candidate truncates a chunk. Decided: bge-small-en-v1.5
through fastembed (option A).

## Stage 4 -> Stage 5: querying the index

- Embed questions with `retrieve.embed.MODEL_NAME`, and check the table's
  `embedding_model` schema metadata before searching. Vectors from a
  different model would rank chunks meaninglessly without raising an error.
- Prepend bge's query instruction to every question: "Represent this sentence
  for searching relevant passages: ". Chunks were embedded without it, and
  fastembed's `query_embed` does not add it for this model.
- Stored vectors are unit length, so cosine, dot product and L2 rank alike.
- fastembed serves Qdrant's quantized ONNX export
  (qdrant/bge-small-en-v1.5-onnx-q). The model card's benchmark scores
  describe BAAI's original weights; judge quality on the smoke test.
- Standalone and consolidated statements embedded almost identically: the
  p114 chunk holding `TOTAL ASSETS | 8,743.37 | 8,138.03` had p194's
  consolidated chunk 2 as its nearest neighbour (cosine 0.978), because only
  each page's first chunk named its statement. Fixed within the page:
  chunk.py carries a statement page's title into every chunk on it. That
  chunk's closest p194 chunk is now 0.933, fifth behind its own page. Twins
  whose chunks both state a title stay close (p115 and p195 first chunks:
  0.959, still nearest), and notes pages have no statement title, so v2's
  scope tag (SPEC.md §3.4) is still needed.

## Stage 8: the moved virtualenv

`.venv` was created at /Users/shivank/Desktop/rag and later moved. Sixteen
scripts in `.venv/bin` (including `pip` and `streamlit`) still point at the
old interpreter path and fail. `python -m pip` and `python -m streamlit` work;
recreating the venv fixes the scripts.

## Stage 9: one clean file in, one chunks file out

`ingest/chunk.py` reads a single clean file and overwrites
`data/chunks.jsonl`. A second company needs several inputs or per-company
output.

## Stage 8/10: deploy on Streamlit Community Cloud (decided 2026-09-13)

Decision: the v1 demo deploys free on Streamlit Community Cloud, straight
from the GitHub repo, and Stage 8 stays Streamlit. This replaces Hugging Face
Spaces, where creating a Docker (Streamlit) Space now needs a paid plan.

What the platform imposes (Streamlit docs, checked 2026-09-13):
- An app inherits its repo's visibility. A public repo gives a public app; a
  private repo gives a private app that only invited viewers can open, and an
  account may run one private app at a time. A public demo therefore needs
  the repo public at ship. Deploying needs admin rights on the repo, and
  private repos need an extra GitHub authorization. No remote exists yet.
- There is no build hook: Community Cloud installs requirements.txt (from the
  entrypoint's folder or the repo root) and runs the entrypoint.
- An app gets 0.078 to 2 CPU cores and 690 MB to 2.7 GB of memory, and sleeps
  after 12 hours without traffic.

Decision: deploy rebuilds the index instead of shipping it. With no build
hook, the app must do it itself on start: download the source PDF (never in
git, SPEC.md §7, so corpus/SOURCES.md must carry its exact URL, a TODO still
open), run preprocess, chunk and embed, and cache the result for the life of
the process. `data/lancedb/` and `data/models/` stay gitignored.

The cost to plan for at Stage 10: embedding alone ran about 7 chunks/s on two
laptop threads (about 4 minutes for 1,620 chunks), and Community Cloud grants
at most two cores. If the disk does not survive sleep (the docs do not say),
the first visitor after each 12-hour idle waits minutes, far outside SPEC.md
§6's 10-second bar. Embedding one question takes about 8 ms, so query time is
not the issue. The Anthropic key goes in Community Cloud's secrets settings,
never in the repo (SPEC.md §7).

## Stage 5 -> Stages 6-7: what the retrieval smoke test showed (2026-09-13)

`python -m retrieve.smoke`, vector search only. Rank is the position of the
first chunk from an expected page, searched to depth 20; the generator will
see the top 5.

| Question | Expected | Rank | Top 5 |
|---|---|---|---|
| 001 standalone total assets, FY24 vs FY25 | p114 | not in top 20 (answer chunk 28th) | no |
| 002 consolidated total income, FY25 | p195, p265 | 17 (answer chunk 44th) | no |
| 003 standalone receivables over 3 years | p138 | 2 (consolidated p220 first) | yes |
| 004 share of India's hydropower capacity | p15 | 1 | yes |
| 005 EV charging stations (not in filing) | none | best score 0.673 | n/a |

Statement-title inheritance, run on the same questions before and after:
identical except 002, which rose from outside the top 20 to 17. Scope was not
what kept 001 and 002 out.

Why they missed, from a scratch diagnostic (plain BM25 keyword scoring and
reciprocal-rank fusion with the vector ranking; not project code):

| Question as asked, or rephrased | Vector | Keyword | Fused |
|---|---|---|---|
| 001 "from FY24 to FY25" | 23 | 101 | 16 |
| 001 "from March 31, 2024 to March 31, 2025" | 10 | 1 | 1 |
| 002 "for FY25" | 17 | 4 | 4 |
| 002 "for the year ended March 31, 2025" | 1 | 2 | 1 |
| 003 as asked | 2 | 1 | 2 |
| 004 as asked | 1 | 3 | 1 |

- The statements never print "FY25"; they print "As at March 31, 2025" and
  "Year ended March 31, 2025". Questions follow FY convention (SPEC.md §3.1),
  so the words never meet. Rewriting FY terms as period-end dates lifts both
  misses, and with keyword fusion both reach rank 1.
- Keyword fusion alone helps where row labels carry the match (002: 17 to 4)
  and changed nothing else measured, but it cannot fix 001 without the date
  rewrite: "FY 24" and "FY 25" match BRSR pages that print exactly those
  tokens.
- Pending decision: fuse keyword search with vector search, expand FY terms
  into dates on the query side, or both. Each is a retrieval change and needs
  a before/after run on these questions (rag-eval).
- Not in the filing: the negative's best score (0.673) sat only 0.016 below
  the weakest answerable top score (0.689). A similarity threshold alone
  cannot carry Stage 7's "not in the filing".
- Scope on notes pages: for 003 the consolidated schedule (p220) outranks the
  standalone one (p138). Notes pages carry no statement title; v2 scope tag.
