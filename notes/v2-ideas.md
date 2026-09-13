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
