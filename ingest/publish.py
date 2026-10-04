"""Publish the local index as a release asset and point corpus/index.json at it.

Ingest step (SPEC.md §4). After ingest.add or ingest.build changes the index:

    python -m ingest.publish

packs data/lancedb into a tarball named by its SHA-256, uploads it to the
repository's "index" release (a pre-release, so it never shows as the latest
version of the code), and rewrites corpus/index.json. Committing that file is
what makes the deployed app pick up the new index on its next start
(retrieve/store.py). Old assets stay on the release, so an older commit still
finds the index it names.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path

import lancedb

from retrieve.embed import MODEL_NAME, TABLE_NAME
from retrieve.store import MARKER, POINTER

DB = Path("data/lancedb")
RELEASE = "index"


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout.strip()


def pack(db_path: Path, out_dir: Path) -> Path:
    """Tar the index directory (without its local marker) and name the file by its checksum."""
    staging = out_dir / "folio-index.tar.gz"
    with tarfile.open(staging, "w:gz") as tar:
        tar.add(db_path, arcname="lancedb", filter=lambda info: None if info.name.endswith(MARKER) else info)
    digest = hashlib.sha256(staging.read_bytes()).hexdigest()
    final = out_dir / f"folio-index-{digest[:12]}.tar.gz"
    staging.replace(final)
    return final


def main() -> None:
    table = lancedb.connect(str(DB)).open_table(TABLE_NAME)
    rows = table.search().select(["company", "fiscal_year"]).limit(10_000_000).to_list()
    filings = sorted({f"{r['company']} {r['fiscal_year']}" for r in rows})
    archive = pack(DB, DB.parent)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()

    repo = gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    try:
        gh("release", "view", RELEASE)
    except subprocess.CalledProcessError:
        gh("release", "create", RELEASE, "--prerelease", "--title", "Search index",
           "--notes", "Folio's LanceDB search index, one tarball per build. corpus/index.json in each "
                      "commit names the tarball that commit uses. Built by python -m ingest.publish.")
    gh("release", "upload", RELEASE, str(archive), "--clobber")
    url = f"https://github.com/{repo}/releases/download/{RELEASE}/{archive.name}"

    # The asset must be fetchable anonymously before anything points at it.
    head = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Folio publish check"})
    with urllib.request.urlopen(head, timeout=60) as response:
        assert response.status == 200, f"{url} answered {response.status}"

    pointer = {"asset": archive.name, "url": url, "sha256": digest, "bytes": archive.stat().st_size,
               "chunks": len(rows), "filings": filings, "embedding_model": MODEL_NAME,
               "published": time.strftime("%Y-%m-%d %H:%M")}
    POINTER.write_text(json.dumps(pointer, indent=2) + "\n", encoding="utf-8")
    archive.unlink()
    print(f"published {archive.name} ({pointer['bytes'] / 1e6:.1f} MB, {len(rows)} chunks: {', '.join(filings)})")
    print(f"  {url}\n  {POINTER} updated: commit it to deploy this index")


if __name__ == "__main__":
    main()
