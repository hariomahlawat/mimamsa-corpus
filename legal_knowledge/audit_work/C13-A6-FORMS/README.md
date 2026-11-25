# C13 Workstream A6: forms and procedural knowledge

**Recorded:** 2026-11-25. **Tool:** `c13-a6-forms/1.0.0`. **Branch:** `claude/c13-a6-forms`.
**Status:** research only. Every row is `DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED`; `legal_approval_state` is `NOT_APPROVED` for every form; `applicability_state` is `NOT_ESTABLISHED`. Nothing here is a legal determination, an approved template or a currency finding. The transcriptions are AI visual readings of page images and are **pending independent review**. WS-G R04 stays deferred, and the restriction on its capability stays in place, until that review confirms them (see "What R04 closure still needs").

## What was done

1. **WS-G R04, done in substance.** I rendered each relevant page of the official copies (`tools/render_pages.py`: pymupdf 2.1, greyscale, 150 dpi; Navy pages 100-110 dpi), read the image, and typed every printed element of each form in order. Each typed element is labelled as a heading, blank, column, question, statement, signature, instruction, note, address or marking. I recorded each page's copy sha256, PDF page, approximate region (bbox as page fractions), renderer and dpi. Misprints are kept as printed and listed in the notes. Where a word could not be read, it is written `[illegible]` and described. **Nothing was filled from the MML or from memory.**
   - Copies used, all sha256-verified before every read (`tools/a6_common.py`):
     - 1954 Gazette `c5ef95a9…`: pp.2-3, 18-19, 36, 42, 58-86;
     - S.R.O. 17(E)/1993 `e9bf2114…`: pp.18-21;
     - S.R.O. 116/1965 `682afce5…`: pp.1-3;
     - AFT (Procedure) Rules 2008 `590cf7cd…`: pp.42-47;
     - DPP Rules 1953 `d969593b…`: p.6, to confirm that the schedules are absent;
     - Navy Act 1957 `db6d2b3e…`: pp.15, 40;
     - Regulations for the Navy Part II `884a893c…`: pp.1, 105;
     - Regulations for the Navy Part IV `e4148ee0…`: p.81.
   - The HF preserved path of each copy is in `PAGE_IMAGE_LOG.csv`.
2. **Comparison with the MML version** (`R04_COMPARISON.csv`, `R04_FAMILY_STATUS.csv`).
   - Each C12 field row is tested against the official transcription by normalised whole-phrase containment.
   - Each official row is tested against the MML 2 text of the same form (`db211918…`, pages from the C12 locator). A row is either exact, a variant (best-window token ratio ≥ 0.85, with the unmatched tokens listed) or not found.
   - These tests locate differences. They do not judge the legal effect of any difference.
3. **Expanded register** (`FORM_REGISTER_C13.csv`): 106 families, each with the full blueprint record:
   - identity and prescribing authority;
   - source copy, edition and exact pages;
   - provision and requirement quote;
   - mandatory or specimen status;
   - applicability as printed;
   - required fields;
   - competent authority;
   - signatories (taken from the official signature blocks where transcribed);
   - supporting documents and procedural dependencies (including the rule text read from images, `spec_register.RULE_READINGS`);
   - version history (including the 1965 and 1993 page-image evidence) and supersession;
   - fidelity and R04 status;
   - legal approval `NOT_APPROVED`, publication `NOT_STAGED` and freshness `NOT_ASSESSED`.
4. **New field file** `FORM_FIELDS_C13_v2.csv`. The C12 `FORM_FIELDS.csv` is not edited.
   - Families with an official transcription get `field_set_version = OFFICIAL_PAGE_IMAGE_TRANSCRIPTION_C13 (source)`.
   - All other families carry their C12 rows, labelled `CARRIED_FROM_C12`.
5. **Navy and Air Force.**
   - New Navy families:
     - Navy Act 1957 s.13 oath of allegiance, s.104(1) members' oath and s.104(2) trial judge advocate oath: statutory forms, transcribed from page images;
     - Regulations for the Navy Part IV Schedule II oath: transcribed;
     - Part IV Schedule I Form INXS I: discovered from the text layer, fields not transcribed;
     - Regulations for the Navy Part II Appendix I, Forms No. 1-34: registered from the list page, which I read as an image (p.105). Each form's heading page comes from the text layer. Fields were not transcribed this cycle.
   - **Air Force:**
     - The Air Force Act 1950 copy prints no forms; it refers to "prescribed" forms, which are in the Air Force Rules 1969, and those are not held.
     - The Regulations for the Air Force 2000 copy (RM-001) and its derived text and metadata were **not opened or used**. Any Air Force form that exists only there is listed as `NEEDS_AUTHORISED_SOURCE`.
   - The guard in `a6_common.is_restricted` mirrors `config/restricted_material.json` (branch `claude/c13-gov`), and a test checks the mirror against that file.
