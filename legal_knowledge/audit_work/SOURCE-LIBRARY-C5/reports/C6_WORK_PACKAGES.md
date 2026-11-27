# Cycle 6 work packages (prepared, NOT executed)

Nothing here is authorised. Each package needs the owner approval named against it. No external correspondence is authorised.

## C6-01: Recover provenance for existing held sources (no download)
- **Scope:** the 34 held official copies whose provenance is undocumented: 26 publications or records and 8 SC judgments (`registers/source_copy_register.csv`, `copy_evidence_class=PROVENANCE_UNDOCUMENTED_COPY`, excluding compilations and manuals). They are listed by `source_id` in `registers/source_master_register.csv` (`holding_state=*_PROVENANCE_UNDOCUMENTED`).
- **Evidence to search, read-only:**
  - PILOT-01 and CALIBRATION-02 `sources/*.json` (`locator`, `retrieved_on`, `retrieved_by`);
  - WS-A/WS-B/WS-D registers;
  - `ACQ-*/config_pr_evidence/`;
  - `ARMY-RULES-CHAIN-01` evidence locators;
  - archive.org identifiers embedded in held paths;
  - `downloads/*/item*.json` and `bundles*.json` metadata in the session scratchpad, where still available.
- **Output:** a *proposal* CSV with the same columns as `CALIBRATION-02/registers/source_authentication_register.csv`. Each proposed row must cite source-specific evidence (URL, retrieval record, metadata md5 match). Where none exists, write `NO_RECOVERABLE_PROVENANCE`; never reconstruct an acquisition history. Each proposed row also needs a page-image identity check.
- **Gate:** independent review, then a reviewed addendum to the register. Never an in-place edit.
- **Effect (to be measured, not assumed):** may turn some PARTIAL_MATCH crosswalk rows into EXACT_ANCHOR (for example, 7 case records).

## C6-02: Public Gazette acquisition (Batch A)
- **Approval:** A-C5-1. A new crawler-config PR is needed, separate from #7/#8/#17/#23. Host controls follow DISCOVERY_SAFETY_POLICY: archive.org robots policy established, HTTPS only, per-file md5 and size pins, PDF signature check, a single host and no redirects off-host.
- **Rights:** Government of India Gazette facsimiles. The archive.org carrier is recorded as THIRD_PARTY_ARCHIVAL_FACSIMILE. Private store only until the owner decides otherwise.
- **Validation after download:**
  1. sha256;
  2. md5 and size against the pin;
  3. page count;
  4. page-image identity check of the masthead (issue number, date, Part/Section);
  5. then a source-authentication register row via a reviewed addendum.
- **Duplicates with PR #23:** none is a configured download there. PR #23's matrix lists `in.gazette.e.1950.306` as 'Not configured (candidate located)'. Re-check the stack before configuring.

| id | item | location | pin |
| --- | --- | --- | --- |
| C5-ACQ-01 | Army Act 1950 as enacted (Gazette Extraordinary No.306, 1950) | https://archive.org/download/in.gazette.e.1950.306/E-2350-1950-0011-109089.pdf | md5 68bcdd4e8db91eb83d1e6b92a393b2db; 6491633 bytes |
| C5-ACQ-02 | AFT Act 2007 Gazette Extraordinary Pt II s.1, 2007-12-28 | https://archive.org/download/in.gazette.central.e.2007-12-28.020/020.pdf | md5 4cf633923182d8a4d87a9ad9d51f3c11; 574004 bytes |
| C5-ACQ-03 | BNSS 2023 Gazette Extraordinary 2023-12-25 | https://archive.org/download/in.gazette.central.e.2023-12-25.250884/250884.pdf | md5 34490767b89234e6217b55e7d30dc3b6; 2033181 bytes |
| C5-ACQ-04 | BSA 2023 Gazette Extraordinary 2023-12-25 | https://archive.org/download/in.gazette.central.e.2023-12-25.250882/250882.pdf | md5 90822f55c6dea27049c76d29ca26d707; 1218408 bytes |
| C5-ACQ-05 | Commencement notifications BNS/BNSS/BSA, Gazette Extraordinary 2024-02-24 (three items) | https://archive.org/download/in.gazette.central.e.2024-02-24.252352/252352.pdf ; .252353/252353.pdf ; .252354/252354.pdf | md5 6288ffbc08004bbe858e6c4450524dc2 / 393d0cd8277d823bfeb38113b0ae707d / af9e7e74b1f50f549ae6ab74e9747b58; 922833 / 922134 / 924297 bytes |
| C5-ACQ-06 | Ten MoD/DMA S.R.O. Gazette items 2022-06-23..2026-06-24 (possible Army Rules amendments) | archive.org in.gazette.central.e.{2022-06-23.236757, 2022-12-21.241268, 2023-05-30.246170, 2023-06-12.246457, 2024-05-22.254308, 2024-08-31.256844, 2025-04-23.262667, 2025-05-08.262992, 2026-01-30.269859, 2026-06-24.273809} | md5 per item in discovery/C_candidates.csv C5C-004..013 |
| C5-ACQ-20 | BNS 2023 Gazette Extraordinary 2023-12-25 | https://archive.org/download/in.gazette.central.e.2023-12-25.250883/250883.pdf | md5 5639d038c8464645e42a9b7ddaa6d7be; 1382923 bytes |
| C5-ACQ-21 | Army and Air Force (Disposal of Private Property) Amendment Act 2000 (Gazette 2000-08-25) | archive.org in.gazette.central.e.2000-08-25.168 / in.gazette.e.2000.379 | to be pinned from metadata |

