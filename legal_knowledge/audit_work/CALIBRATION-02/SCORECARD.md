# CALIBRATION-02 quality scorecard (46 records, 382 propositions)

**REVIEWED is not LEGAL_APPROVED.** The figures below are evidence-review results from four independent reviewers (A statutory, B judicial, C procedure, D challenge), reconciled by `tools/reconcile.py`. The machine-readable versions are in `reconciliation/scorecard.json` and `reconciliation/record_scorecard.csv`.

## Records (46 of 46 reviewed)
| Classification | Records | Records |
| --- | --- | --- |
| FULLY_EVIDENCE_SUPPORTED (every legal proposition verified against a held primary source, with nothing above P3 and no source gap) | 2 | KB-030, HCE-008 |
| PARTIALLY_SUPPORTED (some propositions verified, none above P3) | 14 | HCE-033, HCE-001, CM-001, EV-011, ADM-CL-07, ADM-SC-02, CM-008, CM-012, EV-017, HCE-031, KB-004, KB-018, AFT-001, KB-029 |
| SUBSTANTIVE_DEFECT_FOUND (at least one P1 or P2) | 19 | COI-003 (P1), CM-026, CM-028, HCE-016, CM-JD-01, PEN-WF-03, ADM-CL-02, AFT-039, COI-031, J-03, PEN-003, PEN-024, PEN-CL-06, SC13, V7-JD-05, ADM-014, AFT-003, CIV-011, V8-JD-02 |
| UNSUPPORTED_OR_SOURCE_GAP (nothing verifiable from held primary sources) | 11 | ADM-013, ADM-026, CM-040, PEN-006, ADM-001, ADM-CL-03, CM-007, COI-018, CIV-039, KB-001, KB-002 |

"Fully supported" is narrow. For KB-030 and HCE-008 it means every legal proposition was matched to a held primary instrument at a cited page. It does not mean the rule is currently in force, because the Army Rules amendment chain is still partial.

## Findings
| Measure | Value |
| --- | --- |
| Findings, all reviewers (A / B / C / D) | 1,536 (384 / 387 / 383 / 382) |
| Severity: P1 / P2 / P3 | 1 / 46 / 199 |
| Distinct propositions with a P1 or P2 | 32 |
| Evidence states | 142 VERIFIED against a held primary source; 290 secondary only; 125 source not held; 21 historical version unresolved; 26 interpretation needs legal advice; 22 unsupported; 4 contradictory; 780 not a legal proposition; 126 out of a reviewer's scope |
| Unsupported legal propositions (any reviewer) | 13 |
| Historical-version findings | 44 |
| Judicial relationship findings (mislinked case or missing authority) | 32 |
| Cross-volume links | 35 (`registers/cross_volume_register.csv`) |
| P1 and P2 by defect class | omission 21; wording 7; historical version 4; wrong provision 4; source gap 3; citation 2; mislinked case or code 2; wrong authority 1; missing exception 1; cross-volume 1; metadata 1 |

## Agreement between reviewers (by proposition)
| Class | Propositions |
| --- | --- |
| No material defect raised | 199 |
| Non-legal, or outside every reviewer's scope | 151 |
| CORROBORATED_DEFECT (P1 or P2 raised by two or more reviewers) | 9 |
| SINGLE_REVIEWER_DEFECT (raised by one reviewer, with no dissent) | 3 |
| SEVERITY_SPLIT (raised by one reviewer, rated P3 by another) | 12 |
| DISAGREE (raised by one reviewer, assessed by another as supported with no defect) | 8 |

All 20 disagreements and severity splits are escalated in `reconciliation/disagreements.csv`. None is resolved by majority.

## Correction proposals (`proposals/`)
There are 47 proposals across 19 records:

| Status | Count |
| --- | --- |
| EVIDENCE_SUPPORTED (held-source hash and locator) | 27 |
| DISPUTED_ESCALATED | 11 |
| SOURCE_CONFLICT_OPEN (r.182 Gazette omission; Santosh Lohar copy and date) | 6 |
| EVIDENCE_GAP | 3 |

None is incorporated. Each one carries the original verbatim text and is linked to its record ID in `proposals/proposed_versions.jsonl`.

## Legal-adviser and source questions
- **Legal-adviser questions:** 36 from the reviewers, grouped into 13 topics, plus the 9 reserved items unchanged (`adviser/`).
- **Records unable to progress for lack of primary sources:** 11 (UNSUPPORTED_OR_SOURCE_GAP).
- **Records with at least one source-gap proposition:** 29.
