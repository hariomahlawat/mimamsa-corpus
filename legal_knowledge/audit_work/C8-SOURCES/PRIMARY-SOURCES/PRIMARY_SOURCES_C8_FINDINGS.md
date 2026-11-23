# PRIMARY_SOURCES_C8_FINDINGS (Cycle 8, Workstream D)

**Scope:** inventories and evidence matrices only. No download, no network request, no crawler/config/robots change, no legal status changed, no commencement date inferred, no reserved state resolved. Repository snapshot read-only at commit bb1f0971. All outputs regenerate with `python tools/build_c8_d.py <repo> --check`.

## 1. Baseline (recomputed)

- KB records: reported 658, recomputed **658** (MATCH)
- Case records: reported 53, recomputed **53** (MATCH)
- "KB citation items" as reported: reported 1,060, recomputed **1060** (MATCH)
- of which genuine citation items (relationship_type=CITES): reported 1,060, recomputed **983** (DIFFERENCE)
- of which NO_CITATION placeholder rows: reported not stated, recomputed **77** (n/a)
- KB exact citation anchors: reported 42, recomputed **42** (MATCH)
- KB PARTIAL_MATCH items: reported 652, recomputed **652** (MATCH)
- KB MISSING_EVIDENCE items: reported 366, recomputed **366** (MATCH)
- KB records with no exact anchor: reported 618, recomputed **618** (MATCH)
- KB records, all items exact: reported 10, recomputed **10** (MATCH)
- KB records, some items exact: reported 30, recomputed **30** (MATCH)
- Case records EXACT / PARTIAL / MISSING: reported 6 / 7 / 40, recomputed **6 / 7 / 40** (MATCH)
- coverage_summary.json kb items (EXACT/PARTIAL/MISSING): reported 42 / 652 / 366, recomputed **42 / 652 / 366** (MATCH)
- AUTH-LEDGER effective v0000 NO_EXACT_ANCHOR: reported 618, recomputed **618** (MATCH)

**Discrepancy:** "1,060 KB citation items" counts crosswalk rows, including 77 NO_CITATION placeholders; the true number of citation items is **983**, and genuine MISSING items are **289** (not 366). 618 reproduces, but 77 of those records cite nothing (541 have citations and no exact anchor). Details: `BASELINE_RECOMPUTE.md`.

## 2. Key gaps per instrument

