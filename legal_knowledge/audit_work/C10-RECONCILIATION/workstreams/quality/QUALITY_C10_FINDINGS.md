# C10 workstream D: corpus quality after the unified reconciliation

Database research only. Nothing here changes a record, a register, an anchor, a holding state or a legal status. Every proposal is `PROPOSAL_NOT_APPLIED`. Having a copy available is not the same as having it authenticated, and availability never upgrades a citation anchor.

## Inputs (pinned)
- Staging `21e73b83`: the SOURCE-LIBRARY-C5 crosswalk, which is byte-identical to the AUTH-LEDGER effective v0000 crosswalk; the v0000 copy, master and state registers; `records_658.jsonl` and `cases_53.jsonl`, read only (sha256 values in `outputs/QUALITY_C10_MANIFEST.json`); and the finding registers listed under task 3.
- PR #41 head `cfc52d57`: the C9 CORRECTIONS package (23 findings, 40 proposals, `record_impact.csv`) and C9 STATUTORY `instrument_records.csv`.
- Raw-data `ad77758d`: used only to re-hash the GitHub copies named in the curated candidate tables. Every copy gave `GH_REHASHED_MATCH`.
- C10 reconciliation outputs. Their bytes are copied into `inputs/c10_outputs_snapshot/` and pinned by SHA-256, because the live `../../outputs/` folder was regenerated during this work (23:22 UTC). At build time the live files matched the snapshot.

## 1. Baseline reproduced exactly (stop condition not triggered)
| metric | expected | recomputed |
|---|---|---|
| KB crosswalk rows | 1,060 | 1,060 |
| citation items (`CITES`) | 983 | 983 |
| EXACT_ANCHOR / PARTIAL_MATCH / MISSING_EVIDENCE | 42 / 652 / 289 | 42 / 652 / 289 |
| NO_CITATION placeholder rows (all MISSING_EVIDENCE) | 77 | 77 |
| KB records / case records | 658 / 53 | 658 / 53 |
| exact anchors on `C5-SRC-P0-ARMY-RULES-1954~C1` (c5ef95a9) | 42 | 42 |
| ledger `coverage_summary.json` (366 = 289 + 77) | 42 / 652 / 366 | 42 / 652 / 366 |

The builder exits with code 2 if any of these values fails to reproduce.

## 2. Coverage by dimension (983 citation items)
**C: Citation resolution.** No change: 42 / 652 / 289. No anchor was upgraded because a copy turned out to be available.

**B: Source authentication.** No change. The ledger v0000 holding states are: HELD_GOVERNMENT_COMPILATION 393, HELD_PRIMARY_GAZETTE_FACSIMILE 204, HELD_PRIMARY_OFFICIAL_COURT_COPY 74, HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED 23, NOT_HELD_* 140, and no source (UNMAPPED) 149. All 4,103 inventory rows carry `NOT_AUTHENTICATED_BY_THIS_RECONCILIATION`. The anchor copy behind all 42 anchors (`~C1`) remains `EFFECTIVE_PRIMARY_VERIFIED`, as in the ledger.

**A: Source availability.** The baseline did not say where a copy was stored. C10 now does:
| C10 availability | items | resolution |
|---|---|---|
| HELD_HF_AND_GITHUB (Army Act and AFT Act compilations, BNSS, BSA) | 393 | all PARTIAL |
| HELD_HF_ONLY, HF bytes NOT_CHECKED (Virendra Kumar, P S Gill) | 27 | all PARTIAL |
| HELD_WORKING_STORE_ONLY (ephemeral) | 274 | 42 EXACT, 232 PARTIAL |
| NOT_REGISTERED but an unregistered copy is in the canonical store (AFT Procedure/Practice Rules 46; BNS India Code compilation 12) | 58 | MISSING |
| NOT_HELD, related material only, in the working store (ER/GMO 2023 letter 3; CCCM papers-laid record 8; RA 1987 Ch. V extract 4) | 15 | MISSING |
| NOT_HELD in any store (Army Orders 10, DESW FAQ 18, PRA 2008 34, ISO 4, Sanhita commencement 1) | 67 | MISSING |
| SOURCE_NOT_IDENTIFIED (UNMAPPED) | 149 | MISSING |

The 58 items do not move out of MISSING_EVIDENCE. C9 STATUTORY had already identified these copies in the raw store (`HELD_CORPUS_RAW_UNREGISTERED`). C10 adds that they are in both HF and GitHub.

