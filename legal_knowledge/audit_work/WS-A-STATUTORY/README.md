# WS-A-STATUTORY: statutory and Gazette verification (issue #11, programme #10)

**Research proposal only. Nothing here is approved.** Rule 23(3) stays CONFLICTING. Rule 194 (C-09) stays a PROPOSAL. Rule 193 (C-08) stays OPEN. No download, crawler-config change, upload, push or correspondence was made. Read-only lookups were rate-limited (at least 2.2 s per host) and every one is logged in `network_requests_log.tsv`.

## Files
| File | Rows | Content |
| --- | --- | --- |
| `provision_change_log.csv` | 107 (86 in cycle 1; 21 added in cycle 2) | 42 rows itemising S.R.O. 17(E)/1993 (all 41 items plus its note); 7 rows for r.193/r.194/r.1 (1954 base text, 1987, 1989, 1993); 37 baseline rows carried by reference |
| `army_act_amendment_chain.csv` | 31 | Army Act 1950 chain: Acts 19/1955, 56/1974, 13/1975, 20/1983, 37/1992 (one row per section), the Adaptation Order 1956, the 1975 Ordinance, the repealing Acts 58/1960, 30/2001 and 4/2018, Bills, and the post-1992 gap |
| `identity_transcription_register.csv` | 54 | WSA-PIC-01..54: file SHA-256, computed and archived MD5, page, DPI, clip, render PNG SHA-256, independent transcription |
| `instrument_search_inventory.csv` | 166 | Deduplicated log: this session's searches, prior FTS logs reused (not repeated), and explicit NOT_CHECKED rows |
| `acquisition_requests.csv` | 30 | ACQ-03 batches B1 to B5, proposed and not executed; none overlaps PR #8 or ACQ-02 |
| `gaps_register.csv` / `open_questions.csv` | 15 / 12 | NOT_FOUND, NOT_CHECKED and OPEN items |
| `network_requests_log.tsv` | | Audit trail: every request with UTC time, URL, status and bytes |
| `mml_footnote_crosscheck_cycle2.csv` | 11 | Cycle 2: WS-C MML 2 footnote leads checked against the 41-item itemisation and held Gazettes |
| `official_note_observations_cycle2.csv` | 4 | Cycle 2: further errors in official amendment notes |
| `acq03_pinned_candidates.csv` / `acq03_summary.md` | 44 | Cycle 3: crawler-ready pinned candidates consolidating ACQ-03 B1–B5 and ACQ-C2 (URL, expected MD5/bytes, overlap check), not executed |
| `acquisition_requests_cycle2.csv` | 12 | Cycle 2: ACQ-C2-01..12 (pre-1960 instruments, Mar–Apr 1964 issues, AFT rules on India Code), not executed |

## Key findings (image-checked by WS-A unless stated)
1. **S.R.O. 17(E)/1993 is fully itemised** from page images of printed pp.12–21 (SHA-256 e9bf2114…, MD5 matches archive.org).
   - It has **41 items**, not the ~22 rules in AR-029. The extra items cover rr.135–136, 145, 150, 159, 160, 164, 168(2), 170, 170A/B (inserted), Section 7 and rr.172–176 (field punishment, omitted), 179, 182, 186, 193 and Appendices III–V.
   - The item AR-029 marked "118(?)" does read **r.118**.
   - r.1(2) states commencement **on publication**, contrary to the baseline's "not recorded".
2. **C-08 lead confirmed.** Item 38 substitutes r.193 to read: "Prescribed Officer under Section 90(i) and 91(i) … the Chief of the Army Staff or the officer commanding the Army". This matches the India Code compilation (PIC-29) and is the earliest located instrument containing the s.90(i) words.
   - The 1954 base text (printed p.346) covered s.91(i) only, naming the "Commander-in-Chief".
   - Act 37/1992 s.7(ii) first inserted "or any prescribed officer" into Army Act s.90(i).
   - This is recorded, not determined: r.193 stays OPEN (OQ-A-01).
3. **1954 base text of r.194** (printed p.346) is transcribed. S.R.O. 17(E)/1993 does not touch r.194.
4. **Army Act chain.**
   - Act 37/1992 has been read in full (pp.2–4 by WS-A; p.1 is PILOT-01 PIC-07). s.2 omits ss.75–76 and s.11 omits s.127. The Act has **no commencement section**; India Code's "w.e.f. 6-9-1992" is the assent date.
   - Act 13/1975 has no commencement section. Its s.4(1) repeals Ordinance 3 of 1975, and s.4(2) is a saving clause: anything done under the Ordinance is deemed done under the amended Acts "as if this Act had come into force on the 25th day of January, 1975" (WSA-PIC-30). This does not establish the Act's own commencement; the effective date stays NOT_DETERMINED, for the legal advisor (OQ-A-04). India Code's "w.e.f. 25-1-1975" is a compiler inference.
   - Two Gazette misprints are recorded (OQ-A-07): "existing authority" in s.7(i) and "Code of Criminal Procedure, 1899" in s.14.
