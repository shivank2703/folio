
## Carried from Funds · 18 October 2026

No orchestration was built during Funds. A future plain tool-use loop can call
the verified disclosure lookups and the one-filing Q&A path, preserving their
source dates and scope. Do not silently broaden a fund's top-ten coverage.

Unresolved layout work remains separate: conservative interleaved-prose
exclusions reduce coverage, and ambiguous headings retain unstated/mixed scope.
Any future reader or finer scope tagging needs its own before/after evaluation.
No new geometry-based table heuristic or OCR path is proposed here.

Ten oversized whole rows still exceed the embedding tokenizer's input limit
(maximum 865 versus 512), although keyword search and cited context retain
their full text. Consider tokenizer-aware chunk sizing in a separately measured
change; do not cut a financial label away from its values or unit declaration.


- Funds live probe: BEL's total-assets question with “at March 31, 2026”
  retrieved page 98 but scored 0.663 and was refused; “at the end of FY26”
  passed. Build a broader paraphrase/date-format evaluation before revisiting
  query normalization or the similarity gate. Do not tune the threshold on
  this single example; Funds retains the existing 0.67 floor.

## Agent implementation · 25 October 2026

The user advanced to Agent with Funds' owner-session verification and profile
pinning still recorded as pending. Those gates have not been marked complete;
v1.3 remains untagged. Agent is a local candidate, with no deployment or release
tag claimed by this sitting.

### Scope and implementation

- `agent/run.py` is one plain Anthropic Messages loop over two read-only tools.
  No new framework, model, dependency, ingestion path or report coverage was added.
- `agent/tools.py` resolves a selected company or a selected fund's existing
  top-ten report coverage. Company tools reuse the unchanged report retrieval,
  context packing, generator and guardrails. Fund facts retain their reviewed
  values, BER/TER definitions, source dates and original page/row citations.
- Precise company requests reach retrieval unchanged. Generated subquestions
  replace a manifest legal name with its resolved company code, retaining dates
  and scope. Effective queries appear in the trace. The 0.67 floor is unchanged.
- A per-request evidence registry binds text to filing identity and context.
  Final model output is a structured selection of evidence IDs. The renderer
  resolves each filing's own page markers, groups source labels and preserves
  the cited evidence text. It cannot introduce synthesis prose or new links.
- Every accepted company sentence must carry its own citation. Uncited sentences
  are omitted; unknown citations, figure-grounding warnings or removed guidance
  withhold that report-tool result. This is stricter than ordinary company Q&A,
  whose existing warnings remain available in Companies mode.
- Limits: six turns, eight tool calls, twelve API calls, eight selected evidence
  entries, 200 words per report answer and 450 words including source labels per
  memo. Exact duplicate tool calls reuse evidence. One selection correction is
  allowed within these limits. A budget stop publishes no partial memo.
- `ui/memo.py` adds Company/Fund memo requests, an evidence trace and Markdown
  download. Session allowance is shared with Q&A. Every orchestration and nested
  generation call consumes a daily allowance; deterministic tools do not.
  Download reruns do not call the model. No memo or request is saved to disk by
  the app. Only public test results and UI captures are part of this change.

### Validation

- Fresh pre-change Q&A baseline: 54/54 answerable samples passed and 18/18 strict
  refusals (`agent-baseline.json`, 24 questions × three samples).
- Initial company-agent comparison: 50/72. Precise-question paraphrasing, overly
  strict citation placement and sentence splitting around abbreviations caused
  avoidable refusals. The intermediate company run improved to 68/72.
- The first routing run stopped after 10/12 cases because the new Navneet fixture
  used its exchange symbol instead of its manifest code. Its 22/30 completed
  samples are retained in `agent-routing-initial.json`; it is not a complete run.
- Subsequent complete routing runs scored 27/36, 32/36 and 34/36. Problems included
  JSON prose wrappers, selecting ten holdings when only one was asked for,
  corporate-header retrieval after legal-name expansion, and rejecting citations
  followed by a parenthetical qualifier. These files remain as measured.
- Final routing suite: **36/36 passed**, covering a complete fund memo, independent
  dates, unavailable plans/periods, wrong days, unavailable total TER, unknown
  holdings, per-fund coverage, fund-to-report routing, consolidated scope, lakh
  units and an absent report fact (`agent-routing-release.json`).
- Five wording probes × three samples scored 10/15 (`agent-phrasing.json`, before
  the final sentence-placement adjustment). The March-date BEL probe failed 0/3;
  the fiscal-year and consolidated variants were answerable. This supports the
  existing wording limitation; it does not justify relaxing the floor.
- Local regression tests: **34 passed**. Deterministic disclosure and coverage
  regression: **24/24**. Compile and whitespace checks passed.
