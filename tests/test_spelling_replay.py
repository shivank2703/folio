"""Misspelling correction keeps real words, and a recorded retrieval replays faithfully."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from evals import retrieval
from retrieve.embed import DIMENSION, to_arrow, write_index
from retrieve.search import open_index
from retrieve.spelling import correct, one_edit

FILING_TEXT = ("TOTAL ASSETS 2,28,299 total assets total equity total income. The Company has three urea plants "
               "plants plants. Revenue revenue revenue from operations. Payments payments payments were made. "
               "Rail rail rail freight. Oem oem oem parts. Does does does it matter.")


class Table:
    """Just enough of a LanceDB table for vocabulary(): every row's text for one company."""

    def __init__(self, text: str):
        self.text = text

    def search(self):
        return self

    def where(self, _):
        return self

    def select(self, _):
        return self

    def limit(self, _):
        return self

    def to_list(self):
        return [{"text": self.text}]


class SpellingTests(unittest.TestCase):
    def setUp(self):
        self.table = Table(FILING_TEXT)

    def test_typos_become_the_filing_word(self):
        self.assertEqual(correct("totla assets navneet", self.table, "AAA"), "total assets navneet")
        self.assertEqual(correct("how many urea plnts", self.table, "AAA"), "how many urea plants")
        self.assertEqual(correct("divis revenu fy26", self.table, "AAA"), "divis revenue fy26")

    def test_real_words_the_filing_never_prints_are_kept(self):
        # Each was rewritten by the first, filing-only version of the corrector,
        # turning a not-in-the-filing question into another question.
        for question in ("How many patents did HCC file?", "How many branches in Brazil?",
                         "Write a poem about steel", "How many drones did it deploy?"):
            with self.subTest(question=question):
                self.assertEqual(correct(question, self.table, "AAA"), question)

    def test_no_company_no_change(self):
        self.assertEqual(correct("totla assets", self.table, None), "totla assets")

    def test_one_edit(self):
        self.assertTrue(one_edit("totla", "total"))
        self.assertTrue(one_edit("plnts", "plants"))
        self.assertFalse(one_edit("drones", "does"))
        self.assertFalse(one_edit("assets", "assets"))


class ReplayTests(unittest.TestCase):
    def test_replay_rebuilds_text_and_keeps_scores(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        chunks = [{"text": f"page {p} chunk {c}", "company": "AAA", "fiscal_year": "FY26", "page": p, "chunk": c,
                   "tokens": 5, "scope": "unstated"} for p in (3, 4) for c in (0, 1)]
        vectors = np.eye(len(chunks), DIMENSION, dtype=np.float32)
        write_index(to_arrow(chunks, vectors), tmp / "db")
        dump = {"questions": {retrieval.key("AAA", "q?"): {
            "hits": [{"page": 4, "chunk": 1, "score": 0.71, "sibling": False}],
            "context": [{"page": 4, "chunk": 0, "score": None, "sibling": True},
                        {"page": 4, "chunk": 1, "score": 0.71, "sibling": False}]}}}
        hits, context = retrieval.replay(json.loads(json.dumps(dump)), open_index(tmp / "db"), "AAA", "q?")
        self.assertEqual([(h["page"], h["chunk"], h["text"], h["score"]) for h in hits], [(4, 1, "page 4 chunk 1", 0.71)])
        self.assertEqual([(c["chunk"], c["sibling"]) for c in context], [(0, True), (1, False)])
        with self.assertRaises(KeyError):
            retrieval.replay(dump, open_index(tmp / "db"), "AAA", "a different question")


if __name__ == "__main__":
    unittest.main()


class GateTests(unittest.TestCase):
    def test_floor_reads_the_filing_wide_gate(self):
        from gen.guardrails import MIN_SIMILARITY, has_enough_context

        # A ranked list of weak chunks still passes when the filing holds a close one.
        self.assertTrue(has_enough_context([{"score": 0.50, "gate": MIN_SIMILARITY}]))
        self.assertFalse(has_enough_context([{"score": 0.50, "gate": MIN_SIMILARITY - 0.01}]))
        # Without a recorded gate (older recordings) the hits' own scores decide.
        self.assertTrue(has_enough_context([{"score": MIN_SIMILARITY}]))
