"""Build the Cycle 9 Supreme Court human page-verification pack, citation/completeness register and treatment leads.

usage: python -I build_c9_pack.py <c9out_SC_dir> <c8_sc_t2_dir> [--check]
Inputs:  <c9out_SC>/tools/render_facts_c9.jsonl (render hashes, produced by render_c9.py),
         <c9out_SC>/judis_scan_c9.csv, <c9out_SC>/scr_pinpoint_check_c9.csv,
         <c8_sc_t2>/page_checks_sc_c8.csv (C8 check ids), <c8_sc_t2>/subsequent_treatment_leads.csv (carried forward verbatim).
Outputs: human_verification_checklist.csv, HUMAN_VERIFICATION_PACK.md, citation_completeness_c9.csv,
         subsequent_treatment_leads_c9.csv (all in <c9out_SC>). --check compares instead of writing (exit 1 on difference).
Content rules: identity elements only (court, parties as printed in the cause title, case number, date, bench, citation);
service numbers masked; no medical or personal details; no page text beyond those elements. Every AI reading is a
PROPOSAL by "AI agent (Claude Opus 5.5 subagent), not human-confirmed"."""
import csv, io, json, sys
from pathlib import Path

READER = "AI agent (Claude Opus 5.5 subagent), not human-confirmed"
MASK = "[service number masked]"
HELD = {  # copy key -> (copy_id, sha256, held path relative to the scratchpad root, pages)
    "RANJIT": ("C5-SRC-J-SC-1987-RANJIT-THAKUR~C1", "ed7cf31fd8fbe50822e0a60f80b96ed1187dcd465dc4ae2649424c58001ff399", "downloads/citation-codes/ranjit_judis8566.pdf", 9),
    "SNM": ("C5-SRC-J-SC-1990-SN-MUKHERJEE~C1", "eb4420801e978469e9c7407f8c079273f9cd483ad45a4427daa53e3d229969cc", "downloads/citation-codes/snmukherjee_judis7439.pdf", 23),
    "NAVJOT": ("C5-SRC-J-SC-2005-NAVJOT~C1", "3b75354869ffb928f73532f475f5f920e2f2a1f8817163caba2f7fb5e1eb215d", "downloads/independent-reviewer-B/navjot_sandhu_2005.pdf", 107),
    "DHARAMVIR": ("C5-SRC-J-SC-2013-DHARAMVIR~C1", "3056712cc7614399f72ee19f529f91990e70dba8a317dd3bd07e76e4ac546b75", "downloads/independent-reviewer-B/dharamvir_40493.pdf", 36),
    "RAJBIR_C1": ("C5-SRC-J-SC-2015-RAJBIR~C1", "970b96807bcbf8a1255fe16c574b575f64fe2edee1cbb271485fa7661a62c666", "downloads/independent-reviewer-B/rajbir_42379.pdf", 20),
    "RAJBIR_C2": ("C5-SRC-J-SC-2015-RAJBIR~C2", "c6ec489dff7a107b630a8646190a8cda303a54e4e9f5463eaed748ae0a42a1dd", "downloads/independent-reviewer/rop_275403.pdf", 21),
    "RAJBIR_C3": ("C5-SRC-J-SC-2015-RAJBIR~C3", "6b495f1483657581965b808b18aa23c09b424989e41d43226c90d35845855cde", "downloads/judgment-auditor/rajbir_bosir_2213461.pdf", 15),
    "GIRISH": ("C5-SRC-J-SC-2026-GIRISH-FEB~C1", "4f7ea3a451c6f9a11d7e4dd96822e68cd9cd7a01d8dc74cf46ad34e79029b86c", "downloads/citation-codes/girish_feb2026.pdf", 17),
    "MULLIKOTE": ("C5-SRC-J-SC-2026-MULLIKOTE~C1", "10e1954f2e39916ea0f0e8e759c3823581becf752dd6ad2e9058569a1fd97444", "downloads/citation-codes/mullikote_2026.pdf", 62),
    "PPS_BEDI": ("C5-SRC-J-SC-1982-PPS-BEDI~C1", "211dbaf4e20371cc476d09c158e41b976786d57f67336ff6fc802170178b3cca", "downloads/citation-codes/ppsbedi_judis9884.pdf", 38),
}
SHEETS = [  # (copy key, title, case record, anchor effect alone (C9 sim), role)
    ("RANJIT", "Ranjit Thakur v Union of India (1987)", "DCLR-SC-1987-R01", "6 -> 7", "ANCHOR_CANDIDATE (depends on P-D3)"),
    ("SNM", "S.N. Mukherjee v Union of India (1990)", "DCLR-SC-1990-N02", "6 -> 7", "ANCHOR_CANDIDATE (depends on P-D3)"),
    ("NAVJOT", "State (N.C.T. of Delhi) v Navjot Sandhu @ Afsan Guru (2005)", "DCLR-SC-2005-L01", "6 -> 7", "ANCHOR_CANDIDATE (depends on P-D3; C8 recommends keep PARTIAL)"),
    ("DHARAMVIR", "Dharamvir Singh v Union of India (2013)", "DCLR-SC-2013-N08", "6 -> 7", "ANCHOR_CANDIDATE"),
    ("RAJBIR_C1", "Union of India v Rajbir Singh (2015), copy C1", "DCLR-SC-2015-N09", "6 -> 7", "ANCHOR_CANDIDATE (C1 only; C2/C3 are context)"),
    ("GIRISH", "Union of India v Sgt Girish Kumar (2026 INSC 149)", "DCLR-SC-2026-007", "6 -> 7", "ANCHOR_CANDIDATE"),
    ("MULLIKOTE", "Union of India v Balakrishnan Mullikote (2026 INSC 286)", "DCLR-SC-2026-N16", "6 -> 7", "ANCHOR_CANDIDATE (C8 recommends keep PARTIAL until pp.1-31 named)"),
    ("PPS_BEDI", "Lt Col Prithi Pal Singh Bedi v Union of India (1982), baseline anchor", "DCLR-SC-1982-001", "already anchored at version 0", "CONTEXT_FOR_P-D3 (optional; no approval sought)"),
]
# (copy key, pdf page or 'last', element, AI proposal, question for the reviewer, source of the AI reading)
ITEMS = [
    ("RANJIT", 1, "court / header", "SUPREME COURT OF INDIA (database header 'http://JUDIS.NIC.IN ... Page 1 of 9')", "Is this a JUDIS database rendition (URL header, field labels, JUDIS watermark) rather than a signed court-layout judgment?", "C8-SCPIC-01"),
    ("RANJIT", 1, "parties", "PETITIONER: RANJIT THAKUR / RESPONDENT: UNION OF INDIA AND ORS.", "Confirm parties as printed.", "C8-SCPIC-01"),
    ("RANJIT", 1, "date", "DATE OF JUDGMENT 15/10/1987", "Confirm the date field.", "C8-SCPIC-01"),
    ("RANJIT", 1, "bench", "VENKATACHALLIAH, M.N. (J); SEN, A.P. (J)", "Confirm the bench field.", "C8-SCPIC-01"),
    ("RANJIT", 1, "citations (database block)", "1987 AIR 2386; 1988 SCR (1) 512; 1987 SCC (4) 611; JT 1987 (4) 93; 1987 SCALE (2)773", "Confirm the CITATION block. AIR 1987 SC 2386 is not in the case record: is it printed here?", "C8-SCPIC-01"),
    ("RANJIT", 3, "case number", "Civil Appeal No. 2630 of 1987 (after 'JUDGMENT:')", "Confirm the case number and that the HEADNOTE ends before 'JUDGMENT:' on this page.", "C8-SCPIC-02"),
    ("RANJIT", 3, "editorial note", "Headnote note: point 1.3 to be read with and subject to the subsequent order dated 10.8.88", "Is this note part of the headnote (database/reporter matter), not the judgment? (The 10.8.88 order is not held.)", "C8-SCPIC-02"),
    ("RANJIT", 4, "author", "VENKATACHALIAH, J. (judgment of the Court)", "Confirm the author line.", "C8-SCPIC-03"),
    ("RANJIT", "last", "end of text", "Ends 'N.P.V. Appeal allowed.' then report page 525; no signature lines, names or date", "Confirm there is no signature or date block (completeness against a signed original cannot be shown).", "C8-SCPIC-04"),
    ("SNM", 1, "court / header", "SUPREME COURT OF INDIA (JUDIS header, Page 1 of 23)", "JUDIS database rendition? (as for Ranjit)", "C8-SCPIC-05"),
    ("SNM", 1, "parties", "PETITIONER: S.N. MUKHERJEE / RESPONDENT: UNION OF INDIA", "Confirm parties as printed.", "C8-SCPIC-05"),
    ("SNM", 1, "date", "DATE OF JUDGMENT 28/08/1990", "Confirm the date field.", "C8-SCPIC-05"),
    ("SNM", 1, "bench", "AGRAWAL, S.C. (J); MUKHARJI, SABYASACHI (CJ); KANIA, M.H.; SHETTY, K.J. (J); SAIKIA, K.N. (J)", "Confirm five names in the bench field.", "C8-SCPIC-05"),
    ("SNM", 1, "citations (database block)", "1990 AIR 1984; 1990 SCR Supl. (1) 44; 1990 SCC (4) 594; JT 1990 (3) 630; 1990 SCALE (2)383", "Confirm the CITATION block (AIR 1990 SC 1984 is not in the case record).", "C8-SCPIC-05"),
    ("SNM", 3, "case number", "Civil Appeal No. 417 of 1984 (after 'JUDGMENT:'); headnote and cases-referred list end on this page", "Confirm the case number (the case record DCLR-SC-1990-N02 has none) and the end of the headnote.", "C8-SCPIC-06"),
    ("SNM", 4, "author", "S.C. AGRAWAL, J. (judgment of the Court)", "Confirm the author line.", "C9 reading of new render"),
    ("SNM", "last", "end of text", "Ends 'R.N.J. Appeal dismissed.' then report page 76; no signature or date block", "Confirm there is no signature or date block.", "C8-SCPIC-07"),
    ("NAVJOT", 1, "court / header", "SUPREME COURT OF INDIA (JUDIS header, Page 1 of 107); no CITATION, CITATOR or HEADNOTE block", "JUDIS database rendition without headnote?", "C8-SCPIC-08"),
    ("NAVJOT", 1, "case number", "Appeal (crl.) 373-375 of 2004; with Crl.A. 376-378, 379-380 and 381 of 2004", "Confirm the lead and connected case numbers.", "C8-SCPIC-08"),
    ("NAVJOT", 1, "parties", "STATE (N.C.T. OF DELHI) v NAVJOT SANDHU @ AFSAN GURU (connected appeals list three further accused by name)", "Confirm the lead cause title.", "C8-SCPIC-08"),
    ("NAVJOT", 1, "date", "DATE OF JUDGMENT: 04/08/2005 (read as 4 August 2005)", "DISCREPANCY Q-NAVJOT-DATE: confirm the printed string. The field does not itself show day/month order; the sibling JUDIS files print 15/10/1987, 28/08/1990 and 25/08/1982 (day first). Record whether 4 August 2005 is the reading you accept. The date is absent from the case record and C6-01 identity.", "C8-SCPIC-08"),
    ("NAVJOT", 1, "bench / author", "P. VENKATARAMA REDDI & P.P. NAOLEKAR; author P. VENKATARAMA REDDI, J.", "Confirm the bench and author.", "C8-SCPIC-08"),
    ("NAVJOT", 2, "transcription defects (optional)", "Literal escape sequences such as '\\027' appear in running text (text layer: \\005 x90, \\026 x22, \\027 x127)", "Optional: do escape sequences appear on the page image as printed characters?", "C9 reading of new render"),
    ("NAVJOT", "last", "end of text", "Ends at the operative paragraph; no signature lines, names or date", "Confirm there is no signature or date block.", "C8-SCPIC-09"),
    ("DHARAMVIR", 1, "court", "IN THE SUPREME COURT OF INDIA, CIVIL APPELLATE JURISDICTION; REPORTABLE", "Confirm court and marking.", "C8-SCPIC-10"),
    ("DHARAMVIR", 1, "case number", "CIVIL APPEAL NO. 4949 OF 2013 (arising out of SLP(C) No. 6940 of 2010)", "Confirm the case number.", "C8-SCPIC-10"),
    ("DHARAMVIR", 1, "parties", "DHARAMVIR SINGH ... APPELLANT VERSUS UNION OF INDIA & ORS. ... RESPONDENTS", "Confirm parties as printed.", "C8-SCPIC-10"),
    ("DHARAMVIR", 1, "reported citation", "No neutral or reported citation printed", "DISCREPANCY: the case record gives (2013) 7 SCC 316. Confirm it is NOT printed on this copy (so it cannot be confirmed from it).", "C8-SCPIC-10"),
    ("DHARAMVIR", "last", "bench and date", "(A.K. PATNAIK) J.; (SUDHANSU JYOTI MUKHOPADHAYA) J.; NEW DELHI, JULY 2, 2013", "Confirm bench names and place/date; signature lines are dotted placeholders.", "C8-SCPIC-11"),
    ("RAJBIR_C1", 1, "court / case number", "IN THE SUPREME COURT OF INDIA, CIVIL APPELLATE JURISDICTION; REPORTABLE; CIVIL APPEAL NO.2904 OF 2011 (with connected appeals)", "Confirm court, marking and lead case number.", "C8-SCPIC-12"),
    ("RAJBIR_C1", 1, "parties", "Union of India & Anr. ...Appellants Versus Rajbir Singh ...Respondent", "Confirm parties as printed.", "C8-SCPIC-12"),
    ("RAJBIR_C1", 1, "copy identity", "This file (970b9680...) carries a watermark and a 'Page N' footer; it does not itself bear the identifiers 'rop_275403' or 'bosir' (those are the file names of copies C2 and C3)", "DISCREPANCY Q-RAJBIR-C1: confirm you are reviewing C1 (re-hash) and that the C6-01/C5 identity string 'JUDIS 42379; rop_275403; bosir copy' is a source-level title naming all three copies, not C1's own identity.", "C8-SCPIC-12"),
    ("RAJBIR_C1", 2, "author / connected appeals", "Remaining connected C.A. numbers; author T.S. THAKUR, J.", "Confirm the author line.", "C8-SCPIC-13"),
    ("RAJBIR_C1", "last", "bench and date", "(T.S. THAKUR) J.; (R. BANUMATHI) J.; New Delhi February 13, 2015; judgment ends on p.20 of C1", "Confirm bench, date and that the judgment ends on p.20 of C1.", "C8-SCPIC-14"),
    ("RAJBIR_C2", 18, "context: end of judgment in C2", "Same operative words and bench as C1 p.20, ending on C2 p.18", "Context only: is C2 p.18 the same ending as C1 p.20 (so pinpoints differ by copy)?", "C8-SCPIC-24"),
    ("RAJBIR_C3", 1, "context: C3 rendition", "Monospaced plain-text rendition of the C2 content (non-primary; never an anchor)", "Context only: confirm C3 is a text rendition, not a court-layout copy.", "C8-SCPIC-27"),
    ("GIRISH", 1, "court / marking / neutral citation", "IN THE SUPREME COURT OF INDIA, CIVIL APPELLATE JURISDICTION; REPORTABLE; 2026 INSC 149", "DISCREPANCY: the case record reporter_citation is empty. Confirm '2026 INSC 149' is printed.", "C8-SCPIC-17"),
    ("GIRISH", 1, "case number / parties", "CIVIL APPEAL NOS.6820-6824 OF 2018; UNION OF INDIA THROUGH ITS SECRETARY & ORS. v SGT GIRISH KUMAR AND ORS. ETC.", "Confirm the lead case numbers and parties; note blank connected numbers.", "C8-SCPIC-17"),
    ("GIRISH", 1, "signature appearance", "'Signature Not Verified / Digitally signed by KAPIL TANDON / Date: 2026.02.12'", "Confirm the visible appearance (no validation is asked of you).", "C8-SCPIC-17"),
    ("GIRISH", 3, "author", "ALOK ARADHE, J.", "Confirm the author line.", "C9 reading of new render"),
    ("GIRISH", "last", "bench and date", "[PAMIDIGHANTAM SRI NARASIMHA] J.; [ALOK ARADHE] J.; NEW DELHI; FEBRUARY 12, 2026.", "Confirm bench and date.", "C8-SCPIC-18"),
    ("MULLIKOTE", 1, "markings / neutral citation", "CORRECTED; 2026 INSC 286; REPORTABLE; QR code", "Confirm the CORRECTED marking and neutral citation on p.1.", "C8-SCPIC-19"),
    ("MULLIKOTE", 1, "case number / parties", f"CIVIL APPEAL NO ____ OF 2026 (Arising out of Diary No(s). 27246/2023); UNION OF INDIA & ORS. v BALAKRISHNAN MULLIKOTE (EX HAV {MASK})", "Confirm the lead appeal number is blank and the cause title. Do not transcribe the service number.", "C8-SCPIC-19"),
    ("MULLIKOTE", 1, "signature appearance", "'Digitally signed by KAVITA PAHUJA / Date: 2026.04.04' (after the judgment date)", "Confirm the visible signing date; is any correction date printed anywhere on p.1?", "C8-SCPIC-19"),
    ("MULLIKOTE", 4, "author / numbering (version 1)", "J U D G M E N T; MANMOHAN, J.; paragraphs 1, 2, 3 then 4; questions lettered A and B", "Confirm author and numbering in the first version.", "C9 reading of new render"),
    ("MULLIKOTE", 31, "end of version 1", "Para 51 conclusion; [MANOJ MISRA,J] [MANMOHAN,J]; New Delhi; March 24, 2026", "Confirm that a complete judgment ends here (p.31 of 62).", "C8-SCPIC-20"),
    ("MULLIKOTE", 32, "start of version 2", f"Second cover: REPORTABLE; no CORRECTED marking, no neutral citation, no QR or signature appearance; service number differs from p.1 (one digit fewer) {MASK}", "DISCREPANCY Q-MULLIKOTE-VERSION: confirm a second cover begins here and compare the service number with p.1 by eye (record only SAME / DIFFERENT).", "C8-SCPIC-21"),
    ("MULLIKOTE", 35, "numbering (version 2)", "J U D G M E N T; MANMOHAN, J.; paragraphs 4, 5, 6 then 52; questions lettered C and D", "Confirm the second version continues numbering (4-6, 52-...) and re-letters the questions.", "C9 reading of new render"),
    ("MULLIKOTE", "last", "end of version 2", "Para 99 conclusion; same bench; New Delhi; March 24, 2026", "Confirm the same conclusion numbered 99. Which version is the corrected judgment? Any anchor must name pp.1-31.", "C8-SCPIC-22"),
    ("PPS_BEDI", 1, "context: JUDIS rendition profile", "JUDIS header 'Page 1 of 38'; PETITIONER: LT. COL. PRITHI PAL SINGH BEDI ETC. v UNION OF INDIA & OTHERS; DATE OF JUDGMENT25/08/1982; BENCH field repeats DESAI, D.A.; CITATION 1982 AIR 1413, 1983 SCR (1) 393, 1982 SCC (3) 140; CITATOR INFO; ACT; HEADNOTE", "Context for P-D3: same rendition type as Ranjit/S N Mukherjee/Navjot?", "C9 reading of new render"),
    ("PPS_BEDI", 7, "context: end of headnote", "Headnote ends with report pinpoints [441 F-G; 442 B]; 'JUDGMENT:' Writ Petition Nos. 4903 of 1981, 1513 of 1979 and 5930 of 1980; author DESAI, J.", "Context: pp.1-7 up to 'JUDGMENT:' are database/headnote matter.", "C9 reading of new render"),
    ("PPS_BEDI", "last", "context: end of text", "Ends 'P.B.R. Petitions dismissed.' then report page 445; no signature or date block", "Context: confirm no signature or date block.", "C9 reading of new render"),
]


