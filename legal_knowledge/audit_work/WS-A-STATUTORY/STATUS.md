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
- [x] CP-04 / OQ-D-019: PCL-BL-25 (r.23 search-absence summary) is now REQUIRES_VERIFICATION; it relies on no page image and no render hash.
  - The other 31 carried baseline rows that claimed PAGE_IMAGE_CHECKED now cite render evidence:
    - 25 rows cite WS-A renders (WSA-PIC, with hashes in identity_transcription_register.csv);
    - 6 rows cite baseline PICs that carry a render SHA-256.
  - No rows were left without evidence.

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
