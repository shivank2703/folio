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
