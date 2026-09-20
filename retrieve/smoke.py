"""Smoke test: run the recorded questions and show which pages retrieval found.

Stage 5 (SPEC.md §4). This is not the v2 eval — no answer is generated or
graded. It asks one question of retrieval alone: for each recorded question,
does a page holding the answer come back, and how high?

The switches matter as much as the numbers. Every retrieval change has to show
a before and after on these questions (rag-eval), so --no-expand and
--vector-only reproduce the retrieval a change replaced.
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
    parser.add_argument("--no-expand", action="store_true", help="skip fiscal-year expansion")
    parser.add_argument("--vector-only", action="store_true", help="skip the keyword ranking")
    parser.add_argument(
        "--answer", action="store_true", help="also answer each question through the guardrails (spends API credit)"
    )
    args = parser.parse_args()

    table = open_index(args.db)
    model = load_model()
    # The harness reaches up into gen on purpose: these are the same questions
    # the answer path must handle. The import sits here, not at module level,
    # so a retrieval-only run needs no API credentials at all.
    client = None
    if args.answer:
        from gen.answer import build_client, guarded_answer
        from gen.guardrails import cited_pages

        client = build_client()
    with args.questions.open(encoding="utf-8") as f:
        questions = [json.loads(line) for line in f]

    label = ("vector" if args.vector_only else "hybrid") + (", no FY expansion" if args.no_expand else ", FY expanded")
    print(f"retrieval: {label}")
    found, answerable_best, negative_best = 0, [], []
    answerable = [q for q in questions if q["expected_pages"]]
    for q in questions:
        hits = search(
            table, model, q["question"], SEARCH_DEPTH, expand=not args.no_expand, hybrid=not args.vector_only
        )
        best = max(hit["score"] for hit in hits[:SHOWN])
        print(f"\n{q['id']} [{q['type']}] {q['question']}")
        print("  top %d: %s" % (SHOWN, ", ".join(f"p{h['page']} {h['score']:.3f}" for h in hits[:SHOWN])))
        if q["expected_pages"]:
            rank = first_rank(hits, q["expected_pages"])
            found += rank is not None and rank <= SHOWN
            answerable_best.append(best)
            wanted = ", ".join(f"p{p}" for p in q["expected_pages"])
            print(f"  expected {wanted}: " + (f"rank {rank}" if rank else f"not in the top {SEARCH_DEPTH}"))
        else:
            # Retrieval always returns chunks; only a score can say "nothing
            # here". Stage 7 sets that threshold, and this line is its evidence.
            negative_best.append(best)
            print(f"  not in the filing: best similarity in the top {SHOWN} is {best:.3f}")
        if client is not None:
            verdict = guarded_answer(q["question"], hits[:SHOWN], client)
            if verdict["refused"]:
                print(f"  ANSWER: refused - {verdict['reason']}")
            else:
                print(f"  ANSWER: {verdict['text']}")
                print(f"  cited pages {sorted(set(cited_pages(verdict['text'])))}"
                      f" | invalid {verdict['invalid_citations']} | advice removed {len(verdict['scrubbed'])}")

    print(f"\n{found}/{len(answerable)} answerable questions found an expected page in the top {SHOWN}")
    if answerable_best and negative_best:
        gap = min(answerable_best) - max(negative_best)
        print(f"score gap: weakest answerable {min(answerable_best):.3f} - strongest not-in-filing "
              f"{max(negative_best):.3f} = {gap:+.3f}")


if __name__ == "__main__":
    main()
