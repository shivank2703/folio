"""The units a page declares, found wherever the page prints them.

Corpus rule 2 (SPEC.md §3.2): a figure must never be separated from its unit.
chunk.py carries a unit line into every chunk of its page, but only a line it
recognised as one, and on many pages the declaration is fused into another:
Solar Industries prints "for the year ended March 31, 2026 | (All amounts in
H Crores, unless otherwise stated)" as one running-header line, so the
page's later chunks reached the model with figures and no unit. Measured on
the published index, 68% of Solar's figure-bearing chunks, 65% of L&T's and
44% of Infosys's carried no unit word at all.

So the unit is attached at query time instead, per page: every cell and every
parenthesised phrase on the page is tested with the same rule the ingest
side uses (ingest.preprocess.is_unit_declaration), after repairing the rupee
glyphs these reports' fonts map to letters ("H Crores", "in I crore",
"J crore"). Nothing is re-indexed, and a page that declares nothing gets
nothing.
"""

from __future__ import annotations

import re

from ingest.preprocess import is_unit_declaration, normalize_glyphs

MAGNITUDE = r"(?:crores?|cr\.?|lakhs?|lacs?|millions?|mn|billions?|bn|thousands?)"

# A lone capital standing where ₹ belongs, straight before a magnitude: the
# currency fonts in these reports map the rupee sign to H, I, J, C, K or v.
RUPEE_GLYPH = re.compile(rf"(?<![A-Za-z])[CHIJKv`]\s+(?=(?i:{MAGNITUDE})(?![a-z]))")
PARENTHESISED = re.compile(r"\([^()]{3,160}\)")

# A declaration that opens with its unit, however long its qualifier:
# Infosys's "(In ₹ crore, except equity share and per equity share data)" is
# ten words, past ingest's eight-word limit, and HDFC Bank writes "(₹ Cr)".
LEADING_UNIT = re.compile(
    rf"^[(\[]?\s*(?:all\s+)?(?:amounts?\s+|figures?\s+)?(?:are\s+)?(?:in\s+)?(?:₹|rs\.?|inr|rupees)\s*(?:in\s+)?{MAGNITUDE}(?![a-z])",
    re.I)

# A page rarely declares more than one or two; more are repeats or noise.
MAX_PER_PAGE = 3


def is_declaration(text: str) -> bool:
    """ingest's rule for a unit label, or a digit-free phrase that opens with currency and magnitude."""
    if re.search(r"\d", text):
        return False
    return is_unit_declaration(text) or bool(LEADING_UNIT.match(text))


def declarations(text: str) -> list[str]:
    """Every unit declaration in a chunk's text, glyphs repaired, in reading order."""
    found: list[str] = []
    for line in text.splitlines():
        for cell in line.split(" | "):
            for candidate in (cell, *PARENTHESISED.findall(cell)):
                repaired = RUPEE_GLYPH.sub("₹ ", normalize_glyphs(candidate.strip()))
                # L&T's text layer doubles the sign around its glyph ("₹I₹ crore").
                repaired = re.sub(r"₹\s*[CHIJKv]?\s*₹", "₹", repaired).replace("( ₹", "(₹")
                if repaired and is_declaration(repaired) and repaired not in found:
                    found.append(repaired)
    return found


def page_units(table, company: str, pages: list[int]) -> dict[int, list[str]]:
    """The unit declarations each of these pages prints, read from all of its chunks."""
    if not pages:
        return {}
    rows = (table.search()
            .where("company = '" + company.replace("'", "''") + "' AND page IN (" + ", ".join(map(str, sorted(set(pages)))) + ")")
            .select(["page", "chunk", "text"]).limit(100_000).to_list())
    units: dict[int, list[str]] = {}
    for row in sorted(rows, key=lambda r: (r["page"], r["chunk"])):
        listed = units.setdefault(row["page"], [])
        for declaration in declarations(row["text"]):
            if declaration not in listed and len(listed) < MAX_PER_PAGE:
                listed.append(declaration)
    return {page: found for page, found in units.items() if found}


def attach_units(table, context: list[dict]) -> list[dict]:
    """Each context chunk with "units": what its page declares (possibly nothing)."""
    if not context:
        return context
    units = page_units(table, context[0]["company"], [c["page"] for c in context])
    return [{**c, "units": units.get(c["page"], [])} for c in context]
