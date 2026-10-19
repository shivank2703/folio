"""Deterministic disclosure and coverage checks, separate from model-judged reports.

The references were transcribed from rendered issuer factsheets and original
spreadsheet cells. These checks exercise the same lookup and coverage functions
as Streamlit, without asking a model to judge a copied percentage.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from funds.answer import answer
from funds.data import coverage, load_funds
from gen.guardrails import REFUSAL


def run() -> dict:
    funds = {f['id']: f for f in load_funds()}
    filings = json.loads(Path('corpus/corpus.json').read_text())
    results = []
    for line in Path('evals/funds-cases.jsonl').read_text().splitlines():
        case = json.loads(line)
        fund = funds[case['fund']]
        if case['kind'] == 'lookup':
            actual = answer(case['question'], fund)
            passed = actual == REFUSAL if case.get('refusal') else all(s in actual for s in case['contains'])
        else:
            row = next(r for r in fund['holdings'] if r['row'] == case['row'])
            filing = coverage(row, filings)
            actual = filing['company'] if filing else 'Not indexed'
            passed = actual == case['expected']
        results.append({**case, 'actual': actual, 'passed': passed})
    return {'passed': sum(r['passed'] for r in results), 'total': len(results), 'cases': results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run()
    with args.output.open('x') as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
    print(f"Disclosure and coverage: {result['passed']}/{result['total']}")
    for case in result['cases']:
        if not case['passed']:
            print('FAILED', case['id'], case['actual'])
    if result['passed'] != result['total']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
