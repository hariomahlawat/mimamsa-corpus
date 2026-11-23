# Cycle 9 corpus corrections (CORR): findings summary

**Scope.** These are versioned correction **proposals**, not corrections:
- Snapshot: `c9src` (commit 2d7c02cf), treated as read-only.
- Starting point: the C8 CORPUS-QUALITY outputs and the C8-SOURCES Fable reviews and dispositions.
- Supreme Court evidence: C8-EVIDENCE/SC-T2.
- No record, register or repository file was edited. Nothing was downloaded, and no network access was used.
- Every proposal is `PROPOSAL_NOT_APPLIED`.
- No judgment is marked overruled, invalid or inapplicable. No disputed legal interpretation is stated as fact.

**Readings.**
- Page readings: AI agent (Claude Opus 5.5 subagent), not human-confirmed.
- Every held file was re-hashed before use: 8 files, all MATCH.
- Quotations are limited to statutory or holding language. No personal or medical details are reproduced, and no text dumps were written.

**Priorities.** Priorities use the binding scale in `docs/legal-audit/EVIDENCE_STANDARD.md`. Where an earlier cycle used another scale, the register's `prior_priority_note` column records it.

## Counts

| | P0 | P1 | P2 | P3 | Total |
| --- | --- | --- | --- | --- | --- |
| Findings (`consolidated_finding_register.csv`) | 1 | 8 | 9 | 5 | 23 |
| Proposals (`correction_proposals_v2.csv`) | 6 | 14 | 13 | 7 | 40 |

- **Novelty of the 23 findings.** 9 are NEW, or NEW proposals on registered dependencies. 14 are EXISTING: re-confirmed, updated with new evidence, or listed for traceability.
- **Superseded C8 proposals.** The proposals supersede E8-CP-01, -02, -03, -04, -08 and -09. They carry forward E8-CP-10--007 and the PILOT-01 proposed texts for F-PROC-006, F-PROC-007, F-STAT-013, F-XVOL-001/002/006/007 and F-JUD-017.
- **Record impact.** `record_impact.csv` lists 47 records and register rows: 30 with direct proposals and 17 linked (no change, consistent, flag inherited, register update, or recorded elsewhere).

## Matter A: Tarsem Singh and Girish Kumar

**Identity and dates, from held official copies.**
- **Girish Kumar.** Union of India v Sgt Girish Kumar, 2026 INSC 149, decided 12-02-2026; CA 6820-6824/2018 and connected appeals. Held copy `4f7ea3a4`, 17 pp.
  - The neutral citation is printed on p.1.
  - It is a two-Judge Bench (P.S. Narasimha and Alok Aradhe JJ, signatures on p.17).
- **Tarsem Singh.** The citation (2008) 8 SCC 648 is printed in two official judgments that cite Tarsem: Girish p.6 footnote, and Mullikote p.26 para 43.
  - The date 2008-08-13 and C.A. 5151-5152/2008 come from an intern mirror only.
  - Tarsem's own text is not held, so its holding and pinpoints are unverified.

**Operative holding.** Girish para 22 (pp.15-16) gives two grounds:
- "of no assistance", because the law changed after the three-Judge Ram Avtar order (in rem);
- "has no application", because the claimants already receive disability pension and seek only re-computation.

It also holds the AFT Act s.22(1)(c) bar inapplicable to those claims. Para 23 grants the appellants arrears from 01.01.1996 or 01.01.2006, with interest.

**Subsequent treatment (NEW evidence in C9).** Mullikote (2026 INSC 286, official copy `10e1954f`) para 43 did not examine limitation, quoted Girish para 22, and left "the said question of law … open".

**Result.** On the documents held, Tarsem is distinguished and not overruled; Girish is a coordinate Bench. The broader question is open (ESC-01).

**Records needing a distinction or warning.**
- AFT-013 and V7-SC-02: C9-CP-A01 and A02 (P1).
- V7-JD-04: C9-CP-A03 (P1, NEW). WS-B lists the record as affected, but its text has no note.
- The DCLR-SC-2008-N10 overlay edge: C9-CP-A04.
- AFT-014, V7-SC-14 and V7-SC-16 are linked to Tarsem but not engaged by the distinction, so no change is proposed for them.

