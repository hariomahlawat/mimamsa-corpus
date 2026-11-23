# D7. Independent review report

## How the review was run
- **Reviewer:** a separate agent, read-only, briefed with the files and the policy but not with the coordinator's conclusions.
- **Method:** it opened the underlying files itself. It rendered page images (`review/review_log.md`), re-derived every amendment and chain row from its origin, and made 2 live archive.org metadata requests.
- **Output:** 32 findings (`review/review_findings.csv`, verbatim): 1 P1, 5 P2, 12 P3 and 14 INFO confirmations.
- **Scope:** technical review only. It is **not** legal review and confers no approval.
- **Independence limit:** the reviewer shared the session filesystem. Its independence of reading is procedural and cannot be proven by git.

## Material findings and dispositions
| ID | Sev | Finding (short) | Disposition | Where |
| --- | --- | --- | --- | --- |
| RV-01 | P1 | The held "CCCM Amendment Rules" file is a Rajya Sabha Papers-Laid page, not the instrument and not from India Code | **Accepted.** New PARLIAMENTARY_RECORD source; Rules row set to NOT_HELD; KB items fall to MISSING (8). The mislabel was the coordinator's: PILOT-01 had described the file correctly. | master; D5 |
| RV-02 | P2 | S.R.O. 34/1963 and 2(E)/2018 are r.188(e) declarations, labelled as amendments | **Accepted.** Labels are now driven by the origin `nature` field (DECLARATION_INSTRUMENT) | master |
| RV-11 | P2 | BNSS and BSA rows give primary authority to a compilation | **Accepted.** Each split into a Gazette row and a compilation row | master; crosswalk map |
| RV-19 | P2 | 13 MB ER 2023 copy identified; GMO-2023 absent | **Accepted.** Completeness set to INCOMPLETE; C5-CF-C5-03 updated | master; conflicts |
| RV-20 | P2 | ER 2023 covering letter is held (p.1), not "secondary only" | **Accepted.** Coordinator re-read p.1 (C5-PIC-01). Effective date 2023-09-21 recorded as STATED_IN_INSTRUMENT; trigger-date applicability stays LAQ-03 | amendment register; master |
| RV-31 | P2 | EXACT_ANCHOR given to r.95 despite the AR-039 hint; amended-rule detection ignored the instrument register | **Accepted.** Detection now includes instrument-register `provisions_affected`, hints included. EXACT_ANCHOR wording now states the incomplete chain. 43 → 42 exact anchors | builder; D6 |
| RV-03 | P3 | S.R.O. 68/1985 is a corrigendum | Accepted (CORRIGENDUM_INSTRUMENT) | master |
| RV-07 | P3 | Act 37/1992 publication date less precise than its origin | Accepted (1992-09-07). Also recorded RV-26: no commencement provision | master |
| RV-09 | P3 | Judgment dates left NOT_DETERMINED | Accepted. Dates taken from the C4 register, cases_53 or the title. N S Yadav and Navjot Sandhu stay NOT_DETERMINED | master |
| RV-12 | P3 | `HELD_PRIMARY_AUTHENTICATION_PENDING` matches prefix filters | Accepted. Renamed `HELD_AUTHENTICATION_PENDING` | master; validator |
| RV-13 | P3 | Act 37/1992 copies differ only in the PDF trailer ID | Accepted. Coordinator confirmed offsets 165208–165338; C5-CF-C5-01 CLOSED_TECHNICAL | conflicts |
| RV-14 | P3 | Carrier stated on undocumented-provenance rows | Accepted in part. Judgment, Act 13/1975 and ER copy carriers marked "(as reported; retrieval record not documented)". Archive.org Gazette rows keep THIRD_PARTY_ARCHIVAL_FACSIMILE because their identifiers are in the held paths. | master |
| RV-17 | P3 | Scanned classifier counts undrawn images | Accepted. Now based on drawn image coverage (at least 50%); baseline rebuilt | baseline |
| RV-21..23 | P3 | Text-layer OCR errors on dates and sub-section numbers | Accepted as a rule: no quotation from text layers without an image check (D5). Register values were already correct. | D5 |
| RV-25 | P3 | Chain-row origin ids positional; no locator | Accepted in part. `origin_id` is now `instrument_id|provision|event`; evidence carries the instrument sha256, locator and Gazette identity. The `chain_row_id` stays positional within the derived file. | builder |
| RV-29 | P3 | Logs lacked headers; robots handling | Headers added; deviations disclosed in D5; stricter robots rule recommended | discovery; D5 |

