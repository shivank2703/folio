# Eval results

`python -m evals.score --label <name>` runs every question in
`notes/eval-candidates.jsonl` through the app's own answer path three times and
grades each answer. A question passes a sample when:

- answerable: not refused, judged **correct** against the recorded answer (a
  Haiku call that never sees the pages), judged **faithful** to the pages it
  cites (a second Haiku call that never sees the reference; unlabelled computed
  figures fail), and no citation to a page the model was not shown;
- not in the filing: the reply is exactly "Not in the filing." Anything after
  it fails, caught or not.

Each run below is the full set, so rows are comparable across runs. The
fit/test split is for the reranker threshold (step 4): fitted on `fit`,
reported on `test`.

### baseline (2026-10-04 12:07, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal |
|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 0/3 | 3/3 | 0/3 | – |
| hcc-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – |
| hcc-fy25-003 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – |
| chambal-fy25-002 | numeric-lookup | test | 1/3 | 3/3 | 1/3 | – |
| navneet-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – |
| navneet-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 1/3 | – | – | 2 |
| hcc-fy25-006 | table | fit | 0/3 | 0/3 | 0/3 | 1 |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – |
| hcc-fy25-008 | table | fit | 3/3 | 3/3 | 3/3 | – |
| hcc-fy25-009 | two-column | test | 3/3 | 3/3 | 3/3 | – |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – |
| chambal-fy25-004 | computed | fit | 0/3 | 3/3 | 0/3 | – |
| chambal-fy25-005 | multi-hop | test | 3/3 | 3/3 | 3/3 | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – |

- Answerable passed: 34/45 (76%) · correct 42/45 (93%) · faithful 34/45 (76%)
- Not-in-filing refused bare: 13/15 (87%) · refusal leaks (any question): 3
- By type: computed 0/3 (0%), multi-hop 3/3 (100%), not-in-filing 13/15 (87%), numeric-lookup 19/24 (79%), table 6/9 (67%), two-column 3/3 (100%), units-trap 3/3 (100%)
- By split: fit 22/33 (67%), test 25/27 (93%)


### rules (2026-10-04 12:13, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure |
|---|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – |
| hcc-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – |
| hcc-fy25-003 | numeric-lookup | fit | 2/3 | 2/3 | 3/3 | – | – |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – |
| chambal-fy25-002 | numeric-lookup | test | 0/3 | 3/3 | 0/3 | – | 3 |
| navneet-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – |
| navneet-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 3/3 | – | – | – | – |
| hcc-fy25-006 | table | fit | 0/3 | 1/3 | 1/3 | 1 | 2 |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – | – |
| hcc-fy25-008 | table | fit | 3/3 | 3/3 | 3/3 | – | – |
| hcc-fy25-009 | two-column | test | 2/3 | 3/3 | 2/3 | – | 1 |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – | – |
| chambal-fy25-004 | computed | fit | 2/3 | 3/3 | 2/3 | – | – |
| chambal-fy25-005 | multi-hop | test | 3/3 | 3/3 | 3/3 | – | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – |

- Answerable passed: 36/45 (80%) · correct 42/45 (93%) · faithful 38/45 (84%)
- Not-in-filing refused bare: 15/15 (100%) · refusal leaks (any question): 1
- By type: computed 2/3 (67%), multi-hop 3/3 (100%), not-in-filing 15/15 (100%), numeric-lookup 20/24 (83%), table 6/9 (67%), two-column 2/3 (67%), units-trap 3/3 (100%)
- By split: fit 28/33 (85%), test 23/27 (85%)

What changed: computed figures must carry "(computed from [page N])"; text
after "Not in the filing." is stripped (the eval still grades the model's raw
reply); every figure in a cited claim must be printed on the page it cites.

Read against the baseline: refusals 13/15 to 15/15, unlabelled differences
fixed (hcc-001 0/3 to 3/3, chambal-004 0/3 to 2/3). chambal-002 still cites
page 4 for a page-5 figure; the grounding check now catches and flags it every
time instead of letting it through. Judge misgrade noted: one chambal-004
sample wrote the decrease as "(146.98)" and the judge called the arithmetic
wrong; parentheses are a negative and the sum is right. The judge stays frozen
for the whole step so runs stay comparable. hcc-003's one miss is the known
scope gap (consolidated p220 used for a standalone question).

