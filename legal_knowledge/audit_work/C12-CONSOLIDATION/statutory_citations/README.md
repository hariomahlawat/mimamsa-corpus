# C12 Workstream F: statutory citation improvement (983 frozen citation items)

**Status: research proposal, version `C12F-v1`. Nothing has been applied.** The frozen originals
(`records_658.jsonl` sha256 `9a8f0d19…`, `cases_53.jsonl` `8b8d53cd…`) are unchanged. The tool checks them on every
run, against the worktree and against `git show 21e73b83:` in `/home/user/c7`. `corpus_crosswalk.csv`, the C10
outputs and the KB records are also unchanged. Every evidence-state change below is a **proposal** in
`outputs/CORRECTION_PROPOSALS_C12.csv`.

## Result (honest before / after)

| Evidence state | Baseline (C5/C10) | C12 proposed | Change |
| --- | ---: | ---: | ---: |
| EXACT_ANCHOR | 42 | 105 | +63 |
| PARTIAL_MATCH | 652 | 589 | −63 |
| MISSING_EVIDENCE | 289 | 289 | 0 |

- **63 promotions (PARTIAL → EXACT), all proposed only.** 43 Army Rules items: rr.14, 15, 16, 17, 26, 33, 36, 37, 134, 179 and 186, and items that combine them with rules already anchored. 17 Virendra Kumar (2020) items and 3 Parashotam Dass (2023) items, each with explicit paragraph locators.
- **The 42 baseline EXACT items are all kept, and each now has a page anchor.** Two of them (r.135: V9-WF-10, V9-SC-14) get a **basis correction**: the C5 parser read only the first number of "rr.134,135,136", so it missed the S.R.O. 17(E)/1993 item 25 amendment. They stay EXACT only because that amending Gazette is itself a registered eligible copy with an image-checked page (1993 p.17).
- **No MISSING_EVIDENCE item is promoted.** No demotion was needed.

### The priority clusters

| Cluster | Army Rules items | Outcome | Why |
| --- | ---: | --- | --- |
| r.22 Hearing of charge | 29 | **all stay PARTIAL** | 1954 text: Gazette PDF p.9, printed p.299 (C12 image check). r.22 was substituted by S.R.O. 17(E)/1993 item 5 (PDF/printed p.14, image-checked) and came into force on publication, 06-12-1993 (r.1(2), p.12). Blocked by the alleged **S.R.O. 258/2002 (AR-030, NOT_FOUND)**, which may add an Explanation to r.22: a specific unlocated instrument. |
| r.23 Summary of Evidence | 26 | **all stay PARTIAL** | 1954 text at printed p.300 (image-checked: "You are **not** obliged to say anything…"). No amendment located on 31+ instruments. Blocked by the reserved conflict **C-01**: the India Code compilation p.41 omits "not". Not resolved here. |
| r.24 Remand (SoE) | 11 | 2 EXACT kept, 9 PARTIAL | r.24 is anchored at printed p.300 and was never amended. The 9 PARTIAL items are co-cited with r.22 or r.23. |
| r.25 | 2 | PARTIAL | Whole rule **omitted** by S.R.O. 17(E)/1993 item 6 (p.14). A live citation cannot be supported. |
| r.180 CoI character | 23 | 5 → 9 EXACT, 14 PARTIAL | Printed p.341 (image-checked), no amendment located. The 14 still PARTIAL are co-cited with r.22, r.23, r.177 (C-03), r.182 (SC4-01) or r.184 (1985 instrument not an eligible copy), or have an inferred identity (EV-015). |
| SoE subject (all sources) | 22 | unchanged (2 EXACT) | Driven by r.23 (C-01) and r.22 (AR-030). |

## Evidence rules applied (availability ≠ authentication ≠ applicability)

An item is proposed as **EXACT_ANCHOR** only when all of the following hold:

1. Every cited provision resolves (identity `id` in the C5 crosswalk; a valid rule number or paragraph).
2. The principal text is anchored to a page of a **registered** copy whose C5 `eligible_for_exact_anchor` is `YES` (1954 Gazette `c5ef95a9`).
3. **Every** amending instrument recorded against the provision (WS-A provision_change_log, ARMY-RULES-CHAIN-01 chronology and instrument register) is itself a registered eligible copy (only AR-006 S.R.O. 205/1961, AR-029 S.R.O. 17(E)/1993 and AR-031 S.R.O. 8(E)/2003 qualify), with a page anchor verified in C12.
4. There is no reserved wording conflict (C-01 r.23, SC4-01 r.182, C-03 r.177, C-02 r.192, C-08/C-09 r.193/194).
5. There is no specific alleged, unlocated or unopened instrument naming the provision (AR-030 → r.22, AR-039 → r.95, AR-038 → r.187, text-layer-only 1960/2010 S.R.O.s → r.13, r.168).
6. The rule has not been omitted.

Generic chain gaps are recorded on every row as "currency NOT_ESTABLISHED", the same convention C5 applied when it accepted r.180 as EXACT. They are: AR-001 E-7/1960 not found, AR-036 (nothing searched after 06-06-2022), and the unopened hints AR-012/013/015/037-046.

EXACT_ANCHOR here means an exact page anchor in a registered documented-primary copy of the version text on the instruments located so far. It does **not** authenticate the archival facsimile. It does not establish the text after the located instruments, the commencement of instruments that state none (AQ-05), or the legal applicability of the record's proposition.

