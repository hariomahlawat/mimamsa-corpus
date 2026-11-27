# Independent review: C13 A6 forms (`claude/c13-a6-forms` at 1b05490f)

**Reviewer:** an independent agent; I did not author this work. **Date:** 2026-11-25. **Mode:** read-only. I worked in a scratch clone (`reviews/a6/repo`, made with `git clone --shared`). I made no commits and wrote nothing to HF.
**Question:** can deferred P2 **WS-G R04** close? The C12 finding was that the field lists for 22 families were taken from undated MML copies instead of the official Gazette copies.

## Verdict

**ACCEPT WITH FINDINGS.** There is no P1 finding. There is one P2 finding (IAFD-905 field file) and several P3/INFO findings.

**R04 recommendation: PARTIAL CLOSE.**
- **Close the transcription-fidelity part of R04 for 21 of the 22 families** (CLOSED_VERIFIED). These are the families whose official copies are held and fully transcribed.
- **Keep R04 deferred for IAFD-905** (`FF-AR54-APPIII-P1D-CHAR`).
- Closing R04 does **not** lift the `form_field_lists` capability restriction, which stays `NON_OPERATIONAL_RESEARCH_ONLY`. The legal-approval gate (Document Studio 3.3) is a separate, outstanding condition.

## 1. Reproduction

| Check | Result |
| --- | --- |
| `tools/build_a6.py --check` | `CHECK OK: 9 files reproduce byte-for-byte` |
| `SHA256SUMS` in the A6 directory | all files OK |
| `tests/test_legal_audit_c13_forms_a6.py` | 18 tests in the file. Without a local `claude/c13-gov` ref: 17 pass, 1 skipped. With the ref created from `origin/claude/c13-gov`: 18 pass, so the restricted-material mirror matches the gov file. |
| `tests/test_legal_audit_c12_research_isolation.py` | 6 pass |
| C12 outputs | `git diff a4c0c382..1b05490f -- legal_knowledge/audit_work/C12-CONSOLIDATION` is empty. `FORM_FIELDS.csv` sha `2ce17181…` equals the hash recorded in A6 `SUMMARY.json`. `build_forms_registry.py --check` gives `CHECK OK: 4 files reproduce byte-for-byte`. `CAPABILITY_RESTRICTIONS.csv` is unchanged. |
| Branch scope | 18 files, all under `C13-A6-FORMS/` plus one new test file |
| Headline counts | All recomputed from the CSVs and all match the author's figures: 63 readings over 46 pages; 955 rows; 9 rows with an illegible span; R04 198/227 confirmed, 29 MML-only (14 of them in CHAR), 91 official-only, 47 variant; statutory 31 transcribed + 8 not held = 39; register 106 families (39 of them new Navy); 86 oracle cases |

## 2. Independent transcription check

**Source bytes.** I downloaded every copy from HF dataset `hariomahlawat/mimamsa-corpus` at revision `5524c3d99b6a069249012fecea75093b875a22c7`, using each copy's `hf_path`. The 1954 Gazette, S.R.O. 17(E)/1993 and S.R.O. 116/1965 copies come from `legal_knowledge/preservation/c5_working_store/`; the others come from `data/raw/indiacode/`. All 9 copies matched their recorded sha256: AR54-GAZ `c5ef95a9…`, AR-AMD-1993 `e9bf2114…`, AR-AMD-1965 `682afce5…`, AR54-IC `48f52219…`, AFTPR08 `590cf7cd…`, DPPR53 `d969593b…`, NA57 `db6d2b3e…`, NR65-P2 `884a893c…`, NR65-P4 `e4148ee0…`.

**Rendering.** I used my own renderer (`reviews/a6/scripts/render.py`), not the author's tool: pymupdf, greyscale, page split into overlapping top and bottom halves. Dpi was 220 for the Gazette, 200 for 1993, 110 for AFTPR and 150 for the Navy copies. I read each image and compared it row by row with `OFFICIAL_TRANSCRIPTIONS.csv`, checking for missing or extra fields, wording and order.

**Census: every page that has a difference or an illegible span.** That is 22 pages:
- AR54-GAZ pp. 2, 3, 18, 19, 72–86;
- AR-AMD-1993 pp. 19–21.

These pages also cover every page of all 22 R04 families.

**Seeded random sample of the other 24 pages.** I drew 10 pages with `random.Random(20261125)`:
- AFTPR08 pp. 42, 43, 47;
- AR54-GAZ pp. 42, 61, 63, 65, 67, 68;
- NA57 p. 40.

I also checked NR65-P4 p. 81 (a Navy page) outside the sample.

