# ACQ-03 pinned candidates: summary (preparation only; nothing downloaded)

**Source file:** `acq03_pinned_candidates.csv`, with one row per file to fetch.

- 44 rows in total: **40 with a pinned HTTPS URL** (37 archive.org, 3 India Code) and **4 with no lawful online source known**.
- Expected size of all URL rows: **78,362,842 bytes (≈74.7 MiB)**.
- Checksums come from read-only metadata requests made on 2026-11-22, all logged in `network_requests_log.tsv`:
  - archive.org `/metadata/<identifier>` (`source=original` PDF chosen; one item offers only a derivative PDF and is marked);
  - India Code `items/<uuid>/bundles` (ORIGINAL bundle).
- **Overlap:** no URL is in ACQ-01 (`origin/claude/acq-01-config`: `sources.archive` and `sources.official_instruments`) or in ACQ-02 (`origin/claude/acq-02-config`: `sources.archive_acq02`).
  - Exception at document level: ACQ03-016 (archive.org 19490.pdf) is the same Act 37/1992 file as ACQ-01's India Code bitstream 7a05a1f5. It is optional (owner's choice).

| Batch | Rows | With URL | Hosts | Expected bytes | What it would close |
| --- | --- | --- | --- | --- | --- |
| B1 hints | 9 | 9 | archive.org | 4,566,403 | AR-012, AR-013, AR-015, AR-041..046; GAP-04; OQ-A-06 (completeness of the 1966–1974 chain) |
| B2 OCR-only instruments | 5 | 5 | archive.org | 1,457,261 | AR-002..005, AR-032; GAP-05 (LOCATED_UNVERIFIED → image-checked) |
| B3 Acts | 4 | 4 | archive.org | 3,807,817 | AA-04, AA-08 (optional), AA-09, AA-11; GAP-08, GAP-09; OQ-A-05 |
| B4 non-archive sources | 11 | 7 | archive.org (7); none (4) | 3,913,623 | Located this cycle: AA-00 (probable), AA-01, AA-02, AA-05, AA-07 (Act + commencement), AA-10; GAP-06..08; OQ-A-03, OQ-A-04. **No source known:** E-7/1960 (AR-001, GAP-01), after 06-06-2022 (AR-036, GAP-03; egazette TLS fails, not bypassed), S.R.O. 258/2002 (AR-030, GAP-02), Army Act 1950 as enacted (AA-00, GAP-06) |
| B5 AFT rules | 6 | 6 | archive.org (3), indiacode.gov.in (3) | 53,992,172 | GAP-11; OQ-A-08, OQ-A-09; OQ-D-005 ("Rule 4-12" in V7-T01..T07). The India Code `aft_1.pdf` alone is 46.8 MB |
| C2 pre-1960 and Mar–Apr 1964 | 9 | 9 | archive.org | 10,625,566 | AR-037..040; GAP-13; GAP-14; OQ-A-11 / OQ-C-06 (r.187(1) "12th March, 1964"). The 07-03-1964 issue is 8.7 MB |

## Execution conditions (each needs owner approval)
1. A separate crawler-config PR pinning these URLs, stacked after PR #8 and PR #17, without editing their lists.
2. Dry run, then fetch.
3. Reject any file whose size or MD5 differs from `expected_*`, and report it.
   - India Code may serve download-specific bytes, as seen with 1992-37.pdf. A mismatch there is reported, not accepted.
4. Re-run the page-image checks on the record copies.
5. Register updates through the coordinator.

**OCR and FTS identities in this file are locators only.** Document identity is established only by the page-image check after fetch.
