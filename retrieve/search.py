"""Search: a question in, the top-k chunks out, each with the page it cites.

Stage 5 (SPEC.md §4). The query side must mirror the index side exactly, so
this file borrows the model and the embedding function from embed.py rather
than restating them, and refuses to search an index built with another model.

Search is exact: with no approximate index on the table, LanceDB compares the
question with every stored vector. At this corpus size that costs nothing, and
it means a miss is a representation problem — the right chunk's vector does
not resemble the question's — never a search shortcut skipping it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import lancedb
from fastembed import TextEmbedding

from retrieve.embed import MODEL_NAME, TABLE_NAME, embed_texts, load_model

# bge-small-en-v1.5 was trained with this instruction in front of queries and
# nothing in front of passages. Chunks were embedded bare, so every question
# gets it here; fastembed does not add it for this model.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

DEFAULT_K = 5


def open_index(db_path: Path) -> lancedb.table.Table:
    """Open the chunks table, refusing one built with a different model.

    Vectors from two models share no geometry. A question embedded with one
    and searched against the other still returns k chunks with ordinary-
    looking scores, none of them relevant. The model name stored at embed
    time turns that silent failure into an error.
    """
    table = lancedb.connect(str(db_path)).open_table(TABLE_NAME)
    built_with = (table.schema.metadata or {}).get(b"embedding_model", b"").decode()
    if built_with != MODEL_NAME:
        raise RuntimeError(
            f"{db_path} was embedded with {built_with or 'an unrecorded model'}, not {MODEL_NAME}; "
            "re-run python -m retrieve.embed"
        )
    return table


def search(table: lancedb.table.Table, model: TextEmbedding, question: str, k: int = DEFAULT_K) -> list[dict]:
    """Return the k chunks closest to the question, best first, with their similarity."""
    vector = embed_texts(model, [QUERY_INSTRUCTION + question])[0]
    hits = (
        table.search(vector)
        .distance_type("cosine")
        .limit(k)
        .select(["company", "fiscal_year", "page", "chunk", "text"])
        .to_list()
    )
    results = []
    for hit in hits:
        # LanceDB reports cosine distance; 1 - distance is cosine similarity,
        # which reads the natural way round: higher is closer, 1.0 is identical.
        score = 1 - hit.pop("_distance")
        results.append({**hit, "score": score})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Top-k search over the chunk index.")
    parser.add_argument("question", help="a question about the filing, in plain English")
    parser.add_argument("-k", type=int, default=DEFAULT_K, help="how many chunks to return")
    parser.add_argument("--db", type=Path, default=Path("data/lancedb"), help="LanceDB directory from retrieve.embed")
    args = parser.parse_args()

    table = open_index(args.db)
    for rank, hit in enumerate(search(table, load_model(), args.question, args.k), start=1):
        opening = hit["text"].split("\n")[0]
        print(f"{rank}. p{hit['page']} chunk {hit['chunk']}  {hit['score']:.3f}  {opening[:90]}")


if __name__ == "__main__":
    main()
