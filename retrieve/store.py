"""Where the index lives: a GitHub release asset, fetched at startup and checked.

Ingest step (SPEC.md §4, §7). Until v1.1 the LanceDB index was committed, so
a fresh clone or a Community Cloud container had it without a build. That
stops scaling at a few filings: every rebuild adds ~10 MB to git history, and
Funds will add 20-30 filings. The index now lives as a tarball attached to the
repository's "index" release; corpus/index.json, which is committed, names the
exact tarball and its SHA-256. A commit therefore still pins the index its code
was tested with, as the committed files did, without carrying its bytes.

A GitHub release asset rather than a Hugging Face dataset: the repository's
gh CLI is already authenticated, a public repository's assets download
without credentials, and the code and its data stay in one place.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

POINTER = Path("corpus/index.json")
# Written beside the index: the SHA-256 of the tarball it came from, or
# "local" for an index built on this machine by ingest.build / ingest.add.
MARKER = ".folio-index-source"


def source_of(db_path: Path) -> str | None:
    marker = db_path / MARKER
    return marker.read_text(encoding="utf-8").strip() if marker.exists() else None


def mark_local(db_path: Path) -> None:
    """Record that this index was built here, so startup never overwrites it with a download."""
    (db_path / MARKER).write_text("local\n", encoding="utf-8")


def ensure_index(db_path: Path) -> str:
    """Make sure db_path holds the index corpus/index.json names; return where it came from.

    A locally built index is always kept: a developer adding a company must
    not have it replaced by the published one. Otherwise the index is fetched
    when it is missing or came from a different tarball, verified against the
    pointer's SHA-256 before anything is unpacked, and swapped in whole.
    """
    have = source_of(db_path)
    if have == "local":
        return "local build"
    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    if have == pointer["sha256"] and (db_path / "chunks.lance").exists():
        return f"cached {pointer['asset']}"

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / pointer["asset"]
        request = urllib.request.Request(pointer["url"], headers={"User-Agent": "Folio index fetch"})
        with urllib.request.urlopen(request, timeout=300) as response, archive.open("wb") as out:
            shutil.copyfileobj(response, out)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != pointer["sha256"]:
            raise RuntimeError(f"index download {pointer['url']} has SHA-256 {digest}, "
                               f"not the {pointer['sha256']} that {POINTER} names")
        unpacked = Path(tmp) / "unpacked"
        with tarfile.open(archive) as tar:
            tar.extractall(unpacked, filter="data")
        if db_path.exists():
            shutil.rmtree(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(unpacked / "lancedb"), str(db_path))
    (db_path / MARKER).write_text(pointer["sha256"] + "\n", encoding="utf-8")
    return f"downloaded {pointer['asset']}"