**The 12-10-2026 "clarification" (2026 INSC 1113) is unverified (NEW, P1).**
- It is not held, its identity is unresolved, and its only URL is a commercial database.
- Seven records state its content as fact. C9 proposes "UNVERIFIED SOURCE" flags (C9-CP-A06 to A10) and deletes nothing.
- The corpus's "case-specific" framing of Girish is partly in tension with paras 18 and 22 of the held judgment. A neutral note is proposed (C9-CP-A11, ESC-02).

**Precision items (P3).**
- Girish para 22 prints both "of no assistance" and "has no application". The C8 dispositions note said the held copy reads "has no application" rather than "of no assistance", which is incomplete. WSB-T-005 merges the two grounds (C9-CP-A13).
- DCLR-SC-2026-007's pinpoints omit paras 17-22 (C9-CP-A12).

## Matter B: Army Rule 23(3)

**The conflict (C-01/U-01, P0).** The conflict is re-confirmed on fresh page renders, and the escalation is kept (ESC-03):
- Gazette of 27-11-1954 (S.R.O. 484, archival facsimile `c5ef95a9`, printed p.300): "You are not obliged to say anything unless you wish to do so".
- India Code compilation `48f52219` p.41: "You are obliged to say anything unless you wish to do so".

**Precise versions.**
- v1954: the only legal version evidenced. No located amendment through 06-06-2022 (31 instruments).
- The compilation text is an undated transcription, not a separate legal version.
- Gaps: E-7/1960; 17 listed S.R.O.s of 1960-1991 not located; S.R.O. 258/2002; S.R.O. 2(E)/2018; anything after 06-06-2022.

**Origin classification.**
- **Source text (transcription):** the primary origin; probable, not determined.
- **Amendment chronology:** a residual risk only.
- **Interpretation:** not the origin.
- **Inconsistent corpus description:** a consequence. HCE-010 asserts "not obliged" as the rule text; V9-SC-19 implies it; four records carry no flag.

**NEW in C9.**
- The caution/procedure split. The procedure limbs of r.23(3) are textually consistent between the Gazette facsimile and the compilation:
  - read-over and signature of each witness's evidence;
  - the accused's statement recorded and read over;
  - no cross-examination on the statement;
  - defence and character witnesses.

  The conflict is confined to the caution sentence. This updates F-STAT-002, whose premise that the Gazette is not held is superseded (C9-CP-B07).
- The compilation attributes the Explanation to r.22, which sits next to r.23, to S.R.O. 258/2002. C5-CF-U-01 understates the relevance of that gap (C9-CP-B08).

**Proposals.** Interim harmonised wording for six records (C9-CP-B01 to B06) quotes both versions and adopts neither.

**Clean result.** No corpus record claims that r.23 was amended. The C8 error "r.23 amended 2022" was confined to the C8 review and was corrected there.

## Matter C: Army Act s.26 (ADM-022)

**Wording (held compilation `e47a4265` p.16).**
- s.26(2): "the aggrieved person **may** complain to such officer's next superior officer".
- s.26(1) is also permissive.
- s.26(3) is the mandatory part: the receiving officer "shall make as complete an investigation … or … refer".

**Result.** ADM-022's "explicitly directs" overstates the statute (EXISTING E8-XR-08; P2 on the binding scale). The C9-CP-C01 replacement tracks the statute. ADM-SC-06 and ADM-020 are already consistent. The evidence class is GOVERNMENT_COMPILATION_ONLY.

## Matter D: court-martial procedure and limitation

**CM-011.**
- **F-PROC-006: reviewer disagreement kept open.** The first pass rated it P1; reviewer A rated it P2, and that position was adopted provisionally (PILOT-01 D-05). C9 proposes wording that tracks s.122(1)(a)-(c) and takes no side on severity (C9-CP-D01).
- **F-PROC-007: upheld (P1).** CM-011 omits s.123(2) (C9-CP-D02).
- **NEW proposals: version notes on CM-011 and CM-012 (P2).** The relevant words of s.122(1) and s.123(2) were substituted by Act 37 of 1992 ss.9-10. That Act states no commencement date (AQ-05), and the pre-1992 versions are LAQ-05 (C9-CP-D03 and D04).
- **Status label (EXISTING E8-XR-09).** CM-011 and CM-025 display SOURCE_REVIEWED while P1 items remain open. An overlay flag is proposed (C9-CP-D05 and D06).

