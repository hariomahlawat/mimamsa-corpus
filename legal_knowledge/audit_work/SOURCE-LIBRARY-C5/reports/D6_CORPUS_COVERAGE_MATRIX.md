# D6. Corpus coverage matrix

**Register:** `registers/corpus_crosswalk.csv`, 1,113 rows, with figures in `registers/coverage_summary.json`. Rows cover:
- every citation item that WS-D `canonical_coverage.csv` parsed from the **658 KB records**, plus one `NO_CITATION` row for each of the 77 records that cite nothing;
- one row for each of the **53 curated cases**, for the case's own source judgment.

The crosswalk is **technical**. It says whether authoritative text is *held* for a citation. It says nothing about whether the record is legally correct, and every row is `NOT_REVIEWED`.

## Classes
- **EXACT_ANCHOR:** the source is identified, a provision locator is present, and a *primary* copy is held with documented provenance. For the Army Rules this applies only to rules that have no recorded amendment and no reserved conflict. The anchor is to the held version: **currency is not implied**, because the Army Rules chain is incomplete.
- **PARTIAL_MATCH:** the source is identified but one of these applies:
  - only a compilation or a copy with undocumented provenance is held;
  - the identity is inferred;
  - there is no locator;
  - the cited rule was amended after 1954, or is reserved.
- **MISSING_EVIDENCE:** either the citation is not identified to a C5 source (`UNMAPPED`), the source is identified but not held, or the record cites nothing.

## Results
| Measure | EXACT_ANCHOR | PARTIAL_MATCH | MISSING_EVIDENCE |
| --- | --- | --- | --- |
| KB citation items (1,060) | 42 | 652 | 366 |
| Case records (53) | 6 | 7 | 40 |

| KB records (658), by best anchor | Count |
| --- | --- |
| All items exact | 10 |
| Some exact | 30 |
| No exact anchor | 618 |

The 42 exact KB anchors all point to Army Rules 1954 provisions with no recorded amendment, reserved conflict or amendment hint in any register, for example r.180, r.181, r.185 and r.39. The Army Rules chain is still incomplete: 11 instruments have unknown provisions affected, so these anchors are to the as-notified 1954 text. They are not anchors to current text. Independent review RV-31 removed r.95 because of the AR-039 hint. Exact anchors are impossible for:
- **Army Act citations (190 items):** no Gazette text is held, only the India Code compilation.
- **AFT Act (89), BNSS (50) and BSA (64):** compilations only.
- **Pension records (PEN module, M08):** 75 of 96 have only MISSING items, because PRA 2008, ER and GMO are not held.

The six exact case anchors are PPS Bedi, Virendra Kumar, Jasbir Singh, Parashotam Dass, Anvar and Arjun Panditrao: official SC copies with documented provenance. Seven case records are partial, because their official SC copies are held but their provenance is not registered: Girish Kumar (Feb), Mullikote, Dharamvir, Rajbir, Ranjit Thakur, S N Mukherjee and Navjot Sandhu. The other 40 cases have no held official copy in this index.

## Module view (KB records)
| Module | All exact | Some exact | Partial only | Missing only |
| --- | --- | --- | --- | --- |
| M03 | 2 | 0 | 53 | 0 |
| M04 | 2 | 10 | 38 | 2 |
| M05 | 1 | 17 | 58 | 2 |
| M06_M07 | 3 | 0 | 33 | 27 |
| M08 (pension) | 0 | 0 | 21 | 75 |
| M09 | 0 | 2 | 86 | 5 |
| M10 | 0 | 0 | 74 | 14 |
| M11 | 0 | 1 | 11 | 4 |
| M12 | 0 | 0 | 2 | 14 |
| M13 | 2 | 0 | 73 | 21 |
| M01, M02, M06 | 0 | 0 | 5 | 0 |

These figures are recomputed from the register by the same rule. The 77 no-citation records count as "missing only".

## What would move the matrix
- **Locating the 1978 CCCM Rules and S.O. 4010/1986** would restore the 8 items that are MISSING since RV-01.
- **Batch A (Army Act, AFT Act, BNSS and BSA Gazettes)** would turn up to about 390 PARTIAL items into candidates for exact anchors, once each has a register row and page checks.
- **Batch B (PRA 2008, ER and GMO)** would move the PEN module out of MISSING.
- **Registering the provenance of the SC copies already held** (no download needed) would lift 7 case records and their KB citations.
