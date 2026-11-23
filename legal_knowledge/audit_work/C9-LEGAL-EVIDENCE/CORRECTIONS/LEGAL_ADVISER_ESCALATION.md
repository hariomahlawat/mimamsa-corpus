# Cycle 9 legal-adviser escalation package (CORR)

**Status:** for decision by JAG or an authorised legal adviser. Nothing in this package has been applied, and no record or register has been edited. Each item gives the question, the evidence on each side, what the corpus says now, and the proposals that wait on the decision (`correction_proposals_v2.csv`, all `PROPOSAL_NOT_APPLIED`).

**Readings.** Page readings are by an AI agent (Claude Opus 5.5 subagent) and are not human-confirmed. Every held file was re-hashed before use, and all matched. `tools/build_corr.py --verify-held` repeats the hash checks and the 33 page-anchor checks.

**Quotations.** Quotations are limited to statutory or holding language. No personal or medical details are reproduced.

**Priorities.** Priorities use the binding scale in `docs/legal-audit/EVIDENCE_STANDARD.md`. The adviser sets the final priority.

## Part 1. Questions of disputed law or interpretation (decision required)

### ESC-01 (Matter A, P1): How far does Girish Kumar's treatment of Tarsem Singh reach?

**Question.** Union of India v Sgt Girish Kumar (2026 INSC 149, 12-02-2026, two-Judge Bench) para 22 rejects the Union's reliance on Union of India v Tarsem Singh ((2008) 8 SCC 648, two-Judge Bench). The adviser is asked to decide three things:
- (a) whether the distinction is confined to re-computation (broad-banding) claims by persons already receiving disability pension, or whether the "legal landscape" ground (Ram Avtar, three-Judge, in rem) also limits Tarsem's arrears and continuing-wrong principle more widely;
- (b) which relation type to record: `distinguishes` is proposed; the documents support no stronger edge;
- (c) whether the warning wording in C9-CP-A01 to A04 may be applied.

**Evidence that the treatment is narrow, or that the question is open.**
- Girish para 22 gives the re-computation ground expressly: Tarsem "has no application to the case in hand as ex-servicemen in the instant appeals are already in receipt of disability pension and are only seeking re-computation" (held `4f7ea3a4…`, PDF p.16).
- Girish is a two-Judge Bench (two signatories, p.17). Tarsem is reported as a two-Judge Bench (R.V. Raveendran and Lokeshwar Singh Panta JJ on the unregistered SCR-format copy in the raw store). Whether a coordinate Bench could overrule it, and what relation to record, is for the adviser to decide; it is not stated here as a conclusion (review LG-09).
- Union of India v Balakrishnan Mullikote (2026 INSC 286, official copy `10e1954f…`, CORRECTED version, PDF pp.26-27, para 43) declined to examine limitation because Tarsem was not invoked. It quoted Girish para 22 and stated: "the said question of law is left open".

**Evidence that the treatment is broader.**
- Girish para 22, first ground: Tarsem "is of no assistance to it, as the legal landscape did not remain static after decision in Tarsem Singh" (p.15). This is tied to Ram Avtar being in rem, not only to the re-computation facts.
- Para 20 records a "consistent line of decisions" that disability pension, once due, cannot be curtailed by restricting it to three years before filing (p.14).
- Para 22 holds the AFT Act s.22(1)(c) bar inapplicable to these claims (p.16).

**What the corpus says now.**
- AFT-013 and V7-SC-02 present Tarsem as the governing arrears authority, with no later treatment.
- V7-JD-04 (the Tarsem digest) has no later-treatment note, although WS-B lists it as affected by both Girish (WSB-T-005) and Mullikote (WSB-T3-003).
- DCLR-SC-2008-N10 reads `NOT_EXHAUSTIVELY_CHECKED`.
- **No official court copy** of Tarsem is held. An unregistered SCR-format copy ([2008] 12 S.C.R. 104) is in the raw store, with undocumented provenance; registering it needs AP-C9-02 (review LG-05; the earlier "not held" was wrong). Its citation is corroborated by the two official judgments that cite it (Girish p.6 footnote; Mullikote p.26). Its date and case number come from an intern mirror only, and its URL is a commercial database.

