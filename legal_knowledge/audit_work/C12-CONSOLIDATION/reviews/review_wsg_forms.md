# Independent review: C12 Workstream G forms discovery register

**Reviewed:** 2026-11-24
**Reviewer:** independent AI reviewer. This is an AI documentary review, not legal validation, and it gives no legal opinion on any form's currency or authority.
**Object:** `C12-CONSOLIDATION/forms_registry/`: README.md, tools/, tests/, and the outputs FORM_DISCOVERY_REGISTER.csv (215 rows), FORM_FIELDS.csv (541), SOURCE_COVERAGE.csv (83) and SUMMARY.json.
**Definition checked against:** `docs/product/FORM_DISCOVERY_AND_COVERAGE_REGISTER.md` @ `origin/docs/mimamsa-product-blueprint-2026-11-24`.
**Mode:** read-only on the registry. Experiments were run in `scratchpad/rev_wsg/` (copied c7 blobs, helper scripts and rendered page images). Nothing was committed or installed.
**Findings CSV:** `review_wsg_forms_findings.csv`, with 15 rows: 1 P1, 6 P2, 5 P3 and 3 INFO.

## Verdict

**CONDITIONAL PASS. This is a discovery-only register, and P1 WSG-R01 must be fixed before anyone uses it.**

The register is careful and mostly honest:
- Every input is hash-verified.
- Every row carries `DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED`, and every row has `legal_approval_state=RESEARCH_ONLY`.
- No coverage percentage is claimed.
- Unheld sources, referenced-but-unprinted forms and conflicts are listed.
- In the samples, the field labels and form titles are genuinely printed on the cited pages.

There is one invented provision. AFT Form III is tied to "rule 17", but the Gazette prints "rule 27". This is the kind of error the "nothing invented" rule exists to catch. The P2 items concern classification consistency (AR 169 'may'; AR 4 savings clause), MML text standing in for held official text, structured MML-only flagging, and over-stated coverage states. These should be fixed before any template or checklist work builds on the register.

## 1. Reproducibility and tests

| Check | Result |
| --- | --- |
| `venv/bin/python -I tools/build_forms_registry.py --check` | `CHECK OK: 4 files reproduce byte-for-byte` (exit 0) |
| `venv/bin/python -m pytest -q tests/` | 15 passed (31 s) |
| `python3.11 -I tools/build_forms_registry.py --check` | Fails with `ModuleNotFoundError: pymupdf`. System 3.11 has no pymupdf or pytest, and nothing was installed (WSG-R13). Every tool and test file parses under the 3.11 grammar. The venv runs Python 3.13.18. |
| Input hashes (20 sources in SUMMARY.inputs) | All SHA-256 values and byte sizes re-computed by the reviewer and matching, for both scratch files and c7 `git cat-file` at ad77758d |

## 2. Form sample and all 42 statutorily prescribed classifications

**Sample.** The 15 families with the lowest `sha256('C12-FORMS-REV'+form_family_id)`:

DPPR53-S1-F3, ISLR38-FA, TAR48-S2B, TAR48-S2C, TAR48-S2E, AR54-APPIII-P1D-SCHED, DPPR53-S2, AR54-APPIII-P3C, DPPR53-S1-F1, AR54-APPIII-SGCM, AR54-APPV-FL, AR54-APPI-F1, AR54-APPII-P2, AFTPR08-F3, ITR42-PASS.

These have 37 occurrences, and every anchor was found within its cited page or line range. Page images were rendered with pymupdf for:
- AR54-GAZ pp.58, 59 and 72;
- AR-AMD-1993 p.19;
- AFTPR08-C7 pp.37, 38 and 46.

All other pages were checked on the text layer. Titles and pages are correct except in one case: **FF-AFTPR08-F3** gives "(see rule 17)" and r.17(3), but the page image reads "(see rule 27)" and the rule heading on p.37 is "27. Registration of legal practitioner's clerk." (WSG-R01, P1).

