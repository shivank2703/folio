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


## Funds · 19 October 2026 · release candidate

The before run is `results/funds-v1.2-baseline.json`, preserved byte-for-byte.
The after run is `results/funds-release-final.json`. Both use the existing
24-question set, three samples per question, the same generation model and
frozen blind correctness/faithfulness judges. The latter uses the complete
32-filing index. No score is manually overridden.

| Measure | Saved v1.2 before | Funds after |
|---|---|---|
| Answerable passed | 44/54 (81%) | 53/54 (98%) |
| Correct | 51/54 (94%) | 54/54 (100%) |
| Faithful | 49/54 (91%) | 53/54 (98%) |
| Bare refusals | 18/18 | 18/18 |
| Refusal leaks | 0 | 0 |

After by type: numeric 30/30, table 12/12, computed 3/3, multi-hop 3/3,
units trap 3/3, two-column 2/3. HCC's previously missing continuation and
Chambal's computed-answer formatting each pass 3/3. The sole after failure is
`hcc-fy25-009`: the faithfulness judge invents a “387 meters” computation absent
from the answer and flags differences between tunnel figures attributed to
separate report sections. The automated failure remains recorded.

Additional sets:

- `funds-cases.jsonl` → `results/funds-disclosures-release.json`: **24/24**
  deterministic factsheet, holding, date/plan, BER/TER, coverage and refusal checks.
- `funds-reports.jsonl` → `results/funds-reports-release.json`: four questions ×
  three samples, **12/12 correct, 11/12 faithful, 11/12 passed**. Covers BEL
  standalone/consolidated, HDFC Bank and Indo-MIM. The one BEL standalone
  failure calls a printed total an unlabelled computation because the answer
  also describes the sum of its printed components. All figures match viewer
  page 98; the failure remains in the score.
- Local regression suite: **18 passed**. Retrieval smoke: **17/18** expected
  pages in the top five and **16/18** exact answer strings in packed context.
  These are string-match checks, not substitutes for end-to-end correctness.

Retained intermediate evidence: `funds-retrieval-candidate.json` (50/54 passed),
`funds-final.json` (47/54), `funds-reports.json` (3/12),
`funds-reports-query.json` (12/12), and `funds-computed-format.json` (3/3).
`funds-release-interrupted.json` records a stopped candidate: using the rewritten
ranking query for the calibrated gate score rejected Navneet's answerable
question. The final implementation keeps the original question representation
for that gate, without changing the 0.67 floor. Failed and interrupted runs are
retained rather than replaced by the better result.

The threshold still cannot separate answerable questions (weakest 0.702) from
negatives (strongest 0.757). Ten oversized whole rows retain full keyword/context
text but exceed the embedding model's input limit. Quality exclusions reduce
coverage; no claim of exhaustive validation follows from these small eval sets.


## Agent · 25 October 2026 — local candidate

The pre-change baseline used ordinary company Q&A. The after run used the new
agent path on the same 24 questions, three samples each, with the existing
Haiku 4.5 correctness and faithfulness judges unchanged. Each company evidence
bundle is judged against its own filing context before page numbers can collide.
The underlying retrieval, packing, generator and ordinary Q&A guards are unchanged.

| Measure | Fresh ordinary-Q&A baseline | Final company-agent path |
|---|---|---|
| Answerable passed | 54/54 | 53/54 |
| Correct | 54/54 | 54/54 |
| Faithful | 54/54 | 53/54 |
| Strict refusals | 18/18 | 18/18 |
| All samples passed | 72/72 | 71/72 |

Files: `agent-baseline.json` and `agent-company-release.json`. The retained
HCC retained-earnings failure is a judge disagreement: it calls a comparison
of two printed deficit balances an unlabelled computation, although the answer
states no computed difference. The score is not manually overridden.

The first company-agent run scored 50/72; preserving precise question wording
and fixing sentence splitting/citation placement improved an intermediate run
to 68/72 and the final run to 71/72. Those files remain available. The agent
withholds numeric/citation warnings rather than showing them in a memo; this is
stricter than ordinary Companies mode. These runs measure an added orchestration
path, not a claimed improvement to retrieval.

The final 12-case agent routing suite scored **36/36**: a fund memo, independent
source dates, wrong plan/month/day, unavailable total TER, unknown instruments,
per-fund top-ten coverage, mixed fund/report routing, scope, units and refusal.
Its complete intermediate scores were 27/36, 32/36 and 34/36. The initial file
has only 10/12 cases (22/30 completed samples): it stopped on an invalid Navneet
fixture code; it is not a complete result. JSON wrappers, over-selecting
holdings and generated legal-name queries account for early failures.

