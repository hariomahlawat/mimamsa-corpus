# Review fix (PR #24, Codex P2): Army Act s.137 completeness overstated

The PR #24 table listed only Act 37/1992 against s.137, so s.137 was overstated and wrongly counted as PARTIALLY_ESTABLISHED. All three affected rows are now corrected, and a regression check guards against a repeat.

## 1. Regression check (written first)
`tools/check_completeness_cycle3.py` uses the standard library only. It runs two checks on every Army Act section and Army Rule in `statutory_version_completeness_cycle3.csv`:
- **C1:** every amending instrument registered against the provision appears in `located_amending_instruments`. The registers it reads are `army_act_amendment_chain.csv` (plus `_addendum_cycle3.csv`), `provision_change_log.csv` and `ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv`.
- **C2:** no row says `amendments_image_checked` = ALL, or has a status that rests on image-checked amendments, while any registered amendment is unexamined or text-only.

One fix was made to the checker itself during the first run. It had taken "(s.3 and Second Schedule)" in AA-04 as Army Act s.3, but that phrase refers to s.3 of the amending Act 56/1974. The parser now drops references to sections of the amending Act.

### Failing output on the table as committed in a50fcc87 (AA-02 only, before the addendum existed)
```
FAIL C1 AA s.137: registered amendment 'A.L.O.' missing from located_amending_instruments
FAIL C2 AA s.137: amendments_image_checked=ALL but unexamined/text-only: A.L.O.
FAIL C2 AA s.137: status 'PARTIALLY_ESTABLISHED' rests on image-checked amendments but unexamined/text-only: A.L.O.
rows_checked=219 failures=3
```
### Failing output on the same committed table, re-run after the addendum below was registered
```
FAIL C1 AA s.2: registered amendment 'A.L.O.' missing from located_amending_instruments
FAIL C1 AA s.137: registered amendment 'A.L.O.' missing from located_amending_instruments
FAIL C1 AA s.137: registered amendment 'S.O. 3912(E)' missing from located_amending_instruments
FAIL C2 AA s.137: amendments_image_checked=ALL but unexamined/text-only: A.L.O., S.O. 3912(E)
FAIL C2 AA s.137: status 'PARTIALLY_ESTABLISHED' rests on image-checked amendments but unexamined/text-only: A.L.O., S.O. 3912(E)
rows_checked=219 failures=5
```

## 2. Verification of s.137
All compilation pages below were rendered by WS-A from the held India Code compilation, sha e47a4265…:
- **Act 37/1992 s.13** substitutes the CrPC 1973 references in s.137(3),(4). Source: Gazette WSA-PIC-27, plus compilation p.38 footnote 1.
- **A.L.O. (No.3) 1956** substitutes "a Part B State" in s.137(3),(4). Source: compilation p.38 footnote 2. The instrument itself has not been examined; it is not held (ACQ03-020).
- **S.O. 3912(E) of 30-10-2019** is cited in a compilation note (p.38, marked *) as making the Act applicable to the UTs of J&K and Ladakh. It was not located, and its effect on the bracketed J&K reference is a legal question (ACQ-C3-05).
- **Result:** s.137 now lists all three instruments, `amendments_image_checked` = NOT ALL, and the status is NOT_ESTABLISHED. It stays incomplete until the 1956 and 2019 instruments are examined.

## 3. Other affected rows
- **Compilation footnote images checked for every section carrying an A.L.O. or J&K* marker:** pp.10–13 (ss.1–7), p.38 (s.137), p.42 (s.151), p.45 (s.174) and p.48 (ss.191–196).
- **The eight remaining PARTIALLY_ESTABLISHED Army Act rows** were re-checked against their compilation pages: ss.70 (p.26), 81 (p.28), 122/123 (p.35), 127 (p.36, cycle 1), 135 (p.37), 169A (p.44) and 191 (p.48). Each carries only the image-checked Acts 37/1992 or 13/1975, so all eight stay PARTIALLY_ESTABLISHED.
- **Rows corrected:**
  - **AA s.2:** "none" is replaced by A.L.O. (No.3) 1956 (cl.(h) omitted; "(g)" substituted). `amendments_image_checked` becomes NOT ALL. The status was already NOT_ESTABLISHED and is unchanged.
  - **AA s.3:** the A.L.O. reference now points to AA-C3-01. Its status is unchanged.
  - **AA s.137:** as described in section 2.
