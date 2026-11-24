# C12 WS-G forms registry: remediation of review WSG-R01..R15

**Recorded:** 2026-11-24.
**Review:** `../reviews/review_wsg_forms.md` and `../reviews/review_wsg_forms_findings.csv`.
**Tool:** `c12-wsg-forms-registry/1.1.0` (was 1.0.0).
**Status:** Remediated. Waiting for the reviewer to re-check. Every row is still `DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED`, and no legal determination is made.

## Method

Before changing anything, each finding was checked against the source. Page images were rendered with pymupdf from the hash-verified bytes and read by the remediating author, as an AI visual reading. They are recorded in `tools/spec_forms.py` `VISUAL_CHECKS` (13 entries) and are reproducible from the cited copy and page. The rendered PNGs are scratch files and are not part of the registry. No source copy or frozen original was modified. Nothing was downloaded, installed or committed. The AFT 2011 amendment PDF was read from the c7 git object (`ad77758d`) with `git cat-file`.

## Finding to change map

| Finding | Verified against | Change |
| --- | --- | --- |
| WSG-R01 (P1) | AFTPR08-C7 page images: p.46 reads 'FORM III (see rule 27)'; p.37 has the heading '27. Registration of legal practitioner's clerk.'; p.38 has r.27(3) 'shall make an application to the Registrar in Form III'. | `FF-AFTPR08-F3`: title, `prescribing_provision`, `requirement_quote` and `version_history` corrected to rule 27. The correction is recorded in `version_history`. **Guards:** `rule_number_guard` attributes each hand-entered rule number to the citation that follows it, or to the PRIMARY source. If that source is OCR, the number must appear in a `VISUAL_CHECKS` entry, otherwise the build fails. `text_cited_rule_numbers_ok` checks native-text citations. Any digit in an OCR anchor must be an exact token or sit on a visually checked page. **Tests:** `test_wsg_r01_aft_form3_pinned_to_rule_27` and `test_wsg_r01_guard_rejects_unconfirmed_ocr_rule_numbers`; the second injects 'rule 17' and also removes the AFT image checks. |
| WSG-R02 | AR54-IC p.191: AR 169 says 'may, if he thinks fit'. AFTPR08-C7 p.27 image: r.4(4) says 'may attach ... which shall be signed'. | The README 'shall' rule was applied mechanically, and a test asserts that every STATUTORY_PRESCRIBED quote contains 'shall'. **Form H:** reclassified to OTHER_OR_UNDETERMINED / `PERMISSIVE_USE_SPECIFIC_RULE` (new status). **AFT Form II:** reclassified to OTHER_OR_UNDETERMINED, keeping PERMISSIVE_ATTACHMENT_FORM_PRESCRIBED. The reclassified list (Form H, AFT Form II, DPP Sch. II, plus the SGCM status) is in SUMMARY `reclassified_in_remediation` and the README. |
| WSG-R03 | AR54-GAZ p.2 image: AR 4(1)-(2). AR54-IC p.2 prints 'any change' for 'any charge'. | The 'Form status under AR 4 is permissive unless a specific rule uses shall' wording was removed. The new neutral wording is 'Interaction between any specific rule quoted here and AR 4(1) not determined (legal review)'. The new column `cross_cutting_caveat_as_printed` carries AR 4(1) verbatim, with the AR54-IC variant noted, on every Army Rules appendix row. No legal conclusion is drawn. |
| WSG-R04 | AR54-GAZ p.72 image: 8 columns, no 'Findings'; heading 'Sec. 80-82'. AR-AMD-1993 p.19 image. | The official OCR copies were not made primary, because their text extraction is not reliable for transcription. Instead each family carries a structured `field_set_version` value: 22 families are `MML_VERSION_UNVERIFIED (official copy held: ...)`. Field rows gain `official_copy_presence`. Every field that is NOT_FOUND or WEAK in a full official copy, or that a page image contradicts, goes to SUMMARY `field_divergence_queue`. That queue holds two fields: 'Findings', absent from the p.72 image, and summons (c) 'for investigation into', which reads differently on the p.19 image. Fields found only in the 1993 amending text are marked as such and are not queued. The offence-report example was rewritten from the image in the register, README and conflict queue. |
| WSG-R05 | Register occurrences. | New register columns `source_basis` (OFFICIAL_COPY / MML_ONLY / BOTH), `official_copy_extent` and `statutory_confirmation_status`. MML-only STATUTORY_PRESCRIBED rows show `NOT_CONFIRMED_FROM_OFFICIAL_COPY: ...`: 8 families (DPP Sch. I Forms I-III; ISL A-D; Tolls Pass). ISL and Tolls provisions now say 'rule text per unverified MML vol 3 only'. SUMMARY counts the split (32 MML_ONLY / 30 BOTH / 5 OFFICIAL_COPY), and the README headline states it. |
| WSG-R06 | c7 raw PDF `fc27032f...` (AFTPRA11-C7). p.2 image (English): S.R.O. 05(E) 29-07-2011, r.7(2) inserted, r.12A 'Every application under rule 8 and the reply under rule 12 shall be supported by an affidavit ...'. p.1 is the Hindi version (not read for content). AFTPR08-C7 p.29 image: r.8 'Contents of application'. | Mechanical rule: an INSPECTED_NO_FORMS_FOUND row without a visually inspected page becomes PARTIAL, with `coverage_method_limitation` set to HEADING_SCAN_... or TEXT_LAYER_SCAN_NO_FORMS_FOUND_NOT_VISUALLY_CONFIRMED (39 rows). AFTPRA11-C7 was added as a source; its coverage row is INSPECTED_NO_FORMS_FOUND, because pp.1-2 were visually checked. The derived-text row it replaces was removed. AFT Form I records the amendment as an UNEXAMINED DEPENDENCY: it quotes r.12A and the r.8 heading, and its effect is NOT DETERMINED. |
| WSG-R07 | C5 source master register; c7 meta listing. | `SCOPE_STATEMENT` added to SUMMARY, and a scope paragraph added to the README. Coverage has a new `scope_this_cycle` column. Seven NOT_HELD rows were added: Air Force Rules 1969; other Air Force Act instruments; AF/Navy pension regulations; Regulations for the Navy Pts I-III official copies; INAS Regulations 1973; Navy amendment regulations 2022/2024; other Navy Act instruments. Nothing is asserted about their contents. Held Air Force and Navy derived texts are tagged OUT_OF_SCOPE_THIS_CYCLE. |
| WSG-R08 | AR54-IC pp.4, 76, 78, 148-149, 167-168. | Each oath row now quotes its own rule verbatim (`OATH_QUOTES`), including AR 46 'in such of the following forms as shall be appropriate' and AR 140 'if so required by the Act' (also in applicability). New build check `verify_quotes`: every quoted piece cited to a native-text page must have a normalised whole-word match on that page or the next one (66 pieces are checked). |
| WSG-R09 | AR54-IC p.38, p.192, p.182. | **Offence report:** pinpoint is now AR 22(3)(a), with the AR 22(3) limbs quoted. **Form I:** leads with AR 170B(1)(b), quoted verbatim. **Form 1-B:** uses AR 170A(4) verbatim. **SGCM:** status is now PERMISSIVE_USE_SPECIFIC_RULE. |
| WSG-R10 | repro1 DOC line texts. | DOC ranges are bounded by min(next registered occurrence - 1, end of file, start + 400). `locator_end_basis` records which bound applied: 76 NEXT_REGISTERED_OCCURRENCE, 2 END_OF_FILE, 17 CAPPED_AT_400_LINES. Labels of two words or fewer, and stock phrases, are marked `generic_label=YES` (210 fields). Cross-copy hits on them are annotated as weak and are excluded from `fields_matched_non_generic`. The next-form-heading boundary was not implemented, because form-internal headings would truncate ranges. Capped ranges are marked instead. |
| WSG-R11 | Builder `match()`. | The README and each field row (`match_method`) describe the method as 'normalised whole-word match'. The word 'verbatim' is now used only for quotations. |
| WSG-R12 | DPPR53-C7 r.33(3). | DPP Schedule II retyped to OTHER_OR_UNDETERMINED / MANDATORY_DOCUMENT_LIST. |
| WSG-R13 (INFO) | n/a | `python_version` was added to SUMMARY. A Python 3.11 run with pymupdf was not done, because nothing could be installed; all files parse under the 3.11 grammar. |
| WSG-R14, R15 (INFO) | n/a | No change needed. |
| Blueprint gaps (review section 5) | n/a | **Register:** `page_image_locator`, `visual_check_refs`, `page_region_bbox` (empty, because no bbox was measured) and `review_finding_refs`. **Coverage:** `reviewer_evidence`, `review_remediation_state` and `legal_review_ref` (empty, because no legal review exists). |

## Counts before and after

| Count | 1.0.0 | 1.1.0 |
| --- | --- | --- |
| Families / occurrences / fields | 67 / 215 / 541 | 67 / 215 / 541 |
| STATUTORY_PRESCRIBED | 42 | 39 |
| MML-only families | 32 (free text) | 32 (structured) |
| MML-only STATUTORY_PRESCRIBED (not confirmed) | 9 | 8 |
| Coverage rows | 83 | 90 |
| INSPECTED_NO_FORMS_FOUND | 40 | 1 |
| Tests | 15 | 27 |

## Not fixed / limits

- Official Gazette copies are still not the primary for field transcription. The field lists of 22 families remain the MML 2 version, now labelled. Replacing them needs a page-image transcription of 1954 Gazette pp.73-86 and 1993 pp.19-21, field by field.
- No bbox was recorded for any form.
- Not run under Python 3.11 with pymupdf (WSG-R13).
- AFT Form I field labels (pp.43-45) were not visually checked.
- The effect of the 2011 amendment (r.12A, r.7(2)) on Form I is recorded but not determined. This is for legal review.
