"""Fit the refusal gate's threshold on half the eval set and report it on the other half.

Accurate step (SPEC.md §4). The 0.67 similarity floor was calibrated on the
same questions it was then judged on, and stopped separating as soon as every
filing had a not-in-filing question (+0.006 margin). A threshold chosen and
scored on one set of questions measures how well it was fitted, not how well
it gates. So the eval set carries a split: the threshold is chosen from the
"fit" questions only, and the "test" questions are scored once, afterwards.

For each question the gate sees the same candidates the app reranks; its
statistic is the best cross-encoder score among them. A threshold is any value
between the strongest not-in-filing score and the weakest answerable one; when
the fit half separates cleanly the midpoint of that gap is used, so neither
side is favoured. When it does not separate, the threshold that misclassifies
the fewest fit questions is used, ties broken toward refusing (a wrong refusal
costs the reader an answer; a wrong answer costs the product its promise).

Run: python -m evals.fit_gate            (no API calls)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from retrieve.embed import load_model
from retrieve.rerank import CANDIDATES, RERANK_MODELS, load_reranker, rerank
from retrieve.search import open_index, search

QUESTIONS = Path("notes/eval-candidates.jsonl")


def gate_scores(model_name: str) -> list[dict]:
    """Every question's best rerank score, and where its answer page landed."""
    table, embedder, reranker = open_index(Path("data/lancedb")), load_model(), load_reranker(model_name)
    rows = []
    for line in QUESTIONS.open(encoding="utf-8"):
        q = json.loads(line)
        candidates = search(table, embedder, q["question"], CANDIDATES, q["company"])
        ranked = rerank(reranker, q["question"], candidates)
        pages = q["expected_pages"]
        first = lambda hits: next((i for i, h in enumerate(hits, 1) if h["page"] in pages), None)
        rows.append({"id": q["id"], "split": q["split"], "answerable": bool(pages),
                     "best": ranked[0]["rerank"], "best_similarity": max(h["score"] for h in candidates[:8]),
                     "rank_before": first(candidates) if pages else None,
                     "rank_after": first(ranked) if pages else None})
    return rows


def fit_threshold(rows: list[dict]) -> float:
    """The threshold the fit half supports (see the module docstring for the rule)."""
    yes = sorted(r["best"] for r in rows if r["answerable"])
    no = sorted(r["best"] for r in rows if not r["answerable"])
    if yes[0] > no[-1]:
        return (yes[0] + no[-1]) / 2
    candidates = sorted(set(yes + no))
    cuts = [(a + b) / 2 for a, b in zip(candidates, candidates[1:])]

    def errors(t: float) -> int:
        return sum(s < t for s in yes) + sum(s >= t for s in no)

    return min(cuts, key=lambda t: (errors(t), -t))


def report(rows: list[dict], threshold: float, split: str) -> str:
    part = [r for r in rows if r["split"] == split]
    passed = sum(r["best"] >= threshold for r in part if r["answerable"])
    refused = sum(r["best"] < threshold for r in part if not r["answerable"])
    n_yes = sum(r["answerable"] for r in part)
    return f"{split}: answerable let through {passed}/{n_yes}, not-in-filing refused {refused}/{len(part) - n_yes}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit the rerank refusal threshold on the fit split.")
    parser.add_argument("--models", nargs="*", default=list(RERANK_MODELS))
    args = parser.parse_args()
    for model_name in args.models:
        rows = gate_scores(model_name)
        threshold = fit_threshold([r for r in rows if r["split"] == "fit"])
        print(f"\n== {model_name}  threshold fitted on 'fit': {threshold:.3f}")
        for r in sorted(rows, key=lambda r: (r["split"], not r["answerable"], r["best"])):
            kind = "answerable" if r["answerable"] else "NOT IN FILING"
            moved = f"rank {r['rank_before']} -> {r['rank_after']}" if r["answerable"] else ""
            print(f"  {r['split']:<4} {kind:<13} {r['id']:<18} rerank {r['best']:7.3f}  "
                  f"sim {r['best_similarity']:.3f}  {moved}")
        print("  " + report(rows, threshold, "fit"))
        print("  " + report(rows, threshold, "test") + "   <- the number that counts")


if __name__ == "__main__":
    main()
