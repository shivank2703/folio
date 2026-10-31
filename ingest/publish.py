"""Publish the local index as a release asset and point corpus/index.json at it.

Ingest step (SPEC.md §4). After ingest.add or ingest.build changes the index:

    python -m ingest.publish

packs data/lancedb into a tarball named by its SHA-256, uploads it to the
repository's "index" release (a pre-release, so it never shows as the latest
version of the code) through the GitHub API, and rewrites corpus/index.json. Committing that file is
what makes the deployed app pick up the new index on its next start
(retrieve/store.py). Old assets stay on the release, so an older commit still
finds the index it names.

Publishing replaces what every visitor searches, so it refuses an index that
does not cover corpus/corpus.json exactly. A fresh clone once built a
one-company index (ingest.add never fetched the published one first), and
publishing it would have dropped the other 32 filings from the app while the
manifest still listed them.
"""

from __future__ import annotations

import hashlib
import json
import tarfile
import time
import urllib.request
from pathlib import Path

import lancedb

from ingest import github
from retrieve.embed import MODEL_NAME, TABLE_NAME
from retrieve.store import MARKER, POINTER, ensure_index, source_of

DB = Path("data/lancedb")
MANIFEST = Path("corpus/corpus.json")
RELEASE = "index"


class PublishRefused(Exception):
    """The local index is not one the app should serve; nothing was uploaded."""


def pack(db_path: Path, out_dir: Path) -> Path:
    """Tar the index directory (without its local marker) and name the file by its checksum."""
    staging = out_dir / "folio-index.tar.gz"
    with tarfile.open(staging, "w:gz") as tar:
        tar.add(db_path, arcname="lancedb", filter=lambda info: None if info.name.endswith(MARKER) else info)
    digest = hashlib.sha256(staging.read_bytes()).hexdigest()
    final = out_dir / f"folio-index-{digest[:12]}.tar.gz"
    staging.replace(final)
    return final


def indexed_filings(db_path: Path) -> tuple[list[str], int]:
    """Every "COMPANY FY" the index holds rows for, and its row count."""
    table = lancedb.connect(str(db_path)).open_table(TABLE_NAME)
    rows = table.search().select(["company", "fiscal_year"]).limit(10_000_000).to_list()
    return sorted({f"{r['company']} {r['fiscal_year']}" for r in rows}), len(rows)


def check_coverage(filings: list[str], manifest: list[dict]) -> None:
    """Refuse unless the index holds exactly the filings the manifest lists.

    Missing filings are the dangerous direction: the app lists a company from
    corpus.json and every question about it searches nothing. Extra filings
    mean the manifest committed beside this index would not describe it, so
    they are refused too rather than published invisibly.
    """
    listed = {f"{e['company']} {e['fiscal_year']}" for e in manifest}
    missing, extra = sorted(listed - set(filings)), sorted(set(filings) - listed)
    if missing or extra:
        problems = []
        if missing:
            problems.append(f"missing {len(missing)} of the {len(listed)} filings in corpus.json: {', '.join(missing)}")
        if extra:
            problems.append(f"holding {len(extra)} filing(s) corpus.json does not list: {', '.join(extra)}")
        raise PublishRefused(
            "not publishing: the local index is " + "; and ".join(problems) + ". If it was built before "
            "the published index was fetched, delete data/lancedb, re-run python -m ingest.add for the "
            "new companies (it fetches the published index first), then publish again.")


def publish_index(db_path: Path = DB, manifest_path: Path = MANIFEST, pointer_path: Path = POINTER) -> dict:
    """Upload data/lancedb as a release asset and write corpus/index.json; return the pointer.

    The same path runs from the command line and from the app's add-company
    panel, through the GitHub API (ingest/github.py), so the deployed host
    needs no gh CLI. The published index is fetched first when there is no
    local one, so a fresh clone can never publish an empty or partial table;
    an index that is exactly the published one is not uploaded again.
    """
    ensure_index(db_path, pointer_path)
    if source_of(db_path) != "local":
        print("the local index is the published one; nothing to publish")
        return json.loads(pointer_path.read_text(encoding="utf-8"))
    filings, chunks = indexed_filings(db_path)
    check_coverage(filings, json.loads(manifest_path.read_text(encoding="utf-8")))

    archive = pack(db_path, db_path.parent)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    release = github.ensure_release(
        RELEASE, "Search index",
        "Folio's LanceDB search index, one tarball per build. corpus/index.json in each "
        "commit names the tarball that commit uses. Built by python -m ingest.publish.")
    url = github.upload_asset(release, archive)

    # The asset must be fetchable anonymously before anything points at it.
    head = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Folio publish check"})
    with urllib.request.urlopen(head, timeout=60) as response:
        assert response.status == 200, f"{url} answered {response.status}"

    pointer = {"asset": archive.name, "url": url, "sha256": digest, "bytes": archive.stat().st_size,
               "chunks": chunks, "filings": filings, "embedding_model": MODEL_NAME,
               "published": time.strftime("%Y-%m-%d %H:%M")}
    pointer_path.write_text(json.dumps(pointer, indent=2) + "\n", encoding="utf-8")
    archive.unlink()
    return pointer


def main() -> None:
    try:
        pointer = publish_index()
    except PublishRefused as refused:
        raise SystemExit(str(refused)) from None
    print(f"published {pointer['asset']} ({pointer['bytes'] / 1e6:.1f} MB, {pointer['chunks']} chunks: "
          f"{', '.join(pointer['filings'])})")
    print(f"  {pointer['url']}\n  {POINTER} updated: commit it to deploy this index")


if __name__ == "__main__":
    main()
