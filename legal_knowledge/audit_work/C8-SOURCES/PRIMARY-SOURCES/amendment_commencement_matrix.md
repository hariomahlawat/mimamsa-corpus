# C8-D Task 3: amendment and commencement evidence matrix

Source: `amendment_commencement_matrix.csv` (105 rows). Army Rules and Army Act rows are carried from `SOURCE-LIBRARY-C5/registers/amendment_register.csv` with their recorded states **preserved verbatim** (`commencement_status_preserved`, `verification_status`, `amendment_chain_status`). AFT Act, TRA and BNS/BNSS/BSA rows are new and cite held page readings (`tools/inputs/held_page_readings.csv`). A commencement date appears in `commencement_date_evidenced` **only** where the instrument itself states it (STATED_IN_INSTRUMENT). Publication dates are never used as commencement dates.

| family | rows |
| --- | --- |
| AFT Act 2007 | 4 |
| AFT Act 2007 / TRA 2021 | 1 |
| AFT Procedure Rules | 1 |
| Army Act 1950 | 36 |
| Army Rules 1954 | 47 |
| Army Rules 1954 (reserved state) | 10 |
| BNS 2023 | 1 |
| BNS 2023 / IPC 1860 | 1 |
| BNSS 2023 | 1 |
| BNSS 2023 / CrPC 1973 | 1 |
| BSA 2023 | 1 |
| BSA 2023 / IEA 1872 | 1 |

## Commencement gaps by family

| family | commencement_gap | rows |
| --- | --- | --- |
| AFT Act 2007 | COMMENCEMENT NOTIFICATION REQUIRED | 2 |
| AFT Act 2007 | INSTRUMENT_NOT_HELD | 1 |
| AFT Act 2007 | NOTIFICATION_STATUS_UNKNOWN (instrument not held; whether s.181 commenced by a separate notification is not evidenced) | 1 |
| AFT Act 2007 / TRA 2021 | COMMENCEMENT NOTIFICATION REQUIRED | 1 |
| AFT Procedure Rules | INSTRUMENT_NOT_HELD | 1 |
| Army Act 1950 | COMMENCEMENT NOTIFICATION REQUIRED | 3 |
| Army Act 1950 | INSTRUMENT_NOT_HELD (known from compilation footnotes only) | 4 |
| Army Act 1950 | INSTRUMENT_NOT_LOCATED | 2 |
| Army Act 1950 | NOT_APPLICABLE | 7 |
| Army Act 1950 | NOT_DETERMINED (preserved) | 2 |
| Army Act 1950 | NOT_STATED_PENDING_ADVICE (AQ-05; preserved, no date inferred) | 18 |
| Army Rules 1954 | INSTRUMENT_NOT_LOCATED | 16 |
| Army Rules 1954 | NONE (commencement stated in the instrument) | 11 |
| Army Rules 1954 | NOT_APPLICABLE | 2 |
| Army Rules 1954 | NOT_DETERMINED (preserved) | 5 |
| Army Rules 1954 | NOT_STATED_PENDING_ADVICE (AQ-05; preserved, no date inferred) | 13 |
| Army Rules 1954 (reserved state) | n/a | 10 |
| BNS 2023 | COMMENCEMENT NOTIFICATION REQUIRED | 1 |
| BNS 2023 / IPC 1860 | COMMENCEMENT NOTIFICATION REQUIRED | 1 |
| BNSS 2023 | COMMENCEMENT NOTIFICATION REQUIRED | 1 |
| BNSS 2023 / CrPC 1973 | COMMENCEMENT NOTIFICATION REQUIRED | 1 |
| BSA 2023 | COMMENCEMENT NOTIFICATION REQUIRED | 1 |
| BSA 2023 / IEA 1872 | COMMENCEMENT NOTIFICATION REQUIRED | 1 |

## Reserved states preserved (not resolved)

- r.23(3): C-01 / U-01 **CONFLICTING** (retained until legal review); no located amending instrument 1963-2022 amends r.23 (R23-VERIFY-01).
- r.182: SC4-01 **OPEN** (S.R.O. 17(E)/1993 item 36 printed wording; no corrigendum searched or located).
- r.193: C-08 / U-07 **OPEN** (chronology incomplete; no correction proposed); U-04 discrepancy candidate.
- r.194: C-09 / U-08 **PROPOSAL** pending legal review (AQ-02).
- r.192: C-02 CONFLICTING; r.177: C-03 CONFLICTING pending text comparison.
- AQ-05 (instrument silent on commencement) and AQ-06 (retrospective deemed effect, AR-024 from 1979-06-04 as printed) remain adviser questions.

