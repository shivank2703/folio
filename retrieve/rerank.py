"""Rerank: read each candidate against the question, and gate refusals on that reading.

Accurate step (SPEC.md §4). Hybrid search ranks chunks by two proxies, vector
closeness and shared words. Neither reads the question and the chunk
together, which is why similarity stopped separating answerable questions from
unanswerable ones: a chunk about advertising spend is close to a question about
television advertising whether or not it says "television". A cross-encoder
takes the question and one chunk as a single input and scores whether that
chunk answers it.

Two jobs, one score. The top candidates are reordered by it, so the pages the
model reads are chosen by the stronger reader; and the best score becomes the
refusal gate in place of the 0.67 similarity floor, fitted on half the eval
set and reported on the other half (evals/fit_gate.py).

The model runs through fastembed on ONNX Runtime, like the embedder: SPEC.md
§5 named a sentence-transformers cross-encoder, but that pulls in PyTorch,
which the Stage 4 decision kept off a free 2-core host.
"""

from __future__ import annotations

from fastembed.rerank.cross_encoder import TextCrossEncoder

from retrieve.embed import MODEL_CACHE

# The candidates measured by evals/fit_gate.py. Both are small, Apache-2.0
# and run on CPU; bge-reranker-base (1 GB) would not fit beside the app on
# Community Cloud, and jina's multilingual reranker is non-commercial.
RERANK_MODELS = ("Xenova/ms-marco-MiniLM-L-6-v2", "jinaai/jina-reranker-v1-tiny-en")
RERANK_MODEL = RERANK_MODELS[0]

# How many fused candidates the cross-encoder reads. It costs one model pass
# per candidate, so this is the latency knob; 20 is the depth the smoke test
# already treats as "found at all".
CANDIDATES = 20


def load_reranker(model_name: str = RERANK_MODEL) -> TextCrossEncoder:
    """Load the ONNX cross-encoder, downloading it beside the embedder on first use."""
    return TextCrossEncoder(model_name=model_name, cache_dir=str(MODEL_CACHE))


def rerank(reranker: TextCrossEncoder, question: str, hits: list[dict]) -> list[dict]:
    """The same hits, best first by cross-encoder score, each carrying that score as "rerank".

    The question goes in as asked, without the fiscal-year expansion: that
    expansion exists to make keyword search meet "As at March 31, 2025", while
    a cross-encoder reads "FY25" and the date as the same thing or not at all,
    and appended dates would only dilute the question it is judging.
    """
    scores = list(reranker.rerank(question, [hit["text"] for hit in hits]))
    scored = [{**hit, "rerank": float(score)} for hit, score in zip(hits, scores)]
    return sorted(scored, key=lambda hit: hit["rerank"], reverse=True)
