"""Answer bounded fund lookups directly from verified rows and factsheet fields.

The table already contains the answer. Sending hundreds of holdings to a
generator would add truncation and transcription risk without adding evidence.
Company financial questions use the existing report Q&A through drill-down.
"""

from __future__ import annotations

import re
from datetime import date

from funds.data import fact_citation, row_citation
from gen.guardrails import REFUSAL

OUT_OF_SCOPE = re.compile(
    r"\b(?:recommend\w*|advice|buy|sell|switch|invest|best|better|should|forecast|predict\w*)\b", re.I
)


def matches_snapshot(text: str, snapshot: str) -> bool:
    """A dated question must match the date of the field actually being read."""
    day = date.fromisoformat(snapshot)
    for supplied in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text):
        if supplied != snapshot:
            return False
    # Numeric dates can use conflicting conventions; require ISO or a named
    # month rather than silently interpreting a different disclosure date.
    without_iso = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", text)
    if re.search(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", without_iso):
        return False
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    if any(int(year) != day.year for year in years):
        return False
    for month in range(1, 13):
        name = date(2000, month, 1).strftime("%B").lower()
        if re.search(r"\b" + name[:3] + r"(?:" + name[3:] + r")?\b", text) and month != day.month:
            return False
        month_pattern = name[:3] + r"(?:" + name[3:] + r")?"
        dates = re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+" + month_pattern + r"\b", text)
        dates += re.findall(r"\b" + month_pattern + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b", text)
        if any(int(value) != day.day for value in dates):
            return False
    temporal = re.sub(r"\bnet current assets\b", "", text)
    return not re.search(r"\b(?:previous|historical|today|current|now|latest|yesterday|tomorrow)\b", temporal)


def answer(question: str, fund: dict) -> str:
    """Return cited disclosed facts, or the same strict refusal as company Q&A."""
    text = question.strip().lower()
    if OUT_OF_SCOPE.search(text):
        return REFUSAL
    # Never answer a financial or historical question with a coincidentally
    # matched holding weight. Report questions belong to an explicit filing.
    if re.search(r"\b(?:regular|idcw|revenue|profit|earnings|dividend|returns?|performance|risk|tax|fy\d+|forecast)\b", text):
        return REFUSAL
    parts = []
    for key, pattern, label in (
        ("benchmark", r"\bbenchmark\b", "Benchmark"),
        ("expense_ratio", r"expense|\b(?:ter|ber)\b|cost", "Direct-plan expense ratio"),
        ("exit_load", r"exit load|redemption", "Exit load"),
    ):
        if re.search(pattern, text):
            fact = fund[key]
            value = fact['value']
            if key == "expense_ratio":
                if fact['kind'] == 'BER' and re.search(r"\b(?:total|ter)\b", text):
                    return REFUSAL
                if fact['kind'] == 'TER' and re.search(r"\b(?:base|ber)\b", text):
                    value = fact['base_value']
                    label = "Direct-plan base expense ratio"
            detail = " " + fact["definition"] if key == "expense_ratio" else ""
            if key == "expense_ratio" and value != fact['value']:
                detail = ""
            parts.append(f"{label}: {value}.{detail} As of {fund['factsheet_date']} "
                         f"{fact_citation(fund, fact)}.")
    if parts:
        if not matches_snapshot(text, fund["factsheet_date"]):
            return REFUSAL
        return "\n\n".join(parts)
    if not matches_snapshot(text, fund["portfolio_date"]):
        return REFUSAL
    if re.search(r"top\s*(?:10|ten)|largest holding", text):
        rows = sorted((r for r in fund["holdings"] if r["eligible"]), key=lambda r: r["rank"])
        if "largest" in text:
            rows = rows[:1]
    elif re.search(r"weight|holding|portfolio|allocation", text):
        rows = []
        for row in fund["holdings"]:
            name = re.sub(r"\b(?:limited|ltd)\.?", "", row["name"].lower()).strip()
            if name in text or (row.get("company") and re.search(r"\b" + re.escape(row["company"].lower()) + r"\b", text)):
                rows.append(row)
        if not rows:
            return REFUSAL
    else:
        return REFUSAL
    return "\n\n".join(f"{r['name']}: {r['weight_display']} of net assets as of "
                         f"{fund['portfolio_date']} {row_citation(fund, r)}." for r in rows)
