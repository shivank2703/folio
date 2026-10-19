"""Read statement scope from headings before page furniture is removed.

A mention in prose is not a label for an entire page. Only short financial
headings count; ambiguous spreads retain both scopes rather than guessing.
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz

SCOPE = re.compile(r"\b(standalone|consolidated)\b", re.I)
STATEMENT = re.compile(r"balance sheet|statement|financial|notes to|cash flow", re.I)


def heading_scope(text: str) -> str:
    for word in ("standalone", "consolidated"):
        text = re.sub(r"\b" + r"\s*".join(word) + r"\b", word, text, flags=re.I)
    found = set()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        # Split headings often put 'Standalone' on a line above the title.
        heading = " ".join(lines[i:i + 3]) if SCOPE.search(line) and not STATEMENT.search(line) else line
        is_heading = re.match(r"(?:standalone|consolidated|notes\b|summary of material accounting)", heading, re.I)
        if is_heading and len(heading) <= 240 and STATEMENT.search(heading):
            found.update(word.lower() for word in SCOPE.findall(heading))
    return next(iter(found)) if len(found) == 1 else "mixed" if found else "unstated"


def tag_pages(pdf: Path, pages: list[dict]) -> list[dict]:
    """Keep source headings, including repeated headers, available to citations."""
    with fitz.open(pdf) as document:
        for page in pages:
            page["scope"] = heading_scope(document[page["page"] - 1].get_text())
    return pages
