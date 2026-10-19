"""Verify Streamlit preserves the complete table and the per-fund drill boundary."""
import unittest
from streamlit.testing.v1 import AppTest


class FundsReaderTests(unittest.TestCase):
    def test_table_and_drill_down_follow_selected_fund(self):
        app = AppTest.from_string('''
import streamlit as st
from ui.funds import render
filing = render([{'company':'BEL'}, {'company':'SUNPHARMA'}])
if filing:
    st.write('Selected filing: ' + filing['company'])
''').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value),62)
        kotak = app.dataframe[0].value
        bel = kotak[kotak['Instrument'].str.contains('Bharat Electronics')].iloc[0]
        self.assertEqual(bel['Coverage'],'Not indexed')
        self.assertNotIn(bel['Instrument'],app.selectbox[1].options)
        app.selectbox[0].select('HDFC Defence Fund').run()
        self.assertEqual(len(app.dataframe[0].value),26)
        hdfc = app.dataframe[0].value
        self.assertEqual(hdfc.iloc[0]['Coverage'],'Indexed')
        app.selectbox[1].select('Bharat Electronics Ltd.').run()
        self.assertIn('Selected filing: BEL',[x.value for x in app.markdown])
        app.selectbox[0].select('Motilal Oswal Nifty 500 Index Fund').run()
        self.assertEqual(len(app.dataframe[0].value),500)
        self.assertFalse(app.exception)