- **Rows not in the KB list** (ss.4, 5, 151, 174, 194) are covered by the addendum only.
- **New addendum `army_act_amendment_chain_addendum_cycle3.csv`.** The cycle-1 rows are unchanged and the addendum is versioned. It records:
  - AA-C3-01: A.L.O. 1956, itemised by section;
  - AA-C3-02: S.O. 3912(E)/2019;
  - AA-C3-03: Act 36/1957, which repealed s.194 and the Schedule;
  - AA-C3-04: the 1962–63 extension instruments (these amend no section text).
- **Army Rules:** C1 and C2 pass for all 107 rule rows. No Army Rule row was affected.

## 4. Statistics (regenerated deterministically by the same generator)
| | ESTABLISHED_SUBJECT_TO_REGISTER_GAPS | PARTIALLY_ESTABLISHED | NOT_ESTABLISHED |
| --- | --- | --- | --- |
| AR before → after | 2 → 2 | 31 → 31 | 74 → 74 |
| AA before → after | 0 → 0 | **9 → 8** | **103 → 104** |

## 5. Passing output and boundary tests
```
rows_checked=219 failures=0
selftest PASS (no-amendment case: AA s.18; image-only case: AA s.70)
```
The self-test covers four cases:
- a section with no registered amendment (AA s.18), which must pass;
- a section with only image-checked amendments (AA s.70), which must pass;
- a row whose registered instrument has been removed, which must fail C1;
- s.137 forced to ALL, which must fail C2.

## 6. Follow-up to the conditional acceptance (independent review of bfc9765a)
1. **The C2 negative test no longer depends on live data.** Explicit fixtures inject a synthetic registry into `check()`:
   - an AA row forced to ALL with a known unexamined registration must fail C2;
   - the same row marked PARTIALLY_ESTABLISHED must fail C2;
   - the same row marked NOT ALL / NOT_ESTABLISHED must pass.
2. **C1 now matches on token boundaries** (`present()`), not substrings. A registered ID must not be followed or preceded by a letter or digit. Boundary fixtures:
   - "AR-01" must **not** match inside "AR-010" (fails C1);
   - "AR-010" present (passes);
   - "S.O. 39" must **not** match inside "S.O. 3912(E)" (fails C1).
3. **Known false-pass limitation.** AA-01 (Act 19/1955) says "Commander-in-Chief → Chief of the Army Staff in many sections" without listing them.
   - C1 therefore registers Act 19/1955 against s.3 only. It **cannot** detect Act 19/1955 being missing from the row of any other section that Act amended.
   - The sections are not guessed. This is recorded as **OQ-A-13** in `open_questions_cycle3.csv`, pending examination of the Act's Schedule (Gazette `in.gazette.e.1955.613` is in ACQ-01 B6) or itemisation of all compilation footnote images.
4. **WS-D input.** `army_act_amendment_chain_addendum_cycle3.csv` (AA-C3-01..04) is not yet an input to WS-D `build_versioned_edges`. This is raised as a request in STATUS.md, routed to WS-D through the coordinator. No WS-D file was edited.

### Outputs after this follow-up
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
The pre-fix table still fails with boundary matching:
```
FAIL C1 AA s.2: registered amendment 'A.L.O.' missing from located_amending_instruments
FAIL C1 AA s.137: registered amendment 'A.L.O.' missing from located_amending_instruments
FAIL C1 AA s.137: registered amendment 'S.O. 3912(E)' missing from located_amending_instruments
FAIL C2 AA s.137: amendments_image_checked=ALL but unexamined/text-only: A.L.O., S.O. 3912(E)
FAIL C2 AA s.137: status 'PARTIALLY_ESTABLISHED' rests on image-checked amendments but unexamined/text-only: A.L.O., S.O. 3912(E)
rows_checked=219 failures=5
```
