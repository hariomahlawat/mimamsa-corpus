#!/usr/bin/env python3
"""C13 A4: acquisition requests for workstream A7 and the legal-adviser review packet.

Reads (read-only): C12F outputs (57 promotion proposals, verification rows), the C12 independent-review verdicts,
the C13 evidence outputs (10 further proposals), the C13 version records, WS-A gaps / pinned acquisition
candidates, the C5 conflict register and the C12 adviser question list (for cross-references).

Writes outputs/ACQUISITION_REQUESTS_A4.csv, outputs/ADVISER_REVIEW_PACKET_A4.csv, outputs/ADVISER_REVIEW_PACKET_A4.md.
Nothing is fetched and nothing is decided: every row states a question or a request, never a legal conclusion.

Usage: build_packets_c13.py [--check]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict

from c13a4_common import AW, PKG, assert_no_restricted, csv_bytes, read_csv, require_env

OUT = PKG / "outputs"
C12F = AW / "C12-CONSOLIDATION/statutory_citations/outputs"
ACQ03 = {r["acq03_id"]: r for r in read_csv(AW / "WS-A-STATUTORY/acq03_pinned_candidates.csv")}

ACQ_FIELDS = ["request_id", "priority", "request_type", "target_instrument", "why_needed", "closes", "dependent_citation_items",
              "dependent_version_records", "candidate_source", "url", "expected_md5", "expected_bytes", "prior_request_refs",
              "access_constraints", "post_fetch_checks", "status"]
ADV_FIELDS = ["packet_id", "category", "subject", "exact_question", "evidence", "competing_readings", "affected_records", "affected_items",
              "decision_required", "cross_refs", "independent_review_verdict", "status"]

ACCESS_NOTE = ("allow-listed hosts only; robots.txt; >=2 s per host; no login/CAPTCHA; never aftjabalpur.in; no TLS bypass. C12 WS-H found archive.org "
               "downloads redirect to storage nodes that are not allow-listed and egazette.gov.in fails TLS verification from the build container: a config/allow-list "
               "decision by the owner may be needed before any fetch")
CHECKS = "size and MD5 vs pinned metadata; SHA-256; render operative page(s) and image-check masthead, instrument number/date, operative words and commencement clause; record PIC with render SHA-256"


def acq_rows(matrix, recs):
    def items(pat):
        rx = re.compile(pat)
        return sum(1 for r in matrix if rx.search(r["blockers_c13"] or ""))

    def vers(pat, currency=False):
        rx = re.compile(pat)
        return sum(1 for r in recs if rx.search(json.dumps([r["open_items"], r["effective_from"]["basis"], r["text_evidence"]] + ([r["currency"]] if currency else []))))

    def src(*ids):
        return sum(1 for r in matrix if r["source_id"] in ids)

    def pin(aid):
        r = ACQ03.get(aid, {})
        return r.get("download_url", ""), r.get("expected_md5", ""), r.get("expected_bytes", "")

    rows = []

    def add(pri, typ, target, why, closes, it, ve, src, aid, refs, access=ACCESS_NOTE, checks=CHECKS):
        url, md5, by = pin(aid) if aid else ("", "", "")
        rows.append({"request_id": f"A4-ACQ-{len(rows) + 1:03d}", "priority": pri, "request_type": typ, "target_instrument": target, "why_needed": why,
                     "closes": closes, "dependent_citation_items": it, "dependent_version_records": ve, "candidate_source": src, "url": url,
                     "expected_md5": md5, "expected_bytes": by, "prior_request_refs": ";".join(x for x in [aid, refs] if x),
                     "access_constraints": access, "post_fetch_checks": checks, "status": "QUEUED_FOR_A7"})

    add("P1", "DISCOVERY_THEN_ACQUIRE", "S.R.O. 258 dated 27-11-2002 (alleged Army Rules amendment; possibly an Explanation to r.22)",
        "Hard blocker for every r.22 item (29 Army Rules items incl. tier A hearing-of-charge records); r.22 version chain cannot be closed",
        "AR-030; GAP-02", items(r"AR-030"), vers(r"AR-030"), "No lawful online source located (ACQ03-028). Gazette of India Pt II s.3/s.4 Nov-Dec 2002; NAI / GoI Press / MoD file copy (custodian request)",
        "ACQ03-028", "ACQ-03-B4-09")
    add("P1", "DISCOVERY_THEN_ACQUIRE", "Source of '[or Military Secretary]' in Army Rule 15 (MML 2 p.142 attributes it to S.R.O. 17(E)/1993, which has no r.15 item)",
        "Hard blocker for the 6 r.15 items (5 withdrawn in C12F v1.1, F-01); r.15 version after 1961 cannot be confirmed",
        "OQ-A-10; GAP-15; XC-03", items(r"GAP-15"), vers(r"GAP-15"), "1966-1974 Army Rules hints (ACQ03-001..009) are the only located candidates; otherwise MoD custodian copy",
        "", "ACQ-C3-03; ACQ03-001..009")
    for aid in ["ACQ03-001", "ACQ03-002", "ACQ03-003", "ACQ03-004", "ACQ03-005", "ACQ03-006", "ACQ03-007", "ACQ03-008", "ACQ03-009"]:
        r = ACQ03[aid]
        add("P1", "ACQUIRE_PUBLIC_PINNED", r["target_instruments"], "Unchecked Army Rules amendment hint: chain completeness for every rule (currency NOT_ESTABLISHED); possible r.15 source",
            r["closes"], items(re.escape(r["closes"].split(";")[0])), vers(r"unopened hints", True), "archive.org (pinned MD5)", aid, r.get("prior_request_id", ""))
    add("P1", "DISCOVERY_THEN_ACQUIRE", "E-7 dated 17-06-1960 (alleged first Army Rules amendment of 1960, listed in every official note)",
        "Generic chain gap on every Army Rules version (AR-001); listed in the r.23(3) C-01 chain", "AR-001; GAP-01", items(r"GAP-01"), vers(r"AR-001", True),
        "No lawful online source (ACQ03-026); NAI / GoI Press / MoD", "ACQ03-026", "ACQ-03-B4-01")
    add("P1", "ACQUIRE_PUBLIC_CANDIDATES", "Army Rules / Army Act instruments after 06-06-2022 (C5C-004..013 egazette candidates incl. S.R.O. 9(E)/2022, 15(E)/2024, 10(E)/2026)",
        "Every Army Rules version is OPEN_ON_LOCATED_INSTRUMENTS; currency after 06-06-2022 not searched", "AR-036; AA-13; GAP-03",
        src("C5-SRC-P0-ARMY-RULES-1954"), vers(r"AR-036", True), "egazette.gov.in WriteReadData/2022-2026 (TLS failure in C12 WS-H); archive.org mirror if any", "ACQ03-027",
        "C12 acquisition T4-AR-POST2022-236757/241268/246457/254308/273809")
    for aid, why in [("ACQ03-010", "r.168(2) 1960 amendment (text layer only)"), ("ACQ03-011", "App. I forms 1960"), ("ACQ03-012", "Table below r.13 (1960)"),
                     ("ACQ03-013", "r.168(3) and App. IV forms 1960"), ("ACQ03-014", "Table below r.13 (2010)")]:
        r = ACQ03[aid]
        add("P2", "ACQUIRE_PUBLIC_PINNED", r["target_instruments"], f"OCR-only located instrument ({why}); amending copy not registered, so r.13 / r.168 versions stay TEXT_LAYER_ONLY",
            r["closes"], items(re.escape(r["closes"].split(";")[0])), vers(re.escape(r["closes"].split(";")[0])), "archive.org (pinned MD5)", aid, "")
    for aid, why in [("ACQ03-036", "pre-1960 App. I amendment"), ("ACQ03-037", "r.187(1) item (r) 1958"), ("ACQ03-038", "r.95 amendment 1958 (blocks CM-019, CM-SC-07)"),
                     ("ACQ03-039", "1959 amendments")]:
        r = ACQ03[aid]
        add("P1" if "r.95" in why else "P2", "ACQUIRE_PUBLIC_PINNED", r["target_instruments"], f"Unopened pre-1960 hint: {why}", r["closes"],
            items(re.escape(r["closes"].split(";")[0])), vers(re.escape(r["closes"].split(";")[0])), "archive.org (pinned MD5)", aid, "ACQ-C2-01..04")
    add("P1", "ACQUIRE_PUBLIC_PINNED", "Army Act, 1950 as enacted (Act 46 of 1950), Gazette of India Extraordinary 23-05-1950",
        "No documented-primary copy of any Army Act section: all 190 Army Act items stay PARTIAL and every AA1950 base version is COMPILATION_ONLY",
        "AA-00; GAP-06; CC-17; FID-03", src("C5-SRC-P0-ARMY-ACT-1950-INDIACODE"), vers(r"ACQ-C3-01"), "archive.org in.gazette.e.1950.306 (pinned MD5)", "ACQ03-029", "ACQ-C3-01; C5-ACQ-01; C12 T4-AA-ENACTED-1950")
    add("P2", "ACQUIRE_PUBLIC_PINNED", "Commencement notification of the Army Act 1950 (S.R.O. 120 of 22-07-1950; probable candidate)",
        "Army Act base versions carry only a compilation-reported start date (22-07-1950)", "AA-00; GAP-06", 0, vers(r"S\.R\.O\. 120"), "archive.org in.gazette.1950.318 (pinned MD5)", "ACQ03-019", "")
    add("P2", "ACQUIRE_PUBLIC_PINNED", "S.R.O. 2(E) of 07-05-1955 (commencement of the Commanders-in-Chief (Change in Designation) Act 1955) and the Act's Schedule",
        "Act 19/1955 substitutions not enumerated (OQ-A-13); commencement not held", "AA-01; GAP-07; OQ-A-13", 0, vers(r"OQ-A-13"), "archive.org (pinned MD5)", "ACQ03-020", "ACQ-01 B6")
    for aid in ["ACQ03-021", "ACQ03-015", "ACQ03-022", "ACQ03-023", "ACQ03-024", "ACQ03-017", "ACQ03-025"]:
        r = ACQ03[aid]
        add("P3", "ACQUIRE_PUBLIC_PINNED", r["target_instruments"], "Army Act amendment chain instrument not held (versions carry compilation-footnote evidence only)", r["closes"],
            0, vers(re.escape(r["closes"].split(";")[0])), "archive.org (pinned MD5)", aid, "")
    add("P3", "DISCOVERY_THEN_ACQUIRE", "Notification S.O. 3912(E) dated 30-10-2019 (application of the Army Act references to J&K / Ladakh) and Repealing and Amending Act 1957",
        "AA ss.137, 151, 174 and s.194 versions rest on compilation notes only", "AA-C3-02; AA-C3-03", 0, vers(r"AA-C3-0[23]"), "egazette / archive.org (no pin yet)", "", "ACQ-C3-05; ACQ-C3-06")
    add("P1", "DISCOVERY_THEN_ACQUIRE", "S.O. 14(E) dated 13-06-2008 appointing 15-06-2008 under AFT Act s.1(2)",
        "Every AFT2007 base version carries only a compilation-reported start date; AQ-STA-08", "I-AFT-SO14E-2008; G-AFT-COMM", src("C5-SRC-P0-AFT-ACT-2007-INDIACODE"), vers(r"S\.O\. 14\(E\)"),
        "egazette.gov.in (2008 Extraordinary Pt II s.3(ii)); archive.org mirror if any", "", "C9 missing_originals")
    add("P1", "DISCOVERY_THEN_ACQUIRE", "Commencement notification(s) of the Tribunals Reforms Act 2026 under s.1(2)",
        "AFT s.9A (2026 substitution) and the repeal of TRA 2021 have no established start; AQ-STA-10", "I-AFT-TRA2026-COMM", 0, vers(r"TRA2026-COMM|TRA 2026 commencement"),
        "egazette.gov.in 2026", "", "C9 I-AFT-TRA2026-COMM")
    add("P1", "ACQUIRE_PUBLIC_CANDIDATES", "S.O. 848(E), 849(E) and 850(E) dated 23-02-2024 (commencement of BNSS, BSA and BNS; 01-07-2024 with stated exceptions)",
        "The 1 July 2024 transition date and the BNS s.106(2) exception are recorded only from compilation footnotes; AQ-STA-19", "C5C-021/022/023; G-SANHITA-COMM",
        items(r"SANHITA") + sum(1 for r in matrix if r["source_id"] == "C5-SRC-P0-SANHITA-COMMENCEMENT-2024"), vers(r"S\.O\. 8(48|49|50)\(E\)"),
        "egazette.gov.in WriteReadData/2024/252352-252354.pdf (TLS failure in C12 WS-H)", "", "C12 acquisition T4-BSA-COMM-252352; T4-BNS-COMM-252353; T4-BNSS-COMM-252354")
    add("P2", "ACQUIRE_PUBLIC_CANDIDATES", "BNS, BNSS and BSA 2023 as enacted (Gazette of India Extraordinary 25-12-2023)",
        "Only compilations held; BNSS/BSA citation items (114) cannot be anchored to an enacted text", "C5-ACQ-03/04/20", src("C5-SRC-P0-BNSS-2023-INDIACODE", "C5-SRC-P0-BSA-2023-INDIACODE", "C5-SRC-P1-BNS-2023"), vers(r"Gazette as enacted NOT_HELD"),
        "archive.org pinned metadata (C5-ACQ-03/04/20); egazette", "", "C9-ACQ-111")
    add("P1", "REGISTRATION_OF_HELD_COPY", "AFT (Procedure) Rules 2008, Amendment Rules 2011, Practice Rules 2009: register the corpus raw-store copies in the C5 copy register (no download)",
        "46 AFT Procedure Rules items are MISSING_EVIDENCE although the instruments are held in the raw store (C9); registration + page-image identity review would allow evidence work (no promotion is proposed here)",
        "GAP-11; OQ-A-08; AQ-STA-09", sum(1 for r in matrix if r["source_id"] == "C5-SRC-P1-AFT-PROC-RULES"), vers(r"AFTPR2008"), "already held: raw-data@ad77758d data/raw/indiacode/0000 (590cf7cd..., fc27032f..., c57b113a...)",
        "", "ACQ03-030..035 (optional independent copies)", access="no network needed; owner decision on raw-data provenance (AP-C9-02)", checks="page-image identity review of masthead, S.R.O. number/date and r.1")
    add("P2", "REGISTRATION_OF_HELD_COPY", "Register documented-primary status for held Army Rules amending copies now ineligible (AR-007, 009-011, 014, 016-028, 033-035), starting with AR-018 S.R.O. 44/1985 (r.184) and AR-027 S.R.O. 61/1991 (r.15A)",
        "Amending copy not eligible_for_exact_anchor blocks r.184 (3 items), r.15A, r.13A, r.13 items; all are HF-preserved (5524c3d9)", "C10 registration_proposals_c10; F-03",
        items(r"amending copy not registered"), vers(r"NOT_REGISTERED|eligible_for_exact_anchor=NO"), "HF preservation copies (legal_knowledge/preservation/c5_working_store)", "", "C10 AP-C9-02",
        access="no network needed; provenance documentation decision by the owner", checks="provenance record (archive.org item identifier + MD5) and page-image identity check")
    add("P1", "CUSTODIAN_REQUEST", "Custodian-certified copy of Army Rule 23(3) as notified (S.R.O. 484/1954 p.300) or official confirmation of the India Code compilation wording",
        "C-01: Gazette 'not obliged' vs compilation 'obliged'; blocks every r.23 item (26) and the SoE cluster", "C-01; ESC-R23-3; AQ-STA-01", items(r"C-01"), vers(r"C-01"),
        "MoD / Legislative Department (custodian letter drafted in earlier cycles, not sent)", "", "C8 CUSTODIAN_REQUEST_DRAFTS.md", access="owner signature required; no network", checks="certified copy identity and page match")
    add("P2", "CUSTODIAN_REQUEST", "Regulations for the Army, Revised Edition 1987, Vols I-II, with amendment lists / correction slips",
        "RA 1987 items (4) MISSING; RA1987 versions are instrument-level only", "D-REG-01..03", sum(1 for r in matrix if r["source_id"] == "C5-SRC-P0-RA-1987"), vers(r"RA1987|D-REG-0[123]"),
        "MoD / Army HQ (custodian); access marking to be checked before any processing", "", "C8 regulations_custodian_inventory",
        access="custodian route only; check for restrictive markings before processing (restricted-material rule)", checks="marking inspection; edition and amendment-list identity")
    add("P2", "CUSTODIAN_REQUEST", "Defence Services Regulations / Regulations for the Army 1962 edition",
        "DSR family has no held text; suspected restricted uploads were deliberately not acquired", "D-REG-05; D-REG-07", 0, vers(r"D-REG-0[57]"),
        "custodian only (no public source; suspected restricted copies must not be used)", "", "", access="custodian route only; restricted-material rule applies", checks="marking inspection")
    add("P1", "ACQUIRE_PUBLIC_CANDIDATES", "Pension Regulations for the Army 2008 Parts I-II, Entitlement Rules 1982/2008, Guide to Medical Officers 2023 and the amending circulars",
        "PRA 2008 items (34) and ER/GMO items MISSING; pension versions are instrument-level only; ER 2008 two non-identical versions recorded", "C8 pension_source_coverage",
        sum(1 for r in matrix if r["source_id"] in ("C5-SRC-P1-PRA-2008-PT1", "C5-SRC-P1-PRA-2008-PT2", "C5-SRC-P1-ER-GMO-2023")), vers(r"PRA2008|ER2008|GMO2023|ER1982"),
        "desw.gov.in (not allow-listed in C12 WS-H)", "", "C12 T4-PRA-2008; T4-ER-2008; T4-GMO-2023; T4-PEN-CIRCULARS",
        access=ACCESS_NOTE + "; desw.gov.in needs an allow-list decision", checks=CHECKS)
    add("P2", "DISCOVERY_THEN_ACQUIRE", "Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978 (S.O. 488) and amendment S.O. 4010 (1986)",
        "CCCM items (8) MISSING; S.O. 4010 date disputed (AQ-STA-05)", "I-CCCM-1978; I-CCCM-SO4010-1986", sum(1 for r in matrix if r["source_id"] == "C5-SRC-P1-CCCM-ADJ-RULES"),
        vers(r"CCCM"), "Gazette of India 25-02-1978 Pt II s.3(ii) p.525 (register); archive.org", "", "PILOT-01 T5-02")
    add("P3", "DISCOVERY_THEN_ACQUIRE", "Inter-Services Organisations (Command, Control and Discipline) Act 2023 and rules", "ISO items (4) MISSING", "I-ISO-2023",
        sum(1 for r in matrix if r["source_id"] == "C5-SRC-P1-ISO-ACT-RULES"), vers(r"ISO2023"), "India Code / egazette", "", "")
    return rows


DECISION = {  # review R-06: category-specific decision wording
    "CONFLICT": "Determine the wording to be used for research records, or direct that the conflict stay reserved",
    "SCOPE": "State the scope of the omission to be recorded, or direct that it stay open",
    "APPLICABILITY": "State the applicability limitation to be recorded (dates and offices), or direct that it stay open",
    "ALLEGED_AMENDMENT": "State whether the located text may be used pending the instrument search, or direct that the rule stay blocked",
    "COMMENCEMENT": "State the commencement date (or rule) to be recorded for each instrument, or direct that it stay NOT_STATED_PENDING_ADVICE",
    "RETROSPECTIVITY": "State the effect to be recorded for the deemed period, or direct that it stay open",
    "DATE_DISPUTE": "State which date to record, or direct that both readings stay preserved",
    "VERSION_IDENTITY": "State which version is to be treated as notified once a copy is held, or direct that both stay recorded",
}


def adviser_rows(matrix, recs):
    c12p = [r for r in read_csv(C12F / "CORRECTION_PROPOSALS_C12.csv") if r["proposal_type"] == "EVIDENCE_STATE_PROMOTION"]
    verif = {v["verification_id"]: v for v in read_csv(C12F / "PRIORITY_VERIFICATION.csv")}
    rev = {r["item"].split(" ")[0]: r for r in read_csv(AW / "C12-CONSOLIDATION/reviews/review_wsf_statutory_promotions.csv")}
    c12m = {r["item_id"]: r for r in read_csv(C12F / "IMPROVEMENT_MATRIX.csv")}
    c13 = read_csv(OUT / "EVIDENCE_PROPOSALS_C13.csv")
    rows = []

    def add(**kw):
        kw["packet_id"] = f"A4-ADV-{len(rows) + 1:03d}"
        kw["status"] = "FOR_LEGAL_ADVISER_NO_CONCLUSION_DRAWN"
        rows.append(kw)

    for p in c12p:
        item = p["target"].split(" ")[0]
        m = c12m[item]
        vs = [verif[x] for x in p["evidence_refs"].split(";") if x in verif]
        ev = " | ".join(f"{v['provision']}: {v['edition_or_version'][:160]}; PDF p.{v['pdf_page']}; printed p.{v['printed_page']}; copy {v['copy_sha256'][:16]}; {v['page_evidence_method'][:160]}" for v in vs)
        add(category="PROMOTION_C12F", subject=f"{item} ({m['kb_record_id']}) {m['provision_id'] or m['source_id']}",
            exact_question=(f"May citation item {item} of record {m['kb_record_id']} be recorded as EXACT_ANCHOR at citation level, anchored to the stated page(s), "
                            "on the understanding that currency after the located instruments, authentication of the archival facsimile, commencement and the "
                            "applicability of the cited text to the record's proposition are NOT established?"),
            evidence=ev, competing_readings=("(a) EXACT at citation level: every cited provision/paragraph is page-anchored in a registered eligible copy and no recorded blocker applies; "
                                             "(b) keep PARTIAL: the anchor does not establish currency, commencement (AQ-05) or authentication, and the record's other items are "
                                             f"{m['record_level_state']} at record level ({m['exact_scope'][:120] or 'record scope n/a'})"),
            affected_records=m["kb_record_id"], affected_items=item, decision_required="ACCEPT / REJECT / DEFER the promotion proposal " + p["proposal_id"] + " (citation-level only; no record wording change)",
            cross_refs=f"{p['proposal_id']}; {p['evidence_refs']}", independent_review_verdict=(rev.get(item, {}).get("verdict", "") + ": " + rev.get(item, {}).get("reason", "")[:200]).strip(": "))
    for p in c13:
        add(category="PROMOTION_C13", subject=f"{p['item_id']} ({p['kb_record_id']}) {p['provision_id']}",
            exact_question=(f"May citation item {p['item_id']} of record {p['kb_record_id']} be recorded as EXACT_ANCHOR at citation level on the 1954 Gazette and S.R.O. 17(E)/1993 "
                            "pages listed, with the same reservations (currency, commencement AQ-05, authentication, applicability not established)?"),
            evidence=f"{p['instrument_edition_pages'][:900]} | page evidence {p['page_evidence_ids']} | copies {p['copy_sha256'][:140]}",
            competing_readings="(a) EXACT at citation level on image-checked pages of registered eligible copies; (b) keep PARTIAL until an independent page re-read and the generic chain gaps (AR-001, AR-030 n/a, AR-036, hints) are closed",
            affected_records=p["kb_record_id"], affected_items=p["item_id"], decision_required=f"ACCEPT / REJECT / DEFER {p['proposal_id']} after independent re-read of the C13 page rows",
            cross_refs=p["proposal_id"], independent_review_verdict="NOT_YET_REVIEWED (C13 output; coordinator to arrange independent review)")

    def recs_for(fam, prov):
        return ";".join(r["version_id"] for r in recs if r["family"] == fam and r["provision"] == prov)

    def items_for(pat, fam, prov):
        rx = re.compile(pat) if pat else None
        ns = {"AR1954": "rules-army-rules-1954", "AFT2007": "act-armed-forces-tribunal-2007", "BNS2023": "act-bns-2023"}.get(fam)
        tok = ("r" if fam == "AR1954" else "s") + prov.split(".")[-1] if "." in prov else None
        it = [r for r in matrix if (rx and rx.search(r["blockers_c13"] or "")) or
              (ns and tok and r["provision_id"].startswith(ns + "#") and tok in r["provision_id"].split("#")[1].split(","))]
        return ";".join(sorted({r["kb_record_id"] for r in it}))[:900], len(it)

    conflicts = [
        ("CONFLICT", "Army Rule 23(3) caution wording (C-01)", "Which wording of r.23(3) is to be treated as the notified text: the 1954 Gazette ('You are not obliged to say anything unless you wish to do so') or the India Code compilation ('You are obliged to say anything ...')?",
         "Gazette S.R.O. 484 printed p.300 (PDF p.10), copy c5ef95a9 (HF preserved), C12 PE-1954-300-R23 image check; India Code compilation 48f52219 p.41", "(a) Gazette wording; (b) compilation wording; (c) neither until a custodian-certified copy is obtained",
         "AR1954", "r.23", r"C-01", "AQ-STA-01; ESC-R23-3; C5-CF-C-01"),
        ("CONFLICT", "Army Rule 182 as substituted in 1993 (SC4-01)", "Which text of r.182 is operative: the S.R.O. 17(E)/1993 substitution as printed, or wording found in other texts that is absent from the 1993 Gazette?",
         "S.R.O. 17(E)/1993 item 36, printed p.18 (PE-1993-18-R179-R182), copy e9bf2114", "(a) 1993 Gazette text; (b) other printed texts", "AR1954", "r.182", r"SC4-01", "AQ-STA-12; C5-CF-SC4-01"),
        ("CONFLICT", "Army Rule 177(1)-(2) (C-03)", "Which text of r.177(1)-(2) is operative after S.R.O. 8(E)/2003?", "S.R.O. 8(E)/2003 copy ca5d79c2 (registered eligible; no C12/C13 page row for r.177)",
         "(a) 2003 amending instrument; (b) consolidation; (c) manual", "AR1954", "r.177", r"C-03", "AQ-STA-14; C5-CF-C-03"),
        ("CONFLICT", "Army Rule 192 proviso (C-02)", "Which text of the r.192 proviso (1965) is operative?", "S.R.O. 215/1965 copy be7fefc9 (HF preserved; not eligible)", "(a) amending instrument; (b) consolidation; (c) manual",
         "AR1954", "r.192", r"C-02", "AQ-STA-13; C5-CF-C-02"),
        ("CONFLICT", "Army Rules 193/194 prescribed officer (C-04, C-08, C-09)", "Does r.193 cover s.90(i) as well as s.91(i), and is the operative r.194 the 1989 substituted text?",
         "S.R.O. 302/1987 (4392f326), S.R.O. 332/1989 (31fedb68), S.R.O. 17(E)/1993 item 38 (p.19)", "(a) 1993 substitution governs r.193; (b) earlier text; r.194: (a) 1989 text; (b) other", "AR1954", "r.193", r"C-08|C-09|C-04", "AQ-STA-15; AQ-STA-16"),
        ("SCOPE", "Army Rule 135 'or abstract' omission (S.R.O. 17(E)/1993 item 25; C12F F-09)", "Does item 25 omit 'or abstract' at both places in r.135 ('summary or abstract of evidence given to the accused'; 'such notice or abstract having been given') and with what effect on the notice/abstract procedure described in V9-WF-10 and V9-SC-14?",
         "1954 p.331 (PE-1954-331-R134-R136); 1993 p.17 (PE-1993-17-R134-136)", "(a) both occurrences omitted; (b) only the 'summary or abstract' phrase", "AR1954", "r.135", None, "C12F VERSION_NOTE r.135"),
        ("APPLICABILITY", "Army Rule 15B (S.R.O. 17(E)/2019) disapplying rr.14, 15, 15A for the office of the Chief of Defence Staff", "From 28-12-2019, how does r.15B limit the application of rr.14, 15 and 15A, given that the AR-034 copy is not registered as eligible?",
         "AR-034 copy 138c1da0 (HF preserved; eligible NO); WS-A r15 trace item 8", "(a) limitation applies to the CDS office only; (b) wider effect", "AR1954", "r.15", None, "C12F F-06 APPLICABILITY_NOTE (also rr.14, 15A)"),
        ("ALLEGED_AMENDMENT", "Army Rule 15 '[or Military Secretary]' (OQ-A-10 / GAP-15)", "Should the r.15 text be read with or without '[or Military Secretary]' until the source instrument is located?",
         "1954 p.297 and S.R.O. 205/1961 p.142 image-checked; MML 2 p.142 attribution to S.R.O. 17(E)/1993 unsupported (XC-03)", "(a) 1961 text as located; (b) MML text", "AR1954", "r.15", r"GAP-15", "OQ-A-10; XC-03"),
        ("ALLEGED_AMENDMENT", "Army Rule 22 and S.R.O. 258/2002 (AR-030)", "Pending location of S.R.O. 258/2002, should r.22 be treated as the 1993 substituted text only?",
         "S.R.O. 17(E)/1993 item 5, p.14 (PE-1993-14-R22); r.1(2) in force on publication 06-12-1993 (p.12)", "(a) 1993 text complete; (b) an Explanation may have been added in 2002", "AR1954", "r.22", r"AR-030", "GAP-02"),
        ("COMMENCEMENT", "Instruments that print no commencement clause (S.R.O. 484/1954 and 13 amending S.R.O.s; Army (Amendment) Act 1992)", "On what date does each such instrument take effect (publication, a later notification, or another rule)?",
         "AQ-05 rows in ARMY-RULES-CHAIN-01 and WS-A; 165 version records carry NOT_STATED_PENDING_ADVICE", "(a) date of publication; (b) for the Army (Amendment) Act 1992 (an Act of Parliament), the date of assent 06-09-1992 (the reading on which the India Code 'w.e.f. 6-9-1992' note appears to rest) - posed as a question, not adopted; (c) another date; (d) not determinable from held sources", "AR1954", "", None, "AQ-STA-06; AQ-STA-11; GAP-12"),
        ("RETROSPECTIVITY", "Retrospective deemed omission by S.R.O. 216/1988 (r.2 clauses and r.16A Explanation deemed from 04-06-1979)", "What is the legal effect of the deemed retrospective operation for the period 04-06-1979 to 17-09-1988?",
         "S.R.O. 216/1988 copy 1d67bddd (WSA-PIC-41)", "(a) deemed effect from 1979; (b) effect only from publication for some purposes", "AR1954", "r.2", None, "AQ-06"),
        ("COMMENCEMENT", "AFT Act s.9A (2017 insertion, 2021 amendment deemed 04-04-2021, 2026 substitution)", "From what date does s.9A operate in each form?", "Finance Act 2017 7a5551ba pp.53, 64; TRA 2021 0c2f4e9e pp.1, 13; TRA 2026 be619533 p.1", "(a) notified dates; (b) deemed date only for 2021", "AFT2007", "s.9A", None, "AQ-STA-10"),
        ("COMMENCEMENT", "BNS/BNSS/BSA commencement and the BNS s.106(2) exception", "May the 01-07-2024 commencement be recorded from compilation footnotes while S.O. 848/849/850(E) are not held?", "BNS d4449e99 p.16; BNSS 572c7988; BSA 554b2b4a p.10 (compilation footnotes)", "(a) record as reported; (b) wait for the notifications", "BNS2023", "whole", r"SANHITA", "AQ-STA-19"),
        ("DATE_DISPUTE", "CCCM Rules amendment S.O. 4010 (1986)", "Which date applies: 24-11-1986 (notification) or 06-12-1986 (papers laid / Gazette)?", "Rajya Sabha papers-laid record fa51a4b1 (HF preserved)", "(a) 24-11-1986; (b) 06-12-1986", "CCCM1978", "whole", r"CCCM", "AQ-STA-05"),
        ("VERSION_IDENTITY", "Entitlement Rules 2008: two non-identical versions recorded", "Which ER 2008 text is the notified one?", "no held copy (C9 I-ER-2008)", "(a) version A; (b) version B", "ER2008", "whole", None, "C8 pension_source_coverage ER2008"),
    ]
    for cat, subj, q, ev, comp, fam, prov, pat, xr in conflicts:
        recs_s, n = items_for(pat, fam, prov)
        add(category=cat, subject=subj, exact_question=q, evidence=ev, competing_readings=comp, affected_records=recs_s or "(see version records)",
            affected_items=f"{n} citation items (citing the provision or blocked by the matter)" + (f"; versions {recs_for(fam, prov)}" if recs_for(fam, prov) else ""),
            decision_required=DECISION.get(cat, "State the reading to be used for research records, or direct that the matter stay open"), cross_refs=xr, independent_review_verdict="")
    for a in read_csv(OUT / "TEMPORAL_AXES_A4.csv"):
        add(category="TEMPORAL_AXIS", subject=a["scope"], exact_question=a["question"], evidence=a["evidence_constraint"],
            competing_readings="conduct date | proceedings date | procedural-action date | document preparation/review date", affected_records="all version records of the scope",
            affected_items=f"version records with temporal_axes question {a['question_id']}: {sum(1 for r in recs if r['temporal_axes']['conduct_date']['question_id'] == a['question_id'])}",
            decision_required="State which date axis selects the governing version (per provision class if needed)", cross_refs=a["question_id"], independent_review_verdict="")
    for x in read_csv(OUT / "CRIMINAL_LAW_TRANSITION_LINKS_A4.csv"):
        qid = re.search(r"A4-LQ-XREF-\d+", x["successor_provision_mapping"]).group(0)
        add(category="CROSS_REFERENCE", subject=f"{x['army_act_provision']} -> {x['old_code']}", exact_question=f"After the repeal of the {x['old_code']}, how is this reference in the Army Act to be read, and is there a provision-level correspondence to the successor code?",
            evidence=f"{x['reference_as_recorded'][:300]} ({x['recorded_in']}; {x['evidence_level']})", competing_readings="(a) reference continues to the repealed provision for saved matters; (b) reference read as to the successor provision; (c) other",
            affected_records="(Army Act records citing the section)", affected_items="", decision_required="Provide the reading and, if any, the correspondence source to be used", cross_refs=qid + "; AQ-STA-20", independent_review_verdict="")
    return rows


def md(rows, acq):
    out = ["# C13 A4 legal-adviser review packet", "",
           "Status: **for the legal adviser; no legal conclusion is drawn anywhere in this packet.** Every entry states the exact question, the evidence, the competing readings,",
           "the affected records and the decision required. Promotions are evidence-state *proposals* (citation level only); none is applied. AUTH-LEDGER stays at version 0.", "",
           "| Category | Entries |", "| --- | ---: |"]
    from collections import Counter
    for k, v in sorted(Counter(r["category"] for r in rows).items()):
        out.append(f"| {k} | {v} |")
    out += ["", "## How to use", "",
            "* `ADVISER_REVIEW_PACKET_A4.csv` holds one row per question (`packet_id` A4-ADV-nnn). Promotion rows cite the C12F/C13 proposal id and the verification rows with page, edition and copy sha256.",
            "* The 57 C12F promotions carry the C12 independent reviewer's verdict; the 10 C13 promotions are not yet independently reviewed.",
            "* Conflict, commencement, temporal-axis and cross-reference rows link to existing adviser questions (AQ-STA-nn) where one exists, so nothing is asked twice.",
            "", "## Non-promotion questions", ""]
    for r in rows:
        if not r["category"].startswith("PROMOTION"):
            out.append(f"* **{r['packet_id']} {r['category']}: {r['subject']}.** {r['exact_question']} Readings: {r['competing_readings']}. Decision: {r['decision_required']}. Refs: {r['cross_refs']}.")
    out += ["", f"Acquisition requests for A7: {len(acq)} rows in `ACQUISITION_REQUESTS_A4.csv` (queued only; nothing fetched).", ""]
    return "\n".join(out).encode()


def build():
    matrix = read_csv(OUT / "EVIDENCE_MATRIX_C13.csv")
    recs = [json.loads(l) for l in open(PKG / "records/PROVISION_VERSIONS_C13.jsonl", encoding="utf-8")]
    acq = acq_rows(matrix, recs)
    adv = adviser_rows(matrix, recs)
    files = OrderedDict()
    files["ACQUISITION_REQUESTS_A4.csv"] = csv_bytes(acq, ACQ_FIELDS)
    files["ADVISER_REVIEW_PACKET_A4.csv"] = csv_bytes(adv, ADV_FIELDS)
    files["ADVISER_REVIEW_PACKET_A4.md"] = md(adv, acq)
    for k, v in files.items():
        assert_no_restricted(k, v)
    return files


def main(argv=None):
    require_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    files = build()
    if a.check:
        bad = [n for n, b in files.items() if not (OUT / n).exists() or (OUT / n).read_bytes() != b]
        if bad:
            print("CHECK FAILED: " + ", ".join(bad))
            return 1
        print(f"CHECK OK: {len(files)} packet outputs reproduce byte-for-byte")
        return 0
    for n, b in files.items():
        (OUT / n).write_bytes(b)
    print({n: b.count(b"\n") for n, b in files.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