5. **Register completeness.** Prior and new OCR locators show **six Army Rules amendment hints that are not in the register** (1967-12-16, 1968-11-16, 1969-03-01 S.R.O. 66, 1970-01-17, 1972-02-19 "Army (First Amendment) Rules, 1972", 1974-08-17), plus the three existing hints. All are LOCATED_UNVERIFIED, and ACQ-03-B1 is proposed for them.
6. **Gaps.**
   - E-7/1960 was not found in either 1960 Extraordinary series on archive.org.
   - S.R.O. 258/2002 was not found.
   - egazette.gov.in fails TLS verification (code 20) and was not bypassed, so the period after 06-06-2022 remains unsearched authoritatively.

## What is text-only (REQUIRES_VERIFICATION)
- Act 19/1955: the India Code text copy.
- India Code compilation footnotes, other than pp.27 and 36, which were image-checked.
- All OCR/FTS hints.
- The held OCR of the 1969 issue.
- Baseline rows marked TEXT_LAYER.

## Coordinator corrections adopted (2026-11-22)
- Dates are kept in separate columns:
  - `publication_date`
  - `commencement_as_printed`
  - `effective_date`, filled only when the instrument states a commencement
  - `effective_date_status`
- Pages read only from the text layer are marked REQUIRES_VERIFICATION.
- r.193 is tracked as C-08 and r.194 as C-09.

## Reproduce
Scripts are kept in the session scratchpad (`ws-a/scripts/`: `render.py`, `clip.py`, `net.py`, `build.py`, `build2.py`). Renders depend on the renderer (pymupdf) and the DPI, so equality of the **source** SHA-256 is the integrity test.

## Cycle 2 findings (for independent coordinator check)
1. **r.187(1) (OQ-C-06).**
   - S.R.O. 126 of 12-03-1964 amends r.13(2A) only; this was image-checked.
   - S.R.O. 1/1961 substitutes the whole phrase "Chapters II and III of these rules except rule 13".
   - No 1964 amendment of r.187 has been located.
   - MML's "SRO 1, dated 12th March, 1964" may be a conflation of the two instruments. This is recorded, not determined (XC-11, OQ-A-11).
2. **Commencement is printed (on publication)** in 188/1979, 216/1988, 8(E)/2003, 17(E)/2019 and 6(E)/2022.
   - S.R.O. 216/1988 deems its changes from 04-06-1979. That is the date of S.R.O. 188/1979, whose own commencement was 28-07-1979 (OQ-A-12).
3. **MML footnote leads: 7 agree, 1 partial, 3 discrepancies.**
   - r.13A(3) and r.15 are attributed by MML to 1993, but the 1993 instrument has no item for either rule.
   - For r.164, the Gazette inserts the entries 96–101, and the 80-A entry dates from 1985.
4. **Four pre-1960 Army Rules amendments** were located by OCR (1956, 28-11-1958 r.187(1)(r), 12-12-1958 r.95, 1959). No official note lists them.
5. **AFT rules (OQ-D-005).** India Code lists the 2008 Procedure Rules, the 2011 amendment and the 2009 Practice Rules. The instrument that "Rule 4-12" refers to is still OPEN.

## Cycle 3 files (branch claude/ws-a-cycle3)
| File | Content |
| --- | --- |
| `statutory_version_completeness_cycle3.csv` | 219 rows: every AR rule (107) and AA section (112) cited by the 658 KB, with version-history completeness |
| `r15_military_secretary_trace_cycle3.csv` | r.15 "or Military Secretary": instrument-by-instrument trace (source not found) |
| `r187_evidence_dossier_cycle3.md` | r.187(1) evidence dossier (OQ-C-06) |
| `s129_trace_cycle3.csv` | Army Act s.129 wording trace; enacted 1950 Gazette located (not held) |
| `commencement_readings_cycle3.csv` | Commencement clauses read for AR-010, AR-011, AR-024, AR-025 |
| `identity_transcription_register_cycle3.csv` | WSA-PIC-55..59 |
| `acquisition_requests_cycle3.csv` | ACQ-C3-01..04 (not executed) |
