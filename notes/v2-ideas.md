# v2 ideas

Logged during v1 so they are flagged, not built early (CLAUDE.md). Each
entry: what, the evidence, and where in v2 it belongs.

## Note-number cross-references are a retrieval hop

Statement rows carry a "Note No." cell that points into the Notes to
Accounts, often 15-40 pages later. On p114, `Property, plant and equipment |
3A | 156.08 | 228.79` sends the reader to Note 3A. A question about what
makes up a balance-sheet line needs the statement page and the note page
together, and nothing in the statement chunk's text resembles the note
chunk's text, so similarity search will not pair them.

Idea: when a retrieved chunk contains a note reference, fetch the chunk that
opens with that note's heading as a second hop. Belongs with the multi-hop
eval pairs (v2.3) and gets a before/after eval run like any retrieval change.
Not a footnote matcher, and not built in v1.

## Statement scope lives in the stripped running header

Stage 3 strips the running header "Summary of material accounting policies
and other explanatory information to the standalone / consolidated financial
statements..." as furniture (126 pages). On notes pages it is the only
in-text signal of statement scope. It is kept in each clean page record's
`furniture` field, so the v2 scope tag (SPEC.md §3.4) can read it instead of
re-deriving it from the PDF.

## Full-text statistics drift as the corpus grows

Adding Chambal and Navneet moved an HCC result, even though every query is
filtered to one company. Eval 001 fell from rank 5 to 6 and two questions lost
their answer-bearing chunk from the context — on identical chunks, an
identical query and unchanged code. An HCC-only index built from the same
chunk file reproduced the old ranking, which isolates the cause: LanceDB's
full-text scores use collection-wide word statistics, so a term's weight
depends on how often it appears across all filings. The `where` clause filters
rows after scoring; it does not rescope the statistics behind the score.

The v1 fix — 8 expansion seeds and a 6,000-token budget — restored 8/8 answer
availability by widening the net, not by rescoping. It absorbs drift; it does
not stop it. Three filings moved a rank by one, and the budget has room for
that. Twelve will not be so forgiving, and the budget cannot keep growing:
context costs money per question and dilutes what the model attends to.

For v2: once multi-year ingest brings 12+ documents, measure whether the
current retrieval still holds against the 20-pair eval set, then evaluate
per-filing tables — one table per document, so each filing's statistics are
its own — against a single table with the wider expansion. Per-filing tables
cost a table open per query and make cross-filing questions (v3) harder;
that trade is the decision, and it needs the eval numbers, not an argument.

## The refusal floor is compressed, and may not survive v2

Stage 7 set the similarity floor from HCC alone: the weakest answerable
question scored 0.732, the not-in-the-filing question 0.644, and 0.69 sat in
that +0.088 gap. Three filings compressed it. The weakest answerable question
is now 0.702 and the strongest miss 0.644 — a +0.058 gap — and the floor moved
to 0.67 to stay inside it.

The direction is what matters. More documents mean more chances that some page
somewhere resembles a question the filing does not answer, so the gap narrows
as the corpus grows, and the floor is a single number calibrated on nine
questions. At some corpus size the distributions overlap and no single
threshold separates them.

The eval set already carries not-in-filing questions per company, so the gap
is measurable at every corpus size rather than discovered when it closes. v2
decides whether a similarity gate survives at all, or whether refusal moves
to evidence the gate cannot see — a reranker score, or the model's own
judgement of the extracts under the refusal contract, which is the only
check of the four that reads the text rather than a number about it.
