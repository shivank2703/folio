"""A memo is an independent bounded request, with source evidence beside it."""

from __future__ import annotations

import time

import anthropic
import streamlit as st

from agent.run import CallLimit, run_agent
from funds.data import load_funds


class DailyBudgetReached(RuntimeError):
    """Stop before the next paid call when the shared daily budget is exhausted."""


def render(filings: list[dict], table, model, client, client_error: str, *, owner: bool,
           limiter, address: str | None, max_questions: int) -> None:
    kind = st.radio('Memo subject', ['Company', 'Fund'], horizontal=True)
    company, fund = None, None
    if kind == 'Company':
        by_name = {f"{f['name']} — {f['fiscal_year']}": f for f in filings}
        selected = by_name[st.selectbox('Company filing', list(by_name))]
        company = selected['company']
        subject = company
        default = (f"Prepare a short factual memo on the business, standalone total assets at the end of "
                   f"{selected['fiscal_year']}, and risks disclosed in this annual report.")
    else:
        by_name = {f['name']: f for f in load_funds()}
        fund = by_name[st.selectbox('Fund snapshot', list(by_name))]
        subject = fund['id']
        st.caption(f"Portfolio: {fund['portfolio_date']} · Factsheet: {fund['factsheet_date']}")
        default = ('Prepare a short factual memo on the Direct-plan expense ratio, benchmark, '
                   'exit load and three largest domestic equity holdings in the disclosed snapshot.')
    st.caption('Up to 450 words of cited evidence. Some requested information may be unavailable. '
               'Each model call uses one daily allowance; a memo can use up to 12 calls.')
    with st.form('memo-request'):
        request = st.text_area('Memo request', value=default, max_chars=2000)
        submitted = st.form_submit_button('Create cited memo', type='primary')
    if submitted and request.strip():
        st.session_state.pop('memo_result', None)
        asked = st.session_state.get('asked', 0)
        if not owner and asked >= max_questions:
            st.info(f'This visit has reached the {max_questions}-request limit.')
            return
        if client is None:
            st.error(client_error)
            return
        st.session_state['asked'] = asked + 1

        def before_call() -> None:
            if not owner and limiter.take(limiter.visitor(address)):
                raise DailyBudgetReached('The daily model-call allowance is exhausted. '
                                         'It resets at midnight UTC.')

        started = time.perf_counter()
        try:
            with st.spinner('Gathering cited evidence...'):
                result = run_agent(request, table, model,
                                   client.with_options(timeout=60, max_retries=0), filings,
                                   company=company, fund=fund, before_call=before_call)
        except (CallLimit, DailyBudgetReached) as stopped:
            st.info(str(stopped))
            return
        except anthropic.APIError:
            st.error('The answer service is unavailable. The memo was not completed.')
            return
        result.update(elapsed=time.perf_counter() - started, request=request)
        st.session_state['memo_result'] = (subject, result)
    stored = st.session_state.get('memo_result')
    if not stored or stored[0] != subject:
        return
    result = stored[1]
    if result['refused']:
        st.warning(result['text'])
    else:
        st.subheader('Cited research memo')
        st.markdown(result['text'])
        st.download_button('Download memo', '# Folio — cited research memo\n\n' + result['text'] + '\n',
                           file_name='folio-memo.md', mime='text/markdown')
    st.caption(f"{result['api_calls']} model calls · {result['elapsed']:.1f} s")
    with st.expander('Evidence gathered'):
        for step in result['trace']:
            st.write(step['tool'], step['input'])
            st.json(step['result'])
        for entry in result['evidence']:
            for chunk in sorted(entry['context'], key=lambda c: (c['page'], c['chunk'])):
                st.caption(f"{entry['source']} · page {chunk['page']} · {chunk.get('scope', 'unstated')}")
                st.text(chunk['text'])
