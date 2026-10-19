"""Keep visibly interleaved narrative out of the searchable corpus.

A financial row pairs a label with figures. Repeated rows pairing long prose
fragments instead can be two newspaper columns accidentally zipped together.
Refusing those pages is safer than turning the joined fragments into evidence.
"""

from __future__ import annotations

import re


def interleaved_prose(text: str) -> bool:
    """Flag repeated side-by-side prose fragments, never ordinary numeric rows."""
    suspect = 0
    for row in text.splitlines():
        cells = [cell.strip() for cell in row.split(" | ")]
        if len(cells) < 2 or any(re.fullmatch(r"[\d,.()%₹\s−–-]+", c) for c in cells if c):
            continue
        if sum(len(re.findall(r"\b[a-zA-Z]+\b", c)) >= 4 for c in cells) >= 2:
            suspect += 1
    return suspect >= 8


def exclude_unreadable(pages: list[dict]) -> list[dict]:
    for page in pages:
        if not page["excluded"] and interleaved_prose(page["text"]):
            page["excluded"] = "quality check: possible interleaved prose columns"
    return pages
