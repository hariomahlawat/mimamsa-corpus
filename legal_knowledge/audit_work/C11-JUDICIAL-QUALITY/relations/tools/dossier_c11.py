"""PRIORITY_TREATMENT_DOSSIER.md builder for relations_c11.

Graph-derived sections are computed from the builder's tables. The "verified readings" are AI-agent readings of the
text layer (ad77758d), embedded here and re-checked verbatim (whitespace-insensitive) against the stated PDF page on
every build: the build fails if any quotation is not found on its page.
"""
import re
from collections import Counter, defaultdict

# ----------------------------------------------------------------------------- priority cases
PRIORITY = [
    {"key": "TARSEM", "label": "Union of India v. Tarsem Singh", "cur": "DCLR-SC-2008-N10",
     "doc_ids": ["sc-2008-union-of-india-ors-2008insc930"]},
    {"key": "GIRISH", "label": "Union of India v. Sgt Girish Kumar (main judgment, 12-02-2026)", "cur": "DCLR-SC-2026-007",
     "doc_ids": ["sc-2026-union-of-india-through-its-sec-2026insc149"]},
    {"key": "GIRISH_CLAR", "label": "Union of India v. Sgt Girish Kumar (reported clarification order, 12-10-2026)",
     "cur": "DCLR-SC-2026-008", "doc_ids": []},
    {"key": "SHRIKANT", "label": "Union of India v. Major General Shri Kant Sharma", "cur": "DCLR-SC-2015-N06",
     "doc_ids": ["sc-2015-union-of-india-ors-2015insc206"]},
    {"key": "PARASHOTAM", "label": "Union of India v. Parashotam Dass", "cur": "DCLR-SC-2023-009",
     "doc_ids": ["sc-2023-union-of-india-ors-2023insc265"]},
    {"key": "RANJIT", "label": "Ranjit Thakur v. Union of India", "cur": "DCLR-SC-1987-R01",
     "doc_ids": ["sc-1987-ranjit-thakur-1987insc285"]},
    {"key": "SNM", "label": "S. N. Mukherjee v. Union of India", "cur": "DCLR-SC-1990-N02",
     "doc_ids": ["sc-1990-s-n-mukherjee-1990insc257"]},
    {"key": "RAMAVTAR", "label": "Union of India v. Ram Avtar (order of 10-12-2014)", "cur": "DCLR-SC-2014-A08",
     "doc_ids": [], "raw_keys": ["SCCOL|2014|SC|1761", "CASE|CA|418|2012"], "name_rx": r"\bRam\s+Avtar\b"},
    {"key": "DHARAMVIR", "label": "Dharamvir Singh v. Union of India", "cur": "DCLR-SC-2013-N08",
     "doc_ids": ["sc-2013-dharamvir-singh-2013insc408"]},
]

