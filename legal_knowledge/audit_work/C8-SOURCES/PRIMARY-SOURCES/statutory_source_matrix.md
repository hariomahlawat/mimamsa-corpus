# C8-D Task 2: priority statutory instrument completeness matrix

Source: `statutory_source_matrix.csv` (90 rows). Categories are kept apart: **ORIGINAL_ENACTMENT** (Gazette/notified text), **OFFICIAL_CONSOLIDATION** (India Code compilation of the instrument as amended), **OFFICIAL_TEXT_RENDERING** (government-hosted text rendering of a single instrument; neither a consolidation nor a Gazette image), **AUTHORITATIVE_AMENDMENT** (amending instrument as published), **NOTIFICATION** (commencement / declarations), **SECONDARY_COMPILATION** (manuals, correspondence tables, parliamentary records), **INCOMPLETE_EXTRACT**, **NO_RELIABLE_COPY** (including derived text with no source binary). A consolidation is never treated as the enactment, and no current text is reconstructed from an old enactment plus an incomplete amendment list.

Commencement: where an Act or Rules commence by a separate notification that is not held, the row carries **COMMENCEMENT NOTIFICATION REQUIRED**. Compilation footnotes naming a date are recorded as such and are not treated as evidence of commencement.

| instrument | original enactment held | consolidation held | commencement notification held | amending instrument rows (held / not held or not located) | KB items (crosswalk) | KB records (crosswalk) | KB records (text mention) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Army Act 1950 (Act 46 of 1950) and amending Acts | NO | YES (e47a4265*) | NO | 3 / 7 | 190 | 185 | 77 |
| Army Rules 1954 (S.R.O. 484 of 27-11-1954) and amending S.R.O.s | YES (c5ef95a9) | YES (48f52219*) | n/a (none recorded) | 22 / 5 | 204 | 188 | 80 |
| Armed Forces Tribunal Act 2007 (Act 55 of 2007), amendments (Finance Act 2017; TRA 2021; TRA 2026) and AFT Procedure/Practice Rules | NO | YES (665863d1*, 48f57c81*) | NO | 1 / 3 | 135 | 102 | 28 |
| Bharatiya Nyaya Sanhita 2023 (Act 45 of 2023) | NO | derived text only | NO | 0 / 0 | 12 | 12 | 11 |
| Bharatiya Nagarik Suraksha Sanhita 2023 (Act 46 of 2023) | NO | YES (572c7988*) | NO | 0 / 0 | 50 | 49 | 31 |
| Bharatiya Sakshya Adhiniyam 2023 (Act 47 of 2023) | NO | YES (554b2b4a*) | NO | 0 / 0 | 64 | 64 | 65 |
| Indian Penal Code 1860 (historical) | NO | NO | n/a (none recorded) | 0 / 0 | 0 | 0 | 8 |
| Code of Criminal Procedure 1973 (historical) | NO | derived text only | n/a (none recorded) | 0 / 0 | 0 | 0 | 9 |
| Indian Evidence Act 1872 (historical) | NO | derived text only | n/a (none recorded) | 0 / 0 | 0 | 0 | 8 |
| Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978 and S.O. 4010 of 1986 | NO | NO | n/a (none recorded) | 0 / 1 | 8 | 8 | 5 |
| Army and Air Force (Disposal of Private Property) Act 1950 and Amendment Act 2000 | NO | NO | n/a (none recorded) | 0 / 2 | 0 | 0 | 0 |
| Air Force Act 1950 (Act 45 of 1950) | NO | derived text only | n/a (none recorded) | 0 / 0 | 0 | 0 | 0 |
| Navy Act 1957 (Act 62 of 1957) | NO | derived text only | n/a (none recorded) | 0 / 0 | 0 | 0 | 0 |
| Inter-Services Organisations (Command, Control and Discipline) Act 2023 and Rules 2025 | NO | NO | n/a (none recorded) | 0 / 0 | 4 | 2 | 1 |

`*` = held copy whose retrieval provenance is undocumented (copy_evidence_class PROVENANCE_UNDOCUMENTED_COPY); such copies cannot anchor exactly.

## Key gaps per instrument