def load(c9, c8):
    facts = {}
    for line in open(c9 / "tools/render_facts_c9.jsonl", encoding="utf-8"):
        o = json.loads(line)
        facts[(o["copy_key"], o["pdf_page"])] = o
    c8ids = {}
    for r in csv.DictReader(open(c8 / "page_checks_sc_c8.csv", encoding="utf-8")):
        c8ids[(r["sha256"], int(r["pdf_page"]))] = r["check_id"]
    return facts, c8ids


def csv_text(cols, rows):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return b.getvalue()


def checklist(facts):
    cols = ["item_id", "copy_key", "copy_id", "sha256_to_rehash", "held_path", "pdf_page", "render_png", "render_png_sha256", "render_settings",
            "element", "ai_proposal", "ai_reading_source", "ai_reader", "question_for_reviewer", "reviewer_name", "review_date",
            "result_CONFIRMED_or_NOT_CONFIRMED", "reviewer_notes"]
    rows, n = [], {}
    for key, page, el, prop, q, src in ITEMS:
        cid, sha, hp, pages = HELD[key]
        pn = pages if page == "last" else page
        f = facts[(key, pn)]
        n[key] = n.get(key, 0) + 1
        rows.append({"item_id": f"C9-HV-{key}-{n[key]:02d}", "copy_key": key, "copy_id": cid, "sha256_to_rehash": sha, "held_path": hp,
                     "pdf_page": pn, "render_png": f"renders/{f['png']} (not committed)", "render_png_sha256": f["png_sha256"],
                     "render_settings": f["render_settings"] + f"; {f['width']}x{f['height']} px", "element": el, "ai_proposal": prop,
                     "ai_reading_source": src, "ai_reader": READER, "question_for_reviewer": q, "reviewer_name": "", "review_date": "",
                     "result_CONFIRMED_or_NOT_CONFIRMED": "", "reviewer_notes": ""})
    return cols, rows


