# D5. Source authentication and integrity report

**Identity, integrity and legal applicability are three separate checks:**
- **Identity:** what the document is.
- **Integrity:** whether the bytes are the bytes. A matching hash proves nothing more.
- **Applicability:** whether the text is law on a given date. This report covers the first two only.

## 1. Integrity of held files
- **Re-hashing:** all 93 held binary paths in the CALIBRATION-02 index (67 unique files) were re-hashed from disk. **93 MATCH, 0 MISMATCH, 0 missing** (`baseline/held_binaries_manifest.csv`). `check_c5.py --verify-files` repeats this check.
- **Act 37/1992 copies:** two held copies of the India Code Gazette scan have the same length and 122 differing bytes. The differences all fall at offsets 165208–165338, inside the PDF trailer `/ID`. **C5-CF-C5-01 is closed as technical:** the page content is identical.
- **Duplicates:** the same bytes are held at several paths (for example Virendra Kumar at four paths, and the Army Rules compilation at four). Each is one source with several held paths.

## 2. Text layer and OCR
Each PDF page is classed by text length and by **drawn** image coverage (at least 50% of the page). This is a heuristic, revised after independent review RV-17.

| Class | Files (paths) |
| --- | --- |
| TEXT_LAYER_NO_IMAGES_ALL_PAGES (born-digital or retyped; not proof of either) | 34 |
| SCANNED_IMAGE_WITH_TEXT_LAYER_ALL_PAGES (OCR or overlay text) | 14 |
| MIXED | 35 |
| IMAGE_ONLY_NO_TEXT_LAYER: ER 2023 13 MB copy; RS papers-laid page; S.R.O. 8(E)/2003 | 3 |
| Word binaries (MML), not profiled | 7 |

**OCR fidelity:** the independent review compared text layers with page images (RV-21..23) and found errors on consequential items.

| File | Text layer | Printed page |
| --- | --- | --- |
| 1961 Gazette | "JULY 21, 1961" | 22 July |
| 1963 Gazette | "&th January" | 5th January |
| Act 37/1992 s.5 | "sub-section (i)" | sub-section (1) |
| Act 37/1992 s.5 | "(ft)" / "(/)" | (b) / (j) |

The registers were right in each case, because their values had been taken from images. **Rule:** no number, date or negation may be quoted from a text layer without a page-image check (policy step 3). Pages below an OCR confidence threshold are not scored here because no OCR was run in C5. Image-only files are listed above for OCR and review.

## 3. Identity checks completed in C5
- **All 62 HELD rows (at the time of the review):** the independent reviewer read p.1 or the notification page of every held file (RV, R1). The corrections below are applied, and identities are otherwise confirmed.
- **RV-01 (P1): CCCM file.** The file recorded as the "CCCM (Adjustment of Jurisdiction) Amendment Rules" is actually a **Rajya Sabha Debates page (Papers Laid, 03-03-1987, cols 207–208)** recording that MHA Notification S.O. No. 4010 was laid. It is now its own source (`C5-SRC-P2-RS-PAPERS-LAID-1987`, PARLIAMENTARY_RECORD), and the Rules row is NOT_HELD. On a 4x zoom (C5-PIC-02) the notification date reads "6th December, 1986", which agrees with PILOT-01. The reviewer read 08-12-1986; the disagreement is recorded in D7.
- **RV-19/RV-20 (P2): ER 2023 13 MB copy.** Identified from the page images.

  | Pages | Content |
  | --- | --- |
  | 1 | DESW covering letter F.No.16(3)/2023/D(Pen/Pol)/Vol-II dated 21.09.2023 (C5-PIC-01) |
  | 2–19 | ER-2023 (Appendix-I) |
  | 20–35 | annexures |

  **GMO-2023 (Appendix-II) is absent**, so the copy is INCOMPLETE. The letter states "with effect from 21st September, 2023", which is recorded as STATED_IN_INSTRUMENT. Which cases the Rules apply to stays reserved (LAQ-03).
- **RV-02/RV-03 (P2/P3): Army Rules Gazettes.** S.R.O. 34/1963 and S.R.O. 2(E)/2018 are r.188(e) **declarations**, not amendments. S.R.O. 68/1985 is a **corrigendum**. Labels and currency_status are corrected.
- **RV-11 (P2): BNSS and BSA.** Each is split into a NOT_HELD Gazette row and a HELD India Code compilation row with GOVERNMENT_COMPILATION authority.

## 4. Authentication state (unchanged rules)
- **13 files** have documented provenance in the CALIBRATION-02 register, and only these are `HELD_PRIMARY_*`. RV-15 confirmed an exact match.
- **Isaac (2026 INSC 993)** stays AUTHENTICATION_PENDING, renamed `HELD_AUTHENTICATION_PENDING` so that no prefix logic treats it as primary (RV-12).
- **34 held official copies have undocumented provenance**: 26 publications or records and 8 SC judgments. They need register rows, which require source-specific evidence of where and when each was obtained. **No download is needed for this.**
- **No signature has been cryptographically verified.** No MML edition is authenticated (8 files, `HELD_UNVERIFIED_MANUAL`).

## 5. Discovery protocol deviations (disclosed, not hidden)
- **UK National Archives:** robots.txt disallows `/catalogue`, but one page was fetched before this was noticed (Group A).
- **desw.gov.in:** robots.txt returned 403 or failed, but listing and HEAD requests continued (Groups A and B). **mod.gov.in:** one listing request ran before a successful robots retry, which turned out to allow all.
- **Log repairs:**
  - Two Group B log lines were corrected by hand after a proxy "200 Connection Established" was recorded instead of the real status.
  - The B and C logs had no header line; one was added in C5 (RV-29).
- **Blocked or unreachable hosts:** India Code (timeouts and a TLS name error), egazette.gov.in (TLS chain failure), pcdapension.nic.in and cgda.nic.in (connection reset), indianarmy.nic.in, thc.nic.in and web.archive.org. TLS verification was **never** disabled, and no CAPTCHA or login was attempted.
- **No binary GET and no aftjabalpur.in request** appears in any log. The validator and tests enforce this.

**Recommendation for the brief:** if robots.txt cannot be read, make no further requests to that host. This is a stricter rule than was applied this cycle.
