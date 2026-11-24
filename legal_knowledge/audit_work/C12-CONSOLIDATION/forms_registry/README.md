# C12 Workstream G: forms registry (discovery from held sources only)

**Recorded:** 2026-11-24
**Status:** Discovery register only. Every row is `DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED`. Nothing here is an approved template, a currency finding or a legal determination. Classifications are *candidates* on the blueprint axes.
**Version:** tool 1.1.0, remediated after the independent review `../reviews/review_wsg_forms.md` (findings WSG-R01..R15). See `REMEDIATION_C12.md` and the change log below.
**Scope (Army-first):** this cycle registers forms from the held Army Rules 1954 copies, plus the AFT (Procedure) Rules 2008, DPP Rules 1953, Indian Soldiers (Litigation) Rules 1938, TA Rules 1948, Indian Tolls Rules 1942 and Assam Rifles Act 1941 copies that are held. Air Force and Navy rule-level instruments were **not assessed**: held derived texts were heading-scanned only, and official copies are NOT_HELD (listed in `SOURCE_COVERAGE.csv` with `scope_this_cycle=OUT_OF_SCOPE_THIS_CYCLE`). The 67 families are not the military-law form universe.
**Definition followed:** `docs/product/FORM_DISCOVERY_AND_COVERAGE_REGISTER.md`, `docs/architecture/DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md` §3 and ADR-0003 (branch `origin/docs/mimamsa-product-blueprint-2026-11-24`).

## What was done

- Only sources already held were examined: the scratchpad working store (read-only), the owner-supplied MML originals (`mml_x/originals`) with the WS-C pinned derived DOC line texts (`repro1/`), and raw files read from c7 git objects at `ad77758d` with `git cat-file`. Nothing was downloaded. No file outside this directory was written, and nothing was committed.
- Before it is read, every source is checked against its byte SHA-256. A mismatch stops the build.
- Form titles, anchors and field labels were copied from the printed text of the cited copy. The tool checks each one against that copy's text layer with a **normalised whole-word match** (case and punctuation stripped, whole words, within the cited page or line range). This is not a raw verbatim comparison:
  - For native-text sources (MML 2, MML vol 3, India Code compilation) the build **fails** if a label has no normalised whole-word match.
  - For OCR scans (1954 Gazette, 1993 amendment, AFT Procedure Rules) a fuzzy score is recorded instead.
  - Alternate copies are cross-checked field by field (`FORM_FIELDS.csv` `cross_copy_presence`). Labels of two words or fewer, and a few stock phrases, are flagged `generic_label=YES`; a cross-copy hit on them is weak evidence and is excluded from `fields_matched_non_generic`.
- Quotations of rule text cited to a native-text page (`[AR54-IC p.N]` and similar) are checked by the build: each quoted piece must have a normalised whole-word match on the cited page (or the next page). Rule numbers next to such citations must occur on the cited page.
- **Rule-number guard (WSG-R01).** A rule number written by hand into a title, prescribing provision or requirement quote whose source is an OCR scan is accepted only if a recorded page-image check (`spec_forms.VISUAL_CHECKS`) confirms it. Otherwise the build fails. Digits in OCR anchors must be exact text-layer tokens or on a visually checked page.
- Page images were rendered with pymupdf from the hash-verified bytes and read for: 1954 Gazette p.2 (AR 4), pp.59-61 and p.72; 1993 amendment p.19; AFT (Procedure) Rules pp.26, 27, 29 (band), 37, 38, 42 (upper part), 46, 47; AFT (Procedure) Amendment Rules 2011 pp.1-2. These are AI visual readings, not legal validation. All other pages are text-layer only, and no row is `FIDELITY_VERIFIED`. `TRANSCRIBED` means the primary copy is a native text layer and every label had a normalised whole-word match there.

## Outputs (`outputs/`)

