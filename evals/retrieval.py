"""Retrieval as data: record it where the embedding model is, replay it where it is not.

search() and page_context() are the only steps of the answer path that need
the embedding model, and for one index, one model and one question they return
the same chunks every time. So the path can be split: a machine that has the
model (the `retrieval` GitHub Actions workflow) records which chunks each eval
question retrieved and with what scores, and any machine with the same index
replays them: `python -m evals.score --retrieval FILE` rebuilds each chunk's
text from the local index and runs the gate, generation, guards and judge
unchanged. A sandbox that cannot download the model can still run the eval.

Only identities and scores are recorded, never text: the text is in the index
already, so a dump stays small and cannot disagree with the chunks it names. A
dump is refused on replay when the index, the retrieval code or a question's
wording differs from the ones it was recorded with.

Each record also carries candidate gate scores, the numbers a refusal floor
could be set on, so alternatives can be compared on one run (evals/RESULTS.md):

- fused_best: the best cosine among the ranked hits: today's gate;
- vector_best: the best cosine anywhere in the filing (search()'s "gate"),
  which the floor has used since Nov 2026.

Recordings before that change also carried corrected_best, fused_best after
misspelling correction; search() now corrects every question itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from retrieve.embed import MODEL_NAME
from retrieve.search import DEFAULT_K, EXPANSION_SEEDS, TEXT_FIELDS, page_context, search
from retrieve.store import POINTER, source_of

# Files whose change can change what search() and page_context() return. A
# dump recorded before such a change no longer describes the code.
CODE = [Path("retrieve/search.py"), Path("retrieve/embed.py"), Path("retrieve/spelling.py")]
DB = Path("data/lancedb")


def code_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in CODE:
        if path.exists():
            digest.update(path.name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()[:16]


def index_fingerprint(db: Path = DB) -> str:
    """The published tarball's SHA-256 the local index came from; a local build is not replayable."""
    source = source_of(db)
    if source in (None, "local"):
        raise RuntimeError(f"{db} is a local build or missing; a dump must name a published index")
    return source


def key(company: str, question: str) -> str:
    return f"{company}\t{question}"


def ident(row: dict) -> dict:
    out = {"page": int(row["page"]), "chunk": int(row["chunk"]),
           "score": None if row.get("score") is None else round(float(row["score"]), 6),
           "sibling": bool(row.get("sibling", False))}
    if row.get("gate") is not None:
        out["gate"] = round(float(row["gate"]), 6)
    return out


def gate_scores(hits: list[dict]) -> dict:
    """The two candidate floor statistics for one question (see the module docstring)."""
    return {"fused_best": round(max((h["score"] for h in hits), default=0.0), 6),
            "vector_best": round(max((h.get("gate", h["score"]) for h in hits), default=0.0), 6)}


def record(questions: list[dict], table, model) -> dict:
    """Run retrieval for every question and keep what the replay needs."""
    out = {"recorded": time.strftime("%Y-%m-%d %H:%M"), "model": MODEL_NAME, "index": index_fingerprint(),
           "code": code_fingerprint(), "questions": {}}
    for q in questions:
        hits = search(table, model, q["question"], max(DEFAULT_K, EXPANSION_SEEDS), q["company"])
        context = page_context(table, hits)
        out["questions"][key(q["company"], q["question"])] = {
            "id": q.get("id"), "hits": [ident(h) for h in hits], "context": [ident(c) for c in context],
            "gate": gate_scores(hits)}
    return out


def load(path: Path, table_db: Path = DB) -> dict:
    """Read a dump and refuse it unless it was recorded on this index with this retrieval code."""
    dump = json.loads(path.read_text(encoding="utf-8"))
    if dump["index"] != index_fingerprint(table_db):
        raise RuntimeError(f"{path} was recorded on index {dump['index'][:12]}, not the local one")
    if dump["code"] != code_fingerprint():
        raise RuntimeError(f"{path} was recorded with different retrieval code ({dump['code']} vs "
                           f"{code_fingerprint()}); record it again")
    return dump


def replay(dump: dict, table, company: str, question: str) -> tuple[list[dict], list[dict]]:
    """The hits and packed context recorded for this question, with their text from the index."""
    entry = dump["questions"].get(key(company, question))
    if entry is None:
        raise KeyError(f"no recorded retrieval for {company}: {question!r}")
    pages = sorted({r["page"] for r in entry["hits"] + entry["context"]})
    rows = (table.search().where("company = '" + company.replace("'", "''") + "' AND page IN ("
                                 + ", ".join(map(str, pages)) + ")").limit(100_000).select(TEXT_FIELDS).to_list())
    by_id = {(r["page"], r["chunk"]): r for r in rows}

    def rebuild(recorded: dict) -> dict:
        row = by_id[(recorded["page"], recorded["chunk"])]
        extra = {"gate": recorded["gate"]} if "gate" in recorded else {}
        return {**row, "score": recorded["score"], "sibling": recorded["sibling"], **extra}

    return [rebuild(r) for r in entry["hits"]], [rebuild(r) for r in entry["context"]]


def main() -> None:
    from retrieve.embed import load_model
    from retrieve.search import open_index
    from retrieve.store import ensure_index

    parser = argparse.ArgumentParser(description="Record retrieval for eval questions (needs the embedding model).")
    parser.add_argument("--questions", type=Path, nargs="+", required=True, help="JSONL files with company and question")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    ensure_index(DB, POINTER)
    table, model = open_index(DB), load_model()
    questions = [json.loads(line) for path in args.questions for line in path.read_text(encoding="utf-8").splitlines()
                 if line.strip()]
    started = time.perf_counter()
    dump = record(questions, table, model)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(dump, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"recorded {len(dump['questions'])} questions in {time.perf_counter() - started:.0f}s -> {args.out}")


if __name__ == "__main__":
    main()