**Army Act 1950 (Act 46 of 1950) and amending Acts**
- `D-SSM-001` ORIGINAL_ENACTMENT: Army Act 1950 as enacted: Gazette of India Extraordinary No.306 of 1950 - ORIGINAL_ENACTMENT_NOT_HELD (route: C5-ACQ-01; archive.org in.gazette.e.1950.306/E-2350-1950-0011-109089.pdf (md5 68bcdd4e8db91eb83d1e6b92a393b2db, 6491633 bytes; pinned); approval A-C5-1)
- `D-SSM-002` OFFICIAL_CONSOLIDATION: India Code compilation "As on the 21st July, 2025" (51 pp.) - CONSOLIDATION_NOT_ENACTMENT; PROVENANCE_UNDOCUMENTED
- `D-SSM-003` NOTIFICATION: Commencement of the Act under s.1(2): S.R.O. 120 of 22-07-1950 (named only in a compilation footnote) - COMMENCEMENT NOTIFICATION REQUIRED (route: not in C5 acquisition_register / C6-02; probable candidate in ACQ-03 (PR #23, unmerged): ACQ03-019 [ACQ-03 B4 (archive_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); md5=c99cf4895e8f7d565cd739d2f411cd0e; bytes=130078] https://archive.org/download/in.gazette.1950.318/O-2345-1950-0013-108766.pdf)
- `D-SSM-004` AUTHORITATIVE_AMENDMENT: Army (Amendment) Act 1992 (37 of 1992): India Code Gazette scan - COMMENCEMENT_NOT_STATED (AQ-05 preserved)
- `D-SSM-005` AUTHORITATIVE_AMENDMENT: Army (Amendment) Act 1992: second held copy (PDF trailer /ID variant) - DUPLICATE_COPY (C5-CF-C5-01 CLOSED_TECHNICAL)
- `D-SSM-006` OFFICIAL_TEXT_RENDERING: Army (Amendment) Act 1992: India Code text rendering (3 pp.; not a Gazette image) - TEXT_RENDERING_NOT_GAZETTE
- `D-SSM-007` AUTHORITATIVE_AMENDMENT: Air Force and Army Laws (Amendment) Act 1975 (13 of 1975): Gazette Extraordinary (2 pp.) - PROVENANCE_UNDOCUMENTED; COMMENCEMENT_NOT_DETERMINED
- `D-SSM-008` INCOMPLETE_EXTRACT: Commanders-in-Chief (Change in Designation) Act 1955 (19 of 1955): India Code repealed-record text, 1 page - INCOMPLETE_EXTRACT; COMMENCEMENT NOTIFICATION REQUIRED (route: ACQ-01:act-commanders-in-chief-change-designation-1955 [ACQ-01-B6 (configured in PR #8 (unmerged)); PREPARED — NOT EXECUTED; md5=6371b6ad0a8885ebf339200846044a21; bytes=92935] https://archive.org/download/in.gazette.e.1955.613/E-2210-1955-0031-101567.pdf || ACQ03-020 [ACQ-03 B4 (archive_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); md5=00dfb70630574c20c8a7e94be4502b57; bytes=21902] https://archive.org/download/in.gazette.e.1955.15/E-2210-1955-0002-101603.pdf)
- `D-SSM-009` NO_RELIABLE_COPY: Adaptation of Laws (No.3) Order 1956 (see also AA-C3-01) - AMENDMENT_INSTRUMENT_NOT_HELD (route: ACQ03-021 [ACQ-03 B4 (archive_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); md5=cfc5cb5cf1cdeac4cb34784b705d7639; bytes=1058089] https://archive.org/download/in.gazette.e.1956.717/E-2189-1956-0415-100172.pdf)
- `D-SSM-010` NO_RELIABLE_COPY: Repealing and Amending Act 1974 (56 of 1974) - AMENDMENT_INSTRUMENT_NOT_HELD (route: ACQ03-015 [ACQ-03 B3 (archive_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); md5=7b057ed27bc13f8413777322f229e9f8; bytes=609985] https://archive.org/download/in.gazette.e.1974.333/E-1272-1974-0084-56281.pdf)
- `D-SSM-011` NO_RELIABLE_COPY: Air Force and Army Laws (Amendment) Ordinance 1975 - AMENDMENT_INSTRUMENT_NOT_HELD (route: ACQ03-022 [ACQ-03 B4 (archive_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); md5=5d1011da90899da51a9c292580f1b391; bytes=95670] https://archive.org/download/in.gazette.csl_extraordinary.1975-01-25.E-1236-1975-0004-54581/E-1236-1975-0004-54581.pdf)
- `D-SSM-012` NO_RELIABLE_COPY: Act 20 of 1983 (Delegated Legislation Provisions (Amendment) Act per compilation list; s.193A) - AMENDMENT_INSTRUMENT_NOT_HELD; COMMENCEMENT NOTIFICATION REQUIRED (route: ACQ03-023 [ACQ-03 B4 (archive_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); md5=0f040ff6e5774797881ce86d2e46f050; bytes=1076879] https://archive.org/download/in.gazette.e.1983.330/E-0913-1983-0023-39490.pdf || ACQ03-024 [ACQ-03 B4 (archive_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); md5=6280672cd4f711d5cfc76edd381fd9ca; bytes=41367] https://archive.org/download/in.gazette.e.1984.465/E-0871-1984-0057-37466.pdf)
- `D-SSM-013` NO_RELIABLE_COPY: Notification S.O. 3912(E) of 30-10-2019 (application to UT of J&K and Ladakh, per compilation note) - AMENDMENT_INSTRUMENT_NOT_HELD (route: ACQ-C3-05 [WS-A cycle 3 (not configured; no config PR exists); NO_LAWFUL_ONLINE_SOURCE_KNOWN (not located); NOT_PINNED])
- `D-SSM-014` NO_RELIABLE_COPY: Repealing and Amending Act 1957 (36 of 1957) (s.194 and Schedule repealed) - AMENDMENT_INSTRUMENT_NOT_HELD (route: ACQ-C3-06 [WS-A cycle 3 (not configured; no config PR exists); NO_LAWFUL_ONLINE_SOURCE_KNOWN (not located); NOT_PINNED])
- `D-SSM-015` NO_RELIABLE_COPY: Any amending Act after 1992 (NOT_FOUND in searched sources; not proof of none) - AMENDMENT_INSTRUMENT_NOT_HELD (route: ACQ03-027 [ACQ-03 B4 (not configured (no lawful online source known)); NO_LAWFUL_ONLINE_SOURCE_KNOWN; NOT_PINNED])
- `D-SSM-016` NOTIFICATION: Gazette notifications under the Army Act (s.4 application, s.9 active service, etc.) - NOT_CHECKED (route: DISCOVERY_REQUIRED (phase 6))
- `D-SSM-017` SECONDARY_COMPILATION: Manual of Military Law vol 2 (Army Act) owner-supplied file - SECONDARY_ONLY
- `D-SSM-018` SECONDARY_COMPILATION: Manual of Military Law vol 2 (Army Act) owner-supplied file - SECONDARY_ONLY

**Army Rules 1954 (S.R.O. 484 of 27-11-1954) and amending S.R.O.s**
- `D-SSM-019` ORIGINAL_ENACTMENT: Army Rules 1954 as notified: S.R.O. 484, Gazette Pt II s.4 No.47, 27-11-1954 (88-page issue) - COMMENCEMENT_NOT_STATED (AQ-05 preserved)
- `D-SSM-020` OFFICIAL_CONSOLIDATION: India Code compilation (214 pp.) - CONSOLIDATION_NOT_ENACTMENT; PROVENANCE_UNDOCUMENTED
- `D-SSM-022` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 1 (1961-12-22); Pt II-S4 No.1, 06-01-1962, p.1 - PROVENANCE_UNDOCUMENTED
- `D-SSM-023` NOTIFICATION: Army Rules r.188(e) declaration Gazette (not an amendment): S.R.O. 34 (1963-01-05 (notes misdate as 05-06-1963)); Pt II-S4 No.3, 19-01-1963, p.14 - R188E_DECLARATION_NOT_AMENDMENT; PROVENANCE_UNDOCUMENTED
- `D-SSM-024` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 126 (1964-03-12); Pt II-S4, 28-03-1964, p.282 - PROVENANCE_UNDOCUMENTED
- `D-SSM-025` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 116 (1965-03-27); Pt II-S4 No.15, 10-04-1965, pp.96-97 - PROVENANCE_UNDOCUMENTED
- `D-SSM-026` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 215 (1965-06-17); Pt II-S4 No.27, 03-07-1965, p.172 - PROVENANCE_UNDOCUMENTED
- `D-SSM-027` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 5 (1968-12-23); Pt II-S4 No.2, 11-01-1969, pp.9-10 - PROVENANCE_UNDOCUMENTED
- `D-SSM-028` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 188 (1979-06-04); Pt II-S4 No.30, 28-07-1979, pp.258-261 - PROVENANCE_UNDOCUMENTED
- `D-SSM-029` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 246 (1982-10-12); Pt II-S4, 13-11-1982, p.413 - PROVENANCE_UNDOCUMENTED
- `D-SSM-030` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 44 (1985) (1985-01-24); Pt II-S4, 16-02-1985, p.60 - PROVENANCE_UNDOCUMENTED
- `D-SSM-031` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 55 (1985-02-22); Pt II-S4, 09-03-1985, p.97 - PROVENANCE_UNDOCUMENTED
- `D-SSM-032` AUTHORITATIVE_AMENDMENT: Army Rules corrigendum Gazette: S.R.O. 68 (1985-04-01); Pt II-S4, 20-04-1985, p.142 - PROVENANCE_UNDOCUMENTED
- `D-SSM-033` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 278 (1985-11-29); Pt II-S4, 28-12-1985, pp.531-532 - PROVENANCE_UNDOCUMENTED
- `D-SSM-034` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 169 (1987-05-15); Pt II-S4, 30-05-1987, p.197 - PROVENANCE_UNDOCUMENTED
- `D-SSM-035` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 302 (1987-09-18); Pt II-S4, 10-10-1987, p.367 - PROVENANCE_UNDOCUMENTED
- `D-SSM-036` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 216 (1988-08-30); Pt II-S4 No.36, 17-09-1988, p.617 - PROVENANCE_UNDOCUMENTED
- `D-SSM-037` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 332 (1989-09-26); Pt II-S4, 02-12-1989, p.736 - PROVENANCE_UNDOCUMENTED
- `D-SSM-038` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 44 (1991) (1991-02-01); S.R.O. 61 (1991-02-07); Pt II-S4, 23-02-1991, p.214 - PROVENANCE_UNDOCUMENTED
- `D-SSM-039` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 235 (1991-10-01); Pt II-S4, 09-11-1991, p.614 - PROVENANCE_UNDOCUMENTED
- `D-SSM-042` NOTIFICATION: Army Rules r.188(e) declaration Gazette (not an amendment): S.R.O. 2(E) (2018-02-20); Pt II-S4 Extraordinary, 20-02-2018, p.2 - R188E_DECLARATION_NOT_AMENDMENT; PROVENANCE_UNDOCUMENTED
- `D-SSM-043` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 17(E) (2019-12-28); Pt II-S4 Extraordinary No.13, 28-12-2019, p.2 - PROVENANCE_UNDOCUMENTED; SIGNATURE_DOES_NOT_VERIFY (T1-20)
- `D-SSM-044` AUTHORITATIVE_AMENDMENT: Army Rules amendment Gazette: S.R.O. 6(E) (2022-06-06); Pt II-S4 Extraordinary No.06, 06-06-2022, p.2 - PROVENANCE_UNDOCUMENTED
- `D-SSM-045` NO_RELIABLE_COPY: E-7 (7(E)) (1960-06-17 (2003 Hindi note: 16-07-1960)) - instrument not found - AMENDMENT_INSTRUMENT_NOT_LOCATED (route: ACQ03-026 [ACQ-03 B4 (not configured (no lawful online source known)); NO_LAWFUL_ONLINE_SOURCE_KNOWN; NOT_PINNED])
- `D-SSM-046` NO_RELIABLE_COPY: S.R.O. 258 (2002-11-27) - instrument not found - AMENDMENT_INSTRUMENT_NOT_LOCATED (route: ACQ03-028 [ACQ-03 B4 (not configured (no lawful online source known)); NO_LAWFUL_ONLINE_SOURCE_KNOWN; NOT_PINNED])
- `D-SSM-047` NO_RELIABLE_COPY: 10 possible Army Rules S.R.O.s 2022-06-23..2026-06-24 (subject unconfirmed) + AR-036 (not searched authoritatively) - AMENDMENT_CHAIN_OPEN_AFTER_2022-06-06 (route: C5-ACQ-06 (10 files pinned in C6-02); approval A-C5-1; ACQ03-027 [ACQ-03 B4 (not configured (no lawful online source known)); NO_LAWFUL_ONLINE_SOURCE_KNOWN; NOT_PINNED])
- `D-SSM-048` NO_RELIABLE_COPY: 5 instruments located from a text layer only: S.R.O. 331 1960-09-23; S.R.O. 348 1960-10-03; S.R.O. 351 1960-10-07; S.R.O. 404 1960-11-21; S.R.O. 22 2010-05-13 - TEXT_LAYER_ONLY (route: candidates pinned in ACQ-03 (PR #23, unmerged): ACQ03-010, ACQ03-011, ACQ03-012, ACQ03-013, ACQ03-014)
- `D-SSM-049` NO_RELIABLE_COPY: 13 full-text-search hints not opened (AR-012, AR-013, AR-015, AR-037, AR-038, AR-039, AR-040, AR-041, AR-042, AR-043, AR-044, AR-045, AR-046) - HINT_ONLY (route: candidates in ACQ-03 (PR #23, unmerged): AR-012->ACQ03-001 (year match only (probable)); AR-013->ACQ03-002,ACQ03-003 (year match only (probable)); AR-015->ACQ03-008,ACQ03-009 (year match only (probable)); AR-037->ACQ03-036 (date match); AR-038->ACQ03-037 (date match); AR-039->ACQ03-038 (date match); AR-040->ACQ03-039 (date match); AR-041->ACQ03-003 (date match); AR-042->ACQ03-004 (date match); AR-043->ACQ03-005 (date match); AR-044->ACQ03-006 (date match); AR-045->ACQ03-007 (date match); AR-046->ACQ03-008 (date match))
- `D-SSM-050` ORIGINAL_ENACTMENT: Interim rules under AA ss.21, 102(4) and 191 (Gazette Extraordinary No.8, 1950) - historical layer - HISTORICAL_LAYER_NOT_HELD (route: archive.org candidate C5C-002 (historical layer))
- `D-SSM-051` SECONDARY_COMPILATION: Manual of Military Law vol 2 (Army Rules) owner-supplied file - SECONDARY_ONLY
- `D-SSM-052` SECONDARY_COMPILATION: Manual of Military Law vol 2 (Army Rules) owner-supplied file - SECONDARY_ONLY

**Armed Forces Tribunal Act 2007 (Act 55 of 2007), amendments (Finance Act 2017; TRA 2021; TRA 2026) and AFT Procedure/Practice Rules**
- `D-SSM-053` ORIGINAL_ENACTMENT: AFT Act 2007 as enacted: Gazette Extraordinary Pt II s.1, 28-12-2007 - ORIGINAL_ENACTMENT_NOT_HELD (route: C5-ACQ-02; in.gazette.central.e.2007-12-28.020/020.pdf (md5 4cf633923182d8a4d87a9ad9d51f3c11, 574004 bytes); duplicate item C5C-017 identical md5; A-C5-1)
- `D-SSM-054` OFFICIAL_CONSOLIDATION: India Code compilation (English) "As on the 1st September, 2026" (16 pp.) - CONSOLIDATION_NOT_ENACTMENT; PROVENANCE_UNDOCUMENTED
- `D-SSM-055` OFFICIAL_CONSOLIDATION: India Code compilation (Hindi) (13 pp.) - CONSOLIDATION_NOT_ENACTMENT
- `D-SSM-056` NOTIFICATION: Commencement of the Act under s.1(2): Notifn. S.O. 14(E) of 13-06-2008 (named only in a compilation footnote; date stated 15-06-2008) - COMMENCEMENT NOTIFICATION REQUIRED (route: NOT REGISTERED: string "S.O. 14(E)" NOT FOUND in acquisition_register.csv / c6_02_batch_a_files.csv / COORDINATION acquisition_schedule.csv; discovery required)
- `D-SSM-057` NO_RELIABLE_COPY: Finance Act 2017 (7 of 2017) s.181 (inserted s.9A; compilation says w.e.f. 26-5-2017) - AMENDMENT_INSTRUMENT_NOT_HELD; NOT_REGISTERED; NOTIFICATION_STATUS_UNKNOWN (instrument not held) (route: discovery required (Gazette of India 2017))
- `D-SSM-058` NO_RELIABLE_COPY: Tribunals Reforms Act 2021 (33 of 2021) (listed as an amending Act; no footnote in the held compilation shows which AFT provisions it changed) - AMENDMENT_INSTRUMENT_NOT_HELD; NOT_REGISTERED; PROVISIONS_AFFECTED_UNKNOWN (route: discovery required (Gazette of India 2021))
- `D-SSM-059` AUTHORITATIVE_AMENDMENT: Tribunals Reforms Act 2026 (17 of 2026): Gazette Extraordinary Pt II s.1 No.31, 13-08-2026 (15 pp.) - PROVENANCE_UNDOCUMENTED; COMMENCEMENT NOTIFICATION REQUIRED
- `D-SSM-060` NOTIFICATION: Commencement notification(s) for TRA 2026 under s.1(2) (compilation footnote says s.9A substitution w.e.f. 25-08-2026) - COMMENCEMENT NOTIFICATION REQUIRED (route: not registered; discovery required (egazette 2026))
- `D-SSM-061` NO_RELIABLE_COPY: Armed Forces Tribunal (Procedure) Rules 2008 (Gazette Extraordinary Pt II s.4, 17-09-2008 per derived OCR) - DERIVED_TEXT_ONLY (route: C5 says DISCOVERY_REQUIRED, but candidates exist in ACQ-03 (PR #23, unmerged): ACQ03-030 [ACQ-03 B5 (archive_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); md5=50cb5c011bf60c3b800e235061e8eb4e; bytes=760396] https://archive.org/download/in.gazette.central.e.2008-09-17.2326/2326.pdf || ACQ03-033 [ACQ-03 B5 (official_instruments_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); NOT_PINNED (listing md5=c08af236bfd7c5bf79d25a858226d8f3, bytes=46767577 informational only: host watermarks PDFs; served SHA-256 to be recorded)] https://indiacode.gov.in/server/api/core/bitstreams/3a17342b-6811-4e2c-98c8-fc4954bf5a53/content)
- `D-SSM-062` NO_RELIABLE_COPY: AFT (Procedure) Amendment Rules 2011 and AFT Practice Rules 2009 - NOT_HELD; AMENDMENT_INSTRUMENT_NOT_HELD (2011 Rules) (route: candidates in ACQ-03 (PR #23, unmerged): ACQ03-031 [ACQ-03 B5 (archive_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); md5=b3539b33452f645260495b00ad30fb6b; bytes=53537] https://archive.org/download/in.gazette.central.e.2011-07-29.188/188.pdf || ACQ03-032 [ACQ-03 B5 (archive_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); md5=e57de9958b8c03ee23530db1c4626f06; bytes=4805182] https://archive.org/download/in.gazette.central.e.2009-05-13.5014/5014.pdf || ACQ03-034 [ACQ-03 B5 (official_instruments_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); NOT_PINNED (listing md5=dae2291aa84a37ea271b896340739ec6, bytes=163806 informational only: host watermarks PDFs; served SHA-256 to be recorded)] https://indiacode.gov.in/server/api/core/bitstreams/5a416087-b3bd-4fa5-8fc8-e9b6768f2966/content || ACQ03-035 [ACQ-03 B5 (official_instruments_acq03 (PR #23, unmerged)); CANDIDATE (not fetched); NOT_PINNED (listing md5=0fa7231285f2022db43a0150fb5817ea, bytes=1441674 informational only: host watermarks PDFs; served SHA-256 to be recorded)] https://indiacode.gov.in/server/api/core/bitstreams/18a102cd-fbb9-49de-9e80-b0c553ff25dd/content)

**Bharatiya Nyaya Sanhita 2023 (Act 45 of 2023)**
- `D-SSM-063` ORIGINAL_ENACTMENT: Bharatiya Nyaya Sanhita 2023 as enacted: Gazette Extraordinary 25-12-2023 - ORIGINAL_ENACTMENT_NOT_HELD (route: C5-ACQ-20; in.gazette.central.e.2023-12-25.250883/250883.pdf (md5 5639d038c8464645e42a9b7ddaa6d7be, 1382923 bytes; pinned); A-C5-1)
- `D-SSM-064` NO_RELIABLE_COPY: India Code compilation "As on the 6th October, 2025" - derived text only - DERIVED_TEXT_ONLY
- `D-SSM-065` NOTIFICATION: Commencement notification (BNS 2023 commencement notification under s.1(2)); stated in the consolidation footnote only - COMMENCEMENT NOTIFICATION REQUIRED (route: C5-ACQ-05; in.gazette.central.e.2024-02-24.252353/252353.pdf (md5 393d0cd8277d823bfeb38113b0ae707d, 922134 bytes; pinned); A-C5-1)

**Bharatiya Nagarik Suraksha Sanhita 2023 (Act 46 of 2023)**
- `D-SSM-066` ORIGINAL_ENACTMENT: Bharatiya Nagarik Suraksha Sanhita 2023 as enacted: Gazette Extraordinary 25-12-2023 - ORIGINAL_ENACTMENT_NOT_HELD (route: C5-ACQ-03; in.gazette.central.e.2023-12-25.250884/250884.pdf (md5 34490767b89234e6217b55e7d30dc3b6, 2033181 bytes; pinned); A-C5-1)
- `D-SSM-067` OFFICIAL_CONSOLIDATION: India Code compilation "As on the 6th October, 2025" - CONSOLIDATION_NOT_ENACTMENT; PROVENANCE_UNDOCUMENTED
- `D-SSM-068` NOTIFICATION: Commencement notification (BNSS 2023 commencement notification under s.1(3)); stated in the consolidation footnote only - COMMENCEMENT NOTIFICATION REQUIRED (route: C5-ACQ-05; in.gazette.central.e.2024-02-24.252354/252354.pdf (md5 af9e7e74b1f50f549ae6ab74e9747b58, 924297 bytes; pinned); A-C5-1)

**Bharatiya Sakshya Adhiniyam 2023 (Act 47 of 2023)**
- `D-SSM-069` ORIGINAL_ENACTMENT: Bharatiya Sakshya Adhiniyam 2023 as enacted: Gazette Extraordinary 25-12-2023 - ORIGINAL_ENACTMENT_NOT_HELD (route: C5-ACQ-04; in.gazette.central.e.2023-12-25.250882/250882.pdf (md5 90822f55c6dea27049c76d29ca26d707, 1218408 bytes; pinned); A-C5-1)
- `D-SSM-070` OFFICIAL_CONSOLIDATION: India Code compilation "As on the 6th October, 2025" - CONSOLIDATION_NOT_ENACTMENT; PROVENANCE_UNDOCUMENTED
- `D-SSM-071` NOTIFICATION: Commencement notification (BSA 2023 commencement notification under s.1(3)); stated in the consolidation footnote only - COMMENCEMENT NOTIFICATION REQUIRED (route: C5-ACQ-05; in.gazette.central.e.2024-02-24.252352/252352.pdf (md5 6288ffbc08004bbe858e6c4450524dc2, 922833 bytes; pinned); A-C5-1)

**Indian Penal Code 1860 (historical)**
- `D-SSM-072` ORIGINAL_ENACTMENT: Indian Penal Code 1860 (historical) as enacted / as last amended before repeal - NO_RELIABLE_COPY; HISTORICAL_VERSION_NOT_IDENTIFIED (route: DISCOVERY_REQUIRED (not searched in C5))
- `D-SSM-073` SECONDARY_COMPILATION: section correspondence table data/correspondence/bns-ipc.jsonl (525 lines) - SECONDARY_ONLY

**Code of Criminal Procedure 1973 (historical)**
- `D-SSM-074` ORIGINAL_ENACTMENT: Code of Criminal Procedure 1973 (historical) as enacted / as last amended before repeal - NO_RELIABLE_COPY; HISTORICAL_VERSION_NOT_IDENTIFIED (route: DISCOVERY_REQUIRED (not searched in C5))
- `D-SSM-075` NO_RELIABLE_COPY: derived text rendering (edition/as-on date not printed) - DERIVED_TEXT_ONLY
- `D-SSM-076` SECONDARY_COMPILATION: section correspondence table data/correspondence/bnss-crpc.jsonl (487 lines) - SECONDARY_ONLY
- `D-SSM-080` SECONDARY_COMPILATION: BPRD BNSS-CrPC comparison (derived text) - SECONDARY_ONLY

**Indian Evidence Act 1872 (historical)**
- `D-SSM-077` ORIGINAL_ENACTMENT: Indian Evidence Act 1872 (historical) as enacted / as last amended before repeal - NO_RELIABLE_COPY; HISTORICAL_VERSION_NOT_IDENTIFIED (route: DISCOVERY_REQUIRED (not searched in C5))
- `D-SSM-078` NO_RELIABLE_COPY: derived text rendering (edition/as-on date not printed) - DERIVED_TEXT_ONLY
- `D-SSM-079` SECONDARY_COMPILATION: section correspondence table data/correspondence/bsa-iea.jsonl (182 lines) - SECONDARY_ONLY

**Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978 and S.O. 4010 of 1986**
- `D-SSM-081` NO_RELIABLE_COPY: Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978 (S.O. 488, MHA, 09-02-1978; Gazette 25-02-1978) - NOT_HELD; C5_REGISTER_NOT_RECONCILED_WITH_ACQ-01 (route: ACQ-01:rules-adjustment-jurisdiction-1978-so-488 [ACQ-01-B2 (configured in PR #8 (unmerged)); PREPARED — NOT EXECUTED; md5=91b0dd7aab747fe5260b1ffe61fd4d1d; bytes=5923089] https://archive.org/download/in.gazette.central.w.1978-02-25.48290/48290.pdf)
- `D-SSM-082` NO_RELIABLE_COPY: Amendment Rules 1986: MHA Notification S.O. 4010 (dated 24-11-1986 per ACQ-01/PILOT-01; "dated 6th December 1986" per the C5 master title; Gazette 06-12-1986) - NOT_HELD; AMENDMENT_INSTRUMENT_NOT_HELD; DATE_DISCREPANCY_BETWEEN_REGISTERS (route: ACQ-01:notif-adjustment-jurisdiction-amdt-so-4010-1986 [ACQ-01-B2 (configured in PR #8 (unmerged)); PREPARED — NOT EXECUTED; md5=c5eaada91e55121d0e048542f4a0e68b; bytes=5891276] https://archive.org/download/in.gazette.central.w.1986-12-06.32435/32435.pdf)
- `D-SSM-083` SECONDARY_COMPILATION: Rajya Sabha Debates 03-03-1987 "Papers Laid on the Table" cols 207-208 (records laying of S.O. 4010/1986) - NOT_THE_INSTRUMENT

**Army and Air Force (Disposal of Private Property) Act 1950 and Amendment Act 2000**
- `D-SSM-084` ORIGINAL_ENACTMENT: Army and Air Force (Disposal of Private Property) Act 1950 (principal Act) - NO_RELIABLE_COPY (route: DISCOVERY_RETRY (India Code))
- `D-SSM-085` AUTHORITATIVE_AMENDMENT: Amendment Act 2000 (archive item in.gazette.central.e.2000-08-25.168; the two items may be the same Act) - NOT_HELD; UNPINNED (P-C7-02-META decision) (route: C5-ACQ-21; owner decision C6-02-D1 / P-C7-02-META)
- `D-SSM-086` AUTHORITATIVE_AMENDMENT: Amendment Act 2000 (archive item in.gazette.e.2000.379; the two items may be the same Act) - NOT_HELD; UNPINNED (P-C7-02-META decision) (route: C5-ACQ-21; owner decision C6-02-D1 / P-C7-02-META)
- `D-SSM-087` NO_RELIABLE_COPY: 1999 Bill to amend the Act (Gazette 1999-02-26) - NOT_HELD

**Air Force Act 1950 (Act 45 of 1950)**
- `D-SSM-088` NO_RELIABLE_COPY: India Code compilation "As on the 21st July, 2025" - derived text only - DERIVED_TEXT_ONLY; NOT_REGISTERED

**Navy Act 1957 (Act 62 of 1957)**
- `D-SSM-089` NO_RELIABLE_COPY: India Code compilation "As on the 1st June, 2026" - derived text only - DERIVED_TEXT_ONLY; NOT_REGISTERED

**Inter-Services Organisations (Command, Control and Discipline) Act 2023 and Rules 2025**
- `D-SSM-090` NO_RELIABLE_COPY: ISO (Command, Control and Discipline) Act 2023 and Rules 2025 - NOT_HELD; NOT_CHECKED (route: DISCOVERY_REQUIRED)

## Observations

- **Air Force Act 1950 and Navy Act 1957 have no C5 master-register row**; only derived India Code texts exist in the scratchpad (no source binary). They should be registered before any reliance.
- **AFT Act commencement notification S.O. 14(E)/2008 and the TRA 2026 commencement notification are not in any acquisition register** (C5 acquisition_register, C6-02 batch). They are new gaps raised here.
- **Tribunals Reforms Act 2021** is listed as an amending Act in the held AFT compilation (R02) but no footnote attributes any AFT provision to it, and it is repealed by TRA 2026 s.24(1) (R20). PILOT-01 `amendment_source_gaps.csv#AMD-16` says a corpus document for TRA 2021 is "HELD"; no such binary is in `held_binaries_manifest.csv`, so that claim is unverified.
- No KB record cites AFT s.9A, the only provision the held compilation attributes to Finance Act 2017 and TRA 2026.
- BNSS and BSA compilations (as on 06-10-2025) print no list of amending Acts; absence in a compilation is not proof of no amendment.
- IPC 1860 has no copy of any kind (not even derived text); CrPC 1973 and IEA 1872 exist only as derived text of unknown edition.

