# Legal-advisor review packet — PILOT-01 (FINAL v1.0, 2026-11-22)

| Status layer | Meaning | Who | State in this packet |
|---|---|---|---|
| Source verification | A cited source exists and reads as stated at the pinpoint | audit agents | recorded per item |
| Independent review / disposition | Adversarial technical challenge by a separate agent; orchestrator's provisional disposition | independent-reviewer A/B/C, orchestrator | recorded per item — **NOT legal approval** |
| Substantive legal decision | Professional legal judgement on the proposition and proposed correction | nominated legal advisor | **blank — advisor not nominated** |
| Formal validation | Attributable JAG/formal authority approval | formal authority | **none** |

**Status: FOR ADVISOR DECISION. Advisor not yet nominated. No item is advisor-approved or JAG-validated.** Agent findings are research proposals; independent-agent reviews are challenges, not legal sign-off. Originals (658 records, 53 cases, 8 MML files) are unchanged; every correction is a proposal.

**How to decide each item:** mark one of ACCEPT_PROPOSAL / ACCEPT_WITH_AMENDMENT / REJECT / NEEDS_MORE_EVIDENCE, confirm or set severity, and answer the listed question(s). Record name, role, date and a signature/approval reference so that the decision can be entered as a LEGAL_ADVISOR review record (`reviews/*.json`).

Items: 32 queued first-pass findings (P0 first), plus an annex of 2 supplementary remediation findings. Page-image evidence: `registers/page_image_checks.csv`. Dispositions: `post_review/`.


## A. P0 issues

### Item 1: F-XVOL-001 — EV-016 — first pass P0 / provisional P2

- **Outcome / evidence state:** CONFLICTING_SOURCES / CONFLICTING; agent: cross-volume-auditor
- **Record text tested:** records_658.jsonl:line 578: “The accused may cross-examine, make a voluntary statement after appropriate caution, and call defence witnesses; evidence must be read over and signed as provided.”
- **Finding:** EV-016 states the accused may make 'a voluntary statement after appropriate caution' under Rule 23 without quoting the caution. The r.23(3) caution wording is CONFLICTING between the India Code compilation (no 'not') and the MML copies ('not obliged'). EV-016 is caution-neutral in wording but its 'may ... voluntary statement' framing implies the 'not obliged' reading, and its url field points to a government-hosted Army Rules compilation of the kind that omits 'not'.
- **Proposed correction (not applied):** Proposal only: add a visible flag, e.g. 'The wording of the Rule 23(3) caution differs between government-hosted compilations and Manual of Military Law copies; the original S.R.O. 484 (27-11-1954) has not been authenticated. Do not quote either version as authoritative; refer to legal review.'
- **Temporal scope:** Army Rules 1954 as consolidated on India Code (corpus copy retrieved 2026-11-21); original S.R.O. 484 of 27-11-1954 and later amending S.R.O.s not held or verified.
- **Evidence:** S-XVOL-002: Army Rules, 1954 (India Code compilation) - r.23(3) caution sentence t — [[page 41]]: r.23(3) second sentence, caution reads 'You are obliged to say anything unless you wish to do so' (word 'not' absent) [OFFICIAL_COMPILATION, RULE]
- **MML anchors (secondary, not proof):** S-MML-005, S-MML-006, S-MML-007, S-MML-008
- **Limitations:** The specific url in EV-016 (upload.indiacode.nic.in showfile ... armyrules1954.pdf) was not fetched; the comparison used the corpus India Code copy at a different URL (bitstream a7bf1768...).; MML texts were not re-read beyond confirming the 'not obliged' line in derived text; MML is cited only via mml_anchor_ids.; No judgment on r.23(3) wording or on voluntariness of SoE statements was checked.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-B-005 (independent-reviewer-B, INDEPENDENT_AGENT): **DISPUTES** — The underlying r.23(3) conflict is real (S-REVB-007: compilation prints 'You are obliged to say anything unless you wish to do so'; fixed position - not resolved). But the finding's application to EV-016 is over-flagged. EV-016 never quotes or paraphrases the disputed sentence. Its 'may ... make a voluntary statement after appropriate caution' is supported by parts of r.23(3) that are not in dispute in either version: the accused 'will be asked; 
> - Orchestrator provisional disposition: REVIEWER_POSITION_ADOPTED_PROVISIONALLY; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Which text of the r.23(3) caution is authoritative: the original S.R.O. 484 of 27-11-1954 and any amending S.R.O. must be obtained before any record quotes the caution.
- Question: Should records describing the caution carry a mandatory 'disputed wording' flag until authentication?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 2: F-XVOL-002 — EV-016 — first pass P0 / provisional P2

- **Outcome / evidence state:** CONFLICTING_SOURCES / CONFLICTING; agent: cross-volume-auditor
- **Record text tested:** records_658.jsonl:line 578: “The accused may cross-examine, make a voluntary statement after appropriate caution, and call defence witnesses; evidence must be read over and signed as provided.”
- **Finding:** Across volumes the 658 records describe the r.23(3) caution inconsistently: HCE-010 states as settled law that the accused 'is not obliged' to make a statement (the MML reading); V9-SC-19 implies the same ('voluntary statement protections ... record refusal without coercion'); EV-016, KB-006, V9-CL-04 and V9-WF-05 are caution-neutral. No record found states the compilation wording ('obliged') as authoritative. Because the primary text is CONFLICTING, HCE-010's unqualified assertion and EV-016's silence cannot both be correct presentations of an unresolved source position.
- **Proposed correction (not applied):** Proposal only: harmonise EV-016, HCE-010, V9-SC-19, KB-006, V9-CL-04 and V9-WF-05 so that each either avoids paraphrasing the caution or carries the same disputed-wording flag; do not adopt either reading by majority of records.
- **Temporal scope:** Army Rules 1954 as consolidated on India Code (corpus copy retrieved 2026-11-21); original S.R.O. 484 of 27-11-1954 and later amending S.R.O.s not held or verified.
- **Evidence:** S-XVOL-002: Army Rules, 1954 (India Code compilation) - r.23(3) caution sentence t — [[page 41]]: r.23(3) second sentence, caution reads 'You are obliged to say anything unless you wish to do so' (word 'not' absent) [OFFICIAL_COMPILATION, RULE]
- **MML anchors (secondary, not proof):** S-MML-005, S-MML-006, S-MML-007
- **Limitations:** Record-to-record comparison covered only records located by the stated regex searches over records_658.jsonl (body + references); records phrased differently may have been missed.; HCE-010 and V9-SC-19 are not primary records of this agent; findings on their own accuracy belong to other agents.; Art 20(3) and any judgment on SoE voluntariness were not checked.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-B-006 (independent-reviewer-B, INDEPENDENT_AGENT): **DISPUTES** — Partly disputed. Detection (records describing the caution differently) is useful, but two premises fail. (1) Logic: EV-016's silence on the caution wording and HCE-010's assertion are not mutually inconsistent; a record that omits a disputed word cannot contradict one that states it. (2) HCE-010's 'invited to make a statement but is not obliged to do so' is substantially supported by undisputed r.23(3) text - the invitation is framed as a questi
> - Orchestrator provisional disposition: REVIEWER_POSITION_ADOPTED_PROVISIONALLY; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Until r.23(3) is authenticated, should HCE-010's 'not obliged' sentence be marked as the MML reading rather than as the rule text?
- Question: Is the voluntariness of an SoE statement independently secured by other law (e.g. Constitution Art 20(3)) such that records may state 'not obliged' without relying on r.23(3)? (Not checked here.)
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 3: F-STAT-001 — HCE-010 — first pass P0 / provisional P0

- **Outcome / evidence state:** CONFLICTING_SOURCES / CONFLICTING; agent: statutory-auditor
- **Record text tested:** records_658.jsonl:line 86: “the accused is invited to make a statement but is not obliged to do so”
- **Finding:** Record states the accused 'is not obliged' to make a statement (r.23(3) caution). The government-hosted compilation prints the caution without 'not'; MML copies print 'not obliged'. Authoritative S.R.O. 484 text not held.
- **Temporal scope:** India Code-hosted annotated Army Rules compilation (undated; latest authority note SRO 258 of 27-11-2002); S.R.O. 484 (1954) and amending S.R.O.s not held; question is the wording of r.23(3) as made in 1954 and as in force today
- **Evidence:** S-STAT-012: Army Rules 1954 r.23(3) caution (India Code annotated compilation) — [[page 41]] r.23(3): '...You are obliged to say anything unless you wish to do so...' [OFFICIAL_COMPILATION, RULE]
- **MML anchors (secondary, not proof):** S-MML-005, S-MML-006, S-MML-007
- **Page-image checks:** PIC-01, PIC-02
- **Limitations:** Did not inspect any page image of the compilation PDF or the MML PDF for the negation; derived text only.; Did not examine judicial treatment of the caution wording.; Unapproved research output; not legal advice; no advisor nominated.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-006 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — CONFLICTING outcome upheld and must remain unresolved. I visually checked the compilation page ([[page 41]] rendered to image): 'not' is absent from the printed caution, so the omission is not a text-extraction artefact; India Code's own TEXT bitstream (line 3552) reads the same (same underlying document, not independent). MML 2.pdf p.152 (image-checked) and both vol 2(AR) .doc copies (L00472, L01383) print 'not obliged'. BLOCKED-type gap justifi
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P0 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Can the custodian (MoD/JAG/Central Secretariat Library/National Archives) supply the authenticated Gazette S.R.O. 484 of 27-11-1954 and every later S.R.O. amending r.23?
- Question: Pending that, should commander-facing content quote the caution at all, or only describe the right to silence with a source-conflict notice?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 4: F-MML-003 — MMLPKT-02 — first pass P0 / provisional P0

- **Outcome / evidence state:** CONFLICTING_SOURCES / CONFLICTING; agent: manual-of-military-law-auditor
- **Record text tested:** MMLPKT-02: “Army Rules 1954 r.23(3) (caution to accused at SoE)”
- **Finding:** Army Rule 23(3) caution: all three MML copies read 'You are not obliged to say anything unless you wish to do so', whereas the India Code compilation reads 'You are obliged to say anything unless you wish to do so'.
- **Temporal scope:** Manual copies undated; India Code compilation retrieved 2026-11-21. Original S.R.O. 484 (27-11-1954) and any amendment to r.23 not examined; conflict persists for all dates.
- **Evidence:** S-MML-102: Army Rules, 1954 (India Code compilation) - r.23 Procedure for taking  — [[page 41]]-[[page 42]]: r.23(1)-(6); r.23(3) caution at [[page 41]] [OFFICIAL_COMPILATION, RULE]
- **Contrary evidence:** S-MML-005: MML 2.pdf - Army Rules r.23 Procedure for taking down the summary of e — PDF pp.151-152 (printed pp.151-152): r.23(1)-(6); r.23(3) caution at p.152 lines 1-3 [USER_SUPPLIED_REFERENCE, MANUAL]; S-MML-006: MML vol 2(AR).doc.doc - Army Rules r.23 (reproduced) — derived lines L00470-L00475; r.23(3) caution at L00472 [USER_SUPPLIED_REFERENCE, MANUAL]; S-MML-007: MML vol 2(AR).doc-1.doc - Army Rules r.23 (reproduced) — derived lines L01377-L01389; r.23(3) caution at L01383 (embedded printed p.352) [USER_SUPPLIED_REFERENCE, MANUAL]
- **MML anchors (secondary, not proof):** S-MML-005, S-MML-006, S-MML-007, S-MML-008
- **Limitations:** MML 'not' reading not confirmed against page images of MML 2.pdf p.152.; No Gazette or Ministry source consulted; MML cannot resolve the conflict.; MML text read only from derived text layers; no page-image check of negations, numerals or dates.; India Code compilation is not the authenticated Gazette/S.R.O.; original notifications and full amendment chain not examined.; Edition/printing date of e

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-016 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Test passed: all three MML locators confirmed ('not obliged'; MML 2 p.152 image-checked); compilation [[page 41]] image-checked without 'not'. Conflict correctly recorded and not resolved; MML notes do not authenticate rule text. P0 retained. r.23(3) remains UNRESOLVED. Limitation: same-model correlation - reviewer and first-pass agent are the same underlying model; India Code compilation copies are bit-identical to the first-pass copies, so agre
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P0 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Obtain and authenticate the Gazette text of S.R.O. 484 dated 27-11-1954 (r.23(3)) and any later amendment before any wording is adopted.
- Question: Pending authentication, what interim wording, if any, may be displayed with a conflict warning?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 5: F-STAT-020 — MMLPKT-02 — first pass P0 / provisional P0