A separate five-question wording check scored **10/15** before the final
sentence-placement adjustment. The explicit March-date BEL variant failed 0/3,
retaining the known wording limitation. No threshold was relaxed.

The default company-memo check scored **2/3**. Every sample retained the correct
cited assets figure. For the failed sample the judge listed ₹4.36 crore as an
unlabelled computed figure, while its explanation said the amount is printed on
page 252 and no calculation occurred. The list overrides its summary boolean,
as in the existing evaluator, and the failure is retained. Completeness of
all sections is not established: a refused subquestion can leave a partial memo.

Local tests: **34 passed**. Existing deterministic fund checks: **24/24**.
Compile/whitespace checks and local browser smoke tests passed. The local UI
walkthrough and write-up are in `docs/`; deployment, owner-session verification,
profile pinning and tagging are not claimed here. See `notes/agent-step.md`.


## Natural questions · 1 November 2026 — false refusals at the floor

Four of sixteen live natural questions were refused at the 0.67 similarity
floor although their filings answer them: "Summarise HCC's performance in
FY25", "What are the key risks Unihealth faces?", "How big is L&T's order
book?" and "totla assets navneet". The eval set grew from 24 to 51 questions:
those four verbatim, nine more broad, summary, terse and misspelled questions
across other filings, and 14 new negatives (near misses, misspelled, broad and
off-topic), each split fit/test. 31 answerable, 20 negatives.

**How this was measured, and what is missing.** The sandbox this sitting ran
in cannot download the embedding model and has no Anthropic key
(notes/next-step.md). Retrieval was therefore recorded on GitHub's runners
(`evals/retrieval.py`, the `retrieval` workflow) and measured from those
recordings with no model calls: floor decisions (`python -m evals.gate_report`)
and answer availability (`python -m evals.availability`: is an expected page,
and the recorded answer string, in the context the model reads). **The
model-judged before/after has not run.** It is queued in
`evals/eval-requests.yaml` (`natural-before` at 96b305d, `natural-after` at
1d8e5b4) and runs on the `eval` workflow once the repository secret
`ANTHROPIC_API_KEY` exists; its first attempt stopped at that check
(run 41301501578). Until it runs, refusal strictness for the negatives that now
reach the model is not measured.

| Measure (no model calls) | Before: 0.67 floor (96b305d) | After: 0.59 filing-wide floor (1d8e5b4) |
|---|---|---|
| Answerable refused at the floor, fit | 2/16 | 0/16 |
| Answerable refused at the floor, test | 3/15 | 0/15 |
| Negatives stopped at the floor | 10/20 | 2/20 |
| Expected page in context | 23/31 | 27/31 |
| Recorded answer string in context | 21/31 | 26/31 |

The floor was not the only cause. On the before recording 8 of the 13 new
answerable questions never had their page in context: "Summarise BEL's FY26
results" ranked a "Summarised Cash Flows" note first on the instruction word,
"What does Tata Steel do?" became "What does do?" once the company name was
deleted from the query, and risk questions found the financial-risk notes
rather than the MD&A's threats. Retrieval changes (5272de0): misspellings
corrected against the filing's own vocabulary with common English protected
(the first, filing-only version turned "drones" into "does" and "patents"
into "payments" and was not shipped); the vector query names the company "the
company" instead of deleting it; instruction words leave the keyword query;
summary, risk and business questions add the section words reports print. No
original question lost its page.

The floor then changed statistic as well as value (1d8e5b4): the best cosine
anywhere in the filing instead of among the ranked hits, because the rewrites
move which chunks rank (Unihealth's risk question fell to 0.584 on the old
statistic, level with an off-topic question). 0.59 is the fit half's weakest
answerable question, L&T at 0.619, less a 0.03 margin fixed before the test
half was read. That binding case is a single question; the test half is the
evidence it generalises (0/15 refused), and the margin on the other side is
thin: the off-topic weather question sits at 0.584.

Still failing, retrieval-level:

- `sbin-fy26-001` "how many branches does sbi have": the ten-year table
  (p10) and network page (p6) are not retrieved; "branches" is on hundreds of
  pages.
- `eichermot-fy26-001` "royal enfield sales fy26": subsidiary pages rank, not
  p13's "sold more than 1.2 million". The full-text index does not stem, so
  "sales" never meets "sold" (notes/next-step.md).
- `divislab-fy26-001` and `icicibank-fy26-001` have their answer in context
  from pages other than the expected ones; counted as misses above, likely
  answerable.
- Negatives overlap answerable questions completely (0.64–0.76 on the new
  statistic); only off-topic input is stopped before the model.


## Units and scope · 1 November 2026

