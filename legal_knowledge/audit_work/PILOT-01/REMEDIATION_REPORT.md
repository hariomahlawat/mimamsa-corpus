# PILOT-01 remediation report

**DATABASE ONLY. NO APPLICATION WORK.** 2026-11-22. The pilot is accepted by the owner as a research and technical audit exercise, not as legal validation.
**No proposition is advisor-approved or JAG-validated. The advisor has not been nominated.**
**Preserved unchanged:** the 658 originals (`9a8f0d19…`), the 53 cases (`8b8d53cd…`), all 8 MML files (manifest re-verified) and all prior research batches. CI re-checked the originals (below).

Labels: **[V]** verified this stage, with a locator. **[P]** proposal or preliminary. **[A]** assumption.

## 1. Disputed independent-review findings → `post_review/post_review_dispositions.csv`
There are 7 rows: the 6 DISPUTES plus the 1 RETURN_FOR_EVIDENCE. Original findings and reviews are preserved unchanged, and every row says `original_finding_changed=NO` and `advisor_decision_required=YES`.

| # | Finding | Disposition | Provisional | Basis |
| --- | --- | --- | --- | --- |
| D-01 | F-XVOL-001 (EV-016) | Reviewer position adopted provisionally | P0 → P2 | [V] EV-016 never quotes the caution. The r.23(3) conflict stays P0 at HCE-010 and MMLPKT-02. |
| D-02 | F-XVOL-002 (EV-016) | Reviewer position adopted provisionally | P0 → P2 | A silent record cannot contradict one that states the wording; P0 here double-counted F-STAT-001. The harmonisation proposal is kept. |
| D-03 | F-XVOL-007 (CIV-034) | **Advisor decision required** | P2 (provisional) | Interpretive: whether General Clauses Act s.8 reads Army Act s.133 as a reference to the BSA. Not marked resolved. |
| D-04 | F-JUD-014 (COI-039, control) | Reviewer position adopted provisionally | P3, no issue | Counted as a control false positive. The blind-pass issue on COI-039 (placeholders; "JAG approved" label with no supporting record) remains open. |
| D-05 | F-PROC-006 (CM-011) | Reviewer position adopted provisionally | P1 → P2 | A paraphrase ambiguity. The s.123(2) omission (F-PROC-007, P1) stands. |
| D-06 | F-MML-019 (MMLPKT-10) | Split / re-scoped | P1 | [V] page image: MML 2 p.89 note 6 says "by court-martial or a criminal court"; the s.121 text bars a second court-martial only. New finding **F-REM-002**. |
| D-07 | F-STAT-006 (HCE-017) | Evidence supplied; supplementary finding | P1 | [V] page images: India Code p.209 has no r.192 proviso; MML 2 p.227 prints one (SRO 215/1965). New finding **F-REM-001** (CONFLICTING). |

`post_review/severity_recalibration_proposals.csv` lists 10 further proposals from reviewer decisions that SUPPORTED a finding but recommended a different severity. One is an increase: F-PROC-019, s.81(4), P1 → P0. **[V]** The image of India Code Army Act p.28 shows s.81(4)'s "or was, at the time of committing the offence … of such rank" limb, which HCE-017 leaves out.
**Provisional profile, if adopted:** P0 4, P1 16, P2 41, P3 48 (originally 5 / 25 / 31 / 48). The two supplementary findings (F-REM-001/002) **are not yet independently reviewed**; they are queued in the packet annex.

## 2. Citation-code resolution → `registers/source_code_resolution_v2.csv` (v1 kept unchanged)
| | v1 | v2 |
| --- | --- | --- |
| Officially corroborated (SHA-256 verified) | — | **33** |
| Resolved because the record itself names the source | — | **32** |
| Resolved by co-citation (V9-S01 = BSA, V9-S02 = Army Act, V9-S03 = Army Rules) | — | 3 *(statistical: 31/32 and 12/15 co-occurrence; treat as strong-probable)* |
| Proposed | 57 | — |
| Probable (single weak signal) | — | 9 |
| Unresolved / unresolvable | 21 | **1** (V6-S03, "Portal" with no name) |

