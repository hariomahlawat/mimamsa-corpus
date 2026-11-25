"""Source-derived test oracle for future Document Studio generation and scrutiny (C13 A6).

Independence: every case below was written by hand against the official page
transcription (spec_transcriptions.py) and the rule text read from page images
(spec_register.RULE_READINGS). No generator, validator or template engine exists
in this repository, and none was used: the oracle cannot be a generator's
self-agreement. A future generator/auditor must be tested AGAINST these cases,
and must not import this file into its own rule set.

Every synthetic document is clearly marked SYNTHETIC and contains only
placeholder values (no real person, unit, case or record). Expected results use
the Document Studio 9.1 vocabulary. Two separate expectations are recorded:
  expected_result            mechanical check outcome for the tested requirement
  expected_legal_consequence always NOT_DETERMINED (no legal conclusion is made;
                             AR 4(1)-(3) and similar provisions are for legal review)
and every case expects the operational-use gate to refuse (NOT_APPROVED).

Mutation ops (applied to the official element list of the family, in order):
  ("drop", substr)            remove the element whose label contains substr
  ("add_after", substr, text) insert a new element after it
  ("replace", substr, old, new) replace text inside that element
The build fails if a substr does not match exactly one element of the family,
so every pinpoint is checked against the official transcription.
"""

SYN = "SYNTHETIC TEST DOCUMENT - NOT A REAL RECORD - placeholder values only"
GATE = "REFUSED_RESEARCH_ONLY (legal_approval_state NOT_APPROVED; Document Studio 3.2/3.3)"
AR4 = "RR-GAZ-P2-AR4"

