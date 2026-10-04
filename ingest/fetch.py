"""Find and download a company's annual reports, politely.

Ingest step (SPEC.md §4). What was checked on 04 Oct 2026, with a plain
request carrying an honest User-Agent:

- NSE's website and its annual-report API reset the connection for scripted
  clients (bot protection); only robots.txt answers. Not a source.
- BSE's API (api.bseindia.com) answers "Access Denied" from Akamai. Not a
  source. Working around either would mean imitating a browser, which the
  project does not do.
- NSE's file archive (archives.nseindia.com) serves annual-report PDFs to a
  plain request and has no robots.txt. A source for downloads, but not for
  discovery: its file names carry an internal id and a timestamp, so a URL can
  only come from a person who looked it up.
- Company investor-relations pages (Unihealth, HCC, Chambal, Navneet) serve
  their pages and PDFs, and their robots.txt allows them. A source for both.

So a company in corpus/urls.yaml names an investor page to search, explicit
report URLs maintained by hand, or both. Every request checks robots.txt,
identifies itself, and waits between calls to the same host.
"""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import Counter
from html import unescape
from pathlib import Path

import fitz

USER_AGENT = "Folio/1.2 (+https://github.com/shivank2703/folio; annual-report indexer)"
# Seconds between two requests to one host. Annual reports are a handful of
# files a year per company; nothing here needs to be fast.
HOST_DELAY = 4.0
TIMEOUT = 120
# An investor page can link dozens of PDFs (notices, policies, old reports).
# Only this many unlabelled ones are downloaded to read their year.
MAX_UNLABELLED_DOWNLOADS = 6

_last_request: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


class Refused(Exception):
    """A request this tool will not make, or a server that would not answer it."""


def allowed(url: str) -> bool:
    """True if the host's robots.txt lets this agent fetch the URL.

    A missing robots.txt (404) allows everything, as the convention says. A
    robots.txt that cannot be fetched at all is treated as allowing too, but
    the request that follows will fail on its own if the host refuses scripts.
    """
    parts = urllib.parse.urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in _robots:
        parser = urllib.robotparser.RobotFileParser(f"{root}/robots.txt")
        try:
            polite_wait(parts.netloc)
            parser.read()
        except Exception:
            parser = None
        _robots[root] = parser
    parser = _robots[root]
    return parser is None or parser.can_fetch(USER_AGENT, url)


def polite_wait(host: str) -> None:
    gap = time.monotonic() - _last_request.get(host, 0.0)
    if gap < HOST_DELAY:
        time.sleep(HOST_DELAY - gap)
    _last_request[host] = time.monotonic()


def get(url: str) -> bytes:
    """Fetch one URL, after robots.txt and the per-host delay. Raises Refused."""
    if not allowed(url):
        raise Refused(f"robots.txt disallows {url}")
    polite_wait(urllib.parse.urlsplit(url).netloc)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except Exception as error:
        # A reset connection or a 403 from a bot filter ends here, on purpose:
        # the answer to "the site blocks scripts" is a URL in urls.yaml, not a
        # browser disguise.
        raise Refused(f"{url}: {error}") from error


PDF_LINK = re.compile(r"""<a\b[^>]*?href=["']([^"']+?\.pdf)(?:[?#][^"']*)?["'][^>]*>(.*?)</a>""", re.IGNORECASE | re.DOTALL)


def pdf_links(page_url: str, html: str) -> list[tuple[str, str]]:
    """Every PDF the page links, as (absolute URL, visible link text), in page order."""
    seen: dict[str, str] = {}
    for href, label in PDF_LINK.findall(html):
        url = urllib.parse.urljoin(page_url, unescape(href))
        text = " ".join(unescape(re.sub(r"<[^>]+>", " ", label)).split())
        seen.setdefault(url, text)
    return list(seen.items())


# "2025-26", "2025-2026", "2025 – 26", "FY 2025-26". The second year must be
# the first plus one, which is what separates a fiscal year from a date range.
YEAR_SPAN = re.compile(r"\b(20\d{2})\s*[-–/]\s*(20)?(\d{2})\b")


def fiscal_years_in(text: str) -> Counter[str]:
    """How often each fiscal year is named in the text, as "FY26"-style labels."""
    found: Counter[str] = Counter()
    for start, _, end in YEAR_SPAN.findall(text):
        if int(end) == (int(start) + 1) % 100:
            found[f"FY{end}"] += 1
    return found


def fiscal_year_of(pdf: Path, pages: int = 6) -> str | None:
    """The fiscal year an annual report is for, read from its first pages.

    The year the report is about is the one its opening pages name most:
    covers, contents and letters repeat it, while the previous year turns up
    only in comparisons. Ties go to the later year, the one a report of that
    year would be the first to print.
    """
    with fitz.open(pdf) as doc:
        text = " ".join(doc[i].get_text() for i in range(min(pages, len(doc))))
    counts = fiscal_years_in(text)
    if not counts:
        return None
    return max(counts, key=lambda fy: (counts[fy], fy))


def download(url: str, destination: Path) -> Path:
    """Fetch a PDF to disk, refusing anything that is not one."""
    data = get(url)
    if not data.startswith(b"%PDF"):
        raise Refused(f"{url} did not return a PDF")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return destination