**Clean results.**
- CM-011's warning that a CoI or SoE does not pause limitation is consistent with s.122(3).
- CM-012's description of s.123 matches the compilation.
- The range citations that include the omitted s.127 (CM-001, KB-030) are already recorded in CALIBRATION-02.

## Matter E: judicial treatment and citations

The items are classified as incorrect citations or as unsupported or incomplete conclusions.

**Incorrect citations or identifiers.**
- **Parashotam pinpoint "11–16".** These paragraphs are submissions; the Court's view is at paras 24-32 (P1, F-JUD-017).
- **KB-025 and KB-028 pinpoints (NEW, P3).** KB-025 cites para 18, which is in the Union's pleas, and both omit para 32.
- **Ram Avtar URL.** The URL is the S P Rathore judgment (OI-08, P1). The official Girish paras 13-14 now give an official description of Ram Avtar.
- **PEN-J-04 (NEW, P2).** Its source URL is a Supreme Court office report, not the order.

**Incomplete or unsupported conclusions.**
- **Parashotam holding.** The holding omits the para 32 ratio: Shri Kant Sharma "does not lay down the correct law", and there is "no per se restriction" on Art.226 review.
- **Shri Kant Sharma relation type.** The type, `overrules` or "declared not good law", is left to the adviser (ESC-06) although the evidence is explicit.
- **S P Rathore limitation of Ram Avtar.** This rests on a mirror copy only. The proposal stays conditional (C9-CP-E10).

**BSA s.133 (C-07).** This is an interaction between two Acts, not a source conflict:
- CM-025 and EV-003 state s.133 correctly;
- CM-025 omits BSA s.1(2) and s.170;
- CIV-034's title is temporally unqualified (C9-CP-E11 and E12; LAQ-01).

## Escalations (`LEGAL_ADVISER_ESCALATION.md`)

| ID | Matter | Topic |
| --- | --- | --- |
| ESC-01 | A | Reach of Girish para 22 on Tarsem; relation type; Mullikote "left open" |
| ESC-02 | A | The unheld 12-10-2026 clarification; "case-specific" framing |
| ESC-03 | B | r.23(3) caution (P0, reserved); interim wording; amendment gaps |
| ESC-04 | all | Authorisation to acquire official copies: Tarsem, the clarification, S P Rathore, the Ram Avtar order, certified S.R.O. 484 |
| ESC-05 | D | s.122 formula (F-PROC-006 dispute); cumulative ss.122/123(2); pre-1992 versions and commencement |
| ESC-06 | E | Parashotam to Shri Kant Sharma relation type; F-JUD-017 corrections |
| ESC-07 | E | AA s.133 and BSA s.1(2)/s.170 (LAQ-01) |
| ESC-08 | E | Ram Avtar identity; S P Rathore propagation |
| ESC-09 | C | ADM-022 wording (confirmation only) |

## Limitations

- **Statutory evidence.** Statutory text comes from India Code government compilations. There is no Gazette copy of the 1950 Army Act. For r.23 the only Gazette evidence is an archival facsimile, not a certified copy.
- **Unread sources.** The 1992 amending Act (`f11d443e`) was cited from the C8 matrix and was not re-read in C9.
- **Judgment readings.** Judgment readings used text layers. C9 rendered page images only for the r.23(3) caution, at both sources.
- **Exhaustiveness.** Treatment searches are not exhaustive. The absence of a treatment row is not proof that no treatment exists.
- **What the builder proves.** `--check` proves the outputs are reproducible. Quote checks prove that each "current text" is verbatim in the snapshot. Neither proves that the legal content is right.

## Reproduce

```
python c9out/CORR/tools/build_corr.py <c9src> --check
python c9out/CORR/tools/build_corr.py <c9src> --verify-held <scratchpad>   # PyMuPDF; 8 hashes, 33 anchors
cd c9out/CORR && sha256sum -c OUTPUT_SHA256SUMS
```
