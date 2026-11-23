# Owner decision matrix, Cycle 9 (proposals only; nothing adopted)

**Status.**
- Rule version 1 stays in force, and the AUTH-LEDGER stays at version 0.
- Each row is a decision for the repository owner, and for the legal adviser where marked.
- "Recommendation" is the preparer's view. Agreement between agents is not a reason to adopt anything.
- An adopted item is built in its own reviewed PR: rule version 2, or activation policy 2.

## How to read the columns
- **Effect now:** what changes on current data if the item is adopted.
- **Blocks:** what cannot proceed until the item is decided.
- **Evidence:** where the facts are. C8 evidence is on the clean branch `claude/c9-evidence-clean` (draft PR #40).

## Evidence-rule and classification decisions
| Id | Question | Options | Recommendation | Effect now | Blocks | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| P-A (A3) | Should a SOURCE_LOCATED retrieval record count for provenance only, with content identity proved separately? | A1 keep rule 1; A2 require VERIFIED; A3 add `retrieval_verification_state` | **A3, only together with B2** | 3 drafts affected (Navjot, S.R.O. 34/1963, Rajbir rendition); none becomes ineligible under A3, 2 would under A2 | Navjot and S.R.O. 34 entries | `C8-SOURCES/RULE_VERSION_DECISION_PACK_C8.md` (A3); PR #40 page checks |
| P-B (B2) | Does an anchor-creating entry need a CONFIRMED identity check, and do AI-agent page readings count as CONFIRMED? | B1 rule 1; B2 confirmed check or a reviewer statement | **B2; AI readings are supporting evidence only** | 7 court entries need a human or reviewer-attested check. The human pack prepares this (`SC-C9/HUMAN_VERIFICATION_PACK.md`, PR #40) | All 7 anchor-creating court entries | Decision pack (B2); SC-C9 pack |
| P-C (C2) | URL comparison and aliases | C1 exact string; C2 RFC-safe normalisation plus a reviewed alias table | **C2, with the archive.org item alias (item identity plus hash agreement)**; a court-path alias only on byte-identity evidence | none on current data | none | Decision pack (C2) |
| P-D1 | Confirm the copy-fidelity table | confirm / amend | confirm | none | P-D2, P-D2a | `AUTH-LEDGER/POLICY_OPTIONS.md` |
| P-D2 | Born-digital T1-19 (S.R.O. 2(E)/2018), whose CMS signature verifies (integrity only) | primary provisionally / hold | **provisionally primary, integrity only** | 1 Gazette candidate | T1-19 | PR #40 `GAZETTE-T1/BORN_DIGITAL_FINDINGS.md` |
| P-D2a | Born-digital file whose signature **fails** (T1-20, S.R.O. 17(E)/2019) | primary (rule 1 today) / split class non-primary | **split: `BORN_DIGITAL_SIGNATURE_FAILS` is non-primary**; until then, do not approve T1-20 | T1-20 ineligible for a primary class | T1-20 | same; reproduced with `openssl cms` |
| P-D2b | Unsigned born-digital or text-layer file (e.g. S.R.O. 6(E)/2022) | own class / facsimile route | own class (Fable task 8) | none yet | future entries | Decision pack |
| P-D3 (JUDIS) | How to class JUDIS text renditions (PPS Bedi baseline anchor; Ranjit, S N Mukherjee, Navjot drafts) | (a) primary: 6→13; (b) non-primary, applied consistently: 6→9; (c) identity primary, anchors only on judgment text (needs rule 2) | **end state (c); until rule 2, no change either way**: do not add the 3 drafts, keep PPS Bedi's row with a recorded limitation. If the asymmetry is unacceptable, demote PPS Bedi to pending (6→9), but only after O-5 | none until decided | 3 JUDIS drafts; any PPS Bedi CORRECTION | PR #40 `SC-C9/JUDIS_POLICY_DECISION.md`, `EXACT_ANCHOR_C9.md` |

**Exact-anchor counts.** All were re-run in C9 with the real reader, in temporary ledgers:

| Scenario | Exact anchors |
| --- | --- |
| Version 0 | 6 |
| Any one candidate | 7 (Narsingh Yadav 6) |
| All 8 together | 13 |
| Without the JUDIS drafts | 10 |
| Without Navjot and Mullikote | 11 |
| Without the JUDIS drafts and Mullikote | 9 |
| Option (b) applied consistently | 9, a different set of cases |

No count above 13 was reproduced. **New in C9:** option (b) cannot be recorded cleanly under rule 1, because demoting PPS Bedi to a documented non-primary rendition fails the validator. PPS Bedi has no `copy_facts` row.

## Ledger governance decisions
| Id | Question | Recommendation | Blocks | Evidence |
| --- | --- | --- | --- | --- |
| O-1 | An owner signature over each BIND line, with a key supplied out of band | **decide before the first BIND line**. Without it, owner identity rests on GitHub account control | first BIND | `AUTH-LEDGER/APPROVAL_CONTROLS.md` |
| O-2 | Branch protection on staging: PR required, 1 approving review, stale approvals dismissed, no force-push, no bypass | adopt. This is a GitHub setting, not changed by agents | meaningful BIND assurance | same |
| O-3 | CI full history | **discharged**: PR #37 merged at `ff425a9a` | — | `.github/workflows/legal-audit-kit-ci.yml` |
| O-4 | A committed list of authorised owner and reviewer identities | only together with O-1 | — | same |
| O-5 | Should a WITHDRAW or demoting CORRECTION take effect before its BIND line? | **activation policy 2**: demotions for cause take effect immediately, with records; promotions stay staged. Not implemented | P-D3 option (b); any demotion | `AUTH-LEDGER/DEMOTION_SEMANTICS_O5.md` |

## New decisions raised in Cycle 9
| Id | Question | Options | Recommendation | Evidence |
| --- | --- | --- | --- | --- |
| PRIV-01 | Mullikote officer service numbers: 36 tokens in 12 C8 files and 36 in 11 pre-existing files | mask in a reviewed change / accept as published | owner's choice. Masking C8 needs builder regeneration | PR #40 `TRANSFER_RECORD.md` §4 |
| PRIV-02 | A diagnosis term naming an individual's condition (4 pre-existing files, including the protected `records_658.jsonl`) and an N S Yadav service number (3 files), already on staging | accept / mask derived files, with a separate decision on the protected original / also purge history | owner's choice. Agents cannot modify protected originals | same |
| RAW-01 | Register the 67 raw-store statutory PDFs (`raw-data` @ `ad77758d`), which include the AFT Act 2007 Gazette and the AFT Procedure and Practice Rules | AP-C9-02 registration, no download / leave unregistered | **register under AP-C9-02**. Ten C8 "not held" statements are superseded by this finding | `STATUTORY/STATUTORY_C9_FINDINGS.md`, `APPROVAL_PACKAGES.md` |
| ACQ | Acquisition approvals AP-C9-03 to AP-C9-08 | per package | per package. Only the 14 PR #8 documents are ready under existing approval, and they still need PR #8 merged and a logged run approval | `STATUTORY/acquisition_manifest_ready.csv`, `APPROVAL_PACKAGES.md` |
| ESC-01..09 | Legal-adviser escalations: Tarsem / Girish reach; the unheld 2026 clarification; r.23(3) caution (P0); acquisitions; s.122 / s.123(2); Parashotam / Shri Kant Sharma; s.133 and BSA; Ram Avtar identity; ADM-022 wording | adviser to decide | proposals stay PROPOSAL_NOT_APPLIED | `CORRECTIONS/LEGAL_ADVISER_ESCALATION.md` |
| TXN-1..3 | Ledger tooling gaps found by the synthetic transaction: `verify` ignores unexpected files under `effective/`; there is no CLI append or bind command; the `basis` column wording | fix in a reviewed AUTH-LEDGER PR / accept | fix TXN-1 before the first real entry; TXN-2 optional | `TXN-DEMO/README.md` |
