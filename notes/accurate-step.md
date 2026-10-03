# Accurate step: logged during Public

Things that came up on Sat 03 Oct while shipping Public and were deliberately
not done then (CLAUDE.md: log, don't build). Each entry: what, the evidence,
and which Accurate item it belongs to, if any.

## Refusal contract leaks on near-miss negatives (item 3: reranker / refusal gate)

First generation run, 2026-10-03, Haiku 4.5. Both CHAMBAL and NAVNEET
negatives pass the 0.67 similarity floor (0.695, 0.696), so their refusal
rests on the prompt contract. Sampled four times each:

- chambal-fy25-003 (drones): 3 of 4 exact "Not in the filing."; 1 added
  uncited text, which the citation check withheld. Safe either way.
- navneet-fy25-003 (TV advertising): 2 of 4 replied "Not in the filing."
  followed by a cited sentence giving total advertising spend (1,399 lakhs,
  p322) and saying the TV share is not stated. `is_refusal` needs an exact
  match, the citation is valid, so this is shown as an answer.

The leaked text is true and cited, so nothing incorrect reaches a reader. It
is still a contract the prompt states and the model breaks half the time.
Decide in Accurate: either make "refusal + nearest cited fact" a defined
output (and render it as a refusal with context), or enforce the bare
refusal. Measure either way on the 20-question eval, with the reranker gate.

## Derived figures are stated without a source

hcc-fy25-001 answered "an increase of ₹605.34 crore". The arithmetic is
right (8,743.37 - 8,138.03), but the difference is printed nowhere in the
filing, and it sits in a sentence whose citation covers only the two
inputs. Belongs with answer-quality scoring (item 2): decide whether the
judge accepts computed differences, and whether the prompt should label them
("difference computed from [page 114]").

## LanceDB deprecation warnings on every hybrid search

lancedb 0.34 warns twice per query that `_distance` / `_score` will stop
being auto-projected. Harmless today, but a future upgrade silently drops
the columns `search` reads scores from. Fix when tables work touches
retrieval: select the score columns explicitly. It also floods the Cloud
logs (two lines per question).

## Transitive dependencies are not pinned

requirements.txt pins the nine direct dependencies exactly, but not what they
pull in (onnxruntime, tokenizers, huggingface-hub and so on). Those resolve at
install time and can differ by Python version or date, which is the silent
index/runtime mismatch the pins were meant to prevent. Python is held at 3.13
partly to compensate (Community Cloud picks Python only in the deploy dialog).
Generate a full lock from the working venv (`pip freeze` or `uv pip compile`)
and deploy from that.

## The sources panel is not in page order

`render_sources` says it shows chunks "in page order"; the live hcc-001 answer
listed p46, p101, p116 and then p114. It follows the context order from
`page_context`. Either sort it or fix the docstring; small, but the panel is
the citation UI.

## Cited pages could open the PDF at that page

The app now links each filing's source PDF (SPEC.md §7). A `#page=N` fragment
on that URL would make each [page N] citation open the page it cites. Most PDF
viewers honour it; check the three issuers' hosts serve the PDF inline.

## Local preview launcher cannot read the venv in some sessions

2026-10-04: `preview_start folio-ui` failed with PermissionError on
`.venv/pyvenv.cfg` (macOS file access for the launcher, not the app); starting
streamlit from the shell worked. Tooling only.
