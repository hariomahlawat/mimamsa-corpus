# PILOT-01: controlled database audit pilot (completed findings for owner review)

**DATABASE ONLY. NO APPLICATION WORK.** Completed 2026-11-22 on branch `claude/gifted-bardeen-byeim6`. The PR 5 kit is merged into this branch; the PR itself is not merged.
**Status:** all output is unapproved research. **No legal advisor has been nominated, so 0 findings are advisor-reviewed and 0 are formally approved.**
**Originals:** unchanged. records_658 `9a8f0d19…`, cases_53 `8b8d53cd…` and the MML manifest re-hash identically. No source file, crawler data or earlier batch was edited.
**Corrections:** proposals only, not applied.

Contents of `PILOT-01/`:

| What | Where |
| --- | --- |
| Frozen inputs | `pilot-manifest.json`: 25 KB records, 12 MML provisions and 6 linked case rows, each with an input hash |
| Evidence register | `sources/` (205) |
| Findings | `findings/` (109 first-pass + 15 blind) |
| Reviews | `reviews/` (33) |
| Outcome per item | `record_outcomes.csv` |
| Advisor queue | `advisor_queue.csv` (32) |
| Scorecard | `scorecard.json` |
| Registers | `registers/` (list in §1) |
| Packet rules | `briefs/COMMON.md` |
| Consolidation | `build_pilot_outputs.py` |

## How it was run (bounded stages; at most 3 agents at once)

| Stage | Agents | Independence control |
| --- | --- | --- |
| 0 | Orchestrator: validator controls and tests, frozen manifest, hashed derived-text layer (local only, not committed) | — |
| 1 | manual-of-military-law-auditor ‖ independent-reviewer (**blind**, 8 records) | The blind pass ran before any first-pass finding existed and was barred from earlier research. Its files were held in `blind_staging/` and moved into the batch only after the first pass finished. |
| 2 | statutory-auditor ‖ judgment-auditor ‖ procedure-auditor | Each read primary text. None could see other agents' findings, the blind results or earlier batches. They could use MML anchors only as `mml_anchor_ids`. |
| 3 | cross-volume-auditor | Same restrictions |
| 4 | independent-reviewer A (21 findings) ‖ B (12 findings + blind comparison) | Fresh agents. Each must cite evidence it **retrieved itself**; the validator rejects SUPPORTS or DISPUTES without it. |

## 1. Source and MML cross-reference registers

**Evidence register:** 205 sources.

| Authenticity | Count |
| --- | --- |
| OFFICIAL_COMPILATION (India Code) | 89 |
| USER_SUPPLIED_REFERENCE (MML) | 78 |
| OFFICIAL_COURT_ARCHIVE (sci.gov.in / JUDIS) | 17 |
| UNCONFIRMED | 15 |
| SECONDARY | 3 |
| ORIGINAL_OFFICIAL (Gazette scans) | 3 |

The 3 Gazette scans are Act 37 of 1992 (Gazette Extraordinary No. 59, 7-9-1992), held twice, and the Tribunals Reforms Act 2026.
- **Verified:** all 56 primary sources cited by verified findings carry a pinpoint, a date and a SHA-256.
- **Verified:** 0 verified findings rely on a secondary, unconfirmed or manual source.

**MML crosswalk** (`registers/mml_crosswalk_pilot.csv`, 63 rows):
- Every row gives the file, its SHA-256, the version, and a PDF page or derived DOC line range, plus the printed page where visible.
- Each row distinguishes MANUAL_REPRODUCED_LEGAL_TEXT from MANUAL_COMMENTARY.
- **13 of 25 records have an EXACT_PASSAGE anchor:** ADM-009, CIV-008, CM-003, CM-011, CM-013, COI-008, COI-025, EV-016, HCE-004, HCE-010, HCE-017, KB-003, KB-026.
- The KB-026 anchor is borderline: it supports "Rule 180 is mandatory" but not the Virendra Kumar holding. **The strict count is 12**, which meets the 12-record target in the PR 5 docs.
- 5 records have only RELATED_PASSAGE links: CIV-033, CM-025, KB-028, CIV-034, V9-CL-02.
- 7 have NO_MML_COVERAGE: EV-002, CIV-019, AFT-004, AFT-011, PEN-043, PEN-J-01, COI-039. Their subjects post-date or fall outside the manuals.
- No link was forced.