For judgments, paragraph numbers are located in the text layer of the hash-verified registered copy. A paragraph is **ambiguous** when the held file contains more than one rendition and they differ. KB-026 cites para 16 of Virendra, which differs between the corrected and the original renditions in the file, so it stays PARTIAL. Jasbir (2022) has no detectable paragraph numbers, so all its items stay PARTIAL.

Army Act, AFT Act, BSA and BNSS citations stay **PARTIAL**: only India Code compilations with undocumented provenance are held. For tier A and B items, sections are located to a compilation page (`PAGE_LOCATED_IN_COMPILATION_ONLY`) as a lead, not an anchor.

## Page-level evidence

`tools/page_evidence_c12.csv` is curated input: 18 page checks. 16 were image-read in C12 (renders at 110 dpi; PNG sha256 recorded) and 2 rely on prior PIC image checks. Each row carries a text-layer probe that the tool must find on the stated page of the hash-verified held copy, or the build fails. The pages:

- 1954 Gazette: PDF pp.9, 10, 15, 17, 51 (printed pp.299, 300, 305, 307, 341)
- S.R.O. 17(E)/1993: pp.12, 14, 15, 17, 18, 19
- S.R.O. 205/1961: printed pp.141-143

All other 1954 rule pages come from a deterministic heading index over the text layer (longest increasing subsequence of `N. Heading.—`). The printed page is the PDF page + 290, an offset image-verified on three pages. A rule located only by a fallback line match does not anchor unless a C12 image check confirms it; r.39 and r.43 were confirmed this way.

## Outputs (`outputs/`)

| File | Content |
| --- | --- |
| `IMPROVEMENT_MATRIX.csv` | All 983 items, ranked. Tier A = r.22, r.23, r.180, SoE; tier B = the other priority subjects; tier C = the rest. Within a tier, items are ordered by `priority_score = legal_consequence (1-5) × evidence_gap (1-4) × source_availability (1-4)`. Also gives the baseline and proposed state, change, blockers, next action and links to verification and proposals. The subject classification is a deterministic keyword and provision heuristic, not a legal characterisation. |
| `PRIORITY_VERIFICATION.csv` | 1,156 rows, one per (item, provision): provision, edition or version, copy and sha256, PDF and printed page, page-evidence method, excerpt (image-read or text-layer OCR, marked as such), amendment evidence, commencement evidence, supersession chain, temporal applicability, reserved conflict, blockers, C11 judgment-link count, status. |
| `CROSS_VOLUME_ISSUES.csv` | 13 issues across the nine families. Highlights: r.23(3) caution depends on C-01 (HIGH). r.22 records rely on 1993-only elements with the version unstated. r.182 records mix the 1993 proviso with 1954 wording absent from the 1993 Gazette (SC4-01). 26 of 42 r.180 records lack the Virendra remedy qualification. HCE-003 pairs the 1993 r.22 with a 1982 judgment that construed the 1954 text. rr.14/15/17 version chain 1954→1961→1993. r.25 omitted. r.177 C-03. The statutory-complaint ↔ AFT s.21/22 link is missing. The "r.23 amended 2022" claim is absent from the frozen text. |
| `CORRECTION_PROPOSALS_C12.csv` | 117 proposals, all `PROPOSED_NOT_APPLIED`: 63 promotions, 40 page-anchor additions, 2 basis corrections, 4 rule-level version or reserved-conflict notes, 8 cross-volume corrections. |
| `SUMMARY.json` | Before and after counts, transitions, promotions by source and rule set, priority clusters, counts by subject and by family, per-rule units, input hashes, frozen-original verification, probe validation and honesty notes. |
| `OUTPUT_SHA256SUMS` | Hashes of the five outputs. |

## Running

```
VENV=/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python
$VENV tools/build_c12f.py          # rebuild outputs
$VENV tools/build_c12f.py --check  # byte-for-byte reproduction + frozen/probe checks (exit 1 on drift)
$VENV -m pytest -q tests           # 13 tests (invariants: no MISSING promoted; every EXACT has eligible copies + pages; r.22/r.23/r.177/r.182 never promoted; …)
```

Environment: Python 3.11+ (3.13 used) and PyMuPDF (`pymupdf`; the version is recorded in SUMMARY.json because text extraction is version-sensitive). Held copies are read **read-only** from the C5 `held_paths`, which are relative to the scratchpad and overridable with `C12F_HELD_BASE`; each one is hash-verified before use. `C12F_REPO` and `C12F_C7` override the worktree and frozen-commit repository.

## Limits and next actions

- Preservation: the anchoring copies are held in the ephemeral working store only (1954 Gazette `c5ef95a9`; Parashotam), which is a C10 preservation risk. Every promotion is conditional on preserving them.
- r.22 can be promoted once S.R.O. 258/2002 is located, or confirmed not to amend r.22. r.23, r.182 and r.177 need the legal adviser's determination of C-01, SC4-01 and C-03.
- Registering documented-primary copies of AR-018 (r.184, 1985) and the 1960/2010 instruments (r.13, r.168) would unblock further CoI and administrative-action items.
- 289 MISSING items need source identification (149 `UNMAPPED`) or approved acquisition. Nothing was downloaded.