**D: Legal applicability.** Not determined for any of the 983 items. Existing flags were copied, not assessed: C9 `record_impact` on 66 items, open PILOT-01 P0-P2 findings on 26, open WS-B adverse items on 45, C8 cross-reference findings on 64. KB status is unchanged.

**Case rows (53).** EXACT 6, PARTIAL 7, MISSING 40, unchanged. Of the 40 MISSING rows, 29 have a candidate rendition in the canonical store. For 27 of these, a third-party Supreme Court Reports (SCR) mirror is held in HF and GitHub; for the other 2 (A11 Ram Sarup and L04 Mani Ram Bhaira), the copy is in HF only. All 29 were already recorded in WS-B or v3.3 registers. None of them is an official copy, so the rows stay MISSING. Five title-search hits were checked against the caption and rejected (`case_coverage_c10.csv#A_rejected_title_hit`); one of them is the claimed 12-10-2026 Girish clarification, for which there is no October 2026 item.

## 3. Preservation risk (copies held only in the ephemeral C5 working store)
- 48 registered copies are working-store-only. 13 of the sources cited by the KB have every copy in the working store.
- **274 of the 983 citation items (27.9%) depend on these copies:** 204 cite the Army Rules 1954 Gazette and 70 cite 12 Supreme Court judgments.
- **All 42 exact anchors** sit on c5ef95a9 (Army Rules 1954, S.R.O. 484 Gazette facsimile), which is only in `downloads/discovery/` and `downloads/independent-reviewer-D/`.
- The India Code Army Rules compilation (48f52219, held in HF and GitHub) is a different source. It cannot stand in for the as-notified anchors.
- **KB records:** 252 of 658 have at least one item at risk, and 93 have every citation item at risk. All 40 records that carry an exact anchor (10 with every item exact, 30 with some) depend entirely on c5ef95a9 for those anchors.
- **Case anchors:** 5 of the 6 rest on working-store-only copies (Bedi, Jasbir, Parashotam, Anvar, Arjun). The sixth, Virendra, is in HF only with bytes NOT_CHECKED.
- **Partial mitigation:** 35 of the 70 judgment items (Bedi, Ranjit Thakur, Mukherjee, Dharamvir, Rajbir, N S Yadav, Parashotam, Girish) have an SCR rendition in HF and GitHub. These renditions have different bytes and different pages, so they preserve the text, not the anchors or PDF-page pinpoints. Jasbir, Anvar, Arjun and Mullikote have no alternate copy anywhere.
- **Findings at risk:** 14 of 23 C9 findings, 28 of 40 C9 proposals and 40 of the 204 open register items rely on at least one working-store-only copy. Among these, c5ef95a9 is cited by C9-F-B01/B02 (P0/P2) and 7 proposals; Girish 4f7ea3a4, Mullikote 10e1954f and Parashotam fe19875b carry Matters A and E.
- The fix is already stated in the C10 `MISSING_SOURCE_EVIDENCE.csv` ("owner to place the registered bytes in the canonical HF dataset"). It is not repeated here as a new proposal.

Per-copy figures are in `outputs/preservation_risk_c10.csv`. The 3 Rajbir copies each show the source's items, so add up the totals from the citation file, not from that table.

## 4. Finding and proposal status (267 rows in `finding_status_c10.csv`)
Scope:
- C9: 23 findings and 40 proposals, at any priority.
- Open P0-P2 rows at staging:
  - PILOT-01 corrections: 42
  - C8 cross-reference: 8
  - C8 proposals: 3
  - WS-B adverse queue: 23
  - WS-B pending acquisition: 55
  - WS-A gaps: 13
  - WS-C candidate corrections: 13
  - CALIBRATION-02 proposals: 47

**The unified inventory changes the evidence status of none of the findings.** The outcomes are:
| outcome | C9 findings | C9 proposals | register items |
|---|---|---|---|
| NO_CHANGE_PRESERVATION_RISK | 13 | 21 | 35 |
| NO_CHANGE_AVAILABILITY_CONFIRMED_IN_CANONICAL_STORE | 7 | 9 | 46 |
| NO_CHANGE_CANDIDATE_ALREADY_RECORDED_ELSEWHERE_NOW_IN_CANONICAL_STORE | 1 | 7 | 9 |
| NO_CHANGE_HF_ONLY_BYTES_NOT_CHECKED | 0 | 0 | 15 |
| NO_CHANGE_NO_HELD_DOCUMENT_IDENTIFIED | 2 | 3 | 99 |
| CHANGED_CANDIDATE_COPY_NOT_PREVIOUSLY_RECORDED | 0 | 0 | 0 |

Each row lists the specific inventory rows (full sha256 plus where it is held).