## New rows (outside the C5 amendment register)

- `D-AMC-AFT-00` Act 55 of 2007 (principal); appointing Notifn. S.O. 14(E) of 13-06-2008 - s.1(2) commencement of the whole Act: NOT_DETERMINED from primary evidence: compilation footnote states 15-06-2008 vide S.O. 14(E); commencement gap **COMMENCEMENT NOTIFICATION REQUIRED**.
- `D-AMC-AFT-01` Finance Act 2017 (7 of 2017) s.181 - s.9A (inserted): NOT_DETERMINED: compilation says w.e.f. 26-5-2017; commencement basis of the Finance Act provision not evidenced; commencement gap **NOTIFICATION_STATUS_UNKNOWN (instrument not held; whether s.181 commenced by a separate notification is not evidenced)**.
- `D-AMC-AFT-02` Tribunals Reforms Act 2021 (33 of 2021) - UNKNOWN (no footnote in the held compilation attributes any AFT provision to Act 33 of 2021): NOT_DETERMINED; commencement gap **INSTRUMENT_NOT_HELD**.
- `D-AMC-AFT-03` Tribunals Reforms Act 2026 (17 of 2026) s.18 and Second Schedule item 9 - s.9A (substituted): NOT_DETERMINED from primary evidence: s.1(2) commencement by notification; compilation says w.e.f. 25-08-2026; commencement gap **COMMENCEMENT NOTIFICATION REQUIRED**.
- `D-AMC-AFT-04` Tribunals Reforms Act 2026 s.24 - whole of TRA 2021 (repeal); savings for appointments and selections: NOT_DETERMINED: depends on the s.1(2) notification; commencement gap **COMMENCEMENT NOTIFICATION REQUIRED**.
- `D-AMC-AFT-05` subordinate legislation made under the AFT Act (rule-making provision not checked; not held) - whole (Procedure Rules 2008; Amendment Rules 2011 r.12A/r.7; Practice Rules 2009): NOT_DETERMINED; commencement gap **INSTRUMENT_NOT_HELD**.
- `D-AMC-BNS-COMM` commencement notification (Gazette Extraordinary 24-02-2024; archive in.gazette.central.e.2024-02-24.252353) - whole Act (commencement); any section-specific exception must be read from the notification: NOT_DETERMINED from primary evidence: consolidation/derived footnote states 01-07-2024 (derived text only); commencement gap **COMMENCEMENT NOTIFICATION REQUIRED**.
- `D-AMC-BNSS-COMM` commencement notification (Gazette Extraordinary 24-02-2024; archive in.gazette.central.e.2024-02-24.252354) - whole Act (commencement); any section-specific exception must be read from the notification: NOT_DETERMINED from primary evidence: consolidation/derived footnote states 01-07-2024 (compilation footnote); commencement gap **COMMENCEMENT NOTIFICATION REQUIRED**.
- `D-AMC-BSA-COMM` commencement notification (Gazette Extraordinary 24-02-2024; archive in.gazette.central.e.2024-02-24.252352) - whole Act (commencement); any section-specific exception must be read from the notification: NOT_DETERMINED from primary evidence: consolidation/derived footnote states 01-07-2024 (compilation footnote); commencement gap **COMMENCEMENT NOTIFICATION REQUIRED**.
- `D-AMC-BNSS-REPEAL` BNSS s.531 - CrPC 1973 whole (repeal); savings for pending matters: operative from BNSS commencement, which is not evidenced by a held notification; commencement gap **COMMENCEMENT NOTIFICATION REQUIRED**.
- `D-AMC-BSA-REPEAL` BSA s.170 - Indian Evidence Act 1872 whole (repeal); savings for pending matters: operative from BSA commencement, which is not evidenced by a held notification; commencement gap **COMMENCEMENT NOTIFICATION REQUIRED**.
- `D-AMC-BNS-REPEAL` BNS s.358 - IPC 1860 (repeal and savings under BNS s.358, cited by 6 KB items): NOT_DETERMINED: no BNS text held (derived text only); commencement gap **COMMENCEMENT NOTIFICATION REQUIRED**.

Historical applicability intervals are filled only where a chain row has a stated commencement; everywhere else the column says NOT EVIDENCED. The IPC/CrPC/IEA to BNS/BNSS/BSA transition date (01-07-2024) appears only in consolidation/derived footnotes and is therefore not evidenced by a primary document.