- **Firm resolution:** 65/78 = **83%**. With co-citation: 68/78 = **87%**. **Below the 90% threshold; no identity was inflated to reach it.**
- **Downgrades from v1 (2):** V7-S16 (no named portal); V8-S15 (AFSPA 1958 vs the J&K 1990 Act is undetermined).
- **v1 errors corrected:** Tarsem Singh and L. Chandra Kumar *are* in the 53 cases.
- **[V]** All 33 official SHA-256 values match downloaded or registered files. The paragraph locators checked against official texts were consistent: Virendra Kumar, Parashotam Dass, Jasbir Singh (53 paras), P S Gill, N S Yadav, Girish Kumar (Feb 2026), Balakrishnan Mullikote, Prithi Pal Singh Bedi and Ranjit Thakur.
- **Duplicates:** Virendra Kumar has 4 codes (SRC-VIR, SRC-VIRENDRA, SC_VK, V9-S07). The Army Act, Army Rules, AFT Act, BNSS and AFT Procedure Rules each have several.
- **Gap in the register itself:** SRC-RA (6 records), SRC-AO (6), SRC-INDER (1), SRC-HUSSAIN (1) and the shorthands PPS, VISHAV, RANDHIR and VIRENDRA are used in the records but were missed by the v1 extraction. They are to be added in the next batch, so the code universe is above 78.

## 3. MML reproducibility (private) → `tools/legal_audit/mml_extract.py`, `docs/legal-audit/MML_REPRODUCIBILITY.md`, `PILOT-01/mml_derived_manifest.json`
- The tool checks all 8 originals against the manifest, refuses any output path inside the repository, runs LibreOffice with an isolated profile, and can render page images for checks.
- **[V]** Two runs gave byte-identical output for all 8 files. The 3 PDF layers are byte-identical to the pilot layer. The 5 DOC layers keep identical line counts and numbering, so every pilot DOC locator stays valid. The differences are characters only: the earlier layer was partly cp1252 and lost ellipses, soft hyphens and dashes.
- Only hashes, counts and tool versions are committed (pdftotext 24.02.0, LibreOffice 24.2.7.2). **No extracted manual text is committed or uploaded.**
- **Owner decision:** the base64 MML transfer parts remain in the private Git history of `legal-knowledge/v2.5-staging`.

## 4. Reviewer identity and source authenticity
- **Validator** (`identity_checks`) with `PILOT-01/reviewer_identities.json`:
  - every independent review is bound to a declared reviewer
  - a reviewer's evidence must carry its own source prefix
  - no cross-reviewer evidence
  - no first-pass finding may cite reviewer sources
  - no self-review
  - `blind=true` only for the blind stage
  - optional exact `retrieved_by`, mandatory for the next batch
- **Tests:** 10 new; **33 tests** in total. The PILOT-01 batch passes the identity rules: **[V]** no independence leak detected.
- **Page-image register** (`registers/page_image_checks.csv`): 7 checks with render SHA-256, recorded by me, plus 2 reported by reviewer A without hashes. All matched the text layer:

| Page | Provision |
| --- | --- |
| India Code Army Rules p.41 | r.23(3) "obliged" |
| MML 2 p.152 | r.23(3) "not obliged" |
| India Code Army Rules p.209 | r.192, no proviso |
| MML 2 p.227 | r.192 proviso; also a r.194 wording variant |
| MML 2 p.89 | s.121 note 6 |
| India Code Army Act p.28 | s.81(4) |
| Act 37 of 1992 Gazette Extraordinary No. 59, p.1 | 7-9-1992; assent 6-9-1992; s.2 omits ss.75–76 |

- **New observation [V]:** r.194 differs between the India Code compilation and MML 2 ("or the officer commanding an Army"). Not in the pilot scope; noted for the next batch.

