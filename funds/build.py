"""Build reproducible public snapshots from verified monthly disclosure files.

Source-specific row ranges are reviewed against the original workbook. A new
month is a new review, not a silent refresh that assumes an unchanged layout.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from funds.data import validate
from funds.xlsx import read_sheet


def build(config: dict, root: Path = Path("data/funds")) -> dict:
    fund = {k: v for k, v in config.items() if k not in ("layout", "companies")}
    for source in fund["sources"].values():
        path = root / source["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"Source checksum mismatch: {source['file']}")
    layout = config["layout"]
    rows = read_sheet(root / fund["sources"]["portfolio"]["file"], layout["sheet"])
    for cell, expected in layout["checks"].items():
        import re
        col, number = re.fullmatch(r"([A-Z]+)(\d+)", cell).groups()
        if rows[int(number)].get(col) != expected:
            raise ValueError(f"Disclosure layout changed at {cell}")
    holdings = []
    for section in layout["sections"]:
        for number in range(section["start"], section["end"] + 1):
            row = rows[number]
            raw = row[layout["weight"]]
            # The issuer's '$0.00' explicitly means less than 0.005%; it is
            # not a measured zero and must remain visible as a bound.
            weight = 0.0 if raw == "$0.00" else float(raw)
            isin = row.get(layout["isin"], "")
            holdings.append({"name": row[section.get("name", layout["name"])], "isin": isin,
                             "weight_pct": weight,
                             "weight_display": "<0.005%" if raw == "$0.00" else f"{weight:.2f}%",
                             "asset_type": section["asset_type"], "rank": None,
                             "eligible": False, "company": config["companies"].get(isin),
                             "sheet": layout["sheet"], "row": number})
    equity = sorted((r for r in holdings if r["asset_type"] == "domestic equity"),
                    key=lambda r: (-r["weight_pct"], r["row"]))
    for rank, row in enumerate(equity, 1):
        row.update(rank=rank, eligible=rank <= 10)
    fund["holdings"] = holdings
    validate(fund)
    return fund


def main() -> None:
    configs = json.loads(Path("corpus/funds-sources.json").read_text())
    funds = [build(config) for config in configs]
    Path("corpus/funds.json").write_text(json.dumps(funds, ensure_ascii=False, indent=2) + "\n")
    print(f"Verified {len(funds)} funds, {sum(len(f['holdings']) for f in funds)} disclosure rows")


if __name__ == "__main__":
    main()