Supporting registers:
- `mml_version_diffs.csv`: 38 rows. For example, the AR .doc copies lack the r.22 Explanation added in 2002; r.180 reads "or/and" in different copies; the vol 2(AA) PDF prints "in adding arrest" for "evading arrest" (verified by me).
- `mml_edition_notes.csv`: **no edition, printing date or access marking was found in any of the 8 files.** "CONFIDENTIAL" appears only as a form label.
- `source_code_resolution.csv`: 78 internal citation codes. 57 have a proposed identity (29 high, 19 medium, 9 low confidence); 21 cannot be resolved. Three different codes refer to Virendra Kumar.
- `volume_mapping_verification.csv`: **Volumes II (COI), IV (CM), VI (PEN), VII (AFT), VIII (CIV) and IX (EV) are verified** from record text or ID prefixes. **Volumes I, III and V are not evidenced anywhere in the 658 records.** The rev1 nine-family inference is therefore not authoritative.
- `amendment_source_gaps.csv`: 19 required amending or commencement instruments. 2 are held (Finance Act 2017, Tribunals Reforms Acts) and Act 37 of 1992 was located during the pilot; the rest are not held.

## 2. Findings: all 25 records and the 12-provision MML packet

Every one of the 43 manifest items has an explicit outcome (`record_outcomes.csv`; the validator enforces this). The worst outcome per KB record:

| Outcome | KB records |
| --- | --- |
| DISCREPANCY (proposal) | 12: HCE-017, CM-025, HCE-004, CM-011, ADM-009, KB-026, KB-028, KB-003, CIV-008, AFT-004, V9-CL-02, COI-039 |
| CONFLICTING_SOURCES | 4: HCE-010, EV-016 (r.23(3)); COI-008 (r.177(1)-(2) compilation vs MML); CIV-034 (Army Act s.133 vs BSA, now proposed P2) |
| UNVERIFIED | 5: AFT-011, PEN-043, CIV-019, PEN-J-01, CM-003 |
| BLOCKED | 1: CIV-033 (1978 Adjustment Rules not obtainable) |
| NO_ISSUE_FOUND (only) | 3: CM-013, EV-002, COI-025 |

- **MML packet, worst outcome:** 1 CONFLICTING (r.23(3)), 4 BLOCKED (amending S.R.O.s for r.22, 25, 180 and 182 not held), 6 DISCREPANCY (outdated or incorrect manual notes), 1 NO_ISSUE_FOUND (ss.109–111).
- **Case rows:** 5 DISCREPANCY and 1 UNVERIFIED (Navjot Sandhu).
- **First-pass totals (109):**
  - By outcome: 44 NO_ISSUE_FOUND, 34 DISCREPANCY, 19 UNVERIFIED, 7 CONFLICTING, 5 BLOCKED.
  - By severity: P0 5, P1 25, P2 31, P3 48.

## 3. Independent review

- **Blind pass** (8 records, 15 findings), compared on 27 issues (`blind_vs_firstpass.csv`): 14 AGREE, 8 FIRSTPASS_ONLY, 2 BLIND_ONLY, 3 DISAGREE.
  - Issues found by both passes include the CM-011 s.122(1)/s.123(2) error and the HCE-017 s.81(4) "was an NCO" limb.
  - **Caveat:** both passes used the same model family and byte-identical sources, so agreement is weak corroboration.
- **Adversarial reviews:** 33 reviews covering **all 31 P0/P1/conflict findings** and both controls. Result: 26 SUPPORTS, 6 DISPUTES, 1 RETURN_FOR_EVIDENCE.

Material changes proposed by the reviewers (each still subject to the advisor):

| Finding | Record | First pass | Reviewer result |
| --- | --- | --- | --- |
| F-XVOL-001 / 002 | EV-016 | P0 conflict | **DISPUTES → P2.** EV-016 is neutral on the disputed word; P0 double-counted HCE-010's conflict. |
| F-XVOL-007 | CIV-034 | P1 CONFLICTING | **DISPUTES → P2.** General Clauses Act s.8(1) offers a way to read Army Act s.133 as pointing to the BSA; whether it applies is for the advisor. |
| F-JUD-014 | COI-039 (control) | P3 DISCREPANCY | **DISPUTES: false positive.** It is an improvement proposal, not an error. |
| F-PROC-006 | CM-011 | P1 | **DISPUTES → P2.** A paraphrase ambiguity, not a misstatement. The s.123(2) omission (F-PROC-007) is upheld. |
| F-MML-019 | MMLPKT-10 | P1 | **DISPUTES: re-scope.** The vol 2(AA) s.121 note matches s.121; MML 2's note overstates it. |
| F-STAT-006 | HCE-017 | P1 | **RETURN_FOR_EVIDENCE.** The MML copies print a r.192 proviso (SRO 215/1965) that the India Code compilation leaves out. Record r.192 as CONFLICTING. |
| F-PROC-019 | HCE-017 | P1 | **SUPPORTS, raise to P0.** The narrowed s.81(4) bar on NCOs risks an illegal punishment. |
| F-JUD-005 / 007 / 021 | PEN-043, PEN-J-01, Dharamvir row | P1 UNVERIFIED | **SUPPORTS.** The official 2026 INSC 993 PDF (hash-matched) confirms Isaac does not overrule Dharamvir. "Cannot be mechanically applied" is the Attorney General's submission. Proposed edge: "cites" plus a proposition-level "limits" note. |
| F-STAT-013, F-STAT-018, F-STAT-022, F-MML-002, F-MML-017, F-XVOL-009 | various | P1 | SUPPORTS, recommend P2 |

