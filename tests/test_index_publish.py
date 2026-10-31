"""A fresh clone must add to the published index, and publish must never shrink it.

The bug these guard: on a clone with no data/lancedb, ingest.add's
replace_filing found no table and created one holding only the new company;
ingest.publish then uploaded it, and the app would have lost every other
filing. Built offline: a real LanceDB table with random unit vectors (no
embedding model), served to retrieve.store through a file:// pointer.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lancedb
import numpy as np

from ingest import add, publish
from retrieve.embed import DIMENSION, TABLE_NAME, replace_filing, to_arrow, write_index
from retrieve.store import MARKER, source_of


def rows(company: str, n: int = 3):
    """An Arrow table of n chunks for one filing, shaped exactly like ingest's."""
    chunks = [{"text": f"{company} chunk {i}", "company": company, "fiscal_year": "FY26", "page": i + 1,
               "chunk": 0, "tokens": 10, "scope": "unstated"} for i in range(n)]
    vectors = np.random.default_rng(len(company) + n).normal(size=(n, DIMENSION)).astype(np.float32)
    return to_arrow(chunks, vectors / np.linalg.norm(vectors, axis=1, keepdims=True))


def companies(db: Path) -> set[str]:
    table = lancedb.connect(str(db)).open_table(TABLE_NAME)
    return {r["company"] for r in table.search().select(["company"]).limit(1000).to_list()}


class PublishedIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        # The "published" index: two filings, packed exactly as publish packs one.
        source = self.tmp / "published" / "lancedb"
        write_index(rows("AAA"), source)
        replace_filing(rows("BBB"), "BBB", source)
        archive = publish.pack(source, source.parent)
        self.pointer = self.tmp / "index.json"
        self.pointer.write_text(json.dumps({
            "asset": archive.name, "url": archive.as_uri(),
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}))
        self.manifest = self.tmp / "corpus.json"
        self.db = self.tmp / "clone" / "data" / "lancedb"

    def write_manifest(self, *codes: str) -> None:
        self.manifest.write_text(json.dumps([{"company": c, "fiscal_year": "FY26"} for c in codes]))

    def test_the_hazard_replace_filing_alone_builds_a_one_company_index(self):
        replace_filing(rows("CCC"), "CCC", self.db)
        self.assertEqual(companies(self.db), {"CCC"})

    def test_add_on_a_fresh_clone_fetches_the_published_index_first(self):
        self.assertFalse(self.db.exists())
        add.index_filing(rows("CCC"), "CCC", self.db, self.pointer)
        self.assertEqual(companies(self.db), {"AAA", "BBB", "CCC"})
        self.assertEqual(source_of(self.db), "local")

    def test_publish_refuses_an_index_missing_manifest_filings(self):
        replace_filing(rows("CCC"), "CCC", self.db)  # the old, buggy path
        self.write_manifest("AAA", "BBB", "CCC")
        with mock.patch.object(publish.github, "upload_asset") as upload, \
                mock.patch.object(publish.github, "ensure_release") as release:
            with self.assertRaises(publish.PublishRefused) as refused:
                publish.publish_index(self.db, self.manifest, self.pointer)
        self.assertIn("AAA FY26, BBB FY26", str(refused.exception))
        upload.assert_not_called()
        release.assert_not_called()

    def test_publish_refuses_filings_the_manifest_does_not_list(self):
        add.index_filing(rows("CCC"), "CCC", self.db, self.pointer)
        self.write_manifest("AAA", "BBB")
        with self.assertRaises(publish.PublishRefused):
            publish.publish_index(self.db, self.manifest, self.pointer)

    def test_publish_on_a_fresh_clone_uploads_nothing(self):
        self.write_manifest("AAA", "BBB")
        with mock.patch.object(publish.github, "upload_asset") as upload:
            pointer = publish.publish_index(self.db, self.manifest, self.pointer)
        upload.assert_not_called()
        self.assertEqual(pointer["sha256"], json.loads(self.pointer.read_text())["sha256"])
        self.assertEqual(companies(self.db), {"AAA", "BBB"})

    def test_publish_uploads_a_complete_index(self):
        add.index_filing(rows("CCC"), "CCC", self.db, self.pointer)
        self.write_manifest("AAA", "BBB", "CCC")
        ok = mock.MagicMock(status=200)
        ok.__enter__.return_value = ok
        with mock.patch.object(publish.github, "ensure_release", return_value={}), \
                mock.patch.object(publish.github, "upload_asset", return_value="https://example.invalid/x.tar.gz") as upload, \
                mock.patch.object(publish.urllib.request, "urlopen", return_value=ok):
            pointer = publish.publish_index(self.db, self.manifest, self.pointer)
        upload.assert_called_once()
        self.assertEqual(pointer["filings"], ["AAA FY26", "BBB FY26", "CCC FY26"])
        self.assertEqual(pointer["chunks"], 9)
        self.assertFalse(any(p.name.endswith(".tar.gz") for p in self.db.parent.iterdir()))
        self.assertTrue((self.db / MARKER).exists())


if __name__ == "__main__":
    unittest.main()