- **Outcome / evidence state:** CONFLICTING_SOURCES / CONFLICTING; agent: statutory-auditor
- **Record text tested:** MMLPKT-02: “Army Rules 1954 r.23(3) (caution to accused at SoE)”
- **Finding:** r.23(3) caution wording conflicts: compilation 'You are obliged to say anything unless you wish to do so'; MML copies 'not obliged'. Not resolved.
- **Temporal scope:** India Code-hosted annotated Army Rules compilation (undated; latest authority note SRO 258 of 27-11-2002); S.R.O. 484 (1954) and amending S.R.O.s not held
- **Evidence:** S-STAT-012: Army Rules 1954 r.23(3) caution (India Code annotated compilation) — [[page 41]] r.23(3): '...You are obliged to say anything unless you wish to do so...' [OFFICIAL_COMPILATION, RULE]
- **MML anchors (secondary, not proof):** S-MML-005, S-MML-006, S-MML-007
- **Page-image checks:** PIC-01
- **Limitations:** No page-image check.; Unapproved research output; not legal advice; no advisor nominated.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-012 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Same evidence as F-STAT-001 review: compilation [[page 41]] visually confirmed to omit 'not'; all three MML copies include it; original S.R.O. 484 (1954) and any amending S.R.O. unobtainable from reachable sources. CONFLICTING, unresolved; P0 retained. Duplicate of F-STAT-001/F-MML-003 at packet level - acceptable but should be cross-linked. Limitation: same-model correlation - reviewer and first-pass agent are the same underlying model; India Co
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P0 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Custodian request for authenticated S.R.O. 484 Gazette scan (see registers/RULE23_3_CUSTODIAN_REQUEST_DRAFT.md).
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 6: F-PROC-019 — HCE-017 — first pass P1 / provisional P0

- **Outcome / evidence state:** DISCREPANCY / SOURCE_VERIFIED; agent: procedure-auditor
- **Record text tested:** records_658.jsonl:line 93: “custody/detention/confinement are not awardable to NCOs; reprimand is not for ranks below NCO.”
- **Finding:** The s.81(4) NCO bar is stated incompletely (omits persons who were NCOs at the time of the offence); s.80 list summary omits forfeiture of good service/good conduct pay.
- **Proposed correction (not applied):** Check s.81(4): clauses (a)-(c) cannot be awarded to a person who is an NCO or was an NCO when the offence was committed; s.81(5): reprimand/severe reprimand not below NCO rank.
- **Temporal scope:** Current consolidation India Code compilation retrieved 2026-11-21; amendment chain and original Gazette not verified (s.81(1) omitted and s.81(4) amended by Act 37 of 1992).
- **Evidence:** S-PROC-001: The Army Act, 1950 (46 of 1950) - India Code consolidated PDF a1950-46 — ss.79-82 at PDF [[page 27]]-[[page 28]] (s.81(1) omitted by Act 37 of 1992 s.5; s.81(4) subs. ibid.; s.80 cl.(j) omitted by Act 37 of 1992 s.4); ss.83-88 at [[page 28]]-[[page 29]]; s.89 at [[page 29]] [OFFICIAL_COMPILATION, STATUTE]
- **MML anchors (secondary, not proof):** S-MML-026, S-MML-027, S-MML-028
- **Page-image checks:** PIC-06
- **Limitations:** Any COAS specification under s.82 not examined.; Research only; not legally approved.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-005 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Test passed: s.81(4) in my India Code copy [[page 28]] bars s.80(a)-(c) for a person who is, or was at the time of the offence, an NCO; letters '(a), (b) and (c)' substituted by Act 37 of 1992 s.5 (Gazette p.2 confirms). s.81(5) and s.82 correctly reported; s.80(f) forfeiture of good service and good conduct pay is indeed missing from the record's list (line 93). Severity change recommended: P1 -> P0. The record affirmatively states the NCO bar i
> - Orchestrator provisional disposition: SEVERITY_RECALIBRATION_PROPOSED; provisional severity P0 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Confirm KB should state s.81(4) with both limbs (present rank and rank at time of offence).
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)


## B. Unresolved statutory / source conflicts and blocked authority

### Item 7: F-STAT-010 — CIV-033 — first pass P1 / provisional P1

