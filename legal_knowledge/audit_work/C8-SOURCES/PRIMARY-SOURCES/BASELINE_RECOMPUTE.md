# C8-D Task 1: baseline recompute of the KB citation figures

Recomputed offline from committed files only (`tools/build_c8_d.py`). Every figure names the file and column it comes from.

| metric | reported | recomputed | result | derivation | note |
| --- | --- | --- | --- | --- | --- |
| KB records | 658 | 658 | MATCH | count of distinct "id" in legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl (658 lines); sha256 9a8f0d193065762f = frozen_baseline_manifest.json#original_corpus_sha256.records_658 (MATCH) |  |
| Case records | 53 | 53 | MATCH | count of distinct "id" in legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl; sha256 8b8d53cd1434f7c1 = frozen manifest (MATCH) |  |
| "KB citation items" as reported | 1,060 | 1060 | MATCH | SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv: rows with knowledge_base_record_id non-empty (all rows, any relationship_type) | Figure reproduces, but it is a crosswalk ROW count, not a citation-item count: it includes the NO_CITATION placeholder rows (next two lines). |
|   of which genuine citation items (relationship_type=CITES) | 1,060 | 983 | DIFFERENCE | SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv#relationship_type=CITES; equals sum of WS-D-QUALITY/canonical_coverage.csv#n_items (983) and WS-D canonical_coverage.md "Citation items: 983 total" | DIFFERENCE: the true number of parsed KB citation items is 983. The reported 1,060 adds 77 one-per-record NO_CITATION placeholders. |
|   of which NO_CITATION placeholder rows | not stated | 77 | n/a | SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv#relationship_type=NO_CITATION (one row per record that cites nothing; canonical_coverage.csv#citation_present=NO: 77) | placeholders are counted as MISSING_EVIDENCE items in the reported 366 |
| KB exact citation anchors | 42 | 42 | MATCH | SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv#evidence_status=EXACT_ANCHOR (KB rows); anchor_copy_id: C5-SRC-P0-ARMY-RULES-1954~C1=42 | MATCH. Share of genuine citation items: 42/983 = 4.3% (not 42/1060 = 4.0%). All 42 point to the as-notified 1954 Army Rules facsimile; currency is not implied. |
| KB PARTIAL_MATCH items | 652 | 652 | MATCH | SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv#evidence_status=PARTIAL_MATCH (KB rows; all are CITES) |  |
| KB MISSING_EVIDENCE items | 366 | 366 | MATCH | SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv#evidence_status=MISSING_EVIDENCE (KB rows) | of which 289 are genuine citation items and 77 are NO_CITATION placeholders |
| KB records with no exact anchor | 618 | 618 | MATCH | records grouped by SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv#knowledge_base_record_id; class NO_EXACT_ANCHOR = no row with EXACT_ANCHOR | MATCH, but 77 of the 618 cite nothing at all; 541 records have at least one citation item and no exact anchor |
| KB records, all items exact | 10 | 10 | MATCH | same grouping; every row EXACT_ANCHOR |  |
| KB records, some items exact | 30 | 30 | MATCH | same grouping; at least one but not all rows EXACT_ANCHOR |  |
| Case records EXACT / PARTIAL / MISSING | 6 / 7 / 40 | 6 / 7 / 40 | MATCH | SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv#case_id rows (53) by evidence_status |  |
| coverage_summary.json kb items (EXACT/PARTIAL/MISSING) | 42 / 652 / 366 | 42 / 652 / 366 | MATCH | json values: {"EXACT_ANCHOR": 42, "MISSING_EVIDENCE": 366, "PARTIAL_MATCH": 652} | json agrees with the crosswalk recount |
| AUTH-LEDGER effective v0000 NO_EXACT_ANCHOR | 618 | 618 | MATCH | json value; AUTH-LEDGER effective state v0000 has not changed the C5 coverage |  |

## Difference found

- **1,060 is not a citation-item count.** It is the number of KB rows in `SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv`, which includes one `NO_CITATION` placeholder row for each of the 77 records that cite nothing. The number of parsed KB citation items is **983** (CITES rows; equal to the sum of `WS-D-QUALITY/canonical_coverage.csv#n_items`, and to the "983 total" already stated in `WS-D-QUALITY/canonical_coverage.md`).
- Consequently the reported **366 MISSING items** contain 77 placeholders; genuine missing citation items are **289**. The exact-anchor share is 42/983 (4.3%), not 42/1,060 (4.0%).
- **618 records with no exact anchor** reproduces, but 77 of them cite nothing at all; 541 records have at least one citation item and no exact anchor.
- All other figures (42, 652, 658, 53, 10/30, 6/7/40) reproduce exactly. KB and case-file hashes equal the frozen C5 baseline manifest.

No register was changed. The correction is a labelling one: future reports should say "1,060 crosswalk rows (983 citation items + 77 no-citation placeholders)".