**Statutory set.** The 42 primary rows with `STATUTORY_PRESCRIBED` were each checked against the provision text on the cited page:

| Group (families) | Provision checked | 'shall'? | Assessment |
| --- | --- | --- | --- |
| AFT Form I (1) | r.4(1), p.26 | shall | OK |
| AFT Form II (1) | r.4(4), p.27 | 'may attach'; slip 'shall be signed' | Disclosed as PERMISSIVE_ATTACHMENT; see WSG-R02 on consistency |
| AFT Form III (1) | r.27(3), p.38 (register says r.17) | shall | Classification OK; **rule number wrong** (WSG-R01) |
| App. I Forms I-II (2) | AR 190, AR54-IC p.208 | shall | OK; currency flagged (IAFK-1162 not held) |
| App. III Pt II, Pt III (a) and (c), Pt IV (4) | AR 22(3)(a); 23(6); 179(5A); 27 | shall | OK; AR 22 pinpoint (WSG-R09) |
| App. IV Pt I Forms 1-2 (2) | AR 26(3) | shall ... 'as far as practicable' | Defensible with the QUALIFIED status; legal-review point |
| App. IV Pt II Forms A-G (7) | AR 166, 167 | shall | OK, subject to the AR 4(1) savings clause (WSG-R03) |
| App. V Forms 1-A, 1-B, I, J, K, L (6) | AR 170A(1) and (4), 170B(1)(b), 171(a) | shall (some conditional) | OK; Form I quote should be 170B(1)(b) (WSG-R09) |
| App. V Form H (1) | AR 169 | **may, if he thinks fit** | **Inconsistent with the stated rule** (WSG-R02) |
| Oath forms rr.9, 45, 46(A)-(D), 109, 140 (8) | rules as printed | shall ... or other form to same purport | OK; AR 46 quote not verbatim; AR 140 conditional (WSG-R08) |
| DPP Sch. I Forms I-III, Sch. II (4) | rr.9, 29(1), 33(3), DPPR53-C7 | shall | Rule text official; **form text MML-only**; Sch. II is a document list (WSG-R12) |
| ISL Forms A-D (4), Tolls Pass (1) | ISL rr.4-6, ITR r.2, MML3 pp.207 and 237 | shall | 'shall' confirmed **only in unverified MML vol 3** (WSG-R05) |

Summary of the statutory set:
- All 42 provisions were located.
- 40 contain 'shall'; some of these are conditional.
- 1 says 'may' (AR 169).
- 1 is 'may attach', which the register discloses (AFT Form II).

No form classified `OTHER_OR_UNDETERMINED` was found to have a specific 'shall' rule in AR54-IC that the register missed. This was checked with a full-text scan of every 'Appendix' mention.

## 3. Field rows (40 sampled)

The sample was the 40 rows with the lowest `sha256('C12-FORMS-REV'+field_id)`. Each label was checked raw, apart from whitespace collapse, against the text of its primary page range:
- **39 are verbatim**, case included.
- **1 matches after normalisation only**: FF-AFTPR08-F1#F17, where OCR inserted a stray quote mark. The page shows the label.

None was invented. One caveat: many labels are generic ('Name', 'Unit', 'Dated', 'Signed', 'versus'), and the matcher normalises case and punctuation (WSG-R11). The 'Findings' column (F13) is verbatim in MML 2 but absent from the 1954 Gazette page image. It is a real divergence and is correctly queued as a conflict (see WSG-R04).

## 4. MML-only marking, conflicts and amendment history

**MML-only marking.** 32 of the 67 families occur only in MML copies. Every one of them has UNVERIFIED_MANUAL in `source_evidence_class` and an MML caveat in `outstanding_uncertainties`. That marking is present, but it is free text only:
- there is no structured flag;
- there is no SUMMARY count;
- `fidelity_state=TRANSCRIBED` can read as stronger than it is;
- 9 MML-only families carry a STATUTORY_PRESCRIBED candidate.