# (case_id, family, category, mutations, tested_requirement, expected_result, rationale, extra_refs)
CASES = [
    # ------------------------------------------------ Offence report (App III Pt II), AR54-GAZ pp.72-73
    ("OR-01", "FF-AR54-APPIII-P2", "correct", [], "all printed header items, 8 columns and signature present", "PASS_FOR_TESTED_REQUIREMENT", "matches the 1954 printed layout", []),
    ("OR-02", "FF-AR54-APPIII-P2", "defective", [("drop", "Plea")], "column 3 'Plea' present", "FAIL_SOURCE_SUPPORTED", "column 3 is printed on p.72; legal consequence of the deviation not determined (AR 4(1))", [AR4]),
    ("OR-03", "FF-AR54-APPIII-P2", "borderline", [("add_after", "Names of Witnesses", "Findings")], "column set matches the official version", "REVIEW_REQUIRED", "a 'Findings' column appears in MML 2 p.302 but not on the 1954 Gazette p.72 image; version conflict (C12 conflict queue)", []),
    ("OR-04", "FF-AR54-APPIII-P2", "defective", [("drop", "Signature of O. C. Unit.")], "signature block 'Signature of O. C. Unit.' present", "FAIL_SOURCE_SUPPORTED", "printed signature block missing; whether the report was actually signed is not verifiable from text", [AR4]),
    ("OR-05", "FF-AR54-APPIII-P2", "borderline", [("drop", "Col. 7 In cases of absence")], "printed instruction for column 7 retained", "REVIEW_REQUIRED", "omission of an instruction: AR 4(3) says omission to comply with instructions does not by itself invalidate; mechanical deviation only", [AR4]),
    ("OR-06", "FF-AR54-APPIII-P2", "defective", [("replace", "Sec. 80-82", "80-82", "83-84")], "heading cites Sec. 80-82", "FAIL_SOURCE_SUPPORTED", "Part II heading prints Sec. 80-82; 83-84 is the Appendix IV Part I heading (officers/JCOs/WOs)", []),
    # ------------------------------------------------ Summons (a), (b)
    ("SA-01", "FF-AR54-APPIII-P3A", "correct", [], "summons (a) wording and signatory", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.73", []),
    ("SA-02", "FF-AR54-APPIII-P3A", "defective", [("drop", "Whereof you shall fail at your peril.")], "warning sentence present", "FAIL_SOURCE_SUPPORTED", "printed sentence missing", [AR4]),
    ("SA-03", "FF-AR54-APPIII-P3A", "borderline", [("replace", "Commanding Officer of the accused.", "Commanding Officer of the accused.", "Adjutant (SYNTHETIC)")], "signatory designation as printed", "REVIEW_REQUIRED", "printed signatory is 'Commanding Officer of the accused'; AR 5 delegation by custom of the service is a legal question", [AR4]),
    ("SB-01", "FF-AR54-APPIII-P3B", "correct", [], "summons (b) wording and signatory", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.73", []),
    ("SB-02", "FF-AR54-APPIII-P3B", "correct", [("replace", "Convening officer (or judge-advocate", "Convening officer (or judge-advocate or presiding officer of the court or commanding officer of the accused.)", "presiding officer of the court")], "signatory within printed alternatives", "PASS_FOR_TESTED_REQUIREMENT", "presiding officer is one of the printed alternatives", []),
    ("SB-03", "FF-AR54-APPIII-P3B", "borderline", [("replace", "of the regmient", "regmient", "regiment")], "misprint corrected", "PASS_FOR_TESTED_REQUIREMENT", "correcting the printed misprint 'regmient' is harmless reflow; checker must not fail it (Document Studio 6 step 3)", []),
    # ------------------------------------------------ Summons (c) 1993
    ("SC-01", "FF-AR54-APPIII-P3C", "correct", [], "summons (c) IAFD-919C wording and signatory", "PASS_FOR_TESTED_REQUIREMENT", "as printed AR-AMD-1993 p.19; r.179(5A)", ["RR-1993-P18-179-5A"]),
    ("SC-02", "FF-AR54-APPIII-P3C", "borderline", [("replace", "IAFD-919C", "IAFD-919C", "IAFD-919A")], "form designation", "REVIEW_REQUIRED", "1993 Gazette prints IAFD-919C; MML 2 prints IAFD-919C/919A (C12 conflict queue)", []),
    ("SC-03", "FF-AR54-APPIII-P3C", "defective", [("drop", "Officer Assembling the Court of Inquiry")], "signatory 'Officer Assembling the Court of Inquiry'", "FAIL_SOURCE_SUPPORTED", "r.179(5A): summons 'under the hand of the officer assembling the Court'", ["RR-1993-P18-179-5A"]),
    ("SC-04", "FF-AR54-APPIII-P3C", "borderline", [], "purpose words after 'for' completed", "REVIEW_REQUIRED", "the word after 'for' is illegible on the official page image (p.19); checker must report source uncertainty with the page reference, not supply the word", []),
    # ------------------------------------------------ Delay report
    ("DR-01", "FF-AR54-APPIII-P4-DELAY", "correct", [], "items 1-10, subject line, signature, copy-to", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.74", []),
    ("DR-02", "FF-AR54-APPIII-P4-DELAY", "defective", [("drop", "10. Reasons for delay")], "item 10 'Reasons for delay' present", "FAIL_SOURCE_SUPPORTED", "printed item missing", [AR4]),
    ("DR-03", "FF-AR54-APPIII-P4-DELAY", "borderline", [("replace", "SUBJECT", "IST, (2ND), (3RD), (4TH), ETC, ETC,", "8TH"), ("drop", "DJAG Command")], "copy-to for 8th and subsequent reports", "REVIEW_REQUIRED", "printed instruction: HQ Command and DJAG Command copies 'In the case of the 8th and subsequent reports'; AR 4(3) omission caveat", [AR4]),
    ("DR-04", "FF-AR54-APPIII-P4-DELAY", "borderline", [("drop", "CONFIDENTIAL")], "printed 'CONFIDENTIAL' label retained", "REVIEW_REQUIRED", "the label is part of the printed form layout; effect of omitting it not determined", [AR4]),
    ("DR-05", "FF-AR54-APPIII-P4-DELAY", "defective", [("replace", "SUBJECT", "AA SEC 103 AND ARMY RULE 27", "AA SEC 102 AND ARMY RULE 26")], "statutory references in subject line as printed", "FAIL_SOURCE_SUPPORTED", "printed subject line cites AA Sec 103 and Army Rule 27", []),
    # ------------------------------------------------ Appendix IV Part I Forms 1 and 2
    ("S1-01", "FF-AR54-APPIV-P1-F1", "correct", [], "questions 1-5, finding/award block, notes", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.75", []),
    ("S1-02", "FF-AR54-APPIV-P1-F1", "defective", [("drop", "2. Have you had sufficient time")], "question 2 present", "FAIL_SOURCE_SUPPORTED", "printed question missing", [AR4]),
    ("S1-03", "FF-AR54-APPIV-P1-F1", "borderline", [("add_after", "4. Do you wish to make a statement", "ANSWER (oral statement recorded): [SYNTHETIC TEXT]")], "Note 1: oral statement in answer to question 4 not recorded", "REVIEW_REQUIRED", "printed Note 1 says the oral statement 'will not be recorded'; recording it deviates from the note (AR 4(3) caveat)", [AR4]),
    ("S1-04", "FF-AR54-APPIV-P1-F1", "borderline", [], "use of Form 1 rather than Form 2 when witnesses attended", "REVIEW_REQUIRED", "Form 1 heading condition: authority decides with written consent to dispense with witnesses; Form 2: witnesses attend. Which applied is NOT_VERIFIABLE_FROM_DOCUMENT", []),
    ("S1-05", "FF-AR54-APPIV-P1-F1", "borderline", [("drop", "5. Do you elect to be tried")], "question 5 when award is a reprimand (synthetic award: reprimand)", "NOT_APPLICABLE", "printed condition: question 5 is put only where a punishment other than reprimand, severe reprimand or penal deductions is proposed, in the case of an officer. Note (review F09): the mutation drops the question row only; the orphan 'ANSWER' line that followed it remains in the synthetic document and should be ignored or removed by the test harness", []),
    ("S2-01", "FF-AR54-APPIV-P1-F2", "correct", [], "questions 1-6 and blocks", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.76", []),
    ("S2-02", "FF-AR54-APPIV-P1-F2", "defective", [("drop", "5. Do you desire to call any witnesses")], "question 5 (defence witnesses) present", "FAIL_SOURCE_SUPPORTED", "printed question missing in Form 2", [AR4]),
    # ------------------------------------------------ Appendix IV Part II warrants
    ("WA-01", "FF-AR54-APPIV-P2-FA", "correct", [], "Form A wording, notes (a)-(f)", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.77", []),
    ("WA-02", "FF-AR54-APPIV-P2-FA", "defective", [("drop", "Signature (f)")], "signature block present", "FAIL_SOURCE_SUPPORTED", "note (f): signature of commanding officer of prisoner or other prescribed officer (see rule 166)", [AR4]),
    ("WA-03", "FF-AR54-APPIV-P2-FA", "borderline", [], "applicability of a 'transportation' warrant", "REVIEW_REQUIRED", "Form A is printed for sentences of transportation (1954); current applicability of the punishment named is a legal question outside this oracle", []),
    ("WB-01", "FF-AR54-APPIV-P2-FB", "correct", [], "Form B 1954 wording", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.78 (date basis before S.R.O. 17(E)/1993)", []),
    ("WB-02", "FF-AR54-APPIV-P2-FB", "borderline", [], "custody set-off paragraph present (controlling date after 06-12-1993)", "REVIEW_REQUIRED", "S.R.O. 17(E)/1993 item 40(a) inserts the set-off paragraph and note (ff); the checker must ask for the controlling date and not assume the 1954 text", []),
    ("WB-03", "FF-AR54-APPIV-P2-FB", "borderline", [], "inapplicable alternative struck out (note (c))", "REVIEW_REQUIRED", "both 'has been duly confirmed by' and 'is by law valid without confirmation' left standing; note (c) 'Strike out inapplicable words'", [AR4]),
    ("WB-04", "FF-AR54-APPIV-P2-FB", "defective", [("drop", "(Sentence to be entered in full, but without signature).")], "instruction to enter sentence in full without signature retained", "REVIEW_REQUIRED", "omission of an instruction (AR 4(3) caveat)", [AR4]),
    ("WC-01", "FF-AR54-APPIV-P2-FC", "correct", [], "Form C wording", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.79", []),
    ("WC-02", "FF-AR54-APPIV-P2-FC", "defective", [("replace", "The Commandant,", "The Commandant,", "The Superintendent,")], "addressee for a military prison", "FAIL_SOURCE_SUPPORTED", "Form C (military prison) is addressed to 'The Commandant'; Form B (civil prison) to 'The Superintendent'", []),
    ("WD-01", "FF-AR54-APPIV-P2-FD", "borderline", [], "form letter identification", "REVIEW_REQUIRED", "the 1954 page prints 'FORM' with no letter; identification as Form D is positional; checker must not assert a printed letter", []),
    ("WE-01", "FF-AR54-APPIV-P2-FE", "correct", [], "Form E wording", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.81 (with recorded illegible spans)", []),
    ("WF-01", "FF-AR54-APPIV-P2-FF", "correct", [], "Form F wording", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.82", []),
    ("WF-02", "FF-AR54-APPIV-P2-FF", "defective", [("drop", "(g) Enter date on which original sentence was signed.")], "note (g) present", "FAIL_SOURCE_SUPPORTED", "printed note missing (AR 4(3) caveat for legal effect)", [AR4]),
    ("WG-01", "FF-AR54-APPIV-P2-FG", "borderline", [], "receiving officer categories in operative line", "REVIEW_REQUIRED", "official p.83 operative line is partly illegible; checker must cite the page image and not complete the words from another edition", []),
    # ------------------------------------------------ Appendix V
    ("WH-01", "FF-AR54-APPV-FH", "correct", [], "Form H wording", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.84", []),
    ("WI-01", "FF-AR54-APPV-FI", "borderline", [], "rule cited in Form I heading (170 vs 170A)", "REVIEW_REQUIRED", "1954 prints Army Rule 170; S.R.O. 17(E)/1993 item 41(b) substitutes 170A; date basis decides", ["RR-1993-P18-170B1b"]),
    ("WJ-01", "FF-AR54-APPV-FJ", "correct", [], "Form J wording", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.85", []),
    ("WK-01", "FF-AR54-APPV-FK", "defective", [("drop", "(d) Name and designation of authority commuting the sentence.")], "note (d) present", "FAIL_SOURCE_SUPPORTED", "printed note missing", [AR4]),
    ("WL-01", "FF-AR54-APPV-FL", "correct", [], "Form L wording", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.86", []),
    ("W1A-01", "FF-AR54-APPV-F1A", "correct", [], "Form 1-A Parts I-III and notes", "PASS_FOR_TESTED_REQUIREMENT", "as printed 1993 p.20; r.170A(1), r.170B(3)", ["RR-1993-P18-170A1", "RR-1993-P18-170B3"]),
    ("W1A-02", "FF-AR54-APPV-F1A", "defective", [("drop", "Commissioned medical officer of the Armed Forces of India")], "medical certificate signatory capacity", "FAIL_SOURCE_SUPPORTED", "Part III prints 'Commissioned medical officer of the Armed Forces of India'", []),
    ("W1A-03", "FF-AR54-APPV-F1A", "borderline", [], "Parts II and III completed at issue", "NOT_VERIFIABLE_FROM_DOCUMENT", "r.170B(3): Parts II and III are completed after execution; a draft at issue stage must leave them blank and never pre-fill them (Document Studio 5)", ["RR-1993-P18-170B3"]),
    ("W1A-04", "FF-AR54-APPV-F1A", "borderline", [("replace", "PRAT III", "PRAT III", "PART III")], "misprint 'PRAT III' corrected", "PASS_FOR_TESTED_REQUIREMENT", "harmless correction of a printed misprint", []),
    ("W1B-01", "FF-AR54-APPV-F1B", "correct", [], "Form I-B Parts I-II and notes", "PASS_FOR_TESTED_REQUIREMENT", "as printed 1993 pp.20-21; r.170A(4)", ["RR-1993-P18-170A4"]),
    ("W1B-02", "FF-AR54-APPV-F1B", "defective", [("drop", "Superintendent of Prison")], "Part II signatory capacity", "FAIL_SOURCE_SUPPORTED", "Part II return printed for 'Signature / Superintendent of Prison'", []),
    # ------------------------------------------------ Appendix I
    ("E1-01", "FF-AR54-APPI-F1", "correct", [], "questions 1-14, declarations, certificates", "PASS_FOR_TESTED_REQUIREMENT", "as printed pp.59-65 (condition paragraphs recorded as incipits)", []),
    ("E1-02", "FF-AR54-APPI-F1", "defective", [("drop", "CERTIFICATE OF ENROLLING OFFICER")], "certificate of enrolling officer present", "FAIL_SOURCE_SUPPORTED", "printed certificate missing", [AR4]),
    ("E1-03", "FF-AR54-APPI-F1", "borderline", [], "two inapplicable sets of conditions struck out (note (e))", "REVIEW_REQUIRED", "note (e): the two sets of conditions not applicable will be struck out; whether done is a layout fact the checker must show, not decide", [AR4]),
    ("E1-04", "FF-AR54-APPI-F1", "borderline", [], "discharge-authority wording in conditions (1954 vs S.R.O. 116/1965)", "REVIEW_REQUIRED", "S.R.O. 116/1965 substitutes the discharge-authority words in two condition paragraphs; date basis decides", []),
    ("E2-01", "FF-AR54-APPI-F2", "defective", [("drop", "11. Are you willing to be enrolled in the above corps as a wet and dry sweeper")], "question 11 retained or struck out per note (dd)", "REVIEW_REQUIRED", "note (dd): question 11 is struck out for persons other than sweepers; deletion vs omission cannot be told from text alone", []),
    # ------------------------------------------------ Oaths (Army Rules)
    ("O9-01", "FF-AR54-R9-ATTEST", "correct", [], "attestation oath wording", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.2", []),
    ("O9-02", "FF-AR54-R9-ATTEST", "borderline", [("replace", "do swear in the name of God", "even to the peril of my life.", "")], "oath wording complete", "REVIEW_REQUIRED", "r.9(1) permits 'such other form to the same purport'; omission is a deviation whose effect is a legal question", []),
    ("O45-01", "FF-AR54-R45-MEMBER", "correct", [], "member oath and affirmation", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.18", []),
    ("O45-02", "FF-AR54-R45-MEMBER", "defective", [("replace", "swear by Almighty God that I will well and truly try", "will well and truly try the accused (or accused persons) before the Court according to the evidence, and that I will duly administer justice", "will to the best of my ability carry out the duties of Judge Advocate")], "member oath purpose (trial of the accused)", "REVIEW_REQUIRED", "Judge-Advocate wording used for a member; r.45 allows other form 'to the same purport' only", []),
    ("O140-01", "FF-AR54-R140-WITNESS", "borderline", [], "witness oath required in the case", "NOT_VERIFIABLE_FROM_DOCUMENT", "r.140: oath or affirmation 'if so required by the Act'; requirement depends on facts outside the document", []),
    ("O109-01", "FF-AR54-R109-SCM", "correct", [], "SCM court and interpreter oaths", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.36", []),
    # ------------------------------------------------ AFT forms
    ("AF1-01", "FF-AFTPR08-F1", "correct", [], "index, cause title, paras 1-12, verification", "PASS_FOR_TESTED_REQUIREMENT", "as printed pp.42-45", []),
    ("AF1-02", "FF-AFTPR08-F1", "defective", [("drop", "VERIFICATION")], "verification block present", "FAIL_SOURCE_SUPPORTED", "printed verification heading and text required by the form layout", []),
    ("AF1-03", "FF-AFTPR08-F1", "defective", [("drop", "3. Limitation:")], "para 3 Limitation present", "FAIL_SOURCE_SUPPORTED", "printed para 3 missing", []),
    ("AF1-04", "FF-AFTPR08-F1", "borderline", [], "affidavit under r.12A (2011 amendment)", "REVIEW_REQUIRED", "AFT (Procedure) Amendment Rules 2011 insert r.12A; its effect on Form I is not determined (C12)", []),
    ("AF1-05", "FF-AFTPR08-F1", "defective", [("drop", "1. Application along with true copy of the impugned order")], "index item 1 (true copy of impugned order)", "FAIL_SOURCE_SUPPORTED", "printed index entry missing", []),
    ("AF2-01", "FF-AFTPR08-F2", "correct", [], "receipt slip", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.46", []),
    ("AF3-01", "FF-AFTPR08-F3", "correct", [], "clerk registration form", "PASS_FOR_TESTED_REQUIREMENT", "as printed pp.46-47", []),
    ("AF3-02", "FF-AFTPR08-F3", "defective", [("drop", "Signature of the legal practitioner")], "legal practitioner signature", "FAIL_SOURCE_SUPPORTED", "printed signature block missing", []),
    ("AF3-03", "FF-AFTPR08-F3", "borderline", [("replace", "(x) Postal address:", "(x) Postal address:", "(xi) Postal address:")], "duplicated item number corrected", "PASS_FOR_TESTED_REQUIREMENT", "the official page prints '(x)' twice; renumbering is harmless", []),
    # ------------------------------------------------ Navy
    ("N13-01", "FF-NA57-S13-ALLEGIANCE", "correct", [], "s.13 oath wording", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.15", []),
    ("N13-02", "FF-NA57-S13-ALLEGIANCE", "defective", [("replace", "that I will bear true faith", "superior officer", "officer")], "statutory wording 'any superior officer'", "FAIL_SOURCE_SUPPORTED", "s.13 prescribes 'the following form' with no 'same purport' clause; legal consequence not determined", []),
    ("N13-03", "FF-NA57-S13-ALLEGIANCE", "borderline", [], "inapplicable alternative (swear / affirm) struck", "REVIEW_REQUIRED", "both alternatives left standing", []),
    ("N104-01", "FF-NA57-S104-1-MEMBER", "defective", [("replace", "that I will duly and faithfully", "administer justice according to law", "perform the duties of my office according to law")], "member oath wording", "FAIL_SOURCE_SUPPORTED", "s.104(2) trial judge advocate wording used for a member under s.104(1)", []),
    ("N104-02", "FF-NA57-S104-2-TJA", "correct", [], "trial judge advocate oath", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.40", []),
    ("NP4-01", "FF-NR65P4-S2-OATH", "correct", [], "INAS oath schedule with attestation block", "PASS_FOR_TESTED_REQUIREMENT", "as printed p.81", []),
    ("NP4-02", "FF-NR65P4-S2-OATH", "defective", [("drop", "Sworn/duly affirmed before me at")], "attestation line present", "FAIL_SOURCE_SUPPORTED", "printed attestation line missing", []),
]

# Abstention cases: the source text is not held / not officially held.
ABSTAIN = [
    ("AB-01", "FF-DPPR53-S1-F1", "DPP Rules Schedule I Form I bond", "official schedule text not held (India Code copy ends at r.34)"),
    ("AB-02", "FF-AR54-APPII-P1", "charge-sheet commencement (Appendix II)", "Appendix II official text not held; MML-only"),
    ("AB-03", "FF-ISLR38-FA", "Indian Soldiers (Litigation) Rules Form A", "only unverified MML vol 3 held"),
    ("AB-04", "FF-AR54-APPIII-SCM", "SCM proceedings form", "Appendix III Part I official text not held"),
    ("AB-05", "(Air Force form)", "Air Force enrolment / warrant form", "Air Force Rules 1969 not held; restricted RAF 2000 copy must not be used (RM-001)"),
    ("AB-06", "FF-NR65P2-F08", "Navy specimen charge sheet (Form No. 8)", "registered but fields not transcribed from the page image this cycle"),
]


def _doc(elements):
    return "\n".join([SYN] + [lab + (" [SYNTHETIC VALUE]" if kind == "blank" else "") for lab, kind in elements])


def build_oracle(trows):
    import spec_register as SR
    fam_el = {}
    pin = {}
    for r in trows:
        fam_el.setdefault(r["family"], []).append((r["label"], r["kind"]))
        pin.setdefault(r["family"], set()).add((r["source"], r["page"]))
    rr = {x["id"]: x for x in SR.RULE_READINGS}
    out = []
    for (cid, fam, cat, muts, req, exp, why, refs) in CASES:
        if fam not in fam_el:
            raise SystemExit(f"oracle {cid}: family {fam} has no official transcription")
        el = list(fam_el[fam])
        for m in muts:
            idx = [i for i, (lab, _) in enumerate(el) if m[1] in lab]
            if len(idx) != 1:
                raise SystemExit(f"oracle {cid}: '{m[1]}' matches {len(idx)} elements of {fam}")
            i = idx[0]
            if m[0] == "drop":
                el.pop(i)
            elif m[0] == "add_after":
                el.insert(i + 1, (m[2], "column" if "Findings" == m[2] else "statement"))
            elif m[0] == "replace":
                if m[2] not in el[i][0]:
                    raise SystemExit(f"oracle {cid}: replace target not in element")
                el[i] = (el[i][0].replace(m[2], m[3]), el[i][1])
        for x in refs:
            if x not in rr:
                raise SystemExit(f"oracle {cid}: unknown rule reading {x}")
        out.append(dict(case_id=cid, form_family_id=fam, category=cat, synthetic=True, marking=SYN,
                        tested_requirement=req, mutations=[list(m) for m in muts], synthetic_document=_doc(el),
                        expected_result=exp, expected_legal_consequence="NOT_DETERMINED",
                        expected_operational_gate=GATE, rationale=why,
                        source_pinpoints=sorted(f"{s} p.{p}" for s, p in pin[fam]),
                        rule_readings=[dict(id=x, source=rr[x]["source"], page=rr[x]["page"], text=rr[x]["text"]) for x in refs],
                        answer_key_basis="hand-written against official page transcription; not derived from any generator or validator",
                        legal_review="NOT_DONE (competent legal review required for high-consequence answer keys)"))
    for (cid, fam, what, why) in ABSTAIN:
        out.append(dict(case_id=cid, form_family_id=fam, category="abstain", synthetic=True, marking=SYN,
                        tested_requirement=f"request to generate or check: {what}", mutations=[],
                        synthetic_document="", expected_result="NOT_CHECKED", expected_legal_consequence="NOT_DETERMINED",
                        expected_operational_gate=GATE, rationale="checker must abstain and say why: " + why,
                        source_pinpoints=[], rule_readings=[], answer_key_basis="source-availability fact recorded in FORM_REGISTER_C13.csv / ACQUISITION_REQUESTS_A6.csv",
                        legal_review="NOT_DONE"))
    stats = dict(cases=len(out), by_category={}, by_expected_result={}, families=len({o["form_family_id"] for o in out}))
    for o in out:
        stats["by_category"][o["category"]] = stats["by_category"].get(o["category"], 0) + 1
        stats["by_expected_result"][o["expected_result"]] = stats["by_expected_result"].get(o["expected_result"], 0) + 1
    stats["by_category"] = dict(sorted(stats["by_category"].items()))
    stats["by_expected_result"] = dict(sorted(stats["by_expected_result"].items()))
    return out, stats
