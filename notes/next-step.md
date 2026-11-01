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
