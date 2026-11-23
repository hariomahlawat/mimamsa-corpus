# CALIBRATION-02 quality scorecard (46 records, 382 propositions)

**REVIEWED is not LEGAL_APPROVED.** The figures below are evidence-review results from four independent reviewers (A statutory, B judicial, C procedure, D challenge), reconciled by `tools/reconcile.py`. The machine-readable versions are in `reconciliation/scorecard.json` and `reconciliation/record_scorecard.csv`.

**Rule sensitivity.** The reconciliation rule was revised after the reviews were seen, following coordinator QC-07 and the independent technical review (QC-10). `reconciliation/rule_sensitivity.json` gives the pre-registered rule's output beside the final one:
- record classes: 16 partial / 19 defect / 11 gap under the pre-registered rule, against 1 full / 15 partial / 19 defect / 11 gap under the final rule;
- disagreements: 32 escalated under the pre-registered rule, against 12 disagreements plus 17 severity splits under the final rule.

The finding-level counts do not depend on the rule.

## Six distinct layers
None of these implies the next:
1. **Reviewer-submitted evidence assessments** (claimed states): preserved exactly as submitted in `reviews/<R>/findings.csv`.
2. **Effective evidence classification:** derived by the shared rule `tools/evidence_classification.py` and listed per finding in `reconciliation/effective_evidence.csv`.
3. **Primary-source authenticity:** source-specific provenance in `registers/source_authentication_register.csv`. No signature has been cryptographically verified, and the Isaac file is AUTHENTICATION_PENDING.
4. **Source searchability:** WS-D canonical coverage; ANCHORED_FULL is 187 of 658.
5. **Substantive legal verification:** not established by this package. The reviews are evidence reviews.
6. **Formal legal-adviser or JAG approval:** none exists or is claimed.

## Records (46 of 46 reviewed)
| Classification | Count | Records |
| --- | --- | --- |
| FULLY_EVIDENCE_SUPPORTED: every legal proposition verified against a held primary source; nothing above P3; no reviewer recorded a source gap, an unsupported or contradictory state, or a need for legal advice | 1 | HCE-008 |
| PARTIALLY_SUPPORTED: some propositions verified; none above P3 | 15 | HCE-033, HCE-001, CM-001, EV-011, KB-030, ADM-CL-07, ADM-SC-02, CM-008, CM-012, EV-017, HCE-031, KB-004, KB-018, AFT-001, KB-029 |
| SUBSTANTIVE_DEFECT_FOUND: at least one P1 or P2 | 19 | COI-003 (P1), CM-026, CM-028, HCE-016, CM-JD-01, PEN-WF-03, ADM-CL-02, AFT-039, COI-031, J-03, PEN-003, PEN-024, PEN-CL-06, SC13, V7-JD-05, ADM-014, AFT-003, CIV-011, V8-JD-02 |
| UNSUPPORTED_OR_SOURCE_GAP: nothing verifiable from held primary sources | 11 | ADM-013, ADM-026, CM-040, PEN-006, ADM-001, ADM-CL-03, CM-007, COI-018, CIV-039, KB-001, KB-002 |

"Fully supported" is narrow. For HCE-008 it means every legal proposition was matched to a held primary instrument at a cited page. It does not mean the rule is currently in force, because the Army Rules amendment chain is still partial.

## Findings
| Measure | Value |
| --- | --- |
| Findings, all reviewers (A / B / C / D) | 1,536 (384 / 387 / 383 / 382) |
| Severity: P1 / P2 / P3 | 1 / 46 / 199 |
| Distinct propositions with a P1 or P2 | 32 |
| Evidence states (claimed by reviewers, as submitted) | 138 VERIFIED against a held primary source (134 effective primary, 4 authentication pending); 294 secondary only; 125 source not held; 21 historical version unresolved; 26 interpretation needs legal advice; 22 unsupported; 4 contradictory; 780 not a legal proposition; 126 out of a reviewer's scope |
| Unsupported legal propositions (any reviewer) | 13 |
| Historical-version findings | 44 |
| Judicial relationship findings (mislinked case or missing authority) | 32 |
| Cross-volume links | 35 (`registers/cross_volume_register.csv`) |
| P1 and P2 by defect class | omission 21; wording 7; historical version 4; wrong provision 4; source gap 3; citation 2; mislinked case or code 2; wrong authority 1; missing exception 1; cross-volume 1; metadata 1 |

The only P1 (COI-003#P6, Reviewer D) was raised from P2 after coordinator feedback that severity follows content (QC-03). A and C rated the same defect P2 and B rated it P3.

**Claimed versus effective primary evidence.**
- Reviewers claimed VERIFIED_AGAINST_HELD_PRIMARY_SOURCE on **138** findings.
- Under the shared rule, **134** are effective primary: the source's provenance is documented in the authentication register.
- **4** are AUTHENTICATION_PENDING: Reviewer B's Isaac findings B-0109, B-0111, B-0248 and B-0272. The Isaac bytes' official provenance is contested (QC-09, QC-13).
- Those four claims are preserved but not counted as primary. Reviewer D's secondary-only assessments of the same propositions are also preserved.
- **0** VERIFIED claims fail on protocol grounds: none is unheld, derived text, a mirror, a hash mismatch or missing a pinpoint. All held files re-hashed correctly.

## Agreement between reviewers (by proposition)
| Class | Propositions |
| --- | --- |
| No material defect raised | 199 |
| Non-legal, or outside every reviewer's scope | 151 |
| CORROBORATED_DEFECT (P1 or P2 raised by two or more reviewers) | 8 |
| SINGLE_REVIEWER_DEFECT (raised by one reviewer; the others silent or out of scope) | 1 |
| SEVERITY_SPLIT (raised by one reviewer, rated differently by another) | 11 |
| DISAGREE (raised by one reviewer; another assessed it as supported with no defect, or classed it as not a legal proposition) | 12 |

`reconciliation/disagreements.csv` lists 29 escalations: 12 disagreements and 17 severity splits. The 17 include corroborated defects whose severities differ, such as COI-003#P6. None is resolved by majority.

## Correction proposals (`proposals/`)
There are 47 proposals across 19 records:

| Status | Count |
| --- | --- |
| PRIMARY_EVIDENCE_SUPPORTED (the raising finding's effective status is primary, with source provenance documented) | 5: CM-026#P7, CM-028#P8, CM-028#REF, J-03#P1, SC13#P4 |
| AUTHENTICATION_PENDING (claims primary verification; source authentication pending) | 1: PEN-WF-03#P2 (CP2-B-0109, Isaac) |
| SECONDARY_EVIDENCE_ONLY | 16 |
| DISPUTED_ESCALATED | 16 |
| SOURCE_CONFLICT_OPEN (r.182 Gazette omission SC4-01; Santosh Lohar copy and date) | 6 |
| EVIDENCE_GAP | 3 |

None is incorporated. Each carries the original text, the claimed and effective evidence status, and its record ID and canonical hash (`proposals/correction_proposals.csv`, `proposals/proposed_versions.jsonl`). Primary-backed support exists for only 5 of the 47.

## Legal-adviser and source questions
- **Legal-adviser questions:** 36 from the reviewers, grouped into 13 topics, plus the 9 reserved items unchanged (`adviser/`).
- **Records unable to progress for lack of primary sources:** 11.
- **Records with at least one source-gap proposition:** 29.