QUESTIONS = {
    "RANJIT": ["Headnote and database fields occupy pp.1-3 up to 'JUDGMENT:'. Should any pinpoint into pp.1-3 be refused?",
               "The editorial note refers to a subsequent order dated 10.8.88 that is not held. Note this; do not resolve it."],
    "SNM": ["The case record has no case number; the copy prints Civil Appeal No. 417 of 1984 (p.3).",
            "The recorded locator is /judgment/judis/7439.pdf, not /jonew/judis/ (path alias unverified)."],
    "NAVJOT": ["Q-NAVJOT-DATE: printed '04/08/2005'; case record and C6-01 identity have no date or case number.",
               "First-class record S-REVB-012 is SOURCE_LOCATED, not VERIFIED. No paragraph numbers (WS-B OI-11)."],
    "DHARAMVIR": ["(2013) 7 SCC 316 is in the case record but not printed on the copy."],
    "RAJBIR_C1": ["Q-RAJBIR-C1: the identity string 'JUDIS 42379; rop_275403; bosir copy' is the C5 source-level title naming all three copies; C1 is 970b9680 only.",
                  "C1 judgment ends p.20; C2 ends p.18 (C2 pp.19-21 are the Record of Proceedings); C3 is a non-primary text rendition. Pinpoints are copy-specific."],
    "GIRISH": ["'2026 INSC 149' printed; the case record's reporter_citation is empty (proposal E8-CP-10--007, not applied)."],
    "MULLIKOTE": ["Q-MULLIKOTE-VERSION: pp.1-31 (CORRECTED, paras 1-51, questions A/B) and pp.32-62 (unmarked, paras 4-6 then 52-99, questions C/D, service number differs). Which is the corrected judgment? Is a correction date printed anywhere?",
                  "Signed 2026-04-04, after the judgment date 2026-03-24. Lead appeal number blank. Any anchor must name pp.1-31."],
    "PPS_BEDI": ["Context only (baseline anchor, no approval sought): confirms the four JUDIS renditions share one profile (P-D3)."],
}


