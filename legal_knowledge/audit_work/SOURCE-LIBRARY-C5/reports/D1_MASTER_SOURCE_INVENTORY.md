# D1. Master source inventory

**Register:** `registers/source_master_register.csv`. It has 112 publications or instruments, one row per edition or copy-class. It is built by `tools/build_registers.py` from `inputs/target_publications.csv`. Each row is checked against the frozen held-file manifest and the discovery candidates.

**Duplicates:** a source is one row however many copies are held. For example, the Virendra Kumar judgment is held at four paths with one sha256, and appears once. The same instrument is split into separate rows only where the copy class differs: as-enacted Gazette vs government compilation vs extract.

## Counts (priority x holding state)
| Holding state | P0 | P1 | P2 |
| --- | --- | --- | --- |
| HELD_PRIMARY_GAZETTE_FACSIMILE (C4 register PROVENANCE_DOCUMENTED) | 4 | | |
| HELD_PRIMARY_GAZETTE_GOVERNMENT_SCAN | 1 | | |
| HELD_PRIMARY_OFFICIAL_COURT_COPY | | 7 | |
| HELD_AUTHENTICATION_PENDING (Isaac) | | 1 | |
| HELD_GOVERNMENT_COMPILATION | 5 | | |
| HELD_GOVERNMENT_COMPILATION_EXTRACT | 2 | | |
| HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED | 23 | 1 | 2 |
| HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED | | 8 | |
| HELD_UNVERIFIED_MANUAL (MML) | | | 8 |
| NOT_HELD_LOCATED (official or facsimile location identified) | 7 | 7 | 16 |
| NOT_HELD_NOT_FOUND | 4 | 7 | |
| NOT_HELD_NOT_CHECKED | | 8 | |
| NOT_HELD_RESTRICTED_SUSPECTED | 1 | | |

Most P0 "provenance undocumented" rows are archive.org Gazette facsimiles of Army Rules amendments, declarations and a corrigendum, each now labelled by its nature (independent review RV-02/03). They were image-checked in ARMY-RULES-CHAIN-01 but have no row in the source-authentication register. Under the shared C4 rule they are therefore **not** treated as primary.

## Headline gaps
- **No Gazette (as-enacted) text** is held for the Army Act 1950, the AFT Act 2007, BNSS, BSA or BNS. Facsimiles are now located for all of them, with md5 and size pinned (D3 batch A).
- **Regulations for the Army 1987: not found** in any official public location. Only the Chapter V extract is held (D2).
- **The Army Rules chain after 06-2022 is unresolved.** There are 10 candidate S.R.O. items to read (C5C-004..013).
- **Pension:** none of PRA 2008 Parts I/II, ER 2008 or the combined ER/GMO 2023 file is held. The held 13 MB ER 2023 copy is the DESW covering letter of 21-09-2023 plus ER-2023 (Appendix-I) and annexures; it is INCOMPLETE because **GMO-2023 is absent** (C5-PIC-01, RV-19). All are located on desw.gov.in and checked by HEAD only. ER 1982, PRA 1961 and GMO 2002/2008 were NOT_FOUND.
- **Territorial Army:** the Act was NOT_CHECKED because India Code was blocked. The TA Rules 1948 and TA Regulations were NOT_FOUND officially.
- **Pay rules (Army Officers / PBOR 2017):** NOT_FOUND. The old MoD links return 404 and egazette was unreachable.
- **P1 sources not searched this cycle (NOT_CHECKED):** AFT Procedure Rules 2008/2011, the ISO Act 2023 and Rules 2025, Army Act s.4/s.9 notifications, and historical IPC/CrPC/IEA.

- **Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules:** neither the 1978 Rules nor the 1986 amendment (S.O. 4010 of 6-12-1986) is held. The held page is only a Rajya Sabha record that the amendment was laid (RV-01).

## Field notes
- Each row records `publication_type` (statute, subordinate legislation, regulation, administrative instruction, manual, Gazette notification, judicial, compilation, secondary, catalogue) and the two policy dimensions, `document_authority` and `carrier_provenance`. It also records `currency_status`. No row is CURRENT or IN_FORCE: currency needs a checked amendment chain, and none is complete.
- `discovery_state` is the set of states reported for the row's candidates. `NOT_CHECKED` is never collapsed into `NOT_FOUND`.
