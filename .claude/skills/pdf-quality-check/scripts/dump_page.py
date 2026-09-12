"""Dump one page's raw text blocks — the eyeball tool behind pdf-quality-check.

WHY this exists: before any extracted text is trusted for chunking or
embedding, a human has to *look* at what PyMuPDF actually pulled off the
page. Whole-page text hides the two failure modes this script surfaces:
blocks arriving out of reading order (two-column narrative pages, SPEC.md
§3.6), and a "table" that is really a scanned image (born-digital check,
SPEC.md §3.5).

Usage:
    python dump_page.py <path-to.pdf> <viewer-page>

<viewer-page> is the PDF page number a viewer shows (1-based) — the same
number Praman cites (SPEC.md §3.3), NOT PyMuPDF's 0-based index.
"""

from __future__ import annotations

import sys

import fitz  # PyMuPDF


def dump_page(pdf_path: str, viewer_page: int) -> None:
    """Print every text block on one page, in PyMuPDF's reading order.

    Bounding boxes are printed alongside the text because order problems
    only become visible against coordinates: a block whose y-coordinate
    jumps back up the page is the tell-tale of a scrambled two-column
    layout. An empty (or image-only) block list on a page that clearly
    holds a table means the table is an image, not text — the born-digital
    assumption has broken and the page must be escalated, not embedded.
    """
    doc = fitz.open(pdf_path)

    # Viewer pages are 1-based; fitz indexes from 0. Convert once, here, so
    # the rest of the code — and the human reading the output — can stay in
    # the citation convention and never juggle two numbering schemes.
    page = doc[viewer_page - 1]

    # get_text("blocks") -> (x0, y0, x1, y1, text, block_no, block_type).
    # block_type 1 == image; a financial table that surfaces as an image
    # block instead of text blocks is exactly the §3.5 escalation trigger.
    blocks = page.get_text("blocks")

    print(f"--- {pdf_path} · viewer page {viewer_page} · {len(blocks)} blocks ---")
    for x0, y0, x1, y1, text, block_no, block_type in blocks:
        kind = "IMAGE" if block_type == 1 else "text"
        preview = text.strip().replace("\n", " / ")
        print(f"[{block_no:>3} {kind} y={y0:7.1f}] {preview}")

    doc.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python dump_page.py <path-to.pdf> <viewer-page>")
    dump_page(sys.argv[1], int(sys.argv[2]))
