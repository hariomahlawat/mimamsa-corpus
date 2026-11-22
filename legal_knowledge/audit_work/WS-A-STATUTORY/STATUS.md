# WS-A STATUS (resumable)

Updated 2026-11-22 (cycle 3). Branch: `claude/ws-a-statutory` (base 34e75aa9). Worktree: `/home/user/ws-a`.

## Cycle 1 (done; PR #19, accepted)
- S.R.O. 17(E)/1993: all 41 items itemised from page images.
- 1954 base text of rr.193/194 transcribed.
- Army Act chain (31 rows).
- Search inventory, ACQ-03 batches B1–B5, gaps register, open questions.

## Cycle 2 (done)
- [x] **OQ-C-06 (r.187(1)): recorded, not determined.** Item XC-11 in `mml_footnote_crosscheck_cycle2.csv`.
  - New image checks:
    - the 1954 r.187(1) text;
    - S.R.O. 126/1964, a two-item instrument amending r.13(2A) only;
    - a second reading of S.R.O. 1/1961, which substitutes the whole phrase "Chapters II and III of these rules except rule 13".
  - No 1964 amendment of r.187 was found in held bytes or in archive.org locators.
  - Plausible reading: MML conflates the number of S.R.O. 1/1961 with the date of S.R.O. 126/1964. **This needs independent coordinator check.**
- [x] **Change log grown from 86 to 107 rows** (21 new WSA-PIC renders, WSA-PIC-34..54).
  - Covers 116/1965, 215/1965, 188/1979 (commencement), 216/1988, 8(E)/2003, 17(E)/2019, 6(E)/2022, 205/1961, 1/1961, 5/1968, 246/1982, 44/1985, 55/1985, 278/1985, 169/1987 and 126/1964.
  - Commencement is printed (on publication) for 188/1979, 216/1988, 8(E)/2003, 17(E)/2019 and 6(E)/2022. The baseline had "not recorded" for each.
- [x] **MML footnote cross-check** (`mml_footnote_crosscheck_cycle2.csv`, 11 rows):

  | Result | Count | Provisions |
  | --- | --- | --- |
  | Agree | 7 | r.14(4)–(5), r.16A, r.16B, r.145, r.168(2), r.186(1), r.193 |
  | Partial | 1 | r.164 |
  | Discrepancy | 3 | r.13A(3), r.15, r.187(1) |

- [x] **New register-completeness gap.** Four pre-1960 Army Rules amendments were located by OCR only (1956, 1958 ×2 including r.187(1) item (r), 1959). They are in no official note and not in the register (GAP-13, ACQ-C2-01..04).
- [x] **OQ-D-005.** India Code's official records list the AFT (Procedure) Rules 2008, the 2011 amendment and the AFT (Practice) Rules 2009. Bitstream checksums are recorded (ACQ-C2-10..12). Which instrument "Rule 4-12" means is still OPEN.
- [x] Official-note observations (4) and `acquisition_requests_cycle2.csv` (12 rows, nothing fetched).

## Cycle 3 (done)
- [x] `acq03_pinned_candidates.csv` (44 rows) and `acq03_summary.md`. Nothing was downloaded.
  - 40 rows have a pinned URL (37 archive.org, 3 India Code); 4 have no lawful online source known. Expected size about 74.7 MiB.
  - No URL overlaps ACQ-01 or ACQ-02.
  - ACQ03-016 (archive.org copy of Act 37/1992) duplicates the ACQ-01 India Code document and is optional.
- [x] B4 sources located on archive.org (metadata/OCR locators only):
  - S.R.O. 2(E)/1955 (e.1955.15);
  - Adaptation of Laws (No.3) Order 1956 (e.1956.717);
  - Ordinance 3/1975 (csl_extraordinary 1975-01-25; derivative PDF only);
  - Act 20/1983 (e.1983.330) and its commencement notification (e.1984.465);
  - Act 4/2018 (central.e.2018-01-08.181639, a mirror of egazette 181639.pdf);
  - probable Army Act commencement notification of 22-07-1950 (1950.318).

## Review fix (PR #19; Codex finding verified by coordinator)
- [x] Act 13/1975: README and the CSV summaries no longer present 25-01-1975 as the Act's commencement.
  - s.4(2) is described as a repeal-and-saving ("as if") clause for actions under the repealed Ordinance 3/1975.
  - The effective date stays NOT_DETERMINED (AA-06; advisor OQ-A-04).
  - Edited: README.md, army_act_amendment_chain.csv (AA-05, AA-06), open_questions.csv (OQ-A-04), acquisition_requests.csv (ACQ-03-B4-06), acq03_pinned_candidates.csv (ACQ03-022).
- [x] CP-04 / OQ-D-019: PCL-BL-25 (r.23 search-absence summary) now has copy_fidelity NOT_CHECKED (policy v1), with REQUIRES_VERIFICATION in evidence_level; it relies on no page image and no render hash.
  - The other 31 carried baseline rows that claimed PAGE_IMAGE_CHECKED now cite render evidence:
    - 25 rows cite WS-A renders (WSA-PIC, with hashes in identity_transcription_register.csv);
    - 6 rows cite baseline PICs that carry a render SHA-256.
  - No rows were left without evidence.

