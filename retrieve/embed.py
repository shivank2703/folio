"""Embedding: chunks in, a LanceDB table of vectors out.

Stage 4 decision (SPEC.md §5): BAAI/bge-small-en-v1.5, run through
fastembed's ONNX export instead of sentence-transformers. The public demo
runs on 2 CPU cores; ONNX Runtime needs no PyTorch, so the deployed image
stays small and a Space waking from sleep loads a 67 MB model, not a
framework. Measured before choosing: the largest chunk is 393 tokens under
this model's tokenizer, inside its 512 limit, so no chunk is truncated.

fastembed serves Qdrant's quantized export of the model
(qdrant/bge-small-en-v1.5-onnx-q). Quantization trades a little accuracy for
size and speed, and the benchmark scores on BAAI's model card describe the
original weights — so Stage 5's smoke test, not the card, is the quality check.

Output: data/lancedb/, table "chunks", one row per chunk: its vector plus the
{company, fiscal_year, page, chunk, tokens, text} it came from.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import lancedb
import numpy as np
import pyarrow as pa
from fastembed import TextEmbedding

# The one place the model is named. Stage 5 must embed questions with this
# same model: vectors from two models share no geometry, so a mismatched
# query returns confident nonsense instead of an error.
MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Width of every vector this model produces. The table's vector column is
# declared with exactly this width.
DIMENSION = 384

TABLE_NAME = "chunks"

# Downloaded model files sit in data/ with the other disposable artifacts
# rather than the OS temp directory, which macOS clears — so a re-run finds
# them instead of quietly downloading 67 MB again.
MODEL_CACHE = Path("data/models")


def load_chunks(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_model() -> TextEmbedding:
    """Load the ONNX model, downloading it into MODEL_CACHE on first use."""
    return TextEmbedding(model_name=MODEL_NAME, cache_dir=str(MODEL_CACHE))


def embed_texts(model: TextEmbedding, texts: list[str]) -> np.ndarray:
    """Return one unit-length float32 vector per text, shape (len(texts), DIMENSION).

    Chunk text is embedded exactly as chunk.py wrote it, inherited title, unit
    and header lines included: the title is what separates a standalone
    balance-sheet chunk from its consolidated twin, whose row labels match.
    No instruction prefix here — bge puts its instruction on queries, not on
    the passages being searched.
    """
    vectors = np.array(list(model.embed(texts)), dtype=np.float32)
    if vectors.shape != (len(texts), DIMENSION):
        raise ValueError(f"expected {(len(texts), DIMENSION)} vectors, got {vectors.shape}")
    # At unit length, cosine similarity equals the dot product and L2 distance
    # ranks results in the same order, so the distance metric chosen at search
    # time cannot quietly change which chunks come back first.
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def to_arrow(chunks: list[dict], vectors: np.ndarray) -> pa.Table:
    """Pair each chunk with its vector in a typed Arrow table.

    The schema is declared, not inferred: LanceDB searches a column as
    vectors only if it is a fixed-width list of floats, and an inferred
    schema would produce a variable-length list. The model name rides in
    the schema metadata so the query side can check it before searching.
    """
    schema = pa.schema(
        [
            pa.field("vector", pa.list_(pa.float32(), DIMENSION)),
            pa.field("text", pa.string()),
            pa.field("company", pa.string()),
            pa.field("fiscal_year", pa.string()),
            pa.field("page", pa.int32()),
            pa.field("chunk", pa.int32()),
            pa.field("tokens", pa.int32()),
        ],
        metadata={"embedding_model": MODEL_NAME},
    )
    columns = [pa.FixedSizeListArray.from_arrays(pa.array(vectors.ravel(), pa.float32()), DIMENSION)]
    columns += [pa.array([chunk[name] for chunk in chunks], schema.field(name).type) for name in schema.names[1:]]
    return pa.Table.from_arrays(columns, schema=schema)


def write_index(table: pa.Table, db_path: Path) -> None:
    """Replace the chunks table with this run's rows.

    Overwrite, never append: each run embeds the whole chunks file, so the
    table always holds one model's vectors for one set of chunks. An append
    would keep the previous run's rows, and every search hit would come
    back twice.
    """
    db = lancedb.connect(str(db_path))
    db.create_table(TABLE_NAME, data=table, mode="overwrite")


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed chunks with bge-small-en-v1.5 into LanceDB.")
    parser.add_argument(
        "chunks", type=Path, nargs="?", default=Path("data/chunks.jsonl"), help="chunk records from ingest.chunk"
    )
    parser.add_argument(
        "--db", type=Path, default=Path("data/lancedb"), help="LanceDB directory; generated and gitignored"
    )
    args = parser.parse_args()

    chunks = load_chunks(args.chunks)
    model = load_model()
    started = time.perf_counter()
    vectors = embed_texts(model, [chunk["text"] for chunk in chunks])
    seconds = time.perf_counter() - started
    write_index(to_arrow(chunks, vectors), args.db)

    print(f"{len(chunks)} chunks -> {args.db}/{TABLE_NAME}.lance ({MODEL_NAME}, {DIMENSION} dims)")
    print(f"  embedding took {seconds:.1f}s ({len(chunks) / seconds:.0f} chunks/s on this machine)")


if __name__ == "__main__":
    main()