Notes on particular items:
- **C9-F-A04 (Girish clarification, P1).** Still unsupported: there is no October 2026 item in HF, GitHub or the working store.
- **C9-F-E06 and C9-CP-E10 (S P Rathore).** The mirror 2f89730f is now confirmed in HF and GitHub, but an official copy is still not held.
- **C9-F-A03 and C9-CP-A05 (Tarsem).** The SCR copy f8a14181 was already cited in C9 and is in HF and GitHub. The official copy is still not held.
- **C9-F-E02 and C9-CP-E04 (Shri Kant Sharma).** An SCR copy (86de3643, C.A. 7400/2013, 11-03-2015) is in HF and GitHub and already recorded in WS-B. It does not affect the relation-type question, which rests on Parashotam.
- **Reviewer disagreements are kept as recorded:** C9-F-D01 (P2, disputed; P1 at first pass), F-XVOL-001, F-XVOL-002, F-XVOL-007 (reviewer B disputes), and F-PROC-006 and F-MML-019 (reviewer A disputes).

## 5. Versioned proposals (`proposals_c10.csv`, 12 rows, all PROPOSAL_NOT_APPLIED)
Each proposal targets a register only. Current text is quoted verbatim and nothing is overwritten. Any change must go through an AUTH-LEDGER transition, or an overlay for WS-B.
- **C10-QP-01, `C5-SRC-P1-AFT-PROC-RULES`** (now `NOT_HELD_NOT_CHECKED`; cited by 46 items). Record the C9-identified copies 590cf7cd (S.R.O. 26(E) 2008), fc27032f (S.R.O. 05(E) 2011) and c57b113a (S.R.O. 6(E) 2009) as candidate copies. The holding state does not change.
- **C10-QP-02, `C5-SRC-P1-BNS-2023`** (12 items). Leave the Gazette source NOT_HELD. Register a separate India Code compilation source with d4449e99, following the BNSS/BSA pattern. d163e785 (same title, 40.9 MB) is a Hindi text in Gazette pagination and is not proposed (C10 review WS-03).
- **C10-QP-03 to QP-10, eight judgment sources whose copies are all in the working store.** Append an SCR rendition candidate copy row with `eligible_for_exact_anchor NO` and no page equivalence. This preserves the text only; the registered bytes still need to be placed in HF.
- **C10-QP-11 and QP-12, WS-B PQ-C3-39 (Ram Sarup) and PQ-C3-40 (Mani Ram Bhaira).** Replace "reportedly archived on the HF dataset" with a note that the C10 HF listing shows the file and that its hash is declared only by the sidecar (bytes NOT_CHECKED). The acquisition stays open.

No record-level (KB or case text) correction is newly supported by a held document. The C9 proposals therefore stand unchanged and none is superseded.

## Limitations
- HF bytes are NOT_CHECKED. For HF-only items there is only the listing and the sidecar or manifest declaration.
- Candidate identities come from first-page captions extracted with pdftotext and read by an AI agent. No human has confirmed them. The provenance of the S3 SCR mirror is undocumented. N S Yadav: the army number differs between copies (14666828M in the working copy, 1466828M in the SCR copy).
- Detection in the finding rows relies on SHA-256 values or prefixes, C5 source ids, cases_53 ids and a short list of name keywords. Rows that cite a source only by description (for example "compilation p.35" without a hash) are reported as NO_HELD_DOCUMENT_IDENTIFIED. Some PILOT-01 rows that rest on held compilations are therefore under-counted as "availability confirmed".
- Not covered:
  - CALIBRATION-02 individual reviewer findings (about 1,540 rows), covered here only through the 47 consolidated proposals;
  - the SOURCE-LIBRARY-C5 conflict register, which has no priority field and whose C-01 entry is carried by C9-F-B01;
  - registers that only rank acquisitions.
- No legal applicability was assessed.

## Files
- `tools/build_quality_c10.py`. Run `--repo <checkout> [--check]`; `--check` confirms that all 8 outputs reproduce byte for byte.
- `outputs/citation_coverage_c10.csv`: 1,060 rows, the 983 items plus the 77 placeholders.
- `outputs/case_coverage_c10.csv`
- `outputs/coverage_summary_c10.csv`
- `outputs/preservation_risk_c10.csv`
- `outputs/finding_status_c10.csv`
- `outputs/proposals_c10.csv`
- `outputs/QUALITY_C10_MANIFEST.json`
- `outputs/OUTPUT_SHA256SUMS`
- `inputs/c10_outputs_snapshot/` (pinned copy of the C10 reconciliation outputs)