| Set | Pages | Rows | Text/field errors | Pinpoint errors | Row accuracy, strict (95% Wilson CI) | Row accuracy, text only |
| --- | --- | --- | --- | --- | --- | --- |
| Census (difference/illegible pages) | 22 | 499 | 1 | 3 | 99.20% (97.96–99.69) | 99.80% (98.87–99.96) |
| Seeded sample | 10 | 184 | 3 | 0 | 98.37% (95.32–99.44) | 98.37% (95.32–99.44) |
| All checked (+NR65-P4 p.81) | 33 | 693 / 955 | 4 | 3 | **98.99% (97.93–99.51)** | **99.42% (98.53–99.78)** |

The rows are clustered by page, so the Wilson interval is somewhat too narrow. The 262 unchecked rows lie on 14 pages and are estimated from the sample rate only. The comparison is itself an AI visual reading, so the method is not independent of the author's.

**Errors found (all minor):**
1. **AR54-GAZ p.73, `FF-AR54-APPIII-P3B` seq 3.** The page prints "Whereas a ____ court-martial has been ordered…", with a blank for the type of court-martial. The row "Whereas a court-martial has been ordered to assemble at" drops that blank, although in (a) on the same page the author split at every blank.
2. **AR54-GAZ p.68, `FF-AR54-APPI-F2` seqs 70, 78, 82.** Printed misprints were silently corrected: "whcih" became "which", "Reseve" became "Reserve", and "Service or years" became "Service for years". The README says misprints are kept as printed, and elsewhere they are ("regmient", "Prision", "togethe", "PRAT III").
3. **AR54-GAZ p.19, `FF-AR54-APPIII… R46B/R46C/R46D` seq 1.** The rule 46 preamble is printed on p.18 but recorded as `pdf_page` 19. The text is correct; only the pinpoint is wrong.

**Confirmed correct.** Everything else matched the page images:
- all column, heading, note and signature rows;
- order on every checked page;
- every printed-as-is misprint;
- the absence of a "Findings" column on p.72, with the 8 numbered columns;
- "IAFD-919C" on 1993 p.19;
- "FORM" printed with no letter on p.80.

The 9 `[illegible]` spans are on pp. 77, 79 (×2), 81 (×3), 83 and 1993 p.19 (×2). On my images each one is genuinely degraded or clipped, for example "corresponding u11h the enemy", "which is to b…", "nives'igating" and "b?fore".

## 3. Gap filling

- **Illegible spans.** None of the 9 was filled. Each stays `[illegible]` and is described in `PAGE_IMAGE_LOG`. That includes cases where the MML or common sense would supply the word, such as "with", "to be", "investigating" and "before".
- **The 8 statutory forms with no official copy** (DPP Sch. I Forms I–III, ISL Forms A–D, Tolls Pass). There are no official rows. `FORM_FIELDS_C13_v2.csv` carries their C12 rows, labelled `CARRIED_FROM_C12: MML_ONLY_UNVERIFIED`, and the oracle abstains on them (AB-01, AB-03). They were carried with a label, not filled.
- **IAFD-905.** Nothing was filled. However, v2 drops the rest of the form instead of carrying it with a label (finding F01, P2).
- **Degraded glyphs read as the obvious word.** A few clearly readable but degraded words were normalised without a mark: p.81 "warrant ol" read as "warrant of", p.82 "r?quire an.l", p.65 "attacl cd … sl cct ıoll". I do not consider this filling from memory, but it is applied inconsistently with the `[illegible]` policy (F05).

## 4. Oracle

- All 86 cases have `synthetic: true` and carry the marking "SYNTHETIC TEST DOCUMENT - NOT A REAL RECORD"; values are placeholders.
- `expected_legal_consequence` is `NOT_DETERMINED` and the operational gate is `REFUSED_RESEARCH_ONLY` for all 86.
- I checked the answer keys of **32 cases** against my own page images: OR-01..06, SA-02/03, SB-02/03, SC-02/03/04, DR-02/03/05, S1-02/03/05, S2-02, WA-02, WC-02, WD-01, WF-02, WI-01, WK-01, W1A-02/04, W1B-02, AF1-03/05, AF3-02, N104-01, NP4-02 and O45-02.
- **Every mutation target exists as printed** on the cited page, and every expected result is consistent with the printed text and with the stated AR 4(3) caveat.
- One cosmetic issue: S1-05 deletes Q5 but leaves its "ANSWER" line in the synthetic document (INFO).

## 5. Navy additions and restricted material