See WSG-R05. A further 22 families use MML 2 as PRIMARY even though an official Gazette copy is held (WSG-R04).

**Conflicts.** All four queue entries are real:
- offence report 'Findings' column, confirmed on the AR54-GAZ p.72 image;
- MML 2 p.303 prints 'IAFD 919 C' and 'IAFD-919A', while the 1993 Gazette p.19 image shows 'IAFD-919C';
- 1954 Gazette 'sections 83-84' versus MML 2 'Sections 83 to 85';
- 'this Form is redundant' appears at L5623 of the DOC and L9013 of DOC-1, and not in the MML 2 PDF text.

**S.R.O. 116/1965.** Supported. Item 2(b) on AR-AMD-1965 p.3 substitutes the discharge-authority words in Appendix I Form No. I under both headings.

**S.R.O. 17(E)/1993.** Every change the register claims is supported:
- r.179 sub-rule (5A) inserted (p.18);
- item 39(a), IAFD-905 para 9 (character statement) substituted;
- item 39(b), Part III (c) IAFD-919C added;
- item 40, set-off paragraphs added to Forms B and C;
- item 41(a), Appendix V heading 170 changed to 170A;
- item 41(b), Form I 170 changed to 170A;
- item 41(c), Forms 1-A and 1-B added (p.20).

Items 39-41 were confirmed on the p.19 page image.

**Gap claims.** The claim that App. II and App. III Pt I are absent from 1954 Gazette pp.59-86 is supported. Printed pages run continuously (PDF 58 is printed 348; PDF 72 is printed 362), and App. I Form II is followed directly by App. III Pt II.

## 5. Register columns compared with the blueprint (section 3 and section 4)

**Present:**
- stable candidate ID;
- exact source copy and SHA-256;
- page or line locator;
- printed name and number;
- field labels (FORM_FIELDS);
- requirement language;
- authority candidate;
- related provisions, companions and dependencies;
- alternates and conflict links;
- independent fidelity, applicability, legal-approval, publication and dependency-freshness states;
- the coverage record linked through `candidate_ids`;
- unique families counted separately from copies.

**Partial or missing:**
- no page-image locator or boundary (bbox) for any form;
- coverage rows lack reviewer evidence, remediation/review state and legal-review references;
- DOC sources use derived line text rather than a documented render with page mapping;
- 'verbatim layout/footnotes' is reduced to labels for the long records (IAFD-906/907), which the register discloses.

These gaps are acceptable for a discovery register but should be closed before template activation. None is graded above P3, and they are noted here rather than as separate findings.

## 6. Coverage honesty

**Good:**
- 20 NOT_HELD rows, including RA 1987, DSR, S.R.O. 348/1960 and 404/1960, IAFK-1162, TA and DPP schedules, AFT Practice Forms 1-9, PRA 2008 and ER/GMO 2023;
- a referenced-forms-not-printed list;
- no aggregate percentage;
- negative results scoped to source copies.

**Weak:**
- INSPECTED_NO_FORMS_FOUND rests on heading scans of OCR or derived text, including a garbled AFT 2011 amendment text (WSG-R06).
- The 'Army-first' scope is not stated in the README or SUMMARY, and Air Force and Navy rule-level instruments are absent from both the not-held and out-of-scope lists (WSG-R07).

## Requested actions (priority order)

1. Fix the AFT Form III rule number to 27 and add a digit-exactness or visual guard for OCR anchors (R01).
2. Make the classifications consistent for 'may' provisions (R02), and stop implying an AR 4 hierarchy (R03).
3. Add a structured MML-only flag and count (R05). Use the official copy as primary, or label the field sets as the MML version (R04).
4. Downgrade heading-scan-only negatives to PARTIAL (R06), and state the service scope and missing Air Force and Navy instruments (R07).
5. Tidy the P3 items: verbatim per-rule quotes (R08), pinpoints (R09), DOC range bounds (R10), README matcher wording (R11), DPP Sch. II typing (R12).
