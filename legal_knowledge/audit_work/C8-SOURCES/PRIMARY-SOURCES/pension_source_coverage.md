# C8-D Task 5: pension and entitlement source coverage

Sources: `pension_source_coverage.csv` (one row per document) and `pension_record_dependency.csv` (one row per record). Dependencies come from the `V6-S..` citation codes in each KB record's `references` field, resolved through `PILOT-01/registers/source_code_resolution_v3.csv`. Keyword mentions are reported separately and are indicative only.

- M08 (pension) records: **96**. Records citing at least one V6 code: **68**. Records with at least one cited pension document not held: **61**.
- The held ER-2023 copy (`29f6fa2c...`, 35 pp., 13,011,188 bytes) contains the covering letter, ER-2023 (Appendix-I) and annexures; **GMO-2023 (Appendix-II) is absent**. It is kept as a distinct row, is provenance-undocumented, and is never treated as the complete publication (the complete file is C5-ACQ-09, 49,925,674 bytes; comparison is C5-CF-C5-03, OPEN).
- **Blockers preserved:** only the ER/GMO 2023 URL is in draft PR #9; all other DESW items need an allow-list extension; desw.gov.in robots.txt returned 403, so the fail-closed rule applies (no bypass). Approval A-C5-2 is required.
- **Register observation:** code V6-S07 (GMO 2023, 11 records) is resolved in v3 but is UNMAPPED in the C5 crosswalk (`corpus_source_map.csv` has no V6-S07 row). Its records are therefore counted as "citation not identified" rather than as dependent on C5-SRC-P1-ER-GMO-2023. Proposed fix for a later cycle: add the mapping (not done here).

| document | state | records citing (code) | records closed if acquired (sole missing source) | records (text mention) | cases | route |
| --- | --- | --- | --- | --- | --- | --- |
| Pension Regulations for the Army 2008, Part I | NOT_HELD | 25 | 7 | 13 | DCLR-SC-2026-N16 | C5-ACQ-07 |
| Pension Regulations for the Army 2008, Part II | NOT_HELD | 9 | 0 | 13 | - | C5-ACQ-08 |
| Pension Regulations for the Army 1961, Parts I and II | NOT_HELD | 0 | 0 | 1 | DCLR-SC-2011-A09;DCLR-SC-2011-L06;DCLR-SC-2013-N08;DCLR-SC-2015-N09;DCLR-SC-2026-N16 | none (NOT_FOUND; DESW archive pages unread) |
| Entitlement Rules for Casualty Pensionary Awards 1982 | NOT_HELD | 0 | 0 | 0 | DCLR-SC-2013-N08;DCLR-SC-2015-N09 | none (NOT_FOUND; DISCOVERY_RETRY) |
| Entitlement Rules for Casualty Pensionary Awards 2008 (two non-identic | NOT_HELD | 0 | 0 | 0 | DCLR-SC-2013-N08;DCLR-SC-2015-N09 | C5-ACQ-10 |
| Entitlement Rules 2023 (Appendix-I to MoD letter 21-09-2023) - complet | NOT_HELD_COMPLETE | 3 | 0 | 6 | - | C5-ACQ-09 (49,925,674-byte file) |
| Guide to Medical Officers (Military Pensions) 2023 (Appendix-II) - com | NOT_HELD | 11 | 6 | 5 | - | C5-ACQ-09 (same combined file) |
| HELD incomplete ER-2023 copy (letter + ER-2023 App-I + annexures; GMO- | HELD_INCOMPLETE_PROVENANCE_UNDOCUMENTED | 0 | 0 | 0 | - | n/a (held; compare after C5-ACQ-09) |
| Guide to Medical Officers (Military Pensions) 2002 and 2008 (+2008 Ch. | NOT_HELD | 0 | 0 | 5 | - | none (NOT_FOUND; 404) |
| PRA/ER amending circulars: Reg 18 Pt II (14-11-2013); family pension ( | NOT_HELD | 0 | 0 | 13 | DCLR-SC-2011-L06;DCLR-SC-2014-A08;DCLR-SC-2019-A03;DCLR-SC-2026-007 | C5-ACQ-11 |
| MoD letter 27-12-2023 on broad-banding of disability element (V6-S11) | NOT_HELD | 3 | 0 | 0 | - | not registered in C5 (code UNMAPPED) |
| OROP table correction letter 13-10-2025 (V6-S10, PROBABLE) | NOT_HELD | 2 | 0 | 0 | - | not registered in C5 (code UNMAPPED) |
| DESW FAQ (Q1-12) and PIB/DESW clarification on ER/GMO 2023 (secondary) | NOT_HELD | 11 | 5 | 0 | - | DISCOVERY_REQUIRED |
| DESW web pages (kinds of pension overview V6-S08; grievance channel V6 | NOT_HELD | 8 | 0 | 0 | - | not registered in C5 (codes UNMAPPED) |
| DESW circulars index (V6-S09) | NOT_HELD | 7 | 0 | 0 | - | DISCOVERY_RETRY |
| CGDA SPARSH portal and FAQs (V6-S12, V6-S13) | NOT_HELD | 10 | 4 | 0 | - | not registered in C5 (codes UNMAPPED) |
| Code V6-S03 (UNRESOLVABLE identity) | UNKNOWN | 2 | 0 | 0 | - | identity must be resolved first |
| Dharamvir Singh v UOI (SC 02-07-2013) | HELD_PROVENANCE_UNDOCUMENTED | 2 | 0 | 0 | - | provenance registration (no download) |
| UOI v Rajbir Singh (SC 13-02-2015) | HELD_PROVENANCE_UNDOCUMENTED | 2 | 0 | 0 | - | provenance registration (no download); 3 non-ident |
| Ex Cfn N S Yadav v UOI (SC 2019) | HELD_PROVENANCE_UNDOCUMENTED | 3 | 0 | 0 | - | provenance registration (no download) |
| UOI v Ram Avtar (SC 10-12-2014) | NOT_HELD | 4 | 2 | 0 | - | not held; official SC copy to locate |
| UOI v Sgt Girish Kumar, 2026 INSC 149 (12-02-2026) | HELD_PROVENANCE_UNDOCUMENTED | 6 | 0 | 0 | - | provenance registration (no download) |
| UOI v Sgt Girish Kumar, 2026 INSC 1113 (clarification 12-10-2026) | NOT_HELD | 5 | 3 | 0 | - | not held; official SC copy to locate |
| UOI v Balakrishnan Mullikote, 2026 INSC 286 (24-03-2026) | HELD_PROVENANCE_UNDOCUMENTED | 7 | 0 | 0 | - | provenance registration (no download) |
| AFT Act 2007 (cited from pension records) | HELD_COMPILATION_ONLY | 4 | 0 | 0 | - | C5-ACQ-02 (Gazette) |

"Closed if acquired" means the document is the only cited pension source of that record that is not held; acquiring it would leave the record dependent only on held (if still unregistered) sources. It does not mean the record becomes legally verified.

## Historical regimes

ER 1982, ER 2008, PRA 1961 and GMO 2002/2008 are not cited by code, but records and cases discuss them (Dharamvir Singh and Rajbir Singh under the earlier entitlement regime; Mullikote under PRA 1961 and 2008; Jujhar Singh and K J S Buttar under PRA 1961). ER 1982, PRA 1961 and GMO 2002/2008 were NOT_FOUND in the searched sources; ER 2008 has two non-identical DESW files (C5-ACQ-10, comparison C5-CF-C5-02 OPEN). Which edition governs a claim depends on dates of service events and is a legal question; nothing here assigns a regime.