| File | Content |
| --- | --- |
| `FORM_DISCOVERY_REGISTER.csv` | One row per form occurrence (candidate) in a specific source copy. Occurrences are grouped by `form_family_id`; unique forms are counted separately from copies and versions. Each row records: source logical ID and copy SHA-256; locator (PDF page, or DOC derived line); anchor match; prescribing provision and the requirement language as printed; form-authority candidate; status category; applicability; signatory; competent authority; dependencies; companion documents; version and amendment history; supersession; alternate occurrences; fidelity; independent status axes; uncertainties. |
| `FORM_FIELDS.csv` | Printed field labels, questions, columns, signature blocks and instruction notes for each family, taken from the PRIMARY occurrence, with a presence check in every other copy. No field is marked mandatory, because no held form prints field-level mandatoriness. The form-level requirement is in the register. |
| `SOURCE_COVERAGE.csv` | Coverage records per source copy and segment. Each record gives the method, pages visually inspected, gaps or exclusions, and the coverage state (blueprint vocabulary). It also counts form-like headings found by the automated scan that are not covered by a registered occurrence. Further rows cover held Army Rules and Army Act amendment Gazettes from the C5 register, c7 derived texts that were only heading-scanned (Navy, Air Force, BNSS and CrPC schedules), and known-needed sources that are not held. |
| `SUMMARY.json` | Counts, input hashes, the conflict queue, and referenced forms not printed in any held copy. No aggregate coverage percentage is given, because the denominators are unknown. |

## Headline results (see SUMMARY.json for exact counts)

- **67 form families, 215 occurrences, 541 field rows.** Statutorily prescribed candidates: **39** (42 before remediation).
- **Source basis (`source_basis`):** 32 of 67 families are **MML_ONLY** (no official copy held), 30 are **BOTH**, and 5 are **OFFICIAL_COPY** only. Of the 30 BOTH families, 22 take their field list from MML 2 although an official copy is held (`field_set_version=MML_VERSION_UNVERIFIED`), and 8 (oath forms) take it from the India Code compilation. "Official copy" means a held non-MML government copy (Gazette facsimile, India Code compilation or India Code file); it does not mean authenticated or current.
- **Not confirmed from an official copy:** 8 STATUTORY_PRESCRIBED candidates carry `statutory_confirmation_status=NOT_CONFIRMED_FROM_OFFICIAL_COPY`. These are DPP Sch. I Forms I-III (rule text official, form text MML only) and ISL Forms A-D and the Indian Tolls Pass (rule text and form text both from unverified MML vol 3).
  - Army Rules 1954: 44 families. These are Appendix I Forms I-II, Appendix II Parts I-IV, Appendix III (IAFD-937, medical certificate, IAFD-916, AR 36 declaration, IAFD-906, IAFD-907, IAFF-956, IAFD-905 and schedule, IAFD-901, summonses (a)-(c), delay report), Appendix IV Forms 1, 2 and A-G, Appendix V Forms H, I, 1-A, 1-B and J-L, and the oath/affirmation forms in rr.9, 45, 46(A)-(D), 109 and 140.
  - AFT (Procedure) Rules 2008: Forms I-III.
  - DPP Rules 1953: Schedule I Forms I-III and Schedule II.
  - Indian Soldiers (Litigation) Rules 1938: Forms A-D.
  - TA Rules 1948: Form I, Form II and Schedules II-B to II-I.
  - Indian Tolls Rules 1942: Form of Pass.
  - Assam Rifles Act 1941: Schedule Statement.
- **Gaps:**
  - The 1954 Gazette lists Appendix II and Appendix III Part I in its arrangement (p.58), but their text was not located in pp.59-86. Those forms are known only from unverified MML copies.
  - The India Code Army Rules compilation prints no appendices.
  - MML 2 does not reproduce Appendix I. It names IAFK-1162, which is not held.
- **Conflict queue:**
  - Offence report columns: the 1954 Gazette page image (p.72) has 8 columns and no 'Findings' column; MML 2 p.302 has 9 including 'Findings'.
  - Summons to a court of inquiry: IAFD-919C in the 1993 Gazette, but IAFD-919C/919A in MML 2.
  - App. IV Forms 1-2: 'sections 83-84' in 1954, but '83 to 85' in MML 2.
  - The DOC transcriptions add an editorial note after Form E: 'this Form is redundant' (IPC s.53A).
- **Field divergence queue** (SUMMARY `field_divergence_queue`): offence report 'Findings' (absent from the 1954 page image) and summons (c) 'for investigation into' (the 1993 page image prints a different, defectively printed word).
- **Version evidence used:**
  - S.R.O. 116/1965 (App. I Form I).
  - S.R.O. 17(E)/1993: IAFD-905 para 9; summons (c) added; Forms B and C custody set-off; App. V heading and Form I changed to 170A; Forms 1-A and I-B added.
  - S.R.O. 348/1960 and S.R.O. 404/1960 also change forms, but they are **not held**.

## Status vocabulary used