def pack_md(rows):
    out = ["# Human page-verification pack: Supreme Court anchor candidates (Cycle 9)", "",
           "**Read this first.**",
           "- Every reading in this pack is a **proposal** by an AI agent (Claude Opus 5.5 subagent). **It is not human confirmation.** Nothing here counts as a CONFIRMED identity check until a named person completes the blank fields.",
           "- The pack approves nothing, authenticates nothing and says nothing about precedent status (good law, followed, overruled). The AUTH-LEDGER stays at version 0.",
           "- Copies whose approval would create a new exact anchor: Ranjit Thakur, S N Mukherjee, Navjot Sandhu, Dharamvir Singh, Rajbir Singh C1, Girish Kumar, Mullikote. **Narsingh Yadav (\"N S Yadav\") is not included:** it has no case record, so approving it creates no anchor (C9 simulation: 6 -> 6). PPS Bedi is included as an optional context sheet for P-D3 only.",
           "- Privacy: open the held PDF or the render; do not copy page text into this pack. Record only the identity elements listed. Service numbers are masked; do not write them down. Medical and personal details must not be recorded.",
           "", "## How to review one copy",
           "1. Re-hash the held file: `sha256sum <scratchpad>/<held path>` and compare with the sha256 shown. Stop if it differs.",
           "2. Open the listed PDF pages (or regenerate the renders with `tools/render_c9.py`; each render's sha256 is given so you can check you are looking at the same image).",
           "3. For each item, compare the AI proposal with the page and fill in `reviewer_name`, `review_date`, `result_CONFIRMED_or_NOT_CONFIRMED` and `reviewer_notes` in `human_verification_checklist.csv`.",
           "4. Answer the discrepancy questions in the notes. A NOT CONFIRMED result on any identity element blocks that copy.",
           "", "Render settings for every page: PyMuPDF 2.1 (MuPDF 1.28.6), 150 dpi, grayscale, full page. All 28 pages rendered in C8 were re-rendered in C9 and are byte-identical (`tools/render_facts_c9.jsonl`, column `c8_reproduced`).", ""]
    by = {}
    for r in rows:
        by.setdefault(r["copy_key"], []).append(r)
    for key, title, case, eff, role in SHEETS:
        cid, sha, hp, pages = HELD[key]
        out += [f"## {title}", "",
                f"- Copy: `{cid}`; role: {role}; case record: {case}; anchor effect if approved alone: {eff}",
                f"- Re-hash: `{hp}` must give `{sha}` ({pages} pages)", ""]
        ctx = [k for k in ("RAJBIR_C2", "RAJBIR_C3") if key == "RAJBIR_C1"]
        items = by[key] + [r for k in ctx for r in by[k]]
        pages_open = ", ".join(sorted({str(r["pdf_page"]) for r in by[key]}, key=int))
        out += [f"- PDF pages to open: {pages_open}" + ("; context: C2 p.18, C3 p.1" if ctx else ""), ""]
        out += ["| Item | Page | Render sha256 | Element | AI proposal (not human-confirmed) | Question |", "| --- | --- | --- | --- | --- | --- |"]
        for r in items:
            pg = f"{r['pdf_page']}" + ("" if r["copy_key"] == key else f" ({r['copy_key']})")
            out.append(f"| {r['item_id']} | {pg} | `{r['render_png_sha256']}` | {r['element']} | {r['ai_proposal']} | {r['question_for_reviewer']} |")
        out += ["", "**Discrepancy questions**"] + [f"- {q}" for q in QUESTIONS[key]]
        out += ["", "| Reviewer name | Date | CONFIRMED / NOT CONFIRMED (copy as a whole) | Notes |", "| --- | --- | --- | --- |", "|  |  |  |  |", ""]
    out += ["## After review",
            "- A completed sheet is evidence for policy B2 only if the reviewer is a named person (not an AI agent) and the pages were re-hashed.",
            "- Recording a CONFIRMED check in the AUTH-LEDGER evidence, and any approval, are separate owner steps (rule-version and ledger PRs). This pack does neither.", ""]
    return "\n".join(out)


