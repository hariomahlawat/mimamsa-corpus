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
