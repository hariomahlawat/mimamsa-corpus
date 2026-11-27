# Review fixes, cycle 3 (PR #25): three Codex P2 findings, owner-verified

Method for each defect:
1. Add a regression test reproducing the reported case (in `tests/test_legal_audit_review_fixes_cycle3.py`, 12 tests).
2. Run it on the unfixed code (`a1f2966f`) and record the failure.
3. Apply the minimal defensible fix.
4. Re-run; neighbouring and boundary cases are included.

Results:
- Before the fix: 7 FAIL and 5 ERROR (the ERRORs are tests that need the fixed API, which did not exist yet).
- After the fix: 12/12 OK.

## (1) Change-log rows listing several provisions registered only the first
| Test | Before | After |
| --- | --- | --- |
| `test_rr_134_135_136_all_registered` | `AssertionError: 'PCL-93-25' not found in set() : r.135 from 'rr.134,135,136' not registered` | ok |
| `test_ranges_letter_suffixes_and_lists` | `'PCL-93-34' not found in set() : r.173 from 'rr.172-176'` | ok: rr.172–176; 170A, 170B; 16A–16C; 15B |
| `test_army_act_lists` | `'AA-08-s2' not found in set()` | ok: ss.75, 76; ss.139, 151, 174; ss.4, 6, 7; ss.137/151 |
| `test_boundaries_no_invented_provisions` | `AttributeError: ... no attribute 'expand_provisions'` (the first-number logic was inline) | ok: 17 boundary strings, e.g. `r.14(4),(5)` gives [14]; `App. I Forms I,II` gives []; `rr.10–12` (en-dash) gives [10, 11, 12] |
| `test_records_citing_r135_r136_get_edges` | `KeyError: 'evidence_refs'` (no edge to r.135 or r.136 existed) | ok: V9-WF-10, V9-SC-14 and EV-006 get r.135; EV-006 gets r.136 |

**Fix.** `expand_provisions()` handles:
- comma, slash, `&` and `and` lists;
- hyphen, en-dash and `to` ranges (span of 60 or less);
- letter suffixes.

Bracketed sub-provisions never create new provisions. Every expanded number is verified against the original text (a literal token or inside an explicit range), otherwise generation stops with an error. Army Act rows that are Bills or "proposed" sections, and rows with sections "none", "unknown" or "all", are not versions.

## (2) Duplicate evidence of one amendment event treated as successive versions
| Test | Before | After |
| --- | --- | --- |
| `test_no_zero_length_or_reversed_intervals` | `AssertionError: Lists differ: [('ADM-033', 'PCL-8E-2003', '2003-06-24', ...` (49 edges with valid_to == valid_from) | ok: 0 |
| `test_r177_seed_and_change_log_are_one_event` | `KeyError: 'evidence_ids'` | ok: one event with evidence r.177@v2003, PCL-8E-2003, PCL-BL-36 |
| `test_distinct_instruments_stay_distinct_versions` | `KeyError: 'event_key'` | ok: r.193 1954, 1987 and 1993 remain separate events; 1993 groups r.193@v1993, PCL-93-38, PCL-193-1993 |
| `test_interval_guard_rejects_bad_successor` | `AttributeError: ... no attribute 'successor_bound'` | ok: returns ('', 'VALIDITY_INTERVAL_REJECTED') |

**Identity criteria for an amendment event** (documented in the script):
- the same instrument (Army Act or Army Rules);
- the same provision number;
- the same amending-instrument key, normalised as S.R.O. number(E)/year or Act number of year;
- the same publication date where both rows state one.

**How groups are handled:**
- An event keeps all its evidence references (`evidence_refs`) and uses the seed-register row as representative where one exists.
- Predecessor and successor bounds are computed over events, never over evidence rows.
- Zero-length or reversed intervals are rejected.
- A commencement date is used only if it is stated in the instrument. Conflicting stated dates within a group are flagged, not chosen between.
- Publication dates are never used as effective dates.

**Existing test extended (not weakened).** `test_stated_dates_are_the_registers_own` now checks:
- every evidence reference exists;
- `version_id` is one of the evidence references;
- `valid_from` equals a STATED effective date of one of those rows;
- the status belongs to one of them.

