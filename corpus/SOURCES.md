# Corpus sources

Praman does not commit source PDFs (SPEC.md §7) — same principle as the v4
fetcher: the code ships, the data doesn't. The filings below are public
statutory documents. This file records where to obtain each one and a
checksum so you can confirm you have the exact file the index was built from.

**To rebuild the corpus:** download each PDF into this `corpus/` folder under
the filename in the table, then verify its SHA-256 (command at the bottom).

| Company | Exchange ID | Fiscal year | Document | Filename | SHA-256 |
|---|---|---|---|---|---|
| Hindustan Construction Company (HCC) | BSE 500185 · NSE HCC | FY25 (Apr 2024 – Mar 2025) | Annual Report 2024-25 | `0_14711100_1755498593_HCC_Annual_Report_2025.pdf` | `9417307d85a84e78963b0cde625d3337efc2c8357affec37bd3832abae764a26` |

## Where to obtain
- **HCC investor relations** — https://www.hccindia.com (Investors → Annual Reports); the company's own primary source.
- **BSE** — https://www.bseindia.com (Corporate Announcements / Annual Reports; scrip code 500185).
- **NSE** — https://www.nseindia.com (symbol HCC).

**Exact download URL (verified 2026-09-21):**
<https://hccindia.com/uploads/reports/0_14711100_1755498593_HCC_Annual_Report_2025.pdf>

Verified by downloading it and comparing SHA-256 against the local copy and
the checksum in the table: all three match, so this is the exact file the
index was built from. This link is load-bearing — the repository ships text
derived from this document (SPEC.md §7), and the demo attributes it here.

## Verify a download
```
shasum -a 256 corpus/0_14711100_1755498593_HCC_Annual_Report_2025.pdf
```
The output must match the SHA-256 in the table above.
