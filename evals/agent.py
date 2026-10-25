"""Measure the memo path, including tool routing and source-isolated judging.

Company evidence is judged against its own filing's context before page numbers
can collide with another tool result. Disclosure evidence is copied from the
verified snapshot and checked mechanically; it needs no generative judge.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

from agent.run import CallLimit, run_agent
from evals.score import CORRECT_SCHEMA, CORRECT_SYSTEM, FAITHFUL_SCHEMA, FAITHFUL_SYSTEM, ask_judge
from funds.data import load_funds
from gen.answer import build_client
from gen.guardrails import REFUSAL, cited_pages
from retrieve.embed import load_model
from retrieve.search import open_index


def grade(case: dict, result: dict, client) -> dict:
    text = result['text']
    negative = case.get('refusal', not case.get('expected_pages', [1]))
    row = {'text': text, 'refused': result['refused'], 'api_calls': result['api_calls'],
           'trace': result['trace'], 'reason': result.get('reason', '')}
    if negative:
        return {**row, 'passed': result['refused'] and text == REFUSAL}
    canonical = '\n\n'.join(e['text'] for e in result['evidence'])
    correct = not result['refused'] and all(term in text for term in case.get('contains', []))
    if case.get('expected_answer') and not result['refused']:
        verdict = ask_judge(client, CORRECT_SYSTEM,
                            f"Question: {case['question']}\n\nReference answer: {case['expected_answer']}"
                            f"\n\nSystem answer: {canonical}", CORRECT_SCHEMA)
        correct = correct and verdict['correct']
        row['correct_judge'] = verdict
    faithful = not result['refused']
    faithfulness = []
    for entry in result['evidence']:
        if not entry['url']:
            continue
        cited = set(cited_pages(entry['text']))
        pages = '\n\n'.join(f"--- page {c['page']} chunk {c['chunk']} ---\n{c['text']}"
                            for c in entry['context'] if c['page'] in cited)
        verdict = ask_judge(client, FAITHFUL_SYSTEM,
                            f"Answer: {entry['text']}\n\nCited pages:\n{pages}", FAITHFUL_SCHEMA)
        valid = verdict['faithful'] and all(c['labelled'] and c['arithmetic_right']
                                          for c in verdict['computed_figures'])
        faithful = faithful and valid
        faithfulness.append({'source': entry['source'], **verdict})
    return {**row, 'correct': correct, 'faithful': faithful,
            'faithfulness_judge': faithfulness, 'passed': correct and faithful}


def main() -> None:
    parser = argparse.ArgumentParser(description='Evaluate the bounded cited memo path')
    parser.add_argument('--label', required=True)
    parser.add_argument('--samples', type=int, default=3)
    parser.add_argument('--questions', type=Path, default=Path('evals/agent-cases.jsonl'))
    args = parser.parse_args()
    destination = Path('evals/results') / f'{args.label}.json'
    if destination.exists() or args.samples < 1:
        parser.error('Use a new label and positive sample count')
    cases = [json.loads(line) for line in args.questions.read_text().splitlines() if line.strip()]
    filings = json.loads(Path('corpus/corpus.json').read_text())
    funds = {f['id']: f for f in load_funds()}
    table, model = open_index(Path('data/lancedb')), load_model()
    client = build_client().with_options(timeout=60, max_retries=0)
    out = {'label': args.label, 'samples': args.samples,
           'when': datetime.now(timezone.utc).isoformat(), 'questions': []}
    with destination.open('x') as output:
        json.dump(out, output)
    for case in cases:
        rows = []
        for _ in range(args.samples):
            try:
                result = run_agent(case['question'], table, model, client, filings,
                                   company=case.get('company'), fund=funds.get(case.get('fund')))
                rows.append(grade(case, result, client))
            except CallLimit as error:
                rows.append({'passed': False, 'error': str(error)})
        out['questions'].append({'id': case['id'], 'samples': rows})
        destination.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
        print(f"{case['id']}: {sum(r['passed'] for r in rows)}/{args.samples}", flush=True)
    total = sum(r['passed'] for q in out['questions'] for r in q['samples'])
    print(f'{total}/{len(cases) * args.samples} passed')


if __name__ == '__main__':
    main()