READINGS = [
    # id, case, doc_id, pdf page, paragraph, kind, quote, note
    ("RD-TARSEM-H1", "TARSEM", "sc-2008-union-of-india-ors-2008insc930", 5, "5", "HOLDING",
     "will restrict the consequential relief relating to arrears normally",
     "SCR rendition [2008] 12 SCR 104 (AWS e-SCR mirror; not a signed court copy). Para 5 continues 'to a period of three "
     "years prior to the date of filing of tlie writ petition' (OCR noise in the text layer)."),
    ("RD-TARSEM-H2", "TARSEM", "sc-2008-union-of-india-ors-2008insc930", 6, "6", "HOLDING",
     "It ought to have restricted the relief relating to ar- rears to only three years before the date of writ petition",
     "Operative direction on the facts (16 years' delay). Two-Judge Bench per the printed bench line."),
    ("RD-GIRISH-T1", "GIRISH", "sc-2026-union-of-india-through-its-sec-2026insc149", 11, "22", "TREATMENT",
     "The reliance placed by the appellant on the decision of a two-Judge Bench of this Court in Tarsem Singh (supra) is "
     "of no assistance to it, as the legal landscape did not remain static after decision in Tarsem Singh.",
     "Girish's own wording (court voice, not a submission or quotation). First ground: later three-Judge Bench order in Ram Avtar."),
    ("RD-GIRISH-T2", "GIRISH", "sc-2026-union-of-india-through-its-sec-2026insc149", 11, "22", "TREATMENT",
     "the decision in Tarsem Singh (supra) has no application to the case in hand as ex-servicemen in the instant appeals "
     "are already in receipt of disability pension",
     "Second, fact-based ground (claimants already in receipt of pension; only re-computation sought)."),
    ("RD-GIRISH-T3", "GIRISH", "sc-2026-union-of-india-through-its-sec-2026insc149", 11, "22", "TREATMENT",
     "decided the issue of applicability of instruction dated 31.01.2001 and the aforesaid decision is in rem.",
     "Characterises Ram Avtar as a decision in rem."),
    ("RD-GIRISH-H1", "GIRISH", "sc-2026-union-of-india-through-its-sec-2026insc149", 11, "22", "HOLDING",
     "Therefore, the bar contained in Section 22(1)(c) of the Act has no application to the",
     "Sentence continues on p.12: 'claims filed by the ex-servicemen before the Tribunal.'"),
    ("RD-GIRISH-R1", "GIRISH", "sc-2026-union-of-india-through-its-sec-2026insc149", 9, "14", "TREATMENT",
     "The legal position continued to be uncertain until it was settled by a three-Judge bench of this Court in Union of "
     "India & Others v. Ram Avtar (supra).", "Girish's account of Ram Avtar (not held in the corpus)."),
    ("RD-GIRISH-ED", "GIRISH", "sc-2026-union-of-india-through-its-sec-2026insc149", 2, "", "REPORTER_EDITORIAL",
     "Tarsem Singh [2008] 12 SCR 104 : (2008) 8 SCC 648 – held inapplicable.",
     "Reporter's 'Case Law Cited' entry in the SCR rendition. Editorial matter: never used as the court's treatment."),
    ("RD-GIRISH-BENCH", "GIRISH", "sc-2026-union-of-india-through-its-sec-2026insc149", 1, "", "BENCH",
     "[Pamidighantam Sri Narasimha and Alok Aradhe,* JJ.]", "Two-Judge Bench printed in the SCR rendition."),
    ("RD-PARASHOTAM-T1", "PARASHOTAM", "sc-2023-union-of-india-ors-2023insc265", 17, "32", "TREATMENT",
     "We have, thus, no hesitation in concluding that the judgment in",
     "Para 32 opening (printed report page 614 of [2023] 3 SCR)."),
    ("RD-PARASHOTAM-T2", "PARASHOTAM", "sc-2023-union-of-india-ors-2023insc265", 17, "32", "TREATMENT",
     "Shri Kant Sharma & Anr.24 case does not lay down the correct law and is in conflict with judgments of the Constitution",
     "Exact wording in the held SCR rendition: 'does not lay down the correct law' (the '24' is a footnote marker; fn 24 reads '(supra)'). "
     "The word 'overruled' is not used."),
    ("RD-PARASHOTAM-T3", "PARASHOTAM", "sc-2023-union-of-india-ors-2023insc265", 18, "32", "TREATMENT",
     "power under Article 226 of the Constitution by the High Court. However, in respect of matters of self-discipline, "
     "the principles already stand enunciated.",
     "Para 32 ends on p.18 (report page 615) with a reservation for 'matters of self-discipline'."),
    ("RD-PARASHOTAM-ED", "PARASHOTAM", "sc-2023-union-of-india-ors-2023insc265", 4, "", "REPORTER_EDITORIAL",
     "& Anr. (2015) 6 SCC 773 : [2015] 4 SCR 676 – held not correct law.",
     "Reporter's case-law entry (editorial)."),
    ("RD-PARASHOTAM-BENCH", "PARASHOTAM", "sc-2023-union-of-india-ors-2023insc265", 1, "", "BENCH",
     "[SANJAY KISHAN KAUL, B. V. NAGARATHNA AND ABHAY S. OKA, JJ.]", "Three-Judge Bench."),
    ("RD-SHRIKANT-H1", "SHRIKANT", "sc-2015-union-of-india-ors-2015insc206", 47, "34(iv)", "HOLDING",
     "226 of the Constitution if an effective alternative remedy is available to the aggrieved person or the statute",
     "Para 34(iv) summary: 'The High Court will not entertain a petition under Article 226 ...' (Refer: Nivedita Sharma). "
     "The same words also occur on p.44 inside a quotation of an earlier judgment."),
    ("RD-SHRIKANT-H2", "SHRIKANT", "sc-2015-union-of-india-ors-2015insc206", 49, "38", "HOLDING",
     "we are of the view that Delhi High Court was not",
     "Para 38: Delhi HC 'not justified in entertaining the petition under Article 226' against AFT orders."),
    ("RD-SHRIKANT-H3", "SHRIKANT", "sc-2015-union-of-india-ors-2015insc206", 33, "25", "HOLDING",
     "judicial review vested in the High Court under Article 226 is one of the basic essential features of theConstitution",
     "Para 25 (and 34(i) p.47): Shri Kant Sharma itself accepts that Art. 226 review is a basic feature; its restriction "
     "operates through discretion/alternative remedy."),
    ("RD-SHRIKANT-BENCH", "SHRIKANT", "sc-2015-union-of-india-ors-2015insc206", 1, "", "BENCH",
     "[SUDHANSU JYOTI MUKHOPADHAYA AND", "Two-Judge Bench (with N.V. Ramana J., next line)."),
    ("RD-RANJIT-H1", "RANJIT", "sc-1987-ranjit-thakur-1987insc285", 12, "", "HOLDING",
     "offence as to shock the conscience and amount in itself to conclusive evidence of bias. The doctrine of "
     "proportionality, as part of the con-",
     "Judgment body (after 'delivered by', p.5). The same proposition also appears in the reporter's headnote on p.4."),
    ("RD-SNM-H1", "SNM", "sc-1990-s-n-mukherjee-1990insc257", 27, "", "HOLDING",
     "no requirement to record reasons by the confirming authority while",
     "Five-Judge (Constitution) Bench; continues: confirmation of court-martial findings/sentence and the post-confirmation "
     "order need no reasons, but remain open to challenge under Art. 32 / Art. 226."),
    ("RD-SNM-H2", "SNM", "sc-1990-s-n-mukherjee-1990insc257", 27, "", "HOLDING",
     "it is open to the person aggrieved by such", "Text layer is OCR-noisy on this page ('te challenge')."),
    ("RD-DHARAMVIR-H1", "DHARAMVIR", "sc-2013-dharamvir-singh-2013insc408", 27, "28(ii)", "HOLDING",
     "A member is to be presumed in sound physical and mental condition upon entering service if there is no note or "
     "record at the time of entrance.",
     "Read with para 28(i): determined under the Entitlement Rules for Casualty Pensionary Awards, 1982 (Appendix II, Reg. 173)."),
    ("RD-JKHC-SKS", "SHRIKANT", "hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06", 2, "6", "LATER_RELIANCE",
     "Since the Apex Court in case titled as “Union of India vs. Shri Kant Sharma (2015) 6 SCC 773 has specifically "
     "provided that High Court",
     "J&K HC (Srinagar), 06-10-2025, single Judge: relies on Shri Kant Sharma more than two years after Parashotam; "
     "Parashotam is not cited in this order."),
    ("RD-JKHC-SKS2", "SHRIKANT", "hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06", 3, "6", "LATER_RELIANCE",
     "should refrain from entertaining petitions under Article 226 if alternative or effective remedy is available",
     "Context: an original petition (not a writ against an AFT order); the AFT remedy was available."),
    ("RD-DHC-TARSEM-A", "TARSEM", "hc-delhi-2026-w-p-c-16771-2025-dlhc010862002025-1-2026-03-11", 9, "27", "LATER_RELIANCE",
     "view the law laid down by Supreme Court in Union of India & Ors v. Tarsem Singh8 , the arrears will be restricted "
     "to three years prior the OA,",
     "Delhi HC, 11-03-2026 (after Girish, 12-02-2026): restricts arrears by Tarsem while granting rounding-off from Ram Avtar's date. "
     "Girish is not mentioned in this passage."),
    ("RD-DHC-TARSEM-D", "TARSEM", "hc-delhi-2026-w-p-c-2053-2026-dlhc010054682026-1-2026-04-20", 3, "10", "LATER_RELIANCE",
     "The reliance placed on Tarsem Singh (supra) is misconceived.",
     "Delhi HC, 20-04-2026: petitioner's reliance on Tarsem rejected (p.4 explains Tarsem concerned recurring pension injury)."),
]

