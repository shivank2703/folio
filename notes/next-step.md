# Next step: logged during the 31 Oct – 1 Nov 2026 sitting

Work requested after Agent: fix the fresh-clone index hazard, false refusals,
units and scope, offline company overviews, UI, an owner-only portfolio view,
and asset pruning. Each entry: what, the evidence, where it went.

## Where model and publishing work can run

The sitting ran in a cloud sandbox whose egress policy denies
`huggingface.co` (the bge-small embedding model) and
`openaipublic.blob.core.windows.net` (tiktoken's `cl100k_base` file), and
whose GitHub proxy accepts only JSON request bodies: a release-asset upload to
`uploads.github.com` is refused with `415 Request bodies must declare
Content-Type: application/json`. Git pushes and JSON API calls work; Actions
artifact downloads (`*.blob.core.windows.net`, `*.actions.githubusercontent.com`)
are denied.

- tiktoken: the encoding file was taken from a PyPI wheel (PyPI is allowed)
  and pointed to with `TIKTOKEN_CACHE_DIR`. tiktoken checks the file against
  its pinned SHA-256 (`223921b7…`), so a wrong file cannot load.
- Publishing: `.github/workflows/index.yml` runs `ingest.add` and
  `ingest.publish` on GitHub's runners with the repository token, and commits
  the record files back to the branch. `python -m ingest.publish --probe`
  tests an upload first, so a sandbox like this one fails in seconds rather
  than after an hour of indexing.
- Embedding: the model weights are not relayed into the sandbox. Retrieval
  that needs the model runs on a runner and commits chunk identities and
  scores only; the sandbox rebuilds the text from its own copy of the index.

## Status of the requested steps (branch claude/folio-indexing-refusals-pd8pc6)

1. Fresh-clone index hazard: fixed and tested; `python -m tests`; CI green.
2. Release upload: refused from the sandbox (415); works from the `index`
   workflow (probe run 41299964867).
3. False refusals: done at retrieval level (evals/RESULTS.md). Model-judged
   `natural-before` and `natural-after` are queued and have not run.
4. Units and scope: done at retrieval level; `accuracy-after` queued.
5. Overviews: builder, tests and workflow step done; `corpus/overviews.json`
   does not exist yet (needs the API key in CI). The builder's code landed
   in step 4's commit eeb5c96 rather than a commit of its own.
6. Company page: done, checked in a browser at 390 and 1,280 px.
7. Holdings view: done. No companies were added: the request's portfolio
   list and MODE arrived as unfilled placeholders.
8. Prune: `ingest.prune` lists 530fb980d5ac and b7f5770b5960 (10 MB each,
   named by no commit); deleting them from the sandbox was refused
   ("not permitted for this session type") and is left to the maintainer.

## Logged, not built

- **Stemming in the full-text index.** "royal enfield sales fy26" never meets
  p13's "sold more than 1.2 million"; LanceDB's FTS can stem, but the index
  is part of the published tarball, so it needs a rebuild and a republish,
  and a before/after on the eval.
- **Reliance's consolidated statement of profit and loss (p101) does not
  rank** for "net profit", even with statement labels and titles; its
  context has other consolidated pages. Look at why p101's chunks score low
  before adding anything Reliance-specific.
- **Fix units at the source on the next full re-index.** `retrieve/units.py`
  patches at query time what ingest misses: `is_unit_declaration`'s
  eight-word limit, declarations fused into other lines, ₹ glyphs. The same
  rules belong in preprocess/chunk, so chunk text itself carries the unit.
- **The agent does not use the unit guard.** Memo report tools withhold on
  invalid citations, ungrounded figures and scrubbed advice, not on
  `unitless`; deciding that needs the agent eval re-run.
- **The floor's off-topic margin is thin** (a weather question at 0.584
  against 0.59). Off-topic input that passes costs one model call and is
  refused by the contract; watch the live refusal reasons.
- **The misspelling corrector's English test is a heuristic**: a word cl100k
  encodes as one token is treated as English. A rare real word one edit from
  a frequent filing word could still be rewritten; the eval saw none.
- **SBI branch count** ("how many branches does sbi have") is not retrieved:
  "branches" is on hundreds of pages and "SBI" does not match the code SBIN.
- **Index fetch hashes the tarball in memory** (`retrieve/store.py`
  reads 93 MB at once, +88 MB peak at startup); hash while streaming.
