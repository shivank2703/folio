"""An overview keeps only clean, cited sections, and knows when it is stale."""

from __future__ import annotations

import unittest
from unittest import mock

from overviews import build


def verdict(text: str, **flags) -> dict:
    return {"refused": False, "text": text, "reason": "", "invalid_citations": [], "ungrounded": [],
            "unitless": [], "scrubbed": [], **flags}


class SectionTests(unittest.TestCase):
    def test_refused_and_flagged_answers_become_missing_sections(self):
        refused = build.section("q", {**verdict("Not in the filing."), "refused": True, "reason": "below the floor"})
        self.assertEqual((refused["text"], refused["missing"]), ("", "below the floor"))
        flagged = build.section("q", verdict("Revenue was 1,48,819 [page 77].", unitless=[("1,48,819", [77])]))
        self.assertEqual((flagged["text"], flagged["missing"]), ("", "withheld: unitless"))

    def test_only_sentences_with_their_own_citation_survive(self):
        kept = build.section("q", verdict("The company builds tunnels [page 12]. It is well regarded. "
                                          "Revenue was ₹4,801 crore [page 7]."))
        self.assertEqual(kept["text"], "The company builds tunnels [page 12]. Revenue was ₹4,801 crore [page 7].")
        self.assertEqual(kept["pages"], [7, 12])
        self.assertEqual(kept["missing"], "")

    def test_questions_cover_every_section_of_every_filing(self):
        manifest = [{"company": "AAA", "name": "Aaa Ltd", "fiscal_year": "FY26"},
                    {"company": "BBB", "name": "Bbb Ltd", "fiscal_year": "FY25"}]
        questions = build.questions(manifest)
        self.assertEqual(len(questions), 2 * len(build.SECTIONS))
        self.assertIn("Bbb Ltd's revenue from operations in FY25", questions[len(build.SECTIONS) + 1]["question"])

    def test_staleness_follows_filing_index_and_prompt(self):
        entry = {"sha256": "f1"}
        with mock.patch.object(build, "fingerprint", return_value="p1"), \
                mock.patch.object(build.Path, "read_text", return_value='{"sha256": "i1"}'):
            fresh = {"filing_sha256": "f1", "index": "i1", "fingerprint": "p1"}
            self.assertFalse(build.stale(fresh, entry))
            self.assertTrue(build.stale(None, entry))
            self.assertTrue(build.stale({**fresh, "index": "i0"}, entry))
            self.assertTrue(build.stale({**fresh, "fingerprint": "p0"}, entry))
            self.assertTrue(build.stale(fresh, {"sha256": "f2"}))


if __name__ == "__main__":
    unittest.main()
