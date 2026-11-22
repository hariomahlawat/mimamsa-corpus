# Review fixes, 2026-11-22: four Codex P2 findings on WS-D-owned code

Method for each defect:
1. Add a regression test that reproduces the reported case.
2. Run it on the unfixed code and record the failing assertion.
3. Fix.
4. Run the same test, now passing.

All tests are in `tests/test_legal_audit_review_fixes.py` (10 tests). Results:
- Before the fix (unfixed code; scratch logs `fixes_before.log`, `fix2_before.log`): 9 FAIL, plus 1 genuine-case control that passes before and after.
- After the fix: 10/10 OK, and the full audit suite is 179 OK.

For defect 1, the original logic was first moved into a helper with no change in behaviour, `coverage_scorecard.assess_plain_segment` (outputs byte-identical, checked with `cmp`), so that it could be tested directly.

Fix commit: see "Commits" at the end.

## (1) PR #18: plain-text segments kept only their first instrument (`coverage_scorecard.py` `toks[:1]`)
| Test | Before (failing assertion) | After |
| --- | --- | --- |
| `Fix1InstrumentPerLocator.test_adm_jd_02_rule_14_belongs_to_army_rules_not_army_act` | `AssertionError: Lists differ: ['19', '14', '122'] != ['19']`: Army Rules r14 and §122 were counted as Army Act s14/s122 | ok: AA s19; AR r14; `§122` recorded as AMBIGUOUS (section locator under an AR context), not counted |
| `Fix1InstrumentPerLocator.test_v7_wf_12_every_instrument_assessed` | `AssertionError: Lists differ: ['AFT Act'] != ['AFT Act', 'Constitution']` | ok: both assessed; Constitution has no crawler doc, so V7-WF-12 is no longer "every statute instrument searchable" |

**Fix.** A shared parser, `build_plaintext_index.instrument_locators()`, keeps every instrument in a segment. Each locator binds to the instrument named most recently before it in the text. A unit that does not fit that instrument is recorded as AMBIGUOUS, never reassigned. Continuation segments continue the last instrument of their context segment, and none if that segment was a case.

Both the scorecard and the index now use the parser. The index has a new column, `instrument_locators`.

## (2) PR #18: PAGE_IMAGE_READING passed with an unregistered check ID when `copy_fidelity` was not PAGE_IMAGE_CHECKED
| Test | Before | After |
| --- | --- | --- |
| `Fix2PageImageReadingRegisteredCheck.test_page_image_reading_with_nonexistent_check_is_rejected`: controls-v2 GOVERNMENT_COMPILATION RULE source, `copy_fidelity` HASH_ONLY, proof PAGE_IMAGE_READING, render hash, `page_image_check_id` "nonexistent" | `AssertionError: True is not false : PAGE_IMAGE_READING with page_image_check_id 'nonexistent' was accepted` | ok: "PAGE_IMAGE_READING requires page_image_check_id to be exactly a registered check_id (got 'nonexistent')" |

**Fix.** `validate.py source_integrity` now applies this check whatever the `copy_fidelity` value, and in every batch. No frozen source carries `proof_type`, so PILOT-01 and R23 are unaffected.

## (3) PR #22: check-ID matching stripped workstream prefixes (`PIC_TOKEN`)
| Test | Before | After |
| --- | --- | --- |
| `Fix3CompleteCheckIds.test_prefixed_id_not_masked_by_unprefixed_entry` | `AssertionError: True is not false : WSZ-PIC-900 was resolved through an unrelated unprefixed PIC-900` | ok: rejected, citing WSZ-PIC-900 |
| `Fix3CompleteCheckIds.test_prefixed_id_resolves_to_its_own_entry` | `AssertionError: False is not true : [... page_image_check_id cites PIC-901, absent from every page_image_checks register]` | ok |
| `Fix3CompleteCheckIds.test_check_provenance_does_not_strip_prefixes` | `AssertionError: Lists differ: [] != ['IMG-2']`: WSD-PIC-5 was masked by PIC-5 | ok: IMG-2 raised |

