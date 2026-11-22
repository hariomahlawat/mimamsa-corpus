# Coordinator review: WS-B hand-off 1 (issue #12), 2026-11-22

**Reviewed:** `claude/ws-b-judgments` commits 28326d4c, d164f682, plus merge 68290bae of `claude/next-stage-proposal` (PR #16). No agent file was edited.

## Checks performed
| Check | Result |
| --- | --- |
| Paths changed only under `WS-B-JUDGMENTS/` | PASS |
| Intern intake read-only, not duplicated | PASS: read from `origin/raw-data` at ad77758d via git; no re-collection; missing judgments are queued (22), not downloaded |
| Commercial databases not used as evidence | PASS: the single indiankanoon URL is the curated record's own `curated_primary_source_url`, marked NO_MATCH_FOUND / UNRESOLVED |
| No approval states claimed | PASS: legal-advisor and JAG states NOT_STARTED; the one "APPROVED" string match is inside a case title in the intake data |
| Gates after merge | PASS: audit tests OK; PILOT-01 and R23 strict OK; `check_registers.py` 0 errors; CSVs well formed; cases_53 sha unchanged (8b8d53cd…); `tools/check_ws_b.py` OK |
| **Independent spot check of a consequential item (A-03)** | **CONFIRMED** on the official SC copy of Parashotam Dass (sha fe19875b…, equal to the PILOT-01 register), PDF p.22 para 32: "...the judgment in Major General Shri Kant Sharma & Anr. case does not lay down the correct law and is in conflict with judgments of the Constitution Benches...". Read from the text layer by the coordinator; WS-B recorded its own page-image check of p.22. |

## Assessment
- **Intake:** 4,327 intern records, 4,259 judgments, 3,951 distinct by SHA-256. Defects found in the intern intake:
  - the "invalided" keyword also matches "invalidation";
  - two cited precedents were filtered out (L. Chandra Kumar, S.R. Dhingra);
  - no AFT judgments are present;
  - the counts differ from PROGRESS.md.

  These are reported to the owner; nothing in the intern corpus was changed.
- **Carrier:** the AWS Open Data mirror is classed as a third-party facsimile with hash-only fidelity, per policy v1. The SCR headnote pages are editorial and are not used as holdings.
- **The 53 curated cases:** 34 matched to intern documents by cover-page identity (answers OQ-D-012); 13 have official copies held; 13 are unresolved; 10 have an empty holding and are flagged not citable (OQ-D-008).
- **Holdings:** 16 judgments read on official copies (6 pages image-checked); the 7 P0 pension cases are mirror-only, with provisional pinpoints.
- **Adverse queue:** 16 items. Notable ones:
  - Isaac 2026 paras 34 and 39 (assumes the 2008 Rules' effect; Rule 7 burden after 15 years);
  - Isaac para 19.4 is argument, not holding;
  - the role of Isaac Part III (A-16);
  - Shri Kant Sharma is disapproved in Parashotam (A-03), but curated row N06 carries no adverse flag;
  - N.S. Yadav;
  - corrected versions of Virendra and Mullikote.

  All are proposals for legal review.

## Routing
- Owner: OQ-01 (canonical intern snapshot), OQ-02 (mirror as interim carrier), OQ-07 (a lawful, CAPTCHA-free route to SC copies), OQ-08 (an allow-list for cited precedents in the intern filter), and an AFT route.
- Advisor: OQ-04/05 (Entitlement Rules 2008, Rule 7 period), OQ-06 (adverse flag wording), A-16.

## Disposition
Accepted as a review proposal. PR opened against `claude/next-stage-proposal`. Not merged. Technical review only.