**Waiting on this decision.** C9-CP-A01, A02, A03, A04 (and A05, metadata only). The proposals state expressly that Tarsem is **not** recorded as overruled.

### ESC-02 (Matter A, P1): The reported 12-10-2026 "clarification" of Girish Kumar, and the reach of the February judgment

**Questions.**
- (a) Until an official copy of the 12-10-2026 order (reported as 2026 INSC 1113) is obtained and read, may the corpus state its content at all? If it may, only with the proposed "UNVERIFIED SOURCE" flag?
- (b) Is the corpus framing of Girish as a "case-specific arrears award" supported by the February judgment itself?

**Evidence for (a).**
- No official copy is held, and the order's identity is `UNRESOLVED` (WS-B `identity_resolution.csv` and `identity_resolution_cycle3.csv`, `GIRISH_CLAR`). It is not in the intern corpus, and no official record could be reached without a CAPTCHA.
- The only URL is a commercial database, which is a discovery lead under CLAUDE.md, not a source.
- C8-EVIDENCE/SC-T2 lead GIRISH-1 records: "Clarification not held; content unverified".

**Evidence for (b).**
- Supports "case-specific": the operative para 23 (pp.16-17) quashes the three-year restriction and grants arrears from 01.01.1996 or 01.01.2006 to the appellants in the listed appeals.
- Points the other way: para 18 (p.13) describes a Government policy, the order of 18.04.2016, "to confer upon all eligible pensioners the benefit of arrears of disability pension", and para 22 describes Ram Avtar as in rem.
- The "not universal" framing in the corpus currently rests on the unheld clarification.

**What the corpus says now.** Seven records state the clarification's content as fact:
- PEN-045: "The Supreme Court clarified on 12 October 2026 …";
- PEN-048: "squarely rejects universalisation";
- DCLR-SC-2026-007 scope_and_caveats: "expressly prevents mechanical extension";
- DCLR-SC-2026-008 holding;
- PEN-J-06;
- and, by reference, PEN-WF-08, PEN-CS-09 and PEN-J-05.

**Waiting on this decision.** C9-CP-A06 to A11. Applying these proposals deletes nothing; it adds flags and a neutral note.

### ESC-03 (Matter B, P0, reserved RES-r23(3)): Army Rule 23(3) caution

The conflict stays **CONFLICTING (retained until legal review)**. C9 does not resolve it.

**Questions.** These carry forward F-R23-001 and F-XVOL-002:
- (a) Does the adviser accept the archival facsimile of the Gazette of 27-11-1954 (S.R.O. 484, printed p.300) as evidence of the notified text, pending a certified copy?
- (b) Is the amendment search sufficient, given the remaining gaps?
- (c) May the interim harmonised wording in C9-CP-B01 to B06 be displayed? It quotes both versions and adopts neither.
- (d) Is the accused's right not to make a statement secured independently of r.23(3), for example by Art.20(3)? C9 has not checked this.

**Evidence: the conflict.**
- The Gazette facsimile (`c5ef95a9…`, PDF p.10) prints "You are not obliged to say anything unless you wish to do so". C9 re-rendered it at 150 dpi; crop sha256 `c784cd2e…`.
- Manual of Military Law copies print the same wording.
- The India Code compilation (`48f52219…`, PDF p.41) prints "You are obliged to say anything unless you wish to do so". C9 crop sha256 `88783b51…`.
- Under the source hierarchy the notified instrument outranks the later consolidation (C-01). The omission of "not" is a *probable* transcription discrepancy, not a determined fact.

**Evidence: the amendment chain.**
- No located instrument amends r.23: 31 instruments examined, 1960-2022.
- These gaps remain:
  - E-7 of 17-06-1960;
  - 17 S.R.O.s of 1960-1991 that are listed in official notes but not located;
  - S.R.O. 258/2002;
  - S.R.O. 2(E)/2018;
  - anything after 06-06-2022.