**Fix.** Both `PIC_TOKEN` (validator) and `CHECK_ID` (`check_provenance.py`) now match the complete ID: `(?<![A-Za-z0-9-])(?:WS[A-Z]-)?PIC-\d+(?!\d)`. The ID is resolved against register rows that carry exactly that ID. The validator's register set now also includes `identity_transcription_register*.csv` (WS-A's WSA-PIC IDs).

## (4) PR #22: manual_supported evidence accepted any check that had some render
| Test | Before | After |
| --- | --- | --- |
| `Fix4RelationBoundToCheckRecord.test_other_document_check_with_fabricated_render_is_rejected` (PIC-10, a 1954 Gazette page; render `f`*64) | `AssertionError: True is not false : relation accepted with PIC-10 (a 1954 Gazette page) and a fabricated render hash` | ok: rejected (the check is for another document) |
| `Fix4RelationBoundToCheckRecord.test_fabricated_render_on_the_right_check_is_rejected` (PIC-02, MML 2.pdf; render `f`*64) | `AssertionError: True is not false` | ok: "render_sha256 does not equal the registered render hash of check PIC-02" |
| `Fix4RelationBoundToCheckRecord.test_cross_document_check_with_its_real_render_is_rejected` (PIC-01, India Code compilation, real render) | `AssertionError: True is not false : PIC-01 is an India Code compilation page, not MML 2.pdf` | ok: rejected |
| `Fix4RelationBoundToCheckRecord.test_genuine_mml_check_with_its_real_render_passes` (control) | ok | ok |

**Fix.** `validate.py page_image_check_records()` keeps the full check record (document, document SHA-256, page, render PNG SHA-256, register file). `relation_checks` now requires all three of:
- the check's document equals the relation's `mml_file`;
- the check's document hash equals the MML manifest hash for that file;
- the relation's `render_sha256` equals the check's registered render.

**Fixture correction.** The earlier valid-relation fixture in `test_legal_audit_provenance_controls.py` was itself an instance of this defect: PIC-01, an India Code page, with a placeholder render. It now uses PILOT-01 PIC-02 (MML 2.pdf p.152) with its real render hash. The negative cases are unchanged.

## Regenerated outputs (recomputed, not assumed)
**`plaintext_citation_index.csv`**
- New column `instrument_locators`; 269 records and 403 segments, both unchanged in number.
- One ambiguous locator: ADM-JD-02 `§122`.

**`coverage_scorecard.json/.md`**

| Measure | Before | After |
| --- | --- | --- |
| Statute instrument mentions searchable (key renamed from per-segment) | 251/261 segments | 254/265 mentions |
| Plain-text records with every statute instrument searchable | 169/178 | 168/178 (V7-WF-12: Constitution not in corpus) |
| Cited Act sections present | 448/448 | 446/446 (AR r14 no longer counted as AA s14; §122 ambiguous, not counted) |
| Whole KB, plain-text part | 169/658 | 168/658 |

Code-level figures are unchanged: 52/87 codes, 520/681 links, 279/389 coded records, 279/658 KB.

**`coverage_reconciliation.*`** (WS-C @ba3d370e): agreement 556/658 (84.5%), up from 554. All 102 disagreements are explained and none is unexplained. Rule counts:

| Rule | Records |
| --- | --- |
| R1 co-citation | 39 |
| R2 no pinpoint | 30 |
| R7 plain statute list | 19 |
| R6 plain case citation | 11 |
| R8 no-citation definition | 11 |
| R4 placeholder | 6 |
| R3 structural flag | 3 |
| R11 plain statute name in a coded record | 3 |
| R9 unresolved code | 2 |

**Other outputs**
- `relation_graph_summary.json/report.md`: the page-image check count is now 36 (was 29), catching up with registers the coordinator merged earlier. There are no dangling edges.
- `citation_resolution_score`: unchanged (it does not use plain-text parsing).
- Provenance baseline: unchanged (3 known violations, none new).
