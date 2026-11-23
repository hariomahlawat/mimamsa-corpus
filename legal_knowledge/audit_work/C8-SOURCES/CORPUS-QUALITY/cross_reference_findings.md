# C8 / WS-E: cross-reference audit

Snapshot: `c8base` at commit bb1f0971 (read-only; `git status` was clean after the run). Findings are in `cross_reference_findings.csv` (23 rows). Raw candidates from the scripted checks are in `work/xref_candidates.csv` (125 rows).

## Method

1. **Scripted checks.** `tools/xref_checks.py <repo> <scratchpad> <out>` runs offline, stdlib only, and never edits its inputs. It joins the curated records (`records_658.jsonl`, `cases_53.jsonl`) with the WS-B, WS-D and SOURCE-LIBRARY-C5 registers and the held-binary manifest. Every candidate row names the record or register key, the field, and the evidence file.
2. **Novelty check.** Each candidate was checked by hand against an index of existing registers: WS-D, WS-B (including open_inconsistencies_cycle3 and the adverse queue), SOURCE-CONFLICTS-01, CALIBRATION-02 (findings, proposals, cross_volume_register, adviser questions), the C6-PREP carry-over, PILOT-01 (findings JSON, corrections, missing relationships and records), the C5 conflict register and correction register, verification_batches and legal_review. A candidate is NEW only if no register already records the same defect on the same record.
3. **Verification against held sources.** Statutory checks used PyMuPDF text extracted from the held copies. Each was cited by sha256 and PDF page:
   - Army Act compilation `e47a4265…`
   - Army Rules compilation `48f52219…`
   - AFT Act `665863d1…`
   - BNSS `572c7988…`
   - BSA `554b2b4a…`
   - Girish Kumar (2026) `4f7ea3a4…`
   - Parashotam Dass `fe19875b…`

## Checks and counts

| Check | What it tests | Candidates | Triage result |
| --- | --- | --- | --- |
| X00 | Held-binary manifest `hash_check` = MATCH | 0 | clean |
| X01 | Case record archive flags vs held official copies | 13 | EXISTING (E8-XR-10) |
| X02 | Commercial-database URLs in case/KB records | 23 | EXISTING (E8-XR-11) |
| X03 | One URL attached to several distinct judgments | 3 groups | 1 NEW (E8-XR-03), 2 EXISTING (E8-XR-12, -13) |
| X04/X04b | id-year vs decision date; missing decision dates | 1 / 9 | id-year: cosmetic, not reported; dates EXISTING (E8-XR-16) |
| X05b | Asymmetric `related_cases` | 1 | EXISTING (E8-XR-23) |
| X06 | Omitted AA ss.75, 76, 127, 195, 196 cited without a flag | 4 | 3 EXISTING (E8-XR-14); 1 false positive (CM-SC-18 itself flags the omission) |
| X07 | IPC/CrPC/Evidence Act references with no 2024-transition marker | 3 | 0 defects: all 3 carry "obsolete/earlier/older" caveats |
| X08 | Unresolved citation codes | 2 | EXISTING (E8-XR-18) |
| X09 | corpus_crosswalk referential integrity (KB, case, source ids) | 0 | clean |
| X10 | Copy register vs held manifest vs master register | 0 | clean |
| X11/X12 | Amendment-register chronology; chain instrument refs exist | 0 | clean |
| X13 | Versioned edges: valid_to before valid_from; unknown record ids | 0 | clean |
| X14b | WS-B `affected_kb_ids` tokens that are not record ids | 11 | NEW P3 (E8-XR-07) |
| X14c | WS-B copy hashes not in the C5 held manifest | 9 | by design (intern mirrors, not C5 binaries): not a finding |
| X15 | Neutral citation in WS-B identity register but absent from the case record | 31 | NEW P3 (E8-XR-06) |
| X16 | Duplicate KB titles (duplicate concepts) | 3 | Virendra/PPS Bedi EXISTING (E8-XR-17, CALIBRATION D-CV); PEN-017/PEN-WF-03 consistent, not a finding |
| X18 | Conflict register cites unknown sources | 0 | clean |
| X19 | Later-treatment edges vs every KB record the WS-B crosswalk links to the treated case | 5 | 1 NEW P2 (E8-XR-01), 1 NEW P3 (E8-XR-02), 2 EXISTING (Isaac/NS Yadav, E8-XR-15), 1 no defect (AFT-035) |
| X20 | Chain commencement status vs amendment register for the same instrument | 6 | NEW P3 (E8-XR-04) |
| X21 | Parent conflict left open after a split | 1 | NEW P3 (E8-XR-05) |
| manual | High-risk sample (see HIGH_RISK_REVIEW.md) | — | NEW P3 E8-XR-08, E8-XR-09 |

## NEW findings

- **E8-XR-01 (P2): Tarsem Singh treatment not propagated.** Girish Kumar (2026 INSC 149, held official copy `4f7ea3a4…` pp.15-16 para 22) held Tarsem Singh to have "no application" to broad-banding re-computation claims, and held the AFT s.22(1)(c) bar inapplicable to them. WS-B recorded the edge (WSB-T-005, WSB-H-027) but listed only V7-JD-04 and PEN-CS-09 as affected. AFT-013 and V7-SC-02, which both deal with pension arrears and continuing wrong, still present Tarsem Singh with no reference to the 2026 distinction. Case record DCLR-SC-2008-N10 carries no treatment.
- **E8-XR-02 (P3):** S P Rathore's explanation and limitation of Ram Avtar (WSB-T-024) is not propagated to PEN-023, PEN-044 or PEN-WF-08. The evidence is an intern mirror only.
- **E8-XR-03 (P3):** Four citation-lead case records (L07–L10) use the Ravinder Kumar order URL (`bosir/orderpdf/1525127.pdf`) as their own accessible source. This is the same class as OI-08, but these records are not registered anywhere.
- **E8-XR-04 (P3):** Six C5 chain rows say "commencement NOT_DETERMINED". The amendment register says "STATED_IN_INSTRUMENT" for the same instruments (AR-016, -031, -034, -035).
- **E8-XR-05 (P3):** C5-CF-C-04 is still OPEN after its split into C-08/C-09.
- **E8-XR-06 (P3):** Neutral citations are absent from case records. Five of them are corroborated by held official copies.
- **E8-XR-07 (P3):** WS-B `affected_kb_ids` contains codes and wildcards, which blocks deterministic propagation.
- **E8-XR-08 (P3):** ADM-022 turns the permissive s.26(2) "may complain" into "explicitly directs".
- **E8-XR-09 (P3):** CM-011 and CM-025 carry SOURCE_REVIEWED status while their P1 findings are still open and unapplied.

The checks found no unsupported current-law claim in the KB:

- No record presents IPC, CrPC or the Evidence Act as current without a transition caveat.
- No record presents the omitted field-punishment sections (ss.75-76) or s.127 as in force. The remaining range citations that include s.127 are already registered (D-CV-001/002).

## Limitations

- X15 and X19 depend on the WS-B crosswalk. A KB record that discusses a case without being linked to it in that crosswalk is not tested.
- X07 is lexical. It cannot detect an outdated proposition that names no statute.
- Several judgment readings rest on text layers, not page images (Girish p.15-16 is text layer only).
