# C12 Workstream F: statutory citation improvement (983 frozen citation items)

**Status: research proposal, version `C12F-v1.1` (v1 remediated after the independent review
`../reviews/review_wsf_statutory.md`, findings F-01 to F-10; mapping in `REMEDIATION_C12.md`). Nothing has been applied.** The frozen originals
(`records_658.jsonl` sha256 `9a8f0d19…`, `cases_53.jsonl` `8b8d53cd…`) are unchanged. The tool checks them on every
run, against the worktree and against `git show 21e73b83:` in `/home/user/c7`. `corpus_crosswalk.csv`, the C10
outputs and the KB records are also unchanged. Every evidence-state change below is a **proposal** in
`outputs/CORRECTION_PROPOSALS_C12.csv`.

## Result (honest before / after)

| Evidence state | Baseline (C5/C10) | C12F-v1 (reviewed) | **C12F-v1.1 (remediated)** | Change vs baseline |
| --- | ---: | ---: | ---: | ---: |
| EXACT_ANCHOR | 42 | 105 | **99** | +57 |
| PARTIAL_MATCH | 652 | 589 | **595** | −57 |
| MISSING_EVIDENCE | 289 | 289 | **289** | 0 |

The regenerated figures equal the reviewer's expected 99 / 595 / 289. They were not tuned: the six withdrawals follow from
two data-driven rules (F-01, F-02); `SUMMARY.json` → `review_reconciliation` confirms that the 57 promotions the review
supported are all still promoted, that the 6 it did not support are all withdrawn, and that nothing else moved.

**Withdrawn in v1.1 (6, now PARTIAL_MATCH):**

| Item | Record | Reason |
| --- | --- | --- |
| C10Q-CW-0031 | KB-018 | r.15: OPEN alleged amendment OQ-A-10 / GAP-15 (cross-refs XC-03 DISCREPANCY, WS-C OQ-C-10) — F-01 |
| C10Q-CW-0363 | ADM-006 | same (r.15) — F-01 |
| C10Q-CW-0369 | ADM-012 | same (r.15) — F-01 |
| C10Q-CW-0395 | ADM-032 | same (r.15) — F-01 |
| C10Q-CW-0402 | ADM-SC-03 | same (r.15) — F-01 |
| C10Q-CW-0087 | COI-021 | locator "r 180 explanatory note": no explanatory note to r.180 is printed in the 1954 Gazette (p.341 image-checked) or in any amending instrument — F-02 |

