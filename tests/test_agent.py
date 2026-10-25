"""Exercise agent trust boundaries without spending API credit."""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agent.run import CallLimit, MeteredClient, MAX_API_CALLS, run_agent, select_memo
from agent.tools import ResearchTools, render_evidence, report_sentences
from funds.data import load_funds
from gen.guardrails import REFUSAL

FILINGS = json.load(open('corpus/corpus.json'))
FUNDS = {f['id']: f for f in load_funds()}


def block(kind, **kwargs):
    b = SimpleNamespace(type=kind, **kwargs)
    b.model_dump = lambda: {'type': kind, **kwargs}
    return b


def response(stop, *blocks):
    return SimpleNamespace(stop_reason=stop, content=list(blocks))


class AgentTests(unittest.TestCase):
    def tools(self, **kwargs):
        return ResearchTools(None, None, Mock(), FILINGS, **(kwargs or {'company': 'HCC'}))

    def test_fund_report_access_cannot_escape_top_ten(self):
        kotak = self.tools(fund=FUNDS['kotak-manufacture'])
        self.assertNotIn('BEL', kotak.filings)
        with self.assertRaises(ValueError):
            kotak.call('company_question', {'company': 'BEL', 'question': 'Total assets?'})
        self.assertIn('BEL', self.tools(fund=FUNDS['hdfc-defence']).filings)

    def test_unknown_tool_and_bad_arguments_do_not_execute(self):
        tools = self.tools()
        for name, args in [('shell', {}), ('company_question', {'company': 'HCC'}),
                           ('company_question', {'company': [], 'question': 'x'}),
                           ('fund_disclosure', {'field': 'benchmark'}), ('shell', [])]:
            with self.subTest(name=name, args=args), self.assertRaises(ValueError):
                tools.call(name, args)

    def test_disclosures_preserve_definition_dates_and_original_links(self):
        tools = self.tools(fund=FUNDS['motilal-nifty500'])
        expense = tools.call('fund_disclosure', {'field': 'expense_ratio'})
        for value in ('0.23%', 'Total TER', '0.13%', '2026-08-31', '#page=5'):
            self.assertIn(value, expense['text'])
        rows = tools.call('fund_disclosure', {'field': 'top_holdings'})['evidence']
        self.assertEqual(len(rows), 10)
        self.assertIn('2026-09-30', rows[0]['text'])
        self.assertIn('YO18 row 13', rows[0]['text'])
        largest = tools.call('fund_disclosure', {'field': 'top_holdings', 'count': 1})
        self.assertEqual(len(largest['evidence']), 1)
        for count in (0, 11, True, '1'):
            with self.assertRaises(ValueError):
                tools.call('fund_disclosure', {'field': 'top_holdings', 'count': count})

    def test_original_request_date_and_plan_cannot_be_silently_replaced(self):
        for request in ('September 2026 expense ratio?', 'Regular-plan expense ratio?',
                        'What is the expense ratio today?'):
            tools = self.tools(fund=FUNDS['motilal-nifty500'], request=request)
            self.assertEqual(tools.call('fund_disclosure', {'field': 'expense_ratio'})['text'], REFUSAL)
        tools = self.tools(fund=FUNDS['hdfc-defence'], request='What is the total TER?')
        self.assertTrue(tools.call('fund_disclosure', {'field': 'expense_ratio'})['refused'])

    def test_duplicate_calls_reuse_evidence(self):
        tools = self.tools(fund=FUNDS['hdfc-defence'])
        first = tools.call('fund_disclosure', {'field': 'benchmark'})
        self.assertEqual(first, tools.call('fund_disclosure', {'field': 'benchmark'}))
        self.assertEqual(len(tools.evidence), 1)

    def test_every_sentence_requires_its_own_citation(self):
        self.assertEqual(report_sentences('Uncited fact. Another fact [page 2].'), ['Another fact [page 2].'])
        self.assertEqual(report_sentences('Uncited fact. another fact [page 2].'), ['another fact [page 2].'])
        self.assertEqual(report_sentences('A fact [page 2]. Uncited tail.'), ['A fact [page 2].'])
        self.assertEqual(report_sentences('A fact [page 2].\n\nAnother [page 3].'),
                         ['A fact [page 2].', 'Another [page 3].'])
        self.assertEqual(report_sentences('Assets 8,743.37 crore. [page 114]'),
                         ['Assets 8,743.37 crore [page 114].'])
        self.assertEqual(report_sentences('Assets Rs. 11,146.51 crore [page 98] (standalone).'),
                         ['Assets Rs. 11,146.51 crore [page 98] (standalone).'])

    def test_citation_belongs_to_its_filing(self):
        entry = {'text': 'A fact [page 98].', 'url': 'https://example.com/BEL.pdf'}
        self.assertIn('BEL.pdf#page=98', render_evidence(entry))
        entry['url'] = 'https://example.com/HCC.pdf'
        self.assertNotIn('BEL.pdf', render_evidence(entry))

    def test_generated_prose_or_unknown_ids_cannot_reach_memo(self):
        tools = self.tools(fund=FUNDS['hdfc-defence'])
        known = tools.call('fund_disclosure', {'field': 'benchmark'})['id']
        for raw in ('Invented claim [page 1].', '{"evidence_ids": ["E999"]}',
                    '{"evidence_ids": [], "text": "Invented"}',
                    json.dumps({'evidence_ids': [known, known]}),
                    '{"evidence_ids": [{}]}', '[]'):
            self.assertTrue(select_memo(raw, tools)['refused'])
        good = select_memo(json.dumps({'evidence_ids': [known]}), tools)
        self.assertFalse(good['refused'])
        self.assertIn(tools.evidence[known]['text'], good['text'])

    @patch('agent.tools.page_context', return_value=[])
    @patch('agent.tools.search', return_value=[])
    @patch('agent.tools.guarded_answer')
    def test_report_warnings_or_uncited_sentences_are_withheld(self, answer, search, context):
        good = {'text': 'Assets 8,743.37 crore [page 114].', 'refused': False,
                'context': [], 'invalid_citations': [], 'ungrounded': [], 'scrubbed': []}
        for changes in ({'ungrounded': ['999']}, {'invalid_citations': [99]},
                        {'scrubbed': ['removed']}, {'text': 'Only an uncited answer.'}):
            answer.return_value = {**good, **changes}
            out = self.tools().call('company_question', {'company': 'HCC', 'question': 'Assets?'})
            self.assertTrue(out['refused'])
        answer.return_value = good
        tools = self.tools()
        tools.call('company_question', {'company': 'HCC', 'question': 'Assets?'})
        self.assertEqual(len(tools.evidence), 1)

    @patch('agent.tools.page_context', return_value=[])
    @patch('agent.tools.guarded_answer', return_value={'refused': True})
    @patch('agent.tools.search', return_value=[])
    def test_query_identity_changes_preserve_dates_scope_and_precise_requests(self, search, answer, context):
        question = 'What were BEL consolidated total assets at March 31, 2026?'
        tools = self.tools(company='BEL', request=question)
        tools.call('company_question', {'company': 'BEL', 'question': 'A planner paraphrase'})
        self.assertEqual(search.call_args.args[2], question)
        tools = self.tools(fund=FUNDS['hdfc-defence'])
        tools.call('company_question', {'company': 'BEL', 'question':
                   "What were Bharat Electronics Ltd.'s consolidated total assets at March 31, 2026?"})
        self.assertEqual(search.call_args.args[2], question)

    def test_meter_covers_nested_calls_and_stops_before_spend(self):
        raw, hook = Mock(), Mock()
        client = MeteredClient(raw, hook)
        for _ in range(MAX_API_CALLS):
            client.messages.create()
        with self.assertRaises(CallLimit):
            client.messages.create()
        self.assertEqual(raw.messages.create.call_count, MAX_API_CALLS)
        self.assertEqual(hook.call_count, MAX_API_CALLS)
        hook.side_effect = CallLimit('Daily limit')
        with self.assertRaises(CallLimit):
            MeteredClient(raw, hook).messages.create()
        self.assertEqual(raw.messages.create.call_count, MAX_API_CALLS)

    def test_plain_loop_pairs_tool_ids_and_does_not_publish_intermediate_text(self):
        client = Mock()
        client.messages.create.side_effect = [
            response('tool_use', block('text', text='Uncited intermediate text'),
                     block('tool_use', id='call-1', name='fund_disclosure', input={'field': 'benchmark'})),
            response('end_turn', block('text', text='{"evidence_ids": ["E1"]}'))]
        result = run_agent('Benchmark?', None, None, client, FILINGS, fund=FUNDS['hdfc-defence'])
        self.assertFalse(result['refused'])
        self.assertNotIn('intermediate', result['text'])
        messages = client.messages.create.call_args.kwargs['messages']
        self.assertEqual(messages[-1]['content'][0]['tool_use_id'], 'call-1')
        self.assertEqual(result['api_calls'], 2)

    def test_tool_error_is_reported_in_protocol_and_truncation_is_withheld(self):
        client = Mock()
        client.messages.create.side_effect = [
            response('tool_use', block('tool_use', id='bad', name='shell', input={})),
            response('max_tokens', block('text', text='A partial uncited answer'))]
        result = run_agent('Memo', None, None, client, FILINGS, company='HCC')
        self.assertTrue(result['refused'])
        messages = client.messages.create.call_args.kwargs['messages']
        self.assertTrue(messages[-1]['content'][0]['is_error'])

    def test_excessive_tool_batch_stops_before_execution(self):
        client = Mock()
        client.messages.create.return_value = response('tool_use', *[
            block('tool_use', id=str(i), name='fund_disclosure', input={'field': 'benchmark'})
            for i in range(9)])
        with self.assertRaises(CallLimit):
            run_agent('Memo', None, None, client, FILINGS, fund=FUNDS['hdfc-defence'])