CITATION = [  # id, copy, kind, carried/new, finding, evidence, suggested owner action
    ("CC9-01", "RANJIT", "citation", "CARRIED_C8", "AIR 1987 SC 2386 printed in the database CITATION block (p.1) but absent from cases_53 DCLR-SC-1987-R01", "C8-SCPIC-01; C9 render 7e4bcd45 reproduced", "Correction proposal (case record), not applied"),
    ("CC9-02", "RANJIT", "completeness", "CARRIED_C8", "HEADNOTE and database fields pp.1-3 up to 'JUDGMENT:'; C6-01 limitation names only CITATION/CITATOR INFO", "C8-SCPIC-01/02; judis_scan_c9.csv judgment_label_page=3", "Record pp.1-3 as excluded from pinpoints"),
    ("CC9-03", "RANJIT", "completeness", "CARRIED_C8", "Headnote editorial note points to a subsequent order of 10.8.88 (DCLR-SC-1988-R02); the order is not held (WS-B RANJIT_REVIEW UNRESOLVED; PQ-C3-32)", "C8-SCPIC-02; WS-B identity_resolution_cycle3.csv#RANJIT_REVIEW", "Acquire an official copy of the review order"),
    ("CC9-04", "RANJIT", "transcription", "CARRIED_C8", "Date defect '3.?.1986' (p.3, date of the High Court order)", "text layer p.3", "Record as rendition defect"),
    ("CC9-05", "SNM", "citation", "CARRIED_C8", "cases_53 DCLR-SC-1990-N02 case_number empty; copy prints Civil Appeal No. 417 of 1984 (p.3)", "C8-SCPIC-06", "Correction proposal; none exists in C8-SOURCES correction_proposals.csv"),
    ("CC9-06", "SNM", "citation", "CARRIED_C8", "AIR 1990 SC 1984 printed in the database block, not in cases_53; cases_53 source_note ('training institute transcription') conflicts with the sci.gov.in primary_source_url", "C8-SCPIC-05; cases_53", "Correction proposal"),
    ("CC9-07", "SNM", "locator", "CARRIED_C8", "Recorded locator /judgment/judis/7439.pdf differs in path from the /jonew/judis/ family; alias unverified (Fable F-17; C8 open question 6)", "held_copies.csv#SN_MUKHERJEE", "Alias only on evidence of identical bytes (C2)"),
    ("CC9-08", "NAVJOT", "citation", "CARRIED_C8", "Judgment date 04/08/2005 and Crl.A. 373-375/2004 printed (p.1) but absent from C6-01 identity, C5 master (publication_date NOT_DETERMINED) and cases_53 (CITATION_LEAD)", "C8-SCPIC-08; SOURCE-LIBRARY-C5/registers/source_master_register.csv#C5-SRC-J-SC-2005-NAVJOT", "Correction proposal"),
    ("CC9-09", "NAVJOT", "citation", "CARRIED_C8", "(2005) 11 SCC 919 quoted only in a mirror snippet (WSB-T3-046), not printed on the held copy; cases_53 accessible_source_url is a commercial search page", "WSB-T3-046; cases_53", "Keep as unverified lead"),
    ("CC9-10", "NAVJOT", "completeness", "CARRIED_C8", "No paragraph numbering in the rendition; Anvar quotes SCC para 150 (OI-11)", "WS-B open_inconsistencies_cycle3.csv#OI-11", "Pinpoints by rendition page plus SCC para cross-reference"),
    ("CC9-11", "NAVJOT", "transcription", "NEW_C9", "Escape literals in the text layer: '\\005' x90 (C8 recorded only these) plus '\\027' x127 and '\\026' x22 (dash/quote characters lost in rendition)", "judis_scan_c9.csv escape_literals; C9 render of p.2 (7de6ee7f)", "Record all three in the rendition defect list; quotations need checking against a reported or court copy"),
    ("CC9-12", "DHARAMVIR", "citation", "CARRIED_C8", "(2013) 7 SCC 316 (cases_53) not printed on the copy; '2013 INSC 408' only from mirror/spec (E8-CP-10--N08: no supplementation)", "C8-SCPIC-10; C8-SOURCES correction_proposals.csv#E8-CP-10--N08", "None; cannot be confirmed from this copy"),
    ("CC9-13", "DHARAMVIR", "metadata", "CARRIED_C8+REFINED", "copy_structure.csv producer shown as '?' characters; C9 decodes it as UTF-16BE: 'LibreOffice 3.6; modified using iText 2.1.7 by 1T3XT'. The baseline Anvar copy (06f77a70) has the same mis-decoded producer", "judis_scan_c9.csv producer; AUTH-LEDGER/evidence/copy_structure.csv#C5-SRC-J-SC-2013-DHARAMVIR~C1", "Correct the producer decoding in the evidence builder (rule-2/evidence PR)"),
    ("CC9-14", "RAJBIR_C1", "identity", "CARRIED_C8+REFINED", "The string 'JUDIS 42379; rop_275403; bosir copy' is the frozen C5 source-level title (source_master_register) naming all three copies; C6-01 copied it into C1's copy-level document_identity, and C8-SOURCES source_to_record_gap_matrix.csv row 45 repeats it", "SOURCE-LIBRARY-C5/registers/source_master_register.csv#C5-SRC-J-SC-2015-RAJBIR; C6-01 draft; C8-SOURCES/PRIMARY-SOURCES/source_to_record_gap_matrix.csv", "Use a copy-level identity for C1 in any real entry"),
    ("CC9-15", "RAJBIR_C1", "completeness", "CARRIED_C8", "cases_53 primary_source_url empty although an official-path copy is held; C1 (20 pp.) and C2 (judgment on 18 pp.) paginate differently", "C8-SCPIC-14, 24", "Copy-specific pinpoints"),
    ("CC9-16", "NSY", "identity", "CARRIED_C8+REFINED", "Printed appellant name 'NARSINGH YADAV' vs corpus label 'N S Yadav' (C5 master, target_publications, C6-01, C8-SOURCES pension_source_coverage J-NSYADAV-2019); C5 master publication_date NOT_DETERMINED although 'OCTOBER 03, 2019' is printed (p.15); no cases_53 record", "C8-SCPIC-15/16; SOURCE-LIBRARY-C5/registers/source_master_register.csv#C5-SRC-J-SC-2019-NS-YADAV", "Correction proposal; decide whether a case record is needed"),
    ("CC9-17", "NSY", "privacy", "NEW_C9", "WS-B subsequent_treatment_cycle3.csv#WSB-T3-011 records a mirror document identifier that embeds the appellant's service number [masked]", "WS-B-JUDGMENTS/subsequent_treatment_cycle3.csv#WSB-T3-011 (later_judgment column)", "Owner: mask the identifier in WS-B registers"),
    ("CC9-18", "GIRISH", "citation", "CARRIED_C8", "cases_53 reporter_citation empty although '2026 INSC 149' is printed; proposal E8-CP-10--007 exists, PROPOSAL_NOT_APPLIED", "C8-SCPIC-17; C8-SOURCES correction_proposals.csv#E8-CP-10--007", "Apply via owner-approved correction"),
    ("CC9-19", "GIRISH", "completeness", "CARRIED_C8", "Several connected civil appeal numbers printed blank ('NO(S). ___ OF 2026') on pp.1-3", "C8-SCPIC-17; C9 render p.3 (922120cb)", "Record as printed"),
    ("CC9-20", "MULLIKOTE", "completeness", "CARRIED_C8", "One file holds two versions: pp.1-31 CORRECTED (paras 1-51) and pp.32-62 unmarked (paras 4-6, 52-99); service number differs between p.1 and p.32 [masked]; lead appeal number blank; signed 2026-04-04 after judgment date 2026-03-24; no correction date printed (OI-03, OQ-10)", "C8-SCPIC-19..22", "Owner: canonical version; any anchor names pp.1-31"),
    ("CC9-21", "MULLIKOTE", "completeness", "NEW_C9", "Version 2 also re-letters the two substantial questions (A/B in version 1, C/D in version 2), consistent with numbering continued from version 1; author line MANMOHAN, J. in both versions (pp.4, 35)", "C9 renders p.4 (11bad34f), p.35 (e0e2b8b1)", "Evidence for the version question; no conclusion drawn"),
    ("CC9-22", "MULLIKOTE", "rule", "NEW_C9", "C5 master completeness_status for Mullikote reads 'full judgment file held (page completeness not re-checked ...)', so rule 1's completeness test cannot see the duplication; the simulated anchor is file-level (62 pp.)", "SOURCE-LIBRARY-C5/registers/source_master_register.csv#C5-SRC-J-SC-2026-MULLIKOTE; ledger.py _evidence_checks", "Rule 2: page-range anchors"),
    ("CC9-23", "PPS_BEDI", "classification", "NEW_C9", "Cycle 4 register limitation calls the copy a 'Historic JUDIS scan', but the file has 0 embedded images and a text layer on all 38 pages: it is a Ghostscript typed-text rendition, not a scan", "judis_scan_c9.csv (image_count 0); CALIBRATION-02/registers/source_authentication_register.csv (211dbaf4 limitations)", "Documentary note (corrections/notes.csv) after owner decision; frozen text not edited"),
    ("CC9-24", "PPS_BEDI", "completeness", "NEW_C9", "Database/headnote matter runs pp.1-7 up to 'JUDGMENT:' (longer than Ranjit/S N Mukherjee pp.1-3); inline report pages 394-445 continuous; ends with reporter tag 'P.B.R. Petitions dismissed.'; no signature or date block; BENCH field repeats 'DESAI, D.A.'", "judis_scan_c9.csv; C9 renders p.1 (50ffbe69), p.7 (6fd04e35), p.38 (17a2d5bb)", "Pinpoints into pp.1-7 to be refused"),
    ("CC9-25", "PPS_BEDI", "transcription", "NEW_C9", "Probable transcription defect: '2S' where a rule number is expected (p.7, list of rules challenged)", "C9 render p.7 (6fd04e35)", "Record in the rendition defect list"),
    ("CC9-26", "PPS_BEDI", "pinpoint", "NEW_C9", "WS-B holdings_register.csv#WSB-H-053 states PDF pp.19-21 with 'SCR p.426-427', but SCR pp.426-427 fall on PDF pp.25-27 of the held rendition (pp.19-21 carry SCR 416-420); one of the two locators is wrong", "scr_pinpoint_check_c9.csv (INCONSISTENT); other 5 SCR pinpoints into JUDIS renditions CONSISTENT", "WS-B owner to re-check; no correction made here"),
    ("CC9-27", "PPS_BEDI", "evidence class", "NEW_C9", "WS-B OI-06 describes the '[1964] 5 SCR 931' reading as from the 'official PPS Bedi p.2 list'; that list is the rendition's cases-referred headnote matter (database/editorial), as WS-B's own RAM_SARUP resolution notes ('editorial list')", "WS-B open_inconsistencies_cycle3.csv#OI-06; identity_resolution_cycle3.csv#RAM_SARUP", "Label the evidence as database editorial matter, not judgment text"),
    ("CC9-28", "PPS_BEDI", "rule", "NEW_C9", "PPS Bedi has no row in AUTH-LEDGER/evidence/copy_facts.csv and no page-image check, so rule 1 cannot validate a documented CORRECTION of its class (option (b) as NON_PRIMARY_OFFICIAL_COURT_RENDITION fails; only an AUTHENTICATION_PENDING demotion validates)", "exact_anchor_simulations_c9.json option_b.b1 (FAIL reason) vs b2/b3 (PASS)", "Owner: P-D3; evidence addition needed before any documented re-classification"),
    ("CC9-29", "ANVAR", "classification", "NEW_C9 (INFO)", "Baseline anchor Anvar (06f77a70, /jonew/judis/41931.pdf) is a court-layout PDF from a JUDIS path, like Dharamvir and Rajbir C1: a /judis/ path does not imply a database rendition. Exactly four held files are JUDIS typed-text renditions (PPS Bedi, Ranjit, S N Mukherjee, Navjot)", "judis_scan_c9.csv profile column", "None; supports treating the rendition type, not the path, under P-D3"),
]