- **Navy sources.**
  - Navy Act 1957 (`db6d2b3e…`), Navy Regulations Part II (`884a893c…`) and Part IV (`e4148ee0…`) are India Code bitstreams (`indiacode.gov.in/server/api/core/bitstreams/...`).
  - Their C7 metadata has `access_marking = null`.
  - A full-text scan for "official use only / restricted / confidential / secret" finds only ordinary regulation wording (for example "confidential Navy Orders" in a definition, and "Confidential Reports" as a regulation heading). There is no protective marking on any page. **Not restricted.**
  - Pages checked visually: NA57 p.40 (8 rows), NR65-P4 p.81 (10 rows) and the NR65-P2 list page p.105. All matched.
  - The list on p.105 runs only to Form 25. The titles of Forms 26–34 come from p.106, read through the text layer only (F06).
- **RM-001** (`4284820e…`, `regs-regulations-for-the-air-force-reprinted-edition-2000`).
  - Neither the hash nor the doc_id appears in any transcription, register, field, comparison, oracle or acquisition output.
  - It appears only as a deny-list:
    - in the guard code `a6_common.py`;
    - in the test file;
    - in `SUMMARY.json`, under `restricted_material_excluded`, which lists the source hash and two derived hashes.
  - These are identifiers for exclusion, not content. `read_source` refuses the copy, and that is tested. No Air Force form was derived from the 2000 copy; AB-05 abstains (F08, INFO).

## 6. R04 recommendation in detail

R04 asked for the official copy to become primary wherever one is held, with a visual check, and for differences to go to a queue.

**What closes (21 families).** For these 21 families the official Gazette text (1954, plus the 1993 amendments) has now been transcribed from page images. I re-rendered every page they occupy and found 1 field-level omission (p.73 P3B) in 499 rows, at 99.8% text-only accuracy (CI 98.9–99.96). Every C12/MML row that is not in the official text is listed in `R04_COMPARISON.csv` for review. → **CLOSED_VERIFIED** for transcription fidelity, once F02 is fixed or accepted.

**What stays deferred.**
- **IAFD-905 (`FF-AR54-APPIII-P1D-CHAR`).** The only official text held is the substituted para 9 (S.R.O. 17(E)/1993 item 39(a)). The 1954 Gazette prints no Appendix III Part I: p.72 runs straight from Appendix I Form II to Appendix III Part II. The rest of IAFD-905 is therefore still MML-only. R04 stays deferred for this family until the official base text is acquired. F01 must also be fixed.
- **The 8 statutory forms with no official copy.** These are outside R04's scope, because R04 covers families whose official copy *is* held. They must stay `MML_ONLY_UNVERIFIED` and be tracked as acquisition items (A6-ACQ-06 and the others). They do not block R04.
- **Capability restriction.** `form_field_lists` stays `NON_OPERATIONAL_RESEARCH_ONLY` until legal approval is given. R04 closure is a fidelity finding, not an approval.

## Findings (summary; detail in the CSV)

| ID | Sev | Statement |
| --- | --- | --- |
| F01 | P2 | The IAFD-905 v2 field set (5 rows, para 9 only) claims to supersede **all** C12 rows of the family and drops the rest of the form. The register's `required_fields` says "5 printed elements". This overstates the official coverage. |
| F02 | P3 | p.73 P3B seq 3 omits the blank before "court-martial" (the type of court-martial). |
| F03 | P3 | p.68 APPI-F2: 3 misprints were silently corrected, contrary to the stated as-printed policy. |
| F04 | P3 | Wrong page pinpoint for the rule 46 preamble rows of R46B, R46C and R46D (printed on p.18, recorded as p.19). |
| F05 | P3 | The blank and normalisation conventions are applied inconsistently: blanks embedded in statement rows ("I …… do solemnly declare") are not itemised, and degraded glyphs are sometimes normalised and sometimes marked `[illegible]`. |
| F06 | P3 | Page reads named in the README are missing from `PAGE_IMAGE_LOG`: 1965 pp.1–3, DPP p.6, NR65-P2 pp.1/105 and 1993 p.18 (rule readings). The Navy Part II list is described as "p.105 (page image read)", but Forms 26–34 come from p.106 via the text layer. |
| F07 | INFO | The reviewer's comparison is itself an AI visual reading. Get a human spot check of a few pages before the legal gate. |
| F08 | INFO | The RM-001 hashes appear only as a deny-list (`SUMMARY.json`, guard, tests). Consider citing the restriction id alone. |
| F09 | INFO | Oracle S1-05 leaves an orphan "ANSWER" line after deleting Q5. |
| F10 | INFO | All headline counts reproduce exactly. C12 outputs are unchanged and the C12 research-isolation test passes. |
