# Corpus sources

Folio does not commit source PDFs (SPEC.md §7): the code ships, the data
doesn't. The filings below are public statutory documents. This file records where to obtain each one and a
checksum so you can confirm you have the exact file the index was built from.

**To rebuild the corpus:** download each PDF into this `corpus/` folder under
the filename in the table, then verify its SHA-256 (command at the bottom).

| Company | Exchange ID | Fiscal year | Document | Filename | SHA-256 |
|---|---|---|---|---|---|
| Hindustan Construction Company (HCC) | BSE 500185 · NSE HCC | FY25 (Apr 2024 – Mar 2025) | Annual Report 2024-25 | `0_14711100_1755498593_HCC_Annual_Report_2025.pdf` | `9417307d85a84e78963b0cde625d3337efc2c8357affec37bd3832abae764a26` |
| Chambal Fertilisers and Chemicals (CHAMBAL) | CIN L24124RJ1985PLC003293 | FY25 (Apr 2024 – Mar 2025) | Annual Report 2024-25 (40th) | `Annual-Report-for-the-Financial-Year-2024-2025.pdf` | `165dfdf87214cb36a3c51506468e2fdc168b2079eae3af0acd77ebb9c2ce7cb7` |
| Navneet Education (NAVNEET) | BSE 508989 · NSE NAVNETEDUL | FY25 (Apr 2024 – Mar 2025) | Annual Report 2024-25 (39th) | `annual-report-24-25.pdf` | `ed2eca6940e5e07d5e2784e71104b029e77a560dc9545fe78856677279116e48` |

## Where to obtain
- **Company investor-relations pages** — hccindia.com, chambalfertilisers.com, navneet.com (Investors → Annual Reports); each company's own primary source.
- **BSE** — https://www.bseindia.com (Corporate Announcements / Annual Reports; scrip code 500185).
- **NSE** — https://www.nseindia.com (symbol HCC).

**Exact download URLs (each verified by re-downloading and matching SHA-256
against the local copy and the checksum above — all three match, so these are
the exact files the index was built from):**

- HCC, verified 2026-09-21 —
  <https://hccindia.com/uploads/reports/0_14711100_1755498593_HCC_Annual_Report_2025.pdf>
- Chambal Fertilisers, verified 2026-09-22 —
  <https://www.chambalfertilisers.com/pdf/Annual-Report-for-the-Financial-Year-2024-2025.pdf>
- Navneet Education, verified 2026-09-22 —
  <https://navneet.com/annual-report-24-25.pdf>

These links are load-bearing: the repository ships text derived from these
documents (SPEC.md §7), and the demo attributes each one here.

`corpus.json` beside this file carries the same identities, checksums and URLs
in machine-readable form; `python -m ingest.build` verifies every checksum
before it ingests anything.

## Verify a download
```
shasum -a 256 corpus/0_14711100_1755498593_HCC_Annual_Report_2025.pdf
```
The output must match the SHA-256 in the table above.