- **57 promotions (PARTIAL → EXACT), all proposed only.** 37 Army Rules items: rr.14, 17, 26, 33-41, 134, 178-181 and 186 (alone or in combination). 17 Virendra Kumar (2020) items and 3 Parashotam Dass (2023) items, each with explicit paragraph locators. Every 1954 principal page behind the 37 Army Rules promotions now has its own per-page image check (F-03).
- **EXACT is citation-level only (F-04).** `IMPROVEMENT_MATRIX.csv` now carries `record_level_state` (the minimum state over all of a record's citation items) and `exact_scope`. An EXACT item on a record whose other items are PARTIAL or MISSING is marked `CITATION_LOCATOR_ONLY` (66 items) and its proposal says the record must not be shown or aggregated as EXACT. Judgment promotions on records whose statutory content stays PARTIAL: **KB-005, COI-003, HCE-003, HCE-004, HCE-008, HCE-029 (r.22) and KB-012 (r.182)** — the seven the review named — plus three found by the same rule: **COI-021** (its Army Rules item is now withdrawn, F-02) and **KB-025, KB-028** (Parashotam promotions; their AFT Act ss.30-32 items stay PARTIAL / record MISSING).
- **The 42 baseline EXACT items are all kept, and each now has a page anchor.** Two of them (r.135: V9-WF-10, V9-SC-14) get a **basis correction**: the C5 parser read only the first number of "rr.134,135,136", so it missed the S.R.O. 17(E)/1993 item 25 amendment. They stay EXACT only because that amending Gazette is itself a registered eligible copy with an image-checked page (1993 p.17).
- **No MISSING_EVIDENCE item is promoted.** No demotion was needed.

### The priority clusters

| Cluster | Army Rules items | Outcome | Why |
| --- | ---: | --- | --- |
| r.22 Hearing of charge | 29 | **all stay PARTIAL** | 1954 text: Gazette PDF p.9, printed p.299 (C12 image check). r.22 was substituted by S.R.O. 17(E)/1993 item 5 (PDF/printed p.14, image-checked) and came into force on publication, 06-12-1993 (r.1(2), p.12). Blocked by the alleged **S.R.O. 258/2002 (AR-030, NOT_FOUND)**, which may add an Explanation to r.22: a specific unlocated instrument. |
| r.23 Summary of Evidence | 26 | **all stay PARTIAL** | 1954 text at printed p.300 (image-checked: "You are **not** obliged to say anything…"). No amendment located on 31+ instruments. Blocked by the reserved conflict **C-01**: the India Code compilation p.41 omits "not". Not resolved here. |
| r.24 Remand (SoE) | 11 | 2 EXACT kept, 9 PARTIAL | r.24 is anchored at printed p.300 and was never amended. The 9 PARTIAL items are co-cited with r.22 or r.23. |
| r.25 | 2 | PARTIAL | Whole rule **omitted** by S.R.O. 17(E)/1993 item 6 (p.14). A live citation cannot be supported. |
| r.180 CoI character | 23 | 5 → 8 EXACT, 15 PARTIAL | Printed p.341 (image-checked), no amendment located. The 15 still PARTIAL are co-cited with r.22, r.23, r.177 (C-03), r.182 (SC4-01) or r.184 (1985 instrument not an eligible copy), have an inferred identity (EV-015), or cite an annotation note (COI-021, F-02). |
| r.15 Termination (other than misconduct) | 6 | **all stay PARTIAL** (v1 had promoted 5) | 1954 p.297 and 1961 p.142 image-checked, but OQ-A-10 / GAP-15: MML 2 p.142 prints "[or Military Secretary]" and attributes it to S.R.O. 17(E)/1993, which has no r.15 item; the source is NOT_FOUND. A specific alleged, unlocated amendment naming the rule (rule 5). |
| SoE subject (all sources) | 22 | unchanged (2 EXACT) | Driven by r.23 (C-01) and r.22 (AR-030). |

## Evidence rules applied (availability ≠ authentication ≠ applicability)

An item is proposed as **EXACT_ANCHOR** only when all of the following hold:

1. Every cited provision resolves (identity `id` in the C5 crosswalk; a valid rule number or paragraph).
2. The principal text is anchored to a page of a **registered** copy whose C5 `eligible_for_exact_anchor` is `YES` (1954 Gazette `c5ef95a9`).
3. **Every** amending instrument recorded against the provision (WS-A provision_change_log, ARMY-RULES-CHAIN-01 chronology and instrument register) is itself a registered eligible copy (only AR-006 S.R.O. 205/1961, AR-029 S.R.O. 17(E)/1993 and AR-031 S.R.O. 8(E)/2003 qualify), with a page anchor verified in C12.
4. There is no reserved wording conflict (C-01 r.23, SC4-01 r.182, C-03 r.177, C-02 r.192, C-08/C-09 r.193/194).
5. There is no specific alleged, unlocated or unopened instrument naming the provision (AR-030 → r.22, AR-039 → r.95, AR-038 → r.187, text-layer-only 1960/2010 S.R.O.s → r.13, r.168). **v1.1 (F-01):** this is now also enforced from the registers themselves: every OPEN row of WS-A `open_questions.csv`, `open_questions_cycle3.csv` and `gaps_register.csv` that concerns an alleged/unlocated/unverified amendment and names a rule as `r.N` is a hard blocker for that rule, cited by its ids (WS-C open questions and the WS-A MML footnote cross-check are attached as cross-references). Rules blocked this way: **r.15** (OQ-A-10, GAP-15 — the only new effect), r.22 (GAP-02), r.23 (GAP-01, OQ-A-06), r.95 (GAP-13), r.187 (GAP-13, GAP-14; no citing items), r.193 and r.194 (OQ-A-01, OQ-A-06; no citing items). All except r.15 were already blocked by another rule, so no other state changed.
6. The rule has not been omitted.
7. **v1.1 (F-02):** the citation locator is to the rule text, not to an annotation or note ("explanatory note", "annotated", "note"): such notes are not printed in the Gazette or the amending instruments. This blocks COI-021 (new effect), COI-009 (r.177, already blocked) and EV-017 (r.23, already blocked).

Generic chain gaps are recorded on every row as "currency NOT_ESTABLISHED", the same convention C5 applied when it accepted r.180 as EXACT. They are: AR-001 E-7/1960 not found, AR-036 (nothing searched after 06-06-2022), and the unopened hints AR-012/013/015/037-046.

EXACT_ANCHOR here means an exact page anchor in a registered documented-primary copy of the version text on the instruments located so far. It does **not** authenticate the archival facsimile. It does not establish the text after the located instruments, the commencement of instruments that state none (AQ-05), or the legal applicability of the record's proposition.

For judgments, paragraph numbers are located in the text layer of the hash-verified registered copy. A paragraph is **ambiguous** when the held file contains more than one rendition and they differ. KB-026 cites para 16 of Virendra, which differs between the corrected and the original renditions in the file, so it stays PARTIAL. Jasbir (2022) has no detectable paragraph numbers, so all its items stay PARTIAL.

Army Act, AFT Act, BSA and BNSS citations stay **PARTIAL**: only India Code compilations with undocumented provenance are held. For tier A and B items, sections are located to a compilation page (`PAGE_LOCATED_IN_COMPILATION_ONLY`) as a lead, not an anchor.

## Page-level evidence

`tools/page_evidence_c12.csv` is curated input: **28 page checks** (18 from v1, 10 added in v1.1). Each row carries a text-layer probe that the tool must find on the stated page of the hash-verified held copy, or the build fails. v1.1 columns: `continues_rule` / `continues_to_pdf_page` / `continuation_probe` (page ranges, F-05; the continuation probe is validated on the continuation page), `render_script`, `checker`, `check_date`, `check_note`.

- **Reproducible renders (F-08).** Every row's `render_png_sha256` is now the sha256 of the PNG produced by `tools/render_pages_c12.py` (PyMuPDF `get_pixmap(dpi=110, colorspace=RGB, alpha=False)`, whole page, `tobytes("png")`) from the hash-verified held copy. `tools/render_pages_c12.py --verify` re-renders all 28 rows and compares (28/28 reproduce; also a test). The v1 hashes came from an unrecorded command and are kept, for the record, in `check_note`.
- **Per-page image checks of the 1954 principal pages (F-03).** Ten rows added by `C12 WS-F remediation (AI)`, each rendered and read on the image by the remediation checker: printed pp.296, 297, 301, 303, 304, 305 (rr.37-38), 306, 331, 340 and 342, with continuation pages 297, 304, 305, 306, 307, 341, 342 and 343 read as well. The ten pre-existing pages and the 1961/1993 pages were also re-rendered and re-read.
- **Prior-check references corrected (F-08).** PE-1961-141-R14 cited "R23-VERIFY-01 PIC-13"; the check is **ACQ-02/page_image_checks_acq02.csv PIC-13** (WS-A WSA-PIC-47 covers the same page). PIC-30 and PIC-31 are in ARMY-RULES-CHAIN-01/page_image_checks_chain.csv. PE-1993-17 now records item 25 in full ("In rules 134, 135 and 136 of the said rules, the words "or abstract" shall be omitted"), which is fully legible.
- **Page ranges (F-05).** The anchor is a range wherever the cited rule runs onto the next page. For every indexed 1954 rule the tool derives the end page from the text layer (the next heading's page if body text precedes it there); for every image-checked rule the curated range must agree with it or the build fails. Ranges on cited rules (`SUMMARY.json` → `page_ranges_F05`): image-checked 1954 r.14 pp.296-297, r.34 pp.303-304, r.36 pp.304-305, r.39 pp.305-306, r.41 pp.306-307, **r.179 pp.340-341**, r.183 pp.341-342, r.186 pp.342-343; **1961 r.14 pp.141-142**; 1993 r.26 (item 7) pp.14-15; text-layer only (not image-checked) 1954 r.18, 27, 32, 44, 46, 52, 56, 58, 62, 97, 107, 110, 123, 138, 142, 187.

The pages image-checked in C12: 1954 Gazette PDF pp.6, 7, 9, 10, 11, 13, 14, 15, 16, 17, 41, 50, 51, 52, 53 (printed 296-297, 299-301, 303-307, 331, 340-343); S.R.O. 17(E)/1993 pp.12, 14, 15, 17, 18, 19; S.R.O. 205/1961 printed pp.141-143.

All other 1954 rule pages come from a deterministic heading index over the text layer (longest increasing subsequence of `N. Heading.—`), marked `TEXT_LAYER_HEADING_LIS ... (text layer only; no per-page C12 image check ...)` in `page_evidence_method`. The printed page is the PDF page + 290. A rule located only by a fallback line match does not anchor unless a C12 image check confirms it; r.39 and r.43 were confirmed this way. Residual: 16 baseline EXACT items (page-anchor additions, not promotions) still rest partly on text-layer-only 1954 headings (rr.18, 28-32, 42, 44, 46-49, 56, 129-133; printed pp.297-298, 302-303, 307-310, 312-313, 330); they were outside F-03's scope and are counted in `army_rules_exact_items_by_1954_page_basis_F03`.

## Notes for the legal adviser (no conclusions drawn)

- **r.135 'or abstract' (F-09).** S.R.O. 17(E)/1993 item 25 omits "or abstract" in rr.134-136. The 1954 r.135 contains the phrase twice ("any summary or abstract of evidence given to the accused"; "such notice or abstract having been given"), while "together with an abstract of his proposed evidence" does not contain it. The scope of the omission and the effect on the "notice/abstract procedure" wording in V9-WF-10 and V9-SC-14 are left for legal determination (proposal VERSION_NOTE r.135). The anchor basis correction stands.
- **r.15B applicability (F-06).** S.R.O. 17(E)/2019 (AR-034) inserted r.15B, which disapplies rr.14, 15 and 15A for the office of the Chief of Defence Staff (WS-A r15 trace item 8). The AR-034 copy is registered `eligible_for_exact_anchor = NO`, so r.15B is not anchored. Every r.14 / r.15 / r.15A verification row carries this as `applicability_note`, with an APPLICABILITY_NOTE proposal per rule. It limits applicability, not wording, and changes no state; the citations' scope after 28-12-2019 is not claimed. (r.17 is not named by r.15B.)

## Outputs (`outputs/`)

| File | Content |
| --- | --- |
| `IMPROVEMENT_MATRIX.csv` | All 983 items, ranked. v1.1 adds `record_level_state` and `exact_scope` (F-04). Tier A = r.22, r.23, r.180, SoE; tier B = the other priority subjects; tier C = the rest. Within a tier, items are ordered by `priority_score = legal_consequence (1-5) × evidence_gap (1-4) × source_availability (1-4)`. Also gives the baseline and proposed state, change, blockers, next action and links to verification and proposals. The subject classification is a deterministic keyword and provision heuristic, not a legal characterisation. |
| `PRIORITY_VERIFICATION.csv` | 1,156 rows, one per (item, provision): provision, edition or version, copy and sha256, PDF and printed page or page range (F-05), page-evidence method, excerpt (image-read or text-layer OCR, marked as such), amendment evidence, commencement evidence, supersession chain, temporal applicability, reserved conflict, blockers, C11 judgment-link count, status, applicability note (F-06). |
| `CROSS_VOLUME_ISSUES.csv` | 13 issues across the nine families. Highlights: r.23(3) caution depends on C-01 (HIGH). r.22 records rely on 1993-only elements with the version unstated. r.182 records mix the 1993 proviso with 1954 wording absent from the 1993 Gazette (SC4-01). 26 of 42 r.180 records lack the Virendra remedy qualification. HCE-003 pairs the 1993 r.22 with a 1982 judgment that construed the 1954 text. rr.14/15/17 version chain 1954→1961→1993, now with the r.15 OQ-A-10 issue and the r.15B note. X002 lists 7 records (HCE-027 removed, F-07; it now appears in X003, which lists r.22-mentioning records that do not mention the 1993 proviso). r.25 omitted. r.177 C-03. The statutory-complaint ↔ AFT s.21/22 link is missing. The "r.23 amended 2022" claim is absent from the frozen text. |
| `CORRECTION_PROPOSALS_C12.csv` | 119 proposals, all `PROPOSED_NOT_APPLIED`, version `C12F-v1.1`: 57 promotions, 40 page-anchor additions, 2 basis corrections, 2 version notes (r.22; r.135 for the legal adviser, F-09), 3 reserved-conflict notes (r.23, r.182, r.177), 3 applicability notes (r.14, r.15, r.15A; F-06), 4 open-alleged-amendment notes (r.15, r.22, r.23, r.95; F-01), 8 cross-volume corrections. Rule-level notes now state the citing items' states instead of a fixed "PARTIAL_MATCH (unchanged)". |
| `SUMMARY.json` | Before and after counts, transitions, promotions by source and rule set, priority clusters, counts by subject and by family, per-rule units (with page span and page basis), input hashes, frozen-original verification, probe validation and honesty notes. v1.1 blocks: `open_alleged_amendment_blockers_F01`, `annotation_locator_blocked_items_F02`, `army_rules_exact_items_by_1954_page_basis_F03`, `record_scope_F04`, `page_ranges_F05`, `review_reconciliation`. |
| `OUTPUT_SHA256SUMS` | Hashes of the five outputs. |

## Running

```
VENV=/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python
$VENV tools/build_c12f.py                 # rebuild outputs
$VENV tools/build_c12f.py --check         # byte-for-byte reproduction + frozen/probe/page-range checks (exit 1 on drift)
$VENV tools/render_pages_c12.py --verify  # re-render every page-evidence row and compare PNG sha256 (F-08)
$VENV tools/render_pages_c12.py C5-SRC-P0-ARMY-RULES-1954~C1 50,51 --out /some/scratch/dir   # render pages for an image check
$VENV -m pytest -q tests                  # 27 tests (v1 invariants + F-01..F-09 remediation tests)
```

**Interpreter requirement (F-10).** The recorded outputs, render hashes and tests were produced and pass with **CPython 3.13.18,
PyMuPDF 2.1 (`VersionBind` 2.1, recorded in SUMMARY.json) and pytest 9.2.0** in the venv above (`tools/requirements_c12f.txt`).
That is the tested environment. The container's `/usr/bin/python3.11` has neither PyMuPDF nor pytest, so the tool now
stops at once with a message naming the requirement instead of failing mid-run; installing packages into the system
interpreter was not done. Another PyMuPDF/MuPDF build may change text extraction or PNG bytes; `--check` and
`--verify` will then report drift rather than pass silently. Held copies are read **read-only** from the C5 `held_paths`, which are relative to the scratchpad and overridable with `C12F_HELD_BASE`; each one is hash-verified before use. `C12F_REPO` and `C12F_C7` override the worktree and frozen-commit repository.

## Limits and next actions

- Preservation: the anchoring copies are held in the ephemeral working store only (1954 Gazette `c5ef95a9`; Parashotam), which is a C10 preservation risk. Every promotion is conditional on preserving them.
- r.22 can be promoted once S.R.O. 258/2002 is located, or confirmed not to amend r.22. r.15 needs the instrument behind "[or Military Secretary]" (OQ-A-10 / GAP-15) located or ruled out. r.23, r.182 and r.177 need the legal adviser's determination of C-01, SC4-01 and C-03.
- Registering documented-primary copies of AR-018 (r.184, 1985) and the 1960/2010 instruments (r.13, r.168) would unblock further CoI and administrative-action items.
- 289 MISSING items need source identification (149 `UNMAPPED`) or approved acquisition. Nothing was downloaded.

## Change log

| Version | Change | Finding |
| --- | --- | --- |
| C12F-v1.1 | Data-driven hard blocker from OPEN WS-A open questions / gaps naming a rule; r.15 (OQ-A-10, GAP-15) blocks 5 promotions; test fails if any r.15 item is promoted while OQ-A-10/GAP-15 is open, and if any rule with an open alleged amendment has an EXACT item | F-01 |
| C12F-v1.1 | Annotation/note locators not anchorable; COI-021 (C10Q-CW-0087) withdrawn | F-02 |
| C12F-v1.1 | 10 per-page image-check rows for the 1954 principal pages (and continuation pages); all 28 rows re-rendered with a recorded script; method field says IMAGE_CHECKED or "text layer only" per row | F-03, F-08 |
| C12F-v1.1 | `record_level_state` / `exact_scope` columns; record-scope condition on promotion proposals; judgment-on-partial-statute list in SUMMARY | F-04 |
| C12F-v1.1 | Page ranges (1954 text-layer end page checked against image rows; amendment ranges from evidence rows) | F-05 |
| C12F-v1.1 | r.15B applicability note on r.14/15/15A rows + APPLICABILITY_NOTE proposals | F-06 |
| C12F-v1.1 | HCE-027 removed from X002 / v1 P0111 (now C12F-P0113; proposal ids are sequential and shifted in v1.1) | F-07 |
| C12F-v1.1 | PIC references corrected (ACQ-02 PIC-13); PE-1993-17 item 25 recorded in full; `tools/render_pages_c12.py` | F-08 |
| C12F-v1.1 | r.135 'or abstract' scope note for the legal adviser | F-09 |
| C12F-v1.1 | Interpreter pinned (3.13.18 / PyMuPDF 2.1 / pytest 9.2.0); early environment check | F-10 |
| C12F-v1 | Initial deliverable (EXACT 105 / PARTIAL 589 / MISSING 289) | — |