## C6-03: Pension and entitlement sources (Batch B)
- **Approval:** A-C5-2, plus an extension of the DESW allow-list beyond PR #9 in a separate config PR.
- **Dependencies:**
  - PRA 2008 Pt I/II (C5-ACQ-07/08);
  - the complete ER/GMO 2023 publication (C5-ACQ-09). It is the only located source of GMO-2023, which is absent from the held 13 MB copy;
  - both ER 2008 files (C5-ACQ-10), to resolve C5-CF-C5-02;
  - the PRA/ER circulars (C5-ACQ-11).
- **Then:** read-only paging of the DESW circular archive (pages 4–33+) for ER 1982 and PRA 1961.
- **Validation:** sha256; size against HEAD Content-Length; PDF signature; title-page identity; letter number and date from the image. The trigger date for ER 2023 stays a legal question (LAQ-03).

| id | item | location | size pin |
| --- | --- | --- | --- |
| C5-ACQ-07 | Pension Regulations for the Army Part I (2008) | https://desw.gov.in/sites/default/files/PRA-Pt-I(2008).pdf | size 750383 bytes (HEAD Content-Length; hash on download) |
| C5-ACQ-08 | Pension Regulations for the Army Part II (2008) | https://desw.gov.in/sites/default/files/PRA-Pt-II(2008).pdf | size 868605 bytes |
| C5-ACQ-09 | Entitlement Rules 2023 + GMO 2023 (combined, 49.9 MB) | https://desw.gov.in/sites/default/files/Entitlement%20Rules%202023.pdf | size 49925674 bytes |
| C5-ACQ-10 | Entitlement Rules 2008: two DESW files (ER-2008.pdf; 2010.01.18-Pen-Policy.pdf) | https://desw.gov.in/sites/default/files/ER-2008.pdf ; https://www.desw.gov.in/sites/default/files/2010.01.18-Pen-Policy.pdf | sizes 950023 and 946561 bytes |
| C5-ACQ-11 | PRA 2008 amending circulars (2013 Reg 18 Pt II; 2020 family pension) and ER 2008 second-appeal circular (2021) | URLs in discovery/B_candidates.csv C5B-015, C5B-016, C5B-017 | sizes 552473 / 59009 / 616688 bytes |

## C6-04: DSR custodian route (request text prepared; nothing sent)
**Publication request** for the owner to send, or not, through an authorised channel:
1. Regulations for the Army, Revised Edition 1987, **Volumes I and II** (volume structure per a secondary listing), including:
   - every amendment list and correction slip issued since 1987;
   - the amendment-incorporation record page;
   - the printed title page with publisher, printer and any job number;
   - the access marking.
2. Regulations for the Army, 1962, the edition cited in 1987 Gazette references (for example para 178), with its amendment slips.
3. Regulations for the Medical Services of the Armed Forces, 2010 (and 1983) with amendments.
4. The specific Army Orders and Army Instructions cited by KB records. The owner should first list them from `SRC-AO`/`AO` records (COI-002, COI-007, COI-018, COI-029, COI-033, COI-046, CM-040, HCE-030, HCE-031, HCE-033) and the AO 45/2001 reference in the Pooja Pal (2026) discussion. For each, state whether it is publicly published.

- **Archived CDA copies:** the archived CDA Guwahati / Secunderabad copies (C5-ACQ-26) are an alternative route. Examining them needs a prior owner decision on the possible marking.
- **Handling rule:** any restricted material stays out of public stores. It is recorded with its marking, and only an authorised custodian copy is used as authority.

## C6-05: Legal-adviser evidence pack (no determinations)
- **Index:** `registers/legal_adviser_evidence_index.csv` (built deterministically). It covers:
  - 13 adviser topics (LAQ-01..13);
  - 9 reserved items (r.23(3) CONFLICTING, C-08 r.193 OPEN, C-09 r.194 PROPOSAL, r.15, r.187(1), s.129, AQ-05, AQ-06, OQ-A-13);
  - the 29 Cycle 4 calibration escalations (12 disagreements, 17 severity splits);
  - source conflicts marked for legal review or reserved, including SC4-01 r.182.
- **Applicability questions added by Cycle 5 evidence (documentary, for the adviser):**
  - the ER 2023 covering letter's 'with effect from 21st September, 2023 and in supersession of all previous orders/rules' clause, relevant to LAQ-03/04;
  - Act 37/1992 has no commencement provision (AQ-05);
  - the Sanhita commencement notifications, once acquired (LAQ-13).
- **Rule:** every row carries determination NONE. No dispute is settled by agent vote.