### tables (2026-10-04 12:48, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-003 | numeric-lookup | fit | 0/3 | 0/3 | 0/3 | – | – | – |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-002 | numeric-lookup | test | 0/3 | 3/3 | 0/3 | – | 3 | – |
| navneet-fy25-001 | numeric-lookup | fit | 2/3 | 2/3 | 2/3 | – | – | – |
| navneet-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| hcc-fy25-006 | table | fit | 0/3 | 0/3 | 0/3 | – | – | – |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-008 | table | fit | 2/3 | 3/3 | 3/3 | – | 1 | – |
| hcc-fy25-009 | two-column | test | 2/3 | 3/3 | 2/3 | – | – | – |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – | – | – |
| chambal-fy25-004 | computed | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-005 | multi-hop | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |

- Answerable passed: 33/45 (73%) · correct 38/45 (84%) · faithful 34/45 (76%)
- Not-in-filing refused bare: 15/15 (100%) · refusal leaks (any question): 0
- By type: computed 3/3 (100%), multi-hop 3/3 (100%), not-in-filing 15/15 (100%), numeric-lookup 17/24 (71%), table 5/9 (56%), two-column 2/3 (67%), units-trap 3/3 (100%)
- By split: fit 25/33 (76%), test 23/27 (85%)

What changed: pymupdf4llm 0.3.4 re-reads ruled tables (202 of 872 kept pages
accepted by the four gates in ingest/tables.py); all three filings re-indexed.
Retrieval improved (smoke: expected page in top 5 11/15 -> 13/15, answer text
in context 12/15 -> 13/15) but answers fell 36 -> 33. Cause, read from the raw
replies: the model cited [page 6] for a p138 figure (from "Note 6 Trade
receivables"), [page 2] for a p190 figure, [page 4] for p5. Never-retrieved
pages get the answer withheld, so right figures surfaced as refusals.

### tables+recite (2026-10-04 12:54, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | 1 |
| hcc-fy25-003 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | 2 |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | 3 |
| navneet-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | 3 |
| navneet-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| hcc-fy25-006 | table | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-008 | table | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-009 | two-column | test | 1/3 | 3/3 | 1/3 | – | – | – |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – | – | – |
| chambal-fy25-004 | computed | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-005 | multi-hop | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |

- Answerable passed: 43/45 (96%) · correct 45/45 (100%) · faithful 43/45 (96%)
- Not-in-filing refused bare: 15/15 (100%) · refusal leaks (any question): 0
- By type: computed 3/3 (100%), multi-hop 3/3 (100%), not-in-filing 15/15 (100%), numeric-lookup 24/24 (100%), table 9/9 (100%), two-column 1/3 (33%), units-trap 3/3 (100%)
- By split: fit 33/33 (100%), test 25/27 (93%)

What changed: when a claim's cited page does not print its figures and exactly
one page in the context prints all of them, the guard cites that page and says
so (gen/guardrails.py `recite`). 9 corrections in 60 samples, every one to the
expected page. The small wrong pages were the extract index: the prompt
labelled extracts "[2] page 190", and [2] looks like a citation.

### labels (2026-10-04 13:00, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-003 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| hcc-fy25-006 | table | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-008 | table | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-009 | two-column | test | 2/3 | 3/3 | 2/3 | – | – | – |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – | – | – |
| chambal-fy25-004 | computed | fit | 2/3 | 3/3 | 3/3 | – | 1 | – |
| chambal-fy25-005 | multi-hop | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |

- Answerable passed: 43/45 (96%) · correct 45/45 (100%) · faithful 44/45 (98%)
- Not-in-filing refused bare: 15/15 (100%) · refusal leaks (any question): 0
- By type: computed 2/3 (67%), multi-hop 3/3 (100%), not-in-filing 15/15 (100%), numeric-lookup 24/24 (100%), table 9/9 (100%), two-column 2/3 (67%), units-trap 3/3 (100%)
- By split: fit 32/33 (97%), test 26/27 (96%)

What changed: extracts are labelled "--- extract from page 190 (chunk 3) ---",
with no running number. Corrections needed fell from 9 to 0 at the same pass
rate: the model now cites the right page itself, and re-citation stays as a
net. Two judge disagreements, both read by hand: hcc-009's "5.8 km" is printed
on p22 (the judge called it computed), and one chambal-004 sample states the
decrease unlabelled before labelling it, which the guard flags and the judge
let through. The guard is right by the rule; the judge is frozen.

### rerank-jina (2026-10-04 13:46, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-002 | numeric-lookup | test | 0/3 | 0/3 | 0/3 | – | – | – |
| hcc-fy25-003 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-002 | numeric-lookup | test | 0/3 | 0/3 | 0/3 | – | – | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| hcc-fy25-006 | table | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-008 | table | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-009 | two-column | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – | – | – |
| chambal-fy25-004 | computed | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-005 | multi-hop | test | 1/3 | 1/3 | 3/3 | – | – | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |

- Answerable passed: 37/45 (82%) · correct 37/45 (82%) · faithful 39/45 (87%)
- Not-in-filing refused bare: 15/15 (100%) · refusal leaks (any question): 0
- By type: computed 3/3 (100%), multi-hop 1/3 (33%), not-in-filing 15/15 (100%), numeric-lookup 18/24 (75%), table 9/9 (100%), two-column 3/3 (100%), units-trap 3/3 (100%)
- By split: fit 33/33 (100%), test 19/27 (70%)

What changed (experiment, not shipped): the 20 best hybrid candidates are
reordered by jina-reranker-v1-tiny-en and the best score gates refusal, at the
threshold fitted on the fit half only (1.613; `python -m evals.fit_gate`).

Rejected. The fit half passes 33/33; the held-out test half falls from 26/27
to 19/27. The gate refuses two answerable questions (hcc-002 at 1.337,
navneet-002 at 1.392, both under a threshold the fit half put at 1.613), and
reordering drops the second page of the multi-hop question (chambal-005 3/3 to
1/3). It refuses nothing the prompt contract and strict guard were not already
refusing (15/15 either way). ms-marco-MiniLM-L-6 did worse on the gate alone
(test: 4/7 answerable let through vs jina's 5/7). Both rerankers are trained on
web search pairs and read financial tables poorly; with five negatives, a
threshold fitted on three of them cannot be trusted anyway. The 0.67 floor
stays as a cheap pre-filter: across every run it refused no answerable
question.

## Final: baseline -> shipped

| | Baseline | Shipped (labels) |
|---|---|---|
| Answerable passed | 34/45 (76%) | 43/45 (96%) |
| Correct | 42/45 (93%) | 45/45 (100%) |
| Faithful to cited pages | 34/45 (76%) | 44/45 (98%) |
| Not-in-filing, bare refusal | 13/15 (87%) | 15/15 (100%) |
| Refusal leaks (raw replies) | 3 | 0 |
| Test half only | 25/27 | 26/27 |
| Citations the guard had to correct | (no guard) | 0 |

### unihealth-1 (2026-10-04 22:46, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| unihealth-fy26-001 | numeric-lookup | test | 1/3 | 1/3 | 1/3 | 1 | – | – |
| unihealth-fy26-002 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-003 | table | test | 0/3 | 0/3 | 0/3 | – | – | – |
| unihealth-fy26-004 | not-in-filing | test | 3/3 | – | – | – | – | – |

- Answerable passed: 4/9 (44%) · correct 4/9 (44%) · faithful 4/9 (44%)
- Not-in-filing refused bare: 3/3 (100%) · refusal leaks (any question): 1
- By type: not-in-filing 3/3 (100%), numeric-lookup 4/6 (67%), table 0/3 (0%)
- By split: fit 3/3 (100%), test 4/9 (44%)

Ingest step. Four Unihealth Hospitals FY26 questions added (2 lookups, a table,
a not-in-filing); only these were iterated on, to keep spend low. First run:
the model refused its own company's consolidated figures as "the group's, not
Unihealth's", and the segment table on a two-page spread (p118) was unreadable.

### unihealth-2-spreads (2026-10-04 22:51, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| unihealth-fy26-001 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-002 | numeric-lookup | fit | 2/3 | 3/3 | 2/3 | – | – | – |
| unihealth-fy26-003 | table | test | 0/3 | 0/3 | 0/3 | 2 | – | – |
| unihealth-fy26-004 | not-in-filing | test | 3/3 | – | – | – | – | – |

- Answerable passed: 5/9 (56%) · correct 6/9 (67%) · faithful 5/9 (56%)
- Not-in-filing refused bare: 3/3 (100%) · refusal leaks (any question): 2
- By type: not-in-filing 3/3 (100%), numeric-lookup 5/6 (83%), table 0/3 (0%)
- By split: fit 2/3 (67%), test 6/9 (67%)

What changed: two-page spreads are read as two halves (ingest/preprocess.py
`split_spread`); Unihealth re-indexed. The segment row became readable; the
model now found it and still refused it as not "Unihealth's".

### unihealth-3-filing (2026-10-04 22:52, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| unihealth-fy26-001 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-002 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-003 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-004 | not-in-filing | test | 3/3 | – | – | – | – | – |

- Answerable passed: 9/9 (100%) · correct 9/9 (100%) · faithful 9/9 (100%)
- Not-in-filing refused bare: 3/3 (100%) · refusal leaks (any question): 0
- By type: not-in-filing 3/3 (100%), numeric-lookup 6/6 (100%), table 3/3 (100%)
- By split: fit 3/3 (100%), test 9/9 (100%)

What changed: the prompt opens with the filing's name ("Filing: Unihealth
Hospitals annual report, FY26") and says a short company name in a question
means that filing's company.

### ingest (2026-10-11 00:20, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-003 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| hcc-fy25-006 | table | fit | 0/3 | 0/3 | 1/3 | – | 1 | – |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-008 | table | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-009 | two-column | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – | – | – |
| chambal-fy25-004 | computed | fit | 2/3 | 3/3 | 3/3 | – | 1 | – |
| chambal-fy25-005 | multi-hop | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| unihealth-fy26-001 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-002 | numeric-lookup | fit | 2/3 | 3/3 | 2/3 | – | – | – |
| unihealth-fy26-003 | table | test | 2/3 | 2/3 | 2/3 | 1 | – | – |
| unihealth-fy26-004 | not-in-filing | test | 3/3 | – | – | – | – | – |

- Answerable passed: 48/54 (89%) · correct 50/54 (93%) · faithful 50/54 (93%)
- Not-in-filing refused bare: 18/18 (100%) · refusal leaks (any question): 1
- By type: computed 2/3 (67%), multi-hop 3/3 (100%), not-in-filing 18/18 (100%), numeric-lookup 29/30 (97%), table 8/12 (67%), two-column 3/3 (100%), units-trap 3/3 (100%)
- By split: fit 31/36 (86%), test 35/36 (97%)

The one full run of the step: every filing re-indexed (the table-page header
fix touches all of them), the filing name in the prompt, 24 questions.

Against v1.1 on the same 20 questions: answerable 43/45 -> 42/45, refusals
15/15 -> 15/15. The loss is hcc-006 (SOCIE, 3/3 -> 0/3), read from the
context, not guessed: p118 still ranks among the seeds and six of its seven
chunks reach the model, but the 6,000-token budget fills before chunk 4, the
one printing (1,965.62). Carrying year headers into every chunk of a table
page made HCC's table pages longer, so the budget runs out sooner. Not tuned
here: changing the budget for one question would be fitting the eval. Logged
in notes/funds-step.md. Unihealth in this run: 7/9 answerable (9/9 in its own
run), 3/3 refusals.

## Ingest step: v1.1 -> v1.2

| | v1.1 (20 questions) | v1.2, same 20 | v1.2, all 24 |
|---|---|---|---|
| Answerable passed | 43/45 | 42/45 | 48/54 (89%) |
| Correct | 45/45 | 42/45 | 50/54 |
| Faithful to cited pages | 44/45 | 43/45 | 50/54 |
| Not in the filing, bare | 15/15 | 15/15 | 18/18 |

### haiku-5-5 (2026-10-11 00:30, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-003 | numeric-lookup | fit | 0/3 | 0/3 | 2/3 | – | – | – |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| hcc-fy25-006 | table | fit | 0/3 | 3/3 | 2/3 | – | 2 | – |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-008 | table | fit | 0/3 | 0/3 | 3/3 | – | – | – |
| hcc-fy25-009 | two-column | test | 0/3 | 0/3 | 0/3 | – | – | – |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – | – | – |
| chambal-fy25-004 | computed | fit | 1/3 | 3/3 | 1/3 | – | 1 | – |
| chambal-fy25-005 | multi-hop | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| unihealth-fy26-001 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-002 | numeric-lookup | fit | 0/3 | 3/3 | 0/3 | – | – | – |
| unihealth-fy26-003 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-004 | not-in-filing | test | 3/3 | – | – | – | – | – |

- Answerable passed: 37/54 (69%) · correct 45/54 (83%) · faithful 44/54 (81%)
- Not-in-filing refused bare: 18/18 (100%) · refusal leaks (any question): 0
- By type: computed 1/3 (33%), multi-hop 3/3 (100%), not-in-filing 18/18 (100%), numeric-lookup 24/30 (80%), table 6/12 (50%), two-column 0/3 (0%), units-trap 3/3 (100%)
- By split: fit 22/36 (61%), test 33/36 (92%)

Generation moved to Claude Haiku 5.5 (effort low); the judge stays on Haiku
4.5, so this is a model change measured with the same ruler. 48/54 -> 37/54.
Read by hand, mostly literalism: it would not call a figure consolidated when
the page does not say so (the prompt's own rule, which Haiku 4.5 bent), so it
refused or hedged hcc-003 and hcc-008; it added other sections' figures to
hcc-009; and it stated a computed figure before labelling it.

### haiku-5-5-medium (2026-10-11 00:41, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-003 | numeric-lookup | fit | 0/3 | 0/3 | 2/3 | – | – | – |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| hcc-fy25-006 | table | fit | 0/3 | 1/3 | 0/3 | – | 1 | – |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-008 | table | fit | 1/3 | 1/3 | 3/3 | – | – | – |
| hcc-fy25-009 | two-column | test | 1/3 | 3/3 | 1/3 | – | – | – |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – | – | – |
| chambal-fy25-004 | computed | fit | 0/3 | 3/3 | 3/3 | – | 3 | – |
| chambal-fy25-005 | multi-hop | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| unihealth-fy26-001 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-002 | numeric-lookup | fit | 2/3 | 2/3 | 2/3 | – | – | – |
| unihealth-fy26-003 | table | test | 2/3 | 2/3 | 3/3 | – | – | – |
| unihealth-fy26-004 | not-in-filing | test | 3/3 | – | – | – | – | – |

- Answerable passed: 39/54 (72%) · correct 45/54 (83%) · faithful 47/54 (87%)
- Not-in-filing refused bare: 18/18 (100%) · refusal leaks (any question): 0
- By type: computed 0/3 (0%), multi-hop 3/3 (100%), not-in-filing 18/18 (100%), numeric-lookup 26/30 (87%), table 6/12 (50%), two-column 1/3 (33%), units-trap 3/3 (100%)
- By split: fit 24/36 (67%), test 33/36 (92%)

Effort medium, nothing else changed: 39/54. Effort was not the problem.

### haiku-5-5-prompt (2026-10-11 00:50, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-003 | numeric-lookup | fit | 1/3 | 1/3 | 3/3 | – | – | – |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| hcc-fy25-006 | table | fit | 2/3 | 2/3 | 2/3 | – | – | – |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-008 | table | fit | 0/3 | 0/3 | 3/3 | – | – | – |
| hcc-fy25-009 | two-column | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – | – | – |
| chambal-fy25-004 | computed | fit | 1/3 | 3/3 | 3/3 | – | 2 | – |
| chambal-fy25-005 | multi-hop | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| unihealth-fy26-001 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-002 | numeric-lookup | fit | 2/3 | 2/3 | 3/3 | – | – | – |
| unihealth-fy26-003 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-004 | not-in-filing | test | 3/3 | – | – | – | – | – |

- Answerable passed: 45/54 (83%) · correct 47/54 (87%) · faithful 53/54 (98%)
- Not-in-filing refused bare: 18/18 (100%) · refusal leaks (any question): 0
- By type: computed 1/3 (33%), multi-hop 3/3 (100%), not-in-filing 18/18 (100%), numeric-lookup 27/30 (90%), table 8/12 (67%), two-column 3/3 (100%), units-trap 3/3 (100%)
- By split: fit 27/36 (75%), test 36/36 (100%)

Three prompt rules: when the page does not state standalone or consolidated,
give the figure and say so instead of refusing; state a computed figure once,
where it is labelled; answer only what was asked. 45/54, faithful 53/54.

### haiku-5-5-final (2026-10-11 00:58, 3 samples per question)

| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |
|---|---|---|---|---|---|---|---|---|
| hcc-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-003 | numeric-lookup | fit | 2/3 | 2/3 | 3/3 | – | – | – |
| hcc-fy25-004 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| chambal-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-001 | numeric-lookup | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-002 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| chambal-fy25-003 | not-in-filing | test | 3/3 | – | – | – | – | – |
| navneet-fy25-003 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| hcc-fy25-006 | table | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-007 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-008 | table | fit | 1/3 | 1/3 | 3/3 | – | – | – |
| hcc-fy25-009 | two-column | test | 3/3 | 3/3 | 3/3 | – | – | – |
| hcc-fy25-010 | not-in-filing | test | 3/3 | – | – | – | – | – |
| chambal-fy25-004 | computed | fit | 2/3 | 3/3 | 3/3 | – | 1 | – |
| chambal-fy25-005 | multi-hop | test | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-004 | units-trap | fit | 3/3 | 3/3 | 3/3 | – | – | – |
| navneet-fy25-005 | not-in-filing | fit | 3/3 | – | – | – | – | – |
| unihealth-fy26-001 | numeric-lookup | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-002 | numeric-lookup | fit | 0/3 | 3/3 | 0/3 | – | – | – |
| unihealth-fy26-003 | table | test | 3/3 | 3/3 | 3/3 | – | – | – |
| unihealth-fy26-004 | not-in-filing | test | 3/3 | – | – | – | – | – |

- Answerable passed: 47/54 (87%) · correct 51/54 (94%) · faithful 51/54 (94%)
- Not-in-filing refused bare: 18/18 (100%) · refusal leaks (any question): 0
- By type: computed 2/3 (67%), multi-hop 3/3 (100%), not-in-filing 18/18 (100%), numeric-lookup 26/30 (87%), table 10/12 (83%), two-column 3/3 (100%), units-trap 3/3 (100%)
- By split: fit 29/36 (81%), test 36/36 (100%)

One guard fix: "(computed from [page N])" placed right after a claim's citation
labels that claim (Haiku 5.5 writes it there; the guard had flagged the figure).
47/54 vs Haiku 4.5's 48/54, correct 51 vs 50, faithful 51 vs 50, refusals
18/18 both, test half 36/36 vs 35/36. hcc-006 recovers. Shipped: within one
answer on pass rate, ahead on correctness and faithfulness, and a sixth of the
cost ($0.0012 a question, measured; 3.3 s mean latency, 9.7 s worst). Two
standing judge disagreements: hcc-003/008 answers that say the page does not
state the scope are marked incorrect, and unihealth-002's "150 beds is the sum
of 120 and 30" is marked an unlabelled computation.
