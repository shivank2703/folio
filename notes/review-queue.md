# Review queue

Comprehension questions queued during the v1 build. They no longer block
work (CLAUDE.md, "build first, explain after"): they are asked at the
end-of-sitting review, a few at a time, and an entry is deleted once it is
answered well cold.

## Stage 1: scaffold (answer key was supplied, never answered cold)

A. requirements.txt as a decision log: why was the embedding backend
   deliberately absent at Stage 1? (Installing sentence-transformers early
   drags in PyTorch and decides the Stage 4 gate by inertia.)
B. data/ vs corpus/: why is one disposable and the other irreplaceable, and
   why are both gitignored for opposite reasons? (NB: data/lancedb/ has since
   been un-ignored. Why is that exception safe?)
C. .env.example vs .env: schema vs instance. What does the template buy a
   fresh clone?

## Stages 3-9

preprocess.py (answered weakly in-session):
1. The unit line passes every furniture test (small, top margin, same height
   on 108 pages). What breaks downstream if it is stripped, and why is a
   content rule better than a tighter margin? — Earlier answer: "data loss": right
   on cost, missed the margin half (header line 2 ends y=71.0, unit line
   72.3: a 1.3pt window only true of this typesetter).
2. With `is_prose`/`is_grid` deleted, what changes and why does the
   word-multiset check still pass? — Earlier answer: "no" (wrong). The check
   ignores order; 16 pages change, label+figure rows 58->47. NB: ask about
   p82, not p114 (p114 is one full-width block and doesn't change).
3. Why copy unit/header lines instead of moving them? — Unanswered. Answer:
   p251 prints FY25 and FY24 single-period tables on one page.

chunk.py (never answered):
4. Why does `with_context` decide per kind rather than all-or-nothing?
5. Why may a table row end a chunk without being repeated, when a prose
   line in the same spot is carried over?
6. Why doesn't the chunker carry a header across a page break into chunk
   text? (Superseded by a design change: carried as metadata instead — ask
   why metadata, not text.)

Stage 4, retrieve/embed.py (skipped 2026-09-13, never asked):
7. Why does `write_index` overwrite instead of append, and what would a
   re-run do to search results if it appended?
8. Why normalise vectors to unit length before any distance metric is
   chosen? (cosine = dot, L2 ranks the same.)
9. The standalone and consolidated TOTAL ASSETS chunks score 0.978. Why
   can't the embedding separate them, and which layer should?

Stage 5, retrieve/search.py and smoke.py (skipped 2026-09-13):
10. Why does open_index raise on a different stored model name instead of
    warning and searching anyway?
11. Why does the smoke test search to depth 20 when the generator sees 5?
12. "Total assets" is printed on p114, yet keyword scoring ranked it 101st
    for question 001. Why, and what fixed it?

Stages 6-8, gen/answer.py, gen/guardrails.py, ui/app.py (skipped 2026-09-21
in the catch-up session, at the user's request):
13. Citations are taken from the extract header written from chunk metadata,
    never from the page text. What could the model cite instead, and why is
    that failure worse than a wrong figure?
14. The similarity gate runs before the model call and the citation check
    after. Why can neither replace the other, and what does each miss?
15. The scrub matches "we recommend buying" but not "the Board recommended a
    dividend". What breaks if the pattern is loosened to the word "recommend"?

Stage 9, ingest/build.py and company scoping (skipped 2026-09-22):
16. Identity comes from corpus/corpus.json, not from filenames, and the build
    verifies each SHA-256 before ingesting. What does the checksum protect
    that a filename cannot?
17. All three filings have a page 114. What breaks without the company
    filter, and why is the fix a filter on search rather than putting the
    company into the citation text?
18. Adding two filings moved an HCC page from rank 5 to 6 even though every
    query is filtered to HCC. Why did an unrelated document change HCC's
    ranking, and which half of the hybrid was responsible?

19. The Stage 6 idempotence check — `if TABLE_NAME in db.list_tables():
    db.drop_table(...)` — passed review and never once ran. What was
    `list_tables()` actually returning, why did the membership test fail
    silently instead of raising, and what would have caught it: a second
    build in the same session, or a unit test?
