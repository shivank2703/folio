---
name: ship-checklist
description: Release checklist for shipping Praman v1/v2/v3/v4. Use whenever deploying, releasing, writing the README, or preparing the public repo — even if only one piece is mentioned.
---

# Ship checklist

Work top to bottom — every ship, every version (SPEC.md §4, "Every ship").
Do not skip a step just because only one piece was asked about.

1. **Secrets scan** — including git history, not just the working tree.
   No API keys, no committed `.env`.
2. **No real watchlist data** — confirm only `watchlist.sample.yaml` is
   tracked; real watchlists / holdings are never committed (§7).
3. **License** — LICENSE present and is AGPL-3.0; confirm no proprietary
   deps (no PyMuPDF-Layout, no OCR engine) (§5, §7).
4. **README** — what & why, architecture diagram, demo GIF, and
   run-locally instructions.
5. **Deploy** — push to Hugging Face Spaces, then smoke-test **3 real
   questions** end to end.
6. **Pin** the repo.
7. **LinkedIn post skeleton** — problem → what it does → what I learned
   → link.
8. **Résumé bullet** — one concrete metric.
9. **git tag** the release.