NARRATIVE = {
    "TARSEM": {
        "contrary": [
            "Girish (2026 INSC 149, two Judges) holds Tarsem 'of no assistance' and of 'no application' on two grounds "
            "(RD-GIRISH-T1, RD-GIRISH-T2). The wording is distinguishing, not overruling; both Benches have two Judges.",
            "Delhi HC W.P.(C) 16771/2025 (11-03-2026), after Girish, still restricts arrears to three years by Tarsem "
            "(RD-DHC-TARSEM-A). This conflicting treatment is kept as found; whether that reading survives Girish is a "
            "legal question.",
            "Delhi HC W.P.(C) 2053/2026 (20-04-2026) calls reliance on Tarsem 'misconceived' (RD-DHC-TARSEM-D). That is a "
            "fact-based distinction, not a statement about Tarsem's authority.",
        ],
        "open": [
            "Does Tarsem's three-year arrears rule survive for claims outside Girish's two grounds? Girish confines its "
            "reasoning to broad-banding claimants already in receipt of pension. Adviser question (C10 ESC-C10-01).",
            "C10 reports that Mullikote (2026 INSC 286) para 43 left the question open (official copy p.27). That copy is "
            "not in the ad77758d text layer, so it was not re-read here.",
            "Tarsem is held only as an SCR rendition, with OCR noise. No signed court copy is held.",
        ],
    },
    "GIRISH": {
        "contrary": [
            "No held judgment was found that declines to follow Girish. The Delhi HC decision of 11-03-2026 applies Tarsem "
            "without mentioning Girish (see TARSEM). It is a tension, not an express disagreement.",
        ],
        "open": [
            "Is Girish's 'in rem' reading of Ram Avtar binding beyond broad-banding? Ram Avtar itself is NOT HELD.",
            "Some J&K HC orders of May-June 2026 reproduce Girish para 22 (about Tarsem) inside a quotation. They appear "
            "only in the Tarsem name-only list, because they carry no Tarsem citation string. The treatment words there "
            "are Girish's, not the HC's, and no Tarsem treatment candidate is generated from them. (The attribution test "
            "suite checks that wording of this kind is classed QUOTED_PASSAGE.)",
        ],
    },
    "GIRISH_CLAR": {
        "contrary": [],
        "open": [
            "The clarification order (curated DCLR-SC-2026-008; C10 records it as 2026 INSC 1113 of 12-10-2026) is NOT HELD. "
            "No held judgment cites it (see the deterministic search below). Its content, and whether it modifies Girish "
            "para 22-23, is UNKNOWN. Do not treat Girish as modified or unmodified on this evidence. Acquire the order "
            "(C10 ESC-C10-02).",
        ],
    },
    "SHRIKANT": {
        "contrary": [
            "Parashotam (three Judges) para 32: Shri Kant Sharma 'does not lay down the correct law' (RD-PARASHOTAM-T2). "
            "This is explicit source wording to that effect. The word 'overruled' is not used. The paragraph ends with "
            "a reservation for 'matters of self-discipline' (RD-PARASHOTAM-T3).",
            "The J&K HC (06-10-2025) still relies on Shri Kant Sharma for the alternative-remedy proposition, without "
            "citing Parashotam (RD-JKHC-SKS, RD-JKHC-SKS2). This conflicting later treatment is preserved.",
        ],
        "open": [
            "What survives of Shri Kant Sharma? Para 34(i)-(ii) (Art. 226 is a basic feature; due regard to legislative "
            "intent) are consistent with Parashotam. The proposition in para 37-38 (HC should not entertain writs against "
            "AFT orders) is what Parashotam rejects. Whether para 34(iii)-(iv) (alternative remedy) survives as a "
            "discretionary rule is an adviser question (C10 ESC-C10-03).",
            "Typed edge: the tool proposes OVERRULES (Parashotam -> Shri Kant Sharma) at LEGAL_INTERPRETATION_ADVISER_REVIEW "
            "only. Nothing is marked LEGALLY_VALIDATED. An adviser may prefer 'disapproved' or 'declared not good law'.",
        ],
    },
    "PARASHOTAM": {
        "contrary": [
            "No held decision questions Parashotam. The J&K HC order of 06-10-2025 does not engage with it (see SHRIKANT).",
        ],
        "open": [
            "C10 located para 32 on p.22 of the official court PDF. That copy is outside the ad77758d text layer and was "
            "not re-read here. In the held SCR rendition, para 32 runs from p.17 to p.18 (report pp.614-615).",
            "Scope of the 'self-discipline' reservation (para 32, last sentence) is not defined in the paragraph.",
        ],
    },
    "RANJIT": {
        "contrary": [
            "No held decision found expressly departing from Ranjit Thakur on proportionality or bias. Later cases are "
            "listed below as citations; most are CITES without explicit treatment wording.",
        ],
        "open": [
            "Ranjit is held as a JUDIS/SCR rendition only (two crawler records share one sha). The Review Order (1989) 2 "
            "SCC 438 (curated R02) is NOT HELD, so citations to it stay unresolved.",
        ],
    },
    "SNM": {
        "contrary": [
            "Parashotam relies on S N Mukherjee (Constitution Bench) for HC Art. 226 relief against court-martial "
            "proceedings. That supports S N Mukherjee rather than contradicting it.",
        ],
        "open": [
            "The held copy is an OCR-noisy SCR rendition; the printed date is illegible in the text layer.",
        ],
    },
    "RAMAVTAR": {
        "contrary": [],
        "open": [
            "NOT HELD in any input store; every citation to it stays UNRESOLVED. Its content is known here only through "
            "citing judgments: Girish paras 13, 14 and 22; S P Rathore per C10. 'Ram Avtar' is also a common party name, "
            "so name-only hits are unreliable.",
            "HC citations use at least '2014 SCC OnLine SC 1761' and 'Civil Appeal No. 418/2012'. One Delhi HC order "
            "prints 'Civil Appeal No. 418/2010'.",
        ],
    },
    "DHARAMVIR": {
        "contrary": [
            "C10 records N C Isaac (2026 INSC 993; official copy outside this text layer) as clarifying Dharamvir for the "
            "2008 Entitlement Rules (Isaac p.91 para 34). Dharamvir applied the 1982 Rules (RD-DHARAMVIR-H1). Isaac was "
            "not re-read in C11.",
        ],
        "open": [
            "Instrument version: Dharamvir construes the Entitlement Rules 1982. Citing judgments that concern 2008-Rules "
            "claimants need an adviser check (C10 ESC-C10-04). The statute-link table marks ENT-1982 vs ENT-2008 vs "
            "ENT-UNSPECIFIED and never infers the version.",
        ],
    },
}