- **Outcome / evidence state:** BLOCKED / NOT_FOUND; agent: statutory-auditor
- **Record text tested:** records_658.jsonl:line 492: “Locate current valid Government adjustment rules”
- **Finding:** Text, amendments and current status of the Criminal Courts and Court-Martial (Adjustment of Jurisdiction) Rules 1978 cannot be established: no official copy held.
- **Temporal scope:** Rules of 1978 made under CrPC s.475; status after 1-7-2024 depends on BNSS s.531(2)(b)
- **Evidence:** none
- **MML anchors (secondary, not proof):** S-MML-034
- **Limitations:** Only India Code searched; Gazette unreachable.; Unapproved research output; not legal advice; no advisor nominated.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-008 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — BLOCKED upheld. My India Code searches ('Adjustment of Jurisdiction', 'Criminal Courts and Court-martial', 'S.O. 488') found only the NSG 1987 analogue; archive.org metadata search found no copy of the 1978 Rules. Leads the first pass did not record: MML 2.pdf p.92 and vol 2(AA) L01873 identify the Rules as MHA notification S.O. 488 dated 9 Feb 1978 (manual identity lead only), and a Rajya Sabha record of 3-3-1987 (archive.org mirror of rsdebate.
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Obtain authenticated Gazette copy of the 1978 Adjustment of Jurisdiction Rules and all amendments; confirm no replacement rules were notified under BNSS s.521.
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 8: F-XVOL-007 — CIV-034 — first pass P1 / provisional P2 (provisional)

- **Outcome / evidence state:** CONFLICTING_SOURCES / CONFLICTING; agent: cross-volume-auditor
- **Record text tested:** records_658.jsonl:line 493: “Bharatiya Sakshya Adhiniyam section 1(2) expressly extends the Act to judicial proceedings in or before Courts, including courts-martial.”
- **Finding:** CIV-034 does not mention that Army Act s.133 (India Code consolidation) still provides that the Indian Evidence Act 1872 'shall, subject to the provisions of this Act, apply to all proceedings before a court-martial', while BSA s.1(2) applies the BSA to courts-martial and s.170(1) repeals the IEA. CM-025 and EV-003 expose this cross-reference; CIV-034 refers only to 'Army Act evidence provisions' and cites 'V8-S01|court martial evidence chapter' without a section. Record-level category: legitimate distinction (each record accurately states a different enactment) plus probable gap in CIV-034; the statutory interaction is unresolved.
- **Proposed correction (not applied):** Proposal only: add to CIV-034 'Army Act s.133 as consolidated still names the Indian Evidence Act 1872; the interaction with BSA ss.1(2) and 170 is unresolved pending legal review (see CM-025, EV-003).'
- **Temporal scope:** BSA 2023 India Code consolidation retrieved 2026-11-21; in force 1-7-2024 per compilation footnote (S.O. 849(E) of 23-2-2024 not itself retrieved); Army Act 1950 consolidation retrieved 2026-11-21; amendments after retrieval and General Clauses Act 1897 not checked.
- **Evidence:** S-XVOL-004: Bharatiya Sakshya Adhiniyam, 2023 (Act 47 of 2023) - s.1(2) applicatio — [[page 10]]: s.1(2) 'It applies to all judicial proceedings in or before any Court, including Courts-martial, but not to affidavits ... nor to proceedings before an arbitrator.'; s.1(3) commencement by notification [OFFICIAL_COMPILATION, STATUTE]; S-XVOL-005: Bharatiya Sakshya Adhiniyam, 2023 - s.170 repeal and savings; commence — [[page 51]]: s.170(1) repeals Indian Evidence Act 1872; s.170(2) pending application, trial, inquiry, investigation, proceeding or appeal dealt with under IEA 1872; [[page 10]] footnote 1: in force 1 July 2024 vide S.O. 849(E) dated 23-02-2024 [OFFICIAL_COMPILATION, STATUTE]; S-XVOL-006: The Army Act, 1950 (Act 46 of 1950) - s.133 General rule as to evidenc — [[page 37]]: s.133 'The Indian Evidence Act, 1872 (1 of 1872), shall, subject to the provisions of this Act, apply to all proceedings before a court-martial.' [OFFICIAL_COMPILATION, STATUTE]
- **MML anchors (secondary, not proof):** S-MML-058, S-MML-059, S-MML-063
- **Limitations:** General Clauses Act 1897 text, Gazette amendment search for s.133 and judicial treatment were not checked.; The MML s.133 reproduction (S-MML-058/059) is historical and cited only as anchor.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-B-008 (independent-reviewer-B, INDEPENDENT_AGENT): **DISPUTES** — Texts re-verified (S-REVB-009 Army Act s.133 still names the Indian Evidence Act 1872, p.37; S-REVB-008 BSA s.1(2), s.170(1)). I dispute the CONFLICTING_SOURCES classification and P1 severity. These are not conflicting texts of the same provision; they are two enactments whose interaction the first pass expressly did not check. I retrieved General Clauses Act 1897 s.8(1) from India Code (S-REVB-011): where a Central Act 'repeals and re-enacts, wi
> - Orchestrator provisional disposition: ADVISOR_DECISION_REQUIRED; provisional severity P2 (provisional) (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Does General Clauses Act 1897 s.8 (or any notified adaptation) make Army Act s.133 refer to the BSA from 1-7-2024?
- Question: Does 'subject to the provisions of this Act' in s.133 interact with BSA s.1(2) for matters the Army Act regulates specially?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 9: F-STAT-019 — MMLPKT-01 — first pass P1 / provisional P1

- **Outcome / evidence state:** BLOCKED / SOURCE_LOCATED; agent: statutory-auditor
- **Record text tested:** MMLPKT-01: “Army Rules 1954 r.22 (hearing of charge; r.22(1) proviso)”
- **Finding:** Current r.22 text (incl. r.22(1) proviso and Explanation) is available only from the annotated compilation; enacting and amending S.R.O.s are not held.
- **Temporal scope:** India Code-hosted annotated Army Rules compilation (undated; latest authority note SRO 258 of 27-11-2002); S.R.O. 484 (1954) and amending S.R.O.s not held
- **Evidence:** S-STAT-011: Army Rules 1954 r.22 Hearing of charge (India Code annotated compilati — [[page 37]] r.22(1) and proviso (CoI with r.180 compliance), r.22(2) and proviso; [[page 38]] r.22(3)(a)-(d) and proviso, r.22(4); [[page 39]] Explanation followed by authority note 'SRO No 258 dt 27 Nov 2002' [OFFICIAL_COMPILATION, RULE]
- **MML anchors (secondary, not proof):** S-MML-001, S-MML-003, S-MML-004
- **Limitations:** No Gazette access.; Unapproved research output; not legal advice; no advisor nominated.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-011 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — BLOCKED upheld: no S.R.O. for r.22 is held or available on India Code (item metadata lists only the compilation); egazette unreachable. Partial answer to the finding's open point: MML 2.pdf p.150 attaches 'Inserted by SRO 258/2002' to the Explanation only, and marks the whole r.22 as 'Subs by SRO 17(E), dated 6th December, 1993' - a 1993 instrument the compilation does not mention (vol 2(AR).doc.doc also opens '[22.'). This is manual evidence onl
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Obtain Gazette S.R.O. 484 (1954) and S.R.O. 258 of 27-11-2002 and identify the instrument that inserted the r.22(1) proviso.
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 10: F-STAT-022 — MMLPKT-04 — first pass P1 / provisional P2

- **Outcome / evidence state:** BLOCKED / SOURCE_LOCATED; agent: statutory-auditor
- **Record text tested:** MMLPKT-04: “Army Rules 1954 r.180”
- **Finding:** Current r.180 wording (opening 'Save in the case of a prisoner of war who is still absent') is shown without any amendment authority; amendment chain cannot be established.
- **Temporal scope:** India Code-hosted annotated Army Rules compilation (undated; latest authority note SRO 258 of 27-11-2002); S.R.O. 484 (1954) and amending S.R.O.s not held
- **Evidence:** S-STAT-017: Army Rules 1954 r.180 (India Code annotated compilation) — [[page 196]]-[[page 197]] r.180 (opening words 'Save in the case of a prisoner of war who is still absent'); no amendment authority note printed [OFFICIAL_COMPILATION, RULE]
- **MML anchors (secondary, not proof):** S-MML-014, S-MML-015, S-MML-016
- **Limitations:** No Gazette access.; Unapproved research output; not legal advice; no advisor nominated.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-013 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — BLOCKED outcome upheld only in the narrow sense that S.R.O. 484 and any amending S.R.O. are not held. I dispute the rationale's inference that the prisoner-of-war saving words 'suggest a later amendment': the same words appear in compilation [[page 196]]-[[page 197]], MML 2.pdf p.222, vol 2(AR).doc.doc L01881 and doc-1 L04050, and r.179(3) uses the parallel 'except a prisoner of war who is still absent'; MML 2, which brackets and footnotes amendm
> - Orchestrator provisional disposition: SEVERITY_RECALIBRATION_PROPOSED; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Identify and obtain the S.R.O. that introduced the prisoner-of-war saving in r.180 (if any).
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 11: F-PROC-018 — COI-008 — first pass P2 / provisional P2

- **Outcome / evidence state:** CONFLICTING_SOURCES / CONFLICTING; agent: procedure-auditor
- **Record text tested:** records_658.jsonl:line 38: “Rule 177(3) provides that a CoI may be assembled by the officer in command of a body of troops”
- **Finding:** The corpus India Code compilation prints a different r.177(1)-(2) from the version MML 2 marks as substituted by S.R.O. 8(E) of 23-06-2003; the operative current text of r.177 is unresolved.
- **Temporal scope:** Pre- vs post-23-06-2003 r.177; India Code compilation retrieved 2026-11-21 vs undated MML 2 edition (notes to 2003).
- **Evidence:** S-PROC-007: Army Rules, 1954 - India Code annotated compilation armyrules1954.pdf — r.177(1)-(3) at PDF [[page 194]]; NOTES 1-3 at [[page 194]]-[[page 195]] (editorial) [OFFICIAL_COMPILATION, RULE]
- **MML anchors (secondary, not proof):** S-MML-054, S-MML-056, S-MML-057
- **Limitations:** S.R.O. 8(E) of 23-06-2003 not obtained (gap registered as S-PROC-013).; MML text used as anchor only, not as proof.; Research only; not legally approved.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-004 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Test passed: compilation [[page 194]] r.177(1)-(2) (no presiding-officer clause, no marker) vs MML 2.pdf p.221 bracketed r.177 with fn 'Substituted by SRO 8 (E) dated 23 June, 2003' - quotations accurate; r.177(3) identical in both, so the record's specific claim (line 38) is unaffected. Additional evidence strengthening the conflict: the compilation's amendment markers are demonstrably patchy - it carries the 2002 r.22 Explanation note but no ma
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Obtain S.R.O. 8(E) of 23-06-2003 and confirm current r.177(1)-(2); flag the corpus compilation as possibly stale for r.177.
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)


## C. Other P1 statutory, procedural and manual issues

### Item 12: F-PROC-012 — AFT-011 — first pass P1 / provisional P1

- **Outcome / evidence state:** UNVERIFIED / SOURCE_LOCATED; agent: procedure-auditor
- **Record text tested:** records_658.jsonl:line 372: “Section 22(1)(b) refers to the unanswered-representation case, but publicly reproduced text does not express a complete independent filing formula as clearly as clause (a).”
- **Finding:** s.22(1)(b) as printed has no filing period; the record's refusal to compute a deadline is supported by the compilation, but the authenticated wording and judicial construction are unverified.
- **Temporal scope:** India Code consolidation retrieved 2026-11-21; enacted Gazette wording and any amendment/correction not verified; case law not checked.
- **Evidence:** S-PROC-010: The Armed Forces Tribunal Act, 2007 (55 of 2007) - India Code consolid — s.21(1)-(2) and s.22 (unnumbered opening, clauses (a)-(c), sub-section (2)) at PDF [[page 11]] [OFFICIAL_COMPILATION, STATUTE]; S-PROC-014: Armed Forces Tribunal Act, 2007 (55 of 2007) as published in the Gazet — None [UNCONFIRMED, GAZETTE]
- **Limitations:** Gazette of India text of Act 55 of 2007 not obtained (egazette unreachable).; No AFT/HC/SC judgment construing s.22(1)(b) read.; AFT (Procedure) Rules 2008 text in derived/statutes has no provenance metadata; only noted that its application form declares limitation 'prescribed in section 22'.; Continuing-wrong / pension-arrears limitation doctrine not examined.; Research only; not legally approved

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-003 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — UNVERIFIED outcome upheld, but the BLOCKED premise is weaker than stated: more official text was obtainable. (1) My English India Code copy [[page 11]] confirms s.22 opens without '(1)' and cl.(b) states no filing period. (2) India Code also hosts a Hindi text of the Act (H2007-55.pdf, S-REVA-015) which the first pass did not use: it numbers the section '22. परिसीमा—(1)' (supporting the inference that '(1)' was dropped in the English compilation)
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Does the authenticated Gazette text of s.22(1)(b) include a period (e.g. 'within six months from the date of expiry of the said period')?
- Question: What is the controlling judicial construction of s.22(1)(b) read with s.22(2)?
- Question: What limitation governs s.15 appeals against court-martial?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 13: F-STAT-018 — CIV-008 — first pass P1 / provisional P2

- **Outcome / evidence state:** DISCREPANCY / SOURCE_LOCATED; agent: statutory-auditor
- **Record text tested:** records_658.jsonl:line 467: “A unit CO should not assume that his ordinary command appointment gives an independent section 125 power.”
- **Finding:** Record omits Army Rules r.197A, which prescribes the s.125 officer as the officer commanding the brigade or station (except s.69 cases where death resulted); a unit CO who is the station commander may therefore hold s.125 power.
- **Proposed correction (not applied):** Add: 'AR r.197A: prescribed officer under s.125 is the officer commanding the brigade or station in which the accused is serving, except s.69 cases where death has resulted (then only the s.125-named higher commanders).'
- **Temporal scope:** India Code-hosted annotated Army Rules compilation (undated; latest authority note SRO 258 of 27-11-2002); S.R.O. 484 (1954) and amending S.R.O.s not held
- **Evidence:** S-STAT-020: Army Rules 1954 r.197A Prescribed officer under s.125 (India Code anno — [[page 210]] r.197A [OFFICIAL_COMPILATION, RULE]; S-STAT-004: Army Act 1950 ss.124-127 (India Code) — [[page 36]] s.124; s.125; s.126(1)-(2); s.127 '[Omitted]' by the Army (Amendment) Act, 1992 (37 of 1992), s.11 (w.e.f. 6-9-1992) [OFFICIAL_COMPILATION, STATUTE]
- **MML anchors (secondary, not proof):** S-MML-066
- **Limitations:** r.197A not verified against Gazette.; 1978 Adjustment Rules (record ref 'rule 2(c) historical') not held.; Unapproved research output; not legal advice; no advisor nominated.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-010 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Text test passed: r.197A in my compilation copy [[page 210]] matches the quotation; MML 2.pdf p.227 prints r.197-A identically with no amendment marker; s.125 [[page 36]] names army, army corps, division or independent brigade commanders 'or such other officer as may be prescribed'. However the record (line 467) is not wrong: it already says the choice lies with specified higher commanders 'or another officer duly prescribed', and warns only that
> - Orchestrator provisional disposition: SEVERITY_RECALIBRATION_PROPOSED; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Confirm r.197A text and insertion S.R.O. against Gazette; confirm whether 'station' commander includes a unit CO acting as station commander.
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 14: F-PROC-006 — CM-011 — first pass P1 / provisional P2

- **Outcome / evidence state:** DISCREPANCY / SOURCE_VERIFIED; agent: procedure-auditor
- **Record text tested:** records_658.jsonl:line 138: “Apply the earliest relevant knowledge rule in Section 122(1).”
- **Finding:** The instruction 'Apply the earliest relevant knowledge rule in Section 122(1)' misdescribes the computation structure.
- **Proposed correction (not applied):** Determine which s.122(1) clause applies: (a) date of offence by default; (b) if the offence was not known to the person aggrieved or the competent authority, the first day either of them knew of it (whichever earlier); (c) if the offender was unknown, the first day either knew his identity (whichever earlier).
- **Temporal scope:** Post-Act 37 of 1992 text per India Code compilation retrieved 2026-11-21; amendment chain and original Gazette not verified.
- **Evidence:** S-PROC-002: The Army Act, 1950 (46 of 1950) - India Code consolidated PDF a1950-46 — ss.120-123 at PDF [[page 34]]-[[page 35]]; s.122(1) words subs. by Act 37 of 1992 s.9; s.123(2) words subs. by Act 37 of 1992 s.10 (footnotes 1-2, [[page 35]]) [OFFICIAL_COMPILATION, STATUTE]
- **MML anchors (secondary, not proof):** S-MML-029, S-MML-030, S-MML-065
- **Limitations:** No judgment on s.122(1)(b)/(c) construction read.; Who is the 'authority competent to initiate action' for a given offence not examined.; Research only; not legally approved.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-001 (independent-reviewer-A, INDEPENDENT_AGENT): **DISPUTES** — Test (a)/(b): s.122(1)(a)-(c) re-read in my own India Code download [[page 35]] and in the Act 37 of 1992 Gazette s.9 (Gazette p.2): first-pass quotation and structure are accurate - (b) and (c) are conditional triggers and 'whichever is earlier' operates only within (b)/(c). Dispute is as to characterisation and severity: the record (line 138), read whole, already states that commencement is 'tied to date of offence, knowledge or known identity'
> - Orchestrator provisional disposition: REVIEWER_POSITION_ADOPTED_PROVISIONALLY; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Confirm the computation formula: (a) date of offence by default; (b)/(c) only when their conditions are met, using the earlier of the two persons' knowledge.
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 15: F-PROC-007 — CM-011 — first pass P1 / provisional P1

- **Outcome / evidence state:** DISCREPANCY / SOURCE_VERIFIED; agent: procedure-auditor
- **Record text tested:** records_658.jsonl:line 138: “AA §122(1)–(4)”
- **Finding:** The record omits Army Act s.123(2), a separate limitation for persons who have ceased to be subject to the Act.
- **Proposed correction (not applied):** Add: 'If the accused has ceased to be subject to the Act, also apply AA s.123(2): trial must commence within three years of cessation, excluding periods of absconding/concealment and of any staying injunction or order; not applicable to desertion, fraudulent enrolment or s.37 offences.'
- **Temporal scope:** Post-Act 37 of 1992 text per India Code compilation retrieved 2026-11-21; amendment chain and original Gazette not verified; commencement and transitional effect not verified.
- **Evidence:** S-PROC-002: The Army Act, 1950 (46 of 1950) - India Code consolidated PDF a1950-46 — ss.120-123 at PDF [[page 34]]-[[page 35]]; s.122(1) words subs. by Act 37 of 1992 s.9; s.123(2) words subs. by Act 37 of 1992 s.10 (footnotes 1-2, [[page 35]]) [OFFICIAL_COMPILATION, STATUTE]
- **Limitations:** SC/HC case law on s.123 (e.g. on commencement of trial for retired personnel) not read from official text.; Research only; not legally approved.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-002 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Test passed: s.123(2) and proviso re-read in my India Code download [[page 35]]; substituted words confirmed against the Gazette scan of Act 37 of 1992 s.10 (three years after ceasing to be subject; exclusion of absconding/concealment and of injunction/stay periods incl. day of issue and withdrawal). Proviso (desertion, fraudulent enrolment, s.37 offences; criminal-court jurisdiction unaffected) correctly reported. Record line 138 cites only s.12
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Do s.122 and s.123(2) apply cumulatively to a person who has ceased to be subject to the Act, so that both periods must be satisfied?
- Question: Does the s.123(2) stay/injunction exclusion have any counterpart for persons still subject to the Act?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 16: F-STAT-013 — CM-025 — first pass P1 / provisional P2

- **Outcome / evidence state:** DISCREPANCY / SOURCE_VERIFIED; agent: statutory-auditor
- **Record text tested:** records_658.jsonl:line 152: “India’s replacement evidence statute creates an important transition/savings question that cannot be resolved by silent auto-substitution in an AI assistant.”
- **Finding:** Record frames the s.133/BSA transition but omits that BSA s.1(2) itself applies the Adhiniyam to judicial proceedings before 'Courts-martial', together with s.170 savings and the 1-7-2024 commencement.
- **Proposed correction (not applied):** Add: 'BSA s.1(2) applies the BSA to judicial proceedings before Courts-martial (from 1 July 2024); s.170(2) keeps the IEA for matters pending immediately before that date; Army Act s.133 still names the IEA - JAG to advise on how s.133 is read.'
- **Temporal scope:** BSA commencement 1-7-2024 (India Code footnote; S.O. 849(E) not held); Army Act 'As on 21 July 2025'
- **Evidence:** S-STAT-021: Bharatiya Sakshya Adhiniyam, 2023 (47 of 2023) s.1 application and com — [[page 10]] s.1(2) 'applies to all judicial proceedings in or before any Court, including Courts-martial'; s.1(3) and fn 1 (1-7-2024 vide S.O. 849(E) dated 23-2-2024) [OFFICIAL_COMPILATION, STATUTE]; S-STAT-022: Bharatiya Sakshya Adhiniyam, 2023 s.170 Repeal and savings (India Code — [[page 51]] s.170(1)-(2) [OFFICIAL_COMPILATION, STATUTE]; S-STAT-005: Army Act 1950 s.133 (India Code) — [[page 37]] s.133 'General rule as to evidence' naming 'The Indian Evidence Act, 1872 (1 of 1872)' [OFFICIAL_COMPILATION, STATUTE]
- **Limitations:** General Clauses Act 1897 not held/examined.; No judicial treatment examined.; Unapproved research output; not legal advice; no advisor nominated.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-009 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Text test passed: BSA s.1(2) ('including Courts-martial'), s.1(3) fn (1-7-2024, S.O. 849(E) of 23-2-2024) and s.170(1)-(2) quoted accurately; Army Act s.133 [[page 37]] unamended. Two qualifications. (1) The 'by contrast' framing overstates novelty: IEA s.1 excluded only courts-martial under the British Army Act (44 & 45 Vict. c.58) etc., so the IEA already applied to Army Act 1950 courts-martial; BSA s.1(2) continues rather than introduces appli
> - Orchestrator provisional disposition: SEVERITY_RECALIBRATION_PROPOSED; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Does General Clauses Act 1897 s.8 operate to read Army Act s.133's reference to the IEA as a reference to the BSA from 1-7-2024?
- Question: Is a court-martial a 'trial' or 'proceeding' pending for BSA s.170(2) once convened, or from an earlier stage (charge, summary of evidence)?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 17: F-STAT-006 — HCE-017 — first pass P1 / provisional P1

- **Outcome / evidence state:** DISCREPANCY / SOURCE_LOCATED; agent: statutory-auditor
- **Record text tested:** records_658.jsonl:line 93: “Check ceilings, coexistence of multiple awards, and any notified additional punishments.”
- **Finding:** Record's 'Check ceilings' step omits Army Rules r.192 (prescribed extent), which limits an awarding officer below field rank to 7 days' imprisonment/detention unless empowered by a division-level commander.
- **Proposed correction (not applied):** Add to references and checklist: 'AR r.192 (prescribed extent): officer below field rank - imprisonment/detention max 7 days unless empowered by an officer not below division commander'.
- **Temporal scope:** India Code-hosted annotated Army Rules compilation (undated; latest authority note SRO 258 of 27-11-2002); S.R.O. 484 (1954) and amending S.R.O.s not held
- **Evidence:** S-STAT-019: Army Rules 1954 r.192 Prescribed extent of punishment under s.80 (Indi — [[page 209]] r.192(i)-(ii) [OFFICIAL_COMPILATION, RULE]; S-STAT-001: Army Act 1950 ss.75-82 and s.85 (India Code) — [[page 27]] ss.75-76 '[Omitted]' (Act 37 of 1992, s.2, w.e.f. 6-9-1992), s.79, s.80(a)-(i) & fn 3; [[page 28]] s.81(1) omitted, s.81(2)-(5), s.82; [[page 28]]-[[page 29]] s.85(i)-(ii) & proviso [OFFICIAL_COMPILATION, STATUTE]
- **MML anchors (secondary, not proof):** S-MML-046
- **Page-image checks:** PIC-03
- **Limitations:** r.192 not verified against Gazette.; Unapproved research output; not legal advice; no advisor nominated.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-007 (independent-reviewer-A, INDEPENDENT_AGENT): **RETURN_FOR_EVIDENCE** — Core claim upheld (record line 93 cites only r.22(3)(a)/App III; compilation [[page 209]] r.192 limits an officer below field rank to 7 days' imprisonment/detention unless empowered by a division-level officer). But the evidence base is incomplete and the proposed text would perpetuate a defect: MML 2.pdf p.227 (image-checked) and both vol 2(AR) .doc copies (L02228, L04352) print a r.192 PROVISO - reduction to a lower grade of pay only to the imm
> - Orchestrator provisional disposition: EVIDENCE_SUPPLIED_SUPPLEMENTARY_FINDING; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Confirm r.192 current text and any amendment against authenticated Gazette S.R.O.s.
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 18: F-MML-002 — MMLPKT-01 — first pass P1 / provisional P2

- **Outcome / evidence state:** DISCREPANCY / SOURCE_LOCATED; agent: manual-of-military-law-auditor
- **Record text tested:** MMLPKT-01: “Army Rules 1954 r.22 (hearing of charge; r.22(1) proviso)”
- **Finding:** The two MML vol 2(AR) .doc copies reproduce r.22 without the Explanation (officer other than CO proceeding under s.80) that MML 2.pdf and the India Code compilation carry, and differ in wording from MML 2.pdf in r.22(1)-(2).
- **Proposed correction (not applied):** Proposal only: label the vol 2(AR) .doc r.22 copies as pre-2002 text lacking the Explanation inserted by SRO 258/2002; do not use them as current text of r.22.
- **Temporal scope:** MML texts: undated editions (latest amendment notes seen: MML 2.pdf to SRO 8(E) of 23-06-2003; AR .doc copies to SRO 17(E) of 06-12-1993). Compared with India Code Army Rules compilation retrieved 2026-11-21; amendments after the compilation's last update and original S.R.O. text not verified.
- **Evidence:** S-MML-101: Army Rules, 1954 (India Code compilation) - r.22 Hearing of charge — [[page 37]]-[[page 39]]: r.22(1) with proviso, (2), (3), (4), Explanation ('SRO No 258 dt 27 Nov 2002'), notes [OFFICIAL_COMPILATION, RULE]
- **MML anchors (secondary, not proof):** S-MML-001, S-MML-003, S-MML-004
- **Page-image checks:** PIC-01, PIC-02
- **Limitations:** SRO 17(E) of 1993 and SRO 258 of 2002 not obtained; .doc footnote texts not present in derived text.; MML text read only from derived text layers; no page-image check of negations, numerals or dates.; India Code compilation is not the authenticated Gazette/S.R.O.; original notifications and full amendment chain not examined.; Edition/printing date of each MML file unknown; no access/copyright mark

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-015 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Test passed: MML 2.pdf p.150 has the Explanation (fn 'Inserted by SRO 258/2002'); vol 2(AR).doc.doc L00439-L00451 and doc-1 L01314-L01340 end at r.22(4) with no Explanation; 'call any witness' vs 'call such witness', 'in his discretion' (.doc only) and 'investigating'/'investigation' variants confirmed. Caveat: the proposed label 'pre-2002 text' is an inference - the .doc copies are undated and the missing Explanation could be a transcription omi
> - Orchestrator provisional disposition: SEVERITY_RECALIBRATION_PROPOSED; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Confirm from the Gazette that SRO 258 of 27 Nov 2002 inserted the r.22 Explanation and its exact wording ('shall ... may be complied with').
- Question: Is 'call any witness' (MML 2.pdf) or 'call such witness' (India Code) the authenticated wording of r.22(1) as substituted by SRO 17(E) of 1993?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 19: F-MML-011 — MMLPKT-06 — first pass P1 / provisional P1

- **Outcome / evidence state:** DISCREPANCY / SOURCE_LOCATED; agent: manual-of-military-law-auditor
- **Record text tested:** MMLPKT-06: “Army Act 1950 ss.75-76 (field punishment; omitted)”
- **Finding:** MML vol 2(AA) .doc and .pdf show ss.75-76 merely as 'Omitted' (no authority/date) and their notes to s.80 still describe field punishment as an available summary award.
- **Proposed correction (not applied):** Proposal only: flag vol 2(AA) s.80 notes 6(b)(ii), 9(b) (field-punishment words) and 18 as superseded since 6-9-1992.
- **Temporal scope:** MML texts: undated editions (MML 2.pdf notes Act 37 of 1992 and later material; vol 2(AA) copies cite SROs to 1993). Compared with India Code Army Act compilation retrieved 2026-11-21 (amendment footnotes to Act 37 of 1992 and later); later amendment chain not verified.
- **Evidence:** S-MML-107: The Army Act, 1950 (India Code compilation) - ss.75-76 omission notes — [[page 27]]: ss.75, 76 'Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 2 (w.e.f. 6-9-1992)' [OFFICIAL_COMPILATION, STATUTE]; S-MML-108: The Army Act, 1950 (India Code compilation) - ss.79-82 and s.85 — [[page 27]]-[[page 29]]: s.79, s.80(a)-(i) and footnote 3 (cl.(j) omitted by Act 37 of 1992), s.81(1) omitted, (2)-(5), s.82; s.85 (as substituted by Act 37 of 1992, s.6) at [[page 28]]-[[page 29]] [OFFICIAL_COMPILATION, STATUTE]
- **MML anchors (secondary, not proof):** S-MML-021, S-MML-022, S-MML-023, S-MML-024, S-MML-025
- **Limitations:** MML text read only from derived text layers; no page-image check of negations, numerals or dates.; India Code compilation is not the authenticated Gazette/S.R.O.; original notifications and full amendment chain not examined.; Edition/printing date of each MML file unknown; no access/copyright marking could be visually checked.; Judicial treatment of the provision not examined (outside this agent's

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-017 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Test passed: vol 2(AA).pdf p.78 / .doc L01288-L01290 show ss.75-76 'Omitted' without authority; s.80 note 6(b)(ii) (L01339, pdf p.81) and note 18 cl.(j) (L01366-L01370, pdf p.82) still treat field punishment as available. Current law confirmed on my India Code copy [[page 27]] and the Act 37 of 1992 Gazette (s.2 omits ss.75-76; s.4 omits s.80(j); s.3 amends s.77) - all w.e.f. 6-9-1992. P1 retained (abolished punishment presented as available in c
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Confirm no residual field-punishment power survives (e.g., under s.82 specifications) after Act 37 of 1992.
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 20: F-MML-015 — MMLPKT-08 — first pass P1 / provisional P1

- **Outcome / evidence state:** DISCREPANCY / SOURCE_LOCATED; agent: manual-of-military-law-auditor
- **Record text tested:** MMLPKT-08: “Army Act 1950 s.122 (limitation)”
- **Finding:** MML commentary on limitation (s.122 note 1(a) in all three copies, s.80 note 4(c) in MML 2.pdf, MML 1.doc Part I Ch IV para 14) states the bar as three years from commission of the offence, inconsistent with the post-1992 commencement rules in s.122(1)(b)-(c); vol 2(AA) copies also mis-transcribe s.122(3).
- **Proposed correction (not applied):** Proposal only: mark these limitation notes as pre-1992 commentary; compute limitation from s.122(1)(a)-(c) text only.
- **Temporal scope:** MML texts: undated editions (MML 2.pdf notes Act 37 of 1992 and later material; vol 2(AA) copies cite SROs to 1993). Compared with India Code Army Act compilation retrieved 2026-11-21 (amendment footnotes to Act 37 of 1992 and later); later amendment chain not verified.
- **Evidence:** S-MML-109: The Army Act, 1950 (India Code compilation) - s.122 — [[page 35]]: s.122(1)(a)-(c) (subs. by Act 37 of 1992, s.9), (2)-(4); s.123(2) (subs. by s.10 ibid.) [OFFICIAL_COMPILATION, STATUTE]
- **MML anchors (secondary, not proof):** S-MML-030, S-MML-031, S-MML-032, S-MML-025, S-MML-065
- **Limitations:** MML text read only from derived text layers; no page-image check of negations, numerals or dates.; India Code compilation is not the authenticated Gazette/S.R.O.; original notifications and full amendment chain not examined.; Edition/printing date of each MML file unknown; no access/copyright marking could be visually checked.; Judicial treatment of the provision not examined (outside this agent's

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-018 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Test passed: MML 2 p.90 note 1(a), vol 2(AA) L01837, MML 2 p.64 note 4(c) and MML 1 L00191 state a date-of-commission rule; vol 2(AA) L01834 'in adding arrest'; MML 1 L00194 'six months' for s.123 versus three years substituted by Act 37 of 1992 s.10 (Gazette p.3). Precision point: note 1(a) is accurate for the default s.122(1)(a) case and is 'incomplete' rather than 'inconsistent' for (b)/(c); 'mutiny' is a narrower paraphrase of 's.37 offences'
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Which Regulations for the Army paragraph currently defines 'exemplary manner' for s.122(4)?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 21: F-MML-017 — MMLPKT-09 — first pass P1 / provisional P2

- **Outcome / evidence state:** DISCREPANCY / SOURCE_LOCATED; agent: manual-of-military-law-auditor
- **Record text tested:** MMLPKT-09: “Army Act 1950 ss.125-126 (choice of forum)”
- **Finding:** MML commentary to s.125 is defective or dated: vol 2(AA) copies cite the prescribed-officer rule as 'AR 179-A' and truncate note 2; all copies describe the magistrate-notice procedure by reference to the Cr PC 1973 and the 1978 Adjustment Rules.
- **Proposed correction (not applied):** Proposal only: correct the cross-reference to AR 197A in the vol 2(AA) note and tag the Cr PC/1978-rules note as pre-BNSS commentary.
- **Temporal scope:** MML texts: undated editions (MML 2.pdf notes Act 37 of 1992 and later material; vol 2(AA) copies cite SROs to 1993). Compared with India Code Army Act compilation retrieved 2026-11-21 (amendment footnotes to Act 37 of 1992 and later); later amendment chain not verified. BNSS compilation retrieved 2026-11-21; status of the 1978 Adjustment Rules after 1-7-2024 not verified.
- **Evidence:** S-MML-106: Army Rules, 1954 (India Code compilation) - r.197A Prescribed Officer  — [[page 210]]: r.197A [OFFICIAL_COMPILATION, RULE]; S-MML-112: The Bharatiya Nagarik Suraksha Sanhita, 2023 (India Code compilation)  — [[page 172]]: s.521 'Delivery to commanding officers of persons liable to be tried by Court-martial' [OFFICIAL_COMPILATION, STATUTE]
- **MML anchors (secondary, not proof):** S-MML-034, S-MML-036, S-MML-038
- **Limitations:** MML text read only from derived text layers; no page-image check of negations, numerals or dates.; India Code compilation is not the authenticated Gazette/S.R.O.; original notifications and full amendment chain not examined.; Edition/printing date of each MML file unknown; no access/copyright marking could be visually checked.; Judicial treatment of the provision not examined (outside this agent's

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-019 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Test passed: vol 2(AA).pdf p.115 / .doc L01872 'AR 179-A' (MML 2 p.92 'AR 197.A'; r.197A at compilation [[page 210]]); note 2 begins mid-sentence ('2 he is liable...'); all copies cite Cr PC 1973 and MHA S.O. 488 of 9 Feb 1978; BNSS s.521 confirmed (it begins on page 171, before the [[page 172]] marker - minor pinpoint correction). Additional gap: none of the manual copies reflects the 1986 amendment (S.O. 4010 of 6-12-1986) to the 1978 Rules. Th
> - Orchestrator provisional disposition: SEVERITY_RECALIBRATION_PROPOSED; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Have the Criminal Courts and Court-Martial (Adjustment of Jurisdiction) Rules, 1978 been re-made or adapted under BNSS s.521?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 22: F-MML-019 — MMLPKT-10 — first pass P1 / provisional P1 (dead s.127 references: P2)

- **Outcome / evidence state:** DISCREPANCY / SOURCE_LOCATED; agent: manual-of-military-law-auditor
- **Record text tested:** MMLPKT-10: “Army Act 1950 s.127 (successive trials; omitted)”
- **Finding:** MML vol 2(AA) copies show s.127 only as 'Omitted' (no authority/date) and their notes still rely on s.127 as live: s.21 note (a) says Art 20(2) is 'abrogated by AA.s.127', and s.121 note 6 says a court-martialled person can be tried again by a criminal court, 'see AA.s.127 and notes'.
- **Proposed correction (not applied):** Proposal only: tag vol 2(AA) s.21 note (a) and s.121 note 6 as relying on omitted s.127.
- **Temporal scope:** MML texts: undated editions (MML 2.pdf notes Act 37 of 1992 and later material; vol 2(AA) copies cite SROs to 1993). Compared with India Code Army Act compilation retrieved 2026-11-21 (amendment footnotes to Act 37 of 1992 and later); later amendment chain not verified.
- **Evidence:** S-MML-110: The Army Act, 1950 (India Code compilation) - ss.125-127 — [[page 36]]: s.125, s.126(1)-(2), s.127 'Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 11 (w.e.f. 6-9-1992)' [OFFICIAL_COMPILATION, STATUTE]
- **MML anchors (secondary, not proof):** S-MML-040, S-MML-041, S-MML-042, S-MML-043, S-MML-044
- **Page-image checks:** PIC-05
- **Limitations:** MML text read only from derived text layers; no page-image check of negations, numerals or dates.; India Code compilation is not the authenticated Gazette/S.R.O.; original notifications and full amendment chain not examined.; Edition/printing date of each MML file unknown; no access/copyright marking could be visually checked.; Judicial treatment of the provision not examined (outside this agent's

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-020 (independent-reviewer-A, INDEPENDENT_AGENT): **DISPUTES** — Locators and quotations confirmed (vol 2(AA) L00333/pdf p.15; L01826/pdf p.111; MML 2 p.12 fn 'Omittted by Act No. 37 of 1992'; MML 2 p.89 note 6; s.127 omitted by Act 37 of 1992 s.11, Gazette p.3). Dispute on characterisation: enacted s.121 ([[page 35]]) bars a second trial 'by a court-martial or dealt with under the said sections' only - it says nothing about criminal courts. vol 2(AA) s.121 note 6's main proposition ('merely prohibits a second
> - Orchestrator provisional disposition: SPLIT_RESCOPED; provisional severity P1 (dead s.127 references: P2) (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: After omission of s.127 (6-9-1992), may a criminal court try a person already tried by court-martial for the same offence? Identify controlling authority.
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 23: F-MML-020 — MMLPKT-11 — first pass P1 / provisional P1

- **Outcome / evidence state:** DISCREPANCY / SOURCE_LOCATED; agent: manual-of-military-law-auditor
- **Record text tested:** MMLPKT-11: “MML Part I Ch. II paras 13-14 (field punishment; summary punishments)”
- **Finding:** MML 1.doc Part I Ch II para 13 describes field punishment under AA s.75 as an available court-martial punishment; para 14 describes s.85 as permitting a CO to award a JCO only stoppages.
- **Proposed correction (not applied):** Proposal only: mark MML 1.doc Ch II para 13 as historical (pre-6-9-1992) and para 14's s.85 sentence as incomplete after Act 37 of 1992.
- **Temporal scope:** MML texts: undated editions (MML 2.pdf notes Act 37 of 1992 and later material; vol 2(AA) copies cite SROs to 1993). Compared with India Code Army Act compilation retrieved 2026-11-21 (amendment footnotes to Act 37 of 1992 and later); later amendment chain not verified. MML 1.doc contains no dated amendment references.
- **Evidence:** S-MML-107: The Army Act, 1950 (India Code compilation) - ss.75-76 omission notes — [[page 27]]: ss.75, 76 'Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 2 (w.e.f. 6-9-1992)' [OFFICIAL_COMPILATION, STATUTE]; S-MML-108: The Army Act, 1950 (India Code compilation) - ss.79-82 and s.85 — [[page 27]]-[[page 29]]: s.79, s.80(a)-(i) and footnote 3 (cl.(j) omitted by Act 37 of 1992), s.81(1) omitted, (2)-(5), s.82; s.85 (as substituted by Act 37 of 1992, s.6) at [[page 28]]-[[page 29]] [OFFICIAL_COMPILATION, STATUTE]
- **MML anchors (secondary, not proof):** S-MML-045, S-MML-046
- **Limitations:** MML text read only from derived text layers; no page-image check of negations, numerals or dates.; India Code compilation is not the authenticated Gazette/S.R.O.; original notifications and full amendment chain not examined.; Edition/printing date of each MML file unknown; no access/copyright marking could be visually checked.; Judicial treatment of the provision not examined (outside this agent's

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-021 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Test passed: MML 1 L00041 (para 13) presents s.75 field punishment and ARs 172-176 as current; L00043 (para 14) describes s.85 JCO punishment as stoppages; current s.85 (India Code [[page 28]]-[[page 29]]) and Act 37 of 1992 s.6 (Gazette p.2) add severe reprimand/reprimand with the 'below the rank of Colonel' proviso. Additional outdated item not captured: para 12 (L00039) still says a WO/NCO sentenced to 'dismissal or field punishment' is deemed
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 24: F-STAT-029 — MMLPKT-11 — first pass P1 / provisional P1

- **Outcome / evidence state:** DISCREPANCY / SOURCE_LOCATED; agent: statutory-auditor
- **Record text tested:** MMLPKT-11: “MML Part I Ch. II paras 13-14 (field punishment; summary punishments)”
- **Finding:** MML 1 Part I Ch II para 13 describes field punishment under AA s.75 and ARs 172-176 as current; para 14 describes JCO summary punishment under s.85 as stoppages only. Both are outdated against current law.
- **Proposed correction (not applied):** Tag MML 1 Part I Ch II paras 13-14 as historical (pre-1992) commentary; do not use for current field/summary punishment powers.
- **Temporal scope:** Current law from 6-9-1992 (Act provisions, Gazette-verified) and 6-12-1993 (rr.172-176 cancellation, compilation only); MML 1 edition undated
- **Evidence:** S-STAT-008: The Army (Amendment) Act, 1992 (No. 37 of 1992), Gazette of India Extr — Gazette pp.1-4: preamble (assent 6-9-1992); s.2 (ss.75-76 omitted); s.3 (s.77); s.4 (s.80 cl.(j) omitted); s.5 (s.81(1) omitted; s.81(4) substituted); s.6 (s.85 substituted); s.9 (s.122(1) substituted); s.10 (s.123(2)); s.11 (s.127 omitted) [ORIGINAL_OFFICIAL, GAZETTE]; S-STAT-001: Army Act 1950 ss.75-82 and s.85 (India Code) — [[page 27]] ss.75-76 '[Omitted]' (Act 37 of 1992, s.2, w.e.f. 6-9-1992), s.79, s.80(a)-(i) & fn 3; [[page 28]] s.81(1) omitted, s.81(2)-(5), s.82; [[page 28]]-[[page 29]] s.85(i)-(ii) & proviso [OFFICIAL_COMPILATION, STATUTE]; S-STAT-016: Army Rules 1954 rr.172-176 (India Code annotated compilation) — [[page 194]] '172 to 176. Cancelled vide SRO 17E dt 06 Dec 93.' [OFFICIAL_COMPILATION, RULE]; S-STAT-019: Army Rules 1954 r.192 Prescribed extent of punishment under s.80 (Indi — [[page 209]] r.192(i)-(ii) [OFFICIAL_COMPILATION, RULE]
- **MML anchors (secondary, not proof):** S-MML-045, S-MML-046
- **Limitations:** Verification state held at SOURCE_LOCATED because the rr.172-176 limb rests on the unauthenticated compilation; the Act limbs are Gazette-verified.; MML 1 edition/date unknown.; Unapproved research output; not legal advice; no advisor nominated.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-A-014 (independent-reviewer-A, INDEPENDENT_AGENT): **SUPPORTS** — Test passed on my own Gazette download of Act 37 of 1992 (s.2 omits ss.75-76; s.6 substitutes s.85 incl. proviso 'below the rank of Colonel'; assent 6-9-1992, no separate commencement clause) and India Code [[page 27]]-[[page 29]]; compilation [[page 194]] shows rr.172-176 cancelled vide SRO 17E 1993 (S.R.O. not held). Nuance: MML 1 para 14 does not say 'only'; but the Gazette s.6 replaced the words 'and award the punishment ... made good', so pr
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Confirm via S.R.O. 17(E) of 6-12-1993 that ARs 172-176 were cancelled.
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 25: F-MML-007 — MMLPKT-04 — first pass P2 / provisional P2

- **Outcome / evidence state:** DISCREPANCY / SOURCE_LOCATED; agent: manual-of-military-law-auditor
- **Record text tested:** MMLPKT-04: “Army Rules 1954 r.180”
- **Finding:** All three MML copies read 'producing any witnesses in defence of his character or military reputation'; the India Code compilation reads 'character and military reputation' in that limb.
- **Temporal scope:** MML texts: undated editions (latest amendment notes seen: MML 2.pdf to SRO 8(E) of 23-06-2003; AR .doc copies to SRO 17(E) of 06-12-1993). Compared with India Code Army Rules compilation retrieved 2026-11-21; amendments after the compilation's last update and original S.R.O. text not verified.
- **Evidence:** S-MML-104: Army Rules, 1954 (India Code compilation) - r.180 — [[page 196]]-[[page 197]]: r.180 and NOTE [OFFICIAL_COMPILATION, RULE]
- **MML anchors (secondary, not proof):** S-MML-014, S-MML-015, S-MML-016
- **Limitations:** MML text read only from derived text layers; no page-image check of negations, numerals or dates.; India Code compilation is not the authenticated Gazette/S.R.O.; original notifications and full amendment chain not examined.; Edition/printing date of each MML file unknown; no access/copyright marking could be visually checked.; Judicial treatment of the provision not examined (outside this agent's

> **Independent review and disposition — technical challenge, NOT legal approval**
> - No independent review recorded.
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Confirm authenticated wording of r.180 defence-witness limb ('or' vs 'and').
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)


## D. Judicial holdings and later treatment

### Item 26: F-JUD-021 — DCLR-SC-2013-N08 — first pass P1 / provisional P1 (evidence now official)

- **Outcome / evidence state:** UNVERIFIED / SOURCE_LOCATED; agent: judgment-auditor
- **Record text tested:** cases_53.jsonl:line 19: “NOT_EXHAUSTIVELY_CHECKED”
- **Finding:** Later treatment: Dharamvir followed in Rajbir Singh (2015, verified); considered in Union of India v Col. NC Isaac, 2026 INSC 993 (secondary copy only) without being overruled; the row records no specific treatment.
- **Temporal scope:** Treatment checked to 2026-09-15 (Isaac) on discovery basis only.
- **Evidence:** S-JUD-004: Union of India & Anr. v. Rajbir Singh, Civil Appeal No. 2904 of 2011 w — Para 2 (AFT orders under appeal, PDF p.2); para 3 Union submissions (pp.2-3); para 4 respondents' submissions citing Dharamvir Singh (2013) 7 SCC 316 (p.4); paras 7-10 Regulation 173 and Entitlement Rules 1982 rr.5, 9, 14 (pp.7-9); para 13 quoting Dharamvir paras 29.1-29.7 (p.14-15); para 14 (pp.15-16); para 15 court's statement of legal position (pp.17-18); para 16 application (p.19); para 17 appeals dismissed (p.20); date February 13, 2015. [OFFICIAL_COURT_ARCHIVE, JUDGMENT]; S-JUD-008: Union of India & Ors. v. Col. NC Isaac (Retd.), 2026 INSC 993 (with co — Copy pages: para 15 AG submission on Dharamvir and 2008 Rules (p.52); paras 15.1-15.7 summary of Dharamvir (pp.52-58); para 16.3 Rajbir described as following Dharamvir (pp.60-61); para 18.3 AG submission that Dharamvir cannot be mechanically applied to 2008 Rules (p.66); para 19.4, 19.6 respondents' submissions (pp.68-69); Analysis paras 30.7 (p.86), 33-35 (pp.90-91); Conclusion para 39(i)-(iii) (p.93); date September 15, 2026 (p.93). [SECONDARY, SECONDARY]
- **Limitations:** 2026 INSC 993 official PDF not obtained.; Other cited later cases (Angad Singh Titaria (2015) - Air Force; Manjeet Singh (2015); Bijender Singh (2025); Rajumon T.M. (2025)) not obtained or read.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-B-004 (independent-reviewer-B, INDEPENDENT_AGENT): **SUPPORTS** — Upheld; status can be upgraded. With the official Isaac PDF (S-REVB-001), the first pass's reading holds: paras 15.1-15.7 (pp.52-59) are the Court's account of Dharamvir in Part III; para 15 opens with the AG's submission; 18.3 (AG) and 19.4/19.6 (respondents) are in Part IV 'Party Submissions'; the analysis (30.7, 33-35) and conclusion (39) do not overrule Dharamvir but (i) treat ER 2008 as substantially reproducing the 1982 scheme, (ii) apply t
> - Orchestrator provisional disposition: SEVERITY_RECALIBRATION_PROPOSED; provisional severity P1 (evidence now official) (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: After obtaining the official 2026 INSC 993 text: type the edge Isaac->Dharamvir as 'distinguishes' (2008 Rules context) or leave as 'cites'?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 27: F-JUD-017 — DCLR-SC-2023-009 — first pass P1 / provisional P1

- **Outcome / evidence state:** DISCREPANCY / SOURCE_VERIFIED; agent: judgment-auditor
- **Record text tested:** cases_53.jsonl:line 9: “11–16 (jurisdiction discussion; confirm on official copy)”
- **Finding:** The row's pinpoint (paras 11-16) points to counsel's submissions, and its holding field omits the ratio that Shri Kant Sharma (2015) does not lay down the correct law and that there is no per se restriction on Art 226 review of AFT decisions.
- **Proposed correction (not applied):** pinpoint_paragraphs: '24–32 (Court's observations and conclusion; paras 4–23 are submissions)'. holding: 'Article 226 judicial review of AFT decisions is not per se barred; Major General Shri Kant Sharma (2015) 6 SCC 773 does not lay down the correct law, being in conflict with L. Chandra Kumar, S.N. Mukherjee and Rojer Mathew; Art 227 superintendence is distinct; High Courts exercise self-restraint and do not act as a second appeal on facts.'
- **Temporal scope:** Decision 2023-03-21; later treatment not reviewed.
- **Evidence:** S-JUD-002: Union of India & Ors. v. Parashotam Dass, Civil Appeal No. 447 of 2023 — Private-party submissions paras 4-15 (PDF pp.3-10, para 11 at p.7); Union/JAG submissions paras 16-23 (from p.11); 'Our observations' paras 24-31 (para 24 p.16, 25 p.17, 26 p.18, 30 p.21); 'Conclusion' para 32 (p.22: Shri Kant Sharma 'does not lay down the correct law'); individual dispositions para 33 I-IV; paras 34-35. [OFFICIAL_COURT_ARCHIVE, JUDGMENT]
- **Limitations:** Later judicial treatment searched only via targeted web discovery and the official judgments listed; absence of found treatment is not proof of none.; Shri Kant Sharma (2015) text not obtained.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-B-003 (independent-reviewer-B, INDEPENDENT_AGENT): **SUPPORTS** — Upheld on the official PDF (S-REVB-004, same bytes as S-JUD-002). Identity confirmed (C.A. 447/2023 etc.; 21-03-2023; Kaul, Oka, Nagarathna JJ.; Reportable). The row's pinpoint '11-16' falls in 'Submissions on behalf of the private parties' (paras 4-15) and the start of 'The pleas of Union of India and JAG Branch' (16-23): a real misattribution risk on forum/remedy. Para 32 (Conclusion, p.22) states Shri Kant Sharma 'does not lay down the correct
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Approve correcting the pinpoint and holding fields; should the relation Parashotam Dass -> Shri Kant Sharma be typed 'overrules' (three-judge bench declaring a two-judge decision not good law) for the relations graph?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 28: F-JUD-005 — PEN-043 — first pass P1 / provisional P1 (evidence now official: 2026 INSC 993 sha 3f49a314…)

- **Outcome / evidence state:** UNVERIFIED / SOURCE_LOCATED; agent: judgment-auditor
- **Record text tested:** records_658.jsonl:line 308: “Do not announce a blanket presumption for all 2023 claims”
- **Finding:** The record frames the law as 'earlier entitlement-rule regime' versus '2023 claims' and omits the Entitlement Rules 2008 period and the September 2026 SC decision in Union of India v Col. NC Isaac (2026 INSC 993).
- **Temporal scope:** Isaac decided 2026-09-15 (as printed on secondary copy); concerns Entitlement Rules 2008; Entitlement Rules 2023 not assessed.
- **Evidence:** S-JUD-008: Union of India & Ors. v. Col. NC Isaac (Retd.), 2026 INSC 993 (with co — Copy pages: para 15 AG submission on Dharamvir and 2008 Rules (p.52); paras 15.1-15.7 summary of Dharamvir (pp.52-58); para 16.3 Rajbir described as following Dharamvir (pp.60-61); para 18.3 AG submission that Dharamvir cannot be mechanically applied to 2008 Rules (p.66); para 19.4, 19.6 respondents' submissions (pp.68-69); Analysis paras 30.7 (p.86), 33-35 (pp.90-91); Conclusion para 39(i)-(iii) (p.93); date September 15, 2026 (p.93). [SECONDARY, SECONDARY]
- **Limitations:** Official text of 2026 INSC 993 not obtained (official URL returned 0 bytes).; Entitlement Rules 2008 and 2023 texts not obtained (MoD/egazette unreachable).

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-B-001 (independent-reviewer-B, INDEPENDENT_AGENT): **SUPPORTS** — Upheld on the official text. I downloaded 2026 INSC 993 from api.sci.gov.in (S-REVB-001, sha256 3f49a314...4653, 93 pp.); it is byte-identical to the LiveLaw copy the first pass used (S-JUD-008), so the first pass's paragraph and page pinpoints (30.7 pp.86-87; 33-35 pp.90-91; 39 pp.92-93) are correct for the official copy and the 'secondary only' limitation no longer applies. Holding vs submission: 30.7, 33, 34, 35 are in Part V 'Analysis' and 39
> - Orchestrator provisional disposition: SEVERITY_RECALIBRATION_PROPOSED; provisional severity P1 (evidence now official: 2026 INSC 993 sha 3f49a314…) (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Obtain the official sci.gov.in PDF of 2026 INSC 993 and confirm paras 30.7, 33-35 and 39 before any KB wording change.
- Question: Which Entitlement Rules (1982, 2008 or 2023) govern by date of discharge/claim, and should the record add the 2008 tier and Isaac's 15-year Rule 7 proviso?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 29: F-JUD-007 — PEN-J-01 — first pass P1 / provisional P1 (evidence now official)

- **Outcome / evidence state:** UNVERIFIED / SOURCE_LOCATED; agent: judgment-auditor
- **Record text tested:** records_658.jsonl:line 355: “Later treatment / limitation: Do not automatically apply to ER 2023 claim; read N S Yadav (2019) and medical context.”
- **Finding:** The later-treatment note points only to N S Yadav (2019) and 'ER 2023'; it omits Rajbir Singh (2015, followed Dharamvir) and Col. NC Isaac (2026 INSC 993) on the 2008 Rules.
- **Proposed correction (not applied):** Later treatment: followed in Union of India v Rajbir Singh (2015) paras 13-16 [verified]; Union of India v Col. NC Isaac, 2026 INSC 993 (2008 Rules substantially reproduce the 1982 scheme; Rule 7 fifteen-year proviso; mechanical reliance on Dharamvir may be revisited) [official text pending]. Do not automatically apply to claims under later Entitlement Rules without checking the governing version.
- **Temporal scope:** Treatment checked to 2026-09-15 (Isaac, secondary copy). Entitlement Rules 2023 not examined.
- **Evidence:** S-JUD-004: Union of India & Anr. v. Rajbir Singh, Civil Appeal No. 2904 of 2011 w — Para 2 (AFT orders under appeal, PDF p.2); para 3 Union submissions (pp.2-3); para 4 respondents' submissions citing Dharamvir Singh (2013) 7 SCC 316 (p.4); paras 7-10 Regulation 173 and Entitlement Rules 1982 rr.5, 9, 14 (pp.7-9); para 13 quoting Dharamvir paras 29.1-29.7 (p.14-15); para 14 (pp.15-16); para 15 court's statement of legal position (pp.17-18); para 16 application (p.19); para 17 appeals dismissed (p.20); date February 13, 2015. [OFFICIAL_COURT_ARCHIVE, JUDGMENT]; S-JUD-008: Union of India & Ors. v. Col. NC Isaac (Retd.), 2026 INSC 993 (with co — Copy pages: para 15 AG submission on Dharamvir and 2008 Rules (p.52); paras 15.1-15.7 summary of Dharamvir (pp.52-58); para 16.3 Rajbir described as following Dharamvir (pp.60-61); para 18.3 AG submission that Dharamvir cannot be mechanically applied to 2008 Rules (p.66); para 19.4, 19.6 respondents' submissions (pp.68-69); Analysis paras 30.7 (p.86), 33-35 (pp.90-91); Conclusion para 39(i)-(iii) (p.93); date September 15, 2026 (p.93). [SECONDARY, SECONDARY]
- **Limitations:** 2026 INSC 993 official PDF not obtained.; N S Yadav (2019) not obtained.; Later judicial treatment searched only via targeted web discovery and the official judgments listed; absence of found treatment is not proof of none.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-B-002 (independent-reviewer-B, INDEPENDENT_AGENT): **SUPPORTS** — Upheld, with one addition. Official Isaac PDF (S-REVB-001) confirms the first pass's critical distinction: para 18.3 ('Dharamvir ... cannot be mechanically applied to cases governed by the Entitlement Rules 2008') sits in Part IV.A 'Arguments advanced by Ld. Attorney General' (p.66), and 19.6 ('Dharamvir ... still holds the correct position') in Part IV.B respondents' submissions (p.70). The Court in 39(ii) expressly adopts only the AG's Medical 
> - Orchestrator provisional disposition: SEVERITY_RECALIBRATION_PROPOSED; provisional severity P1 (evidence now official) (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Confirm on the official 2026 INSC 993 text that the Court did not itself adopt the AG's para 18.3 propositions beyond para 39(ii).
- Question: Should the case-law relation be recorded as 'follows' (Rajbir->Dharamvir, verified) and 'distinguishes/limits' (Isaac->Dharamvir, pending) rather than 'overruled'?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)


## E. Cross-volume consistency

### Item 30: F-XVOL-009 — AFT-004 — first pass P1 / provisional P2

- **Outcome / evidence state:** DISCREPANCY / SOURCE_VERIFIED; agent: cross-volume-auditor
- **Record text tested:** records_658.jsonl:line 365: “Do not force a trial appeal into a generic service-law cause of action.”
- **Finding:** AFT-004 frames s.14 and s.15 as alternative routes ('Do not force a trial appeal into a generic service-law cause of action'), and KB-022, ADM-024, AFT-003 and CM-036 mention only the SCM exclusion from 'service matters'. None of these records states that s.3(o) expressly INCLUDES '(iii) summary disposal and trials where the punishment of dismissal is awarded' and, by the exception to exclusion (iv), SCMs awarding dismissal or imprisonment over three months. For AFT-004's own example (soldier dismissed by SCM) the statutory text places the matter within 'service matters' under s.14 as well as within s.15. Category: legitimate distinction / probable gap.
- **Proposed correction (not applied):** Proposal only: add 'Note: s.3(o)(iii) includes summary disposals and trials awarding dismissal within service matters, and exclusion (iv) carves back SCMs awarding dismissal or imprisonment over three months; the relationship between a s.14 application and a s.15 appeal for such cases requires legal review.'
- **Temporal scope:** AFT Act 2007 India Code consolidation retrieved 2026-11-21 (corpus status 'amended'; amendment chain not verified); judicial treatment after 2023 not verified.
- **Evidence:** S-XVOL-007: Armed Forces Tribunal Act, 2007 (Act 55 of 2007) - s.3(f) 'court-marti — [[page 6]]: s.3(f) definition of court-martial; s.3(o) inclusions (i)-(iv) incl. (iii) 'summary disposal and trials where the punishment of dismissal is awarded'; exclusions (i)-(iv) incl. (iv) 'summary court-martial except where the punishment is of dismissal or imprisonment for more than three months' [OFFICIAL_COMPILATION, STATUTE]; S-XVOL-008: Armed Forces Tribunal Act, 2007 - s.14 jurisdiction in service matters — [[page 8]]-[[page 9]]: s.14(1) jurisdiction in relation to all service matters; s.14(2) application by person aggrieved by order pertaining to any service matter; s.14(4)-(5) [OFFICIAL_COMPILATION, STATUTE]; S-XVOL-009: Armed Forces Tribunal Act, 2007 - s.15 appeal against court-martial — [[page 9]]-[[page 10]]: s.15(1)-(2) appeal against any order, decision, finding or sentence passed by a court-martial; s.15(3) bail with death/life proviso; s.15(4)-(5) allowing appeal; s.15(6)(a)-(f) incl. (c) enhancement with hearing proviso [OFFICIAL_COMPILATION, STATUTE]
- **Limitations:** No AFT, High Court or Supreme Court decision on the s.14/s.15 interface was retrieved (aftdelhi.nic.in unreachable; judgments not searched).; Record-to-record comparison covered only records located by the stated regex searches over records_658.jsonl (body + references); records phrased differently may have been missed.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-B-009 (independent-reviewer-B, INDEPENDENT_AGENT): **SUPPORTS** — Textual premise upheld; severity disputed. My copy (S-REVB-010, p.6) confirms s.3(o) includes '(iii) summary disposal and trials where the punishment of dismissal is awarded' and excludes '(iv) summary court-martial except where the punishment is of dismissal or imprisonment for more than three months'; s.15(1)-(2) covers 'any order, decision, finding or sentence passed by a court-martial' (p.9). So for AFT-004's own example a s.14 route is textu
> - Orchestrator provisional disposition: SEVERITY_RECALIBRATION_PROPOSED; provisional severity P2 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: For a court-martial sentence of dismissal, does an applicant proceed under s.14 (service matter by virtue of s.3(o)(iii)), s.15, or either?
- Question: Should KB-022/ADM-024/AFT-003 be harmonised to state the s.3(o)(iii) inclusion alongside the exclusions?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 31: F-XVOL-010 — AFT-004 — first pass P1 / provisional P1

- **Outcome / evidence state:** UNVERIFIED / SOURCE_LOCATED; agent: cross-volume-auditor
- **Record text tested:** records_658.jsonl:line 365: “Example: A soldier dismissed by a SCM must receive a distinct jurisdiction analysis under ss3(o),14 and 15.”
- **Finding:** The SCM-route propositions across Volume VII and other volumes (AFT-004 example, AFT-005, V7-SC-05, V7-JD-05, V7-WF-02, V7-CL-01, CM-SC-16, CM-036, KB-022, ADM-024) are mutually consistent in treating SCM forum questions as litigation-sensitive; no record found makes a flat 'no AFT remedy against SCM' claim. The statutory text supports that s.3(o)(iv) limits only the 'service matters' definition and that s.15 contains no express SCM exclusion, but the judicial treatment relied on (Nk Santosh Lohar, P&H HC, 2023:PHHC:127834) was not retrieved, so the proposition that s.15 independently reaches SCMs remains unverified.
- **Temporal scope:** AFT Act 2007 India Code consolidation retrieved 2026-11-21 (corpus status 'amended'; amendment chain not verified); judicial treatment after 2023 not verified.
- **Evidence:** S-XVOL-007: Armed Forces Tribunal Act, 2007 (Act 55 of 2007) - s.3(f) 'court-marti — [[page 6]]: s.3(f) definition of court-martial; s.3(o) inclusions (i)-(iv) incl. (iii) 'summary disposal and trials where the punishment of dismissal is awarded'; exclusions (i)-(iv) incl. (iv) 'summary court-martial except where the punishment is of dismissal or imprisonment for more than three months' [OFFICIAL_COMPILATION, STATUTE]; S-XVOL-009: Armed Forces Tribunal Act, 2007 - s.15 appeal against court-martial — [[page 9]]-[[page 10]]: s.15(1)-(2) appeal against any order, decision, finding or sentence passed by a court-martial; s.15(3) bail with death/life proviso; s.15(4)-(5) allowing appeal; s.15(6)(a)-(f) incl. (c) enhancement with hearing proviso [OFFICIAL_COMPILATION, STATUTE]
- **Limitations:** Nk Santosh Lohar v Union of India and any subsequent treatment were not retrieved or read; the citation is taken from V7-JD-05 and is unverified.; Absence of a flat-exclusion record in the search is not proof that none exists.; Record-to-record comparison covered only records located by the stated regex searches over records_658.jsonl (body + references); records phrased differently may have been 

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-B-010 (independent-reviewer-B, INDEPENDENT_AGENT): **SUPPORTS** — Upheld as UNVERIFIED. Re-read on my copy (S-REVB-010): s.3(f) defines court-martial as one 'held under the Army Act, 1950' with no SCM carve-out (p.5); the s.3(o)(iv) SCM exclusion is confined to the 'service matters' definition (p.6); s.15(1)-(2) contains no express SCM exclusion (p.9). These textual statements are accurate and correctly limited. The decisive authority (Nk Santosh Lohar, P&H HC, 2023:PHHC:127834) is not on a reachable official h
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Does a s.15 appeal lie against an SCM sentence outside the s.3(o)(iv) carve-back (e.g. 30 days' detention)? What is the binding authority and has the Supreme Court addressed it?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)

### Item 32: F-XVOL-006 — CIV-034 — first pass P1 / provisional P1

- **Outcome / evidence state:** DISCREPANCY / SOURCE_VERIFIED; agent: cross-volume-auditor
- **Record text tested:** records_658.jsonl:line 493: “The relevant commencement and savings rules, the Army Act evidence provisions and court-martial procedure must be analysed together for a particular case.”
- **Finding:** CIV-034's title 'BSA applies to courts-martial' and its legal position are unqualified as to time; BSA s.170(2) preserves the Indian Evidence Act 1872 for any trial, inquiry, investigation, proceeding or appeal pending immediately before 1 July 2024. EV-002, V9-CL-01 and V9-WF-01 state this savings rule expressly; CIV-034 and CIV-019 refer only generically to 'commencement and savings rules' or none. Category: different effective dates.
- **Proposed correction (not applied):** Proposal only: qualify the title/legal position, e.g. 'BSA s.1(2) applies the BSA to courts-martial from 1 July 2024; under BSA s.170(2) a trial or other proceeding pending immediately before that date is dealt with under the Indian Evidence Act 1872.'
- **Temporal scope:** BSA 2023 India Code consolidation retrieved 2026-11-21; in force 1-7-2024 per compilation footnote (S.O. 849(E) of 23-2-2024 not itself retrieved); Army Act 1950 consolidation retrieved 2026-11-21; amendments after retrieval and General Clauses Act 1897 not checked.
- **Evidence:** S-XVOL-004: Bharatiya Sakshya Adhiniyam, 2023 (Act 47 of 2023) - s.1(2) applicatio — [[page 10]]: s.1(2) 'It applies to all judicial proceedings in or before any Court, including Courts-martial, but not to affidavits ... nor to proceedings before an arbitrator.'; s.1(3) commencement by notification [OFFICIAL_COMPILATION, STATUTE]; S-XVOL-005: Bharatiya Sakshya Adhiniyam, 2023 - s.170 repeal and savings; commence — [[page 51]]: s.170(1) repeals Indian Evidence Act 1872; s.170(2) pending application, trial, inquiry, investigation, proceeding or appeal dealt with under IEA 1872; [[page 10]] footnote 1: in force 1 July 2024 vide S.O. 849(E) dated 23-02-2024 [OFFICIAL_COMPILATION, STATUTE]
- **Limitations:** No judgment interpreting s.170(2) was checked.; Record-to-record comparison covered only records located by the stated regex searches over records_658.jsonl (body + references); records phrased differently may have been missed.

> **Independent review and disposition — technical challenge, NOT legal approval**
> - R-B-007 (independent-reviewer-B, INDEPENDENT_AGENT): **SUPPORTS** — Upheld; I would strengthen it. Re-verified on my own download (S-REVB-008): s.1(2) applies the BSA to 'all judicial proceedings in or before any Court, including Courts-martial' (p.10); commencement 1-7-2024 per footnote; s.170(2) preserves the 1872 Act for any 'application, trial, inquiry, investigation, proceeding or appeal pending' immediately before commencement (p.51). Adversarial test of the 'mere omission' characterisation: CIV-034's Asses
> - Orchestrator provisional disposition: NO_CHANGE_PROPOSED; provisional severity P1 (proposal only; original finding unchanged)

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: How is 'pending' under BSA s.170(2) applied to court-martial stages (CoI, hearing of charge, SoE, convening, trial, confirmation, AFT appeal)?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____
- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)


## Annex: supplementary remediation findings (orchestrator-authored; independently reviewed by independent-reviewer-C)

### F-REM-001 — HCE-017 — P1 — CONFLICTING_SOURCES
- Supplementary to F-STAT-006 (returned for evidence by R-A-007; F-STAT-006 preserved unchanged). The text of Army Rules r.192 differs between sources: MML 2.pdf p.227 prints a proviso (reduction to a lower grade of pay only to the immediately next lower grade, not effective beyond one year) footnoted as substituted by SRO 215 of 17-06-1965; the India Code compilation p.209 prints r.192(i)-(ii) without it. HCE-017 cites neither r.192 nor the proviso.
- Evidence: S-REM-001: Army Rules, 1954 (India Code annotated compilation) — PDF p.209, r.192(i)-(ii); page image checked (render sha256 8516c08b…, 110 dpi) [OFFICIAL_COMPILATION, RULE]; S-REM-002: Manual of Military Law (MML 2.pdf, combined AA/AR edition) — PDF p.227 (printed 227), r.192 proviso and footnote 1 'Substituted by SRO 215 dated 17 June, 1965'; page image checked (render sha256 756b0f48…) [USER_SUPPLIED_REFERENCE, MANUAL]

> **Independent review — technical challenge, NOT legal approval**
> - Not yet independently reviewed.

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Is the r.192 proviso (SRO 215/1965) part of the operative rule, and should the database flag its omission from the India Code compilation?
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____ — name/role/date/approval ref: ________

### F-REM-002 — MMLPKT-10 — P1 — DISCREPANCY
- Re-scoping of F-MML-019 per R-A-020 (F-MML-019 preserved unchanged): MML 2.pdf p.89 note 6 states that s.121 'prohibits a second trial by court-martial or a criminal court'. Enacted s.121 (India Code p.35) bars a second trial only 'by a court-martial or dealt with under the said sections'. The vol 2(AA) note 6 tracks the section text; only its cross-reference to omitted s.127 is dead.
- Evidence: S-REM-003: The Army Act, 1950 (India Code) — [[page 35]] s.121 [OFFICIAL_COMPILATION, STATUTE]

> **Independent review — technical challenge, NOT legal approval**
> - Not yet independently reviewed.

**Substantive legal decision — for the nominated legal advisor (blank)**
- Question: Confirm the scope of s.121 and whether any rule bars criminal-court retrial after court-martial (Art 20(2), CrPC s.300 / BNSS equivalent).
- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____ — name/role/date/approval ref: ________

