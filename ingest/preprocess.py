"""Page cleaning: PDF geometry in, one clean text record per page out.

Stage 2 showed where PyMuPDF's plain text goes wrong in ways that hurt
citations and numbers: running footers carry the printed page number, some
two-column pages come out right column first, and unit lines and year
headers drift away from the values they qualify. Every fix needs a line's
position or font size, which plain text discards, so this stage re-reads the
PDF in PyMuPDF's "dict" mode (bbox + font size per line). The Stage 2 dump
stays untouched as the before-picture to diff against.

Every rule is a layout rule, never a page list: the same code must work on
the next eleven annual reports, so pages named in the Stage 2 notes are test
cases for these rules, not inputs to them. No layout model is used —
PyMuPDF-Layout is excluded (SPEC.md §5, §7) — and a heuristic that fails
visibly beats a model we cannot ship.

Output: data/<company>_<fiscal_year>_clean.jsonl, one record per PDF page:

    {"company": "HCC", "fiscal_year": "FY25", "page": 114, "text": "...",
     "title": "Standalone Balance Sheet as at March 31, 2025",
     "units": [...], "headers": [...], "columns": 1,
     "excluded": null, "furniture": [...]}

"title", "units" and "headers" are copies: those lines also stay in "text"
where they sit, and the chunker gives each chunk the copies it lacks.
"columns" and "furniture" exist for the eyeball check — which pages were
re-ordered, and what was stripped.
"""

from __future__ import annotations

import argparse
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from ingest.extract import write_jsonl

# --- Thresholds: each is a proportion of the page or report, not a page number.

# Sizes within this many points of the modal size count as body text. Wide
# enough for 8.5 vs 8.6pt noise inside one paragraph; still separates an
# 8.0pt footer from 8.5pt body.
SIZE_TOLERANCE = 0.3

# Running headers and footers live in the top and bottom margins. A line that
# repeats mid-page (a table's column header) is content, however often.
MARGIN_FRACTION = 0.15

# Two lines this many points apart vertically sit at "the same height".
Y_TOLERANCE = 3.0

# Furniture recurs on at least this share of pages. Small non-body lines such
# as percentages or bracketed figures recur at one spot on a dozen pages; a
# tenth of the report sits well above that and well below a footer's
# near-every-page.
MIN_FURNITURE_SHARE = 0.10

# Column detection, as shares of the page's text width.
SPANNING_WIDTH = 0.6   # wider blocks cross the columns: full-width headings, tables
COLUMN_GAP = 0.15      # left edges further apart start a new column; indents stay inside one
PROSE_MIN_WIDTH = 0.3  # prose columns are wide; a table's value columns are narrow
PROSE_MAX_FIGURES = 0.2  # ...and made of words: mostly bare figures means a value column
GRID_ALIGNMENT = 0.5   # share of block tops lining up across columns that marks a grid
ALIGN_TOLERANCE = 2.0  # points

# Below this many body words (after furniture is gone) a page is a cover,
# blank, full-page photo or back cover: nothing a question should retrieve.
MIN_BODY_WORDS = 50

# --- Text patterns.

# The report's rupee font maps ₹ onto the backtick key, and the sign turns up
# everywhere: before amounts and unit words, alone in a table cell, at a line
# end ("Earnings per share `"). The one backtick that is not a rupee is an
# apostrophe mistyped inside a word ("company`s") in some other filing, so
# only a backtick with a letter on both sides is left alone.
RUPEE_BACKTICK = re.compile(r"(?<![A-Za-z])`|`(?![A-Za-z])")

# Ligatures are replaced one by one, not with Unicode NFKC: NFKC also flattens
# superscripts, turning "m³" into "m3" — and a footnote marker printed on a
# figure into an extra digit of that figure.
LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"}

