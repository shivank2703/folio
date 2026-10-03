"""Page-wise text extraction: one PDF in, one JSONL of page records out.

The page is Folio's citation unit (SPEC.md §3.3): chunk, retrieved
context, and the final [page] cite all point back to a viewer page number.
So extraction preserves exactly one boundary — the page — and interprets
nothing finer. Blocks, columns, and tables stay unparsed in v1 (SPEC.md
§5: raw PyMuPDF, own every layer first); if a layout scrambles the text,
the Stage 2 eyeball check must catch it, not a heuristic hide it.

Output: data/<company>_<fiscal_year>_pages.jsonl, one record per page:

    {"company": "HCC", "fiscal_year": "FY25", "page": 3, "text": "..."}

Records are self-describing — identity rides inside each record instead of
only in the filename, so when v2 lands multiple years of dumps in data/,
no artifact depends on what it happens to be called.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz  # PyMuPDF


def extract_pages(pdf_path: Path, company: str, fiscal_year: str) -> list[dict]:
    """Return one {company, fiscal_year, page, text} record per PDF page.

    "page" is the 1-based number a PDF viewer displays — the citation
    convention (SPEC.md §3.3). PyMuPDF indexes from 0; the +1 happens here,
    once, so nothing downstream ever converts between numbering schemes.

    Empty pages are kept: dropping them would desynchronize record count
    from viewer page numbers, and a run of empty pages is itself a signal
    (a scanned section yields no text — the §3.5 escalation trigger).
    """
    records: list[dict] = []
    with fitz.open(pdf_path) as doc:
        for index, page in enumerate(doc):
            # "text" mode emits blocks in PyMuPDF's natural reading order,
            # deliberately unsorted: if a two-column page interleaves, the
            # eyeball check should see the failure, not a papered-over fix.
            records.append(
                {
                    "company": company,
                    "fiscal_year": fiscal_year,
                    "page": index + 1,
                    "text": page.get_text("text"),
                }
            )
    return records


def write_jsonl(records: list[dict], out_path: Path) -> None:
    """Write records as JSON Lines.

    ensure_ascii=False keeps ₹ and other non-ASCII as readable characters
    instead of \\u escapes — the unit symbol must stay eyeball-able because
    unit declarations are load-bearing (SPEC.md §3.2).
    """
    with out_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract page-wise text from a born-digital annual report."
    )
    parser.add_argument("pdf", type=Path, help="path to the source PDF (corpus/)")
    parser.add_argument("--company", required=True, help='ticker-style name, e.g. "HCC"')
    parser.add_argument(
        "--fiscal-year", required=True, help='FY convention, e.g. "FY25" = Apr 2024-Mar 2025'
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data"),
        help="generated-artifact folder; contents are disposable and gitignored",
    )
    args = parser.parse_args()

    records = extract_pages(args.pdf, args.company, args.fiscal_year)
    out_path = args.out_dir / f"{args.company.lower()}_{args.fiscal_year.lower()}_pages.jsonl"
    write_jsonl(records, out_path)

    # A page with no text on a born-digital filing is worth a human look:
    # separators are fine, but a run of empties means scanned content (§3.5).
    empty_pages = [r["page"] for r in records if not r["text"].strip()]
    total_chars = sum(len(r["text"]) for r in records)
    print(f"{args.pdf.name}: {len(records)} pages -> {out_path}")
    print(f"  total text: {total_chars:,} chars")
    print(f"  empty pages: {empty_pages or 'none'}")


if __name__ == "__main__":
    main()
