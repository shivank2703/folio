# Building Folio's cited memo

A multi-step financial answer can lose its provenance even when every individual
lookup was correct. Page 98 in one company's filing is a different source from
page 98 in another. A fund's September portfolio can legitimately sit beside
an August factsheet. A fluent summary can erase either distinction.

Folio's Agent step uses one plain Anthropic Messages loop. It can ask the existing
annual-report reader a precise company question, or read a verified fund field
and its largest domestic equity positions. The server resolves the selected
company and limits a fund's report access to its own top ten. There is no extra
framework, autonomous ingestion, external browsing or private portfolio input.
The request/response exchange follows Anthropic's
[tool-use lifecycle](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works).

Each successful tool result receives an evidence ID. The final model response
selects IDs; Python assembles the cited text and resolves each page against its
own filing URL. The agent cannot introduce new prose or replace a source link
while assembling the memo. Company evidence must pass the existing guardrails;
sentences without their own page citations are omitted. Fund statements retain
the original spreadsheet sheet/row or factsheet viewer page, the disclosure date
and the issuer's expense definition.

This trades free-form synthesis for evidence preservation. A result can be
incomplete when retrieval or generation refuses a subquestion, and the interface
says so. The 450-word budget includes source labels. Generated evidence is still
model-written: citation presence and figure checks do not prove every prose
claim, so the eval also uses a blind source-faithfulness judge.

The loop has six turns, eight tool calls and twelve API calls at most, with a
single correction opportunity for an invalid evidence selection. Repeated tool
calls reuse the same evidence. Every paid call, including nested company Q&A,
uses the existing daily limiter; a request that hits a budget stops without
publishing a partial memo. A download rerun does not regenerate evidence.

The evaluation retains early failures, including extra output around JSON,
over-selecting holdings, and false refusals after question paraphrasing. Precise
company questions now reach the report reader unchanged. Final measured results
and release gates are recorded in `notes/agent-step.md` and `evals/RESULTS.md`.

The companion demo is a short walkthrough assembled from actual local UI
screenshots, not a continuous recording and not a live deployment claim.

## Post draft — not published

I added a cited research memo to Folio, my workbench for Indian annual reports
and public mutual-fund disclosures. The hard part was keeping evidence intact
across several tool calls: company identity, statement scope, PDF pages,
spreadsheet rows and independent disclosure dates.

One small Python loop gathers the facts. The final model selects evidence IDs;
the renderer preserves the cited text and source links. Bounded calls, existing
rate limits and a before/after evaluation keep the behaviour inspectable.

Code: https://github.com/shivank2703/folio
Demo: https://folio-india.streamlit.app

Résumé draft: Built a bounded two-tool research agent over 32 annual reports
and 588 public fund rows, producing memos of up to 450 words with source-page
and spreadsheet-row citations.