# Control characters (BEL, BS, ...) are debris from glyphs the font maps onto
# control codes, such as a bullet. They carry no text. Tab and newline are
# plain whitespace and are handled with the rest of it.
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
DATE = (
    rf"(?:{MONTH}\s+\d{{1,2}},?\s+\d{{4}}"                # March 31, 2025
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH},?\s+\d{{4}}"  # 31st March 2025
    rf"|\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{4}})"             # 31.03.2025
)
PERIOD_WORDS = (
    r"(?:as at|as on|year ended|for the year ended|for the period(?: ended)?"
    r"|period ended|quarter ended|half year ended|nine months ended)"
)
# A cell that opens a period heading: "As at", "For the period", "As at March 31, 2025".
PERIOD_OPENER = re.compile(rf"^{PERIOD_WORDS}(?:\s+{DATE}(?:\s+to)?)?$", re.IGNORECASE)
# A line continuing a stacked heading ("March 31, 2025", "April 1, 2023 to"),
# or a bare year column: "2024-25", "FY 2024-25", and the short forms BRSR
# tables use, "FY 24-25" and "FY 25". Short forms need the FY prefix: a bare
# "31-60" is an ageing bucket, not a year.
PERIOD_PART = re.compile(
    rf"^(?:{DATE}(?:\s+to)?"
    r"|(?:f\.?\s?y\.?\s*)?\d{4}\s*-\s*\d{2,4}"
    r"|f\.?\s?y\.?\s*\d{2}(?:\d{2}|\s*-\s*\d{2})?)$",
    re.IGNORECASE,
)
# A finished heading: period words plus a date, or plus a date range.
PERIOD_COMPLETE = re.compile(rf"^{PERIOD_WORDS}\s+{DATE}(?:\s+to\s+{DATE})?$", re.IGNORECASE)

# A financial statement's own title: "Standalone Balance Sheet as at March 31,
# 2025", "CONSOLIDATION STATEMENT OF CASH FLOW for the year ended ...". The
# scope word is optional because a company with no subsidiaries prints a plain
# "Balance Sheet". The whole row must be the title, so a sentence that merely
# mentions "the Statement of Profit and Loss" never matches.
STATEMENT_TITLE = re.compile(
    r"^(?:(?:standalone|consolidated|consolidation)\s+)?"
    r"(?:balance sheet|cash flow statement|statement of (?:profit and loss|cash flows?|changes? in equity))"
    rf"(?:\s+(?:as at and for the year ended|{PERIOD_WORDS})\s+{DATE})?"
    r"(?:\s*\(?contd\.?\)?)?$",
    re.IGNORECASE,
)

# A table value: amounts with Indian or Western digit grouping, negatives in
# brackets, percentages, or a dash for nil.
VALUE = re.compile(r"^\(?[-–]?[\d,]*\.?\d+\)?%?$|^[-–]$")

# Unit declarations name a currency and a magnitude: "(Amount in ₹ crore,
# unless otherwise stated)", "₹ in crore, except earnings per share",
# "Standalone (₹ in crore)", a column's "₹ Lacs".
CURRENCY = re.compile(r"₹|\brs\b|\binr\b|\bamounts?\b|\bcurrency\b|\bfigures\b", re.IGNORECASE)
MAGNITUDE = re.compile(r"\b(?:crores?|lakhs?|lacs?|millions?|billions?|thousands?)\b", re.IGNORECASE)
MAX_UNIT_WORDS = 8  # a declaration is a label, not a sentence

# A list marker printed apart from its text: "•", "-", "a)", "(ii)", "3.".
LIST_MARKER = re.compile(
    r"^(?:[•▪◦\-–]|\(?[a-z]\)|[a-z]\.|\(?[ivx]{1,5}\)|\(?\d{1,2}[.)])$", re.IGNORECASE
)