- `form_authority_type_candidate` uses the blueprint values. The **'shall' rule** is applied mechanically: a form is `STATUTORY_PRESCRIBED` only where the quoted provision says the form 'shall' be used (or the instrument 'shall' be in it); for example AR 22(3)(a), 23(6), 26(3), 27, 166, 167, 170A(1), 170A(4), 170B(1)(b), 171, 179(5A) and 190; AFT rr.4(1) and 27(3); DPP rr.9 and 29(1); ISL rr.4-6; Tolls r.2. Every other form is `OTHER_OR_UNDETERMINED`. The test suite checks that every STATUTORY_PRESCRIBED row's quote contains 'shall'.
- Reclassified in remediation (SUMMARY `reclassified_in_remediation`): App. V Form H (AR 169 'may, if he thinks fit') and AFT Form II (r.4(4) 'may attach'), from STATUTORY_PRESCRIBED to OTHER_OR_UNDETERMINED; DPP Schedule II (r.33(3) document list) from STATUTORY_PRESCRIBED to OTHER_OR_UNDETERMINED, keeping status MANDATORY_DOCUMENT_LIST; SGCM status changed from PERMISSIVE_USE_AR4 to PERMISSIVE_USE_SPECIFIC_RULE (AR 151(1) 'may').
- **AR 4(1) caveat.** Every Army Rules appendix row carries AR 4(1) verbatim in `cross_cutting_caveat_as_printed` ('... a deviation from such forms shall not, by reason only of such deviation, render invalid any charge, warrant, order, proceedings or any other document relevant to these rules'). Its text was checked on the 1954 Gazette p.2 image. No relationship between AR 4(1) and any specific rule is asserted; this is for legal review.
- `status_category` uses tool vocabulary that refines this:
  - `MANDATORY_FORM_WORDING`
  - `MANDATORY_WITH_ALTERNATIVE_PERMITTED` (oaths)
  - `QUALIFIED_AS_FAR_AS_PRACTICABLE` (AR 26(3))
  - `PERMISSIVE_USE_AR4`
  - `PERMISSIVE_USE_SPECIFIC_RULE` (a specific rule says the form 'may' be used)
  - `SPECIMEN_OR_ILLUSTRATION`
  - `REQUIREMENT_LANGUAGE_NOT_EXTRACTED`
  - and others
- The other axes are fixed for every row: `applicability_state=NOT_ESTABLISHED`, `legal_approval_state=RESEARCH_ONLY`, `publication_state=NOT_STAGED`, `dependency_freshness_state=NOT_ASSESSED`.
- Editorial material printed in MML is excluded from candidate forms when the MML itself says it does 'not form part of the Appendices'. This covers the notes on forms of charges, the court-room arrangement and the memoranda.

## Columns added in remediation

| File | Columns |
| --- | --- |
| Register | `source_basis`, `official_copy_extent`, `field_set_version`, `statutory_confirmation_status`, `cross_cutting_caveat_as_printed`, `locator_end_basis` (DOC ranges bounded by the next registered occurrence or end of file; `CAPPED_AT_400_LINES` where the form end is not established), `page_image_locator` and `visual_check_refs` (where a page image was checked), `page_region_bbox` (empty: no bbox recorded), `fields_matched_non_generic`, `review_finding_refs` |
| Fields | `match_method`, `generic_label`, `field_set_version`, `official_copy_presence` |
| Coverage | `scope_this_cycle`, `coverage_method_limitation` (`HEADING_SCAN_NO_FORMS_FOUND_NOT_VISUALLY_CONFIRMED` / `TEXT_LAYER_SCAN_NO_FORMS_FOUND_NOT_VISUALLY_CONFIRMED`), `reviewer_evidence`, `review_remediation_state`, `legal_review_ref` (empty: no legal review exists) |

## Before / after (review WSG remediation)

| Count | Before (1.0.0) | After (1.1.0) |
| --- | --- | --- |
| Form families / occurrences / field rows | 67 / 215 / 541 | 67 / 215 / 541 |
| STATUTORY_PRESCRIBED candidates | 42 | 39 |
| MML-only families (structured) | 32 (free text only) | 32 (`source_basis=MML_ONLY`) |
| STATUTORY_PRESCRIBED and MML-only, not confirmed | 9 (unflagged) | 8 (`NOT_CONFIRMED_FROM_OFFICIAL_COPY`) |
| Field lists labelled MML version though official copy held | 0 | 22 |
| Coverage rows | 83 | 90 |
| `INSPECTED_NO_FORMS_FOUND` | 40 | 1 (visually confirmed: AFT 2011 amendment) |
| `PARTIAL` | 11 | 50 (39 carry a not-visually-confirmed limitation) |
| `INACCESSIBLE` (not held) | 21 | 28 |
| Recorded page-image checks | 1 (pp.59-61) | 13 |
| Tests | 15 | 27 |

