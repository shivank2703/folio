"""Smoke test: run the recorded questions and show which pages retrieval found.

Stage 5 (SPEC.md §4). This is not the v2 eval — no answer is generated or
graded. It asks one question of retrieval alone: for each recorded question,
does a page holding the answer come back, and how high? The answer decides
whether vector search needs a keyword search beside it.

Questions come from notes/eval-candidates.jsonl, so the v2 eval set grows from
the same records instead of from a second list that drifts out of step.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from retrieve.embed import load_model
from retrieve.search import open_index, search

# The generator will see SHOWN chunks. Searching deeper tells a near miss (the
# right page at rank 8) apart from a true miss (nowhere in the top 20).
SHOWN = 5
SEARCH_DEPTH = 20


def first_rank(hits: list[dict], pages: list[int]) -> int | None:
    """1-based rank of the first hit on an expected page, or None if none appears."""
    return next((rank for rank, hit in enumerate(hits, start=1) if hit["page"] in pages), None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval smoke test over the recorded questions.")
    parser.add_argument(
        "--questions", type=Path, default=Path("notes/eval-candidates.jsonl"), help="question records"
    )
    parser.add_argument("--db", type=Path, default=Path("data/lancedb"), help="LanceDB directory from retrieve.embed")
    args = parser.parse_args()

    table = open_index(args.db)
    model = load_model()
    with args.questions.open(encoding="utf-8") as f:
        questions = [json.loads(line) for line in f]

    found, answerable_scores, negative_scores = 0, [], []
    answerable = [q for q in questions if q["expected_pages"]]
    for q in questions:
        hits = search(table, model, q["question"], k=SEARCH_DEPTH)
        print(f"\n{q['id']} [{q['type']}] {q['question']}")
        print("  top %d: %s" % (SHOWN, ", ".join(f"p{h['page']} {h['score']:.3f}" for h in hits[:SHOWN])))
        if q["expected_pages"]:
            rank = first_rank(hits, q["expected_pages"])
            found += rank is not None and rank <= SHOWN
            answerable_scores.append(hits[0]["score"])
            wanted = ", ".join(f"p{p}" for p in q["expected_pages"])
            print(f"  expected {wanted}: " + (f"rank {rank}" if rank else f"not in the top {SEARCH_DEPTH}"))
        else:
            # Retrieval always returns chunks; only the score can say "nothing
            # here". Stage 7 sets that threshold, and this line is its evidence.
            negative_scores.append(hits[0]["score"])
            print(f"  not in the filing: best score {hits[0]['score']:.3f}")

    print(f"\n{found}/{len(answerable)} answerable questions found an expected page in the top {SHOWN}")
    if answerable_scores and negative_scores:
        print(f"best score — lowest among answerable: {min(answerable_scores):.3f}; "
              f"highest among not-in-the-filing: {max(negative_scores):.3f}")


if __name__ == "__main__":
    main()