## Cycle 3 statutory completeness (branch `claude/ws-a-cycle3`, worktree `/home/user/ws-a-c3`, base 9b48b08e)
- [x] **r.15 "or Military Secretary"** (`r15_military_secretary_trace_cycle3.csv`).
  - The 1961 substituted r.15 (printed p.142, image-checked WSA-PIC-55/WSA-PIC-56) does **not** contain the words.
  - No held instrument from 1961 to 2022 adds them:
    - S.R.O. 235/1991 adds them to r.13A only (WSA-PIC-58);
    - S.R.O. 61/1991 adds "or the Adjutant General" to r.15A;
    - S.R.O. 17(E)/1993 has no r.15 item.
  - The source remains unidentified (OQ-A-10; WS-C XC-03 agrees). For independent coordinator check.
- [x] **r.187(1) dossier** (`r187_evidence_dossier_cycle3.md`): consolidated. It stays OPEN until ACQ03 C2-05..09 are checked.
- [x] **Army Act s.129** (`s129_trace_cycle3.csv`).
  - The India Code compilation p.36 reads "an officer approved of" (image-checked WSA-PIC-59).
  - Acts 37/1992 and 13/1975 do not touch s.129.
  - The enacted Army Act 1950 was **located** on archive.org (Gazette Extraordinary 23-05-1950, `in.gazette.e.1950.306`). Its OCR reads "an officer approved of" (locator only). Acquisition request ACQ-C3-01.
  - MML 2 "any person" stands alone. For independent coordinator check.
- [x] **Completeness table** (`statutory_version_completeness_cycle3.csv`): 107 AR rules and 112 AA sections cited by the KB.

  | Status | AR rules | AA sections |
  | --- | --- | --- |
  | ESTABLISHED_SUBJECT_TO_REGISTER_GAPS | 2 (r.13A, r.15A) | 0 |
  | PARTIALLY_ESTABLISHED | 31 | 8 |
  | NOT_ESTABLISHED | 74 | 104 |

  - No AA section is established because the enacted 1950 text is not held.
  - Base-text page numbers come from the text layer and are locators only.
- [x] **Commencement readings** (`commencement_readings_cycle3.csv`): AR-010, AR-011 and AR-025 print no commencement clause (NOT_STATED_PENDING_ADVICE). AR-024 is corrected: r.1(2) states commencement on publication, and **both** items 2 and 3 carry the 04-06-1979 deeming clause.
- [x] New PICs: `identity_transcription_register_cycle3.csv` (WSA-PIC-55..59). New acquisition needs: `acquisition_requests_cycle3.csv` (ACQ-C3-01..04).

## Cycle 3 review fix (PR #24)
- [x] Army Act s.137 was overstated. It now lists Act 37/1992, A.L.O. (No.3) 1956 and S.O. 3912(E)/2019; amendments are NOT ALL image-checked; status NOT_ESTABLISHED. s.2 now lists A.L.O. 1956.
- [x] Regression check `tools/check_completeness_cycle3.py` (C1/C2 plus self-test): it fails on the old table and passes on the new one.
- [x] Addendum `army_act_amendment_chain_addendum_cycle3.csv` (AA-C3-01..04). New acquisition rows ACQ-C3-05 and -06.
- [x] Details in `REVIEW_FIX_CYCLE3.md`. AA counts: partial 9 → 8, not established 103 → 104.

## Cycle 3 review follow-up (conditions on bfc9765a)
- [x] The C2 self-test uses explicit fixtures (no vacuous pass). C1 uses token-boundary matching, with prefix-ID fixtures. Self-test 9/9.
- [x] Documented limitation: Act 19/1955 "many sections" (OQ-A-13 in `open_questions_cycle3.csv`). Sections are not guessed.

## Requests to the coordinator (other paths), cycle 3
- **To WS-D (via coordinator):** please add `legal_knowledge/audit_work/WS-A-STATUTORY/army_act_amendment_chain_addendum_cycle3.csv` (AA-C3-01..04) as an input to `build_versioned_edges`.
  - It covers: A.L.O. (No.3) 1956 for Army Act ss.2, 3, 4, 5, 137, 151, 174; S.O. 3912(E)/2019 for ss.137, 151, 174; Act 36/1957 repeal of s.194; and extension instruments that amend no section text.
  - Columns follow `army_act_amendment_chain.csv`, plus `supersedes_or_extends` and `compilation_page_render_sha256`.
  - WS-A has not edited any WS-D file.

## Next
- After approval of ACQ-C2:
  - image-check the four pre-1960 instruments;
  - check the four unheld Mar–Apr 1964 issues;
  - read AFT rules 4–12.
- After approval of ACQ-03-B1/B2: the 1966–1974 hints and the five OCR-only instruments.
- Look for the source of the r.15 words "or Military Secretary" (OQ-A-10).

## Blockers
- egazette.gov.in fails TLS verification (code 20); not bypassed. The period after 06-06-2022 remains unsearched.
- E-7/1960 and S.R.O. 258/2002 still need non-archive.org sources.
- Every download needs owner approval.

## Requests to the coordinator (other paths)
- ARMY-RULES-CHAIN-01:
  - AR-016, AR-034 and AR-035 commencement can be set to "on publication" (STATED_IN_INSTRUMENT), per PCL-188-1979-R1, PCL-17E-2019 and PCL-6E-2022.
  - The AR-024 r.16A change is an Explanation **added**, not amended.
  - Pre-1960 hint rows could be added (GAP-13).
- `official_note_discrepancies.csv`: add ON-C2-01..04.
- WS-C: XC-01, XC-03, XC-07 and XC-11 bear on PG-03, PG-05, PG-06 and PG-12.