C10_COMPARE = {
    "TARSEM": "C10: holding SCR pp.5-6 paras 5-6; DISTINGUISHED by Girish para 22; APPLIED by Delhi HC W.P.(C) 16771/2025 p.9; "
              "DISTINGUISHED by W.P.(C) 2053/2026. C11: all four re-verified verbatim in the ad77758d text layer "
              "(Girish via its SCR rendition, p.11).",
    "GIRISH": "C10: 24 HC citing judgments after decision; 3 read, all APPLY. C11: see the graph counts below. Cue-based "
              "proposals need documentary checks.",
    "GIRISH_CLAR": "C10: NOT HELD, 0 hits for '2026 INSC 1113'. C11 repeats the deterministic search below.",
    "SHRIKANT": "C10: 'OVERRULED in documentary wording' by Parashotam para 32 (official copy p.22). C11: the wording is confirmed in "
                "the held SCR rendition at p.17 (para 32). It is recorded as a proposed OVERRULES edge for adviser review, "
                "not as a validated status.",
    "PARASHOTAM": "C10: APPLIED by SC 2023 INSC 1074; DISTINGUISHED by Allahabad HC WRIA 2923/2026 p.5. C11: see the treatment "
                  "candidates below. These C10 readings were not re-read unless listed.",
    "RANJIT": "C10: JUDIS + SCR renditions; date defect '3.?.1986' (SCR-C01).",
    "SNM": "C10: C.A. 417/1984 agrees; date not legible.",
    "RAMAVTAR": "C10: NOT HELD; APPLIED by Girish as in rem; CLARIFIED by S P Rathore para 8 (SCR pp.4-5).",
    "DHARAMVIR": "C10: APPLIED by Rajbir para 15; CLARIFIED by Isaac (2026 INSC 993).",
}


