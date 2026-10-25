"""Check memo submission, download reruns and daily-budget stops in the UI."""

import unittest
from streamlit.testing.v1 import AppTest

APP = '''
import json
from pathlib import Path
from unittest.mock import Mock
import streamlit as st
import ui.memo as memo
from ui.limits import DailyLimiter

def fake(request, table, model, client, filings, **kwargs):
    st.session_state['runs'] = st.session_state.get('runs', 0) + 1
    kwargs['before_call']()
    kwargs['before_call']()
    return {'text': 'Cited fact [page 114](https://example.com/report.pdf#page=114).',
            'refused': False, 'api_calls': 2, 'trace': [], 'evidence': []}
memo.run_agent = fake
if 'limiter' not in st.session_state:
    st.session_state['limiter'] = DailyLimiter(per_visitor=ALLOWANCE, total=20)
memo.render(json.loads(Path('corpus/corpus.json').read_text()), None, None, Mock(), '',
            owner=False, limiter=st.session_state['limiter'], address='example', max_questions=10)
'''


class MemoUITests(unittest.TestCase):
    def test_memo_download_survives_rerun_and_switch_hides_old_result(self):
        app = AppTest.from_string(APP.replace('ALLOWANCE', '10')).run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn('Cited fact', '\n'.join(m.value for m in app.markdown))
        self.assertEqual(app.session_state['runs'], 1)
        app.run()
        self.assertEqual(app.session_state['runs'], 1)
        app.radio[0].set_value('Fund').run()
        self.assertNotIn('Cited fact', '\n'.join(m.value for m in app.markdown))

    def test_mid_memo_daily_limit_publishes_no_partial_result(self):
        app = AppTest.from_string(APP.replace('ALLOWANCE', '1')).run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn('daily model-call allowance', app.info[0].value)
        self.assertNotIn('Cited fact', '\n'.join(m.value for m in app.markdown))