## 5. GitHub Actions and separation → `CI_EVIDENCE.md`
- **Separation:** draft [hariomahlawat/mimamsa-corpus#6](https://github.com/hariomahlawat/mimamsa-corpus/pull/6) (head `claude/audit-pilot-01`, base the PR 5 kit) contains **audit paths only**. The unrelated crawler and state changes (`main` 21de353: PROGRESS.md, reports/ocr_review.md, state/wider_terms_hits.json) are excluded and remain only on `claude/gifted-bardeen-byeim6`.
- **Actual result:** run **45023068164**, conclusion **success**, on Python 3.11.18:
  - schema check OK
  - **33 tests OK**
  - strict PILOT-01 validation `errors: []` (209/126/33)
  - originals `sha256sum -c` OK
  - The only warning is GitHub's Node 20 deprecation notice.
- **Not in CI:** the crawler test suite (5 local import errors from missing pymupdf and other packages); MML extraction (originals deliberately absent from CI).
- **HF sync safety:** the sync workflow triggers only on pushes to `main` or `legal-knowledge/v2.5-staging`, so the PR does not trigger it. **Merging the stack into either branch would.**

## 6. Legal-advisor review packet → `ADVISOR_REVIEW_PACKET.md` and `advisor_review_packet.csv`
32 items in priority order:

| Group | Items |
| --- | --- |
| A. P0 | 6 |
| B. Unresolved statutory or source conflicts, blocked authority | 5 |
| C. Other P1 statutory, procedural and manual | 14 |
| D. Judicial holdings and later treatment | 4 |
| E. Cross-volume | 3 |

- Each item gives the record text tested, the finding, the proposed correction (not applied), evidence with authenticity tier, page-image references, the independent-review decisions, the post-review disposition, the questions, and a blank decision block (decision, severity, name/role/date, approval reference).
- The annex holds F-REM-001/002.

## 7. Acquisition plan → `ACQUISITION_PLAN.md`
Ten item groups, each with a route, fallback and status:
- Gazette S.R.O.s, including S.R.O. 484 (1954) and SRO 215 (1965)
- Army Act amending Acts
- Regulations for the Army
- Entitlement Rules 1982/2008/2023
- the 1978 Adjustment Rules (amended by S.O. 4010 of 1986)
- AFT judgments
- BNS/BNSS/BSA commencement notifications
- ISO Act and Rules; Agniveer notifications
- six missing judgments

**Blocked from this container:** egazette, mod.gov.in and aftdelhi. **Runnable now from India Code and sci.gov.in:** items 3, 9 (part) and 10.

## Revised scorecard → `scorecard_v2.json` (v1 `scorecard.json` kept)
| Metric | PILOT-01 | After remediation |
| --- | --- | --- |
| Items with explicit outcome | 43/43 | 43/43 (+2 supplementary findings) |
| P0/P1/conflict independently reviewed | 31/31 | 31/31; 7/7 disputes or returns have a recorded disposition |
| Provisional severity P0/P1 | 5/25 | **4/16** (proposed) |
| Citation codes resolved | 57/78 proposed | **65/78 firm (83%), 68/78 inclusive (87%)**; threshold 90% **not met** |
| Page-image checks with recorded hash | 0 | 7 (+2 reported) |
| MML extraction reproducible | not shown | 8/8 deterministic; text not committed |
| Validator tests / CI | 23 local | **33; CI success (run 45023068164)** |
| Reviewer identity enforcement | single shared identity | per-reviewer binding enforced |
| Advisor-reviewed / approved | 0/0 | 0/0 |

## Open items needing owner action before the calibration batch
1. Nominate the legal advisor and have the 32-item packet adjudicated. This creates the reference set that accuracy measurement depends on.
2. Authorise acquisition: Indian-network access for egazette and the AFT site, and sending the custodian request.
3. Decide on the MML transfer parts in private Git history.
4. Approve the next calibration batch scope. Proposed: Vol II (COI, 46 records) under the strengthened controls, after the citation-code register is extended with the missed codes.

**Stopped for review. No calibration batch started. DATABASE ONLY. NO APPLICATION WORK.**
