"""Retrieval: embed chunks, store them in LanceDB, top-k search a query.

Owns Stages 4-5 (SPEC.md §4). LanceDB keeps vectors and metadata in one
embedded, file-based store, so the page number sits beside the vector and
nothing needs hosting (§5). The Stage 4 gate chose bge-small-en-v1.5 run
through ONNX Runtime (embed.py); search must embed queries with that same
model.
"""