def cc_text():
    cols = ["finding_id", "copy", "kind", "status", "finding", "evidence", "suggested_owner_action", "recorded_by"]
    return csv_text(cols, [dict(zip(cols, c + ("AI agent (Claude Opus 5.5 subagent); readings not human-confirmed",))) for c in CITATION])


NEW_LEADS = [  # lead_id, case53_id, copy_id, judgment, question, corpus says, c9 note
    ("PPSBEDI-1", "DCLR-SC-1982-001", "C5-SRC-J-SC-1982-PPS-BEDI~C1", "Lt Col Prithi Pal Singh Bedi v UOI (25-08-1982)", "Was the s.130 objection-procedure proposition followed by Ranjit Thakur, and to what extent?", "WS-B subsequent_treatment_cycle3.csv#WSB-T3-001: Ranjit (official copy p.6, para 5) FOLLOWED (relied on 'Prithvi Pal Singh v. Union of India, AIR 1982 SC 1413')", "The PPS Bedi rendition's JUDIS CITATOR INFO (database matter, p.1) lists 'F 1987 SC2386 (5)'; AIR 1987 SC 2386 is the AIR citation printed in Ranjit's own CITATION block. Two signals, neither a verified treatment finding; citator codes are not defined on the copy"),
    ("PPSBEDI-2", "DCLR-SC-1982-001", "C5-SRC-J-SC-1982-PPS-BEDI~C1", "Lt Col Prithi Pal Singh Bedi v UOI (25-08-1982)", "Effect of later amendment of Army Rules 22-25 (rule 25 omitted, rule 22 substituted) on the 1982 reasoning", "WS-B subsequent_treatment.csv#WSB-T-028 LEGISLATIVELY_OVERTAKEN_PROPOSED (S.R.O. 17(E)/1993 per ARMY-RULES-CHAIN-01; effective date NOT_DETERMINED); holdings WSB-H-032, WSB-H-052", "Legislative change, not judicial treatment; statutory currency to be established from the statutory corpus"),
    ("PPSBEDI-3", "DCLR-SC-1982-001", "C5-SRC-J-SC-1982-PPS-BEDI~C1", "Lt Col Prithi Pal Singh Bedi v UOI (25-08-1982)", "Later citations of PPS Bedi (relied on / referred / distinguished)", "case_relations.csv: Virendra cites PPS Bedi (OQ-D-009); WSB-T3-048..061 mirror citations, CITED_TREATMENT_NOT_CLASSIFIED (several labelled SCR headnote/case list, editorial)", "JUDIS CITATOR INFO p.1 also lists R 1989 SC 611; RF 1990 SC 65; R 1991 SC 558; RF 1991 SC1617; R 1992 SC 1 (database material, unverified)"),
    ("PPSBEDI-4", "DCLR-SC-1982-001", "C5-SRC-J-SC-1982-PPS-BEDI~C1", "Lt Col Prithi Pal Singh Bedi v UOI (25-08-1982)", "Curated pinpoints '40' and '14' cannot be located in the unnumbered rendition", "WS-B OI-12 OPEN", "Pinpoints should use rendition page plus SCR page (scr_pinpoint_check_c9.csv); WSB-H-053 locator inconsistent (CC9-26)"),
    ("RANJIT-4", "DCLR-SC-1987-R01", "C5-SRC-J-SC-1987-RANJIT-THAKUR~C1", "Ranjit Thakur v UOI (15-10-1987)", "Identity and treatment of the later judgment printed as '1991 SC1617', which appears in both the Ranjit citator (D) and the PPS Bedi citator (RF)", "No corpus record resolves '1991 SC 1617'", "Database citator entries only; identify the judgment from an official source before any edge is proposed"),
    ("SNM-4", "DCLR-SC-1990-N02", "C5-SRC-J-SC-1990-SN-MUKHERJEE~C1", "S N Mukherjee v UOI (28-08-1990)", "Further later citations of S N Mukherjee located by WS-B name scan", "WSB-T3-029 (2023 mirror document), WSB-T3-066 (1992 mirror document, case list), WSB-T3-077 (2021 mirror document): CITED_TREATMENT_NOT_CLASSIFIED", "Mirror copies only; the official copies were not read"),
    ("NAVJOT-4", "DCLR-SC-2005-L01", "C5-SRC-J-SC-2005-NAVJOT~C1", "State (NCT of Delhi) v Navjot Sandhu (04-08-2005)", "Fidelity of quoted passages in the rendition, given lost characters", "C8-SOURCES high_risk_record_review.csv row 31 (judicial_overruling; CITATION_LEAD_ONLY)", "Escape literals \\005, \\026, \\027 (CC9-11) mean quotations from this rendition need checking against a reported or court copy before any treatment analysis relies on wording"),
    ("GIRISH-3", "DCLR-SC-2026-007", "C5-SRC-J-SC-2026-GIRISH-FEB~C1", "UOI v Sgt Girish Kumar, 2026 INSC 149 (12-02-2026)", "Propagation of Girish para 22 (Tarsem held inapplicable to broad-banding claims) into KB records", "C8-SOURCES correction_proposals.csv#E8-CP-01..03 (PROPOSAL_NOT_APPLIED); WSB-T-005, WSB-T-025", "Proposals only; the 12-10-2026 clarification (not held) may bear on the same paragraph"),
    ("MULLIKOTE-4", "DCLR-SC-2026-N16", "C5-SRC-J-SC-2026-MULLIKOTE~C1", "UOI v Balakrishnan Mullikote (24-03-2026)", "Dependent KB records whose pinpoints must follow the canonical version once chosen", "C8-SOURCES pension_record_dependency.csv: PEN-002, PEN-004, PEN-007, PEN-011, PEN-046, PEN-J-07, PEN-WF-10 depend on J-MULLIKOTE-2026", "Version question (CC9-20/21) precedes any treatment analysis"),
]