- Browser checks on localhost: the default Kotak memo returned six cited facts in
  two model calls; its evidence trace retained source rows and the factsheet
  definition. An unavailable Regular-plan query returned exactly the strict
  refusal. Download state and daily-budget interruption were also exercised by
  Streamlit AppTest.
- Credential-format scan: 125 working files and 290 reachable history blobs,
  zero findings. No tracked source PDF/XLSX, `.env`, secrets file or real
  watchlist. AGPL-3.0 remains present; no prohibited dependency was introduced.

Final company-agent comparison (`agent-company-release.json`, the same 24
questions × three samples): **53/54 answerable passed, 54/54 correct, 53/54
faithful, 18/18 strict refusals** (71/72 overall). The baseline was 72/72.
The one retained failure is HCC retained earnings: both printed deficit balances
match, but the blind judge labelled “down from” as an unlabelled computation
even though the answer states no computed difference. The automated failure is
not manually overridden. Ordinary Companies Q&A was not modified.

The final suite used two to four API calls per precise question. General memos
can require more; the default HCC browser memo used five calls and returned
business, standalone assets and disclosed risks, each sentence linked to its
own source page. `docs/agent-company.png` preserves that view.

### Demo, write-up and release gates

`docs/agent-demo.mp4` is a 21-second walkthrough assembled from actual local UI
screenshots, showing the request, cited memo, evidence trace and strict refusal.
It is not a continuous recording or a live-deployment claim. The video decoded
successfully; `docs/agent-memo.png` preserves the memo view. The implementation
write-up, unpublished post skeleton and résumé draft are in
`docs/agent-writeup.md`. No social post was sent.

Before release: review the local change, deploy and exercise three live questions including a refusal, verify the
private owner session, verify profile pinning, then tag the release. The Funds
owner-session and pinning gates remain explicit user actions from the prior
sitting; no credential value was read for those checks.

Suggested commit: `Add bounded research agent and source-preserving cited memos`


General company-memo check (`agent-general-memo.json`): **2/3 passed**. All three
retained the correct cited total-assets figure. In the failed sample, the judge
listed ₹4.36 crore as an unlabelled computation, then explained that page 252
prints that impact amount and that no computation was performed. As in the
existing evaluator, the computed-figure list overrides the summary boolean;
this failure remains in the score. A general memo may omit a refused topic,
so this check does not establish completeness of every requested section.


### Status clarification · 25 October 2026

The prior chat “Set Funds deployment secrets” includes the user's “done,
proceed” confirmation, and its handoff explicitly records GITHUB_TOKEN and
FOLIO_OWNER_KEY as configured in Streamlit. Secret configuration is complete;
do not ask the user to repeat it or treat a missing verification record as
unfinished setup. The later Funds chat left the live owner-panel/exemption
check unrecorded. A fresh read-only GitHub query on 25 October returned no
pinned repositories, and the remote has no v1.3 tag. These are distinct status
items, not evidence that secrets were never configured. No secret value was
read in resolving this clarification.


### Push validation · 25 October 2026

The user explicitly requested testing and pushing the Agent implementation.
Fresh checks passed: 34 local tests, 24/24 deterministic fund checks, compile
and whitespace checks. Retrieval reproduced the recorded 17/18 expected pages
in the top five and 16/18 exact answer strings in context. The complete saved
before/after Agent evaluations remain unchanged; no prompt or retrieval code
changed during this push preparation. Git main matched origin/main before the
commit. Secrets configuration is complete and is not a prerequisite to repeat.
The separate profile-pinning/owner-verification records do not block this push.
Live deployment checks will be recorded after the commit reaches Streamlit.


### Live deployment verified · 25 October 2026

Implementation commit `c03265c` was pushed to main after the fresh checks above.
GitHub's main ref matched the local SHA. Streamlit was sleeping; waking it
loaded the new Memo mode in visitor mode, without the maintainer panel.

Three real live questions passed:

1. Company memo: “What were HCC standalone total assets at the end of FY25?”
   returned ₹8,743.37 crore, with the prior-year ₹8,138.03 crore comparison,
   both linked to viewer page 114; three model calls, 4.8 seconds. Clicking
   Download retained the result and the same call count.
2. Default Kotak fund memo: expense ratio with the full BER definition,
   benchmark and exit load linked to factsheet page 20; the three largest
   equities linked to KMI rows 5–7, retaining the September disclosure date;
   two model calls, 4.5 seconds.
3. “What is the Regular-plan expense ratio?” returned exactly
   “Not in the filing.”; two model calls, 2.4 seconds.

Local proof captures are in ignored data/agent-live-company.png,
data/agent-live-fund.png and data/agent-live-refusal.png. Fresh credential-format
scan covered 125 working files and 323 reachable history blobs with no findings.
AGPL-3.0 is present; no prohibited dependency, source document or private
portfolio file was staged. AGENTS.md and .agents/ remain untracked and untouched.
The requested test-and-push work is complete. No version tag was created.