## (3) Coded records skipped section-level checks (canonical coverage)
| Test | Before | After |
| --- | --- | --- |
| `test_kb003_sections_bound_to_code_target` | `Regex didn't match: 'code:SRC-AA=>act-army-1950\[id\]#s79,s80,s81,s82' not found in 'code:SRC-AA=>act-army-1950[id] \| code:SRC-AR=>rules-army-rules-1954[id]'` | ok |
| `test_missing_section_file_downgrades_coded_record` (corpus with s.80 removed) | `AssertionError: 'ALL' == 'ALL' : missing Army Act s.80 file did not downgrade KB-003` | ok: not searchable ALL; ANCHORED_FULL NO |
| `test_mixed_forms_not_discarded` | `'code:AA=>act-army-1950\[id\]#s2,s79,' not found` | ok: bracket (HCE-001) and V-series pipe (AFT-001 → s.2, 3, 14, 15, 21, 22) locators bound |

**Fix.** Each locator written with a code is bound to that code's target. This covers the structured form `{'source_id': X, 'locator': L}`, bracket `[X: L]`, V-series pipe `X|L`, and the leading digest form (case paragraphs, which carry no statute sections). Plain text outside these forms goes through the shared WS-D parser:
- a statute whose corpus document equals a code target merges its locators into that code item;
- any other statute becomes its own item;
- WS-C plain names that the parser did not see are kept, never dropped.

Section-file checks now apply identically to coded and plain-text citations.

## Regenerated figures (recomputed; earlier figures not assumed)
**Canonical coverage**, denominator 658:

| Measure | Before | After |
| --- | --- | --- |
| Citation present | 581 | 581 |
| Source identified | ALL 396 · PARTLY 76 · NONE 109 · n/a 77 | ALL 396 · PARTLY 77 · NONE 108 · n/a 77 |
| Source searchable | ALL 472 · n/a 185 | ALL 473 · n/a 185 |
| ANCHORED_FULL | 362 | **362** |
| Items (identified) | 981 (716) | 983 (718) |

- Section-level checks now run on 187 coded records (658 coded section references). All exist in the crawler corpus, so ANCHORED_FULL is unchanged on recomputation.
- One record changed: CM-040 (identified NONE → PARTLY; its plain "AA/AR records" text is now assessed instead of dropped).

**Versioned edges:**

| Measure | Before | After |
| --- | --- | --- |
| Edges | 471 | 380 |
| Record-provision citations with registered versions | 325 | 331 |
| Amendment events (25 group duplicate evidence) | – | 119 |
| Edges with a stated effective date | 220 | 177 |
| Edges flagged EFFECTIVE_DATE_UNSTATED | 251 | 203 |
| Zero-length or reversed intervals | 49 | 0 |

**Identity map:** unaffected; byte-identical `--check`.

## Commits
- `618dcd11`: regression tests, the three fixes, the extended versioned-edge test and all regenerated artifacts (gate: 214 tests OK, all checks rc=0).

## Returned defect (independent review of 4a17359e): sections of the AMENDING Act treated as Army Act provisions
AA-04 (Repealing and Amending Act 1974) has `sections_affected` = "ss.4(3), 6(1), 7(1), 7(2): 'clause (i) of section 2' -> 'clause (i) of sub-section (1) of section 2' (s.3 and Second Schedule)". The "s.3" is s.3 of Act 56/1974. `expand_provisions` returned ['4','6','7','3'], and the verification guard passed because '3' occurs literally in the text. This produced false Army Act s.3 edges for KB-001, CIV-001, CIV-002, V8-CL-02 and V8-WF-02.