After review the profile shifts from 5 P0 / 25 P1 toward 4 P0 / 16 P1 (proposed, not applied). The two EV-016 P0s come down and F-PROC-019 goes up; eight P1s come down.

## 4. Legal-advisor decision queue

`advisor_queue.csv` lists 32 findings, P0 first, each with the agents' questions and the reviewer decisions. The advisor has not been nominated. The decisions that matter most:
1. **r.23(3)** (HCE-010, MMLPKT-02): interim database flag. The custodian request is drafted, `registers/RULE23_3_CUSTODIAN_REQUEST_DRAFT.md`, and **not sent**. Reviewer A confirmed from the page image that the compilation's printed page itself lacks "not".
2. HCE-017: the s.81(4) NCO bar (proposed P0) and the r.192 proviso conflict.
3. CM-011: the s.123(2) omission.
4. Army Act s.133 and the BSA, via General Clauses Act s.8 (CIV-034, CM-025, CIV-019).
5. The Isaac 2026 treatment edges for Dharamvir and Rajbir.
6. CIV-008: AR r.197A, the officer who chooses the forum.
7. AFT s.3(o)(iii)–(iv) coverage across 5 AFT records.
8. AFT-011: AFT Act s.22(1)(b), which gives no filing period.
9. COI-008: which r.177(1)-(2) text is current (SRO 8(E) 2003).
10. Parashotam Dass para 32 on Shri Kant Sharma.

`registers/unresolved_questions_register.csv` holds the full list of advisor questions.

## 5. Missing subjects and missing authority

- **Missing records** (`registers/missing_records_register.csv`, 16 gaps):
  - The rev2 gaps GAP-01…12 are carried forward with pilot evidence.
  - New: GAP-13 ISO Act 2023 and Rules 2025 (now in scope); GAP-14 the 1978 Adjustment Rules (BLOCKED); GAP-15 Army Rules Appendix III and rule-level records; GAP-16 the Entitlement Rules 1982/2008/2023.
  - Agniveer (GAP-11) is confirmed in scope; there are 0 records and no source.
  - **Not every uncited Act section or Rule needs a record.** The register separates statutory coverage (section records the crawler can supply) from curated explanatory notes. GAP-01 offences, GAP-02 trial procedure and GAP-04 sentences need an owner or advisor decision on curated coverage.
- **Missing authority** (`amendment_source_gaps.csv`): none of the Army Rules amending S.R.O.s (1954–2022) is held, and egazette.gov.in is unreachable from this container.
  - Located during the pilot: Act 37 of 1992 (India Code Gazette scan), and the Tribunals Reforms Act 2026, which amends only AFT Act s.9A.
  - A Rajya Sabha record shows the 1978 Adjustment Rules were amended by S.O. 4010 (6-12-1986).
- **AFT judgments:** still 0. aftdelhi.nic.in timed out again; this is a verified gap.
- **Missing relationships** (`missing_relationships_register.csv`, REL-01…14):
  - 0 KB→MML citations in the originals.
  - 0 KB→corpus doc_id links.
  - 5 duplicate pairs among the records compared.
  - The s.3(o) gap across AFT records.
  - The Isaac→Dharamvir/Rajbir edge, pending.
  - The Parashotam→Shri Kant Sharma edge.
  - Act 37/1992 now linkable to the MML provisions.

## 6. Technical validation results and scorecard

- `validate.py --batch PILOT-01 --manifest pilot-manifest.json --strict` → **exit 0, 0 errors** (205 sources / 124 findings / 33 reviews).
- `validate.py --schema-check` passes. `unittest test_legal_audit_validator test_legal_audit_controls` → **23 tests OK**.

New controls, each with a passing and a failing test:

| Control | What it enforces |
| --- | --- |
| Record and input-hash integrity | `record_id` must be in the manifest and its hash must match |
| Coverage | Every manifest item needs an examination outcome |
| Pinpoint and date traceability | Verified or conflicting findings need pinpoints and effective or decision dates |
| Independent reviewer evidence | SUPPORTS or DISPUTES must cite a pinpointed source the reviewer retrieved, not one from the first pass; independent agents can never accept or approve |
| MML provenance | Must name one of the 8 files; SHA must equal the manifest; page or line pinpoint; content_role; no official authenticity |
| Manual-only block | Applies to every legal workstream |
| State separation | Outcome, verification and legal-review states cannot contradict; ADVISOR_REVIEWED needs an advisor record |