@dataclass
class Line:
    """One PyMuPDF text line, with the geometry every rule below reads."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    block: int


# A PyMuPDF block (a paragraph, or a run of cells) as its bounds plus its lines.
Block = tuple[float, float, float, float, list[Line]]

# A table cell as its text plus horizontal extent, kept so a wrapped fragment
# can find the cell it sits under.
Cell = tuple[str, float, float]


# --- Reading lines ------------------------------------------------------------


def normalize_glyphs(text: str) -> str:
    """Repair font-mapping noise in one line of text (rule 5).

    Runs before anything else reads the text, so furniture signatures, unit
    patterns and the final chunks all see ₹ and "fi", never ` or U+FB01.
    """
    text = RUPEE_BACKTICK.sub("₹", text)
    for ligature, letters in LIGATURES.items():
        text = text.replace(ligature, letters)
    text = CONTROL_CHARS.sub("", text)
    # \s also matches the non-breaking and narrow no-break spaces PDFs put
    # inside amounts; collapsing to one plain space keeps every pattern simple.
    return re.sub(r"\s+", " ", text).strip()


def upright(bbox: tuple[float, float, float, float], direction: tuple[float, float],
            width: float, height: float) -> tuple[float, float, float, float]:
    """Turn a line's box into the frame where its text reads left to right.

    A wide table is often set sideways on a portrait page, its text running
    up the page, so its rows are vertical strips and "sort by height" would
    read it column by column. PyMuPDF reports each line's writing direction
    as a unit vector; turning sideways lines' boxes a quarter turn makes top-
    to-bottom and left-to-right mean the same for them as for ordinary text,
    so every rule after this works unchanged.
    """
    x0, y0, x1, y1 = bbox
    _, dy = direction
    if dy < -0.9:  # text runs up the page: the table's top is the page's left edge
        return height - y1, x0, height - y0, x1
    if dy > 0.9:  # text runs down the page: the table's top is the page's right edge
        return y0, width - x1, y1, width - x0
    return x0, y0, x1, y1


def read_lines(page: fitz.Page) -> list[Line]:
    """Return every non-empty text line on a page with its upright bbox and font size."""
    lines: list[Line] = []
    for block_no, block in enumerate(page.get_text("dict")["blocks"]):
        if block["type"] != 0:  # image block: pixels, no text
            continue
        for raw in block["lines"]:
            text = normalize_glyphs("".join(span["text"] for span in raw["spans"]))
            if not text:
                continue
            # A line can mix sizes (a 10pt heading run into 8.5pt text); the
            # span carrying the most characters speaks for the line.
            size = max(raw["spans"], key=lambda span: len(span["text"].strip()))["size"]
            x0, y0, x1, y1 = upright(raw["bbox"], raw["dir"], page.rect.width, page.rect.height)
            lines.append(Line(text, x0, y0, x1, y1, round(size, 1), block_no))
    return lines


# --- Rule 1: running furniture ------------------------------------------------


def modal_body_size(pages: list[list[Line]]) -> float:
    """The font size carrying the most characters in the report: body text."""
    chars: Counter[float] = Counter()
    for lines in pages:
        for line in lines:
            chars[line.size] += len(line.text)
    return chars.most_common(1)[0][0]


def signature(text: str) -> str:
    """Content key for spotting repeats: the parts of furniture that don't vary.

    Digit runs become "#" so page numbers "9", "13" and "112" match each
    other, and case-folding matches "Annual Report" with "ANNUAL REPORT".
    """
    return re.sub(r"\d+", "#", text.casefold())


def find_furniture(pages: list[list[Line]], heights: list[float]) -> set[tuple[int, int]]:
    """Return (page index, line index) for every running header and footer line.

    This is citation protection. The footer prints the report's own page
    number, which runs behind the PDF page number Praman cites (§3.3) — two
    behind in HCC FY25. If "112" survives into the text of PDF page 114, the
    generator can cite the number it reads instead of the metadata page, and
    every citation lands two pages off. The offset differs between reports,
    so the footer is removed, never corrected.

    Detection is by repetition, and three guards decide what may even be a
    candidate. Body-size lines never are: list numbers like "1." recur at
    page tops at body size. Lines outside the margins never are: a table's
    column header recurs mid-page on every notes page. Unit declarations
    never are: "(Amount in ₹ crore, unless otherwise stated)" is typeset
    exactly like furniture — small, top margin, same spot on a hundred
    pages — yet it changes the meaning of every number below it. A
    candidate becomes furniture only if the same content sits at the same
    height on a large share of pages.
    """
    body_size = modal_body_size(pages)
    candidates: defaultdict[str, list[tuple[float, int, int]]] = defaultdict(list)
    for page_index, (lines, height) in enumerate(zip(pages, heights)):
        top, bottom = height * MARGIN_FRACTION, height * (1 - MARGIN_FRACTION)
        for line_index, line in enumerate(lines):
            if abs(line.size - body_size) <= SIZE_TOLERANCE or is_unit_declaration(line.text):
                continue
            if line.y1 <= top or line.y0 >= bottom:
                candidates[signature(line.text)].append((line.y0, page_index, line_index))

    min_pages = max(3, math.ceil(MIN_FURNITURE_SHARE * len(pages)))
    furniture: set[tuple[int, int]] = set()
    for hits in candidates.values():
        for cluster in split_by_height(sorted(hits)):
            if len({page_index for _, page_index, _ in cluster}) >= min_pages:
                furniture.update((page_index, line_index) for _, page_index, line_index in cluster)
    return furniture


def split_by_height(hits: list[tuple[float, int, int]]) -> list[list[tuple[float, int, int]]]:
    """Split height-sorted occurrences of one signature wherever the gap exceeds Y_TOLERANCE.

    The same text can be furniture at one height and content at another — a
    bare "12" is a page number at the foot and a small label elsewhere — so
    only occurrences sharing a height count toward repetition.
    """
    clusters = [[hits[0]]]
    for hit in hits[1:]:
        if hit[0] - clusters[-1][-1][0] <= Y_TOLERANCE:
            clusters[-1].append(hit)
        else:
            clusters.append([hit])
    return clusters


# --- Rule 2: reading order ----------------------------------------------------


def to_blocks(lines: list[Line]) -> list[Block]:
    """Regroup lines into PyMuPDF's blocks, each with its bounding box."""
    grouped: defaultdict[int, list[Line]] = defaultdict(list)
    for line in lines:
        grouped[line.block].append(line)
    return [
        (min(l.x0 for l in ls), min(l.y0 for l in ls), max(l.x1 for l in ls), max(l.y1 for l in ls), ls)
        for ls in grouped.values()
    ]


def reading_groups(lines: list[Line]) -> tuple[list[list[Line]], int]:
    """Split a page into line groups in reading order; also return the column count.

    PyMuPDF emits blocks in the order the typesetter wrote them, and on some
    two-column pages that is the right column first. So reading order is
    rebuilt from geometry: blocks are clustered into columns by left edge and
    each column is read top to bottom. A block spanning the columns (a
    full-width heading or table) cuts the page into bands, read in turn.

    The danger is a table read as columns — all labels, then all numbers.
    Three guards stand in the way: a column must be prose-width, made of
    words rather than bare figures, and its blocks must not line up
    top-to-top with the next column's like grid cells. A page failing any of
    them stays one column, and row building keeps its tables whole.
    """
    blocks = to_blocks(lines)
    if len(blocks) < 2:
        return [lines], 1
    left = min(b[0] for b in blocks)
    width = max(b[2] for b in blocks) - left
    spanning = sorted((b for b in blocks if b[2] - b[0] > SPANNING_WIDTH * width), key=lambda b: b[1])
    narrow = sorted((b for b in blocks if b[2] - b[0] <= SPANNING_WIDTH * width), key=lambda b: b[0])

    clusters: list[list[Block]] = []
    for block in narrow:
        if clusters and block[0] - clusters[-1][-1][0] <= COLUMN_GAP * width:
            clusters[-1].append(block)
        else:
            clusters.append([block])
    columns = [c for c in clusters if is_prose(c, width)]
    if len(columns) < 2 or is_grid(columns):
        return [lines], 1

    # Narrow blocks outside every prose column (a caption, a small table's
    # value cells) join the column whose left edge is nearest.
    edges = [statistics.median(b[0] for b in column) for column in columns]
    for cluster in clusters:
        if any(cluster is column for column in columns):
            continue
        for block in cluster:
            nearest = min(range(len(columns)), key=lambda k: abs(block[0] - edges[k]))
            columns[nearest].append(block)

    groups: list[list[Line]] = []
    band_top = -math.inf
    cuts: list[tuple[float, Block | None]] = [(b[1], b) for b in spanning] + [(math.inf, None)]
    for band_bottom, cut in cuts:
        for column in columns:
            # A block belongs to the band holding its vertical midpoint, so every
            # block lands in exactly one band even if it overlaps a spanning one.
            band = sorted((b for b in column if band_top <= (b[1] + b[3]) / 2 < band_bottom), key=lambda b: b[1])
            if band:
                groups.append([line for b in band for line in b[4]])
        if cut is not None:
            groups.append(cut[4])
            band_top = band_bottom
    return groups, len(columns)


def is_prose(cluster: list[Block], width: float) -> bool:
    """True if a cluster of blocks reads like a column of running text.

    Width alone is not enough: PyMuPDF sometimes groups a table's unit cell
    with the figures to its right into one wide block, which then passes for
    a column. Prose is made of words, so a cluster whose lines are largely
    bare figures is a table's value column, however wide.
    """
    lines = [line for block in cluster for line in block[4]]
    figures = sum(bool(VALUE.match(line.text)) for line in lines) / len(lines)
    wide = statistics.median(b[2] - b[0] for b in cluster) >= PROSE_MIN_WIDTH * width
    return wide and figures <= PROSE_MAX_FIGURES


def is_grid(columns: list[list[Block]]) -> bool:
    """True if neighbouring columns' blocks line up top-to-top, like table cells.

    Paragraphs in two prose columns start wherever the text flow puts them,
    so few tops coincide. Cells in a wide text table (a governance grid)
    start on shared row lines, so most do.
    """
    for left, right in zip(columns, columns[1:]):
        smaller, other = sorted((left, right), key=len)
        aligned = sum(any(abs(b[1] - o[1]) <= ALIGN_TOLERANCE for o in other) for b in smaller)
        if aligned >= GRID_ALIGNMENT * len(smaller):
            return True
    return False


# --- Rules 3 to 5: rows, cells, units, period headings, wrapped labels ---------


def merge_stacked_periods(lines: list[Line]) -> list[Line]:
    """Merge a period heading stacked over several lines into one cell (rule 4).

    Column headings like "As at" over "March 31, 2025" are typeset as a
    stack. Rows are built from lines sharing a height, so an unmerged stack
    becomes a row "As at | As at" and a second row "March 31, 2025 |
    March 31, 2024" — no cell says which year its column holds. Merged
    first, each column gets one cell, "As at March 31, 2025", which row
    building then places above that column's values.

    Only an unfinished heading absorbs lines below it. A finished one ("As at
    March 31, 2024" as a row label in a movement table) takes nothing, so a
    date in the next row is never pulled up into it.
    """
    ordered = sorted(lines, key=lambda l: (l.y0, l.x0))
    absorbed: set[int] = set()
    result: list[Line] = []
    for i, head in enumerate(ordered):
        if i in absorbed:
            continue
        cell = head
        if PERIOD_OPENER.match(head.text):
            line_height = head.y1 - head.y0
            for j in range(i + 1, len(ordered)):
                below = ordered[j]
                if PERIOD_COMPLETE.match(cell.text) or below.y0 > cell.y1 + line_height:
                    break
                stacked = below.y0 >= cell.y1 - 1 and below.x0 < cell.x1 and below.x1 > cell.x0
                if j not in absorbed and stacked and PERIOD_PART.match(below.text):
                    cell = Line(
                        f"{cell.text} {below.text}",
                        min(cell.x0, below.x0), cell.y0, max(cell.x1, below.x1), below.y1,
                        cell.size, cell.block,
                    )
                    absorbed.add(j)
        result.append(cell)
    return result


def build_rows(lines: list[Line]) -> list[list[Line]]:
    """Group lines that share a height into rows, each ordered left to right.

    In a table each cell is its own PyMuPDF line, and lines do not arrive in
    column order. Grouping by height and sorting by x puts "Trade
    receivables", "6", "2,365.71", "1,852.73" back into one row, in the same
    left-to-right order as the period headings above them.
    """
    rows: list[list[Line]] = []
    for line in sorted(lines, key=lambda l: (l.y0, l.x0)):
        middle = (line.y0 + line.y1) / 2
        if rows and min(l.y0 for l in rows[-1]) <= middle <= max(l.y1 for l in rows[-1]):
            rows[-1].append(line)
        else:
            rows.append([line])
    return [sorted(row, key=lambda l: l.x0) for row in rows]


def to_cells(row: list[Line]) -> list[Cell]:
    """Join a row's lines into cells: near lines form one phrase, far ones separate cells.

    A gap wider than the font size is a column gutter, not a word space. Two
    exceptions. A list marker is glued to the text after it whatever the gap,
    so "•" and its item can never be chunked apart. And some cells stand
    alone however close their neighbour: two figures or two period headings
    (tight numeric columns would fuse "342.75" and "1,425.77" into one wrong
    value), and a unit declaration, which glued onto a long title beside it
    would stop reading as a declaration at all.
    """
    cells: list[Cell] = [(row[0].text, row[0].x0, row[0].x1)]
    for previous, line in zip(row, row[1:]):
        text, x0, x1 = cells[-1]
        marker = len(cells) == 1 and LIST_MARKER.match(text) and not VALUE.match(line.text)
        near = line.x0 - previous.x1 < previous.size
        own_cell = (
            (is_atomic(text) and is_atomic(line.text))
            or is_unit_declaration(text)
            or is_unit_declaration(line.text)
        )
        if marker or (near and not own_cell):
            cells[-1] = (f"{text} {line.text}", x0, max(x1, line.x1))
        else:
            cells.append((line.text, line.x0, line.x1))
    return [piece for cell in cells for piece in split_figures(cell)]


def split_figures(cell: Cell) -> list[Cell]:
    """Split a cell of several bare figures ("52.78 1,796.27") into one cell each.

    PyMuPDF now and then returns two tightly set values as a single line,
    which no gap test can pull apart. Space-separated tokens that are all
    figures are never one value, so each gets its own cell and its share
    of the width.
    """
    text, x0, x1 = cell
    tokens = text.split()
    if len(tokens) < 2 or not all(VALUE.match(token) for token in tokens):
        return [cell]
    step = (x1 - x0) / len(tokens)
    return [(token, x0 + k * step, x0 + (k + 1) * step) for k, token in enumerate(tokens)]


def is_atomic(text: str) -> bool:
    """A figure or a finished period heading: always a cell of its own."""
    return bool(VALUE.match(text) or PERIOD_COMPLETE.match(text))


def join_wrapped_rows(rows: list[list[Cell]]) -> list[list[Cell]]:
    """Re-join a table cell whose text wrapped onto a line of its own (rule 5).

    A long cell wraps, and its figures print beside either its last line or
    its first. Last: a row holding only "...other than micro enterprises and
    small", then "enterprises | 1,935.74 | 1,706.06". First: "(iv) Disputed
    trade receivables - considered | 146.05 | ...", then a row holding only
    "good". Either way the fragment is a text-only row starting in lower
    case, stacked on the cell it belongs to. It joins the text cell it
    overlaps — not simply the first cell, because a wrapped explanation in a
    table's last column belongs to that column.
    """
    joined: list[list[Cell]] = []
    for cells in rows:
        previous = joined[-1] if joined else None
        wrapped_above = (
            previous is not None and text_only(previous) and has_figures(cells)
            and continues(cells[0][0]) and overlap(previous[0], cells[0]) > 0
        )
        wrapped_below = (
            previous is not None and has_figures(previous) and text_only(cells)
            and continues(cells[0][0])
        )
        if wrapped_above:
            joined[-1] = [merge(previous[0], cells[0]), *cells[1:]]
            continue
        if wrapped_below:
            text_cells = [k for k, cell in enumerate(previous) if not VALUE.match(cell[0])]
            target = max(text_cells, key=lambda k: overlap(previous[k], cells[0]), default=None)
            if target is not None and overlap(previous[target], cells[0]) > 0:
                previous[target] = merge(previous[target], cells[0])
                continue
        joined.append(cells)
    return joined


def text_only(cells: list[Cell]) -> bool:
    """A row that is a single cell of text, with no figure."""
    return len(cells) == 1 and not VALUE.match(cells[0][0])


def has_figures(cells: list[Cell]) -> bool:
    """A row with at least one bare figure in it."""
    return any(VALUE.match(text) for text, _, _ in cells)


def continues(text: str) -> bool:
    """Could this text be a cell's wrapped tail? It starts in lower case, but
    is not a lower-case list marker: "b) Advances" opens a new item."""
    return text[:1].islower() and not LIST_MARKER.match(text.split()[0])


def overlap(a: Cell, b: Cell) -> float:
    """Horizontal overlap of two cells in points; zero or less means side by side."""
    return min(a[2], b[2]) - max(a[1], b[1])


def merge(upper: Cell, lower: Cell) -> Cell:
    """One cell from two stacked fragments, text in reading order."""
    return (f"{upper[0]} {lower[0]}", min(upper[1], lower[1]), max(upper[2], lower[2]))


def is_unit_declaration(text: str) -> bool:
    """True for a cell that declares the unit of the figures around it (rule 3).

    Brackets are optional — the same report writes "(₹ in crore)",
    "₹ in crore, except earnings per share" and "₹ Lacs" — so shape decides
    instead. Short, because a declaration is a label and a sentence that
    merely mentions crores is not. Digit-free, because a declaration names a
    unit, never an amount: "(HCC's share: ₹3,472 crore)" is a figure.
    """
    return (
        len(text.split()) <= MAX_UNIT_WORDS
        and not re.search(r"\d", text)
        and bool(CURRENCY.search(text))
        and bool(MAGNITUDE.search(text))
    )


def is_period_header(cells: list[str]) -> bool:
    """True for a row naming the periods of the value columns below it.

    A header row holds no figures — that separates it from a movement table's
    "As at March 31, 2024 | 1,234.56" row. It has one finished heading, or at
    least two bare periods side by side ("2024-25 | 2023-24"); a lone
    "2024-25" is a row label in a year-by-year table, not a header.
    """
    if any(VALUE.match(cell) for cell in cells):
        return False
    finished = sum(bool(PERIOD_COMPLETE.match(cell)) for cell in cells)
    bare = sum(bool(PERIOD_PART.match(cell)) for cell in cells)
    return finished >= 1 or bare >= 2


# --- One page, then the whole report -----------------------------------------


def clean_page(lines: list[Line]) -> dict:
    """Turn one page's body lines (furniture already removed) into text plus context."""
    groups, columns = reading_groups(lines)
    text_rows: list[str] = []
    units: list[str] = []
    headers: list[str] = []
    for group in groups:
        rows = join_wrapped_rows([to_cells(row) for row in build_rows(merge_stacked_periods(group))])
        for cells in rows:
            texts = [text for text, _, _ in cells]
            row_text = " | ".join(texts)
            text_rows.append(row_text)
            # Rule 3 and rule 4 context is copied, never moved: the line stays in
            # place, so a page with two tables keeps each unit and heading beside
            # its own table, while every chunk still receives a copy.
            for text in texts:
                if is_unit_declaration(text) and text not in units:
                    units.append(text)
            if is_period_header(texts) and row_text not in headers:
                headers.append(row_text)

    # A statement prints its title once, as the first line of each of its pages,
    # yet the title is true of every row below it: a balance-sheet page is the
    # standalone balance sheet for its full length. Only the first row counts,
    # so a sub-heading such as "Statement of profit and loss" inside a note is
    # never taken for the page's statement.
    title = text_rows[0] if text_rows and STATEMENT_TITLE.match(text_rows[0]) else None

    words = sum(len(line.text.split()) for line in lines)
    return {
        "text": "\n".join(text_rows),
        "title": title,
        "units": units,
        "headers": headers,
        "columns": columns,
        # Rule 6 as a threshold, not a page list: a page is skipped for what it
        # holds, so the next report's covers and blanks are caught unnamed.
        "excluded": f"fewer than {MIN_BODY_WORDS} body words" if words < MIN_BODY_WORDS else None,
    }


def preprocess(pdf_path: Path, company: str, fiscal_year: str) -> list[dict]:
    """Return one clean record per PDF page, in page order.

    Furniture needs the whole report at once — repetition is invisible from a
    single page — so every page is read first, then each is cleaned.
    """
    with fitz.open(pdf_path) as doc:
        pages = [read_lines(page) for page in doc]
        heights = [page.rect.height for page in doc]
    furniture = find_furniture(pages, heights)

    records = []
    for index, lines in enumerate(pages):
        body = [line for i, line in enumerate(lines) if (index, i) not in furniture]
        records.append(
            {
                "company": company,
                "fiscal_year": fiscal_year,
                "page": index + 1,  # viewer page number, the citation convention (§3.3)
                **clean_page(body),
                "furniture": [line.text for i, line in enumerate(lines) if (index, i) in furniture],
            }
        )
    return records


def print_summary(records: list[dict], out_path: Path) -> None:
    """Print what each rule did — the eyeball check every new report gets (§3.6)."""
    included = [r for r in records if not r["excluded"]]
    stripped = Counter(signature(text) for r in records for text in r["furniture"])
    text = "\n".join(r["text"] for r in included)
    residue = {
        "backtick": text.count("`"),
        "control": len(CONTROL_CHARS.findall(text)),
        "ligature": sum(text.count(lig) for lig in LIGATURES),
    }
    print(f"{len(records)} pages -> {out_path}")
    print(f"  furniture stripped: {sum(stripped.values())} lines")
    for sig, count in stripped.most_common():
        print(f"    {count:>4}x  {sig[:72]}")
    multi = [r["page"] for r in records if r["columns"] > 1]
    print(f"  multi-column pages ({len(multi)}): {multi}")
    print(f"  excluded pages: {[r['page'] for r in records if r['excluded']]}")
    print(f"  pages with a statement title: {[r['page'] for r in included if r['title']]}")
    print(f"  pages with a unit line: {sum(1 for r in included if r['units'])}")
    print(f"  pages with a period header: {sum(1 for r in included if r['headers'])}")
    print(f"  glyph residue (expect all 0): {residue}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean page text for chunking: furniture, reading order, units, headers, glyphs."
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

    records = preprocess(args.pdf, args.company, args.fiscal_year)
    out_path = args.out_dir / f"{args.company.lower()}_{args.fiscal_year.lower()}_clean.jsonl"
    write_jsonl(records, out_path)
    print_summary(records, out_path)


if __name__ == "__main__":
    main()