def leads_text(c8):
    c8rows = list(csv.DictReader(open(c8 / "subsequent_treatment_leads.csv", encoding="utf-8")))
    cols = ["lead_id", "case53_id", "copy_id", "judgment", "question_requiring_examination", "corpus_currently_says", "note", "origin", "status"]
    import re
    m = lambda t: re.sub(r"\b\d{6,8} ?M\b", MASK, t)
    rows = [{k: m(v) for k, v in {"lead_id": r["lead_id"], "case53_id": r["case53_id"], "copy_id": r["copy_id"], "judgment": r["judgment"],
             "question_requiring_examination": r["question_requiring_examination"], "corpus_currently_says": r["corpus_currently_says"],
             "note": r["c8_note"], "origin": "C8 (carried forward verbatim; service numbers masked)", "status": "RESEARCH_LEAD_UNVERIFIED"}.items()} for r in c8rows]
    rows += [{"lead_id": a, "case53_id": b, "copy_id": c, "judgment": d, "question_requiring_examination": e, "corpus_currently_says": f,
              "note": g, "origin": "C9 (WS-B registers and held copies)", "status": "RESEARCH_LEAD_UNVERIFIED"} for a, b, c, d, e, f, g in NEW_LEADS]
    return csv_text(cols, rows)


def main():
    argv = [a for a in sys.argv[1:] if a != "--check"]
    c9, c8 = Path(argv[0]), Path(argv[1])
    facts, _ = load(c9, c8)
    cols, rows = checklist(facts)
    outs = {"human_verification_checklist.csv": csv_text(cols, rows), "HUMAN_VERIFICATION_PACK.md": pack_md(rows),
            "citation_completeness_c9.csv": cc_text(), "subsequent_treatment_leads_c9.csv": leads_text(c8)}
    if "--check" in sys.argv[1:]:
        bad = [n for n, t in outs.items() if not (c9 / n).is_file() or (c9 / n).read_text(encoding="utf-8") != t]
        print("CHECK", "OK" if not bad else f"DIFFERS: {bad}")
        sys.exit(1 if bad else 0)
    for n, t in outs.items():
        (c9 / n).write_text(t, encoding="utf-8")
    print({n: t.count("\n") for n, t in outs.items()})


if __name__ == "__main__":
    main()