def norm_q(s):
    return re.sub(r"\s+", "", s or "")


def verify_readings(b):
    doc_by_id = {}
    for jid, j in b.judg.items():
        if jid in b.docs:
            doc_by_id[j["doc_id"]] = b.docs[jid]
            for a in j["alias_doc_ids"]:
                doc_by_id[a] = b.docs[jid]
    out = []
    for rid, case, did, page, para, kind, quote, note in READINGS:
        doc = doc_by_id.get(did)
        if doc is None:
            raise SystemExit("READING %s: doc %s not in text layer" % (rid, did))
        if norm_q(quote) not in norm_q(doc.page_text(page)):
            found = [p for p in doc.page_nos if norm_q(quote) in norm_q(doc.page_text(p))]
            raise SystemExit("READING %s: quotation not found on p.%s of %s (found on %s)" % (rid, page, did, found))
        out.append({"id": rid, "case": case, "doc_id": did, "page": page, "para": para, "kind": kind, "quote": quote, "note": note,
                    "check": "VERBATIM_FOUND (whitespace-insensitive) on stated page"})
    return out


def md_cell(s):
    return (s or "").replace("|", "/").replace("\n", " ")


def build(b):
    readings = verify_readings(b)
    jid_of_doc = {}
    for jid, j in b.judg.items():
        jid_of_doc[j["doc_id"]] = jid
        for a in j["alias_doc_ids"]:
            jid_of_doc[a] = jid
    edges = b.edge_rows
    cands = b.cand_rows
    by_target = defaultdict(list)
    for e in edges:
        if e["target_group_id"]:
            by_target[e["target_group_id"]].append(e)
    cand_by_target = defaultdict(list)
    for c in cands:
        if c["target_group_id"]:
            cand_by_target[c["target_group_id"]].append(c)
    cur = {c["id"]: c for c in b.curated}
    L = []
    w = L.append
    w("# Priority treatment dossier (Cycle 11, judicial relationships)")
    w("")
    w("**Status: evidence findings only. Nothing here is legally validated.**")
    w("- No status was changed. Every typed relation is a proposal: AUTOMATED_DETECTED, DOCUMENTARY_CHECK_REQUIRED or "
      "LEGAL_INTERPRETATION_ADVISER_REVIEW. LEGALLY_VALIDATED is never assigned.")
    w("- **Readings.** All readings are by an AI agent (Claude Opus 5.5 subagent) of the text layer at raw-data commit ad77758d. "
      "They are not human-confirmed. No page images were rendered.")
    w("- **Copies.** Most held Supreme Court copies here are SCR renditions from the AWS e-SCR mirror. They are not signed "
      "court originals.")
    w("- **Quotation checks.** Each quotation in 'Verified readings' is re-checked on every build, verbatim "
      "(whitespace-insensitive) on the stated PDF page. The build fails on any miss.")
    w("- **Locators.** 'p.' is the text-layer PDF page ([[page N]]). 'para' is the printed paragraph number where shown. "
      "In graph tables the paragraph is a heuristic (the last numbered paragraph start before the citation).")
    w("- **Graph counts.** These come from CASE_CITATION_GRAPH.csv and TREATMENT_CANDIDATES.csv. A citing edge means "
      "the citing judgment carries a citation string resolved to the case, or a case number with party names. "
      "Name-only mentions are listed separately and are not resolved.")
    w("- **Overruling.** No precedent is declared overruled. Where the source wording is explicit, it is quoted, and the "
      "edge goes to adviser review.")
    w("")
    w("## Summary of key findings")
    w("")
    w("| Case | Held copy in text layer | Resolved citing judgments | Key finding (with uncertainty) |")
    w("| --- | --- | --- | --- |")
    summary_rows = []
    for p in PRIORITY:
        jids = [jid_of_doc[d] for d in p["doc_ids"] if d in jid_of_doc]
        groups = sorted(set(b.group_of[j] for j in jids))
        n = len(set(e["source_judgment_id"] for g in groups for e in by_target[g]))
        if p.get("raw_keys"):
            keys = set(p["raw_keys"])
            un = len(set(e["source_judgment_id"] for e in b.edge_rows if not e["target_group_id"] and keys & set(e["citation_keys"].split(";"))))
            n = "0 resolved; %d citing judgments by unresolved string" % un
        held = "; ".join(sorted(set(b.judg[x]["doc_id"] for g in groups for x in b.group_members[g]))) or "NOT HELD"
        summary_rows.append((p, groups, n, held))
    key_find = {
        "TARSEM": "Distinguished (2 grounds) by Girish para 22, p.11. Not overruled on held documents. Still applied by Delhi HC on 11-03-2026, after Girish: conflicting treatment preserved.",
        "GIRISH": "Holds the s.22(1)(c) bar inapplicable and treats Ram Avtar as in rem (para 22, p.11). HC uptake is listed below; documentary checks are pending.",
        "GIRISH_CLAR": "NOT HELD and NOT CITED in any held judgment (deterministic search). Its content is unknown.",
        "SHRIKANT": "Parashotam para 32 (p.17): 'does not lay down the correct law' (three Judges vs two). OVERRULES is proposed for adviser review only. J&K HC still relied on it on 06-10-2025.",
        "PARASHOTAM": "The para 32 wording is verified in the SCR rendition at pp.17-18. The official-copy locator (p.22, from C10) was not re-read.",
        "RANJIT": "A proportionality/bias authority with wide CITES uptake. No explicit negative treatment found.",
        "SNM": "Constitution Bench: no reasons are needed at confirmation, but Art. 32/226 review remains (p.27). Parashotam relies on it.",
        "RAMAVTAR": "NOT HELD; known only through citing judgments. All citations are UNRESOLVED.",
        "DHARAMVIR": "Construes the 1982 Entitlement Rules (para 28, p.27). C10 records Isaac (2026, 2008 Rules) as clarifying it; not re-read here.",
    }
    for p, groups, n, held in summary_rows:
        w("| %s | %s | %s | %s |" % (p["label"], md_cell(held), n, key_find[p["key"]]))
    w("")
    for p, groups, n, held in summary_rows:
        L.extend(case_section(b, p, groups, by_target, cand_by_target, readings, cur, jid_of_doc))
    L.extend(key_authorities(b, by_target, cand_by_target))
    L.extend(method_notes(b))
    return "\n".join(L) + "\n"