- New in C9: the compilation attributes the Explanation to r.22, which sits immediately before r.23, to "SRO No 258 dt 27 Nov 2002" (p.39). The S.R.O. 258/2002 gap is therefore more likely to concern the Army Rules than C5-CF-U-01 suggests (C9-CP-B08).

**Origin classification (C9).**
- Source text: the primary origin.
- Amendment chronology: a residual risk only, while the gaps remain open.
- Interpretation: not the origin.
- Inconsistent corpus description: a consequence of the conflict. HCE-010 states "not obliged" as the rule text; V9-SC-19 implies it; EV-016, KB-006, V9-CL-04 and V9-WF-05 carry no flag.

**New in C9: the conflict is confined to the caution sentence.** The procedure limbs of r.23(3) read the same in the Gazette facsimile and the compilation:
- read-over and signature of each witness's evidence;
- the accused's statement recorded and read over;
- no cross-examination on the statement;
- defence and character witnesses.

This updates F-STAT-002 (C9-CP-B07).

**Waiting on this decision.** C9-CP-B01 to B08.

### ESC-05 (Matter D): Army Act ss.122-123 limitation (CM-011, CM-012)

**Questions.**
- (a) F-PROC-006: is "Apply the earliest relevant knowledge rule in Section 122(1)" a P1 misdescription (first pass) or a P2 drafting ambiguity (reviewer A; adopted provisionally, PILOT-01 D-05)? Either way, may the statute-tracking wording in C9-CP-D01 replace it?
- (b) LAQ-05: do s.122 and s.123(2) apply cumulatively to a person who has ceased to be subject to the Act?
- (c) LAQ-05 and AQ-05: which version applies where the offence or the cessation preceded Act 37 of 1992, and what is that Act's commencement date (it prints no commencement clause)?

**Evidence.** Compilation `e47a4265…` PDF p.35:
- s.122(1)(a) is the default starting point, the date of the offence;
- (b) and (c) are conditional, and "whichever is earlier" operates within each of them;
- s.122(3) excludes time as a prisoner of war, in enemy territory or evading arrest only;
- s.123(2) sets three years after cessation, with an exclusion for absconding or concealment and for staying injunctions or orders;
- footnotes record substitution by Act 37 of 1992 ss.9-10.

**What the corpus says now.** CM-011 omits s.123(2) (F-PROC-007, P1, upheld). Neither record carries a version note. Both display `SOURCE_REVIEWED_JAG_APPROVAL_PENDING` while P1 items remain open.

**Waiting on this decision.** C9-CP-D01 to D06.

### ESC-06 (Matter E, P1): Parashotam Dass and Shri Kant Sharma

**Questions.**
- (a) Which relation type should be recorded from Union of India v Parashotam Dass (CA 447/2023, 21-03-2023, three Judges) to Union of India v Maj Gen Shri Kant Sharma ((2015) 6 SCC 773): `overrules` / `overruled_by`, or "declared not good law" (the WS-B label in WSB-T-004)?
- (b) May the pinpoint and holding corrections (F-JUD-017) be applied?

**Evidence.** Held official copy `fe19875b…`:
- p.22 para 32: the judgment in Shri Kant Sharma "does not lay down the correct law", and "there is no per se restriction on the exercise of power under Article 226";
- p.3: the private parties' submissions begin at para 4;
- p.11: the Union's pleas run from para 16 to para 23;
- p.27: signatories.

**What the corpus says now.**
- The DCLR-SC-2023-009 pinpoint "11–16" points into the private parties' submissions.
- Its holding omits the para 32 ratio.
- Its scope_and_caveats says the official PDF was not retrieved, but it is held.
- The DCLR-SC-2015-N06 record says only that later jurisprudence "must be displayed".
- KB-025 cites para 18, from the Union's pleas, and KB-028 omits para 32.
- V7-JD-02 and AFT-035 already caveat the treatment.

**Classification.**
- The pinpoints are incorrect citations.
- The holding is incomplete, not wrong.
- The relation type is a characterisation, reserved for a human under CLAUDE.md.

**Waiting on this decision.** C9-CP-E01 to E06.

### ESC-07 (Matter E, P1; existing C-07 and LAQ-01): Army Act s.133 and the BSA 2023