**Scorecard** (`scorecard.json`; process and coverage measures, **not a legal-accuracy percentage**, because there is no advisor-adjudicated reference set):

| Metric | Result |
| --- | --- |
| Items with explicit outcome | 43/43 (100%) |
| P0/P1/conflict findings independently reviewed | 31/31 (100%) |
| Reviewer dispute rate on those | 5/31 = 16% |
| Blind vs first-pass agreement | 14/27 AGREE; 8 first-pass-only, 2 blind-only, 3 disagree |
| Verified findings with pinpointed, hashed primary source | 64/64 |
| Manual-only verifications | 0 |
| KB records with exact MML anchor | 13 (strict 12)/25 |
| KB citation codes resolvable | 57/78 proposed (73%); **below the 90% threshold** |
| Controls: P0/P1 false positives | 0 (1 P3 false positive on COI-039) |
| Originals changed | 0 |
| Advisor-reviewed / formally approved | 0 / 0 |

Hard NO-GO checks:
- No invented source was found to have survived. This is limited to what the reviewers re-retrieved.
- No original changed.
- The validator is clean.
- No P0 is shown as resolved.
- No verified finding lacks a pinpoint or SHA.
- **All hard checks pass.**

Limitations found:
- **Reviewer identity is coarse.** The validator recognises one `retrieved_by="independent-reviewer"` identity, so it cannot tell the blind reviewer and reviewers A and B apart.
- **Unstable Gazette scan hashes.** India Code serves the Act 37/1992 scan with a different SHA-256 on each download (the text is identical), so hash identity needs a stable fingerprint for those scans.
- **A source the first pass missed.** The judgment auditor did not find the official Isaac and Navjot PDFs that were already archived on HF. Future packets must be given the archive register.
- **No page-image checks in the first pass.** Only reviewer A rendered page images. This matters for negations such as r.23(3).
- **The derived MML text is local only** (owner instruction), so the MML findings cannot be reproduced from the repository alone.
- **Same model family** throughout.
- **The full `tests/` suite still has 5 import errors** (pymupdf and others not installed; unrelated to this audit).

## 7. Proposed database corrections (not applied)

`registers/corrections_register.csv` lists every DISCREPANCY or CONFLICTING finding with its proposed wording, independent-review result and legal-review state. The status column is `PROPOSAL_NOT_APPLIED`. No record, case row, MML file or corpus file was modified.

Research-layer corrections carried from rev2:
- COR-001: the MML 2.pdf component label
- COR-002: duplicate-overlap figures
- COR-003: DATA_AUTHORITY.md is stale
- COR-004: the rev1 corpus count

## 8. Is the methodology reliable enough to scale to all 658?

**Recommendation: not yet. NO-GO for the full 658 now; GO for a short calibration step first.**

What worked:
- Bounded staging and frozen hashes.
- Blind-first independence.
- Reviewers re-retrieving the evidence themselves, which caught over-calling (2 P0s downgraded), a false positive on a control, a mis-scoped MML finding, and a proposed severity increase (s.81(4)).
- Validator controls that stopped manual-only or unpinpointed verification.
- 100% coverage with explicit outcomes.

What blocks scaling:
1. **No advisor-adjudicated reference set**, so error rates cannot be measured. PILOT_AND_ACCEPTANCE.md requires this before scaling, and the advisor is not nominated.
2. **Systemic evidence gaps** (Gazette S.R.O.s, the 1978 Rules, Entitlement Rules, AFT judgments) would make roughly 20–30% of findings BLOCKED or UNVERIFIED at scale. Scaling will not fix this; acquisition or an authorised egazette route will.
3. **Single-pass recall is uncertain.** The blind pass missed 8 issues the first pass found, and the first pass missed 2 the blind pass found. P0 domains therefore need two passes.
4. **Calibration:** cross-volume severities ran high, and the 73% citation-code resolution is below threshold.

Proposed next step (needs your approval):
- (a) Nominate the advisor and adjudicate the 32 queued items to create the reference set.
- (b) Fix the process: per-reviewer identity in the validator; give packets the archive register; mandatory page-image checks for negations, numbers and dates; a stable fingerprint for Gazette scans.
- (c) Authorise source acquisition (egazette access from another network, or the custodian request).
- (d) Then run one further calibration batch (about 50 records, one complete volume such as Vol II COI) with fixed thresholds, before deciding on the full 658.

**Stopping here for your review. DATABASE ONLY. NO APPLICATION WORK.**
