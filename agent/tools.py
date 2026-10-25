"""Keep an agent's evidence inside one selected company or a fund's top ten.

The model chooses questions, but Python resolves filing identity, coverage and
source links. Final prose is copied from accepted evidence, never rewritten by
the orchestration model, so source identity survives a multi-tool memo.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from funds.answer import OUT_OF_SCOPE, matches_snapshot
from funds.data import coverage, fact_citation, row_citation
from gen.answer import guarded_answer
from gen.guardrails import ADVICE, CITATION, REFUSAL
from retrieve.search import DEFAULT_K, EXPANSION_SEEDS, page_context, search

MAX_EVIDENCE_WORDS = 200


def report_sentences(text: str) -> list[str]:
    """Keep only sentences that carry their own metadata page citation.

    Some answers put their citation just after the full stop; moving that
    punctuation does not change the claim. A citation in one sentence must
    never license an uncited sentence beside it.
    """
    text = re.sub(r"[.!?]\s*((?:\[page \d+\]\s*)+)", r" \1. ", text)
    text = re.sub(r'\b(?:Rs|Ltd|Co|Dr)\.', lambda m: m[0].replace('.', '\ue000'), text)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    accepted = []
    for sentence in sentences:
        sentence = sentence.replace('\ue000', '.').strip().removeprefix('- ').strip()
        if not sentence:
            continue
        if not CITATION.search(sentence) or ADVICE.search(sentence):
            continue
        if re.search(r"https?://|\]\(", sentence):
            continue
        accepted.append(sentence)
    return accepted


class ResearchTools:
    """One request's source registry; no state is shared across visitors."""

    def __init__(self, table, model, client, filings: list[dict], *, company: str | None = None,
                 fund: dict | None = None, request: str = ''):
        if (company is None) == (fund is None):
            raise ValueError('Select exactly one company or fund')
        self.table, self.model, self.client = table, model, client
        self.fund = fund
        self.company = company
        self.original_request = request
        self.request = request.lower()
        if fund is not None:
            self.filings = {f['company']: f for row in fund['holdings']
                            if (f := coverage(row, filings)) is not None}
            self.subject = fund['name']
        else:
            self.filings = {f['company']: f for f in filings if f['company'] == company}
            if not self.filings:
                raise ValueError('Company is not indexed')
            self.subject = next(iter(self.filings.values()))['name']
        self.evidence: dict[str, dict] = {}
        self.trace: list[dict] = []
        self._cache: dict[str, dict] = {}

    def catalog(self) -> dict:
        result = {'subject': self.subject, 'filings': [
            {'company': f['company'], 'name': f['name'], 'fiscal_year': f['fiscal_year']}
            for f in self.filings.values()]}
        if self.fund:
            result.update(portfolio_date=self.fund['portfolio_date'],
                          factsheet_date=self.fund['factsheet_date'])
        return result

    def definitions(self) -> list[dict]:
        tools = [{
            'name': 'company_question',
            'description': 'Ask one precise factual question of an indexed annual report. '
                           'Copy the user question exactly when it is a single report question. '
                           'Use the company code, not an expanded company name. '
                           'Preserve requested fiscal year and statement scope exactly.',
            'input_schema': {'type': 'object', 'properties': {
                'company': {'type': 'string', 'enum': list(self.filings)},
                'question': {'type': 'string', 'maxLength': 1000}},
                'required': ['company', 'question'], 'additionalProperties': False},
        }] if self.filings else []
        if self.fund:
            tools.append({
                'name': 'fund_disclosure',
                'description': 'Read one verified field or the top ten domestic equity rows '
                               'of the selected fund. Factsheet and portfolio dates differ.',
                'input_schema': {'type': 'object', 'properties': {
                    'field': {'type': 'string', 'enum': [
                        'benchmark', 'expense_ratio', 'exit_load', 'top_holdings']},
                    'count': {'type': 'integer', 'description':
                              'For top_holdings only: number requested, 1 for largest, at most 10.'}},
                    'required': ['field'], 'additionalProperties': False},
            })
        return tools

    def _record(self, text: str, source: str, *, context: list[dict] | None = None,
                url: str | None = None) -> dict:
        if len(text.split()) > MAX_EVIDENCE_WORDS:
            return {'refused': True, 'text': REFUSAL, 'reason': 'Evidence exceeds memo budget'}
        key = f'E{len(self.evidence) + 1}'
        entry = {'id': key, 'text': text, 'source': source, 'context': context or [], 'url': url}
        self.evidence[key] = entry
        return {'id': key, 'text': text, 'source': source}

    def _company(self, company: str, question: str) -> dict:
        filing = self.filings.get(company)
        if filing is None or not isinstance(question, str) or not 1 <= len(question.strip()) <= 1000:
            raise ValueError('Question or company is outside selected coverage')
        # A precise company request already is a retrieval query. Letting the
        # planner paraphrase it changes the calibrated floor for no benefit.
        if self.company and self.original_request and not re.search(
                r'\b(?:memo|summari[sz]e|summary|overview|profile)\b', self.request):
            question = self.original_request
        else:
            # The catalog already resolves the issuer. Repeating its legal
            # name makes corporate headers outrank the requested account row.
            # Replace only that manifest identity; dates and scope stay intact.
            name = re.sub(r'\s+(?:Limited|Ltd\.?)$', '', filing['name'], flags=re.I)
            alias = re.escape(name) + r"(?:\s+(?:Limited|Ltd)\.?)?(?:'s)?"
            question = re.sub(alias, company, question, flags=re.I)
        hits = search(self.table, self.model, question, max(DEFAULT_K, EXPANSION_SEEDS), company)
        label = f"{filing['name']} annual report, {filing['fiscal_year']}"
        verdict = guarded_answer(question, hits, self.client, page_context(self.table, hits), label)
        if verdict['refused'] or any(verdict.get(k) for k in ('invalid_citations', 'ungrounded', 'scrubbed')):
            return {'refused': True, 'text': REFUSAL, 'query': question}
        sentences = report_sentences(verdict['text'])
        if not sentences:
            return {'refused': True, 'text': REFUSAL, 'reason': 'Every sentence needs a citation'}
        # Keep accepted sentences together so the final selector cannot detach
        # a computed result from its cited input sentences.
        return {**self._record(' '.join(sentences), label, context=verdict['context'],
                              url=filing['source_url']), 'query': question}

    def _fund(self, field: str, count: int = 10) -> dict:
        fund = self.fund
        if fund is None:
            raise ValueError('No fund selected')
        snapshot = fund['portfolio_date'] if field == 'top_holdings' else fund['factsheet_date']
        if (not matches_snapshot(self.request, snapshot) or OUT_OF_SCOPE.search(self.request)
                or re.search(r'\b(?:regular|idcw)\b', self.request)):
            return {'refused': True, 'text': REFUSAL}
        if (field == 'expense_ratio' and fund[field]['kind'] == 'BER'
                and re.search(r'\b(?:total|ter)\b', self.request)):
            return {'refused': True, 'text': REFUSAL}
        if field == 'top_holdings':
            rows = sorted((r for r in fund['holdings'] if r['eligible']), key=lambda r: r['rank'])
            return {'evidence': [self._record(
                f"{r['name']}: {r['weight_display']} of net assets as of {fund['portfolio_date']} "
                f"{row_citation(fund, r)}.", fund['name']) for r in rows[:count]]}
        if field not in {'benchmark', 'expense_ratio', 'exit_load'}:
            raise ValueError('Unknown disclosure field')
        fact = fund[field]
        label = {'benchmark': 'Benchmark', 'expense_ratio': 'Direct-plan expense ratio',
                 'exit_load': 'Exit load'}[field]
        # Issuer definitions sometimes have several sentences. Join them into
        # one cited statement without dropping BER/TER qualifications.
        detail = ('; ' + fact['definition']) if field == 'expense_ratio' else ''
        value = re.sub(r'\.\s+', '; ', fact['value'] + detail).rstrip('.')
        return self._record(f"{label}: {value}; as of {fund['factsheet_date']} "
                            f"{fact_citation(fund, fact)}.", fund['name'])

    def call(self, name: str, arguments: dict) -> dict:
        import json
        if not isinstance(arguments, dict):
            raise ValueError('Tool input must be an object')
        cache_key = json.dumps([name, arguments], sort_keys=True)
        if cache_key in self._cache:
            return self._cache[cache_key]
        if name == 'company_question' and set(arguments) == {'company', 'question'}:
            if not isinstance(arguments['company'], str):
                raise ValueError('Company must be a code')
            result = self._company(**arguments)
        elif (name == 'fund_disclosure' and set(arguments) in ({'field'}, {'field', 'count'})
              and isinstance(arguments['field'], str)):
            count = arguments.get('count', 10)
            if type(count) is not int or not 1 <= count <= 10:
                raise ValueError('Holdings count must be between one and ten')
            if 'count' in arguments and arguments['field'] != 'top_holdings':
                raise ValueError('Only holdings have a count')
            result = self._fund(**arguments)
        else:
            raise ValueError('Unknown tool or invalid arguments')
        self._cache[cache_key] = result
        self.trace.append({'tool': name, 'input': arguments, 'result': result})
        return result


def render_evidence(entry: dict) -> str:
    """Resolve page markers against this evidence's own filing, never another's."""
    if not entry['url']:
        return entry['text']
    url = quote(entry['url'].split('#')[0], safe=':/?&=%')
    return CITATION.sub(lambda m: f"[page {m[1]}]({url}#page={m[1]})", entry['text'])
