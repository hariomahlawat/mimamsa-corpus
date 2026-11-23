#!/usr/bin/env python3
"""Cycle 9 corpus-correction (CORR) builder.

Deterministic builder for the C9 correction PROPOSALS. It never edits any
record or register: it only reads the snapshot and writes three CSVs plus an
OUTPUT_SHA256SUMS file into the output directory.

Usage:
    python build_corr.py REPO_ROOT [--out-dir DIR] [--check] [--verify-held HELD_ROOT]

  REPO_ROOT       snapshot root (the directory holding legal_knowledge/)
  --out-dir       default: the parent directory of this tools/ folder
  --check         rebuild in memory and compare byte-for-byte with the files
                  on disk, and verify OUTPUT_SHA256SUMS; exit 1 on any drift
  --verify-held   re-hash every held binary cited below (located through
                  SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv,
                  paths relative to HELD_ROOT) and confirm each short anchor
                  string occurs on the cited PDF page (needs PyMuPDF)

Every run also verifies, against REPO_ROOT, that each 'current_text_quote'
in the proposals occurs verbatim in the named record field or register cell.
A mismatch is a hard failure (exit 2): the quotes cannot drift silently.

Page readings recorded here: AI agent (Claude Opus 5.5 subagent), not
human-confirmed. Nothing here is a legal determination.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys

KB = "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
CASES = "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
AW = "legal_knowledge/audit_work/"
MANIFEST = AW + "SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv"
READER = "AI agent (Claude Opus 5.5 subagent), not human-confirmed"

# Held copies cited (sha256 prefix -> label).
H = {
    "GIRISH": "4f7ea3a451c6f9a11d7e4dd96822e68cd9cd7a01d8dc74cf46ad34e79029b86c",
    "MULLIKOTE": "10e1954f2e39916ea0f0e8e759c3823581becf752dd6ad2e9058569a1fd97444",
    "PARASHOTAM": "fe19875b19ed5a4efa257273cd2fb1f1cbb57c4f383117cc40e9a90046568377",
    "AA": "e47a4265813e95b491a24926428ed306cfeaae9013e7edb928cefef6e69a7c08",
    "AR": "48f52219121bf74d070bc832e4573f2f512b239e0a0441ba96b1daca2983a727",
    "G1954": "c5ef95a9d553685aa655f041b71d8360d6272e2775a19a3d6e7273c6cbd0aca6",
    "BSA": "554b2b4ae3d9f09bf31e6e1ba2b2cb8a4e7f4f5ffd6f3156736752cbbce116d5",
    "AFT": "665863d1abb802f7488eb75f776946e30e72ccec16962da8e2b3ee8f2e023e3b",
}


def h(label):
    return "held sha256 %s" % H[label]


# Short anchor strings checked on held pages by --verify-held
# (label, pdf_page, anchor). Whitespace is normalised before matching.
ANCHORS = [
    ("GIRISH", 1, "2026 INSC 149"),
    ("GIRISH", 6, "Tarsem Singh (2008) 8 SCC 648"),
    ("GIRISH", 10, "A three-Judge Bench of this Court in Union of India and Others v. Ram Avtar"),
    ("GIRISH", 10, "dismissed more than 800 appeals"),
    ("GIRISH", 13, "to confer upon all eligible pensioners the benefit of arrears of disability pension"),
    ("GIRISH", 15, "decision of a two- Judge Bench of this Court in Tarsem Singh (supra) is of no assistance to it, as the legal landscape did not remain static"),
    ("GIRISH", 16, "has no application to the case in hand as ex-servicemen in the instant appeals are already in receipt of disability pension and are only seeking re-computation"),
    ("GIRISH", 16, "the bar contained in Section 22(1)(c) of the Act has no application"),
    ("GIRISH", 17, "with effect from 01.01.1996 or 01.01.2006"),
    ("GIRISH", 17, "FEBRUARY 12, 2026"),
    ("MULLIKOTE", 26, "Tarsem Singh, (2008) 8 SCC 648 was not invoked during the course of arguments"),
    ("MULLIKOTE", 26, "2026 SCC OnLine SC 194"),
    ("MULLIKOTE", 27, "the said question of law is left open"),
    ("PARASHOTAM", 3, "Submissions on behalf of the private parties"),
    ("PARASHOTAM", 11, "The pleas of Union of India and JAG Branch"),
    ("PARASHOTAM", 22, "does not lay down the correct law"),
    ("PARASHOTAM", 22, "there is no per se restriction on the exercise of power under Article 226"),
    ("PARASHOTAM", 27, "March 21, 2023"),
    ("G1954", 10, "You are not obliged to say anything unless you wish to do so"),
    ("G1954", 10, "but he will not be cross-examined upon it"),
    ("AR", 41, "You are obliged to say anything unless you wish to do so"),
    ("AR", 41, "but he will not be cross-examined upon it"),
    ("AR", 39, "SRO No 258 dt 27 Nov 2002"),
    ("AA", 16, "the aggrieved person may complain to such officer’s next superior officer"),
    ("AA", 16, "Every officer receiving any such complaint shall make as complete an investigation"),
    ("AA", 35, "whichever is earlier"),
    ("AA", 35, "within a period of three years after he had ceased to be subject to this Act"),
    ("AA", 35, "Subs. by Act 37 of 1992, s. 9, for certain words"),
    ("AA", 35, "Subs. by s. 10, ibid., for certain words"),
    ("AA", 37, "shall, subject to the provisions of this Act, apply to all proceedings before a court-martial"),
    ("BSA", 10, "including Courts-martial"),
    ("BSA", 51, "shall be dealt with under the provisions of the Indian Evidence Act, 1872"),
    ("AFT", 11, "in a case where the grievance in respect of which an application is made had arisen by reason"),
]

UNVERIFIED_CLAR = ("[UNVERIFIED SOURCE: the 12-10-2026 Girish Kumar clarification (reported as 2026 INSC 1113) "
                   "is not held in official form; its identity is UNRESOLVED (WS-B identity_resolution_cycle3 GIRISH_CLAR) "
                   "and its content comes from a secondary reproduction only. Do not rely on this statement until the "
                   "official order is obtained and read (ESC-02).]")

R23_FLAG = ("Source conflict (C-01, P0, reserved): the r.23(3) caution reads 'You are not obliged to say anything unless you "
            "wish to do so' in the Gazette of India of 27-11-1954 (S.R.O. 484, printed p.300; archival facsimile, not "
            "certified) and in Manual of Military Law copies, but the India Code compilation omits 'not'. No amending "
            "instrument touching r.23 has been located up to 06-06-2022 (gaps listed in C5-CF-U-01). Do not quote either "
            "version as the authoritative current text; refer to legal review.")

# ---------------------------------------------------------------- findings
FCOLS = ["finding_id", "matter", "novelty", "existing_refs", "priority_evidence_standard", "prior_priority_note",
         "finding_class", "records_or_register_keys", "field", "observation", "primary_evidence", "page_reading_by",
         "proposal_refs", "escalation_ref", "status"]

FINDINGS = [
    # ---------------- Matter A
    dict(finding_id="C9-F-A01", matter="A", novelty="EXISTING (updated)",
         existing_refs="E8-XR-01; E8-CP-01/02; WSB-T-005; WSB-H-027",
         priority_evidence_standard="P1", prior_priority_note="C8 local P2; C8 indicative P1 candidate (missing contrary precedent)",
         finding_class="MISSING_LATER_TREATMENT",
         records_or_register_keys="AFT-013; V7-SC-02",
         field="body",
         observation=("Both records present Union of India v Tarsem Singh ((2008) 8 SCC 648) as the governing arrears/continuing-wrong "
                      "authority with no reference to later Supreme Court treatment. C9 re-read the held official Girish Kumar copy: para 22 "
                      "gives two separate grounds: (i) Tarsem (a two-Judge Bench) is 'of no assistance' to the Union because the legal landscape "
                      "changed after the three-Judge Ram Avtar order (10-12-2014), described as in rem; (ii) Tarsem 'has no application' where "
                      "ex-servicemen already receive disability pension and seek only re-computation; it also holds the AFT Act s.22(1)(c) bar "
                      "inapplicable to those claims. NEW evidence added in C9: Mullikote (2026 INSC 286, official copy) para 43 declined to examine "
                      "limitation because Tarsem was not invoked, quoted Girish para 22, and stated 'the said question of law is left open'. "
                      "On the held documents Tarsem is distinguished, not overruled (Girish is itself a two-Judge, coordinate Bench), and the wider "
                      "limitation question is expressly open."),
         primary_evidence=("%s (Girish Kumar, 2026 INSC 149) PDF p.15 para 22 ('is of no assistance to it, as the legal landscape did not remain static'), "
                           "p.16 para 22 ('has no application to the case in hand'; 's.22(1)(c) ... has no application'), p.17 (two signatories); "
                           "%s (Mullikote, 2026 INSC 286, CORRECTED pp.1-31) PDF pp.26-27 para 43 ('the said question of law is left open'); "
                           "WS-B subsequent_treatment.csv#WSB-T-005; subsequent_treatment_cycle3.csv#WSB-T3-003") % (h("GIRISH"), h("MULLIKOTE")),
         page_reading_by=READER, proposal_refs="C9-CP-A01; C9-CP-A02", escalation_ref="ESC-01", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-A02", matter="A", novelty="NEW",
         existing_refs="WSB-T-005 (lists V7-JD-04 as affected); WSB-T3-003 / WSB-H3-012 (list V7-JD-04)",
         priority_evidence_standard="P1", prior_priority_note="",
         finding_class="MISSING_LATER_TREATMENT",
         records_or_register_keys="V7-JD-04",
         field="body",
         observation=("The Tarsem Singh digest itself carries no later-treatment note. WS-B lists V7-JD-04 as affected by both the Girish "
                      "distinction (WSB-T-005) and the Mullikote 'left open' observation (WSB-T3-003), but listing a record in a register does "
                      "not change what the record displays. C8 proposed text changes only for AFT-013 and V7-SC-02."),
         primary_evidence="%s PDF pp.15-16 para 22; %s PDF pp.26-27 para 43" % (h("GIRISH"), h("MULLIKOTE")),
         page_reading_by=READER, proposal_refs="C9-CP-A03", escalation_ref="ESC-01", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-A03", matter="A", novelty="EXISTING (updated)",
         existing_refs="E8-CP-03; E8-XR-11 (commercial URL); WS-B identity_resolution.csv#TARSEM; case_relations.csv",
         priority_evidence_standard="P2", prior_priority_note="C8 local P2",
         finding_class="MISSING_LATER_TREATMENT; METADATA_EVIDENCE",
         records_or_register_keys="cases_53 DCLR-SC-2008-N10",
         field="post_decision_treatment_status; reporter_citation; accessible_source_url",
         observation=("Identity check: the citation (2008) 8 SCC 648 is printed in two held official Supreme Court copies (Girish p.6 footnote; "
                      "Mullikote p.26 para 43), so the citation is corroborated by official documents that cite Tarsem; the decision date 2008-08-13 "
                      "and C.A. 5151-5152/2008 rest only on the intern mirror (WS-B identity IDENTITY_CORROBORATED_INTERN_MIRROR_ONLY). "
                      "Tarsem's own text is not held, so its holding and pinpoints ('Paras 4-7') remain unverified, and its only URL is a commercial "
                      "database. The case record still shows NOT_EXHAUSTIVELY_CHECKED with no treatment edge."),
         primary_evidence=("%s PDF p.6 fn ('Tarsem Singh (2008) 8 SCC 648'); %s PDF p.26 para 43; WS-B identity_resolution.csv#TARSEM; "
                           "case_relations.csv edge DCLR-SC-2026-007 -> DCLR-SC-2008-N10 DISTINGUISHED") % (h("GIRISH"), h("MULLIKOTE")),
         page_reading_by=READER, proposal_refs="C9-CP-A04; C9-CP-A05", escalation_ref="ESC-01", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-A04", matter="A", novelty="NEW",
         existing_refs="E8-XR-20 and A-C2-05 (PEN-J-06 unheld); SC-T2 lead GIRISH-1; identity_resolution_cycle3.csv#GIRISH_CLAR; WSB-H-028 uncertainty",
         priority_evidence_standard="P1", prior_priority_note="",
         finding_class="UNSUPPORTED_LEGAL_CONCLUSION (source not held)",
         records_or_register_keys="PEN-045; PEN-048; PEN-J-06; DCLR-SC-2026-007; DCLR-SC-2026-008 (linked: PEN-WF-08, PEN-CS-09, PEN-J-05)",
         field="body; scope_and_caveats; holding",
         observation=("Seven records state the content of a 12-10-2026 'clarification' of Girish Kumar as settled fact (e.g. PEN-048 'squarely "
                      "rejects universalisation'; DCLR-SC-2026-007 'expressly prevents mechanical extension'). No official copy is held, its identity "
                      "and neutral citation (2026 INSC 1113) are unresolved, and the only URL is a commercial database. Earlier cycles recorded the "
                      "source as unheld but did not carry an 'unverified' flag into the records that rely on it. This is an unsupported conclusion, "
                      "not a proven error: the order may exist and say what the records say."),
         primary_evidence=("WS-B identity_resolution.csv#GIRISH_CLAR (NO_MATCH_FOUND, UNRESOLVED_NO_COPY_IN_HAND); identity_resolution_cycle3.csv#GIRISH_CLAR "
                           "(UNRESOLVED); C8-EVIDENCE/SC-T2/subsequent_treatment_leads.csv#GIRISH-1 (clarification not held; content unverified); "
                           "holdings_register.csv#WSB-H-028 uncertainty ('Clarification order 12.10.2026 (2026 INSC 1113) NOT held')"),
         page_reading_by="register reading (no page)", proposal_refs="C9-CP-A06; C9-CP-A07; C9-CP-A08; C9-CP-A09; C9-CP-A10",
         escalation_ref="ESC-02", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-A05", matter="A", novelty="NEW",
         existing_refs="WSB-H-028; WSB-H3-015",
         priority_evidence_standard="P2", prior_priority_note="",
         finding_class="INTERPRETATION_QUESTION",
         records_or_register_keys="DCLR-SC-2026-007 (linked: PEN-J-05, PEN-045)",
         field="commanders_summary; holding",
         observation=("The corpus frames Girish as a 'case-specific arrears award'. The held judgment's operative relief (para 23) is confined to "
                      "the appellants in the listed appeals, which supports that framing; but its reasoning refers to a Government policy (order "
                      "dated 18.04.2016) 'to confer upon all eligible pensioners the benefit of arrears of disability pension' from 01.01.1996 or "
                      "01.01.2006 (para 18) and to Ram Avtar as in rem (para 22). How far the judgment reaches beyond the appellants is a legal "
                      "question; the 'not universal' framing currently rests on the unheld clarification (C9-F-A04)."),
         primary_evidence="%s PDF p.13 para 18; p.16 para 22; pp.16-17 para 23" % h("GIRISH"),
         page_reading_by=READER, proposal_refs="C9-CP-A11", escalation_ref="ESC-02", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-A06", matter="A", novelty="NEW",
         existing_refs="WSB-T-005; WSB-H-027; C8 DISPOSITIONS_44fd72d6.md 'Other correction found while working'",
         priority_evidence_standard="P3", prior_priority_note="",
         finding_class="REGISTER_INCONSISTENCY",
         records_or_register_keys="WS-B-JUDGMENTS/subsequent_treatment.csv#WSB-T-005 (scope); holdings_register.csv#WSB-H-027 (ws_b_paraphrase)",
         field="scope; ws_b_paraphrase",
         observation=("Both phrases occur in Girish para 22: 'of no assistance' (p.15, landscape-change ground) and 'has no application' (p.16, "
                      "re-computation ground). WSB-T-005 merges them into one ground. The C8 dispositions note said the held copy reads 'has no "
                      "application' rather than 'of no assistance'; in fact it prints both. Neither register is wrong in substance; the precision "
                      "matters because the two grounds have different reach (C9-F-A01)."),
         primary_evidence="%s PDF p.15 and p.16 para 22" % h("GIRISH"),
         page_reading_by=READER, proposal_refs="C9-CP-A13", escalation_ref="", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-A07", matter="A", novelty="EXISTING (extended)",
         existing_refs="E8-XR-06; E8-CP-10--007",
         priority_evidence_standard="P3", prior_priority_note="C8 local P3",
         finding_class="METADATA (pinpoint / citation)",
         records_or_register_keys="cases_53 DCLR-SC-2026-007",
         field="pinpoint_paragraphs; reporter_citation",
         observation=("pinpoint_paragraphs (8; 12-16; 23) omit paras 17-22, which hold the arrears and limitation reasoning, including para 22 on "
                      "Tarsem. reporter_citation is empty although '2026 INSC 149' is printed on p.1 (C8 E8-CP-10--007 carried forward). "
                      "Mullikote (official) cites Girish as '2026 SCC OnLine SC 194': a commercial reporter citation printed in an official "
                      "judgment, recordable only as 'as cited in'."),
         primary_evidence="%s PDF p.1, pp.12-16 paras 17-22; %s PDF p.26 para 43" % (h("GIRISH"), h("MULLIKOTE")),
         page_reading_by=READER, proposal_refs="C9-CP-A12", escalation_ref="", status="PROPOSAL_NOT_APPLIED"),
    # ---------------- Matter B
    dict(finding_id="C9-F-B01", matter="B", novelty="EXISTING (re-confirmed; origin classified)",
         existing_refs="SOURCE-CONFLICTS-01 C-01 / U-01; C5-CF-C-01 / C5-CF-U-01; F-STAT-001; F-STAT-020; F-XVOL-001; F-XVOL-002; F-R23-001/002; RES-r23(3); E8-XR-21",
         priority_evidence_standard="P0", prior_priority_note="P0 throughout",
         finding_class="SOURCE_TEXT_CONFLICT",
         records_or_register_keys="HCE-010; EV-016; V9-SC-19; KB-006; V9-CL-04; V9-WF-05",
         field="body",
         observation=("Re-rendered in C9: the Gazette facsimile prints 'You are not obliged to say anything unless you wish to do so' (render of "
                      "crop sha256 c784cd2e861b8637b54e24941a85fe68f454dd3b1f88918617d467c77f3ae636, 150 dpi); the compilation prints 'You are obliged "
                      "to say anything unless you wish to do so' (crop sha256 88783b51208b72d611f341d4ece11af2d162d172bbff669b52d2774b779326c6, 130 dpi). "
                      "Origin classification. (1) SOURCE TEXT: primary origin; a probable transcription omission in a later consolidation, not a "
                      "determined fact. (2) AMENDMENT CHRONOLOGY: not the origin on the evidence located (31 instruments, 1960-2022, none amends r.23), "
                      "but a residual risk while gaps remain (E-7/1960; 17 listed S.R.O.s of 1960-1991 not located; S.R.O. 258/2002; S.R.O. 2(E)/2018; "
                      "anything after 06-06-2022). (3) INTERPRETATION: not the origin; the words differ, not their reading (a separate question, "
                      "whether silence is protected independently of r.23(3), stays with the adviser per F-XVOL-002). (4) INCONSISTENT CORPUS "
                      "DESCRIPTION: a consequence; HCE-010 states 'not obliged' as rule text, V9-SC-19 implies it, and four records are caution-neutral "
                      "without a flag. Versions: v1954 (S.R.O. 484, 27-11-1954, 'not obliged'), with no located amendment to 06-06-2022; the "
                      "compilation version is undated and is not a separate legal version."),
         primary_evidence=("%s (Gazette 27-11-1954) PDF p.10 / printed p.300, r.23(3); %s (India Code compilation) PDF p.41, r.23(3); "
                           "R23-VERIFY-01/registers/amendment_chain_r23.csv; amendment_search_2026-11-22.csv; C5 source_conflict_register.csv#C5-CF-U-01") % (h("G1954"), h("AR")),
         page_reading_by=READER, proposal_refs="C9-CP-B01; C9-CP-B02; C9-CP-B03; C9-CP-B04; C9-CP-B05; C9-CP-B06",
         escalation_ref="ESC-03", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-B02", matter="B", novelty="NEW (updates F-STAT-002)",
         existing_refs="PILOT-01 F-STAT-002; C-01",
         priority_evidence_standard="P2", prior_priority_note="F-STAT-002 P2",
         finding_class="VERIFICATION_STATE_UPDATE",
         records_or_register_keys="PILOT-01/registers/corrections_register.csv#F-STAT-002; HCE-010",
         field="claim / verification_state",
         observation=("The procedure limbs of r.23(3) (read-over and signature of each witness's evidence; the accused's statement recorded and read "
                      "over; no cross-examination on it; defence and character witnesses) read the same in the Gazette facsimile and the compilation. "
                      "Only trivial variants appear (e.g. 'his mark' vs 'the mark'; r.23(2) 'such questions' vs 'such question'). So the conflict is "
                      "confined to the caution sentence. F-STAT-002's premise ('the Gazette original is not held') is superseded by the held facsimile."),
         primary_evidence="%s PDF p.10 r.23(2)-(3); %s PDF p.41 r.23(2)-(3)" % (h("G1954"), h("AR")),
         page_reading_by=READER, proposal_refs="C9-CP-B07", escalation_ref="ESC-03", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-B03", matter="B", novelty="NEW",
         existing_refs="C5-CF-U-01; C-01 gaps; ARMY-RULES-CHAIN-01 AR-030; F-MML-002",
         priority_evidence_standard="P3", prior_priority_note="",
         finding_class="REGISTER_INCONSISTENCY",
         records_or_register_keys="SOURCE-LIBRARY-C5/registers/source_conflict_register.csv#C5-CF-U-01",
         field="evidence (gap description)",
         observation=("U-01 says S.R.O. 258/2002 'may not be an Army Rules instrument'. The compilation prints 'SRO No 258 dt 27 Nov 2002' against "
                      "the Explanation to r.22 (p.39), immediately before r.23, and AR-030 / F-MML-002 record it as possibly inserting that "
                      "Explanation. The gap is therefore more likely to involve the Army Rules than U-01 suggests, and it sits next to r.23."),
         primary_evidence="%s PDF p.39 ('SRO No 258 dt 27 Nov 2002'); ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv#AR-030" % h("AR"),
         page_reading_by=READER, proposal_refs="C9-CP-B08", escalation_ref="ESC-03", status="PROPOSAL_NOT_APPLIED"),
    # ---------------- Matter C
    dict(finding_id="C9-F-C01", matter="C", novelty="EXISTING (re-confirmed)",
         existing_refs="E8-XR-08; E8-CP-08",
         priority_evidence_standard="P2", prior_priority_note="C8 local P3; C8 indicative P2",
         finding_class="OVERSTATED_STATUTORY_WORDING",
         records_or_register_keys="ADM-022 (consistent: ADM-SC-06, ADM-020)",
         field="body",
         observation=("ADM-022 says s.26(2) 'explicitly directs' complaint to the next superior officer. The held compilation prints a permission: "
                      "'the aggrieved person may complain to such officer's next superior officer'. s.26(1) is also permissive ('may ... complain'); "
                      "the mandatory element of s.26 is the receiving officer's duty in s.26(3) ('shall make as complete an investigation ... or ... "
                      "refer'). ADM-SC-06 ('enables escalation') and ADM-020 are consistent with the statute. Evidence class: government compilation "
                      "only (no Gazette copy of the 1950 Act held)."),
         primary_evidence="%s PDF p.16 s.26(1)-(3)" % h("AA"),
         page_reading_by=READER, proposal_refs="C9-CP-C01", escalation_ref="ESC-09", status="PROPOSAL_NOT_APPLIED"),
    # ---------------- Matter D
    dict(finding_id="C9-F-D01", matter="D", novelty="EXISTING (reviewer disagreement open)",
         existing_refs="F-PROC-006; PILOT-01 post_review D-05 (reviewer A DISPUTES; P2 adopted provisionally); E8-XR-09",
         priority_evidence_standard="P2 (disputed: first pass P1)", prior_priority_note="P1 first pass; P2 provisional (D-05)",
         finding_class="AMBIGUOUS_PARAPHRASE",
         records_or_register_keys="CM-011",
         field="body",
         observation=("The statute (p.35) makes (a) the default start date and (b)/(c) conditional alternatives, with 'whichever is earlier' "
                      "operating only inside (b) and (c). CM-011's phrase 'earliest relevant knowledge rule' can be read either way. C9 takes no side "
                      "on severity; it proposes wording that tracks the statutory structure without adding interpretation, and keeps the dispute open "
                      "for the adviser."),
         primary_evidence="%s PDF p.35 s.122(1)(a)-(c)" % h("AA"),
         page_reading_by=READER, proposal_refs="C9-CP-D01", escalation_ref="ESC-05", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-D02", matter="D", novelty="EXISTING (upheld)",
         existing_refs="F-PROC-007 (upheld by reviewer A and blind pass); LAQ-05",
         priority_evidence_standard="P1", prior_priority_note="P1",
         finding_class="OMISSION",
         records_or_register_keys="CM-011 (linked: CM-012)",
         field="body",
         observation=("CM-011 omits s.123(2): for a person who has ceased to be subject to the Act, trial must begin within three years of cessation, "
                      "with exclusions for absconding/concealment and for any staying injunction or order (s.122(3) has no stay exclusion). CM-012 "
                      "covers s.123 but CM-011 does not cross-refer to it. Whether ss.122 and 123(2) apply cumulatively is LAQ-05."),
         primary_evidence="%s PDF p.35 s.123(1)-(2) and proviso" % h("AA"),
         page_reading_by=READER, proposal_refs="C9-CP-D02", escalation_ref="ESC-05", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-D03", matter="D", novelty="NEW (proposal; dependency already registered)",
         existing_refs="LAQ-05; RES-AQ-05; amendment_commencement_matrix D-AMC-AA-08-s9/-s10; C8 high_risk rows CM-011/CM-012",
         priority_evidence_standard="P2", prior_priority_note="",
         finding_class="OMISSION_TEMPORAL_SCOPE",
         records_or_register_keys="CM-011; CM-012",
         field="body",
         observation=("Both records state the current s.122(1)/s.123(2) text as timeless. The commencement limbs of s.122(1) and the three-year "
                      "post-cessation period in s.123(2) were substituted by Act 37 of 1992 ss.9-10; that Act prints no commencement clause (AQ-05), "
                      "and the version for earlier offences or cessation is LAQ-05. C8 recorded this dependency but proposed no record wording."),
         primary_evidence="%s PDF p.35 footnotes 1-2 ('Subs. by Act 37 of 1992, s. 9 ...'; 'Subs. by s. 10, ibid.'); held Gazette of Act 37/1992 sha256 f11d443ebfdada41780974c25612d85f7f62853bc552a38e1e2750a209067185 (per C8 matrix D-AMC-AA-08-*; not re-read in C9)" % h("AA"),
         page_reading_by=READER, proposal_refs="C9-CP-D03; C9-CP-D04", escalation_ref="ESC-05", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-D04", matter="D", novelty="EXISTING",
         existing_refs="E8-XR-09; E8-CP-09-CM-011; E8-CP-09-CM-025",
         priority_evidence_standard="P2", prior_priority_note="C8 local P3; C8 indicative P2",
         finding_class="STATUS_LABEL",
         records_or_register_keys="CM-011; CM-025",
         field="status",
         observation="Status SOURCE_REVIEWED_JAG_APPROVAL_PENDING displayed while P1 items stay unapplied (F-PROC-006/007; F-STAT-013). Unchanged since C8.",
         primary_evidence="records_658.jsonl status; PILOT-01/registers/corrections_register.csv (PROPOSAL_NOT_APPLIED)",
         page_reading_by="register reading (no page)", proposal_refs="C9-CP-D05; C9-CP-D06", escalation_ref="", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-D05", matter="D", novelty="EXISTING (clean re-check)",
         existing_refs="E8-XR-14; D-CV-001/002/003",
         priority_evidence_standard="P3", prior_priority_note="EXISTING",
         finding_class="RANGE_CITATION_INCLUDES_OMITTED_PROVISION",
         records_or_register_keys="CM-001; KB-030 (CM-SC-18 correct)",
         field="references",
         observation=("Range citations 'AA §§2, 108-127' (CM-001) and 'ss 2,79-85,108-130' (KB-030) include s.127, omitted by Act 37/1992 s.11 "
                      "(compilation p.36). Already proposed in CALIBRATION-02; listed for traceability only. CM-011's warning that a CoI or SoE does "
                      "not pause limitation is consistent with s.122(3), which excludes only time as a prisoner of war, in enemy territory or evading arrest."),
         primary_evidence="%s PDF p.36 (s.127 omitted), p.35 s.122(3)" % h("AA"),
         page_reading_by=READER, proposal_refs="", escalation_ref="", status="RECORDED_ELSEWHERE"),
    # ---------------- Matter E
    dict(finding_id="C9-F-E01", matter="E", novelty="EXISTING (re-confirmed)",
         existing_refs="F-JUD-017; REL-13; E8-XR-19; WSB-T-004",
         priority_evidence_standard="P1", prior_priority_note="P1",
         finding_class="INCORRECT_CITATION (pinpoint) + INCOMPLETE_HOLDING",
         records_or_register_keys="cases_53 DCLR-SC-2023-009",
         field="pinpoint_paragraphs; holding; scope_and_caveats",
         observation=("Pinpoint '11-16' falls inside 'Submissions on behalf of the private parties' (from para 4, p.3); paras 16-23 are 'The pleas of "
                      "Union of India and JAG Branch' (p.11); the Court's observations run from para 24 to the conclusion at para 32 (p.22). This is "
                      "an incorrect citation. Separately, the holding omits the para 32 ratio that Shri Kant Sharma 'does not lay down the correct "
                      "law' and that 'there is no per se restriction' on Art.226 review. That is an incomplete statement of the holding, not a wrong "
                      "one. scope_and_caveats still says the official PDF was not retrieved, but it is held."),
         primary_evidence="%s PDF p.3 (para 4 heading), p.11 (para 16 heading), p.22 para 32" % h("PARASHOTAM"),
         page_reading_by=READER, proposal_refs="C9-CP-E01; C9-CP-E02; C9-CP-E03", escalation_ref="ESC-06", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-E02", matter="E", novelty="EXISTING (relation type undecided)",
         existing_refs="REL-13; WSB-T-004 (DECLARED_NOT_GOOD_LAW); case_relations.csv",
         priority_evidence_standard="P1", prior_priority_note="",
         finding_class="RELATION_TYPE_PENDING",
         records_or_register_keys="cases_53 DCLR-SC-2015-N06 (linked: V7-JD-02, AFT-035)",
         field="relations / scope_and_caveats",
         observation=("The Shri Kant Sharma record says only that later jurisprudence 'must be displayed'; it does not record that a three-Judge "
                      "Bench declared it not to lay down the correct law. The documentary evidence for the treatment is explicit (para 32). Whether "
                      "the typed edge should be 'overrules'/'overruled_by' is a characterisation that CLAUDE.md reserves for human verification. "
                      "V7-JD-02 and AFT-035 already caveat the treatment."),
         primary_evidence="%s PDF p.22 para 32; p.27 (three signatories incl. Abhay S. Oka, B.V. Nagarathna)" % h("PARASHOTAM"),
         page_reading_by=READER, proposal_refs="C9-CP-E04", escalation_ref="ESC-06", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-E03", matter="E", novelty="NEW",
         existing_refs="",
         priority_evidence_standard="P3", prior_priority_note="",
         finding_class="INCORRECT_CITATION (pinpoint)",
         records_or_register_keys="KB-025; KB-028",
         field="references",
         observation=("KB-025 cites Parashotam 'paras 18,24-30': para 18 lies in the Union's pleas (paras 16-23), not the Court's view, and the "
                      "conclusion (para 32) is omitted. KB-028 cites 'paras 24-30' and omits para 32. The record bodies are consistent with the judgment."),
         primary_evidence="%s PDF p.11 (paras 16-23 heading), p.22 para 32" % h("PARASHOTAM"),
         page_reading_by=READER, proposal_refs="C9-CP-E05; C9-CP-E06", escalation_ref="", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-E04", matter="E", novelty="EXISTING (re-confirmed; evidence added)",
         existing_refs="OI-08; A-C2-01; E8-XR-12; identity_resolution_cycle3 RAM_AVTAR; PQ-C3-37; AUTH-J-RAM_AVTAR",
         priority_evidence_standard="P1", prior_priority_note="P1",
         finding_class="INCORRECT_CITATION (URL attached to a different judgment)",
         records_or_register_keys="cases_53 DCLR-SC-2014-A08",
         field="accessible_source_url; holding",
         observation=("The accessible URL (Diary 33390/2018, 11-Dec-2019) is the S P Rathore judgment, not the Ram Avtar order. The held official "
                      "Girish copy describes Ram Avtar (p.10, paras 13-14) as a three-Judge order of 10.12.2014 that dismissed more than 800 Union "
                      "appeals and held completion-of-tenure retirees with attributable/aggravated disability eligible for broad-banding. That is "
                      "official secondary evidence of identity and effect; the order itself is still not held."),
         primary_evidence="%s PDF p.10 paras 13-14; WS-B tools/reviewed_matches.py OR-A/OR-B notes (office reports corroborate identity metadata only)" % h("GIRISH"),
         page_reading_by=READER, proposal_refs="C9-CP-E07; C9-CP-E08", escalation_ref="ESC-08", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-E05", matter="E", novelty="NEW",
         existing_refs="WS-B tools/reviewed_matches.py (OR-B identified as office report); EVIDENCE_STANDARD 'Authority and identity' item 2",
         priority_evidence_standard="P2", prior_priority_note="",
         finding_class="INCORRECT_CITATION (source is an office report, not the judgment)",
         records_or_register_keys="PEN-J-04",
         field="references",
         observation=("PEN-J-04 (Ram Avtar) gives as its source URL a Supreme Court office report in a 2022 diary (OR-B), which corroborates "
                      "listing metadata ('Dismissed on 10.12.2014') but is not the order. Under EVIDENCE_STANDARD an office note cannot replace a judgment."),
         primary_evidence="records_658.jsonl PEN-J-04.references; WS-B-JUDGMENTS/tools/reviewed_matches.py comment block (OR-B, sha256 9c6b54b8...)",
         page_reading_by="register reading (no page)", proposal_refs="C9-CP-E09", escalation_ref="ESC-08", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-E06", matter="E", novelty="EXISTING",
         existing_refs="E8-XR-02; E8-CP-04; WSB-T-024",
         priority_evidence_standard="P2", prior_priority_note="C8 local P3; C8 indicative P2",
         finding_class="MISSING_LATER_TREATMENT (mirror evidence only)",
         records_or_register_keys="PEN-044; PEN-023; PEN-WF-08",
         field="body",
         observation=("S P Rathore (2019) is recorded as limiting Ram Avtar (no rounding-off below 20%) on an intern-mirror copy only. No official "
                      "Rathore copy is held in C9, so the C8 conditional proposal is carried forward unchanged in substance."),
         primary_evidence="WSB-T-024 (INTERN_MIRROR_SCR sha256 2f89730f3d0ae1c81a1a423f259136c4423dc8cd43d7bc75a2a2a3121eec6e38 pp.4-5 paras 8-9); official copy NOT held",
         page_reading_by="register reading (no page)", proposal_refs="C9-CP-E10", escalation_ref="ESC-08", status="PROPOSAL_NOT_APPLIED"),
    dict(finding_id="C9-F-E07", matter="E", novelty="EXISTING (classified)",
         existing_refs="C-07; LAQ-01; F-STAT-013 (severity recalibration S-02 proposes P2); F-XVOL-006; F-XVOL-007; E8-XR-22",
         priority_evidence_standard="P1", prior_priority_note="P1 (S-02 proposes P2 for F-STAT-013)",
         finding_class="INTERPRETATION_QUESTION (not a source conflict) + OMISSION",
         records_or_register_keys="CM-025; CIV-034; EV-003",
         field="body; title",
         observation=("Texts verified: AA s.133 still names the Indian Evidence Act 1872 'subject to the provisions of this Act' (p.37); BSA "
                      "s.1(2) applies the BSA to proceedings before 'Courts-martial' (p.10); s.170(2) keeps the IEA for proceedings pending immediately "
                      "before commencement (p.51); commencement 01-07-2024 is a compilation footnote (notification not held). This is an "
                      "interaction between two Acts, not a conflict between copies of one text. Classification: CM-025 and EV-003 state the s.133 "
                      "text correctly (no incorrect citation); CM-025 omits BSA s.1(2)/s.170 (omission); CIV-034's title states a timeless current-law "
                      "conclusion that the savings clause qualifies."),
         primary_evidence="%s PDF p.37 s.133; %s PDF p.10 s.1(2) and fn.1, p.51 s.170" % (h("AA"), h("BSA")),
         page_reading_by=READER, proposal_refs="C9-CP-E11; C9-CP-E12", escalation_ref="ESC-07", status="PROPOSAL_NOT_APPLIED"),
]

# ---------------------------------------------------------------- proposals
PCOLS = ["proposal_id", "overlay_version", "supersedes", "finding_ref", "matter", "target_kind", "record_id", "field",
         "current_text_quote", "proposal_type", "proposed_change", "primary_evidence", "record_level_impact",
         "priority_evidence_standard", "escalation_ref", "status"]

GIR = h("GIRISH")
MUL = h("MULLIKOTE")

PROPOSALS = [
    # ---- A
    dict(proposal_id="C9-CP-A01", supersedes="E8-CP-01", finding_ref="C9-F-A01", matter="A", target_kind="kb", record_id="AFT-013", field="body",
         current_text_quote="Tarsem Singh distinguishes a continuing wrong from stale claims and cautions against prejudice to settled third-party rights.",
         proposal_type="SUPPLEMENTATION (append; no deletion)",
         proposed_change=("Append: 'Later treatment (not exhaustive): in Union of India v Sgt Girish Kumar (2026 INSC 149, 12-02-2026) para 22 the "
                          "Supreme Court held Tarsem Singh of no assistance to the Union because the law changed after the three-Judge Ram Avtar order "
                          "of 10-12-2014 (described as in rem), and of no application where ex-servicemen already receive disability pension and seek "
                          "only re-computation (broad-banding); it also held the AFT Act s.22(1)(c) bar inapplicable to those claims. In Union of India "
                          "v Balakrishnan Mullikote (2026 INSC 286) para 43 the Court did not examine limitation and left the question of law open. "
                          "Tarsem Singh is not recorded as overruled. Whether the distinction reaches other arrears claims is for legal review.'"),
         primary_evidence="%s PDF pp.15-16 para 22; %s PDF pp.26-27 para 43" % (GIR, MUL),
         record_level_impact="V7-SC-02; V7-JD-04; DCLR-SC-2008-N10; WSB-T-005 affected list",
         priority_evidence_standard="P1", escalation_ref="ESC-01"),
    dict(proposal_id="C9-CP-A02", supersedes="E8-CP-02", finding_ref="C9-F-A01", matter="A", target_kind="kb", record_id="V7-SC-02", field="body",
         current_text_quote="compare Tarsem Singh, old PPO, refusals and statutory limitation. No promise of entire arrears.",
         proposal_type="SUPPLEMENTATION (append)",
         proposed_change=("Append: 'If the claim is a re-computation (for example broad-banding) of a disability pension already paid, read Girish "
                          "Kumar (2026 INSC 149) para 22, which held Tarsem Singh inapplicable to such claims and the AFT Act s.22(1)(c) bar "
                          "inapplicable; Mullikote (2026 INSC 286) para 43 left the general limitation question open. Seek legal review before "
                          "applying either judgment to a different claim type.'"),
         primary_evidence="%s PDF p.16 para 22; %s PDF p.27 para 43" % (GIR, MUL),
         record_level_impact="AFT-013; V7-JD-04", priority_evidence_standard="P1", escalation_ref="ESC-01"),
    dict(proposal_id="C9-CP-A03", supersedes="", finding_ref="C9-F-A02", matter="A", target_kind="kb", record_id="V7-JD-04", field="body",
         current_text_quote="this decision does not independently extend every pension limitation period.",
         proposal_type="SUPPLEMENTATION (append later-treatment note)",
         proposed_change=("Append: 'Later treatment (not exhaustive; not overruled on the documents held): DISTINGUISHED in Girish Kumar (2026 "
                          "INSC 149) para 22 for re-computation claims by existing disability pensioners, with the AFT Act s.22(1)(c) bar held "
                          "inapplicable; Mullikote (2026 INSC 286) para 43 left the limitation question open. Tarsem Singh's own text is not held; "
                          "its holding and pinpoints here are unverified.'"),
         primary_evidence="%s PDF pp.15-16 para 22; %s PDF pp.26-27 para 43; WSB-T-005; WSB-T3-003" % (GIR, MUL),
         record_level_impact="DCLR-SC-2008-N10; AFT-013; V7-SC-02", priority_evidence_standard="P1", escalation_ref="ESC-01"),
    dict(proposal_id="C9-CP-A04", supersedes="E8-CP-03", finding_ref="C9-F-A03", matter="A", target_kind="case", record_id="DCLR-SC-2008-N10",
         field="post_decision_treatment_status", current_text_quote="NOT_EXHAUSTIVELY_CHECKED",
         proposal_type="RELATION_SUPPLEMENTATION (overlay; curated field unchanged)",
         proposed_change=("Overlay edges: (1) DCLR-SC-2026-007 -> DCLR-SC-2008-N10 type=distinguishes, scope='re-computation claims by existing "
                          "disability pensioners; s.22(1)(c) AFT Act bar', effective_date=2026-02-12, evidence=Girish para 22, confidence=extracted, "
                          "human_verified=false. (2) DCLR-SC-2026-N16 -> DCLR-SC-2008-N10 observation (not a treatment): 'limitation not examined; "
                          "question of law left open', evidence=Mullikote para 43. Register: extend WSB-T-005 affected_kb_ids with AFT-013;V7-SC-02. "
                          "Keep NOT_EXHAUSTIVELY_CHECKED."),
         primary_evidence="%s PDF pp.15-16 para 22; %s PDF pp.26-27 para 43; case_relations.csv" % (GIR, MUL),
         record_level_impact="AFT-013; V7-SC-02; V7-JD-04; PEN-CS-09; WSB-T-005", priority_evidence_standard="P2", escalation_ref="ESC-01"),
    dict(proposal_id="C9-CP-A05", supersedes="", finding_ref="C9-F-A03", matter="A", target_kind="case", record_id="DCLR-SC-2008-N10",
         field="reporter_citation", current_text_quote="(2008) 8 SCC 648",
         proposal_type="METADATA_EVIDENCE_NOTE (overlay)",
         proposed_change=("Annotate: citation corroborated as printed in two held official SC copies that cite Tarsem (Girish p.6 fn; Mullikote p.26 "
                          "para 43). decision_date 2008-08-13 and C.A. 5151-5152/2008 rest on an intern mirror only. Tarsem's own official copy is "
                          "not held, and accessible_source_url is a commercial database (E8-XR-11). Acquire the official copy before relying on 'Paras 4-7'."),
         primary_evidence="%s PDF p.6; %s PDF p.26; WS-B identity_resolution.csv#TARSEM" % (GIR, MUL),
         record_level_impact="V7-JD-04 (same citation/date)", priority_evidence_standard="P3", escalation_ref=""),
    dict(proposal_id="C9-CP-A06", supersedes="", finding_ref="C9-F-A04", matter="A", target_kind="kb", record_id="PEN-045", field="body",
         current_text_quote="The Supreme Court clarified on 12 October 2026 that it cannot be read as granting disability pension and arrears in every case",
         proposal_type="VERIFICATION_FLAG (prepend; no deletion)",
         proposed_change="Prepend to that sentence: '%s'" % UNVERIFIED_CLAR,
         primary_evidence="identity_resolution_cycle3.csv#GIRISH_CLAR; SC-T2 subsequent_treatment_leads.csv#GIRISH-1",
         record_level_impact="PEN-WF-08; PEN-CS-09; PEN-J-05 (each says to read the clarification with the February judgment)",
         priority_evidence_standard="P1", escalation_ref="ESC-02"),
    dict(proposal_id="C9-CP-A07", supersedes="", finding_ref="C9-F-A04", matter="A", target_kind="kb", record_id="PEN-048", field="body",
         current_text_quote="The October 2026 Girish Kumar clarification squarely rejects universalisation of the February ruling.",
         proposal_type="VERIFICATION_FLAG (prepend; no deletion)",
         proposed_change="Prepend to that sentence: '%s'" % UNVERIFIED_CLAR,
         primary_evidence="identity_resolution_cycle3.csv#GIRISH_CLAR; SC-T2 subsequent_treatment_leads.csv#GIRISH-1",
         record_level_impact="PEN-045", priority_evidence_standard="P1", escalation_ref="ESC-02"),
    dict(proposal_id="C9-CP-A08", supersedes="", finding_ref="C9-F-A04", matter="A", target_kind="kb", record_id="PEN-J-06", field="body",
         current_text_quote="Clarifies February ruling is not universal right to disability pension and all historic arrears",
         proposal_type="VERIFICATION_FLAG (overlay)",
         proposed_change=("Overlay verification_state=UNVERIFIED_SECONDARY_ONLY; mark title citation '2026 INSC 1113' UNVERIFIED (not read from any "
                          "official source); the url field (commercial database) is a discovery lead only (E8-XR-11). Text otherwise unchanged; the "
                          "record already says 'Official PDF to be obtained'."),
         primary_evidence="identity_resolution.csv#GIRISH_CLAR (NO_MATCH_FOUND); identity_resolution_cycle3.csv#GIRISH_CLAR",
         record_level_impact="DCLR-SC-2026-008", priority_evidence_standard="P2", escalation_ref="ESC-02"),
    dict(proposal_id="C9-CP-A09", supersedes="", finding_ref="C9-F-A04", matter="A", target_kind="case", record_id="DCLR-SC-2026-007", field="scope_and_caveats",
         current_text_quote="Read together with the Supreme Court clarification dated 12 October 2026, which expressly prevents mechanical extension to every pension claim.",
         proposal_type="VERIFICATION_FLAG (overlay)",
         proposed_change="Append: '%s'" % UNVERIFIED_CLAR,
         primary_evidence="identity_resolution_cycle3.csv#GIRISH_CLAR; WSB-H-028 uncertainty",
         record_level_impact="PEN-J-05; PEN-045", priority_evidence_standard="P1", escalation_ref="ESC-02"),
    dict(proposal_id="C9-CP-A10", supersedes="", finding_ref="C9-F-A04", matter="A", target_kind="case", record_id="DCLR-SC-2026-008", field="holding",
         current_text_quote="The Court clarified that the February judgment cannot be mechanically used to claim disability pension with arrears in every case",
         proposal_type="VERIFICATION_FLAG (overlay)",
         proposed_change=("Overlay identity_state=UNRESOLVED_NO_COPY_IN_HAND and verification_state=UNVERIFIED_SECONDARY_ONLY on holding, "
                          "case_number ('Misc. Application ...') and decision_date; display the flag text '%s'" % UNVERIFIED_CLAR),
         primary_evidence="identity_resolution.csv#GIRISH_CLAR; identity_resolution_cycle3.csv#GIRISH_CLAR; pending_acquisition (PQ-C3)",
         record_level_impact="PEN-J-06; DCLR-SC-2026-007", priority_evidence_standard="P1", escalation_ref="ESC-02"),
    dict(proposal_id="C9-CP-A11", supersedes="", finding_ref="C9-F-A05", matter="A", target_kind="case", record_id="DCLR-SC-2026-007", field="commanders_summary",
         current_text_quote="Do not convert a case-specific arrears award into a universal entitlement rule.",
         proposal_type="INTERPRETATION_NOTE (append; no determination)",
         proposed_change=("Append: 'Note for legal review: the operative relief (para 23) is confined to the appellants in the listed appeals; the "
                          "reasoning (para 18) refers to a Government policy, the order of 18.04.2016, to confer arrears on all eligible pensioners from "
                          "01.01.1996 or 01.01.2006, and para 22 describes Ram Avtar as in rem. How far the judgment reaches beyond the appellants has "
                          "not been determined.'"),
         primary_evidence="%s PDF p.13 para 18; p.16 para 22; pp.16-17 para 23" % GIR,
         record_level_impact="PEN-J-05; PEN-045; PEN-CS-09", priority_evidence_standard="P2", escalation_ref="ESC-02"),
    dict(proposal_id="C9-CP-A12", supersedes="E8-CP-10--007 (citation part carried forward)", finding_ref="C9-F-A07", matter="A", target_kind="case",
         record_id="DCLR-SC-2026-007", field="pinpoint_paragraphs", current_text_quote="12–16",
         proposal_type="METADATA_SUPPLEMENTATION (overlay)",
         proposed_change=("Add pinpoints '17–22 (arrears reasoning; para 21 limitation; para 22 Tarsem Singh and s.22(1)(c))'. Supplement "
                          "neutral_citation '2026 INSC 149' as printed on p.1 (E8-CP-10--007). Optionally record '2026 SCC OnLine SC 194' as "
                          "'as cited in Mullikote 2026 INSC 286 para 43' (commercial reporter; not a source)."),
         primary_evidence="%s PDF p.1, pp.12-16; %s PDF p.26" % (GIR, MUL),
         record_level_impact="PEN-J-05 (REF V6-S18)", priority_evidence_standard="P3", escalation_ref=""),
    dict(proposal_id="C9-CP-A13", supersedes="", finding_ref="C9-F-A06", matter="A", target_kind="register",
         record_id=AW + "WS-B-JUDGMENTS/subsequent_treatment.csv#WSB-T-005", field="scope",
         current_text_quote="Tarsem held of no assistance for broad-banding re-computation claims after Ram Avtar (in rem)",
         proposal_type="REGISTER_PRECISION (overlay; frozen register unchanged)",
         proposed_change=("Overlay scope: 'Two grounds in para 22: (i) of no assistance to the Union because the legal landscape changed after Ram "
                          "Avtar (three-Judge, in rem) [p.15]; (ii) no application where claimants already receive disability pension and seek only "
                          "re-computation [p.16]; s.22(1)(c) bar not applicable.' Same precision for holdings_register.csv#WSB-H-027 ws_b_paraphrase."),
         primary_evidence="%s PDF p.15 and p.16 para 22" % GIR,
         record_level_impact="WSB-H-027; E8-CP-01/02 wording (superseded by C9-CP-A01/A02)", priority_evidence_standard="P3", escalation_ref=""),
    # ---- B
    dict(proposal_id="C9-CP-B01", supersedes="", finding_ref="C9-F-B01", matter="B", target_kind="kb", record_id="HCE-010", field="body",
         current_text_quote="the accused is invited to make a statement but is not obliged to do so",
         proposal_type="SOURCE_CONFLICT_ATTRIBUTION (replace sentence fragment; no legal determination)",
         proposed_change=("Replace the fragment with: 'the accused is asked whether he wishes to make a statement (Army Rule 23(3)).' and append the "
                          "flag: '%s' The rest of the record is unchanged; its own risk line on an inaccurate caution stays." % R23_FLAG),
         primary_evidence="%s PDF p.10 (printed p.300); %s PDF p.41; C-01; U-01" % (h("G1954"), h("AR")),
         record_level_impact="EV-016; V9-SC-19; KB-006; V9-CL-04; V9-WF-05 (harmonised by C9-CP-B02..B06)", priority_evidence_standard="P0", escalation_ref="ESC-03"),
    dict(proposal_id="C9-CP-B02", supersedes="F-XVOL-001 proposed text (updated: Gazette facsimile now held)", finding_ref="C9-F-B01", matter="B",
         target_kind="kb", record_id="EV-016", field="body", current_text_quote="make a voluntary statement after appropriate caution",
         proposal_type="SOURCE_CONFLICT_FLAG (append)", proposed_change="Append: '%s'" % R23_FLAG,
         primary_evidence="%s PDF p.10; %s PDF p.41" % (h("G1954"), h("AR")),
         record_level_impact="HCE-010", priority_evidence_standard="P0", escalation_ref="ESC-03"),
    dict(proposal_id="C9-CP-B03", supersedes="F-XVOL-002 proposal (part)", finding_ref="C9-F-B01", matter="B", target_kind="kb", record_id="V9-SC-19",
         field="body", current_text_quote="Apply voluntary statement protections and record refusal without coercion",
         proposal_type="SOURCE_CONFLICT_FLAG (append)", proposed_change="Append: '%s'" % R23_FLAG,
         primary_evidence="%s PDF p.10; %s PDF p.41" % (h("G1954"), h("AR")),
         record_level_impact="HCE-010", priority_evidence_standard="P0", escalation_ref="ESC-03"),
    dict(proposal_id="C9-CP-B04", supersedes="F-XVOL-002 proposal (part)", finding_ref="C9-F-B01", matter="B", target_kind="kb", record_id="KB-006",
         field="body", current_text_quote="Offer the accused the prescribed opportunity to make a statement and call defence evidence.",
         proposal_type="SOURCE_CONFLICT_FLAG (append)", proposed_change="Append: '%s'" % R23_FLAG,
         primary_evidence="%s PDF p.10; %s PDF p.41" % (h("G1954"), h("AR")),
         record_level_impact="HCE-010", priority_evidence_standard="P0", escalation_ref="ESC-03"),
    dict(proposal_id="C9-CP-B05", supersedes="F-XVOL-002 proposal (part)", finding_ref="C9-F-B01", matter="B", target_kind="kb", record_id="V9-CL-04",
         field="body", current_text_quote="Caution before accused voluntary statement",
         proposal_type="SOURCE_CONFLICT_FLAG (append)", proposed_change="Append: '%s'" % R23_FLAG,
         primary_evidence="%s PDF p.10; %s PDF p.41" % (h("G1954"), h("AR")),
         record_level_impact="HCE-010", priority_evidence_standard="P0", escalation_ref="ESC-03"),
    dict(proposal_id="C9-CP-B06", supersedes="F-XVOL-002 proposal (part)", finding_ref="C9-F-B01", matter="B", target_kind="kb", record_id="V9-WF-05",
         field="body", current_text_quote="5. caution accused",
         proposal_type="SOURCE_CONFLICT_FLAG (append)", proposed_change="Append: '%s'" % R23_FLAG,
         primary_evidence="%s PDF p.10; %s PDF p.41" % (h("G1954"), h("AR")),
         record_level_impact="HCE-010", priority_evidence_standard="P0", escalation_ref="ESC-03"),
    dict(proposal_id="C9-CP-B07", supersedes="", finding_ref="C9-F-B02", matter="B", target_kind="register",
         record_id=AW + "PILOT-01/registers/corrections_register.csv#F-STAT-002", field="claim",
         current_text_quote="the compilation is unreliable at this very sub-rule and the Gazette original is not held",
         proposal_type="VERIFICATION_STATE_UPDATE (overlay record)",
         proposed_change=("Overlay: 'Superseded premise: the Gazette of 27-11-1954 is held as an archival facsimile (c5ef95a9, C-01). The procedure "
                          "limbs of r.23(3) (read-over/signature; statement recorded and read over; no cross-examination on it; defence and character "
                          "witnesses) read the same in that facsimile and the compilation: SOURCE_LOCATED_CONSISTENT (facsimile, not certified). The "
                          "conflict is confined to the caution sentence (C-01). The proposal to attribute \"voluntary\" to commentary is unchanged.'"),
         primary_evidence="%s PDF p.10; %s PDF p.41" % (h("G1954"), h("AR")),
         record_level_impact="HCE-010; EV-016", priority_evidence_standard="P2", escalation_ref="ESC-03"),
    dict(proposal_id="C9-CP-B08", supersedes="", finding_ref="C9-F-B03", matter="B", target_kind="register",
         record_id=AW + "SOURCE-LIBRARY-C5/registers/source_conflict_register.csv#C5-CF-U-01", field="*",
         current_text_quote="S.R.O. 258/2002 (may not be an Army Rules instrument)",
         proposal_type="REGISTER_CONSISTENCY (overlay; frozen C5 register unchanged)",
         proposed_change=("Overlay the gap text: 'S.R.O. 258 of 27-11-2002 (not located; the India Code compilation p.39 attributes the Explanation "
                          "to r.22 to it, per AR-030 and F-MML-002; whether it also touches r.23 is unknown)'. No change to the C-01 determination."),
         primary_evidence="%s PDF p.39; ARMY-RULES-CHAIN-01 AR-030" % h("AR"),
         record_level_impact="C-01 gaps text in SOURCE-CONFLICTS-01/conflict_determinations.csv", priority_evidence_standard="P3", escalation_ref="ESC-03"),
    # ---- C
    dict(proposal_id="C9-CP-C01", supersedes="E8-CP-08", finding_ref="C9-F-C01", matter="C", target_kind="kb", record_id="ADM-022", field="body",
         current_text_quote="For non-officers §26(2) explicitly directs complaint to next superior when the complained-of officer would otherwise be recipient.",
         proposal_type="WORDING_CORRECTION (replace sentence)",
         proposed_change=("Replace with: 'For persons other than officers, §26(2) permits the aggrieved person to complain to the next superior "
                          "officer of the officer complained against, where that officer is the one to whom the complaint would otherwise be made "
                          "under §26(1). The officer who receives a complaint must investigate it as fully as possible or refer it to superior "
                          "authority (§26(3)).'"),
         primary_evidence="%s PDF p.16 s.26(1)-(3) ('may complain to such officer’s next superior officer'); government compilation only" % h("AA"),
         record_level_impact="ADM-SC-06 and ADM-020 consistent (no change); ADM-023, ADM-028 cite §§26-27 generally (no change)",
         priority_evidence_standard="P2", escalation_ref="ESC-09"),
    # ---- D
    dict(proposal_id="C9-CP-D01", supersedes="F-PROC-006 proposed text (restated)", finding_ref="C9-F-D01", matter="D", target_kind="kb", record_id="CM-011",
         field="body", current_text_quote="Apply the earliest relevant knowledge rule in Section 122(1).",
         proposal_type="WORDING_CLARIFICATION (replace sentence; disputed severity)",
         proposed_change=("Replace with: 'Identify which s.122(1) starting point applies: (a) the date of the offence; or (b) where the offence was not "
                          "known to the person aggrieved or the authority competent to initiate action, the first day it came to the knowledge of "
                          "either, whichever is earlier; or (c) where the offender was not known, the first day his identity became known to either, "
                          "whichever is earlier.'"),
         primary_evidence="%s PDF p.35 s.122(1)(a)-(c)" % h("AA"),
         record_level_impact="CM-012 (cross-reference)", priority_evidence_standard="P2", escalation_ref="ESC-05"),
    dict(proposal_id="C9-CP-D02", supersedes="F-PROC-007 proposed text (carried forward)", finding_ref="C9-F-D02", matter="D", target_kind="kb",
         record_id="CM-011", field="body", current_text_quote="Have JAG independently verify computation",
         proposal_type="SUPPLEMENTATION (append)",
         proposed_change=("Append: 'If the accused has ceased to be subject to the Act, also apply s.123(2) (see CM-012): trial must commence within "
                          "three years of cessation, excluding periods of absconding or concealment and of any injunction or order staying the "
                          "proceedings; not applicable to desertion, fraudulent enrolment or s.37 offences. Whether ss.122 and 123(2) apply "
                          "cumulatively is for legal review (LAQ-05).'"),
         primary_evidence="%s PDF p.35 s.123(1)-(2) and proviso" % h("AA"),
         record_level_impact="CM-012", priority_evidence_standard="P1", escalation_ref="ESC-05"),
    dict(proposal_id="C9-CP-D03", supersedes="", finding_ref="C9-F-D03", matter="D", target_kind="kb", record_id="CM-011", field="body",
         current_text_quote="The normal limitation is three years",
         proposal_type="TEMPORAL_SCOPE_NOTE (append)",
         proposed_change=("Append: 'Version note: the s.122(1) starting-point limbs are words substituted by Act 37 of 1992 s.9 (India Code footnote). "
                          "Act 37 of 1992 states no commencement date (AQ-05). For offences before that amendment, which version applies is for "
                          "legal review (LAQ-05).'"),
         primary_evidence="%s PDF p.35 footnote 1; C8 matrix D-AMC-AA-08-s9" % h("AA"),
         record_level_impact="CM-012", priority_evidence_standard="P2", escalation_ref="ESC-05"),
    dict(proposal_id="C9-CP-D04", supersedes="", finding_ref="C9-F-D03", matter="D", target_kind="kb", record_id="CM-012", field="body",
         current_text_quote="contains a separate three-year post-cessation timing requirement",
         proposal_type="TEMPORAL_SCOPE_NOTE (append)",
         proposed_change=("Append: 'Version note: the three-year post-cessation period in s.123(2) is words substituted by Act 37 of 1992 s.10 (India "
                          "Code footnote); commencement is not stated in that Act (AQ-05); the earlier period and its application to earlier cessation "
                          "are for legal review (LAQ-05).'"),
         primary_evidence="%s PDF p.35 footnote 2; C8 matrix D-AMC-AA-08-s10" % h("AA"),
         record_level_impact="CM-011", priority_evidence_standard="P2", escalation_ref="ESC-05"),
    dict(proposal_id="C9-CP-D05", supersedes="E8-CP-09-CM-011", finding_ref="C9-F-D04", matter="D", target_kind="kb", record_id="CM-011", field="status",
         current_text_quote="SOURCE_REVIEWED_JAG_APPROVAL_PENDING", proposal_type="CLASSIFICATION_FLAG (overlay)",
         proposed_change="Display overlay flag OPEN_P1_FINDINGS=F-PROC-007; DISPUTED=F-PROC-006 (P1 first pass / P2 provisional, D-05) beside the unchanged status.",
         primary_evidence="PILOT-01/registers/corrections_register.csv; post_review/post_review_dispositions.csv#D-05",
         record_level_impact="none beyond record", priority_evidence_standard="P2", escalation_ref=""),
    dict(proposal_id="C9-CP-D06", supersedes="E8-CP-09-CM-025", finding_ref="C9-F-D04", matter="D", target_kind="kb", record_id="CM-025", field="status",
         current_text_quote="SOURCE_REVIEWED_JAG_APPROVAL_PENDING", proposal_type="CLASSIFICATION_FLAG (overlay)",
         proposed_change="Display overlay flag OPEN_P1_FINDINGS=F-STAT-013 (severity recalibration S-02 proposes P2) beside the unchanged status.",
         primary_evidence="PILOT-01/registers/corrections_register.csv; post_review/severity_recalibration_proposals.csv#S-02",
         record_level_impact="none beyond record", priority_evidence_standard="P2", escalation_ref=""),
    # ---- E
    dict(proposal_id="C9-CP-E01", supersedes="F-JUD-017 (pinpoint part)", finding_ref="C9-F-E01", matter="E", target_kind="case", record_id="DCLR-SC-2023-009",
         field="pinpoint_paragraphs", current_text_quote="11–16 (jurisdiction discussion; confirm on official copy)",
         proposal_type="CITATION_CORRECTION (overlay)",
         proposed_change="Overlay: '24–32 (Court's observations and conclusion); paras 4–15 are the private parties' submissions and paras 16–23 the Union's pleas'.",
         primary_evidence="%s PDF p.3, p.11, p.22" % h("PARASHOTAM"),
         record_level_impact="KB-025; KB-028 (pinpoints, C9-CP-E05/E06)", priority_evidence_standard="P1", escalation_ref="ESC-06"),
    dict(proposal_id="C9-CP-E02", supersedes="F-JUD-017 (holding part)", finding_ref="C9-F-E01", matter="E", target_kind="case", record_id="DCLR-SC-2023-009",
         field="holding",
         current_text_quote="The Court distinguished Article 226 judicial review from the Article 227(4) restriction on superintendence and examined the statutory AFT appellate scheme.",
         proposal_type="HOLDING_SUPPLEMENTATION (append)",
         proposed_change=("Append: 'Para 32: Major General Shri Kant Sharma (2015) 6 SCC 773 \"does not lay down the correct law\" and conflicts with "
                          "Constitution Bench decisions (L. Chandra Kumar, S.N. Mukherjee, Rojer Mathew); \"there is no per se restriction\" on the "
                          "High Court's Art.226 power; in matters of self-discipline the principles already stated apply. Para 33: matters remanded "
                          "individually.'"),
         primary_evidence="%s PDF p.22 paras 32-33" % h("PARASHOTAM"),
         record_level_impact="DCLR-SC-2015-N06; V7-JD-02; AFT-035; KB-025; KB-028; V7-WF-08; V7-SC-18", priority_evidence_standard="P1", escalation_ref="ESC-06"),
    dict(proposal_id="C9-CP-E03", supersedes="", finding_ref="C9-F-E01", matter="E", target_kind="case", record_id="DCLR-SC-2023-009",
         field="scope_and_caveats", current_text_quote="Official Supreme Court PDF URL is known but was not retrieved successfully in this session",
         proposal_type="PROVENANCE_UPDATE (overlay)",
         proposed_change=("Overlay: 'Official court copy held (sha256 fe19875b...; 27 pp.; signature appearance not validated). Neutral citation "
                          "2023 INSC 265 is not printed on the held copy (E8-CP-10--009, unverified lead).'"),
         primary_evidence="%s; SOURCE-LIBRARY-C5 held_binaries_manifest.csv" % h("PARASHOTAM"),
         record_level_impact="none beyond record", priority_evidence_standard="P3", escalation_ref=""),
    dict(proposal_id="C9-CP-E04", supersedes="", finding_ref="C9-F-E02", matter="E", target_kind="case", record_id="DCLR-SC-2015-N06",
         field="scope_and_caveats", current_text_quote="later jurisprudence must be displayed next to this judgment.",
         proposal_type="RELATION_PROPOSAL (overlay edge; type for human decision)",
         proposed_change=("Overlay edge DCLR-SC-2023-009 -> DCLR-SC-2015-N06, effective_date=2023-03-21, evidence=para 32 ('does not lay down the "
                          "correct law'), confidence=extracted, human_verified=false, type=PENDING_LEGAL_DECISION (candidates: 'overrules' / "
                          "'declared not good law' as WSB-T-004). Display note: 'Declared not to lay down the correct law by a three-Judge Bench in "
                          "Parashotam Dass (2023) para 32.'"),
         primary_evidence="%s PDF p.22 para 32; p.27; WSB-T-004" % h("PARASHOTAM"),
         record_level_impact="V7-JD-02; AFT-035", priority_evidence_standard="P1", escalation_ref="ESC-06"),
    dict(proposal_id="C9-CP-E05", supersedes="", finding_ref="C9-F-E03", matter="E", target_kind="kb", record_id="KB-025", field="references",
         current_text_quote="paras 18,24–30", proposal_type="CITATION_CORRECTION (overlay)",
         proposed_change="Overlay SRC-PARASH locator: 'paras 24–32' (para 18 is the Union's pleas).",
         primary_evidence="%s PDF p.11, p.22" % h("PARASHOTAM"), record_level_impact="none beyond record",
         priority_evidence_standard="P3", escalation_ref=""),
    dict(proposal_id="C9-CP-E06", supersedes="", finding_ref="C9-F-E03", matter="E", target_kind="kb", record_id="KB-028", field="references",
         current_text_quote="paras 24–30", proposal_type="CITATION_CORRECTION (overlay)",
         proposed_change="Overlay SRC-PARASH locator: 'paras 24–32' (adds the conclusion, para 32).",
         primary_evidence="%s PDF p.22" % h("PARASHOTAM"), record_level_impact="none beyond record",
         priority_evidence_standard="P3", escalation_ref=""),
    dict(proposal_id="C9-CP-E07", supersedes="", finding_ref="C9-F-E04", matter="E", target_kind="case", record_id="DCLR-SC-2014-A08",
         field="accessible_source_url", current_text_quote="33390_2018_11_15_19085_Judgement_11-Dec-2019.pdf",
         proposal_type="PROVENANCE_CORRECTION (overlay)",
         proposed_change=("Overlay: relabel the URL as later_describing_judgment_url (Union of India v Wg Cdr S P Rathore, C.A. 10870/2018, 11-12-2019) "
                          "and set accessible_source_url=UNRESOLVED; record identity per identity_resolution_cycle3 proposal (SC order 10-12-2014 in "
                          "C.A. 418/2012 and connected), pending an official copy of the order (PQ-C3-37)."),
         primary_evidence="%s PDF p.10 paras 13-14; DCLR-SC-2019-A03.primary_source_url is the same URL" % GIR,
         record_level_impact="PEN-J-04; PEN-023; PEN-044; PEN-WF-08 (rely on Ram Avtar)", priority_evidence_standard="P1", escalation_ref="ESC-08"),
    dict(proposal_id="C9-CP-E08", supersedes="", finding_ref="C9-F-E04", matter="E", target_kind="case", record_id="DCLR-SC-2014-A08", field="holding",
         current_text_quote="Subsequent Supreme Court treatment describes Ram Avtar as extending rounding-off",
         proposal_type="EVIDENCE_SUPPLEMENTATION (append)",
         proposed_change=("Append: 'Official description: Girish Kumar (2026 INSC 149) paras 13-14 (p.10) describes Ram Avtar as a three-Judge order "
                          "of 10.12.2014 dismissing more than 800 Union appeals and holding completion-of-tenure retirees with attributable or "
                          "aggravated disability eligible for broad-banding. The order itself is not held.'"),
         primary_evidence="%s PDF p.10 paras 13-14 (WS-B page image cb6de66b...)" % GIR,
         record_level_impact="PEN-J-04; PEN-023; PEN-044", priority_evidence_standard="P2", escalation_ref="ESC-08"),
    dict(proposal_id="C9-CP-E09", supersedes="", finding_ref="C9-F-E05", matter="E", target_kind="kb", record_id="PEN-J-04", field="references",
         current_text_quote="officereport/2022/2165/2165_2022_2022-02-21_218.html",
         proposal_type="PROVENANCE_CORRECTION (overlay)",
         proposed_change=("Overlay: label the URL 'SC office report (identity/listing metadata only; not the judgment)'; source of the proposition = "
                          "Ram Avtar order (not held) as described in Girish paras 13-14."),
         primary_evidence="WS-B-JUDGMENTS/tools/reviewed_matches.py (OR-B); %s PDF p.10" % GIR,
         record_level_impact="DCLR-SC-2014-A08", priority_evidence_standard="P2", escalation_ref="ESC-08"),
    dict(proposal_id="C9-CP-E10", supersedes="E8-CP-04 (carried forward)", finding_ref="C9-F-E06", matter="E", target_kind="kb", record_id="PEN-044", field="body",
         current_text_quote="Ram Avtar addressed eligible personnel leaving after completion of tenure",
         proposal_type="SUPPLEMENTATION (conditional)",
         proposed_change=("After an official copy of S P Rathore (C.A. 10870/2018, 11-12-2019) is held and read: assess adding that S P Rathore paras "
                          "8-9 explained that Ram Avtar did not decide entitlement under para 8.2 and that there is no rounding-off below 20%; apply "
                          "the same assessment to PEN-023 and PEN-WF-08. Until then: no text change; extend WSB-T-024 affected_kb_ids with "
                          "PEN-023;PEN-044;PEN-WF-08."),
         primary_evidence="WSB-T-024 (intern mirror 2f89730f... pp.4-5 paras 8-9); official copy NOT held",
         record_level_impact="PEN-023; PEN-WF-08; PEN-J-04", priority_evidence_standard="P2", escalation_ref="ESC-08"),
    dict(proposal_id="C9-CP-E11", supersedes="F-STAT-013 proposed text (carried forward)", finding_ref="C9-F-E07", matter="E", target_kind="kb", record_id="CM-025",
         field="body", current_text_quote="India’s replacement evidence statute creates an important transition/savings question",
         proposal_type="SUPPLEMENTATION (append)",
         proposed_change=("Append: 'BSA s.1(2) applies the BSA to judicial proceedings before Courts-martial; under s.170(2) a trial or other proceeding "
                          "pending immediately before commencement (01-07-2024 per India Code footnote; notification not held) continues under the "
                          "Indian Evidence Act 1872. Army Act s.133 still names the 1872 Act; how s.133 is read now is for legal review (C-07, LAQ-01).'"),
         primary_evidence="%s PDF p.10, p.51; %s PDF p.37" % (h("BSA"), h("AA")),
         record_level_impact="EV-003 (duplicate statement); CIV-034; CM-026", priority_evidence_standard="P1", escalation_ref="ESC-07"),
    dict(proposal_id="C9-CP-E12", supersedes="F-XVOL-006/007 proposed text (carried forward)", finding_ref="C9-F-E07", matter="E", target_kind="kb", record_id="CIV-034",
         field="body",
         current_text_quote="The relevant commencement and savings rules, the Army Act evidence provisions and court-martial procedure must be analysed together for a particular case.",
         proposal_type="TEMPORAL_QUALIFICATION (append; title overlay)",
         proposed_change=("Title overlay: 'BSA applies to courts-martial (from 1 July 2024, subject to s.170 savings)'. Append: 'Under BSA s.170(2) a "
                          "proceeding pending immediately before 1 July 2024 is dealt with under the Indian Evidence Act 1872. Army Act s.133 still "
                          "names the 1872 Act; the interaction is unresolved pending legal review (see CM-025, EV-003).'"),
         primary_evidence="%s PDF p.10, p.51; %s PDF p.37" % (h("BSA"), h("AA")),
         record_level_impact="CM-025; EV-003; CIV-019 (generic reference)", priority_evidence_standard="P1", escalation_ref="ESC-07"),
]

# Records linked but with no direct proposal (for record_impact.csv)
LINKED = [
    ("AFT-014", "kb", "A", "C9-F-A01", "LINKED_NO_CHANGE", "WS-B crosswalk links it to Tarsem (V7-S11); repeat-representation topic; Girish distinction not engaged (C8 assessment re-confirmed)"),
    ("V7-SC-14", "kb", "A", "C9-F-A01", "LINKED_NO_CHANGE", "Crosswalk link to Tarsem; repeat-representation scenario; not engaged"),
    ("V7-SC-16", "kb", "A", "C9-F-A01", "LINKED_NO_CHANGE", "Crosswalk link to Tarsem; third-party seniority; not engaged"),
    ("PEN-CS-09", "kb", "A", "C9-F-A04", "LINKED_FLAG_INHERITS", "Already says to read Feb 2026 with Oct 2026 clarification; inherits the unverified-source flag via C9-CP-A06/A10"),
    ("PEN-WF-08", "kb", "A", "C9-F-A04; C9-F-E06", "LINKED_FLAG_INHERITS", "Step 5 refers to both Girish orders; inherits the flag; S P Rathore assessment conditional (C9-CP-E10)"),
    ("PEN-J-05", "kb", "A", "C9-F-A04; C9-F-A05", "LINKED_FLAG_INHERITS", "'MUST display 12 October 2026 clarification together' rests on the unheld order; 'case-specific' framing is ESC-02"),
    ("PEN-023", "kb", "E", "C9-F-E04; C9-F-E06", "LINKED_PENDING_CONDITION", "Relies on Ram Avtar; URL/identity correction on DCLR-SC-2014-A08; S P Rathore conditional"),
    ("PEN-J-07", "kb", "A", "C9-F-A01", "LINKED_NO_CHANGE", "Mullikote digest; para 43 'left open' observation is now cited in the Tarsem proposals; no change proposed"),
    ("ADM-SC-06", "kb", "C", "C9-F-C01", "LINKED_CONSISTENT", "'enables escalation' consistent with s.26(2)"),
    ("ADM-020", "kb", "C", "C9-F-C01", "LINKED_CONSISTENT", "Describes s.26 route and investigation/referral duties consistently"),
    ("EV-003", "kb", "E", "C9-F-E07", "LINKED_CONSISTENT", "States the s.133 text correctly and flags the interaction; duplicate of CM-025 on this point"),
    ("V7-JD-02", "kb", "E", "C9-F-E02", "LINKED_CONSISTENT", "Already caveats Shri Kant Sharma with Parashotam"),
    ("AFT-035", "kb", "E", "C9-F-E02", "LINKED_CONSISTENT", "Already says Shri Kant Sharma must be read with later treatment"),
    ("CM-001", "kb", "D", "C9-F-D05", "RECORDED_ELSEWHERE", "Range citation includes omitted s.127 (D-CV-001)"),
    ("KB-030", "kb", "D", "C9-F-D05", "RECORDED_ELSEWHERE", "Range citation includes omitted s.127 (D-CV-002)"),
    (AW + "WS-B-JUDGMENTS/holdings_register.csv#WSB-H-027", "register", "A", "C9-F-A06", "REGISTER_OVERLAY", "Paraphrase precision (C9-CP-A13)"),
    (AW + "WS-B-JUDGMENTS/subsequent_treatment.csv#WSB-T-024", "register", "E", "C9-F-E06", "REGISTER_LIST_UPDATE", "Extend affected list (C9-CP-E10)"),
]

ICOLS = ["record_id", "target_kind", "matters", "finding_refs", "proposal_refs", "impact_type", "max_priority",
         "current_status_in_snapshot", "linked_records", "note"]


# ---------------------------------------------------------------- helpers
def load_jsonl(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                o = json.loads(line)
                out[o["id"]] = o
    return out


def field_text(rec, field):
    v = rec.get(field)
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return "; ".join(v)
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def register_cell(repo, target, field):
    path, key = target.split("#", 1)
    with open(os.path.join(repo, path), encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    for row in rows[1:]:
        if row and row[0] == key:
            if field == "*":
                return " | ".join(row)
            if field not in header:
                raise SystemExit("FAIL: column %r not in %s" % (field, path))
            return row[header.index(field)]
    raise SystemExit("FAIL: key %r not found in %s" % (key, path))


def verify_quotes(repo):
    kb = load_jsonl(os.path.join(repo, KB))
    cases = load_jsonl(os.path.join(repo, CASES))
    errors = []
    for p in PROPOSALS:
        rid, fld, q = p["record_id"], p["field"], p["current_text_quote"]
        if p["target_kind"] == "kb":
            src = kb.get(rid)
            txt = field_text(src, fld) if src else None
        elif p["target_kind"] == "case":
            src = cases.get(rid)
            txt = field_text(src, fld) if src else None
        else:
            txt = register_cell(repo, rid, fld)
        if txt is None:
            errors.append("%s: record %s not found" % (p["proposal_id"], rid))
        elif q not in txt:
            errors.append("%s: quote not found in %s.%s" % (p["proposal_id"], rid, fld))
    for rid, kind, *_ in LINKED:
        if kind == "kb" and rid not in kb:
            errors.append("linked record %s not found" % rid)
        if kind == "register":
            path, key = rid.split("#", 1)
            register_cell(repo, rid, "*")
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        raise SystemExit(2)
    return kb, cases


def status_of(kb, cases, rid, kind):
    if kind == "kb":
        return kb[rid].get("status", "")
    if kind == "case":
        c = cases[rid]
        return "review_status=%s; post_decision_treatment_status=%s" % (c.get("review_status", ""), c.get("post_decision_treatment_status", ""))
    return "register row (frozen)"


PRI_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def pri_key(s):
    return PRI_ORDER.get(s[:2], 9)


def build_impact(kb, cases):
    rows = {}
    for p in PROPOSALS:
        r = rows.setdefault(p["record_id"], dict(record_id=p["record_id"], target_kind=p["target_kind"], matters=set(),
                                                  finding_refs=set(), proposal_refs=set(), impact_type="DIRECT_PROPOSAL",
                                                  pris=set(), linked=set(), note=""))
        r["matters"].add(p["matter"])
        r["finding_refs"].add(p["finding_ref"])
        r["proposal_refs"].add(p["proposal_id"])
        r["pris"].add(p["priority_evidence_standard"])
        for t in p["record_level_impact"].replace(",", ";").split(";"):
            t = t.strip().split(" ")[0]
            if (re.fullmatch(r"[A-Z][A-Z0-9]*(-[A-Z0-9]+)+", t) and not t.startswith(("C9-", "E8-"))
                    and t != p["record_id"]):
                r["linked"].add(t)
    for rid, kind, matter, frefs, itype, note in LINKED:
        r = rows.setdefault(rid, dict(record_id=rid, target_kind=kind, matters=set(), finding_refs=set(), proposal_refs=set(),
                                      impact_type=itype, pris=set(), linked=set(), note=note))
        r["matters"].add(matter)
        for fr in frefs.split(";"):
            r["finding_refs"].add(fr.strip())
        if r["impact_type"] == "DIRECT_PROPOSAL" and not r["note"]:
            r["note"] = note
    out = []
    for rid in sorted(rows):
        r = rows[rid]
        out.append(dict(record_id=rid, target_kind=r["target_kind"], matters=";".join(sorted(r["matters"])),
                        finding_refs=";".join(sorted(r["finding_refs"])), proposal_refs=";".join(sorted(r["proposal_refs"])),
                        impact_type=r["impact_type"], max_priority=(sorted(r["pris"], key=pri_key)[0] if r["pris"] else ""),
                        current_status_in_snapshot=status_of(kb, cases, rid, r["target_kind"]),
                        linked_records=";".join(sorted(r["linked"])), note=r["note"]))
    return out


def to_csv(cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue().encode("utf-8")


def outputs(repo):
    kb, cases = verify_quotes(repo)
    fids = {f["finding_id"] for f in FINDINGS}
    for p in PROPOSALS:
        assert p["finding_ref"] in fids, p["proposal_id"]
        p["overlay_version"] = "C9-v2"
        p["status"] = "PROPOSAL_NOT_APPLIED"
    findings = sorted(FINDINGS, key=lambda f: f["finding_id"])
    props = sorted(PROPOSALS, key=lambda p: p["proposal_id"])
    return {
        "consolidated_finding_register.csv": to_csv(FCOLS, findings),
        "correction_proposals_v2.csv": to_csv(PCOLS, props),
        "record_impact.csv": to_csv(ICOLS, build_impact(kb, cases)),
    }


SUMMED = ["consolidated_finding_register.csv", "correction_proposals_v2.csv", "record_impact.csv",
          "LEGAL_ADVISER_ESCALATION.md", "CORRECTIONS_C9_FINDINGS.md", "tools/build_corr.py"]


def sums(out_dir):
    lines = []
    for name in SUMMED:
        p = os.path.join(out_dir, name)
        if os.path.exists(p):
            lines.append("%s  %s\n" % (hashlib.sha256(open(p, "rb").read()).hexdigest(), name))
    return "".join(lines).encode()


def verify_held(repo, held_root):
    import fitz  # PyMuPDF
    paths = {}
    with open(os.path.join(repo, MANIFEST), encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            paths.setdefault(row["indexed_sha256"], row["held_path"])
    bad = 0
    docs = {}
    for label, sha in sorted(H.items()):
        rel = paths.get(sha)
        if not rel:
            print("NO_MANIFEST_ENTRY %s %s" % (label, sha[:8])); bad += 1; continue
        p = os.path.join(held_root, rel)
        got = hashlib.sha256(open(p, "rb").read()).hexdigest()
        ok = got == sha
        print("%s %s %s" % ("HASH_MATCH" if ok else "HASH_MISMATCH", label, sha[:8]))
        bad += 0 if ok else 1
        docs[label] = fitz.open(p)
    for label, page, anchor in ANCHORS:
        d = docs.get(label)
        if d is None:
            bad += 1; continue
        t = " ".join(d[page - 1].get_text().split())
        a = " ".join(anchor.split())
        ok = a in t
        print("%s %s p.%d %r" % ("ANCHOR_OK" if ok else "ANCHOR_MISSING", label, page, a[:60]))
        bad += 0 if ok else 1
    print("verify-held: %s (%d anchors)" % ("OK" if not bad else "FAIL", len(ANCHORS)))
    return bad == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--out-dir", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verify-held")
    a = ap.parse_args()
    outs = outputs(a.repo)
    if a.check:
        drift = 0
        for name, data in sorted(outs.items()):
            p = os.path.join(a.out_dir, name)
            same = os.path.exists(p) and open(p, "rb").read() == data
            print("%s %s" % ("OK" if same else "DRIFT", name))
            drift += 0 if same else 1
        sp = os.path.join(a.out_dir, "OUTPUT_SHA256SUMS")
        s_ok = os.path.exists(sp) and open(sp, "rb").read() == sums(a.out_dir)
        print("%s OUTPUT_SHA256SUMS" % ("OK" if s_ok else "DRIFT"))
        rc = 0 if (drift == 0 and s_ok) else 1
    else:
        for name, data in outs.items():
            with open(os.path.join(a.out_dir, name), "wb") as f:
                f.write(data)
        with open(os.path.join(a.out_dir, "OUTPUT_SHA256SUMS"), "wb") as f:
            f.write(sums(a.out_dir))
        print("wrote %d CSVs and OUTPUT_SHA256SUMS to %s" % (len(outs), a.out_dir))
        rc = 0
    pc = {}
    for p in PROPOSALS:
        k = p["priority_evidence_standard"][:2]
        pc[k] = pc.get(k, 0) + 1
    print("proposals by priority: " + ", ".join("%s=%d" % (k, pc[k]) for k in sorted(pc)) + " (total %d)" % len(PROPOSALS))
    fc = {}
    for fnd in FINDINGS:
        k = fnd["priority_evidence_standard"][:2]
        fc[k] = fc.get(k, 0) + 1
    print("findings by priority: " + ", ".join("%s=%d" % (k, fc[k]) for k in sorted(fc)) + " (total %d)" % len(FINDINGS))
    if a.verify_held:
        rc = rc or (0 if verify_held(a.repo, a.verify_held) else 1)
    sys.exit(rc)


if __name__ == "__main__":
    main()
