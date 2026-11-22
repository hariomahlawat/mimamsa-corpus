# Proposed citation-code register v4 (WS-D, cycle 2): PROPOSAL ONLY

**Status:** proposal for coordinator decision (OQ-D-003). PILOT-01's frozen `registers/source_code_resolution_v3.csv` (sha256 `40b18c3d…`) is not modified. No resolution class, identity, evidence, URL or hash changes. This is not a legal determination.

## Defect D-WSD-001: root cause
| Grammar form | Example | v2 inventory | v3 inventory | v3 register rows |
| --- | --- | --- | --- | --- |
| structured `{'source_id': ...}` | KB-001 | yes | yes | counted |
| bracket with locator `[CODE: loc]` | `[SRC-AA: ss 2, 101-106]` | yes | yes | counted |
| **bare bracket `[CODE]`** | `[SRC-AA]; [SRC-AR]` (COI-002) | **no** | yes | new codes got rows (`v3-new`); **v2-carried rows not recounted** |
| V-series `V#-S##` | `V6-S03` | yes | yes | counted |
| **leading digest code** | `SC_VK paras 9-13` (J-02) | **no** | yes | as above |
| `sources` field | EV records | yes | yes | counted |

v3 refreshed `forms_used` for every row (verified: 87/87 match the forms present in the KB) but kept the v2 `n_records`/`records_using` on the 78 rows with `inventory_source = v2`. As a result, 8 codes omit **14 record links** (11 bare-bracket, 3 leading). The cycle-1 report said 15; that figure was wrong and is corrected here.

| Code | v3 n | v4 n | Added records | Missed form |
| --- | --- | --- | --- | --- |
| SC_GILL | 1 | 2 | J-03 | leading |
| SC_PPS | 2 | 3 | J-01 | leading |
| SC_VK | 5 | 6 | J-02 | leading |
| SRC-AA | 19 | 21 | COI-002, COI-043 | bracket_bare |
| SRC-AR | 49 | 52 | COI-002, COI-043, COI-044 | bracket_bare |
| SRC-AR185 | 4 | 5 | COI-046 | bracket_bare |
| SRC-JETHI | 5 | 7 | COI-039, COI-041 | bracket_bare |
| SRC-VIR | 7 | 10 | COI-039, COI-041, COI-044 | bracket_bare |

**Impact:** classification is unaffected (72/87 confirmed, 3 co-citation, 12 unresolved). Usage-weighted metrics were already recomputed from the KB by `build_code_inventory.py` (681 links), so the published 87.2%/95.4% figures are unaffected. Only readers of the register's own usage columns were misled.

## Files
- `source_code_resolution_v4_proposed.csv`: all 87 v3 rows. `n_records`/`records_using` are recounted for every code; all other v3 columns are unchanged. Appended columns: `change_vs_v3`, `usage_recount_basis`.
- `source_code_resolution_v4_diff.csv`: cell-level diff against v3 (16 cells, 8 codes, additions only).
- Generator: `../scripts/build_register_v4.py` (deterministic, asserts the v3 hash). Guard: `tests/test_legal_audit_register_v4.py`.

## If accepted
The coordinator would publish it as a new versioned register and point `build_code_inventory.py`/tests at it in a separate reviewed change. `test_legal_audit_citation_register.py` then keeps pinning v3's known stale set, and v4 is guarded to have none.
