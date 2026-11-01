"""Units reach every extract from their page; unscoped line items look for consolidated figures."""

from __future__ import annotations

import unittest

from gen.answer import SYSTEM_PROMPT, build_prompt
from gen.guardrails import unitless_figures
from retrieve.search import LINE_ITEM, scoped
from retrieve.units import declarations


class UnitDeclarationTests(unittest.TestCase):
    def test_declarations_fused_into_other_lines_are_found(self):
        # Solar Industries: the unit shares a line with the running header, and H is the font's ₹.
        solar = "for the year ended March 31, 2026 | (All amounts in H Crores, unless otherwise stated)"
        self.assertEqual(declarations(solar), ["(All amounts in ₹ Crores, unless otherwise stated)"])
        # L&T writes "(in I crore)" inside a table header.
        self.assertIn("(in ₹ crore)", declarations("Parameters FY 2024-25 (in I crore) | FY 2025-26 | % Growth"))
        # HDFC Bank's "(J Cr)", and Infosys's ten-word statement header.
        self.assertEqual(declarations("Profit After Tax | (J Cr)"), ["(₹ Cr)"])
        infosys = "(In ₹ crore, except equity share and per equity share data)"
        self.assertEqual(declarations(infosys), [infosys])

    def test_prose_and_amounts_are_not_declarations(self):
        self.assertEqual(declarations("The Company earned Rs 400 crores in the year."), [])
        self.assertEqual(declarations("(HCC's share: ₹3,472 crore)"), [])
        self.assertEqual(declarations("Hindustan Construction Company"), [])


class UnitGuardTests(unittest.TestCase):
    CONTEXT = [{"page": 77, "chunk": 5, "text": "Revenue | 1,48,819 | 1,36,592", "units": ["(In ₹ crore)"]},
               {"page": 7, "chunk": 0, "text": "more than 5,800 titles", "units": []}]

    def test_an_amount_without_its_magnitude_is_flagged(self):
        self.assertEqual(unitless_figures("Standalone revenue was 1,48,819 [page 77].", self.CONTEXT),
                         [("1,48,819", [77])])
        self.assertEqual(unitless_figures("Revenue grew 9.0% to ₹1,48,819 [page 77].", self.CONTEXT),
                         [("1,48,819", [77])])

    def test_stated_units_and_undeclared_pages_pass(self):
        for answer in ("Standalone revenue was ₹1,48,819 crore [page 77].",
                       "Revenue (₹ crore) was 1,48,819 against 1,36,592 [page 77].",
                       "Navneet publishes more than 5,800 titles [page 7]."):
            with self.subTest(answer=answer):
                self.assertEqual(unitless_figures(answer, self.CONTEXT), [])


class PromptTests(unittest.TestCase):
    def test_extract_label_carries_the_page_units(self):
        prompt = build_prompt("q?", [{"page": 290, "chunk": 1, "scope": "consolidated", "text": "Raw materials | 1,230.22",
                                      "units": ["(All amounts in ₹ Crores, unless otherwise stated)"]}])
        self.assertIn("units on this page: (All amounts in ₹ Crores, unless otherwise stated)", prompt)
        self.assertNotIn("units on this page", build_prompt("q?", [{"page": 3, "chunk": 0, "text": "x"}]))

    def test_prompt_prefers_consolidated_and_never_advises(self):
        self.assertIn("state the consolidated figure and say it is", SYSTEM_PROMPT)
        for word in ("buy", "sell", "recommend"):
            self.assertNotIn(word, SYSTEM_PROMPT.lower())


class ScopeRankingTests(unittest.TestCase):
    class Query:
        def where(self, clause):
            self.clause = clause
            return self

    def test_strict_scope_excludes_unstated_chunks(self):
        self.assertEqual(scoped(self.Query(), "RELIANCE", "consolidated", strict=True).clause,
                         "company = 'RELIANCE' AND scope = 'consolidated'")
        self.assertIn("'unstated'", scoped(self.Query(), "RELIANCE", "consolidated").clause)

    def test_line_items_are_recognised(self):
        self.assertTrue(LINE_ITEM.search("What was Reliance's net profit in FY26?"))
        self.assertTrue(LINE_ITEM.search("How big is L&T's order book?"))
        self.assertFalse(LINE_ITEM.search("How many titles does Navneet publish?"))


if __name__ == "__main__":
    unittest.main()