Two live failures: Infosys's revenue was answered "1,48,819" with no unit,
and "Reliance's net profit" with the standalone figure only. Six questions
added (f4fa88b): four unscoped line items whose filings print both scopes
(Reliance profit, Infosys and Tata Steel and L&T revenue), where a correct
answer gives the consolidated figure and says so, and two unit traps
(Infosys standalone revenue; Solar Industries' raw-materials inventory).

**Units.** The cause was upstream of the model. 2,344 of the index's 10,730
figure-bearing chunks carry no unit word: chunk.py inherits only a line it
recognises as a unit declaration, and many declarations are fused into a
running header (Solar: "for the year ended March 31, 2026 | (All amounts in
H Crores, unless otherwise stated)"), use a font glyph for ₹ ("H", "I", "J"),
abbreviate "(₹ Cr)" (HDFC Bank), or exceed eight words (Infosys's statement
header). `retrieve/units.py` finds declarations anywhere on a page at query
time and every extract's label carries them; 1,931 chunks are left with
neither, mostly counts (vehicles, shares, emissions). No re-index. The
prompt requires a unit on every amount, and a guard flags an amount stated
without one when its cited page declares a unit (counted in the eval's
"Unit missing" column, shown to the reader, not failed).

**Scope.** The prompt told the model to drop "other sections' versions of
the same figure", so with both scopes in context it gave whichever came
first. It now states the consolidated figure and says so. Retrieval for an
unscoped line item adds a ranking over consolidated chunks alone, with the
statement's title and Schedule III labels for a few reader terms ("net
profit" → "profit for the year", "revenue" → "revenue from operations"), and
reserves two of the eight seeds for its best hits.

| Measure (no model calls) | Step 3 code (f4fa88b recording ce5e796, 51 q) | Step 4 code (eeb5c96 recording 05912b3, 57 q) |
|---|---|---|
| Unscoped scope questions with the consolidated figure in context | — | 3/4 (Reliance missing) |
| Unit traps with the page's unit on the answer chunk | — | 2/2 |
| Expected page in context, all answerable | 27/31 | 33/37 |
| Recorded answer string in context, all answerable | 26/31 | 29/37 |

Two of the original 31 lost their recorded answer string, both by design:
"totla assets navneet" now has the consolidated ₹2,35,387 lakhs in context
instead of the standalone ₹2,28,299 lakhs (its reference accepts either),
and Divi's revenue now has the consolidated statement (₹10,560 crore). That
case exposed a wrong reference: it gave ₹10,894 crore, which is standalone
total income; corrected in 2f5f4f4, so runs at 96b305d and f4fa88b judge it
against the first reference.

Still failing: Reliance's consolidated statement of profit and loss (p101)
does not rank, even with the label and title words; its context has other
consolidated pages and the standalone figure. The model-judged run
`accuracy-after` is queued at 2f5f4f4 (code of eeb5c96).


## Memory and cold start · 1 November 2026

`python -m evals.footprint` replays the app's startup in one process and
then asks one question of each of the 32 filings (retrieval only, no API),
recording wall time and resident memory per stage. Measured on a GitHub
runner (`evals/results/footprint*.json`); Streamlit Community Cloud allows
about 2.7 GB.

| Stage (runner) | Time | Resident memory |
|---|---|---|
| imports (Streamlit + the app's modules) | 1.4 s | 332 MB |
| index fetch, SHA-256 check, unpack (fresh container) | 0.9 s | 336 MB (peak 424 MB while hashing) |
| open index (93 MB tarball, 120 MB on disk, 56,112 chunks) | 0.0 s | 360 MB |
| load embedding model (cached; a fresh container also downloads 67 MB) | 0.1 s | 560 MB |
| spelling vocabularies, all 32 filings | 1.0 s | 613 MB |
| first question, cold caches | 0.1 s | 641 MB |

| 10 passes × 32 questions | Resident memory after each pass | Peak |
|---|---|---|
| glibc default malloc arenas (the app until now) | 1,463 → 1,763 MB, still climbing | 1,775 MB |
| `MALLOC_ARENA_MAX=2` | 634–682 MB, flat | 759 MB |
| `mallopt(M_ARENA_MAX, 2)` at startup (shipped, `ui/memory.py`) | 687–729 MB, flat | 765 MB |

The index is not too big: it is 120 MB on disk and opening it costs 25 MB.
What grew was allocator fragmentation across the threads LanceDB, Arrow and
ONNX Runtime allocate from; the code before this sitting (543ff0a) grew the
same way (520 MB → 1,499 MB over three passes, `footprint-543ff0a.json`).
This sitting's retrieval adds about 150 MB at peak under default arenas
(the spelling vocabularies, 73 MB, and the unit lookups' imports) and about
50 ms of retrieval per question. With the arena limit the app holds about
0.7 GB, a quarter of the limit, with room for several times the corpus.
