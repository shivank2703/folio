"""Score answers on the eval set: correctness, faithfulness, refusals.

Accurate step (SPEC.md §4). retrieve.smoke measures retrieval; this measures
what a reader actually gets. Every question goes through the same path the
app runs (search, page expansion, guarded_answer), so a score here is a score
of the deployed behaviour, not of a harness that approximates it.

Three verdicts per answer, two of them mechanical:

- Refusal correctness is checked by equality, not judged. A not-in-filing
  question passes only on the bare refusal; an answerable one fails if it is
  refused. "Not in the filing." followed by anything else fails either way:
  the contract is one sentence (notes/accurate-step.md).
- Citation validity comes from guarded_answer itself: a page the model was
  never shown is a failure no judge should be able to excuse.
- Correctness and faithfulness need reading, so Haiku judges them, against the
  recorded expected answer and against the text of the pages the answer cites.

Answers are sampled several times because generation is not deterministic: the
refusal leak this step exists to fix showed up in two of four samples. A
single run would score it as present or absent by luck.

Run: python -m evals.score --label baseline   (spends API credit)
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import anthropic

from gen.answer import build_client, guarded_answer
from gen.guardrails import REFUSAL, cited_pages
from retrieve.embed import load_model
from retrieve.search import DEFAULT_K, EXPANSION_SEEDS, open_index, page_context, search

QUESTIONS = Path("notes/eval-candidates.jsonl")
RESULTS = Path("evals/results")

# The judge reads a few pages and returns a few fields. The cheapest current
# model is enough for that, and the same model as the answerer keeps the cost
# of an eval run near the cost of the questions themselves. Temperature 0: a
# judge that changes its mind between runs turns a before/after into noise.
JUDGE_MODEL = "claude-haiku-4-5"

# Two calls, not one. A judge that can see the cited pages lets a wrong
# citation colour its reading of a right figure: graded together, chambal-002's
# correct capacity cited to the wrong page came back "incorrect" even when told
# to grade the figures alone. So correctness is judged blind to the evidence,
# and faithfulness is judged against nothing but the evidence.
CORRECT_SYSTEM = """You grade an answer from a question-answering system over \
Indian annual reports against a reference answer written by a person who read \
the filing. Ignore page citations entirely.

correct: the answer gives the same figure(s) as the reference, with the same \
unit (crore vs lakhs matters: a 100x error is wrong), the same period, and the \
same scope (standalone vs consolidated). A negative figure must stay negative. \
Extra true detail is fine. Leaving out a comparison year the question did not \
ask for is fine. If the question asks for two things, both must be right."""

FAITHFUL_SYSTEM = """You check whether an answer from a question-answering \
system over Indian annual reports is supported by the pages it cites. You are \
given the answer and the full text of every page it cites. You are not told \
the right answer, and you must not judge whether the answer is true, only \
whether the cited text supports it.

faithful: every factual claim in the answer is supported by the cited pages' \
text as given. A figure stated in the answer but absent from the cited pages \
is unfaithful, even if it might be true elsewhere.

Computed figures need care. A computed figure is any number the answer states \
that no cited page prints: a difference, a total, a ratio, a percentage \
change. First list every one in computed_figures. A computed figure is \
labelled only if the answer explicitly calls it computed or calculated, for \
example "(computed from [page 114])". Wording such as "an increase of", "a \
difference of", "representing" or "which means" is NOT a label. The answer is \
faithful only if every computed figure is labelled, its inputs are on the \
cited pages, and its arithmetic is right.

