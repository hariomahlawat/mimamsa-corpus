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
- See the line appended below.