## Disagreements (recorded, not resolved by vote)
| Item | Reviewer | Coordinator | State |
| --- | --- | --- | --- |
| Date of MHA Notification S.O. 4010 (RS Papers Laid, cols 207–208) | "08-12-1986" | "6th December, 1986" on a 4x zoom (C5-PIC-02, render `reports/evidence/rs_313431_zoom.png`), agreeing with PILOT-01 | **OPEN, documentary.** The Gazette of S.O. 4010 itself would settle it. Low consequence: the date only identifies the notification. |
| RV-25 `chain_row_id` stability | prefers stable ids | the stable key is carried in `origin_id`, and the derived file is rebuilt deterministically | Recorded; low severity |

## Confirmed by the reviewer (INFO)
- **HELD_PRIMARY gating:** the reviewer matched the 13 HELD_PRIMARY-era rows to the 13 register rows (RV-15). As restated in the C5 corrections, that is **12 documented-primary copies plus 1 authentication-pending copy** (Isaac, not primary).
- **Derivation fidelity:** all 241 amendment and chain rows match their origin field by field, and no effective date was invented (RV-24).
- **Act 37/1992:** s.2 omits ss.75–76 and s.11 omits s.127; confirmed on the image (RV-26).
- **Discovery:** md5, size and date match the live archive.org metadata for 1950.306 and 2007-12-28.020. No binary GET or blocked host appears in the logs (RV-27/28).
- **Reserved states:** preserved verbatim (RV-32).
- **Identities:** confirmed for the Army Rules Gazettes, statutes, compilations, judgments and MML (RV-04..10, 16, 18, 30).

## Not independently reviewed this cycle
- Discovery claims of NOT_FOUND were not re-run by the reviewer: there was no network budget for it. They rest on the discovery agents' logged searches.
- The legal content of any provision.

## Independent review of the final correction diff (151f9358..7bdde558)
- **Reviewer:** separate, read-only. Brief, findings and verdict are verbatim in `review/final_diff_review.md` and `review/final_diff_findings.csv`.
- **Verdict: ACCEPT WITH CONDITIONS** (2 P2, 5 P3).
- **Confirmed:**
  - P1 corrections (TA, 12+1 authentication counts, Act 37/1992 copy-level provenance);
  - no promotion path for undocumented or pending copies;
  - headline figures reproducible;
  - originals unchanged;
  - only authorised files changed.

| ID | Sev | Finding | Disposition |
| --- | --- | --- | --- |
| FD-01 | P2 | BLOCKED_ACCESS appeared only in free text; superseded NOT_FOUND kept in the TA rows' `discovery_state`; TA Act moved on index evidence | **Fixed.** New structured `direct_verification_state` (BLOCKED_ACCESS for the TA Act, Rules, Regulations and RA 1987). New `superseded_candidate_ids`, excluded from `discovery_state` but kept for audit. The TA Act move is kept on the same official-host index evidence as the Rules, with BLOCKED_ACCESS structured. Tests added. |
| FD-02 | P2 | Runner could GET up to 3 MB of a document | **Fixed.** GET only if HEAD gave an explicit listing content type. A 2 KiB range probe is classified before any full GET. Residual risk of 4 KiB from a Range-ignoring server is documented and logged as a violation. Docstring corrected. Mocked runner tests added. |
| FD-03 | P3 | D8 cited a review file not in the commit | **Fixed.** Review files committed in `review/` |
| FD-04 | P3 | TA Rules amendment years inconsistent | **Fixed.** C5D-001 notes aligned (1964, 2017, 2023; all unverified) |
| FD-05 | P3 | Log validator did not require a robots decision first | **Fixed** in `validate_log_v2`; test added |
| FD-06 | P3 | Proxy content type recorded on a 000 row | **Fixed.** Runner drops headers on status 000. Log row corrected with original value retained (`log_amendments.csv` LA-04). |
| FD-07 | P3 | HELD_PRIMARY subtype not checked against the documented copy's class | **Fixed** in `check_holding_vs_copies`; test added |

**Re-review of the changed material (7bdde558..5bc2d12a): VERDICT ACCEPT** (`review/final_diff_rereview.md`). Its non-blocking items were handled as follows:

| ID | Item | Disposition |
| --- | --- | --- |
| RR-01 | Full-GET residual risk | Signature check widened to a PDF header anywhere in the first 1 KiB; residual risk stated in the runner docstring |
| RR-02 | TA Act keeps NOT_FOUND from C5C-029 | Kept deliberately: it is the archive.org search for the as-enacted Gazette, a different carrier from the India Code text |
| RR-03 | Robots decision for redirect hosts | Now required by `validate_log_v2` |
| RR-04 | Re-review file not committed | Now committed |
| RR-05 | curl version requirement | Recorded in the docstring |