Judge only what is written. Do not reward an answer for sounding careful."""

CORRECT_SCHEMA = {
    "type": "object",
    "properties": {"correct": {"type": "boolean"}, "reason": {"type": "string"}},
    "required": ["correct", "reason"],
    "additionalProperties": False,
}

FAITHFUL_SCHEMA = {
    "type": "object",
    "properties": {
        "computed_figures": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "figure": {"type": "string"},
                    "labelled": {"type": "boolean"},
                    "arithmetic_right": {"type": "boolean"},
                },
                "required": ["figure", "labelled", "arithmetic_right"],
                "additionalProperties": False,
            },
        },
        "faithful": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    # computed_figures comes first so the judge commits to the list before it
    # writes a verdict that the list would contradict.
    "required": ["computed_figures", "faithful", "reason"],
    "additionalProperties": False,
}


def ask_judge(client: anthropic.Anthropic, system: str, prompt: str, schema: dict) -> dict:
    """One temperature-0 judge call whose reply is guaranteed to match the schema."""
    message = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=1024,
        temperature=0,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    return json.loads(next(b.text for b in message.content if b.type == "text"))


def judge(client: anthropic.Anthropic, q: dict, answer: str, context: list[dict]) -> dict:
    """Grade one answer: correct against the reference, faithful against its cited pages."""
    correct = ask_judge(
        client, CORRECT_SYSTEM,
        f"Question: {q['question']}\n\nReference answer: {q['expected_answer']}\n\nSystem answer: {answer}",
        CORRECT_SCHEMA,
    )
    cited = set(cited_pages(answer))
    pages = "\n\n".join(
        f"--- page {c['page']} chunk {c['chunk']} ---\n{c['text']}"
        for c in sorted(context, key=lambda c: (c["page"], c["chunk"]))
        if c["page"] in cited
    )
    faithful = ask_judge(
        client, FAITHFUL_SYSTEM,
        f"Answer: {answer}\n\nCited pages:\n\n{pages or '(the answer cites no page)'}",
        FAITHFUL_SCHEMA,
    )
    # The list is the evidence; the boolean is the judge's summary of it. When
    # they disagree the list wins, so a lenient summary cannot pass an
    # unlabelled computation.
    if any(not f["labelled"] or not f["arithmetic_right"] for f in faithful["computed_figures"]):
        faithful["faithful"] = False
    return {"correct": correct["correct"], "faithful": faithful["faithful"],
            "reason": f"correct: {correct['reason']} | faithful: {faithful['reason']}",
            "computed_figures": faithful["computed_figures"]}


def grade(q: dict, verdict: dict, client: anthropic.Anthropic) -> dict:
    """Turn one guarded answer into pass/fail verdicts for this question."""
    text = verdict["text"].strip()
    bare_refusal = verdict["refused"] and text == REFUSAL
    # A reply that opens with the refusal sentence and keeps going broke the
    # contract whether or not a guard later caught it, so this reads the
    # model's raw words, not the repaired text the reader is shown.
    raw = (verdict.get("raw") or verdict["text"]).strip()
    leaked = raw.startswith(REFUSAL) and raw != REFUSAL
    row = {"text": text, "raw": raw, "refused": verdict["refused"], "reason": verdict.get("reason", ""),
           "cited": sorted(set(cited_pages(text))), "invalid": verdict["invalid_citations"],
           "ungrounded": verdict.get("ungrounded", []), "recited": verdict.get("recited", []),
           "leaked_refusal": leaked}
    if not q["expected_pages"]:
        row.update(passed=bare_refusal and not leaked)
        return row
    if verdict["refused"] or leaked:
        row.update(correct=False, faithful=False, passed=False, judge="refused")
        return row
    j = judge(client, q, text, verdict["context"])
    row.update(correct=j["correct"], faithful=j["faithful"], judge=j["reason"], computed=j["computed_figures"])
    # A figure the guard flagged as missing from its cited page reaches the
    # reader with a warning; that is a failure to cite, whatever the judge says.
    row["passed"] = (j["correct"] and j["faithful"] and not verdict["invalid_citations"]
                     and not verdict.get("ungrounded"))
    return row


def run(label: str, samples: int, only: set[str] | None, rerank_gate: tuple[str, float] | None = None) -> dict:
    questions = [json.loads(line) for line in QUESTIONS.open(encoding="utf-8")]
    if only:
        questions = [q for q in questions if q["id"] in only]
    table, model, client = open_index(Path("data/lancedb")), load_model(), build_client()
    reranker = None
    if rerank_gate:
        # Experiment only: the app does not rerank (evals/RESULTS.md says why).
        from retrieve.rerank import CANDIDATES, load_reranker, rerank
        reranker = load_reranker(rerank_gate[0])
    out = {"label": label, "samples": samples, "when": time.strftime("%Y-%m-%d %H:%M"), "questions": []}
    for q in questions:
        hits = search(table, model, q["question"], max(DEFAULT_K, EXPANSION_SEEDS), q["company"])
        if reranker is not None:
            ranked = rerank(reranker, q["question"], search(table, model, q["question"], CANDIDATES, q["company"]))
            hits = ranked[: max(DEFAULT_K, EXPANSION_SEEDS)]
            if ranked[0]["rerank"] < rerank_gate[1]:
                refused = {"text": REFUSAL, "refused": True, "invalid_citations": [], "context": [],
                           "reason": f"rerank {ranked[0]['rerank']:.3f} below {rerank_gate[1]}"}
                rows = [grade(q, refused, client) for _ in range(samples)]
                out["questions"].append({**{k: q[k] for k in ("id", "type", "company", "split")},
                                         "answerable": bool(q["expected_pages"]), "samples": rows})
                print(f"{q['id']:<18} {q['type']:<14} {sum(r['passed'] for r in rows)}/{samples}  gate refused")
                continue
        context = page_context(table, hits)
        rows = [grade(q, guarded_answer(q["question"], hits, client, context), client) for _ in range(samples)]
        out["questions"].append({**{k: q[k] for k in ("id", "type", "company", "split")},
                                 "answerable": bool(q["expected_pages"]), "samples": rows})
        passed = sum(r["passed"] for r in rows)
        print(f"{q['id']:<18} {q['type']:<14} {passed}/{samples}  {rows[0]['text'][:90]!r}")
    return out


def summarise(result: dict) -> str:
    """A markdown table per question plus totals by question type and split."""
    n = result["samples"]
    lines = [f"### {result['label']} ({result['when']}, {n} samples per question)", "",
             "| Question | Type | Split | Pass | Correct | Faithful | Leaked refusal | Ungrounded figure | Citation corrected |", "|---|---|---|---|---|---|---|---|---|"]
    by_type: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_split: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    totals = {"answerable": [0, 0], "negative": [0, 0], "correct": [0, 0], "faithful": [0, 0], "leaks": 0}
    for q in result["questions"]:
        rows = q["samples"]
        p = sum(r["passed"] for r in rows)
        kind = "answerable" if q["answerable"] else "negative"
        for bucket in (by_type[q["type"]], by_split[q["split"]], totals[kind]):
            bucket[0] += p
            bucket[1] += n
        leaks = sum(r["leaked_refusal"] for r in rows)
        totals["leaks"] += leaks
        if q["answerable"]:
            c, f = sum(r.get("correct", False) for r in rows), sum(r.get("faithful", False) for r in rows)
            totals["correct"][0] += c
            totals["faithful"][0] += f
            totals["correct"][1] += n
            totals["faithful"][1] += n
            cf = (f"{c}/{n}", f"{f}/{n}")
        else:
            cf = ("–", "–")
        ungrounded = sum(bool(r.get("ungrounded")) for r in rows)
        # A corrected citation still passes (the reader sees the right page),
        # but it is counted: it is the model getting the page wrong.
        recited = sum(bool(r.get("recited")) for r in rows)
        lines.append(f"| {q['id']} | {q['type']} | {q['split']} | {p}/{n} | {cf[0]} | {cf[1]} | {leaks or '–'} "
                     f"| {ungrounded or '–'} | {recited or '–'} |")

    def pct(pair: list[int]) -> str:
        return f"{pair[0]}/{pair[1]} ({100 * pair[0] / pair[1]:.0f}%)" if pair[1] else "–"

    lines += ["", f"- Answerable passed: {pct(totals['answerable'])} · correct {pct(totals['correct'])}"
              f" · faithful {pct(totals['faithful'])}",
              f"- Not-in-filing refused bare: {pct(totals['negative'])} · refusal leaks (any question): {totals['leaks']}",
              "- By type: " + ", ".join(f"{t} {pct(v)}" for t, v in sorted(by_type.items())),
              "- By split: " + ", ".join(f"{s} {pct(v)}" for s, v in sorted(by_split.items())), ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score cited answers on the eval set (spends API credit).")
    parser.add_argument("--label", required=True, help="name for this run, e.g. baseline or tables")
    parser.add_argument("--samples", type=int, default=3, help="answers generated per question")
    parser.add_argument("--only", nargs="*", help="question ids to run, for debugging")
    parser.add_argument("--rerank-gate", nargs=2, metavar=("MODEL", "THRESHOLD"),
                        help="experiment: rerank candidates and gate on the best score (python -m evals.fit_gate)")
    args = parser.parse_args()
    gate = (args.rerank_gate[0], float(args.rerank_gate[1])) if args.rerank_gate else None
    result = run(args.label, args.samples, set(args.only) if args.only else None, gate)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{args.label}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n" + summarise(result))


if __name__ == "__main__":
    main()
