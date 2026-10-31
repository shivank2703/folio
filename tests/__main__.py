"""Every offline check in one command: .venv/bin/python -m tests

Runs the unit tests and the deterministic fund-disclosure checks
(evals/funds-cases.jsonl). Neither calls the model nor needs the embedding
model or the index, so this is what CI runs on every push; the model-judged
evals (evals.score) spend API credit and stay a deliberate, local step.
"""

from __future__ import annotations

import sys
import unittest

from evals.funds import run as fund_checks


def main() -> int:
    # Same discovery as `python -m unittest discover -s tests`: the test files
    # import as top-level modules, so either command runs the same suite.
    suite = unittest.defaultTestLoader.discover("tests")
    units = unittest.TextTestRunner(verbosity=1).run(suite)
    funds = fund_checks()
    print(f"\nDeterministic fund checks: {funds['passed']}/{funds['total']}")
    for case in funds["cases"]:
        if not case["passed"]:
            print("FAILED", case["id"], case["actual"])
    return 0 if units.wasSuccessful() and funds["passed"] == funds["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