- **Army Act 1950 (Act 46 of 1950) and amending Acts:** Gazette as enacted NOT held (pinned C5-ACQ-01 = ACQ03-029 = ACQ-C3-01); only an India Code compilation (provenance undocumented). Commencement S.R.O. 120/1950 not held (COMMENCEMENT NOTIFICATION REQUIRED; probable candidate ACQ03-019 in PR #23). Act 37/1992 held with documented provenance; Act 13/1975 held (undocumented); Act 19/1955 extract lacks its Schedule (Gazette pinned ACQ-01-B6; appointing S.R.O. 2(E)/1955 candidate ACQ03-020). ALO 1956, Act 56/1974, Ordinance 1975 and Act 20/1983 (+ its commencement notification) not held but pinned in ACQ-03 (PR #23); RAA 1957 and S.O. 3912(E)/2019 not located.
- **Army Rules 1954 (S.R.O. 484 of 27-11-1954) and amending S.R.O.s:** 1954 S.R.O. 484 held (documented primary). 24 amending/declaration Gazettes held, only 3 with documented provenance (AR-006, AR-029, AR-031). Chain open after 06-06-2022 (10 candidate S.R.O.s, subject unconfirmed); AR-001 and AR-030 not found; 5 text-layer-only; 13 hints unopened. Reserved: r.23(3) CONFLICTING, r.182 OPEN, r.193 OPEN, r.194 PROPOSAL.
- **Armed Forces Tribunal Act 2007 (Act 55 of 2007), amendments (Finance Act 2017; TRA 2021; TRA 2026) and AFT Procedure/Practice Rules:** Gazette as enacted NOT held (pinned C5-ACQ-02); compilation as on 01-09-2026 held (undocumented). Commencement S.O. 14(E)/2008 not held and not registered (COMMENCEMENT NOTIFICATION REQUIRED). Finance Act 2017 and TRA 2021 not held or registered; TRA 2021 provisions affected unknown. TRA 2026 held (undocumented) - substitutes s.9A and repeals TRA 2021, but commences by notification (COMMENCEMENT NOTIFICATION REQUIRED). AFT Procedure Rules 2008/2011 and Practice Rules 2009: no held copy, although archive.org candidates are pinned in ACQ-03 (ACQ03-030..032, PR #23) - the C5 master still says DISCOVERY_REQUIRED.
- **Bharatiya Nyaya Sanhita 2023 (Act 45 of 2023):** No reliable copy at all (derived text only); Gazette pinned (C5-ACQ-20); commencement notification not held (COMMENCEMENT NOTIFICATION REQUIRED).
- **Bharatiya Nagarik Suraksha Sanhita 2023 (Act 46 of 2023):** Gazette not held (pinned C5-ACQ-03); compilation held (undocumented); commencement footnote S.O. 848(E) only (COMMENCEMENT NOTIFICATION REQUIRED).
- **Bharatiya Sakshya Adhiniyam 2023 (Act 47 of 2023):** Gazette not held (pinned C5-ACQ-04); compilation held (undocumented); commencement footnote S.O. 849(E) only (COMMENCEMENT NOTIFICATION REQUIRED); C-07 adviser question on AA s.133 preserved.
- **Commencement notifications for BNS, BNSS and BSA (Gazette Extraordinary 24-02-2024):** All three 2024 notifications not held; pinned (C5-ACQ-05). The 01-07-2024 switch date is evidenced only by compilation/derived footnotes.
- **Indian Penal Code 1860 (historical):** No copy of any kind (not even derived text).
- **Code of Criminal Procedure 1973 (historical):** Derived text only (edition unknown); BNSS s.531 repeal read from the compilation.
- **Indian Evidence Act 1872 (historical):** Derived text only (edition unknown); BSA s.170 repeal read from the compilation.
- **Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978 and S.O. 4010 of 1986:** 1978 Rules (S.O. 488) and S.O. 4010/1986 not held (only the Rajya Sabha papers-laid record), but BOTH are already pinned in ACQ-01-B2 (PR #8); the C5 master says NOT_CHECKED / DISCOVERY_REQUIRED. S.O. 4010 is dated 24-11-1986 in ACQ-01/PILOT-01 and "6th December 1986" in the C5 title (Gazette date): unresolved.
- **Army and Air Force (Disposal of Private Property) Act 1950 and Amendment Act 2000:** Principal Act: no copy, India Code blocked. Amendment Act 2000: 2 archive items unpinned (P-C7-02-META).
- **Air Force Act 1950 (Act 45 of 1950):** Derived text only; not registered in C5.
- **Navy Act 1957 (Act 62 of 1957):** Derived text only; not registered in C5.
- **Inter-Services Organisations (Command, Control and Discipline) Act 2023 and Rules 2025:** Not held; not searched.

## 3. Highest-value acquisitions (by dependent records; `source_to_record_gap_matrix.csv`)

| rank | gap | source | KB records (direct) | KB items | upper bound | cases | tier | route | authorisation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | G-AA-ENACT | Army Act 1950 as enacted (Gazette Extraordinary No.306/1950) | 185 | 190 |  | 12 | A | C5-ACQ-01 (pinned) | A-C5-1 (download approval) + crawler-config PR sta |
| 2 | G-AR-CHAIN | Complete, verified Army Rules amendment chain for rules with a recorde | 122 | 131 |  | 9 | A | C5-ACQ-06 post-2022 S.R.O.s; AR-001/AR-0 | A-C5-1 + discovery approval + adviser review (no d |
| 3 | G-AFT-ENACT | AFT Act 2007 as enacted (Gazette Extraordinary 28-12-2007) | 89 | 89 |  | 3 | A | C5-ACQ-02 (pinned) | A-C5-1 (download approval) + crawler-config PR sta |
| 4 | G-BSA-ENACT | BSA 2023 as enacted (Gazette 25-12-2023) | 64 | 64 |  | 1 | A | C5-ACQ-04 (pinned) | A-C5-1 (download approval) + crawler-config PR sta |
| 5 | G-BNSS-ENACT | BNSS 2023 as enacted (Gazette 25-12-2023) | 49 | 50 |  | 0 | A | C5-ACQ-03 (pinned) | A-C5-1 (download approval) + crawler-config PR sta |
| 6 | G-AFT-PR | AFT (Procedure) Rules 2008, Amendment Rules 2011, Practice Rules 2009 | 43 | 55 |  | 0 | A | C5 says DISCOVERY_REQUIRED, but pinned a | A-C5-1 (PR #23 stack); C5 register reconciliation |
| 7 | G-DESW-WEB | DESW/CGDA/PIB web guidance (secondary; not governing authority) | 33 | 44 |  | 0 | C | DISCOVERY_REQUIRED | n/a (secondary) |
| 8 | G-AA-AA-06 | Army Act amending instrument: Air Force and Army Laws (Amendment) Act, | 26 | 26 |  | 0 | B | provenance registration (no download) | owner decision on provenance addendum |
| 9 | G-PRA-PT1 | Pension Regulations for the Army 2008 Part I | 25 | 25 |  | 0 | B | C5-ACQ-07 (DESW) | A-C5-2 + DESW allow-list PR + readable robots (403 |
| 10 | G-AA-AA-02+AA-C3-01 | Army Act amending instrument: Adaptation of Laws (No.3) Order, 1956 (A | 18 | 18 |  | 0 | A | ACQ03-021 [ACQ-03 B4 (archive_acq03 (PR  | A-C5-1 |
| 11 | G-AR-UNDOC | 21 held Army Rules amendment Gazettes without documented provenance (A | 15 | 16 |  | 0 | B | provenance registration (no download) | owner decision on authentication addendum (AUTH-LE |
| 12 | G-BNS-ENACT | BNS 2023 (any reliable text) | 12 | 12 |  | 0 | A | C5-ACQ-20 (pinned) | A-C5-1 (download approval) + crawler-config PR sta |
| 13 | G-GMO2023 | Guide to Medical Officers (Military Pensions) 2023 (Appendix-II) - ABS | 11 | 11 |  | 0 | B | C5-ACQ-09 (DESW) | A-C5-2 + robots |
| 14 | G-AO | Army Orders / Instructions (AO 45/2001 named; others by category) | 11 | 11 |  | 0 | C | custodian route (C6-04 AO-45-2001, AO-CA | scope extension P-C6-04-SCOPE + A-C5-3 |
| 15 | G-PRA-PT2 | Pension Regulations for the Army 2008 Part II | 9 | 9 |  | 0 | B | C5-ACQ-08 (DESW) | A-C5-2 + DESW allow-list PR + readable robots (403 |

Direct = the record has a crosswalk item that depends on the source. Upper bound = records that could be affected where the affected provisions are unknown (e.g. post-2022 Army Rules S.R.O.s could touch any rule, including the 42 exact anchors).

Every one of the 941 non-exact KB citation items is assigned to at least one gap row: YES.

**Priority order (combining dependent records, legal consequence and readiness):**
1. **Batch A Gazettes under A-C5-1** (already pinned): Army Act 1950 (185 records), AFT Act 2007 (89), BSA (64), BNSS (49), BNS (12) and the three 2024 commencement notifications (1 direct; 114 upper bound). These convert compilation-only reliance into enacted text; current text still needs the amendment chains.
2. **Provenance registration of already-held copies (no download):** 7 SC judgments and the 21 undocumented Army Rules Gazettes (AUTH-LEDGER tranches 1-2). Necessary but not sufficient for amended rules.
3. **AFT Procedure Rules 2008/2011 and Practice Rules 2009** (43 records) - already pinned in ACQ-03 (PR #23), needs A-C5-1 and C5 register reconciliation; and the **10 post-2022 Army Rules S.R.O.s** (pinned in C6-02; upper bound 188 records).
4. **Batch B (DESW) under A-C5-2**: PRA 2008 Pt I (25 records), Pt II (9), complete ER/GMO 2023 file (ER 3, GMO 11 records). Blocked by allow-list and robots 403.
5. **Commencement notifications:** AFT S.O. 14(E)/2008 and TRA 2026 s.1(2) notification(s) are in NO register (discovery approval needed); Army Act S.R.O. 120/1950 has a probable candidate (ACQ03-019, PR #23).
6. **CCCM Rules 1978 / S.O. 4010/1986** (8 records): pinned in ACQ-01-B2 (PR #8) - only A-C5-1 is needed; then the historical IPC/CrPC/IEA texts (discovery).
7. **Custodian route (scope extension needed):** RA 1987 + slips, RMSAF, named Army Orders, D&V handbook (lead only).

## 3a. Register reconciliation findings (not corrected here)

- **C5 does not carry forward candidates pinned in ACQ-01 / ACQ-03.** `COORDINATION/CYCLE3-PLANNING/acquisition_schedule.csv` and `ACQ-01/batches.json` hold pinned archive.org candidates for the CCCM Rules 1978 and S.O. 4010/1986 (ACQ-01-B2), the AFT Procedure Rules 2008, Amendment Rules 2011 and Practice Rules 2009 (ACQ03-030..032), the Army Act commencement notification (ACQ03-019, probable), Act 19/1955 and its appointing S.R.O. (ACQ-01-B6, ACQ03-020), ALO 1956, Ordinance 1975, Acts 56/1974 and 20/1983 (+ commencement), and Army Rules hint/OCR instruments (ACQ03-001..014, 036..039). The C5 master register records several of these as NOT_CHECKED / DISCOVERY_REQUIRED, and `D6_CORPUS_COVERAGE_MATRIX.md` says the CCCM items still need "locating". These are acquisition-readiness gaps, not discovery gaps.
- **GMO 2023 has a separate DESW URL** in ACQ-01-B4 (`desw.gov.in/sites/default/files/2026-10/GMO 2023.pdf`, not pinned) besides the combined 49.9 MB ER/GMO file in C6-03; not in PR #9.
- **Code V6-S07 (GMO 2023, 11 records) is UNMAPPED in the C5 crosswalk** although v3 resolves it; `corpus_source_map.csv` has no V6-S07 row.
- **PILOT-01 AMD-16** says a TRA 2021 corpus document is "HELD"; no such binary is in `held_binaries_manifest.csv`.
- **Air Force Act and Navy Act** have derived texts but no C5 source rows.
- **Baseline label:** "1,060 KB citation items" should read "1,060 crosswalk rows (983 citation items + 77 no-citation placeholders)".

## 4. Authorisations required (none granted; none exercised)

| item | what it authorises | needed for |
| --- | --- | --- |
| A-C5-1 | owner approval of real downloads of the pinned archive.org Gazettes, via a crawler-config PR stacked on #8 (adds *.archive.org; staging lists archive.org only) | C6-02 Batch A (18 pinned files) |
| A-C5-2 | owner approval of DESW downloads | C6-03 (PRA 2008, ER 2008, complete ER/GMO 2023, circulars) |
| A-C5-3 | approval of custodian request text and access-marking handling | C6-04 drafts (CUSTODIAN_REQUEST_DRAFTS.md) |
| P-C7-02-META | metadata-only archive.org route for the 2 unpinned DPP identifiers (guard change, mocked tests, logged run) | pinning C5C-026/027; A-C5-1 still needed to download |
| Allow-list extension | config PR adding the DESW file paths beyond the single ER/GMO 2023 URL in draft PR #9 | C6-03 |
| Robots | a later successful robots read of desw.gov.in (currently 403 => fail-closed) or an owner-side manual retrieval with sha256 recorded | C6-03 |
| Scope extension P-C6-04-SCOPE | narrow extension of CLAUDE.md scope to named publications (RA 1987, RMSAF, named AOs) with access-marking handling | C6-04; Army Orders are otherwise out of scope |
| Discovery approval | guarded discovery for instruments with no candidate in any register (AFT S.O. 14(E)/2008, TRA 2026 s.1(2) notification(s), TRA 2021, Finance Act 2017, S.O. 3912(E)/2019, RAA 1957, IPC/CrPC/IEA historical texts, Air Force/Navy Act Gazettes, ISO Act/Rules) | new gaps raised in C8-D |
| PR #8 / PR #23 stack | approval and merge of the existing unmerged config PRs that already pin CCCM (ACQ-01-B2), Act 19/1955 (B6), AFT Procedure/Practice Rules and Army Act amending instruments (ACQ-03) | items already pinned outside C5 |

## 5. Limitations

- Technical inventory only; nothing here is legal advice, a legal-status finding or a currency claim.
- Compilation footnotes and derived texts were read only to identify what is missing; they are never treated as commencement or amendment evidence.
- Text-layer readings (PyMuPDF) of held PDFs were used for the AFT, Army Act, BNSS, BSA compilations and TRA 2026; they were not page-image checked in C8. Needles are re-verifiable with `--verify-held`.
- Text-mention dependencies (pension historical regimes, IPC/CrPC/IEA, Air Force/Navy Acts) are keyword-based and indicative; coded dependencies come from the crosswalk and v3 code resolution.
- Section-overlap dependencies parse section/rule numbers from register text; parenthesised sub-units are ignored, so overlaps are at section/rule level.
- Archive.org pins come from Cycle 5 metadata and could not be re-verified offline; none of the 20 identifiers is in a committed snapshot.
- The baseline discrepancy is a definitional one; no register was edited.

## 6. Output files

- `BASELINE_RECOMPUTE.md`, `baseline_recompute.csv`
- `statutory_source_matrix.csv`, `statutory_source_matrix.md`
- `amendment_commencement_matrix.csv`, `amendment_commencement_matrix.md`
- `c6_02_readiness.csv`, `c6_02_readiness.md`
- `pension_source_coverage.csv`, `pension_record_dependency.csv`, `pension_source_coverage.md`
- `regulations_custodian_inventory.csv`, `CUSTODIAN_REQUEST_DRAFTS.md`
- `source_to_record_gap_matrix.csv`
- `PRIMARY_SOURCES_C8_FINDINGS.md` (this file)
- `OUTPUT_SHA256SUMS`
- `tools/build_c8_d.py`, `tools/inputs/held_page_readings.csv`, `tools/inputs/derived_text_readings.csv`, `tools/inputs/held_md5.csv`
