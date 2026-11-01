"""Build each filing's cited overview offline, so a company page costs no API call.

An overview is five fixed questions per filing, each answered by the app's own
answer path (search, page packing, guarded_answer) and then held to a stricter
bar than an ordinary answer, because nobody asked for it and nobody will
re-ask: a section is kept only if it is not refused, has no citation to a page
never retrieved, no figure missing from its cited page, no amount without the
unit its page declares, and no removed advice. Within a kept section only
sentences that carry their own [page N] survive (agent.tools.report_sentences),
so every claim on the company page is one click from its page.

Stored in corpus/overviews.json beside the manifest: the filing it describes
(SHA-256 and fiscal year), the index and prompt it was built from, and per
section the question, the cited text and the pages. A section that failed is
recorded as missing with its reason, rather than silently absent.

    python -m overviews.build                    # every filing whose overview is missing or stale
    python -m overviews.build --company HCC      # one filing
    python -m overviews.build --write-questions  # refresh overviews/questions.jsonl (no model, no API)

Needs the embedding model and ANTHROPIC_API_KEY; the `overviews` workflow
runs it on GitHub's runners. --retrieval replays a recorded retrieval
(evals/retrieval.py) where the model cannot be downloaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from agent.tools import report_sentences
from gen.answer import MODEL, SYSTEM_PROMPT, build_client, filing_label, guarded_answer
from gen.guardrails import CITATION

MANIFEST = Path("corpus/corpus.json")
OVERVIEWS = Path("corpus/overviews.json")
QUESTIONS = Path("overviews/questions.jsonl")
DB = Path("data/lancedb")

# Section, heading, question. Phrased the way the eval's broad questions are,
# since those are the phrasings retrieval was measured on (evals/RESULTS.md).
# No scope is named, so the prompt's consolidated-first rule applies and
# each figure says which statement it is from.
SECTIONS = [
    ("business", "What it does", "What does {name} do? Describe its main businesses, products or services."),
    ("revenue", "Revenue", "What was {name}'s revenue from operations in {fy}?"),
    ("profit", "Profit", "What was {name}'s profit for the year in {fy}?"),
    ("assets", "Total assets", "What were {name}'s total assets at the end of {fy}?"),
    ("risks", "Top risks", "What are the key risks {name} faces?"),
]


def fingerprint() -> str:
    """What an overview depends on besides its filing: the prompt, the model and this file."""
    digest = hashlib.sha256((SYSTEM_PROMPT + MODEL).encode())
    digest.update(Path(__file__).read_bytes())
    return digest.hexdigest()[:16]


def questions(manifest: list[dict]) -> list[dict]:
    """Every overview question for every filing, in the eval's JSONL shape."""
    return [{"id": f"overview-{e['company'].lower()}-{key}", "company": e["company"],
             "question": template.format(name=e["name"], fy=e["fiscal_year"])}
            for e in manifest for key, _, template in SECTIONS]


def section(question: str, verdict: dict) -> dict:
    """One section from one guarded answer: kept text and pages, or why it is missing."""
    problems = [name for name in ("invalid_citations", "ungrounded", "unitless", "scrubbed") if verdict.get(name)]
    if verdict["refused"]:
        return {"question": question, "text": "", "pages": [], "missing": verdict.get("reason") or "refused"}
    if problems:
        return {"question": question, "text": "", "pages": [], "missing": "withheld: " + ", ".join(problems)}
    sentences = report_sentences(verdict["text"])
    if not sentences:
        return {"question": question, "text": "", "pages": [], "missing": "no sentence carried its own citation"}
    text = " ".join(sentences)
    return {"question": question, "text": text, "pages": sorted({int(p) for p in CITATION.findall(text)}), "missing": ""}


def build_one(entry: dict, retrieve, client) -> dict:
    """The overview of one filing; retrieve(question, company) returns (hits, context)."""
    label = filing_label(entry["company"])
    sections = {}
    for key, heading, template in SECTIONS:
        question = template.format(name=entry["name"], fy=entry["fiscal_year"])
        hits, context = retrieve(question, entry["company"])
        sections[key] = {"heading": heading, **section(question, guarded_answer(question, hits, client, context, label))}
    return {"company": entry["company"], "name": entry["name"], "fiscal_year": entry["fiscal_year"],
            "filing_sha256": entry["sha256"], "built": time.strftime("%Y-%m-%d"), "model": MODEL,
            "fingerprint": fingerprint(), "index": json.loads(Path("corpus/index.json").read_text())["sha256"],
            "sections": sections}


def stale(existing: dict | None, entry: dict) -> bool:
    """Missing, or built from another filing, index or prompt than the ones in force."""
    if not existing:
        return True
    index = json.loads(Path("corpus/index.json").read_text())["sha256"]
    return (existing.get("filing_sha256") != entry["sha256"] or existing.get("index") != index
            or existing.get("fingerprint") != fingerprint())


def load(path: Path = OVERVIEWS) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cited company overviews (needs the model and an API key).")
    parser.add_argument("--company", nargs="*", help="only these filings")
    parser.add_argument("--retrieval", type=Path, help="replay a recorded retrieval instead of searching")
    parser.add_argument("--write-questions", action="store_true", help=f"write {QUESTIONS} and stop")
    parser.add_argument("--force", action="store_true", help="rebuild even if up to date")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if args.write_questions:
        QUESTIONS.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions(manifest)), encoding="utf-8")
        print(f"{QUESTIONS}: {len(manifest) * len(SECTIONS)} questions")
        return

    from retrieve.search import DEFAULT_K, EXPANSION_SEEDS, open_index, page_context, search
    from retrieve.store import ensure_index

    ensure_index(DB)
    table, client = open_index(DB), build_client()
    if args.retrieval:
        from evals.retrieval import load as load_recording, replay
        recording = load_recording(args.retrieval)
        retrieve = lambda q, c: replay(recording, table, c, q)
    else:
        from retrieve.embed import load_model
        model = load_model()

        def retrieve(question: str, company: str):
            hits = search(table, model, question, max(DEFAULT_K, EXPANSION_SEEDS), company)
            return hits, page_context(table, hits)

    overviews = load()
    wanted = [e for e in manifest if not args.company or e["company"] in args.company]
    for entry in wanted:
        if not args.force and not stale(overviews.get(entry["company"]), entry):
            print(f"{entry['company']}: up to date")
            continue
        overviews[entry["company"]] = build_one(entry, retrieve, client)
        kept = sum(1 for s in overviews[entry["company"]]["sections"].values() if s["text"])
        print(f"{entry['company']}: {kept}/{len(SECTIONS)} sections kept", flush=True)
        # Written after every filing, so an interrupted run keeps what it paid for.
        OVERVIEWS.write_text(json.dumps(overviews, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
