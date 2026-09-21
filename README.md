# Praman

*praman (प्रमाण): proof, evidence. Every claim carries its source.*

Ask a question about an Indian listed company's annual report and get an answer
where **every claim cites the page it came from** — or an honest *"Not in the
filing."* Currently covering three FY25 annual reports — Hindustan
Construction, Chambal Fertilisers and Navneet Education — 896 pages and 4,704
chunks in one index. Each question is asked of one filing: page numbers repeat
across reports, and a citation to "page 114" means nothing without knowing
whose page 114 it is.

<!-- TODO at deploy: add docs/demo.gif and the live Streamlit link here. -->

## Why

Aggregate financial data is a solved problem. What is not solved is **checking
a number**. A figure lifted from an annual report is useless for research
unless you also know three things the page knows and a chatbot usually loses:

- **Which page it came from**, so it can be verified in seconds.
- **Its unit.** "8,743.37" means nothing until the page says *₹ crore* — and
  one page of this filing is printed in lakhs.
- **Its scope.** Standalone and consolidated statements repeat the same row
  labels with different numbers, 80 pages apart.

Praman is built so that a claim without all three never reaches the reader.

## How it works

```mermaid
flowchart LR
    PDF[Annual report PDF] --> EX[extract<br/>PyMuPDF, page-wise]
    EX --> PRE[preprocess<br/>layout rules]
    PRE --> CH[chunk<br/>~200 tokens, page-bound]
    CH --> EM[embed<br/>bge-small via ONNX]
    EM --> DB[(LanceDB<br/>vectors + full-text)]
    Q[Question] --> SE[search<br/>FY expansion, hybrid RRF,<br/>page expansion]
    DB --> SE
    SE --> G{guardrails}
    G -->|below the floor| R[Not in the filing.]
    G -->|passes| GEN[Claude Haiku<br/>cite-every-claim prompt]
    GEN --> V[citation validation<br/>+ advice scrub]
    V --> UI[Streamlit: answer + sources]
```

**Extraction keeps the page honest.** Running headers and footers are removed
by repetition, because the footer prints the report's *own* page number — two
behind the PDF page a citation must use. Tables printed sideways are turned
upright, two-column pages are re-ordered from block geometry, and table rows
are rebuilt from line positions so a label keeps its figures.

**Chunks carry their context.** A chunk inherits its page's statement title,
unit declaration and period header, so a chunk taken from the middle of a
balance sheet still knows it is the *standalone* one, reported in *₹ crore*,
*as at March 31, 2025*. Chunks never cross a page boundary — the page is the
citation unit.

**Retrieval is hybrid.** Questions say "FY25" while statements say "As at
March 31, 2025", so fiscal years are expanded to the dates the filing prints.
A vector ranking and LanceDB's full-text ranking are merged by reciprocal rank
fusion, then every retrieved page is widened to its neighbouring chunks: the
figure asked about often sits a chunk away from the wording that matched.

**Generation cites metadata, not text.** Each extract is labelled with the page
from its chunk record, and the model may cite only those labels — never a
number read out of the page, where note references and years look exactly like
page numbers.

## Guardrails

Four checks, because no single one keeps a citation honest:

| Check | When | What it stops |
|---|---|---|
| Similarity floor (0.69) | before the model is called | answering a question the filing never addresses |
| Refusal contract in the prompt | during the call | a hedged half-answer from plausible but unhelpful context |
| Citation validation | after the call | a page number the model never saw; all-invented or uncited answers are withheld entirely |
| Advice scrub | after the call | investment advice, which this project never produces |

## Measured

| | |
|---|---|
| Corpus | 3 filings, 896 pages → 4,704 chunks, index 10.6 MB |
| Rebuild | 2 min 37 s end to end (ingest 19 s, embed 139 s) |
| Retrieval (9 smoke questions) | 7/8 expected pages in the top 5 |
| Answer availability | 8/8 questions have the answer-bearing chunk in context |
| Refusal margin | weakest answerable 0.702 vs not-in-filing 0.644 |
| Warm retrieval | ~21 ms search, ~10 ms page expansion |

## Run locally

```bash
git clone <this repo> && cd praman
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
cp .env.example .env          # then paste your Anthropic API key into it
.venv/bin/python -m streamlit run ui/app.py
```

The search index ships in the repository (`data/lancedb/`), so nothing has to
be rebuilt to try it. To rebuild from source instead, download the PDFs listed
in [`corpus/SOURCES.md`](corpus/SOURCES.md) into `corpus/`, then:

```bash
.venv/bin/python -m ingest.build
```

That verifies each file's SHA-256 against `corpus/corpus.json`, runs extract →
preprocess → chunk for every filing, and embeds them all into one table. Adding
a company means adding its PDF and one manifest entry — no code changes.

Retrieval alone needs no API key: `.venv/bin/python -m retrieve.smoke`.

## Limitations

Stated plainly, because the point of the project is not overclaiming:

- **One fiscal year, and one filing per question.** Multi-year ingest is the
  next version's work, and comparing companies in a single answer is a v3 tool
  rather than something search should do by accident.
- **Adding filings shifts retrieval for the ones already there.** Full-text
  scores use collection-wide word statistics, so a third report moved one of
  HCC's pages from rank 5 to 6 even though the query is filtered to HCC. The
  context is built from more of the ranking than is shown, which absorbs that,
  but it is a property to watch as the corpus grows.
- **The 0.69 refusal floor is calibrated on five questions.** A 20-pair
  evaluation set, scored with RAGAS, is what will validate or move it.
- **Notes pages carry no standalone/consolidated tag.** For a question about
  receivables ageing, the consolidated schedule can outrank the standalone one.
  Statement pages are covered; notes pages are not, until scope tagging lands.
- **Complex tables are still imperfect.** Multi-level headers — statements of
  changes in equity, ageing schedules, sustainability-report grids — reassemble
  only partially. Core statements are clean.
- **The embedding model is a quantized export**, so published benchmark scores
  for it describe slightly different weights.
- **Not advice.** The system reports what the filing says. It produces no
  recommendations, and strips advice language if a model drifts into it.

## Data and licence

The source PDFs are public statutory filings and are **not** committed;
[`corpus/SOURCES.md`](corpus/SOURCES.md) records each exact URL and SHA-256,
and `corpus/corpus.json` carries the same in machine-readable form. The derived
chunk index is committed so the demo can load it, with attribution to each
issuing company and a link to its source document.

Licensed under [AGPL-3.0](LICENSE), matching PyMuPDF's terms for a
network-served application.
