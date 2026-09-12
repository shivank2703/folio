"""Ingestion pipeline: PDF -> page-faithful text -> chunks.

Owns Stages 2-3 (SPEC.md §4): PyMuPDF page extraction, then ~200-token
chunking. The invariant this package must protect: every chunk that leaves
here carries {company, fiscal_year, page}, so the page citation survives
all the way to the final answer. Metadata is written from day one because
v2 (statement-scope) and v4 (multi-year) depend on it (CLAUDE.md).
"""
