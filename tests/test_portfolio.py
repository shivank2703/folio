"""The owner's portfolio view: parsing, matching to filings and funds, and owner-only visibility.

Fixtures are arbitrary indexed companies and public funds, not anyone's holdings.
"""

import json
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from funds.data import load_funds
from ui.portfolio import disclosures, normalised, parse, resolve

FILINGS = json.loads(Path("corpus/corpus.json").read_text(encoding="utf-8"))
FUNDS = load_funds()
SAMPLE = "# test fixture\nSUNPHARMA, 5\nHCC\nHDFC\nTCS\nHDFC Defence Fund\nsomething else entirely\n"


class PortfolioTests(unittest.TestCase):
    def test_parse_keeps_weights_as_typed_and_skips_comments(self):
        self.assertEqual(parse("# x\n\nINFY, 8.5%\n LT \n"),
                         [{"entry": "INFY", "weight": "8.5%"}, {"entry": "LT", "weight": ""}])

    def test_symbols_resolve_to_filings_and_names_to_funds(self):
        kinds = {h["entry"]: (h["kind"], (h["filing"] or h["fund"] or {}).get("name")) for h in resolve(parse(SAMPLE), FILINGS, FUNDS)}
        self.assertEqual(kinds["SUNPHARMA"][0], "stock")
        self.assertEqual(kinds["HCC"][1], "Hindustan Construction Company")
        self.assertEqual(kinds["TCS"], ("stock", None))           # a symbol Folio has not indexed
        self.assertEqual(kinds["HDFC"], ("stock", None))          # never the fund that starts with HDFC
        self.assertEqual(kinds["HDFC Defence Fund"], ("fund", "HDFC Defence Fund"))
        self.assertEqual(kinds["something else entirely"][0], "unrecognised")

    def test_fund_overlap_uses_reviewed_mapping_then_exact_name(self):
        sun = next(f for f in FILINGS if f["company"] == "SUNPHARMA")
        found = disclosures(sun, FUNDS)
        self.assertTrue(found)
        self.assertTrue(all(d["row"].get("company") == "SUNPHARMA" or normalised(d["row"]["name"]) == normalised(sun["name"])
                            for d in found))
        self.assertIn("reviewed mapping", {d["how"] for d in found})
        self.assertEqual(normalised("Infosys Ltd."), normalised("INFOSYS LIMITED"))

    def test_view_renders_without_an_api_call(self):
        app = AppTest.from_string(f'''
import json
from pathlib import Path
from funds.data import load_funds
import ui.portfolio as portfolio
portfolio.read_portfolio = lambda: {SAMPLE!r}
portfolio.render(json.loads(Path("corpus/corpus.json").read_text()), load_funds(), {{}})
''').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 6)
        self.assertIn("Not recognised", " ".join(c.value for c in app.caption))


class OwnerOnlyTests(unittest.TestCase):
    def test_portfolio_mode_is_offered_to_the_owner_only(self):
        from ui.app import research_modes
        self.assertNotIn("My portfolio", research_modes(owner=False))
        self.assertIn("My portfolio", research_modes(owner=True))


if __name__ == "__main__":
    unittest.main()