## Change log by finding

- **WSG-R01 (P1):** AFT Form III corrected to rule 27 (title '(see rule 27)', r.27(3), version history). This was checked on page images of pp.37, 38 and 46. Rule-number guard and anchor-digit guard added, with tests.
- **WSG-R02:** Form H and AFT Form II reclassified as OTHER_OR_UNDETERMINED under the mechanical 'shall' rule. The reclassified list is in SUMMARY.
- **WSG-R03:** the 'permissive unless a specific rule uses shall' wording was removed and replaced by a neutral statement. AR 4(1) is now recorded verbatim in `cross_cutting_caveat_as_printed`.
- **WSG-R04:** field lists are labelled with `field_set_version` (official copies are OCR and were not transcribed). Official-copy presence is recorded per field, with a divergence queue. The offence report 'Findings' example was corrected from the p.72 page image.
- **WSG-R05:** added `source_basis`, `official_copy_extent` and `statutory_confirmation_status`, with SUMMARY counts. ISL and Tolls provisions are marked 'rule text per unverified MML vol 3 only'.
- **WSG-R06:** 39 heading-scan or text-layer negatives were downgraded to PARTIAL with a method limitation. The AFT (Procedure) Amendment Rules 2011 were added as a source and checked on page images. r.12A and r.7(2) are recorded on AFT Form I as an unexamined dependency, without interpretation.
- **WSG-R07:** scope is stated in the README and SUMMARY. Air Force and Navy instruments are listed as NOT_HELD or out of scope.
- **WSG-R08:** oath quotes are now verbatim for each rule (AR 46 'as shall be appropriate'; AR 140 'if so required by the Act'). A quote verifier was added.
- **WSG-R09:** AR 22(3)(a) pinpoint; Form I now leads with AR 170B(1)(b); Form 1-B uses AR 170A(4); SGCM status is now PERMISSIVE_USE_SPECIFIC_RULE.
- **WSG-R10:** DOC ranges are bounded by end of file, and the basis is recorded. Generic labels are flagged.
- **WSG-R11:** the method is described as 'normalised whole-word match'.
- **WSG-R12:** DPP Schedule II retyped as OTHER_OR_UNDETERMINED / MANDATORY_DOCUMENT_LIST.
- **WSG-R13 (INFO):** the Python version is recorded in SUMMARY. A Python 3.11 run with pymupdf is still not possible here, because nothing was installed.

## Running

```
PY=/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python
$PY -I tools/build_forms_registry.py          # rebuild outputs/
$PY -I tools/build_forms_registry.py --check  # exit 0 only if outputs reproduce byte-for-byte
$PY -m pytest -q -p no:cacheprovider tests/
```

- Roots can be overridden with `--scratch`, `--c7` or `--out`, or with the environment variables `FR_SCRATCH` and `FR_C7`.
- The code is Python 3.11 compatible. It needs pymupdf (the version used is recorded in SUMMARY.json) and git.
- The source definitions are in `tools/spec_sources.py`. The form families, occurrences, quotations and field labels are in `tools/spec_forms.py`.

## Not done / next evidence needed

- Visual page-image inspection of the remaining scanned pages: 1954 Gazette pp.62-71 and 73-86, 1993 amendment pp.1-18 and 20-21, and AFT Form I body pp.43-45. Then field-by-field transcription from the official copies, so that the 22 MML-version field lists can be replaced. Only after that can fidelity be promoted.
- Air Force and Navy rule-level instruments: not assessed this cycle.
- Full field itemisation of the long procedural records. IAFD-906 and IAFD-907 are recorded at header and section level only; the statement of offences and the specimen charges catalogues are not itemised.
- Official copies of:
  - Appendix II and Appendix III Part I;
  - current Appendix I (IAFK-1162);
  - S.R.O. 348/1960 and S.R.O. 404/1960;
  - TA Rules and DPP Rules schedules;
  - AFT Practice Rules Forms 1-9;
  - RA 1987, DSR, and Army Orders and Instructions.

  None of these is held, and acquisition is not authorised here.
- Legal review: who reviews, against what scope, and as of which date.
