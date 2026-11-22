# WS-A Cycle 3 final reconciliation (owner-instructed)

**Base:** 2a66cd04 (integration #29 plus baseline PR #28).

**Scope:** no legal determination was made and no reserved state was changed (r.23(3) CONFLICTING, C-08 OPEN, C-09 PROPOSAL). Nothing was downloaded. Every change is backed by evidence already held and carries a versioned note in its row.

## Items
1. **CF-CHAIN-AA-C3-01.** AA-C3-01 (Adaptation of Laws (No.3) Order 1956) cited ACQ03-020, which is S.R.O. 2(E)/1955.
   - `acq03_pinned_candidates.csv` ACQ03-021 is the A.L.O. 1956 candidate: `in.gazette.e.1956.717`, E-2189-1956-0415-100172.pdf. That is the same identifier as AA-C3-01's `gazette_identity`.
   - **Corrected:** ACQ03-020 → ACQ03-021.
2. **CF-ACQ03-029.** ACQ03-029 (Army Act 1950 as enacted) is updated to the source located in cycle 3: `https://archive.org/download/in.gazette.e.1950.306/E-2350-1950-0011-109089.pdf`, 6,491,633 B, md5 68bcdd4e8db91eb83d1e6b92a393b2db.
   - These values are from archive.org metadata (`source=original`), as recorded for ACQ-C3-01.
   - Status is now CANDIDATE: not fetched, and the source stays UNVERIFIED until it is acquired and page-image checked.
   - The overlap check is negative for ACQ-01, ACQ-02 and ACQ-03.
   - Cycle-1 chain row AA-00 is **not edited**. A versioned note row AA-C3-05 in `army_act_amendment_chain_addendum_cycle3.csv` supersedes its acquisition reference and cross-references ACQ-C3-01.
3. **PR #28 values checked** against my provision change log and commencement readings.
   - **The cycle-2/3 readings agree** with #28 in substance: AR-010/011/025 print no commencement clause, and AR-024 is in force on publication 1988-09-17 with items 2 and 3 deemed from 04-06-1979.
   - **Rows corrected.** Six rows carried stale values from the cycle-1 baseline: PCL-BL-02, PCL-BL-04, PCL-BL-18, PCL-BL-41, PCL-BL-45 and PCL-194-1989.
     - PCL-BL-02 (r.2) had `effective_date` = 1979-06-04, i.e. the deemed date placed in the effective-date column.
     - The other five said "not recorded / NOT_DETERMINED".
     - Evidence: my own images WSA-PIC-37/38 (S.R.O. 116/1965 pp.96–97), WSA-PIC-39 (215/1965 p.172), WSA-PIC-41 (216/1988 p.617) and WSA-PIC-57 (332/1989 p.736).
   - **Commencement and deemed effect are now distinct values.** A new column `retrospective_deemed_effect_from` (the same name as in the #28 baseline) was added to `provision_change_log.csv` and `commencement_readings_cycle3.csv`.
     - For r.2 (PCL-BL-02) and the r.16A Explanation (PCL-BL-18), as for PCL-216-1988: `effective_date` = 1988-09-17 (STATED_IN_INSTRUMENT, r.1(2)) and `retrospective_deemed_effect_from` = 1979-06-04.
     - Legal effect is left to AQ-06.
   - **Wording aligned:** the text of PCL-116-1965, PCL-215-1965, PCL-216-1988 and of commencement readings AR-010/011/024/025 now matches #28. The substance is unchanged.
   - **Completeness table:** in row AR r.13, the AR-010 commencement value is recomputed from the #28 register by the generator's own formula. No other row was stale.
   - **Pointer fix:** r.15 trace item 3 cited the wrong cycle-2 PIC numbers. They are corrected against `identity_transcription_register.csv`.
   - **No discrepancy remains OPEN.**
4. `tools/check_completeness_cycle3.py --selftest` has been re-run (output below).

## Pinned-input constraint
- `provision_change_log.csv` is a pinned input of WS-D `build_versioned_edges` (`tests/test_legal_audit_versioned_edges.py`). Editing it fails four WS-D tests, and WS-A may not edit WS-D files.
- The file is therefore left **byte-identical** to its committed version.
- The nine corrected commencement records listed under "PCL" below are recorded instead in `provision_change_log_supersessions_cycle3.csv` (PCL-SUP-C3-01..09). Each row names the superseded change_id, the before values, the after values, the separate `retrospective_deemed_effect_from`, and the image evidence.
- WS-D is asked through the coordinator (STATUS.md) to consume the file and regenerate its edges. WS-D's test that expects the r.2 PCL-216-1988 vs PCL-BL-02 CONFLICTING_EVIDENCE flag will then need WS-D review: the supersession resolves that flag as a column-placement error (deemed date placed in `effective_date`), not a conflict between sources.
- The other edits in this reconciliation are applied in place, because those files are not pinned: the addendum, ACQ03-029, the commencement readings, one cell of the completeness table, and the r.15 trace pointer.

## Every changed cell (before → after)
The "PCL" lines are recorded in the supersession file, not applied to `provision_change_log.csv`.
```
ADDENDUM AA-C3-01 | gazette_identity | 'archive.org in.gazette.e.1956.717 (ACQ03-020)' -> 'archive.org in.gazette.e.1956.717 (ACQ03-021)'
ADDENDUM AA-C3-01 | acquisition_request | 'ACQ03-020' -> 'ACQ03-021'
ADDENDUM AA-C3-01 | notes | 'Versioned addendum to AA-02 (cycle-1 row unchanged): itemises the sections. Review fix: s.137 and s.2 were omitted from the completeness table' -> "Versioned addendum to AA-02 (cycle-1 row unchanged): itemises the sections. Review fix: s.137 and s.2 were omitted from the completeness table; reconcile 2026-11-22 (owner-instructed; agrees with PR #28 ARMY-RULES-CHAIN-01): acquisition reference corrected ACQ03-020 -> ACQ03-021 (ACQ03-020 is S.R.O. 2(E)/1955; ACQ03-021 is in.gazette.e.1956.717, the same identifier as this row's gazette_identity)"
ADDENDUM AA-C3-05 | (new row) | archive.org in.gazette.e.1950.306 (E-2350-1950-0011-109089.pdf, 6491633 B, md5 68bcdd4e8db91eb83d1e6b92a393b2db; metadata subject 'THE ARMY ACT, 1950 No. XLVI OF 1950')
ACQ03 ACQ03-029 | host | '' -> 'archive.org'
ACQ03 ACQ03-029 | download_url | '' -> 'https://archive.org/download/in.gazette.e.1950.306/E-2350-1950-0011-109089.pdf'
ACQ03 ACQ03-029 | expected_md5 | '' -> '68bcdd4e8db91eb83d1e6b92a393b2db'
ACQ03 ACQ03-029 | expected_bytes | '' -> '6491633'
ACQ03 ACQ03-029 | file_source_per_metadata | '' -> 'original (Text PDF per archive.org /metadata, fetched 2026-11-22)'
ACQ03 ACQ03-029 | document_identity_expected | 'Gazette of India Extraordinary 1950 Pt II-Sec 1 - not located' -> "Gazette of India Extraordinary dated 23-05-1950 (Ministry of Law), 'THE ARMY ACT, 1950 No. XLVI OF 1950' per metadata subject"
ACQ03 ACQ03-029 | overlap_check | 'n/a (no URL)' -> 'NOT in ACQ-01 (origin/claude/acq-01-config sources.yaml) and NOT in ACQ-02 (origin/claude/acq-02-config); not in origin/claude/acq-03-config'
ACQ03 ACQ03-029 | status | 'NO_LAWFUL_ONLINE_SOURCE_KNOWN' -> 'CANDIDATE (not fetched; source UNVERIFIED until acquired and page-image checked)'
ACQ03 ACQ03-029 | notes | 'custodian / print source required; owner decision' -> 'reconcile 2026-11-22 (owner-instructed; agrees with PR #28 ARMY-RULES-CHAIN-01): was NO_LAWFUL_ONLINE_SOURCE_KNOWN with empty URL; source located in cycle 3 (ACQ-C3-01; metadata + OCR locator only)'
PCL PCL-194-1989 | commencement_as_printed | 'not recorded' -> 'no commencement clause printed (r.1 gives short title only)'
PCL PCL-194-1989 | effective_date_status | 'NOT_STATED_PENDING_ADVICE (AQ-05)' -> 'NOT_STATED_PENDING_ADVICE (AQ-05; instrument silent; no effective date inferred from publication)'
PCL PCL-BL-02 | commencement_as_printed | 'retrospective' -> 'r.1(2): in force on the date of publication in the Official Gazette (1988-09-17); item 2 deemed effective from 04-06-1979'
PCL PCL-BL-02 | effective_date | '1979-06-04' -> '1988-09-17'
PCL PCL-BL-02 | effective_date_status | 'STATED_IN_INSTRUMENT (retrospective; legal effect AQ-06)' -> 'STATED_IN_INSTRUMENT (r.1(2): in force on publication 1988-09-17); retrospective deemed effect from 1979-06-04 recorded separately in retrospective_deemed_effect_from (legal effect AQ-06)'
PCL PCL-BL-02 | retrospective_deemed_effect_from | '' -> '1979-06-04'
PCL PCL-BL-04 | commencement_as_printed | 'not recorded' -> 'no commencement clause printed (r.1 gives short title only)'
PCL PCL-BL-04 | effective_date_status | 'NOT_DETERMINED (commencement clause not yet read)' -> 'NOT_STATED_PENDING_ADVICE (AQ-05; instrument silent; no effective date inferred from publication)'
PCL PCL-BL-18 | commencement_as_printed | 'not recorded' -> 'r.1(2): in force on the date of publication in the Official Gazette (1988-09-17); item 3 deemed effective from 04-06-1979'
PCL PCL-BL-18 | effective_date | '' -> '1988-09-17'
PCL PCL-BL-18 | effective_date_status | 'NOT_DETERMINED (commencement clause not yet read)' -> 'STATED_IN_INSTRUMENT (r.1(2): in force on publication 1988-09-17); retrospective deemed effect from 1979-06-04 recorded separately in retrospective_deemed_effect_from (legal effect AQ-06)'
PCL PCL-BL-18 | retrospective_deemed_effect_from | '' -> '1979-06-04'
PCL PCL-BL-41 | commencement_as_printed | 'not recorded' -> 'no commencement clause printed (r.1 gives short title only)'
PCL PCL-BL-41 | effective_date_status | 'NOT_DETERMINED (commencement clause not yet read)' -> 'NOT_STATED_PENDING_ADVICE (AQ-05; instrument silent; no effective date inferred from publication)'
PCL PCL-BL-45 | commencement_as_printed | 'not recorded' -> 'no commencement clause printed (r.1 gives short title only)'
PCL PCL-BL-45 | effective_date_status | 'NOT_DETERMINED (commencement clause not yet read)' -> 'NOT_STATED_PENDING_ADVICE (AQ-05; instrument silent; no effective date inferred from publication)'
PCL PCL-116-1965 | commencement_as_printed | 'not stated' -> 'no commencement clause printed (r.1 gives short title only)'
PCL PCL-116-1965 | effective_date_status | 'NOT_STATED_PENDING_ADVICE (AQ-05)' -> 'NOT_STATED_PENDING_ADVICE (AQ-05; instrument silent; no effective date inferred from publication)'
PCL PCL-215-1965 | commencement_as_printed | 'not stated' -> 'no commencement clause printed (r.1 gives short title only)'
PCL PCL-215-1965 | effective_date_status | 'NOT_STATED_PENDING_ADVICE (AQ-05)' -> 'NOT_STATED_PENDING_ADVICE (AQ-05; instrument silent; no effective date inferred from publication)'
PCL PCL-216-1988 | commencement_as_printed | "r.1(2): on publication; items 2 and 3: 'shall be deemed to have been omitted/added from the 4th June, 1979'" -> 'r.1(2): in force on the date of publication in the Official Gazette (1988-09-17); items 2 and 3 each deemed effective from 04-06-1979'
PCL PCL-216-1988 | effective_date_status | 'STATED_IN_INSTRUMENT (on publication 17-09-1988; retrospective deeming from 1979-06-04 for items 2-3, legal effect AQ-06)' -> 'STATED_IN_INSTRUMENT (r.1(2): in force on publication 1988-09-17); retrospective deemed effect from 1979-06-04 recorded separately in retrospective_deemed_effect_from (legal effect AQ-06)'
PCL PCL-216-1988 | retrospective_deemed_effect_from | '' -> '1979-06-04'
COMMENCEMENT AR-010 | commencement_as_printed | 'not stated' -> 'no commencement clause printed (r.1 gives short title only)'
COMMENCEMENT AR-010 | effective_date_status | 'NOT_STATED_PENDING_ADVICE (AQ-05)' -> 'NOT_STATED_PENDING_ADVICE (AQ-05; instrument silent; no effective date inferred from publication)'
COMMENCEMENT AR-011 | commencement_as_printed | 'not stated' -> 'no commencement clause printed (r.1 gives short title only)'
COMMENCEMENT AR-011 | effective_date_status | 'NOT_STATED_PENDING_ADVICE (AQ-05)' -> 'NOT_STATED_PENDING_ADVICE (AQ-05; instrument silent; no effective date inferred from publication)'
COMMENCEMENT AR-025 | commencement_as_printed | 'not stated' -> 'no commencement clause printed (r.1 gives short title only)'
COMMENCEMENT AR-025 | effective_date_status | 'NOT_STATED_PENDING_ADVICE (AQ-05)' -> 'NOT_STATED_PENDING_ADVICE (AQ-05; instrument silent; no effective date inferred from publication)'
COMMENCEMENT AR-024 | commencement_as_printed | 'on publication (r.1(2)); items 2-3 deemed from 04-06-1979' -> 'r.1(2): in force on the date of publication in the Official Gazette (1988-09-17); items 2 and 3 each deemed effective from 04-06-1979'
COMMENCEMENT AR-024 | effective_date_status | 'STATED_IN_INSTRUMENT (on publication; items 2-3 retrospective from 1979-06-04, legal effect AQ-06/OQ-A-12)' -> 'STATED_IN_INSTRUMENT (r.1(2): in force on publication 1988-09-17); retrospective deemed effect from 1979-06-04 recorded separately in retrospective_deemed_effect_from (legal effect AQ-06)'
COMMENCEMENT AR-024 | retrospective_deemed_effect_from | '' -> '1979-06-04'
EVIDENCE-POINTER FIX provision_change_log.csv: 5 cells (116/1965 -> WSA-PIC-37/38; 215/1965 -> WSA-PIC-39)
EVIDENCE-POINTER FIX commencement_readings_cycle3.csv: 0 cells (116/1965 -> WSA-PIC-37/38; 215/1965 -> WSA-PIC-39)
R15 item 3 | evidence | 'PIC-14/15/16; WSA-PIC-38..40, 49..50 (cycle 2); T1-03/04' -> 'PIC-14/15/16; WSA-PIC-37..39, 48, 49 (cycle 2); T1-03/04'
COMPLETENESS AR r.13 | commencement_status_of_amendments | 'AR-004: NOT_DETERMINED (commencement clause not yet read); AR-009: NOT_STATED_PENDING_ADVICE (AQ-05); AR-010: NOT_DETERMINED (commencement clause not yet read); AR-032: NOT_DETERMINED (commencement clause not yet read)' -> 'AR-004: NOT_DETERMINED (commencement clause not yet read); AR-009: NOT_STATED_PENDING_ADVICE (AQ-05); AR-010: NOT_STATED_PENDING_ADVICE (AQ-05; instrument silent; no effe; AR-032: NOT_DETERMINED (commencement clause not yet read)'
```

## Completeness check (re-run)
```
rows_checked=219 failures=0
  selftest ok   expect=PASS live: no registered amendment (AA s.18)
  selftest ok   expect=PASS live: only image-checked amendments, ALL (AA s.70)
  selftest ok   expect=C1   live: registered instrument removed
  selftest ok   expect=C2   fixture: unexamined registration forced ALL -> C2
  selftest ok   expect=C2   fixture: unexamined registration with PARTIALLY_ESTABLISHED (AA) -> C2
  selftest ok   expect=PASS fixture: unexamined registration, NOT ALL, NOT_ESTABLISHED -> PASS
  selftest ok   expect=C1   fixture: prefix ID 'AR-01' must NOT match 'AR-010' -> C1
  selftest ok   expect=PASS fixture: exact ID 'AR-010' present -> PASS
  selftest ok   expect=C1   fixture: prefix key 'S.O. 39' must NOT match 'S.O. 3912(E)' -> C1
selftest PASS (9/9 cases)
```

## Gate results (exit codes read directly)
| Gate | Exit | Result |
| --- | --- | --- |
| PILOT-01 strict | 0 | |
| R23 strict | 0 | |
| `check_registers.py` | 0 | |
| `check_csv.py` | 0 | 118 files, 0 errors |
| `check_provenance.py` | 0 | violations=2, both known; new=0 |
| `check_completeness_cycle3.py --selftest` | 0 | 9/9 |
| unittest | **1** | 2 failures |

**The unittest failures pre-date this work.** The same two failures occur on the untouched base 2a66cd04, with WS-A's tracked changes stashed:
- `test_legal_audit_versioned_edges.test_inputs_pinned_and_current`;
- `test_legal_audit_versioned_edges.test_regeneration_is_byte_identical`.

In both, the input that changed is `version_register` (ARMY-RULES-CHAIN-01, updated by PR #28), and the regenerated `relation_graph_versioned_report.md` differs only in that input's hash. Regenerating WS-D outputs is outside WS-A's write scope, so it is routed to the coordinator / WS-D. WS-A's own pinned input (`wsa_change_log`, hash 342ab73c9…) is unchanged.