6. **Test oracle** (`ORACLE_CASES.jsonl`, written in `tools/spec_oracle.py`): 86 synthetic cases across 40 families.
   - 28 correct, 26 borderline, 26 defective and 6 abstain.
   - Each case records the mutation applied to the official element list, the synthetic document, the expected Document Studio 9.1 result, `expected_legal_consequence = NOT_DETERMINED`, the expected operational gate (refused), the source pinpoints and any rule readings.
   - The cases were written by hand against the source. No generator or validator exists, and the oracle is not imported by any tool except the build.
   - The build fails if any mutation's pinpoint does not match exactly one official element.
7. **Acquisition requests** (`ACQUISITION_REQUESTS_A6.csv`): 16 instruments that are needed but not held, or not searched. No download was made.

## Headline counts (measured; exact values in `outputs/SUMMARY.json`)

| Item | Count |
| --- | --- |
| Page-image readings / distinct pages read | 63 / 46 |
| Official transcription rows | 955 (9 with an illegible span, 31 incipit-only condition paragraphs; 17 illegible notes in all) |
| **R04 families (22)** | 21 transcribed in full from official page images; 1 amending text only (IAFD-905 para 9, `FF-AR54-APPIII-P1D-CHAR`); 0 not held |
| R04 C12 field rows confirmed in the official transcription | 198 of 227 |
| R04 differences | 29 C12/MML rows not found in the official transcription (14 of them from the amending-only CHAR family); 91 official rows not found in MML 2; 47 official rows that are variants of MML 2 wording |
| R04 official rows with an illegible span | 9 |
| **Statutory candidates (39)** | 31 transcribed from official page images; 8 have no official copy held (DPP Sch. I Forms I-III, ISL Forms A-D, Tolls Pass) and were not filled |
| Register families | 106 (67 from C12 + 39 new: 3 Navy Act, 2 Navy Part IV, 34 Navy Part II); 42 statutory candidates; all NOT_APPROVED |
| Oracle cases | 86 |
| Acquisition requests | 16 |

Examples of differences the comparison found (these are for legal review, not conclusions):
- The 1954 Form A prints "transportation" where MML 2 has other wording.
- The offence report prints "Names of Witnesses", "Punishment awarded" and 8 columns; MML 2 has "Name of witnesses", "Punishments" and a ninth column, "Findings".
- Form B in the 1954 printing has no custody set-off paragraph; S.R.O. 17(E)/1993 inserts it.
- The 1993 printing of summons (c) reads "IAFD-919C".

## Limits (read before relying on anything here)

- These are AI visual readings. bbox values are approximate. A reviewer re-renders the cited page at the recorded dpi (`reproduce_with` column) and compares.
- Appendix I condition paragraphs are recorded as incipits, with every blank itemised. The full wording is on the cited image.
- Short blank lines (for example "on the day of , 19") often show as differences because of punctuation or layout. Each difference has to be checked against both page images.
- Navy Part II forms: list only; fields not transcribed. Navy copies are India Code retypes, not Gazette facsimiles.
- The held amendment Gazettes of 1963, 1965-07, 1979, 1988, 2003, 2019 and 2022 were scanned by text layer only for form changes, and none was found. That negative was **not** confirmed visually. The amendment chain listed on 1993 p.21 is not reconciled (A6-ACQ-03).
- The C12 test suite (`C12-CONSOLIDATION/forms_registry/tests`) resolves its scratch root relative to the checkout, so 4 of its tests cannot find sources from this worktree. That suite predates C13 and is out of scope here. `build_forms_registry.py --check --scratch <scratchpad> --c7 /home/user/c7` still reproduces byte for byte.

## What R04 closure still needs

1. An independent reviewer re-renders a sample of the cited pages, at minimum every page carrying a difference or an illegible span, and confirms the transcription.
2. The legal approval gate (Document Studio 3.3). Until both are done, `CAPABILITY_RESTRICTIONS.csv` row `form_field_lists` stays `NON_OPERATIONAL_RESEARCH_ONLY`. That row was not edited.

## Running

```
PY=/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python
$PY -I tools/build_a6.py            # rebuild outputs/
$PY -I tools/build_a6.py --check    # byte-for-byte reproduction
$PY -I tools/render_pages.py AR54-GAZ 72 --dpi 150 --out <dir>   # re-render a cited page
$PY -m pytest -q -p no:cacheprovider tests/test_legal_audit_c13_forms_a6.py tests/test_legal_audit_c12_research_isolation.py
```

You can override the roots with `A6_SCRATCH` and `A6_C7`. The code is Python 3.11 compatible; it was run on 3.13 with pymupdf 2.1.
