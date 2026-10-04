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
