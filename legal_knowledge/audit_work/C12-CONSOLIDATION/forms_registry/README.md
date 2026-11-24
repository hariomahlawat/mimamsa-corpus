# C12 Workstream G: forms registry (discovery from held sources only)

**Recorded:** 2026-11-24
**Status:** Discovery register only. Every row is `DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED`. Nothing here is an approved template, a currency finding or a legal determination. Classifications are *candidates* on the blueprint axes.
**Definition followed:** `docs/product/FORM_DISCOVERY_AND_COVERAGE_REGISTER.md`, `docs/architecture/DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md` §3 and ADR-0003 (branch `origin/docs/mimamsa-product-blueprint-2026-11-24`).

## What was done

- Only sources already held were examined: the scratchpad working store (read-only), the owner-supplied MML originals (`mml_x/originals`) with the WS-C pinned derived DOC line texts (`repro1/`), and raw files read from c7 git objects at `ad77758d` with `git cat-file`. Nothing was downloaded. No file outside this directory was written, and nothing was committed.
- Before it is read, every source is checked against its byte SHA-256. A mismatch stops the build.
- Form titles, anchors and field labels were copied from the printed text of the cited copy. The tool checks each one against that copy's text layer:
  - For native-text sources (MML 2, MML vol 3, India Code compilation) the build **fails** if a label is not present verbatim. The match is a whole-word match on normalised text.
  - For OCR scans (1954 Gazette, 1993 amendment, AFT Procedure Rules) a fuzzy score is recorded instead.
  - Alternate copies are cross-checked field by field. The results are in `FORM_FIELDS.csv` `cross_copy_presence`.
- Visual inspection was done only for 1954 Gazette pp.59-61 (Appendix I Form No. I), rendered at 110 dpi. All other pages are text-layer only. For that reason no row is `FIDELITY_VERIFIED`. `TRANSCRIBED` means the labels were taken from a native text layer and were verified to occur verbatim.

## Outputs (`outputs/`)

| File | Content |
| --- | --- |
| `FORM_DISCOVERY_REGISTER.csv` | One row per form occurrence (candidate) in a specific source copy. Occurrences are grouped by `form_family_id`; unique forms are counted separately from copies and versions. Each row records: source logical ID and copy SHA-256; locator (PDF page, or DOC derived line); anchor match; prescribing provision and the requirement language as printed; form-authority candidate; status category; applicability; signatory; competent authority; dependencies; companion documents; version and amendment history; supersession; alternate occurrences; fidelity; independent status axes; uncertainties. |
| `FORM_FIELDS.csv` | Printed field labels, questions, columns, signature blocks and instruction notes for each family, taken from the PRIMARY occurrence, with a presence check in every other copy. No field is marked mandatory, because no held form prints field-level mandatoriness. The form-level requirement is in the register. |
| `SOURCE_COVERAGE.csv` | Coverage records per source copy and segment. Each record gives the method, pages visually inspected, gaps or exclusions, and the coverage state (blueprint vocabulary). It also counts form-like headings found by the automated scan that are not covered by a registered occurrence. Further rows cover held Army Rules and Army Act amendment Gazettes from the C5 register, c7 derived texts that were only heading-scanned (Navy, Air Force, BNSS and CrPC schedules), and known-needed sources that are not held. |
| `SUMMARY.json` | Counts, input hashes, the conflict queue, and referenced forms not printed in any held copy. No aggregate coverage percentage is given, because the denominators are unknown. |

## Headline results (see SUMMARY.json for exact counts)

- **67 form families, 215 occurrences, 541 field rows.**
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
  - Offence report columns differ between the 1954 OCR text and MML 2 ('Findings' column).
  - Summons to a court of inquiry: IAFD-919C in the 1993 Gazette, but IAFD-919C/919A in MML 2.
  - App. IV Forms 1-2: 'sections 83-84' in 1954, but '83 to 85' in MML 2.
  - The DOC transcriptions add an editorial note after Form E: 'this Form is redundant' (IPC s.53A).
- **Version evidence used:**
  - S.R.O. 116/1965 (App. I Form I).
  - S.R.O. 17(E)/1993: IAFD-905 para 9; summons (c) added; Forms B and C custody set-off; App. V heading and Form I changed to 170A; Forms 1-A and I-B added.
  - S.R.O. 348/1960 and S.R.O. 404/1960 also change forms, but they are **not held**.

## Status vocabulary used

- `form_authority_type_candidate` uses the blueprint values. Army Rules appendix forms governed only by AR 4 ('may be used ... deviation shall not ... render invalid') are recorded as `OTHER_OR_UNDETERMINED`. A form is `STATUTORY_PRESCRIBED` only where a specific provision says it 'shall' be in the form; for example ARR 22, 23(6), 27, 166, 167, 170A, 171, 179(5A) and 190, AFT r.4, DPP rr.9 and 29, and ISL rr.4-6.
- `status_category` uses tool vocabulary that refines this:
  - `MANDATORY_FORM_WORDING`
  - `MANDATORY_WITH_ALTERNATIVE_PERMITTED` (oaths)
  - `QUALIFIED_AS_FAR_AS_PRACTICABLE` (AR 26(3))
  - `PERMISSIVE_USE_AR4`
  - `SPECIMEN_OR_ILLUSTRATION`
  - `REQUIREMENT_LANGUAGE_NOT_EXTRACTED`
  - and others
- The other axes are fixed for every row: `applicability_state=NOT_ESTABLISHED`, `legal_approval_state=RESEARCH_ONLY`, `publication_state=NOT_STAGED`, `dependency_freshness_state=NOT_ASSESSED`.
- Editorial material printed in MML is excluded from candidate forms when the MML itself says it does 'not form part of the Appendices'. This covers the notes on forms of charges, the court-room arrangement and the memoranda.

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

- Visual page-image inspection of all scanned pages, including 1954 Gazette pp.62-86, the 1993 amendment and the AFT forms. Only after that can fidelity be promoted.
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