def case_section(b, p, groups, by_target, cand_by_target, readings, cur, jid_of_doc):
    L = []
    w = L.append
    k = p["key"]
    w("## %s" % p["label"])
    w("")
    c = cur.get(p["cur"])
    if c:
        w("- **Curated record.** %s. Curated date: %s. Case number: %s. Reporter: %s." % (
            c["id"], c["date"] or "-", c["case_number"] or "-", c["reporter"] or "-"))
        w("- **C10 held status:** %s." % (c["held_status"] or "-"))
        st = c.get("c10") or {}
        if st.get("official_court_copy_held"):
            w("- **C10 official-copy status (copies outside this text layer were not re-read):** %s.%s" % (
                md_cell(st.get("official_court_copy_held"))[:160],
                (" Working store: %s." % md_cell(st.get("working_store_paths"))[:200]) if st.get("working_store_paths") else ""))
    if groups:
        for g in groups:
            jids = sorted(b.group_members[g])
            m = b.judg[jids[0]]["meta"]
            rec = b.recon.get(g, [])
            cls = sorted(set(r["group_class"] for r in rec)) or ["(not in C10 reconciliation)"]
            rend = sorted(set(r["rendition_type"] for r in rec if r["rendition_type"]))
            w("- **Held copy in the ad77758d text layer.** Group %s (%s). Renditions: %s." % (
                g, ", ".join(cls), ", ".join(rend) or "-"))
            w("  - Records: %s." % "; ".join("%s (sha %s, %s pp.)" % (b.judg[j]["doc_id"], b.judg[j]["sha"][:12],
                                                                        b.judg[j]["meta"].get("page_count")) for j in jids))
            w("  - Neutral citation: %s. Reported: %s. Date: %s." % (
                m.get("neutral_citation") or "-", "; ".join(m.get("reported_citations") or []) or "-", m.get("issue_date")))
    else:
        w("- **Held copy in the ad77758d text layer:** NONE.")
    w("- **C10 prior reading vs C11:** %s" % C10_COMPARE.get(k, "-"))
    w("")
    # readings
    rs = [r for r in readings if r["case"] == k or (k == "RAMAVTAR" and r["id"] in ("RD-GIRISH-R1", "RD-GIRISH-T3"))
          or (k == "SHRIKANT" and r["case"] == "PARASHOTAM" and r["kind"] in ("TREATMENT", "REPORTER_EDITORIAL"))
          or (k == "TARSEM" and r["id"] in ("RD-GIRISH-T1", "RD-GIRISH-T2", "RD-GIRISH-ED"))]
    if rs:
        w("### Verified readings")
        w("")
        w("| Reading | Kind | Document | p. | para | Quotation (verbatim) | Note |")
        w("| --- | --- | --- | --- | --- | --- | --- |")
        for r in rs:
            w("| %s | %s | %s | %s | %s | \"%s\" | %s |" % (r["id"], r["kind"], r["doc_id"], r["page"], r["para"] or "-",
                                                       md_cell(r["quote"]), md_cell(r["note"])))
        w("")
    # citing judgments
    es = []
    for g in groups:
        es.extend(by_target[g])
    if p.get("raw_keys"):
        keys = set(p["raw_keys"])
        es.extend(e for e in b.edge_rows if not e["target_group_id"] and keys & set(e["citation_keys"].split(";")))
    if es:
        courts = Counter(e["source_court"] for e in es)
        years = Counter(e["source_date"][:4] for e in es)
        w("### Citing judgments (graph)")
        w("")
        w("- **Distinct citing judgments:** %d." % len(set(e["source_judgment_id"] for e in es)))
        w("  - By court: %s." % ", ".join("%s %d" % (c_, n) for c_, n in sorted(courts.items())))
        w("  - By year: %s." % ", ".join("%s: %d" % (y, n) for y, n in sorted(years.items())))
        if not groups:
            w("- **Target unresolved.** The case is not held, so these edges stay UNRESOLVED. They were matched only by "
              "the citation strings listed above.")
        sc = sorted([e for e in es if e["source_court"].startswith("Supreme")], key=lambda e: (e["source_date"], e["source_doc_id"]))
        hc = sorted([e for e in es if not e["source_court"].startswith("Supreme")], key=lambda e: (e["source_date"], e["source_doc_id"]), reverse=True)
        show = sc + hc[:12]
        w("")
        w("All Supreme Court citing edges are listed, plus the %d most recent High Court edges (of %d). The paragraph "
          "number is heuristic." % (min(12, len(hc)), len(hc)))
        w("")
        w("| Citing judgment | Court | Date | p. | para | Method | Excerpt |")
        w("| --- | --- | --- | --- | --- | --- | --- |")
        for e in show:
            w("| %s | %s | %s | %s | %s | %s | %s |" % (e["source_doc_id"], e["source_court"].replace("High Court of ", "HC ").replace("Supreme Court of India", "SC"),
                                                    e["source_date"], e["page"], e["paragraph"] or "-", e["resolution_method"] or e["target_state"],
                                                    md_cell(e["excerpt"])[:250]))
        w("")
    # treatment candidates
    cs = []
    for g in groups:
        cs.extend(cand_by_target[g])
    if p.get("raw_keys"):
        keys = set(p["raw_keys"])
        eids = set(e["edge_id"] for e in es)
        cs.extend(x for x in b.cand_rows if x["edge_id"] in eids and not x["target_group_id"])
    if cs:
        w("### Treatment candidates (cue wording near a citation or a later name reference)")
        w("")
        att = Counter(x["attribution"] for x in cs)
        w("- **Cue hits:** %d." % len(cs))
        w("  - By attribution: %s." % ", ".join("%s %d" % kv for kv in sorted(att.items())))
        w("  - Only COURT_LIKELY hits can carry a proposed relation.")
        prop = [x for x in cs if x["proposed_relation"] or x["status"] != "AUTOMATED_DETECTED"]
        other = [x for x in cs if not (x["proposed_relation"] or x["status"] != "AUTOMATED_DETECTED")]
        rows = sorted(prop, key=lambda x: (x["source_date"], x["source_doc_id"], x["cue_page"]))
        rows += sorted(other, key=lambda x: (x["source_date"], x["source_doc_id"]), reverse=True)[:max(0, 14 - len(rows))]
        w("")
        w("| Candidate | Citing judgment | Date | cue p./para | Cue | Attribution | Proposed | Status | Excerpt |")
        w("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for x in rows[:40]:
            w("| %s | %s | %s | %s/%s | %s | %s | %s | %s | %s |" % (
                x["candidate_id"], x["source_doc_id"], x["source_date"], x["cue_page"], x["cue_paragraph"] or "-",
                x["cue_text"], x["attribution"], x["proposed_relation"] or "-", x["status"], md_cell(x["excerpt"])[:220]))
        w("")
    # name-only mentions
    nm = name_only(b, p, groups)
    if nm is not None:
        hits, rx_desc = nm
        w("### Name-only mentions (not resolved; may be false positives)")
        w("")
        w("- **Pattern:** `%s`. Searched in judgments with no resolved or string-matched edge to this case." % rx_desc)
        w("- **Window:** decided on or after %s." % (p.get("date_from") or name_date(b, groups) or "-"))
        w("- **Hits:** %d judgments." % len(hits))
        for did, date, page, exc in hits[:10]:
            w("  - %s (%s) p.%s: \"%s\"" % (did, date, page, md_cell(exc)))
        w("")
    if k == "GIRISH_CLAR":
        L.extend(clar_search(b))
    nar = NARRATIVE.get(k, {})
    w("### Contrary authority / conflicting treatment")
    w("")
    for s in nar.get("contrary") or ["None identified in the held corpus. Absence of a hit is not proof of absence."]:
        w("- %s" % s)
    w("")
    w("### Open questions and uncertainty")
    w("")
    for s in nar.get("open") or ["-"]:
        w("- %s" % s)
    w("")
    return L


def name_date(b, groups):
    ds = [b.g_label(g)["date"] for g in groups]
    return min(ds) if ds else ""


def name_only(b, p, groups):
    if groups:
        bg = set()
        for g in groups:
            for j in b.group_members[g]:
                from relations_c11 import name_bigrams
                bg |= name_bigrams(b.judg[j]["meta"])
        if not bg:
            return None
        pats = ["%s %s" % x for x in sorted(bg)]
        rx = re.compile("|".join(r"\b%s[\s.]+%s\b" % (re.escape(a), re.escape(c)) for a, c in sorted(bg)), re.I)
        dfrom = name_date(b, groups)
        linked = set(e["source_judgment_id"] for g in groups for e in b.edge_rows if e["target_group_id"] == g)
        own = set(j for g in groups for j in b.group_members[g])
    elif p.get("name_rx"):
        rx = re.compile(p["name_rx"])
        pats = [p["name_rx"]]
        dfrom = "2014-12-10" if p["key"] == "RAMAVTAR" else ""
        keys = set(p.get("raw_keys") or [])
        linked = set(e["source_judgment_id"] for e in b.edge_rows if keys & set(e["citation_keys"].split(";")))
        own = set()
    else:
        return None
    hits = []
    for jid in sorted(b.docs):
        if jid in linked or jid in own:
            continue
        d = b.judg[jid]["meta"].get("issue_date") or ""
        if dfrom and d < dfrom:
            continue
        doc = b.docs[jid]
        m = rx.search(doc.text, doc.editorial_end)
        if m:
            exc = doc.text[max(0, m.start() - 80):m.end() + 80]
            hits.append((b.judg[jid]["doc_id"], d, doc.page_at(m.start()), re.sub(r"\s+", " ", exc).strip()[:200]))
    hits.sort(key=lambda h: (h[1], h[0]), reverse=True)
    return hits, " | ".join(pats)[:200]


def clar_search(b):
    L = []
    w = L.append
    n_insc = []
    n_clar = []
    same_day = []
    girish_rx = re.compile(r"\bGirish[\s.]+Kumar\b", re.I)
    for jid in sorted(b.docs):
        doc = b.docs[jid]
        t = doc.text
        did = b.judg[jid]["doc_id"]
        if re.search(r"2026\s*INSC\s*1113\b", t):
            n_insc.append(did)
        for m in girish_rx.finditer(t):
            win = t[max(0, m.start() - 400):m.end() + 400]
            if re.search(r"clarif", win, re.I):
                n_clar.append((did, doc.page_at(m.start()), re.sub(r"\s+", " ", t[max(0, m.start() - 100):m.end() + 140]).strip()[:230]))
                break
        if (b.judg[jid]["meta"].get("issue_date") or "") == "2026-10-12":
            same_day.append((did, bool(girish_rx.search(t))))
    w("### Deterministic search for the clarification order")
    w("")
    w("- **'2026 INSC 1113':** found in %d held judgments%s." % (len(n_insc), (": " + "; ".join(n_insc)) if n_insc else ""))
    w("- **'Girish Kumar' within 400 characters of 'clarif\\*':** %d held judgments." % len(n_clar))
    for did, pg, exc in n_clar[:10]:
        w("  - %s p.%s: \"%s\"" % (did, pg, md_cell(exc)))
    if n_clar:
        w("  - These hits are proximity matches only. They were not read as references to the clarification order.")
    w("- **Held judgments dated 2026-10-12:** %d (%s)." % (len(same_day), "; ".join("%s mentions Girish: %s" % (d, "yes" if g else "no") for d, g in same_day) or "-"))
    w("- **Result:** the clarification order is NOT HELD, and no held judgment cites it by neutral citation.")
    w("")
    return L


def key_authorities(b, by_target, cand_by_target):
    L = []
    w = L.append
    w("## Key authorities by in-degree (graph-derived; not priority-read)")
    w("")
    w("In-degree is the number of distinct citing judgments with a resolved CITES edge. Proposals are cue-based and "
      "unverified.")
    w("")
    w("| Rank | Authority | Date | Court | In-degree | Proposed treatments (by relation) | Adviser-review candidates |")
    w("| --- | --- | --- | --- | --- | --- | --- |")
    indeg = Counter()
    for g, es in by_target.items():
        indeg[g] = len(set(e["source_judgment_id"] for e in es))
    for i, (g, n) in enumerate(sorted(indeg.items(), key=lambda kv: (-kv[1], kv[0]))[:20], 1):
        lab = b.g_label(g)
        cs = cand_by_target.get(g, [])
        pr = Counter(x["proposed_relation"] for x in cs if x["proposed_relation"])
        adv = sum(1 for x in cs if x["status"] == "LEGAL_INTERPRETATION_ADVISER_REVIEW")
        w("| %d | %s (%s) | %s | %s | %d | %s | %d |" % (i, md_cell(lab["title"])[:70], "; ".join(lab["doc_ids"])[:70], lab["date"],
                                                       lab["court"].replace("Supreme Court of India", "SC"), n,
                                                       ", ".join("%s %d" % kv for kv in sorted(pr.items())) or "-", adv))
    w("")
    return L


def method_notes(b):
    return [
        "## Method notes and limits",
        "",
        "- **Citation detection.** Patterns cover SCC, SCC OnLine, SCR (all common layouts), AIR, INSC, JT, SLT, SCALE, SLR, "
        "HC neutral citations, and case numbers (Civil/Criminal Appeal, SLP, W.P.(C), CWP, SWP, OWP, WRIA, LPA).",
        "- **Resolution order.**",
        "  - First, deterministic keys from the target's own metadata (neutral citation, reported citation, or a "
        "self-printed HC neutral citation).",
        "  - Then the C10-held curated crosswalk.",
        "  - Then parallel citations learned from metadata-resolved clusters.",
        "  - Last, a conservative fallback: case number plus a party-name bigram, or party bigram plus year plus court.",
        "  - Ambiguous matches stay UNRESOLVED_AMBIGUOUS with their candidates.",
        "- **Dropped references.** These are not citations and are dropped: self-citations, the citing judgment's own "
        "case numbers, and same-day connected matters.",
        "- **Treatment attribution.** Cue words in reporter headnotes or case-law lists, in quoted passages, in party "
        "submissions, or in reports of what a lower forum or another bench did never produce a proposal. Neither do "
        "past-tense participles without present or first-person voice, or cues more than 150-250 characters from the "
        "citation. OVERRULES, REVERSES and QUESTIONS proposals always go to adviser review.",
        "- **Coverage limits.** Coverage is limited to the crawler judgment corpus (ad77758d). The official copies of "
        "Girish, Parashotam, Mullikote, Isaac and others in the C5 working store or HF legal_knowledge were not part "
        "of this input. The absence of a hit is not proof that no treatment exists.",
        "",
    ]