Tests are in `tests/test_legal_audit_review_fixes_cycle3.py` (`Fix1bAmendingActOwnSections`, which uses AA-04's full text including the parenthetical).

| Test | Before (4a17359e) | After |
| --- | --- | --- |
| `test_aa04_full_text_yields_only_army_act_sections` | `AttributeError: ... no attribute 'army_act_sections'` (Army Act text went straight to `expand_provisions`, which returned ['4','6','7','3']) | ok: ['4','6','7'] |
| `test_aa04_not_registered_against_army_act_s3` | `AssertionError: 'AA-04' unexpectedly found in {'AA-02', 'AA-06', 'AA-04', 'AA-01'}` | ok |
| `test_no_false_s3_edges_from_aa04` | `AssertionError: Lists differ: ['CIV-001', 'CIV-002', 'KB-001', 'V8-CL-02', 'V8-WF-02'] != []` | ok |
| `test_other_amending_act_reference_forms` (6 boundary strings) | `AttributeError` | ok, e.g. "s.12 of Act 37 of 1992 inserts words in s.135(1)" gives ['135'] |

**Fix.** `strip_amending_refs()` / `army_act_sections()` remove the following before expansion and verification:
- `s.N and [the] [Second|First] Schedule`;
- `s.N of Act X/YYYY` and `s.N of Act X of YYYY`;
- `s.N of the <Name> Act, YYYY`.

This is aligned with WS-A `tools/check_completeness_cycle3.py`. The tails are bounded so that Army Act references after them are kept. Verification runs on the stripped text, so an excluded number cannot be re-admitted by its literal occurrence.

**Scan of every Army Act chain row.** The pattern occurs in three rows:

| Row | Text removed | Before | After | Effect |
| --- | --- | --- | --- | --- |
| AA-04 | `s.3 and Second Schedule` | 4, 6, 7, 3 | 4, 6, 7 | corrected |
| AA-01 | `s.3 of Act 19/1955` | 3 | 3 | unchanged: s.3 legitimately remains through `s.3(iv)` |
| AA-03 | `s.2 and Schedule` | 2 | – | the row was already excluded as "none in Army Act", so no edge changes |

AA-06 ("Explanation below s.70") is a genuine Army Act reference and is kept.

**Edges after the fix:**

| Measure | Before | After |
| --- | --- | --- |
| Edges | 380 | 375 (the 5 false s.3 edges removed) |
| Amendment events | 119 | 118 |
| Edges with a stated effective date | 177 | 177 |
| Edges flagged EFFECTIVE_DATE_UNSTATED | 203 | 198 |
| Zero-length or reversed intervals | 0 | 0 |

`--check` was run twice: MATCH both times.

## Conditions
**(a) CONFLICTING_EVIDENCE is no longer skipped** (`tests/test_legal_audit_versioned_edges.py`). For every edge whose status is CONFLICTING_EVIDENCE, the test now asserts:
- every date listed in the status is a STATED effective date of one of the edge's evidence rows;
- at least two dates are listed;
- `valid_from` is empty;
- the edge carries the EVIDENCE_EFFECTIVE_DATE_CONFLICT flag.

New tests:
- `test_conflicting_evidence_path_fixture`: two descriptions of one event with different stated dates are grouped, flagged and left unresolved.
- `test_conflicting_evidence_present_in_real_versions`: the r.2 event exists and is flagged.

**(b) Corpus-dependent tests cannot pass vacuously.**
- The real-corpus Fix3 tests now state their skip reason explicitly.
- `Fix3WithoutCorpusRef` (3 tests) runs without `origin/raw-data`, on a minimal synthetic corpus committed inside the test file: KB-003 sections are checked, a missing s.80 downgrades the record, and bracket and V-series locators are bound.

**(c) Notes.**
- **r.2 CONFLICTING_EVIDENCE** (PCL-216-1988 vs PCL-BL-02, S.R.O. 216/1988). The two dates are the commencement on publication (1988-09-17) and the retrospective deemed effect (1979-06-04). This is not an evidential conflict between sources: the instrument states both. The event stays flagged CONFLICTING_EVIDENCE with `valid_from` empty, and is deliberately not resolved. Its legal effect on records dated 1979–1988 is advisor question AQ-06. No KB record cites r.2, so no edge carries it.
- **`successor_bound` and retrospective successors (AQ-06).** When the next event's stated effective date is on or before the current event's own `valid_from` (a retrospective successor), no `valid_to` is emitted. The edge gets VALIDITY_INTERVAL_REJECTED instead of a zero-length or reversed interval. The ordering of overlapping retrospective effect is a legal question (AQ-06) and is not decided by the generator.

## Commits (returned defect)
- `2c633b04`: regression tests, fix, conditions (a)-(c), regenerated versioned edges (gate: 223 tests OK; all checks rc=0).

## Final reconciliation (owner-instructed; base 2a66cd04 = integration #29 + PR #28)

### Task 1: P2 on PR #29 (Codex thread PRRT_kwDOV2o5I866mW1q), empty provision index rated ALL
**Defect.** In `canonical_coverage.py`, the check `C["sections"].get(target)` is falsy for a missing or EMPTY index, so section validation was skipped. KB-003 (Army Act ss.79–82, Army Rules r.22) was therefore rated `source_searchable = ALL` and `anchored_full = YES` without any provision evidence. Rule references were never checked at all.

Tests are in `tests/test_legal_audit_section_evidence.py`, 7 in total. All run on in-file fixtures and none depends on `origin/raw-data`, so none can be skipped in CI.

| Test | Before (2a66cd04) | After |
| --- | --- | --- |
| `test_empty_index_never_all` (Army Act + Army Rules metadata, EMPTY index) | `AssertionError: 'ALL' == 'ALL' : {'record_id': 'KB-003', ...` | ok: NONE, flag PROVISION_FILES_ABSENT |
| `test_missing_index_key_never_all` | `AssertionError: 'ALL' == 'ALL'` | ok: NONE |
| `test_missing_section_files` (s.81, s.82 absent) | ok (the non-empty index was already checked) | ok: PARTLY |
| `test_partial_index` (Army Act indexed, Army Rules index empty) | `AssertionError: 'ALL' != 'PARTLY'` | ok: PARTLY; instrument level ALL |
| `test_fully_populated_index` | `Regex didn't match: ...#r22` (rule references were not tracked) | ok: ALL |
| `test_unavailable_corpus_is_not_checked` (corpus = None) | ok | ok: NOT_CHECKED, never ALL |
| `test_plain_text_parity` (ADM-JD-02) | `AssertionError: 'ALL' != 'NONE'` | ok: ALL / NONE / PARTLY, matching KB-003 |

**Fix.** `provision_searchable()` and `searchable_state()` implement the following rules.
- An identified citation with section or rule references is searchable only when every corresponding provision file exists (`s<n>` / `r<n>`) in the document's index.
- A missing or empty index means ABSENT: the source is not searchable and the record is flagged PROVISION_FILES_ABSENT.
- An unavailable corpus means NOT_CHECKED.
- Any ABSENT source prevents ALL for the record, even if other sources are unchecked.
- Coded and plain-text citations follow identical rules.
- A new informational field, `source_searchable_instrument_level` (not a gate), repeats the check at document level only. It keeps the effect of absent provision files visible.

**Fixture completion (not a weakening).** `Fix3WithoutCorpusRef.FIXTURE_CORPUS` now includes `rules-army-rules-1954: {r22}`. KB-003 cites r.22, and the test's `ALL` assertion is unchanged.

**Canonical coverage figures (recomputed; the earlier 362 was provisional):**

| Measure | Old | New |
| --- | --- | --- |
| citation_present | YES 581 · NO 77 | unchanged |
| source_identified | ALL 396 · PARTLY 77 · NONE 108 · n/a 77 | unchanged |
| source_searchable | ALL 473 · n/a 185 | ALL 280 · PARTLY 105 · NONE 88 · n/a 185 |
| source_searchable_instrument_level (new, informational) | – | ALL 473 · n/a 185 |
| **ANCHORED_FULL** | YES 362 · NO 296 | **YES 187 · NO 471** |
| CODED family: searchable ALL / anchored | 297 / 207 | 181 / 102 |
| PLAINTEXT family: searchable ALL / anchored | 176 / 155 | 99 / 85 |
| Items searchable (of 718 identified) | 718 | 500 |
| Flag PROVISION_FILES_ABSENT (records) | – | 193 |

**Cause.** Every absent provision is a rule-level reference to a Rules document; the crawler corpus has no rule-level index for any Rules document:

| Document | Rule references absent | Records |
| --- | --- | --- |
| Army Rules 1954 | 454 | 157 |
| AFT Procedure Rules 2008 | 67 | 36 |
| AFT Amendment Procedure Rules 2011 | 11 | 9 |

Every cited Act section is present. This is a corpus-granularity gap, not a defect in the records. It closes when rule-level provision files exist, and the instrument-level field shows that the documents themselves are present.

**Versioned edges.** These were regenerated without code change for the #28 input-hash change. `statutory_version_register_seed.csv` changed from `b434a037…` to `595532f1…`; every edge figure is identical.

### Task 2: versioned edges after PR #28 and the WS-A in-place correction (merged 18ae1078 via merge commit 4c445df7)
**Addendum input.** WS-A `army_act_amendment_chain_addendum_cycle3.csv` is now a declared, pinned input (`INPUTS["wsa_aa_chain_addendum"]`). Its SHA-256 is recorded in the summary and the report.
- **Exclusions:** the same as for the main chain. Rows with no Army Act section text, Bills, "none" rows and NOT_APPLICABLE rows are dropped. AA-C3-04 (extension instruments) is therefore excluded.
- **Amending-Act stripping:** applies as before. AA-C3-03 yields only s.194, not s.2 of Act 36/1957.
- **Linkage:** a row declaring `supersedes_or_extends = "extends AA-NN"` joins that row's amendment event, because it is the same instrument and never a successor. AA-C3-01 joins AA-02 (Adaptation of Laws (No.3) Order 1956).
- **"instrument NOT examined":** such rows are text-only evidence (TEXT_OR_OCR_EVIDENCE_ONLY, INSTRUMENT_NOT_EXAMINED), and their dates are never used as stated.

**r.2 date model.** Publication date, commencement (`valid_from`, only when STATED_IN_INSTRUMENT) and `retrospective_deemed_effect_from` are distinct fields on the event.
- The deemed date is read from WS-A's change-log column and from the ARMY-RULES-CHAIN-01 chronology (PR #28). If the two disagree, the event is flagged EVIDENCE_DEEMED_EFFECT_CONFLICT.
- S.R.O. 216/1988 is now one event for r.2 (PCL-216-1988 + PCL-BL-02) and one for r.16A (PCL-216-1988 + PCL-BL-18): commencement 1988-09-17, deemed effect 1979-06-04, flag RETROSPECTIVE_DEEMED_EFFECT_AQ06. Legal applicability is left to AQ-06.
- No KB record cites r.2 or r.16A, so no edge carries the deemed effect yet (`edges_with_retrospective_deemed_effect` = 0).
- Two different STATED commencement dates are still CONFLICTING. `test_conflicting_evidence_path_fixture` is kept unchanged.

**Data correction, not a weakening.** The former assertion that r.2 was CONFLICTING_EVIDENCE (`test_conflicting_evidence_present_in_real_versions`) reflected WS-A's change log holding the deemed date (1979-06-04) in `effective_date` for PCL-BL-02. WS-A corrected that row in place (18ae1078), consistent with ARMY-RULES-CHAIN-01 after PR #28. The test is replaced by `test_r2_distinct_fields_model`, which asserts the corrected model: one event, commencement and deemed effect in separate fields, no conflict flag. The real-conflict path remains covered by a fixture.

Tests are `VersionedEdges.test_r2_distinct_fields_model`, `test_retrospective_fixture_is_not_a_conflict`, `test_edges_keep_publication_commencement_and_deemed_effect_distinct` and `AddendumInput` (5). The existing `test_stated_dates_are_the_registers_own` was extended to resolve addendum evidence rows.

| Test | Before (pre-Task-2 script on the corrected inputs) | After |
| --- | --- | --- |
| `test_r2_distinct_fields_model` | `KeyError: 'retro'` | ok |
| `test_retrospective_fixture_is_not_a_conflict` | `AssertionError: 'EVIDENCE_DEEMED_EFFECT_CONFLICT' not found in []` | ok |
| `AddendumInput.test_declared_and_pinned` | `AssertionError: 'wsa_aa_chain_addendum' not found in {...}` | ok |
| `AddendumInput.test_rows_are_read` | `AssertionError: 'AA-C3-01' not found in {...}` | ok |
| `AddendumInput.test_extends_row_joins_the_existing_event` | `AssertionError: 0 != 1` | ok |
| `AddendumInput.test_no_amending_act_own_sections_from_addendum` | `AssertionError: Lists differ: [] != ['194']` | ok |
| `AddendumInput.test_instrument_not_examined_is_text_only_never_stated` | ok (vacuous: no addendum rows were read) | ok (27 edges checked) |

**Versioned-edge figures:**

| Measure | Old (7e2e1baa) | New |
| --- | --- | --- |
| Edges | 375 | 391 |
| Amendment events | 118 | 123 |
| Events grouping duplicate evidence | 25 | 29 |
| Provisions with versions | 89 | 91 |
| Citations with registered versions | 331 | 341 |
| Edges with a stated commencement | 177 | 177 |
| Edges flagged EFFECTIVE_DATE_UNSTATED | 198 | 214 |
| Zero-length or reversed intervals | 0 | 0 |
| Events with conflicting commencement | 1 (r.2) | 0 |
| Events from the addendum | – | 9 |
| Edges with retrospective deemed effect | – | 0 |

| Flag | Old | New |
| --- | --- | --- |
| INSTRUMENT_NOT_EXAMINED | 0 | 27 |
| TEXT_OR_OCR_EVIDENCE_ONLY | 5 | 32 |
| SUBPROVISION_VERSION | 178 | 200 |
| VALID_TO_UNSTATED | 31 | 37 |

The AA-04 regression still passes: no false Army Act s.3 edges.

## Commits (reconciliation)
- `7e2e1baa`: R-1 provision-level searchability and the #28 regeneration.
- `4c445df7`: merge of claude/ws-a-cycle3-reconcile (18ae1078).
- `aef02e0e`: R-2 versioned edges (addendum input, r.2 date model), tests and regenerated outputs.
