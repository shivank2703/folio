"""Compare refusal-floor candidates on recorded gate scores: fit on one half, report on the other.

The floor's job, measured since Funds, is narrower than its name: it cannot
separate answerable questions from plausible negatives (those overlap), so
refusing those rests on the prompt contract and the strict-refusal guard. What
the floor can do is stop a question nothing in the filing resembles before a
paid call, and what it must not do is refuse a question the filing answers.
So a candidate is fitted to the fit half's weakest answerable question, less
a margin, and judged on the test half by two counts: answerable questions it
refuses (must be zero) and negatives it still stops before the model.

Run: python -m evals.gate_report --retrieval evals/retrieval/eval-candidates.json   (no API calls)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.retrieval import key

QUESTIONS = Path("notes/eval-candidates.jsonl")
# The floor before Nov 2026 (fused_best) and since (vector_best).
PREVIOUS_FLOOR = 0.67
CURRENT_FLOOR = 0.59

# Below the weakest fit answerable score, so a test question a little weaker
# than any fit question is not refused on noise. 0.03 is about half the gap
# measured between paraphrases of one question (notes/agent-step.md).
MARGIN = 0.03

STATISTICS = {
    "fused_best": "best cosine among the ranked hits (today's gate)",
    "vector_best": "best cosine anywhere in the filing (vector-only top hit)",
    "corrected": "best of fused_best and fused_best after misspelling correction (older recordings)",
}


def statistic(gate: dict, name: str) -> float:
    if name == "corrected":
        return max(gate["fused_best"], gate.get("corrected_best", 0.0))
    return gate[name]


def rows(dump: dict, questions: list[dict]) -> list[dict]:
    out = []
    for q in questions:
        gate = dump["questions"][key(q["company"], q["question"])]["gate"]
        out.append({"id": q["id"], "split": q["split"], "style": q.get("style") or q["type"],
                    "answerable": bool(q["expected_pages"]), "gate": gate})
    return out


def evaluate(table: list[dict], name: str, floor: float) -> dict:
    counts = {}
    for split in ("fit", "test"):
        part = [r for r in table if r["split"] == split]
        counts[split] = {
            "refused_answerable": sorted(r["id"] for r in part if r["answerable"] and statistic(r["gate"], name) < floor),
            "stopped_negatives": sorted(r["id"] for r in part if not r["answerable"] and statistic(r["gate"], name) < floor),
            "answerable": sum(r["answerable"] for r in part), "negatives": sum(not r["answerable"] for r in part)}
    return counts


def report(table: list[dict]) -> str:
    lines = ["| Statistic | Floor | Fit: answerable refused | Fit: negatives stopped | Test: answerable refused | Test: negatives stopped |",
             "|---|---|---|---|---|---|"]
    fitted = {}
    for name in STATISTICS:
        weakest = min(statistic(r["gate"], name) for r in table if r["split"] == "fit" and r["answerable"])
        candidates = ([("0.67 floor", PREVIOUS_FLOOR)] if name == "fused_best" else
                      [("shipped", CURRENT_FLOOR)] if name == "vector_best" else [])
        candidates.append(("fitted", round(weakest - MARGIN, 3)))
        for how, floor in candidates:
            c = evaluate(table, name, floor)
            fitted[(name, how)] = (floor, c)
            cell = lambda s, k: f"{len(c[s][k])}/{c[s]['answerable' if k.startswith('refused') else 'negatives']}"
            lines.append(f"| {name} ({how}) | {floor} | {cell('fit', 'refused_answerable')} | "
                         f"{cell('fit', 'stopped_negatives')} | {cell('test', 'refused_answerable')} | "
                         f"{cell('test', 'stopped_negatives')} |")
    lines += ["", "| Question | Split | Style | Answerable | fused_best | vector_best | corrected_best |", "|---|---|---|---|---|---|---|"]
    for r in sorted(table, key=lambda r: (not r["answerable"], r["gate"]["fused_best"])):
        g = r["gate"]
        corrected = f"{g['corrected_best']:.3f}" if "corrected_best" in g else "–"
        lines.append(f"| {r['id']} | {r['split']} | {r['style']} | {'yes' if r['answerable'] else 'no'} | "
                     f"{g['fused_best']:.3f} | {g['vector_best']:.3f} | {corrected} |")
    details = []
    for (name, how), (floor, c) in fitted.items():
        for split in ("fit", "test"):
            if c[split]["refused_answerable"]:
                details.append(f"- {name} {how} {floor}, {split}: refuses {', '.join(c[split]['refused_answerable'])}")
    return "\n".join(lines + [""] + details)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare refusal floors on recorded gate scores (no API calls).")
    parser.add_argument("--retrieval", type=Path, required=True)
    parser.add_argument("--questions", type=Path, default=QUESTIONS)
    args = parser.parse_args()
    dump = json.loads(args.retrieval.read_text(encoding="utf-8"))
    questions = [json.loads(line) for line in args.questions.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(report(rows(dump, questions)))


if __name__ == "__main__":
    main()
