"""Validate public snapshots and resolve the deliberately limited report coverage."""

from __future__ import annotations

import json
import math
from pathlib import Path
from datetime import date
import re
from urllib.parse import urlsplit

CATALOG = Path("corpus/funds.json")


def validate(fund: dict) -> None:
    """Fail closed when a disclosure loses provenance, rows or ranking information."""
    for field in ("portfolio_date", "factsheet_date"):
        date.fromisoformat(fund[field])
    for source in fund["sources"].values():
        if urlsplit(source["url"]).scheme != "https" or not re.fullmatch(r"[a-f0-9]{64}", source["sha256"]):
            raise ValueError("A disclosure needs an HTTPS source and SHA-256")
    for name in ("benchmark", "expense_ratio", "exit_load"):
        fact = fund[name]
        if not fact["value"] or fact["page"] < 1:
            raise ValueError(f"Missing cited {name}")
    if fund['expense_ratio']['kind'] not in {'BER', 'TER'}:
        raise ValueError("Expense ratio must preserve the issuer's BER/TER definition")
    rows = fund["holdings"]
    if len(rows) != fund["holding_count"]:
        raise ValueError("Incomplete holdings table")
    locations = [(r["sheet"], r["row"]) for r in rows]
    if len(locations) != len(set(locations)):
        raise ValueError("Duplicate disclosure rows")
    equity = sorted((r for r in rows if r["asset_type"] == "domestic equity"),
                    key=lambda r: (-r["weight_pct"], r["row"]))
    for rank, row in enumerate(equity, 1):
        if row["rank"] != rank or row["eligible"] != (rank <= 10):
            raise ValueError("Only the top ten domestic equities are eligible")
    for row in rows:
        if row["eligible"] and not re.fullmatch(r"[A-Z0-9]{2,20}", row.get("company") or ""):
            raise ValueError("A top-ten holding needs a reviewed company mapping")
        if not math.isfinite(row["weight_pct"]) or row["row"] < 1:
            raise ValueError("Invalid holding weight or source row")
        if row["asset_type"] != "domestic equity" and (row["eligible"] or row["rank"] is not None):
            raise ValueError("Non-equity instruments cannot enter report coverage")
    # Every percentage is rounded by the issuer. The tolerance is half a
    # unit in its last decimal place per row, not a blanket missing-cash plug.
    tolerance = len(rows) * 0.005 + 0.005
    if abs(sum(r["weight_pct"] for r in rows) - fund["disclosed_total_pct"]) > tolerance:
        raise ValueError("Holdings do not reconcile to the disclosed total")


def load_funds(path: Path = CATALOG) -> list[dict]:
    funds = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    for fund in funds:
        validate(fund)
    return funds


def coverage(row: dict, filings: list[dict]) -> dict | None:
    """A top-ten selection is not indexed until its exact company is in the corpus."""
    if not row["eligible"] or not row.get("company"):
        return None
    return next((f for f in filings if f["company"] == row["company"]), None)


def fact_citation(fund: dict, fact: dict) -> str:
    return f"[factsheet page {fact['page']}]({fund['sources']['factsheet']['url']}#page={fact['page']})"


def row_citation(fund: dict, row: dict) -> str:
    return f"[{row['sheet']} row {row['row']}]({fund['sources']['portfolio']['url']})"