**Question.** This repeats LAQ-01 without change: from what date, and for which pending proceedings, is AA s.133's reference to the Indian Evidence Act 1872 to be read as a reference to the BSA (General Clauses Act s.8; BSA s.170(2))?

**Evidence.**
- AA s.133 (`e47a4265…` p.37) still names the 1872 Act, "subject to the provisions of this Act".
- BSA s.1(2) (`554b2b4a…` p.10) applies the BSA to proceedings before "Courts-martial".
- BSA s.170(2) (p.51) saves the IEA for proceedings pending immediately before commencement.
- The commencement date of 01-07-2024 comes from a compilation footnote; the notification is not held.

**Classification.** This is an interaction between two Acts, not a source conflict.
- CM-025 and EV-003 state s.133 correctly.
- CM-025 omits BSA s.1(2) and s.170. Severity recalibration S-02 proposes lowering this from P1 to P2.
- CIV-034's title states a timeless conclusion.

**Waiting on this decision.** C9-CP-E11 and E12.

### ESC-08 (Matter E): Ram Avtar's identity and the limitation by S P Rathore

**Questions.**
- (a) Approve the identity resolution: Ram Avtar is the SC order of 10-12-2014 in C.A. 418/2012 and connected appeals. The curated URL, which is the S P Rathore judgment, would be relabelled.
- (b) After an official copy of S P Rathore is held, approve the propagation of its limitation to PEN-023, PEN-044 and PEN-WF-08.

**Evidence.**
- Girish (official copy), p.10, paras 13-14, describes Ram Avtar as a three-Judge order of 10.12.2014 that dismissed "more than 800 appeals" and held completion-of-tenure retirees with attributable or aggravated disability eligible for broad-banding. The order itself is not held.
- The S P Rathore limitation rests on an intern mirror only (WSB-T-024).
- PEN-J-04's source URL is a Supreme Court office report (OR-B). An office report corroborates listing metadata only and is not the order.

**Waiting on this decision.** C9-CP-E07 to E10.

## Part 2. Acquisition decisions (owner or adviser authorisation needed; no download made)

### ESC-04: Approve acquisition of official copies

The following official copies are needed before Part 1 items can be closed:
- Tarsem Singh (C.A. 5151-5152/2008): an official court copy is still needed; the raw store holds only an unregistered SCR-format copy, so registering it under AP-C9-02 is a separate, cheaper step (review LG-05);
- the 12-10-2026 Girish Kumar order;
- Union of India v Wg Cdr S P Rathore (C.A. 10870/2018);
- the Ram Avtar order (C.A. 418/2012);
- for r.23(3): a certified copy of S.R.O. 484/1954 and the instruments in the listed gaps.

CLAUDE.md requires approval before any real download run. If a source needs login or a CAPTCHA, as the GIRISH_CLAR lookup did, the brief requires stopping and reporting.

## Part 3. Evidence-supported corrections for approval (no disputed interpretation)

### ESC-09 (Matter C, P2): ADM-022 and Army Act s.26(2)

**Proposal.** Replace "explicitly directs complaint to next superior" with the permissive statutory wording (C9-CP-C01, which supersedes E8-CP-08).

**Evidence.** Compilation `e47a4265…` p.16:
- s.26(2): "the aggrieved person may complain to such officer's next superior officer";
- s.26(1) is also permissive;
- s.26(3) imposes the receiving officer's duty to investigate or refer.

**What the corpus says now.** ADM-SC-06 ("enables escalation") and ADM-020 are already consistent with the statute.

**Limitation.** The evidence is a government compilation only; no Gazette copy of the 1950 Act is held. The adviser need only confirm the wording.

### Other Part 3 items

The following are register or metadata precision items that need approval but no legal judgment:
- C9-CP-A05: Tarsem citation evidence note;
- C9-CP-A12: Girish pinpoints and neutral citation;
- C9-CP-A13: WS-B paraphrase of Girish's two grounds;
- C9-CP-B08: the S.R.O. 258/2002 gap text;
- C9-CP-E03: Parashotam provenance;
- C9-CP-E05 and E06: Parashotam pinpoints in KB-025 and KB-028.
