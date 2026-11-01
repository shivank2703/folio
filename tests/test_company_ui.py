"""The company page: search across filings, the stored overview, example questions."""

import json
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from ui.company import examples, find_filings, link_citations, short_name

FILINGS = json.loads(Path("corpus/corpus.json").read_text(encoding="utf-8"))

APP = '''
import json
from pathlib import Path
import streamlit as st
from ui import company
filings = json.loads(Path("corpus/corpus.json").read_text(encoding="utf-8"))
filing = company.choose(filings)
if filing:
    company.header(filing)
    company.render_overview(filing, OVERVIEW)
    asked = company.ask(filing)
    if asked:
        st.write("ASKED: " + asked)
'''


class CompanySearchTests(unittest.TestCase):
    def test_search_matches_name_code_and_symbol(self):
        self.assertEqual(find_filings("infosys", FILINGS)[0]["company"], "INFY")
        self.assertEqual(find_filings("INFY", FILINGS)[0]["company"], "INFY")
        self.assertEqual(find_filings("LT", FILINGS)[0]["company"], "LT")
        self.assertEqual(find_filings("L&T".replace("&", ""), FILINGS)[0]["company"], "LT")
        self.assertIn("NAVNEET", [f["company"] for f in find_filings("navnetedul", FILINGS)])
        self.assertEqual({f["company"] for f in find_filings("bank", FILINGS)},
                         {"AXISBANK", "HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN"})
        self.assertEqual(find_filings("no such company", FILINGS), [])
        self.assertEqual(len(find_filings("", FILINGS)), len(FILINGS))

    def test_examples_use_the_short_name_and_fiscal_year(self):
        infy = next(f for f in FILINGS if f["company"] == "INFY")
        self.assertEqual(short_name(infy), "Infosys")
        self.assertIn("What was Infosys's revenue from operations in FY26?", examples(infy))

    def test_citations_link_to_the_page(self):
        self.assertEqual(link_citations("₹4,801 crore [page 7].", "https://x.example/r.pdf"),
                         "₹4,801 crore [page 7](https://x.example/r.pdf#page=7).")


class CompanyPageTests(unittest.TestCase):
    def overview(self, sha: str) -> str:
        return repr({"filing_sha256": sha, "built": "2026-11-01", "sections": {
            "business": {"heading": "What it does", "text": "It builds tunnels and dams [page 12].", "pages": [12]},
            "risks": {"heading": "Top risks", "text": "", "pages": [], "missing": "refused"}}})

    def test_search_overview_and_example_question(self):
        hcc = next(f for f in FILINGS if f["company"] == "HCC")
        app = AppTest.from_string(APP.replace("OVERVIEW", self.overview(hcc["sha256"]))).run()
        self.assertFalse(app.exception)
        app.text_input(key="company_query").input("hindustan construction").run()
        self.assertEqual(app.selectbox(key="company_choice").value.split(" (")[0], "Hindustan Construction Company")
        shown = " ".join(m.value for m in app.markdown)
        self.assertIn("[page 12](", shown)
        self.assertIn("Not found in the filing: top risks", " ".join(c.value for c in app.caption))
        app.button[0].click().run()
        self.assertIn("ASKED: What does Hindustan Construction Company do?", [m.value for m in app.markdown])

    def test_overview_of_another_filing_version_is_not_shown(self):
        app = AppTest.from_string(APP.replace("OVERVIEW", self.overview("stale"))).run()
        self.assertIn("No overview has been built", " ".join(c.value for c in app.caption))

    def test_no_match_says_so(self):
        app = AppTest.from_string(APP.replace("OVERVIEW", "None")).run()
        app.text_input(key="company_query").input("zzzz").run()
        self.assertIn("No indexed filing matches", app.info[0].value)


if __name__ == "__main__":
    unittest.main()
