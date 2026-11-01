"""Answer availability from a recorded retrieval: is the answer in front of the model at all?

No model and no API: for each answerable question, whether an expected page is
among the ranked hits, whether it is in the packed context, and whether the
recorded answer string (expected_answer_text) is printed in that context. A
question that fails here cannot be answered whatever the prompt says, so this
separates retrieval failures from generation failures before any paid run.

Run: python -m evals.availability --retrieval evals/retrieval/eval-candidates.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.retrieval import load, replay
from retrieve.search import open_index

QUESTIONS = Path("notes/eval-candidates.jsonl")


def availability(dump: dict, table, questions: list[dict]) -> list[dict]:
    rows = []
    for q in questions:
        if not q["expected_pages"]:
            continue
        hits, context = replay(dump, table, q["company"], q["question"])
        text = "\n".join(c["text"] for c in context).replace("\n", " ").lower()
        wanted = (q.get("expected_answer_text") or "").replace("\n", " ").lower()
        rows.append({"id": q["id"], "style": q.get("style") or q["type"],
                     "page_in_hits": any(h["page"] in q["expected_pages"] for h in hits),
                     "page_in_context": any(c["page"] in q["expected_pages"] for c in context),
                     "answer_in_context": bool(wanted) and wanted in text})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Answer availability from a recorded retrieval (no API calls).")
    parser.add_argument("--retrieval", type=Path, required=True)
    parser.add_argument("--questions", type=Path, default=QUESTIONS)
    args = parser.parse_args()
    questions = [json.loads(line) for line in args.questions.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = availability(load(args.retrieval), open_index(Path("data/lancedb")), questions)
    print("| Question | Style | Expected page ranked | Page in context | Answer string in context |\n|---|---|---|---|---|")
    for r in rows:
        mark = lambda v: "yes" if v else "**no**"
        print(f"| {r['id']} | {r['style']} | {mark(r['page_in_hits'])} | {mark(r['page_in_context'])} | {mark(r['answer_in_context'])} |")
    total = len(rows)
    print(f"\nExpected page ranked {sum(r['page_in_hits'] for r in rows)}/{total} · in context "
          f"{sum(r['page_in_context'] for r in rows)}/{total} · answer string in context "
          f"{sum(r['answer_in_context'] for r in rows)}/{total}")


if __name__ == "__main__":
    main()
