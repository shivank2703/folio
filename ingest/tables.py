"""Tables: let pymupdf4llm read a page's ruled tables, but only where it reads them well.

Accurate step (SPEC.md §4, §5). preprocess.py rebuilds table rows from text
geometry, which works on the core statements and breaks on multi-level headers
and fused subtotal columns. pymupdf4llm's classic "lines" strategy reads the
ruling a typesetter drew, so on a gridded note it returns each row with its
cells in their columns.

It is not a replacement, because it fails differently. Measured on the
known-bad pages: on a ruled ageing schedule (HCC p220) and borrowings note
(p230) it is exact; on a shaded, unruled balance sheet (Chambal p98) it merges a
whole column into one cell and repeats it for 57 rows; on a rotated statement
of changes in equity (HCC p118) it returns a grid of repeated headers; with the
default "lines_strict" strategy it finds no table at all and drops the table's
text. So each page keeps preprocess's text unless pymupdf4llm's version passes
every gate below, and the gates are written against those failures.

Licence: pymupdf4llm 0.3.4 is AGPL-3.0. Releases from 1.27 on require
pymupdf_layout, the proprietary layout model SPEC.md §7 excludes; 0.3.4 makes
it an optional extra, which is not installed. Without it pymupdf4llm prints a
hint suggesting it. The hint is advice, not a dependency.
"""

from __future__ import annotations

import re
import signal
from contextlib import contextmanager
from pathlib import Path

import fitz
import pymupdf4llm

from gen.guardrails import FIGURE, checkable
from ingest.preprocess import normalize_glyphs

STRATEGY = "lines"

# Gate 2. A real cell is a label or a figure; the Chambal failure produced cells
# of several thousand characters holding an entire column.
MAX_CELL_CHARS = 120

# Gate 0. Most pages take under a second; a few shaded statement pages send the
# "lines" strategy into thousands of spurious cells and minutes of work, and
# those are exactly the pages gate 2 would reject anyway.
MAX_SECONDS_PER_PAGE = 10

PLACEHOLDER_HEADER = re.compile(r"^Col\d+$")
SEPARATOR_ROW = re.compile(r"^\|(?:\s*:?-{3,}:?\s*\|)+$")


def to_rows(markdown: str) -> list[str]:
    """pymupdf4llm's markdown, rewritten in the row format the rest of the pipeline reads.

    Tables become "cell | cell | cell" lines, as preprocess writes them, so
    chunking, unit detection and the prompt see one format whichever reader
    produced the page. Empty cells are kept: a blank under "Not due" is what
    lets the next figure stay under "Less than 6 months".
    """
    rows: list[str] = []
    for line in markdown.splitlines():
        line = line.replace("**", "").replace("<br>", " ").strip()
        if not line or SEPARATOR_ROW.match(line):
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [" ".join(c.split()) for c in line[1:-1].split("|")]
            cells = ["" if PLACEHOLDER_HEADER.match(c) else c for c in cells]
            # A merged header cell comes back with its text copied into every
            # column it spans, and a row-spanning one leaks its left
            # neighbour's text: on p138 the Total column was headed "More than
            # 3 years". A label repeated beside itself is that copy, so it is
            # blanked. Figures are never touched; two equal amounts side by
            # side are ordinary.
            cells = [
                "" if i and c and c == cells[i - 1] and not figures(c) and c not in {"-", "–"} else c
                for i, c in enumerate(cells)
            ]
            if any(cells):
                rows.append(" | ".join(cells))
        else:
            rows.append(" ".join(line.lstrip("#").split()))
    return [normalize_glyphs(row) for row in rows]


@contextmanager
def time_limit(seconds: int):
    """Raise TimeoutError if the block runs longer than this.

    SIGALRM interrupts at the next Python bytecode, which is enough here:
    pymupdf4llm's slow path is Python looping over cells. Ingest runs offline
    in the main thread, the only place a signal handler can be installed.
    """
    def expire(signum, frame):
        raise TimeoutError
    previous = signal.signal(signal.SIGALRM, expire)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def figures(text: str) -> set[str]:
    return {f for f in (checkable(x) for x in FIGURE.findall(text)) if f}


def accept(chunk: dict, rows: list[str], heuristic_text: str) -> str | None:
    """None if this page's table reading is trustworthy, else the gate it failed."""
    if not chunk.get("tables"):
        return "no table found"
    table_rows = [r for r in rows if " | " in r]
    if any(len(cell) > MAX_CELL_CHARS for r in table_rows for cell in r.split(" | ")):
        return "a cell swallowed a column"
    with_figures = [r for r in table_rows if figures(r)]
    if len(with_figures) != len(set(with_figures)):
        return "rows repeated"
    lost = figures(heuristic_text) - figures("\n".join(rows))
    if lost:
        # Nothing preprocess could read may disappear: a table reader that
        # drops a row is worse than one that leaves it unaligned.
        return f"{len(lost)} figure(s) lost"
    return None


def apply_tables(pdf_path: Path, records: list[dict]) -> list[dict]:
    """Swap in pymupdf4llm's text on the pages where it reads the tables cleanly.

    Title, units and period headers stay as preprocess found them: those are
    page facts, and chunking copies them into every chunk whichever text the
    page ends up with. Running headers and footers that preprocess recorded as
    furniture are removed from the new text by exact match.
    """
    with fitz.open(pdf_path) as doc:
        for record in records:
            if record["excluded"]:
                continue
            try:
                with time_limit(MAX_SECONDS_PER_PAGE):
                    chunk = pymupdf4llm.to_markdown(
                        doc, pages=[record["page"] - 1], page_chunks=True, table_strategy=STRATEGY,
                        # Without hdr_info=False every call rescans the whole
                        # document for heading font sizes, which made one
                        # filing take over ten minutes. Headings play no part.
                        hdr_info=False, ignore_images=True, show_progress=False,
                    )[0]
            except TimeoutError:
                record["table_reader"], record["table_gate"] = "preprocess", "timed out"
                continue
            furniture = {" ".join(f.split()) for f in record["furniture"]}
            rows = [r for r in to_rows(chunk["text"]) if r not in furniture]
            failed = accept(chunk, rows, record["text"])
            record["table_reader"] = "pymupdf4llm" if failed is None else "preprocess"
            record["table_gate"] = failed
            if failed is None:
                record["text"] = "\n".join(rows)
    return records
