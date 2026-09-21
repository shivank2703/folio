"""Batch ingest: every filing in the corpus, one index.

Stage 9 (SPEC.md §4). One command turns corpus/ into a searchable index —
verify, extract, preprocess, chunk each filing, then embed them all into a
single table.

Identity comes from corpus/corpus.json, never from filenames: one of these
reports is called "annual-report-24-25.pdf", which says nothing about whose it
is. The manifest carries the company code that rides on every chunk, and the
SHA-256 that says the file on disk is the document the index claims to be
built from. A mismatch stops the run rather than quietly indexing something
else under a name that will later appear in a citation.

Rebuilds are idempotent. Each stage overwrites its own file, the chunk files
are named per filing so one company's rebuild cannot erase another's, and the
embed step drops the table before writing so the committed index holds one
version's files rather than its predecessors' as well.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from ingest.chunk import chunk_report
from ingest.extract import extract_pages, write_jsonl
from ingest.preprocess import preprocess
from retrieve.embed import embed_texts, load_model, to_arrow, write_index


def verify(pdf_path: Path, expected: str) -> None:
    """Stop unless the file on disk is the one the manifest describes."""
    if not pdf_path.exists():
        raise SystemExit(f"{pdf_path} is missing; corpus/SOURCES.md says where to download it")
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if digest != expected:
        raise SystemExit(
            f"{pdf_path.name}: sha256 {digest[:12]}... does not match the manifest's {expected[:12]}...; "
            "the file is not the filing this index would claim to cite"
        )


def ingest_filing(entry: dict, corpus_dir: Path, data_dir: Path) -> Path:
    """Extract, preprocess and chunk one filing; return the chunk file it wrote."""
    pdf_path = corpus_dir / entry["file"]
    verify(pdf_path, entry["sha256"])
    company, fiscal_year = entry["company"], entry["fiscal_year"]
    stem = f"{company.lower()}_{fiscal_year.lower()}"

    # The plain-text dump is not an input to anything downstream; it is the
    # before-picture the eyeball check reads when a new document's layout
    # misbehaves (SPEC.md §3.6), which is exactly when it is needed.
    write_jsonl(extract_pages(pdf_path, company, fiscal_year), data_dir / f"{stem}_pages.jsonl")

    pages = preprocess(pdf_path, company, fiscal_year)
    write_jsonl(pages, data_dir / f"{stem}_clean.jsonl")
    chunks = chunk_report(pages)
    chunk_path = data_dir / f"{stem}_chunks.jsonl"
    write_jsonl(chunks, chunk_path)

    kept = sum(1 for page in pages if not page["excluded"])
    print(f"  {entry['name']} ({company}): {len(pages)} pages, {kept} kept -> {len(chunks)} chunks")
    return chunk_path


def directory_size(path: Path) -> int:
    """Bytes on disk under a directory — the index ships in git, so its size matters."""
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the whole index from every filing in the manifest.")
    parser.add_argument("--manifest", type=Path, default=Path("corpus/corpus.json"), help="filings to ingest")
    parser.add_argument("--data", type=Path, default=Path("data"), help="generated-artifact folder")
    parser.add_argument("--db", type=Path, default=Path("data/lancedb"), help="LanceDB directory")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    print(f"ingesting {len(manifest)} filing(s) from {args.manifest.parent}/")
    started = time.perf_counter()
    chunk_files = [ingest_filing(entry, args.manifest.parent, args.data) for entry in manifest]
    ingested = time.perf_counter()

    chunks = [json.loads(line) for path in chunk_files for line in path.read_text(encoding="utf-8").splitlines()]
    model = load_model()
    vectors = embed_texts(model, [chunk["text"] for chunk in chunks])
    write_index(to_arrow(chunks, vectors), args.db)
    finished = time.perf_counter()

    print(f"\n{len(chunks)} chunks from {len(manifest)} filing(s) -> {args.db}")
    print(f"  ingest {ingested - started:.0f}s, embed {finished - ingested:.0f}s, total {finished - started:.0f}s")
    print(f"  index on disk: {directory_size(args.db) / 1e6:.1f} MB (it ships in git)")


if __name__ == "__main__":
    main()
