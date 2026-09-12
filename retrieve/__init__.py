"""Retrieval: embed chunks, store them in LanceDB, top-k search a query.

Owns Stages 4-5 (SPEC.md §4). LanceDB keeps vectors and metadata in one
embedded, file-based store, so the page number sits beside the vector and
nothing needs hosting (§5). The embedding backend (local vs API) is a
Stage 4 decision gate and is deliberately not chosen yet.
"""
