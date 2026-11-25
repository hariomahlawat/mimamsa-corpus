#!/usr/bin/env python3
"""C13 A4: provision-level temporal version model (records + coverage), compiled from the reviewed registers.

Inputs (read-only): WS-A provision_change_log, Army Act amendment chain (+cycle-3 addendum), open questions and gaps,
r.15 trace; ARMY-RULES-CHAIN-01 instrument register and provision chronology; C9 instrument records; C10 amendment
graph; C5 copy and conflict registers; C12F page evidence and outputs; C13 page evidence; the held 1954 Gazette and
government compilations (text layer, for page leads only). The frozen KB is read only to verify its hash.

Rules: one record per version of a provision. A version starts with the located event that created it and ends when
the next located event takes effect. A date that no held instrument states is null with a status (never inferred
from publication). Alleged, unlocated or unopened instruments are NOT versions: they are open_items on the provision.
Reserved wording conflicts stay explicit. Every record is AUTOMATED_CANDIDATE_NOT_VERIFIED.

Writes records/PROVISION_VERSIONS_C13.jsonl, outputs/VERSION_COVERAGE_C13.json, outputs/TEMPORAL_AXES_A4.csv,
outputs/CRIMINAL_LAW_TRANSITION_LINKS_A4.csv.   Usage: build_versions_c13.py [--check]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict, defaultdict

from c13a4_common import (AW, C12F_TOOLS, HELD_BASE, PKG, REPO, assert_no_restricted, csv_bytes, prepare_held_base, read_csv,
                          require_env, restricted_sets, verify_frozen)

sys.path.insert(0, str(C12F_TOOLS))
import build_c12f as E  # noqa: E402  (C12F-v1.1 helpers: heading_index, parse_rules, open_alleged_amendments)

OUT = PKG / "outputs"
REC = PKG / "records"
P = {
    "pcl": AW / "WS-A-STATUTORY/provision_change_log.csv",
    "pcl_sup": AW / "WS-A-STATUTORY/provision_change_log_supersessions_cycle3.csv",
    "aa_chain": AW / "WS-A-STATUTORY/army_act_amendment_chain.csv",
    "aa_add": AW / "WS-A-STATUTORY/army_act_amendment_chain_addendum_cycle3.csv",
    "oq": AW / "WS-A-STATUTORY/open_questions.csv", "oq3": AW / "WS-A-STATUTORY/open_questions_cycle3.csv",
    "gaps": AW / "WS-A-STATUTORY/gaps_register.csv", "xc": AW / "WS-A-STATUTORY/mml_footnote_crosscheck_cycle2.csv",
    "wsc_oq": AW / "WS-C-MML/open_questions.csv", "r15": AW / "WS-A-STATUTORY/r15_military_secretary_trace_cycle3.csv",
    "chron": AW / "ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv",
    "instr": AW / "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv",
    "seed": AW / "ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv",
    "c9_instr": AW / "C9-LEGAL-EVIDENCE/STATUTORY/instrument_records.csv",
    "c10_graph": AW / "C10-RECONCILIATION/workstreams/statutory/amendment_graph_c10.csv",
    "c5_copy": AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv",
    "c5_conflict": AW / "SOURCE-LIBRARY-C5/registers/source_conflict_register.csv",
    "pe12": AW / "C12-CONSOLIDATION/statutory_citations/tools/page_evidence_c12.csv",
    "pe13": PKG / "inputs/page_evidence_c13.csv",
    "c12f_matrix": AW / "C12-CONSOLIDATION/statutory_citations/outputs/IMPROVEMENT_MATRIX.csv",
    "c8_regs": AW / "C8-SOURCES/PRIMARY-SOURCES/regulations_custodian_inventory.csv",
}

G1954 = "C5-SRC-P0-ARMY-RULES-1954~C1"
G1954_ED = "Army Rules 1954, S.R.O. 484, Gazette of India Pt II s.4 No.47, 27-11-1954, pp.291-378 (archival facsimile, archive.org in.gazette.central.w.1954-11-27.103686)"
AA_COMP = "C5-SRC-P0-ARMY-ACT-1950-INDIACODE~C1"
AFT_COMP = "C5-SRC-P0-AFT-ACT-2007-INDIACODE~C1"
BNSS_COMP = "C5-SRC-P0-BNSS-2023-INDIACODE~C1"
BSA_COMP = "C5-SRC-P0-BSA-2023-INDIACODE~C1"
AR_CHAIN_GAPS = ["AR-001 E-7/1960 NOT_FOUND", "AR-030 S.R.O. 258/2002 NOT_FOUND", "AR-036 instruments after 06-06-2022 not searched (C5C-004..013 candidates not acquired)",
                 "unopened hints AR-012/013/015/037-046"]
AXIS_Q = {"AR1954": "A4-LQ-AXIS-AR", "AA1950": "A4-LQ-AXIS-AA", "AFT2007": "A4-LQ-AXIS-AFT", "AFTPR2008": "A4-LQ-AXIS-AFT",
          "BNS2023": "A4-LQ-AXIS-BNS", "IPC1860": "A4-LQ-AXIS-BNS", "BNSS2023": "A4-LQ-AXIS-BNSS", "CRPC1973": "A4-LQ-AXIS-BNSS",
          "BSA2023": "A4-LQ-AXIS-BSA", "IEA1872": "A4-LQ-AXIS-BSA"}
STATE_ORDER = {"IMAGE_CHECKED": 0, "COMPILATION_FOOTNOTE_IMAGE_CHECKED": 1, "TEXT_LAYER_ONLY": 2, "COMPILATION_TEXT_LAYER": 3, "NOT_LOCATED_IN_TEXT_LAYER": 4, "NOT_HELD": 5}

R15B_FROM = "2019-12-28"
ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
DMY = re.compile(r"\b(\d{2})-(\d{2})-(\d{4})\b")


def iso(s):
    if not s:
        return None
    m = ISO.search(s)
    if m:
        return m.group(0)
    m = DMY.search(s)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def eff_status(raw, date):
    r = (raw or "").upper()
    if r.startswith("STATED_IN_INSTRUMENT") or r.startswith("EVIDENCED"):
        return ("STATED_DEEMED_IN_INSTRUMENT" if "DEEM" in r else "STATED_IN_INSTRUMENT") if date else "NOT_DETERMINED"
    if r.startswith("NOT_STATED_PENDING_ADVICE"):
        return "NOT_STATED_PENDING_ADVICE"
    if r.startswith("NOT_DETERMINED"):
        return "NOT_DETERMINED"
    if r.startswith("DISPUTED"):
        return "DISPUTED_PRESERVE_BOTH"
    return "UNKNOWN"


def axes(family):
    q = AXIS_Q.get(family, "A4-LQ-AXIS-GENERAL")
    return {k: {"status": "NOT_DETERMINED", "question_id": q} for k in ("conduct_date", "proceedings_date", "procedural_action_date", "document_preparation_review_date")}


def kind_for_rule(rule, provision_text, change_type):
    """Version kind for one rule from the register cell: whole-rule events only when the cell names the rule without a sub-unit."""
    n = rule[1:]
    segs = [g for g in re.split(r";", provision_text or "") if rule in E.parse_rules(g)] or [provision_text or ""]
    seg = segs[0]
    whole = not re.search(rf"\b{re.escape(n)}\s*(?:\(|cls?\.|Explanation|proviso|Table)", seg) and not re.search(r"\bcls?\.|Table|Explanation|proviso", seg)
    c = ((change_type or "") + " " + seg).lower()
    if "omitted w.e.f" in c or "deemed" in c and "omit" in c:
        return "retrospective_omission" if whole else "amendment_words", whole
    if whole and re.search(r"\bomit", c) and "words" not in c and "portion" not in c and "figure" not in c:
        return "omission", whole
    if whole and re.search(r"\bsubst", c) and "words" not in c:
        return "substitution", whole
    if whole and re.search(r"\bins", c) and "sub-rule" not in c:
        return "insertion", whole
    return "amendment_words", whole


def tags_for_rule(n):
    try:
        k = int(re.match(r"\d+", n).group(0))
    except Exception:
        return []
    t = []
    if k in (22, 23, 24, 25):
        t.append("SUMMARY_OF_EVIDENCE")
    if k in (15,):
        t.append("PRIORITY_R15")
    if k in (22, 23, 180):
        t.append(f"PRIORITY_R{k}")
    if 13 <= k <= 18:
        t.append("ADMINISTRATIVE_ACTION_DISCIPLINARY_POWERS")
    if k in (26, 27, 186):
        t.append("DISCIPLINARY_POWERS")
    if 28 <= k <= 176:
        t.append("COURT_MARTIAL_JURISDICTION_PROCEDURE")
    if k in (33, 34, 95, 96, 97, 98, 99, 100, 101, 129, 159):
        t.append("PROCEDURAL_RIGHTS_SAFEGUARDS")
    if k in (53,):
        t.append("LIMITATION_LINK_AA_S122")
    if 177 <= k <= 185:
        t.append("COURT_OF_INQUIRY")
    return t


def tags_for_section(fam, n):
    try:
        k = int(re.match(r"\d+", n).group(0))
    except Exception:
        return []
    if fam == "AA1950":
        return (["LIMITATION"] if k in (122, 123) else []) + (["STATUTORY_COMPLAINTS"] if k in (26, 27) else []) + \
               (["PUNISHMENTS"] if 71 <= k <= 78 or 168 <= k <= 178 else []) + (["DISCIPLINARY_POWERS"] if 79 <= k <= 91 else []) + \
               (["PROCEDURAL_RIGHTS_SAFEGUARDS"] if 101 <= k <= 107 else []) + \
               (["COURT_MARTIAL_JURISDICTION_PROCEDURE"] if 108 <= k <= 167 or 2 <= k <= 6 else []) + (["ADMINISTRATIVE_ACTION"] if 18 <= k <= 25 else [])
    if fam == "AFT2007":
        return ["LIMITATION"] if k in (21, 22) else ["AFT_REMEDIES"]
    return []


def parse_sections(text):
    out = []
    for m in re.finditer(r"\bss?\.\s*(\d{1,3}[A-Z]?)((?:\s*\([^)]*\))*(?:\s*,\s*(?:\(\w+\)\s*)?(?:ss?\.\s*)?\d{1,3}[A-Z]?(?:\s*\([^)]*\))*)*)", text or ""):
        out.append(m.group(1))
        tail = re.sub(r"\([^)]*\)", "", m.group(2))
        out += re.findall(r"(\d{1,3}[A-Z]?)", tail)
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


class Builder:
    def __init__(self):
        self.frozen = verify_frozen()
        self.prov = prepare_held_base()
        E.SCRATCH = HELD_BASE
        self.copies = read_csv(P["c5_copy"])
        self.copy_by_id = {c["copy_id"]: c for c in self.copies}
        self.copy_by_sha = {c["sha256"]: c for c in self.copies}
        self.held = E.HeldCopies(self.copies)
        self.records = []
        self.cited = Counter()
        for r in read_csv(P["c12f_matrix"]):
            p = r["provision_id"]
            if "#" in p:
                a, b = p.split("#")
                for t in set(b.split(",")):
                    self.cited[(a, t)] += 1
        self.pe = read_csv(P["pe12"]) + read_csv(P["pe13"])
        self.pe_by = defaultdict(list)
        for e in self.pe:
            for r in e["provisions"].split(";"):
                self.pe_by[(r, e["instrument_id"])].append(e)
        self.restricted = restricted_sets()

    # ---------------------------------------------------------------- helpers
    def ev(self, role, copy_id=None, sha=None, edition="", pdf=None, printed=None, method="NOT_HELD", ids=(), anchoring=None):
        if sha and not re.fullmatch(r"[0-9a-f]{64}", sha):
            sha = None
        if sha and sha in self.restricted["sha256"]:
            raise SystemExit("restricted copy referenced")
        c = self.copy_by_id.get(copy_id) if copy_id else (self.copy_by_sha.get(sha) if sha else None)
        if c and not copy_id:
            copy_id = c["copy_id"]
        if c and not sha:
            sha = c["sha256"]
        return {"role": role, "copy_id": copy_id, "sha256": sha, "edition": edition, "pdf_page": None if pdf is None else str(pdf),
                "printed_page": None if printed is None else str(printed), "method": method, "evidence_ids": list(ids),
                "eligible_for_exact_anchor": (c["eligible_for_exact_anchor"] == "YES") if c else None,
                "anchoring_copy": anchoring or (self.prov.get(copy_id, "NOT_REGISTERED_IN_C5 (sha256 recorded from register)") if copy_id else
                                                ("NOT_REGISTERED_IN_C5 (sha256 recorded from register)" if sha else "NOT_HELD"))}

    def add(self, **kw):
        kw.setdefault("applicability_exceptions", [])
        kw.setdefault("savings_transitional", [])
        kw.setdefault("conflicts", [])
        kw.setdefault("open_items", [])
        kw.setdefault("priority_tags", [])
        kw.setdefault("retrospective_deemed_effect_from", None)
        kw.setdefault("jurisdiction", {"status": "NOT_DETERMINED_FROM_HELD_TEXT", "note": "territorial and personal application not determined from held text in C13 (legal review)"})
        seen, evs = set(), []
        for e in kw["text_evidence"]:
            key = json.dumps(e, sort_keys=True)
            if key not in seen:
                seen.add(key)
                evs.append(e)
        kw["text_evidence"] = evs
        kw["conflicts"] = sorted({c for c in kw["conflicts"] if c and c.strip() not in ("-", "none", "NONE")})
        kw["temporal_axes"] = axes(kw["family"])
        kw["determination_state"] = "AUTOMATED_CANDIDATE_NOT_VERIFIED"
        kw.setdefault("cited_by_items", 0)
        self.records.append(kw)

    @staticmethod
    def chain(versions):
        """Set effective_to from the next version's effective_from; omission/repeal closes the chain."""
        for i, v in enumerate(versions):
            if v["version_kind"] in ("omission", "repeal", "repeal_with_savings") and v["provision_kind"] != "whole_instrument" or \
               (v["version_kind"] in ("repeal", "repeal_with_savings") and v.get("_ceases")):
                v["effective_to"] = {"date": None, "status": "CEASED_OMITTED_OR_REPEALED", "next_version_id": None,
                                     "basis": "provision omitted/repealed by this version's instrument; no later re-insertion located"}
                continue
            if i + 1 < len(versions):
                nx = versions[i + 1]
                d = nx["effective_from"]["date"]
                v["effective_to"] = {"date": d, "status": "ENDS_ON_NEXT_VERSION" if d else "ENDS_ON_NEXT_VERSION_DATE_NOT_DETERMINED",
                                     "next_version_id": nx["version_id"],
                                     "basis": (f"next located event takes effect {d}" if d else
                                               f"next located event ({nx['created_by']['instrument']}) has no established effective date ({nx['effective_from']['status']})")}
            else:
                v["effective_to"] = {"date": None, "status": "OPEN_ON_LOCATED_INSTRUMENTS", "next_version_id": None,
                                     "basis": "no later event located; currency NOT_ESTABLISHED"}
        for v in versions:
            v.pop("_ceases", None)
        return versions

    # ---------------------------------------------------------------- Army Rules 1954
    def army_rules(self):
        pcl = read_csv(P["pcl"])
        chron = read_csv(P["chron"])
        instr = read_csv(P["instr"])
        ib = {r["instr_id"]: r for r in instr}
        oa = E.open_alleged_amendments(read_csv(P["oq"]) + read_csv(P["oq3"]), read_csv(P["gaps"]), read_csv(P["wsc_oq"]), read_csv(P["xc"]))
        conflicts = defaultdict(set)
        for r in E.C5_RESERVED_RULES:
            conflicts[r].add("C5-BASELINE-RESERVED")
        for c in read_csv(P["c5_conflict"]):
            st = (c.get("status") or "") + " " + (c.get("reserved_status") or "")
            ap = c.get("affected_provision") or ""
            if re.search(r"CONFLICTING|OPEN", st) and ("Army Rule" in ap):
                for n in re.findall(r"\br\.?\s*(\d+[A-Z]?)|\bRule\s+(\d+[A-Z]?)", ap):
                    conflicts["r" + (n[0] or n[1])].add(c["conflict_id"])
        seed = {}
        for s in read_csv(P["seed"]):
            for rr in E.parse_rules(s["provision"]):
                if (s.get("conflict_id") or "").strip() not in ("", "-", "none"):
                    seed.setdefault(rr, set()).add(s["conflict_id"])
        r15b = []
        for t in read_csv(P["r15"]):
            if "15B" in t.get("touches_r15", ""):
                m = re.search(r"disapplies\s+(rr?\.[^,]*?(?:,\s*\d{1,3}[A-Z]?)*)\s+to", t["touches_r15"])
                r15b = E.named_rules(m.group(1)) if m else []
                r15b_ref = f"WS-A r15_military_secretary_trace_cycle3 item {t['item']} ({t['evidence_level']})"
        g_pages = self.held.pages(G1954)
        if g_pages is None:
            raise SystemExit("1954 Gazette not held")
        g_idx = E.heading_index(g_pages)

        events = defaultdict(OrderedDict)  # rule -> {instrument_id: event}  (one version per instrument per rule)
        sup = {r["supersedes_change_id"]: r for r in read_csv(P["pcl_sup"])}
        for r in pcl:
            iid = r["instrument_ref"]
            ct = r["change_type"].lower()
            if not iid.startswith("AR-") or iid == "AR-000" or "enacted" in ct or "no amendment" in ct or "declaration" in ct \
               or r["change_id"].endswith("-N"):
                continue
            ir = ib.get(iid, {})
            bl = r["change_id"].startswith("PCL-BL")
            f = {k: r[k] for k in ("publication_date", "commencement_as_printed", "effective_date", "effective_date_status", "retrospective_deemed_effect_from")}
            if bl:  # baseline rows defer to the ARMY-RULES-CHAIN-01 register for dates
                f = {k: ir.get(k, "") for k in f}
            refs = [f"WS-A provision_change_log#{r['change_id']}"]
            if r["change_id"] in sup:
                s2 = sup[r["change_id"]]
                f.update({k: s2[k] for k in f})
                refs.append(f"WS-A provision_change_log_supersessions_cycle3#{s2['supersession_id']}")
            sha = r["file_sha256"] if re.fullmatch(r"[0-9a-f]{64}", r["file_sha256"] or "") else ir.get("sha256", "")
            ev = {"iid": iid, "item": r["item_no"] or None, "provision_text": r["provision"], "change_type": r["change_type"],
                  "summary": "" if bl else r["text_after_or_summary"], "page_anchor": "" if bl else r["page_anchor"],
                  "pics": r["image_check_ids"], "pub": iso(f["publication_date"]), "comm": f["commencement_as_printed"], "eff": iso(f["effective_date"]),
                  "eff_status": f["effective_date_status"], "retro": iso(f["retrospective_deemed_effect_from"]),
                  "level": r["evidence_level"], "sha": sha, "refs": refs, "bl": bl}
            for rr in E.parse_rules(r["provision"]):
                cur = events[rr].get(iid)
                if cur is None:
                    events[rr][iid] = dict(ev, refs=list(refs))
                    continue
                # merge a second row of the same instrument for the same rule (itemised row wins over baseline row)
                if cur["bl"] and not bl:
                    keep, other = dict(ev, refs=list(refs)), cur
                else:
                    keep, other = cur, ev
                keep["refs"] = sorted(set(keep["refs"]) | set(other["refs"]))
                if other["change_type"] not in keep["change_type"]:
                    keep["change_type"] += "; " + other["change_type"]
                if other["item"] and other["item"] != keep["item"]:
                    keep["item"] = ";".join(x for x in [keep["item"], other["item"]] if x)
                keep["pics"] = ";".join(x for x in [keep["pics"], other["pics"]] if x)
                for k in ("pub", "eff", "retro", "comm", "eff_status", "page_anchor", "summary"):
                    keep[k] = keep[k] or other[k]
                events[rr][iid] = keep
        for r in chron:
            iid = r["instrument_id"]
            if not iid or "NO AMENDMENT" in r["event"].upper() or iid == "AR-000" or ib.get(iid, {}).get("status") == "LOCATED_NOT_AMENDMENT" \
               or "declaration" in r["event"].lower():
                continue
            for rr in E.parse_rules(r["provision"]):
                if iid in events[rr]:
                    events[rr][iid]["refs"].append(f"ARMY-RULES-CHAIN-01 army_rules_provision_chronology ({r['provision']})")
                    for k, v in (("pub", iso(r["publication_date"])), ("eff", iso(r["effective_date"])), ("retro", iso(r["retrospective_deemed_effect_from"])),
                                 ("eff_status", r["effective_date_status"]), ("comm", r["commencement_as_printed"])):
                        events[rr][iid][k] = events[rr][iid][k] or v
                    continue
                events[rr][iid] = {"iid": iid, "item": None, "provision_text": r["provision"], "change_type": r["event"],
                                                     "summary": r["temporal_note"] or r["event"], "page_anchor": "", "pics": "",
                                                     "pub": iso(r["publication_date"]), "comm": r["commencement_as_printed"], "eff": iso(r["effective_date"]),
                                                     "eff_status": r["effective_date_status"], "retro": iso(r["retrospective_deemed_effect_from"]),
                                                     "level": r["evidence_level"], "sha": ib.get(iid, {}).get("sha256", ""), "bl": False,
                                                     "refs": [f"ARMY-RULES-CHAIN-01 army_rules_provision_chronology ({r['provision']}, {iid})"]}
        unlocated = defaultdict(list)
        for r in instr:
            iid = r["instr_id"]
            if iid in ("AR-000", "AR-029"):
                continue
            for rr in E.parse_rules(r["provisions_affected"]):
                if r["status"] in ("GAP", "TO_CHECK"):
                    unlocated[rr].append(f"{iid} {r['instrument']} ({r['status']}; instrument not located/opened: alleged, not a version)")
                    continue
                if r["status"] == "LOCATED_NOT_AMENDMENT":
                    continue
                if iid in events[rr]:
                    continue
                events[rr][iid] = {"iid": iid, "item": None, "provision_text": r["provisions_affected"], "change_type": r["nature"] or "amended",
                                                 "summary": r["provisions_affected"], "page_anchor": r["evidence_locator"], "pics": "",
                                                 "pub": iso(r["publication_date"]), "comm": r["commencement_as_printed"], "eff": iso(r["effective_date"]),
                                                 "eff_status": r["effective_date_status"], "retro": iso(r["retrospective_deemed_effect_from"]),
                                                 "level": r["evidence_level"], "sha": r["sha256"], "bl": False,
                                                 "refs": [f"ARMY-RULES-CHAIN-01 army_rules_instrument_register#{iid} ({r['status']})"]}

        rules = set(events) | {t for (a, t) in self.cited if a == "rules-army-rules-1954"} | set(oa) | set(conflicts) | set(seed)
        prio = {f"r{n}" for n in [15, 22, 23, 24, 25, 180]}
        rules = {r for r in rules if re.match(r"r\d{1,3}[A-Z]?$", r) and int(re.match(r"r(\d+)", r).group(1)) <= 205}
        self.ar_rules = sorted(rules, key=E.rule_key)
        for rule in self.ar_rules:
            n = rule[1:]
            label = f"r.{n}"
            evs = sorted(events.get(rule, {}).values(), key=lambda e: (e["eff"] or e["pub"] or ib.get(e["iid"], {}).get("instrument_date", "9999")[:10], e["iid"]))
            hi = g_idx.get(n)
            img = self.pe_by.get((rule, "AR-000"), [])
            common = dict(family="AR1954", principal_instrument="Army Rules, 1954 (S.R.O. 484 of 27-11-1954)", provision=label, provision_kind="rule",
                          priority_tags=sorted(set(tags_for_rule(n) + (["PRIORITY"] if rule in prio else []))),
                          cited_by_items=self.cited.get(("rules-army-rules-1954", rule), 0))
            cf = sorted(conflicts.get(rule, set()) | seed.get(rule, set()))
            open_items = []
            if rule in oa:
                open_items += [f"{i} (OPEN alleged/unlocated amendment naming {label})" for i in oa[rule]["ids"]] + [f"cross-ref {x}" for x in oa[rule]["xref"]]
            open_items += unlocated.get(rule, [])
            excs = []
            if rule in r15b:
                excs.append({"instrument_id": "AR-034", "provision": "r.15B (inserted by S.R.O. 17(E)/2019)",
                             "effect": f"from {R15B_FROM} (AR-034 in force on publication, as registered): disapplies {label} in relation to the office of the Chief of Defence Staff (as recorded in the WS-A trace)",
                             "anchor_state": "NOT_ANCHORED: AR-034 copy 138c1da0 registered eligible_for_exact_anchor=NO", "ref": r15b_ref})
            versions = []
            starts_with_insert = evs and kind_for_rule(rule, evs[0]["provision_text"], evs[0]["change_type"])[0] == "insertion" and not hi
            if not starts_with_insert:
                if hi:
                    m = "IMAGE_CHECKED" if img else ("TEXT_LAYER_ONLY")
                    end = int(img[0]["continues_to_pdf_page"]) if img and img[0].get("continues_rule") == rule else E.text_layer_end_page(g_pages, g_idx, n)
                    pdf = f"{hi['page']}" + (f"-{end}" if end and end != hi["page"] else "")
                    printed = f"{hi['page'] + 290}" + (f"-{end + 290}" if end and end != hi["page"] else "")
                    e0 = self.ev("principal_as_notified", G1954, edition=G1954_ED, pdf=pdf, printed=printed, method=m,
                                 ids=[x["evidence_id"] for x in img] or [hi["method"]])
                else:
                    e0 = self.ev("principal_as_notified", G1954, edition=G1954_ED, method="NOT_LOCATED_IN_TEXT_LAYER", ids=[])
                versions.append(dict(common, version_id=f"AR1954/{label}/v01", version_seq=1, version_kind="as_notified",
                                     change_summary="Rule as notified in S.R.O. 484/1954" + ("" if hi else " (heading not located in the text layer; page not anchored)"),
                                     created_by={"instrument_id": "AR-000", "instrument": "S.R.O. 484 (Army Rules, 1954)", "instrument_date": "1954-11-27",
                                                 "publication_date": "1954-11-27", "item_no": None,
                                                 "register_refs": ["ARMY-RULES-CHAIN-01 army_rules_instrument_register#AR-000"]},
                                     effective_from={"date": None, "status": "NOT_STATED_PENDING_ADVICE", "reported_date": None,
                                                     "basis": "r.1 of S.R.O. 484 prints no commencement clause (WS-A image check); AQ-05; publication 27-11-1954 is NOT treated as commencement"},
                                     retrospective_deemed_effect_from=None, order_basis="principal instrument",
                                     text_basis="SELF_CONTAINED", text_evidence=[e0], text_status=e0["method"] if e0["method"] in ("IMAGE_CHECKED", "TEXT_LAYER_ONLY") else "NOT_HELD",
                                     sources=["ARMY-RULES-CHAIN-01 army_rules_instrument_register#AR-000", "C12F/C13 page evidence", "1954 Gazette text-layer heading index (C12F heading_index)"]))
            for e in evs:
                k, whole_rule = kind_for_rule(rule, e["provision_text"], e["change_type"])
                ir = ib.get(e["iid"], {})
                c = self.copy_by_sha.get(e["sha"] or ir.get("sha256", ""))
                pes = self.pe_by.get((rule, e["iid"]), [])
                pg = re.search(r"(?:printed|PDF)\s*p\.?\s*([\d\-]+)", e["page_anchor"] or "")
                level = (e["level"] or "").upper()
                if pes:
                    method = "IMAGE_CHECKED"
                elif "IMAGE" in level:
                    method = "IMAGE_CHECKED"
                elif ir.get("status") == "LOCATED_UNVERIFIED" or "TEXT" in level or "REQUIRES_VERIFICATION" in level:
                    method = "TEXT_LAYER_ONLY"
                elif c or e["sha"]:
                    method = "TEXT_LAYER_ONLY"
                else:
                    method = "NOT_HELD"
                ids = [x["evidence_id"] for x in pes] + [x for x in re.split(r"[;,]\s*", e["pics"] or "") if x]
                if method == "IMAGE_CHECKED" and not ids:
                    loc = (ir.get("evidence_locator") or "").strip()
                    if loc:
                        ids = [f"ARMY-RULES-CHAIN-01 {iid} evidence_locator: {loc}"]
                    else:
                        method = "TEXT_LAYER_ONLY"
                if pes:
                    pdfp = ";".join(sorted({x["pdf_page"] + (f"-{x['continues_to_pdf_page']}" if x.get("continues_rule") == rule else "") for x in pes}))
                    prp = ";".join(sorted({x["printed_page"] for x in pes}))
                else:
                    pdfp = pg.group(1) if pg else None
                    prp = pg.group(1) if pg else None
                ed = f"{ir.get('instrument', e['iid'])} dated {ir.get('instrument_date', '')[:10]}; {ir.get('gazette_publication', '') or 'Gazette identity per register'}"
                ev_amend = self.ev("amending_instrument", c["copy_id"] if c else None, sha=(e["sha"] or ir.get("sha256") or None), edition=ed,
                                   pdf=pdfp, printed=prp, method=method, ids=ids)
                text_ev = [ev_amend]
                basis = "SELF_CONTAINED"
                if k == "amendment_words" and versions:
                    basis = "COMPOSITE_WITH_EARLIER_VERSIONS"
                    text_ev = [x for v in versions[-1:] for x in v["text_evidence"]] + [ev_amend]
                if k in ("omission", "retrospective_omission"):
                    basis = "NO_TEXT_OMITTED"
                ef = e["eff"]
                st = eff_status(e["eff_status"], ef)
                ts = min((x["method"] for x in text_ev), key=lambda m: -STATE_ORDER.get(m, 9))
                ts = {"IMAGE_CHECKED": "IMAGE_CHECKED", "TEXT_LAYER_ONLY": "TEXT_LAYER_ONLY", "NOT_LOCATED_IN_TEXT_LAYER": "NOT_HELD", "NOT_HELD": "NOT_HELD"}.get(ts, "TEXT_LAYER_ONLY")
                if basis == "NO_TEXT_OMITTED":
                    ts = "OMITTED_NO_TEXT"
                seq = len(versions) + 1
                versions.append(dict(common, version_id=f"AR1954/{label}/v{seq:02d}", version_seq=seq, version_kind=k,
                                     change_summary=f"{e['provision_text']}: {e['change_type']}" + (f" - {e['summary'][:300]}" if e["summary"] and e["summary"] != e["change_type"] else ""),
                                     created_by={"instrument_id": e["iid"], "instrument": ir.get("instrument", e["iid"]) + (f" ({ir.get('short_title_as_printed')})" if ir.get("short_title_as_printed") else ""),
                                                 "instrument_date": (ir.get("instrument_date") or None), "publication_date": e["pub"], "item_no": e["item"] or None,
                                                 "register_refs": e["refs"]},
                                     effective_from={"date": ef if st.startswith("STATED") else None, "status": st, "reported_date": None,
                                                     "basis": f"commencement as printed: {e['comm'] or 'not recorded'}; register status: {e['eff_status'] or 'not recorded'}"},
                                     retrospective_deemed_effect_from=e["retro"],
                                     order_basis="effective date" if (ef and st.startswith("STATED")) else ("publication date (sort key only; not a commencement)" if e["pub"] else "instrument date (sort key only)"),
                                     text_basis=basis, text_evidence=text_ev, text_status=ts,
                                     sources=e["refs"] + [f"ARMY-RULES-CHAIN-01 army_rules_instrument_register#{e['iid']}"]))
                if k == "retrospective_omission":
                    versions[-1]["open_items"] = ["AQ-06 (legal effect of retrospective deemed omission for the intervening period)"]
            for v in versions:
                v["conflicts"] = cf
                v["open_items"] = sorted(set(v.get("open_items", []) + open_items))
                v["currency"] = {"status": "NOT_ESTABLISHED", "chain_gaps": list(AR_CHAIN_GAPS)}
                v["legal_review_required"] = bool(cf or open_items or excs or v["effective_from"]["status"] != "STATED_IN_INSTRUMENT")
                cf = sorted(c for c in cf if c.strip() not in ("-", "", "none"))
                v["conflicts"] = cf
                if cf and v["version_seq"] == len(versions) and v["version_kind"] not in ("omission", "retrospective_omission"):
                    v["text_status"] = "CONFLICTING"
            for v in self.chain(versions):
                et = v["effective_to"]
                in_force_2019 = et["status"] in ("OPEN_ON_LOCATED_INSTRUMENTS", "ENDS_ON_NEXT_VERSION_DATE_NOT_DETERMINED") or (et["date"] and et["date"] > R15B_FROM)
                v["applicability_exceptions"] = excs if (excs and in_force_2019 and et["status"] != "CEASED_OMITTED_OR_REPEALED") else []
                self.add(**v)

    # ---------------------------------------------------------------- Army Act 1950
    def army_act(self):
        rows = read_csv(P["aa_chain"]) + read_csv(P["aa_add"])
        aa_pages = self.held.pages(AA_COMP)
        aa_idx = E.heading_index(aa_pages) if aa_pages else {}
        oq13 = "OQ-A-13 (Act 19/1955 'Commander-in-Chief' substitutions: sections not enumerated; Schedule not held)"
        events = defaultdict(list)
        chapter_events = []
        for r in rows:
            cid = r["chain_id"]
            if cid in ("AA-00", "AA-03", "AA-05", "AA-09", "AA-10", "AA-11", "AA-12", "AA-13", "AA-C3-04", "AA-C3-05"):
                continue  # principal / no text change / Bill / hint / note rows: recorded in coverage notes, not versions
            if cid == "AA-02":
                continue  # superseded by the cycle-3 itemisation AA-C3-01 (same instrument)
            secs = parse_sections(r["sections_affected"])
            if "Chapter XVI" in r["sections_affected"]:
                chapter_events.append(r)
            for s in secs:
                events[s].append(r)
        cited = {t[1:] for (a, t) in self.cited if a == "act-army-1950"}
        secs = sorted(set(events) | cited, key=lambda x: (int(re.match(r"\d+", x).group(0)), x))
        self.aa_secs = secs
        for s in secs:
            label = f"s.{s}"
            hi = aa_idx.get(s)
            comp = self.ev("government_compilation", AA_COMP, edition="India Code compilation of the Army Act 1950 (as-on date not printed; provenance undocumented; NOT eligible for EXACT)",
                           pdf=hi["page"] if hi else None, printed=None, method="COMPILATION_TEXT_LAYER" if hi else "NOT_LOCATED_IN_TEXT_LAYER",
                           ids=[hi["method"]] if hi else [])
            enacted = self.ev("register_only", None, None, edition="Army Act 1950 as enacted, Gazette of India Extraordinary 23-05-1950 (archive.org in.gazette.e.1950.306): NOT HELD (ACQ-C3-01)", method="NOT_HELD")
            common = dict(family="AA1950", principal_instrument="The Army Act, 1950 (Act 46 of 1950)", provision=label, provision_kind="section",
                          priority_tags=tags_for_section("AA1950", s), cited_by_items=self.cited.get(("act-army-1950", "s" + s), 0))
            evs = sorted(events.get(s, []), key=lambda r: (iso(r["publication_date"]) or iso(r["date_of_instrument"]) or "9999", r["chain_id"]))
            inserted_later = any("inserted" in (r["change_as_printed"] + r["sections_affected"]).lower() and f"s.{s} " in (r["sections_affected"] + " ") for r in evs) or s == "169A" or s == "193A"
            versions = []
            if not inserted_later:
                versions.append(dict(common, version_id=f"AA1950/{label}/v01", version_seq=1, version_kind="as_enacted",
                                     change_summary="Section as enacted in Act 46 of 1950 (enacted text not held; only a compilation is held)",
                                     created_by={"instrument_id": "I-AA-1950", "instrument": "The Army Act, 1950 (Act 46 of 1950)", "instrument_date": "1950-05-20 (assent per compilation only)",
                                                 "publication_date": None, "item_no": None, "register_refs": ["WS-A army_act_amendment_chain#AA-00", "C9 instrument_records#I-AA-1950"]},
                                     effective_from={"date": None, "status": "REPORTED_IN_COMPILATION_ONLY", "reported_date": "1950-07-22",
                                                     "basis": "compilation footnote to s.1(2): 22-07-1950 vide S.R.O. 120 of 22-07-1950; S.R.O. 120 NOT HELD (C9 I-AA-SRO120-1950)"},
                                     order_basis="principal Act", text_basis="SELF_CONTAINED", text_evidence=[enacted, comp], text_status="COMPILATION_ONLY",
                                     sources=["WS-A army_act_amendment_chain#AA-00", "C9 instrument_records#I-AA-1950"]))
            for r in evs:
                ch = (r["change_as_printed"] or "") + " " + r["sections_affected"]
                chl = ch.lower()
                k = ("omission" if re.search(rf"(?:ss?\.[^;]*\b{s}\b[^;]*omitted|section {s} of the principal act shall be omitted|s\.{s}\b.*\bomitted)", chl) and "words" not in chl and "clause" not in chl and "cl." not in chl
                     else "insertion" if "inserted" in chl and (s in ("169A", "193A")) else "repeal" if "repealed" in chl and s == "194" else "amendment_words")
                if s in ("75", "76") and r["chain_id"] == "AA-08-s2":
                    k = "omission"
                if s == "127" and r["chain_id"] == "AA-08-s11":
                    k = "omission"
                if s == "5" and "s.5 omitted" in r["sections_affected"]:
                    k = "omission"
                sha = r["file_sha256"] or None
                c = self.copy_by_sha.get(sha) if sha else None
                if not sha and r.get("bytes_held", "").strip().upper() not in ("", "NO"):
                    pass
                method = ("IMAGE_CHECKED" if "IMAGE_CHECKED" in r["evidence_level"] and "COMPILATION_FOOTNOTE" not in r["evidence_level"] else
                          "COMPILATION_FOOTNOTE_IMAGE_CHECKED" if "COMPILATION_FOOTNOTE_IMAGE_CHECKED" in r["evidence_level"] else
                          "TEXT_LAYER_ONLY" if sha else "NOT_HELD")
                ev_a = self.ev("amending_instrument" if sha else "register_only", c["copy_id"] if c else None, sha,
                               edition=f"{r['instrument']} ({r['number_year']}); {r['gazette_identity'] or 'Gazette identity not recorded'}",
                               pdf=None, printed=None, method=method, ids=[x for x in re.split(r"[;,]\s*", r["image_check_ids"]) if x])
                if method == "COMPILATION_FOOTNOTE_IMAGE_CHECKED":
                    ev_a["edition"] += f"; compilation footnote {r['compilation_footnote']}"
                ef = iso(r["effective_date"])
                st = eff_status(r["effective_date_status"], ef)
                if not sha and st == "UNKNOWN":
                    st = "INSTRUMENT_NOT_HELD"
                seq = len(versions) + 1
                rep = None
                if "2001" in r["instrument"] or "1960" in r["instrument"]:
                    rep = None
                v = dict(common, version_id=f"AA1950/{label}/v{seq:02d}", version_seq=seq, version_kind=k,
                         change_summary=f"{r['sections_affected'][:200]}: {r['change_as_printed'][:300]}",
                         created_by={"instrument_id": r["chain_id"], "instrument": f"{r['instrument']} ({r['number_year']})",
                                     "instrument_date": r["date_of_instrument"] or None, "publication_date": iso(r["publication_date"]), "item_no": None,
                                     "register_refs": [f"WS-A army_act_amendment_chain#{r['chain_id']}"]},
                         effective_from={"date": ef if st.startswith("STATED") else None, "status": st, "reported_date": None,
                                         "basis": f"commencement as printed: {r['commencement_as_printed'] or 'not seen'}; register: {r['effective_date_status']}"},
                         order_basis=("publication date (sort key only; not a commencement)" if iso(r["publication_date"]) else "instrument date / register order (sort key only)"),
                         text_basis="NO_TEXT_OMITTED" if k == "omission" else "COMPOSITE_WITH_EARLIER_VERSIONS",
                         text_evidence=[ev_a] if k == "omission" else ([comp, ev_a]),
                         text_status=("OMITTED_NO_TEXT" if k == "omission" else ("COMPILATION_ONLY" if method != "NOT_HELD" else "NOT_HELD")),
                         sources=[f"WS-A army_act_amendment_chain#{r['chain_id']}"])
                if r["chain_id"] == "AA-06":
                    v["savings_transitional"] = [{"instrument_id": "I-AA-ACT13-1975", "provision": "s.4(2)", "summary": "actions under the repealed Ordinance 3 of 1975 deemed done under the amended Act (as recorded)",
                                                  "ref": "C10 amendment_graph_c10#C9-AG-AA-06"}]
                versions.append(v)
            for v in versions:
                v["open_items"] = [oq13, "AA-13 any amending Act after 1992 NOT_FOUND", "I-AA-NOTIFS s.4/s.9 notifications NOT_HELD"]
                v["currency"] = {"status": "NOT_ESTABLISHED", "chain_gaps": ["enacted Gazette 1950 not held (ACQ-C3-01)", "S.R.O. 120/1950 not held", "AA-13 post-1992 amendments not searched to completion"]}
                v["legal_review_required"] = True
            for v in self.chain(versions):
                self.add(**v)
        for r in chapter_events:
            sha = r["file_sha256"] or None
            v1 = dict(family="AA1950", principal_instrument="The Army Act, 1950 (Act 46 of 1950)", provision="Chapter XVI", provision_kind="chapter",
                      version_id="AA1950/Chapter XVI/v01", version_seq=1, version_kind="as_enacted", change_summary="Chapter XVI as enacted (text not held)",
                      created_by={"instrument_id": "I-AA-1950", "instrument": "The Army Act, 1950 (Act 46 of 1950)", "instrument_date": None, "publication_date": None,
                                  "item_no": None, "register_refs": ["WS-A army_act_amendment_chain#AA-00"]},
                      effective_from={"date": None, "status": "REPORTED_IN_COMPILATION_ONLY", "reported_date": "1950-07-22", "basis": "as for the principal Act"},
                      order_basis="principal Act", text_basis="SELF_CONTAINED",
                      text_evidence=[self.ev("register_only", edition="Army Act 1950 as enacted: NOT HELD", method="NOT_HELD")], text_status="NOT_HELD",
                      sources=["WS-A army_act_amendment_chain#AA-00"], open_items=["sections comprised in Chapter XVI not enumerated from a held enacted text"],
                      currency={"status": "NOT_ESTABLISHED", "chain_gaps": ["enacted Gazette 1950 not held"]}, legal_review_required=True)
            v2 = dict(v1, version_id="AA1950/Chapter XVI/v02", version_seq=2, version_kind="omission", change_summary=f"{r['sections_affected']}: {r['change_as_printed']}",
                      created_by={"instrument_id": r["chain_id"], "instrument": f"{r['instrument']} ({r['number_year']})", "instrument_date": r["date_of_instrument"],
                                  "publication_date": iso(r["publication_date"]), "item_no": None, "register_refs": [f"WS-A army_act_amendment_chain#{r['chain_id']}"]},
                      effective_from={"date": None, "status": eff_status(r["effective_date_status"], None), "reported_date": None, "basis": r["effective_date_status"]},
                      order_basis="publication date (sort key only)", text_basis="NO_TEXT_OMITTED",
                      text_evidence=[self.ev("amending_instrument", None, sha, edition=f"{r['instrument']} ({r['number_year']}); {r['gazette_identity']}", method="IMAGE_CHECKED",
                                             ids=[x for x in re.split(r"[;,]\s*", r["image_check_ids"]) if x])],
                      text_status="OMITTED_NO_TEXT", sources=[f"WS-A army_act_amendment_chain#{r['chain_id']}"])
            for v in self.chain([v1, v2]):
                self.add(**v)

    # ---------------------------------------------------------------- C9/C10-graph families (AFT, BNS/BNSS/BSA and predecessors, CCCM)
    def graph_families(self):
        instr = {r["instrument_id"]: r for r in read_csv(P["c9_instr"])}
        graph = read_csv(P["c10_graph"])

        def shas(text):
            return [h for h in re.findall(r"\b[0-9a-f]{64}\b", text or "") if h not in self.restricted["sha256"]]

        def ev_from(text, role, edition, default_method):
            out = []
            pref = {h[:16]: h for iid in instr for h in shas(instr[iid]["held_copies"])}
            for m in re.finditer(r"(C9R-[\w-]+|C10R-[\w-]+)?\s*\[?(?:corpus raw store |held )?sha256[ =]([0-9a-f]{16})[0-9a-f]*\s*p\.(\d+)", text or ""):
                full = pref.get(m.group(2))
                if not full:
                    continue
                c = self.copy_by_sha.get(full)
                meth = "IMAGE_CHECKED" if "IMG" in (m.group(1) or "") else ("COMPILATION_TEXT_LAYER" if role == "government_compilation" else default_method)
                out.append(self.ev(role, c["copy_id"] if c else None, full, edition=edition, pdf=m.group(3), method=meth, ids=[m.group(1)] if m.group(1) else []))
            return out

        def whole(fam, iid, title, kind, summary, eff, refs, evs, text_status, extra=None, seq=1, created=None):
            ir = instr.get(iid, {})
            v = dict(family=fam, principal_instrument=title, provision="whole", provision_kind="whole_instrument",
                     version_id=f"{fam}/whole/v{seq:02d}", version_seq=seq, version_kind=kind, change_summary=summary,
                     created_by=created or {"instrument_id": iid, "instrument": ir.get("exact_legal_title", title), "instrument_date": ir.get("instrument_date") or None,
                                            "publication_date": None, "item_no": None, "register_refs": refs},
                     effective_from=eff, order_basis="instrument", text_basis="INSTRUMENT_LEVEL",
                     text_evidence=evs or [self.ev("register_only", edition=f"{title}: no held copy", method="NOT_HELD")], text_status=text_status,
                     sources=refs, currency={"status": "NOT_ESTABLISHED", "chain_gaps": [ir.get("missing_originals", "")[:200] or "not recorded"]},
                     legal_review_required=True)
            if extra:
                v.update(extra)
            return v

        def comp_ev(iid, role="government_compilation"):
            ir = instr.get(iid, {})
            out = []
            for h in shas(ir.get("held_copies", ""))[:2]:
                c = self.copy_by_sha.get(h)
                out.append(self.ev(role, c["copy_id"] if c else None, h, edition=f"{ir.get('exact_legal_title', iid)}: held copy ({ir.get('verification_status', '')[:80]})",
                                   method="COMPILATION_TEXT_LAYER" if role == "government_compilation" else "TEXT_LAYER_ONLY"))
            return out

        # --- AFT Act 2007
        aft_title = "The Armed Forces Tribunal Act, 2007 (Act 55 of 2007)"
        aft_comm = {"date": None, "status": "REPORTED_IN_COMPILATION_ONLY", "reported_date": "2008-06-15",
                    "basis": "s.1(2) by notification (image-read, C9R-RD-AFT07-IMG); compilation footnote 15-06-2008 vide S.O. 14(E) of 13-06-2008; S.O. 14(E) NOT HELD"}
        aft_pages = self.held.pages(AFT_COMP)
        aft_idx = E.heading_index(aft_pages) if aft_pages else {}
        aft_edges = defaultdict(list)
        for g in graph:
            if g["target_instrument_id"] == "I-AFT-2007":
                for s in parse_sections(g["provision"]):
                    aft_edges[s].append(g)
        aft_secs = sorted({t[1:] for (a, t) in self.cited if a == "act-armed-forces-tribunal-2007"} | set(aft_edges),
                          key=lambda x: (int(re.match(r"\d+", x).group(0)), x))
        enacted_ev = [x for x in ev_from(instr["I-AFT-2007"]["title_basis"], "principal_as_notified",
                                         "AFT Act 2007 as enacted, Gazette of India Extraordinary Pt II s.1 No.66, 28-12-2007 (corpus raw store copy, unregistered in C5)", "IMAGE_CHECKED")]
        for s in aft_secs:
            label = f"s.{s}"
            hi = aft_idx.get(s)
            comp = self.ev("government_compilation", AFT_COMP, edition="India Code compilation of the AFT Act 2007 (reflects later amendments incl. TRA 2026 s.9A; provenance undocumented; NOT eligible)",
                           pdf=hi["page"] if hi else None, method="COMPILATION_TEXT_LAYER" if hi else "NOT_LOCATED_IN_TEXT_LAYER", ids=[hi["method"]] if hi else [])
            common = dict(family="AFT2007", principal_instrument=aft_title, provision=label, provision_kind="section",
                          priority_tags=tags_for_section("AFT2007", s), cited_by_items=self.cited.get(("act-armed-forces-tribunal-2007", "s" + s), 0))
            versions = []
            def yr(g):
                m = re.search(r"(\d{4})$", g["amending_instrument_id"])
                return f"{m.group(1)}-00-00" if m else "9999"
            edges = sorted(aft_edges.get(s, []), key=lambda g: (iso(g["publication_date"]) or yr(g), g["edge_id"]))
            if s != "9A":
                versions.append(dict(common, version_id=f"AFT2007/{label}/v01", version_seq=1, version_kind="as_enacted",
                                     change_summary="Section as enacted (s.1 and masthead image-read in C9 on the unregistered corpus raw copy; section text itself not image-checked in C13)",
                                     created_by={"instrument_id": "I-AFT-2007", "instrument": aft_title, "instrument_date": "2007-12-25 (assent)", "publication_date": "2007-12-28",
                                                 "item_no": None, "register_refs": ["C9 instrument_records#I-AFT-2007", "C10 amendment_graph_c10#C9-AG-AFT-00"]},
                                     effective_from=dict(aft_comm), order_basis="principal Act", text_basis="SELF_CONTAINED",
                                     text_evidence=enacted_ev + [comp], text_status="COMPILATION_ONLY",
                                     sources=["C9 instrument_records#I-AFT-2007"]))
            for g in edges:
                d = iso(g["commencement_date_evidenced"])
                st = ("STATED_DEEMED_IN_INSTRUMENT" if d and "deem" in g["commencement_date_evidenced"] else "STATED_IN_INSTRUMENT") if d and g["c10_status"] == "EVIDENCED" else \
                     ("NOT_DETERMINED" if g["c10_status"] == "UNRESOLVED_COMMENCEMENT" else "INSTRUMENT_NOT_HELD")
                k = "insertion" if "insert" in g["edge_kind"].lower() else "substitution" if "substitution" == g["edge_kind"].strip().lower() else "amendment_words"
                seq = len(versions) + 1
                evs = ev_from(g["evidence"] + " " + g["saving_or_transitional"] + " " + g["partial_or_staged_commencement"], "amending_instrument",
                              f"{g['amending_instrument']}", "TEXT_LAYER_ONLY") or [self.ev("register_only", edition=g["amending_instrument"], method="NOT_HELD")]
                versions.append(dict(common, version_id=f"AFT2007/{label}/v{seq:02d}", version_seq=seq, version_kind=k,
                                     change_summary=f"{g['provision']}: {g['edge_kind']}",
                                     created_by={"instrument_id": g["amending_instrument_id"], "instrument": g["amending_instrument"], "instrument_date": None,
                                                 "publication_date": iso(g["publication_date"]), "item_no": None, "register_refs": [f"C10 amendment_graph_c10#{g['edge_id']}"]},
                                     effective_from={"date": d if st.startswith("STATED") else None, "status": st, "reported_date": None,
                                                     "basis": f"{g['commencement_as_printed'] or 'commencement not printed on held pages'}; C10 {g['c10_status']}: {g['status_detail'][:160]}"},
                                     order_basis="effective date" if st.startswith("STATED") else "register order (sort key only)",
                                     text_basis="SELF_CONTAINED" if k == "substitution" else "COMPOSITE_WITH_EARLIER_VERSIONS",
                                     text_evidence=evs, text_status="TEXT_LAYER_ONLY" if any(x["method"] in ("IMAGE_CHECKED", "TEXT_LAYER_ONLY") for x in evs) else "NOT_HELD",
                                     sources=[f"C10 amendment_graph_c10#{g['edge_id']}"]))
            for v in versions:
                v["open_items"] = ["C9-AG-AFT-02 (TRA 2021 amendments other than s.9A not itemised)", "I-AFT-TRA2026-COMM commencement notification(s) NOT_HELD"]
                v["currency"] = {"status": "NOT_ESTABLISHED", "chain_gaps": ["S.O. 14(E)/2008 not held", "TRA 2026 commencement not evidenced"]}
                v["legal_review_required"] = True
            for v in self.chain(versions):
                self.add(**v)
        # AFT Procedure Rules 2008 (whole) + 2011 amendment of r.7
        pr = instr["I-AFT-PR-2008"]
        v1 = whole("AFTPR2008", "I-AFT-PR-2008", "The Armed Forces Tribunal (Procedure) Rules, 2008 (S.R.O. 26(E))", "as_notified",
                   "Rules made under AFT Act s.41; held only in the corpus raw store (not registered in C5, so the 46 citing items are MISSING_EVIDENCE)",
                   {"date": "2008-09-17", "status": "STATED_IN_INSTRUMENT", "reported_date": None, "basis": pr["commencement_evidence"][:200]},
                   ["C9 instrument_records#I-AFT-PR-2008", "C10 amendment_graph_c10#C9-AG-AFTPR2008"], comp_ev("I-AFT-PR-2008", "principal_as_notified"), "TEXT_LAYER_ONLY")
        amd = instr["I-AFT-PR-AMD-2011"]
        r7a = whole("AFTPR2008", "I-AFT-PR-AMD-2011", "The Armed Forces Tribunal (Procedure) Rules, 2008 (S.R.O. 26(E))", "amendment_words",
                    "r.7 renumbered as r.7(1); r.7(2) inserted (fee payment) by the AFT (Procedure) Amendment Rules, 2011 (S.R.O. 05(E))",
                    {"date": "2011-07-29", "status": "STATED_IN_INSTRUMENT", "reported_date": None, "basis": amd["commencement_evidence"][:200]},
                    ["C9 instrument_records#I-AFT-PR-AMD-2011", "C10 amendment_graph_c10#C9-AG-AFTPR2011"], comp_ev("I-AFT-PR-AMD-2011", "amending_instrument"), "TEXT_LAYER_ONLY", seq=2)
        r7a["provision"] = "whole"
        for v in self.chain([v1, r7a]):
            v["cited_by_items"] = sum(n for (a, t), n in self.cited.items() if a.startswith("rules-aft"))
            self.add(**v)

        # --- BNS / BNSS / BSA and the repealed codes (1 July 2024 transition)
        trans = [("BNS2023", "I-BNS-2023", "The Bharatiya Nyaya Sanhita, 2023 (Act 45 of 2023)", "S.O. 850(E) dated 23-02-2024", "I-BNS-COMM-SO850E", "s.106(2)",
                  "IPC1860", "I-IPC-1860", "The Indian Penal Code (Act 45 of 1860)", "s.358", "C9-AG-BNS-REPEAL", "act-bns-2023", None),
                 ("BNSS2023", "I-BNSS-2023", "The Bharatiya Nagarik Suraksha Sanhita, 2023 (Act 46 of 2023)", "S.O. 848(E) dated 23-02-2024", "I-BNSS-COMM-SO848E",
                  "the First Schedule entry relating to BNS s.106(2)", "CRPC1973", "I-CRPC-1973", "The Code of Criminal Procedure, 1973 (Act 2 of 1974)", "s.531",
                  "C9-AG-BNSS-REPEAL", "act-bnss-2023", BNSS_COMP),
                 ("BSA2023", "I-BSA-2023", "The Bharatiya Sakshya Adhiniyam, 2023 (Act 47 of 2023)", "S.O. 849(E) dated 23-02-2024", "I-BSA-COMM-SO849E", None,
                  "IEA1872", "I-IEA-1872", "The Indian Evidence Act, 1872 (Act 1 of 1872)", "s.170", "C9-AG-BSA-REPEAL", "act-bsa-2023", BSA_COMP)]
        gby = {g["edge_id"]: g for g in graph}
        for fam, iid, title, so, so_id, exc, ofam, oid, otitle, rep_s, rep_edge, prov_ns, comp_id in trans:
            ir = instr[iid]
            comm = {"date": None, "status": "REPORTED_IN_COMPILATION_ONLY", "reported_date": "2024-07-01",
                    "basis": f"{ir['commencement_evidence'][:220]} (commencement notification {so} NOT HELD; the 1 July 2024 date is not evidenced from a held notification)"}
            excs = [{"instrument_id": so_id, "provision": exc, "effect": f"excluded from the 01-07-2024 appointment as printed in the compilation footnote ({so})",
                     "anchor_state": "NOT_ANCHORED: notification not held", "ref": f"C9 instrument_records#{iid}"}] if exc else []
            cev = comp_ev(iid)
            v = whole(fam, iid, title, "commencement", f"{title}: enacted 25-12-2023 (Gazette not held); commencement as reported in the compilation footnote",
                      comm, [f"C9 instrument_records#{iid}", f"C10 amendment_graph_c10#C9-AG-{fam[:-4] if fam != 'BNSS2023' else 'BNSS'}-COMM"], cev, "COMPILATION_ONLY",
                      extra={"applicability_exceptions": excs, "open_items": [f"{so_id} commencement notification NOT_HELD", "Gazette as enacted NOT_HELD"],
                             "cited_by_items": sum(n for (a, t), n in self.cited.items() if a == prov_ns)})
            for x in self.chain([v]):
                self.add(**x)
            g = gby[rep_edge]
            sav = [{"instrument_id": iid, "provision": f"{rep_s}(2)-(3)" if fam != "BSA2023" else f"{rep_s}(2)", "summary": g["saving_or_transitional"][:300],
                    "ref": f"C10 amendment_graph_c10#{rep_edge}"}]
            oe = comp_ev(oid, "government_compilation")
            o1 = whole(ofam, oid, otitle, "as_enacted", f"{otitle}: text held only as a later rendering/compilation (enacted text not held)",
                       {"date": None, "status": "NOT_DETERMINED", "reported_date": iso(instr[oid]["instrument_date"]) if ofam == "IEA1872" else None,
                        "basis": instr[oid]["commencement_evidence"][:200]}, [f"C9 instrument_records#{oid}"], oe, "COMPILATION_ONLY")
            repev = ev_from(g["saving_or_transitional"] + " " + g["evidence"], "government_compilation", f"{title} {rep_s} (compilation)", "COMPILATION_TEXT_LAYER")
            o2 = whole(ofam, oid, otitle, "repeal_with_savings", f"repealed by {title} {rep_s}(1) with savings in {rep_s}(2)" + ("-(3)" if fam != "BSA2023" else ""),
                       {"date": None, "status": "REPORTED_IN_COMPILATION_ONLY", "reported_date": "2024-07-01",
                        "basis": f"repeal operates from the commencement of {title}; commencement notification {so} NOT HELD"},
                       [f"C10 amendment_graph_c10#{rep_edge}"], repev, "COMPILATION_ONLY", seq=2,
                       created={"instrument_id": iid, "instrument": f"{title} {rep_s}", "instrument_date": "2023-12-25", "publication_date": None, "item_no": rep_s,
                                "register_refs": [f"C10 amendment_graph_c10#{rep_edge}"]},
                       extra={"savings_transitional": sav, "open_items": [f"{so_id} NOT_HELD", "A4-LQ-AXIS: which date governs pending/past matters under the savings clause is a legal question"]})
            o2["_ceases"] = True
            for x in self.chain([o1, o2]):
                self.add(**x)
            # section-level base versions for cited sections of the new codes
            pages = self.held.pages(comp_id) if comp_id else None
            idx = E.heading_index(pages) if pages else {}
            for (a, t), n in sorted(self.cited.items()):
                if a != prov_ns:
                    continue
                s = t[1:]
                hi = idx.get(s)
                e1 = self.ev("government_compilation", comp_id, edition=f"India Code compilation of {title} (provenance undocumented; NOT eligible)",
                             pdf=hi["page"] if hi else None, method="COMPILATION_TEXT_LAYER" if hi else "NOT_LOCATED_IN_TEXT_LAYER", ids=[hi["method"]] if hi else []) if comp_id else \
                    (cev[0] if cev else self.ev("register_only", edition=title, method="NOT_HELD"))
                sv = dict(family=fam, principal_instrument=title, provision=f"s.{s}", provision_kind="section", version_id=f"{fam}/s.{s}/v01", version_seq=1,
                          version_kind="as_enacted", change_summary=f"s.{s} as enacted (compilation text only)" + (" - repeal and savings provision" if f"s.{s}" == rep_s else ""),
                          created_by={"instrument_id": iid, "instrument": title, "instrument_date": "2023-12-25", "publication_date": None, "item_no": None,
                                      "register_refs": [f"C9 instrument_records#{iid}"]},
                          effective_from=dict(comm), order_basis="principal Act", text_basis="SELF_CONTAINED", text_evidence=[e1], text_status="COMPILATION_ONLY",
                          sources=[f"C9 instrument_records#{iid}", "C12F IMPROVEMENT_MATRIX citation"], cited_by_items=n,
                          applicability_exceptions=[x for x in excs if x["provision"].startswith(f"s.{s}")],
                          savings_transitional=sav if f"s.{s}" == rep_s else [],
                          open_items=[f"{so_id} NOT_HELD"], currency={"status": "NOT_ESTABLISHED", "chain_gaps": ["post-2024 amendments not searched in C13"]},
                          legal_review_required=True)
                for x in self.chain([sv]):
                    self.add(**x)

        # --- CCCM Rules 1978 (adjustment of jurisdiction between criminal courts and courts-martial)
        g = gby["C9-AG-CCCM-SO4010"]
        c1 = whole("CCCM1978", "I-CCCM-1978", "Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules, 1978 (S.O. 488)", "as_notified",
                   "Rules as notified (S.O. 488 dated 09-02-1978 per register; Gazette 25-02-1978 per register); NOT HELD",
                   {"date": None, "status": "INSTRUMENT_NOT_HELD", "reported_date": None, "basis": "instrument not held"}, ["C9 instrument_records#I-CCCM-1978"], [], "NOT_HELD")
        c2 = whole("CCCM1978", "I-CCCM-SO4010-1986", "Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules, 1978 (S.O. 488)", "amendment_words",
                   g["provision"], {"date": None, "status": "DISPUTED_PRESERVE_BOTH", "reported_date": None,
                                    "basis": instr["I-CCCM-SO4010-1986"]["instrument_date"][:300]},
                   ["C10 amendment_graph_c10#C9-AG-CCCM-SO4010", "C9 instrument_records#I-CCCM-SO4010-1986"], comp_ev("I-CCCM-SO4010-1986", "register_only"), "NOT_HELD", seq=2,
                   extra={"conflicts": ["C9 DISPUTED_PRESERVE_BOTH (S.O. 4010 date: 24-11-1986 notification vs 06-12-1986)"]})
        for x in self.chain([c1, c2]):
            x["cited_by_items"] = 8 if x["version_seq"] == 1 else 0
            self.add(**x)

    # ---------------------------------------------------------------- regulations and pension instruments (held sources only allow instrument-level records)
    def regulations(self):
        instr = {r["instrument_id"]: r for r in read_csv(P["c9_instr"])}
        regs = {r["inv_id"]: r for r in read_csv(P["c8_regs"])}
        ra5 = self.copy_by_id.get("C5-SRC-P0-RA-1987-CH5-INDIACODE~C1")
        items = [
            ("RA1987", "whole", "whole_instrument", "Regulations for the Army, Revised Edition 1987 (Vols I and II)", "edition",
             "Edition as published; Vols I and II NOT HELD (C8 D-REG-01/02); amendment lists/correction slips NOT HELD (D-REG-03)", [], "NOT_HELD", ["C8 regulations_custodian_inventory#D-REG-01", "#D-REG-02", "#D-REG-03"]),
            ("RA1987", "paras 201-220 (Ch. V)", "paragraph_range", "Regulations for the Army, Revised Edition 1987 (Vols I and II)", "edition",
             "Chapter V (Reserve Forces) paras 201-220: India Code extract held (5 pp., provenance undocumented, incomplete extract)",
             [self.ev("government_compilation", ra5["copy_id"] if ra5 else None, ra5["sha256"] if ra5 else None,
                      edition="RA 1987 Ch. V India Code extract (5 pp.; provenance undocumented; NOT eligible)", method="COMPILATION_TEXT_LAYER")] if ra5 else [],
             "COMPILATION_ONLY", ["C8 regulations_custodian_inventory#D-REG-04", "C5 source_copy_register#C5-SRC-P0-RA-1987-CH5-INDIACODE~C1"]),
            ("DSR", "whole", "whole_instrument", "Defence Services Regulations / Regulations for the Army 1962 (earlier DSR edition)", "edition",
             "NOT HELD (D-REG-05 not found in searched sources; D-REG-07 uploads suspected restricted and not acquired)", [], "NOT_HELD",
             ["C8 regulations_custodian_inventory#D-REG-05", "#D-REG-07"]),
            ("PRA2008", "whole", "whole_instrument", "Pension Regulations for the Army 2008 (Parts I and II)", "edition", "NOT HELD", [], "NOT_HELD", ["C9 instrument_records#I-PRA-2008-PT1", "#I-PRA-2008-PT2"]),
            ("PRA1961", "whole", "whole_instrument", "Pension Regulations for the Army 1961 (Parts I and II)", "edition", "NOT HELD", [], "NOT_HELD", ["C9 instrument_records#I-PRA-1961"]),
            ("ER1982", "whole", "whole_instrument", "Entitlement Rules for Casualty Pensionary Awards 1982", "edition", "NOT HELD", [], "NOT_HELD", ["C9 instrument_records#I-ER-1982"]),
            ("ER2008", "whole", "whole_instrument", "Entitlement Rules for Casualty Pensionary Awards 2008", "edition",
             "NOT HELD; registers record two non-identical versions (conflict preserved)", [], "NOT_HELD", ["C9 instrument_records#I-ER-2008"]),
            ("ER2023", "whole", "whole_instrument", "Entitlement Rules 2023 (Appendix-I to MoD letter dated 21-09-2023)", "edition",
             "Held copy incomplete (letter + App-I + annexures; provenance undocumented); complete instrument NOT HELD",
             [self.ev("register_only", "C5-SRC-P1-ER-2023-HELD-13MB~C1", None, edition="DESW-hosted ER 2023 bundle (incomplete; provenance undocumented)", method="TEXT_LAYER_ONLY")],
             "TEXT_LAYER_ONLY", ["C9 instrument_records#I-ER-2023", "C8 pension_source_coverage#ER2023-HELD-INCOMPLETE"]),
            ("GMO2023", "whole", "whole_instrument", "Guide to Medical Officers (Military Pensions) 2023 (Appendix-II)", "edition", "NOT HELD", [], "NOT_HELD", ["C9 instrument_records#I-GMO-2023"]),
            ("ISO2023", "whole", "whole_instrument", "Inter-Services Organisations (Command, Control and Discipline) Act, 2023", "as_enacted", "NOT HELD", [], "NOT_HELD", ["C9 instrument_records#I-ISO-2023"]),
        ]
        cites = {"RA1987": 4, "PRA2008": 34, "ER2023": 3, "ISO2023": 4}
        for fam, prov, pk, title, kind, summ, evs, ts, refs in items:
            if any(re.search(r"air\s+force", x, re.I) for x in (title, summ)):
                raise SystemExit("restricted family must not be modelled")
            v = dict(family=fam, principal_instrument=title, provision=prov, provision_kind=pk, version_id=f"{fam}/{prov}/v01", version_seq=1, version_kind=kind,
                     change_summary=summ, created_by={"instrument_id": refs[0].split("#")[-1], "instrument": title, "instrument_date": None, "publication_date": None,
                                                      "item_no": None, "register_refs": refs},
                     effective_from={"date": None, "status": "INSTRUMENT_NOT_HELD" if ts == "NOT_HELD" else "NOT_DETERMINED", "reported_date": None,
                                     "basis": "edition/commencement date not established from a held instrument"},
                     order_basis="single recorded edition", text_basis="INSTRUMENT_LEVEL",
                     text_evidence=evs or [self.ev("register_only", edition=f"{title}: NOT HELD", method="NOT_HELD")], text_status=ts, sources=refs,
                     open_items=["acquisition / custodian request (see ACQUISITION_REQUESTS_A4.csv)"] + (["two non-identical ER 2008 versions recorded"] if fam == "ER2008" else []),
                     conflicts=(["ER2008-TWO-VERSIONS (C9 I-ER-2008)"] if fam == "ER2008" else []),
                     currency={"status": "NOT_ESTABLISHED", "chain_gaps": ["amendment lists / circulars not held"]}, legal_review_required=True,
                     cited_by_items=cites.get(fam, 0) if prov in ("whole",) else 0)
            for x in self.chain([v]):
                self.add(**x)

    # ---------------------------------------------------------------- outputs
    def transition_links(self):
        """Army Act provisions that refer to the old criminal codes (as recorded in image-checked WS-A rows): successor mapping NOT determined."""
        out = []
        for r in read_csv(P["aa_chain"]):
            t = r["change_as_printed"] + " " + r["sections_affected"]
            if re.search(r"Criminal Procedure|CrPC|Penal Code|Evidence Act", t, re.I):
                for s in parse_sections(r["sections_affected"]):
                    out.append({"army_act_provision": f"s.{s}", "reference_as_recorded": r["change_as_printed"][:300], "recorded_in": f"WS-A army_act_amendment_chain#{r['chain_id']}",
                                "evidence_level": r["evidence_level"], "old_code": "CrPC 1973" if "1973" in t else "CrPC (1898)",
                                "successor_code_after_repeal": "BNSS 2023 (repeals CrPC 1973 by s.531(1), compilation text)",
                                "successor_provision_mapping": "NOT_DETERMINED (no held instrument maps the referenced CrPC provisions to BNSS provisions; effect of the reference after 01-07-2024 is a legal question: A4-LQ-XREF-01)",
                                "status": "AUTOMATED_CANDIDATE_NOT_VERIFIED"})
        out.append({"army_act_provision": "AA s.3 / s.69 / s.70 (civil offence; offences triable by criminal courts)", "reference_as_recorded": "KB records cite IPC-era and BNS-era offences",
                    "recorded_in": "C12F IMPROVEMENT_MATRIX (act-bns-2023#s358 items); C10 amendment_graph_c10#C9-AG-BNS-REPEAL", "evidence_level": "COMPILATION_ONLY",
                    "old_code": "IPC 1860", "successor_code_after_repeal": "BNS 2023 (repeals IPC by s.358(1), compilation text)",
                    "successor_provision_mapping": "NOT_DETERMINED (no correspondence table held; A4-LQ-XREF-02)", "status": "AUTOMATED_CANDIDATE_NOT_VERIFIED"})
        out.append({"army_act_provision": "evidence provisions applied at courts-martial (e.g. electronic records)", "reference_as_recorded": "KB records cite IEA s.65B (Anvar 2014, Arjun 2020) and BSA ss.61-63",
                    "recorded_in": "C12F IMPROVEMENT_MATRIX (act-bsa-2023 items); C10 amendment_graph_c10#C9-AG-BSA-REPEAL", "evidence_level": "COMPILATION_ONLY",
                    "old_code": "IEA 1872", "successor_code_after_repeal": "BSA 2023 (repeals IEA by s.170(1), compilation text)",
                    "successor_provision_mapping": "NOT_DETERMINED (no correspondence table held; A4-LQ-XREF-03)", "status": "AUTOMATED_CANDIDATE_NOT_VERIFIED"})
        return out

    def axes_rows(self):
        q = [("A4-LQ-AXIS-AR", "Army Rules 1954 (all versions)", "Which date selects the governing version of a rule: the date of the alleged conduct, the date proceedings commenced, the date of the specific procedural act (e.g. hearing of charge, recording of SoE, CoI sitting), or the date a document was prepared/reviewed?",
              "Unstated commencement of S.R.O. 484 and of most amending S.R.O.s (AQ-05); retrospective deemed effect (AQ-06)"),
             ("A4-LQ-AXIS-AA", "Army Act 1950", "Which date (conduct, proceedings, procedural act or document preparation/review) selects the governing version of an Army Act section, e.g. s.122 limitation as substituted by Act 37/1992, or ss.75-76 and 127 omitted by Act 37/1992?", "Act 37/1992 prints no commencement clause (AQ-05)"),
             ("A4-LQ-AXIS-AFT", "AFT Act 2007 / AFT Procedure Rules", "Which date governs AFT jurisdiction and limitation questions across S.O. 14(E)/2008, the 2008 RDO, TRA 2021 (deemed 04-04-2021) and TRA 2026?", "S.O. 14(E)/2008 and TRA 2026 commencement not held"),
             ("A4-LQ-AXIS-BNS", "IPC 1860 -> BNS 2023", "For an offence alleged before the BNS commencement but tried or charged after it, which date governs the applicable substantive law, given BNS s.358(2)-(3) as printed in the compilation?", "S.O. 850(E) not held; compilation only"),
             ("A4-LQ-AXIS-BNSS", "CrPC 1973 -> BNSS 2023", "For proceedings pending on, or steps taken after, the BNSS commencement, which date governs the applicable procedure, given BNSS s.531(2) as printed in the compilation?", "S.O. 848(E) not held; compilation only"),
             ("A4-LQ-AXIS-BSA", "IEA 1872 -> BSA 2023", "For evidence produced/recorded after the BSA commencement in proceedings begun earlier, which date governs admissibility, given BSA s.170(2) as printed in the compilation?", "S.O. 849(E) not held; compilation only"),
             ("A4-LQ-AXIS-GENERAL", "Regulations, pension instruments, CCCM, ISO Act", "These instruments are not held and are modelled only at instrument level: which date (event, claim, decision or review) governs the applicable edition?", "instruments not held")]
        return [{"question_id": a, "scope": b, "axes": "conduct_date | proceedings_date | procedural_action_date | document_preparation_review_date",
                 "question": c, "evidence_constraint": d, "determination": "NOT_DETERMINED (legal adviser)", "status": "OPEN"} for a, b, c, d in q]

    def build(self):
        self.army_rules()
        self.army_act()
        self.graph_families()
        self.regulations()
        recs = sorted(self.records, key=lambda r: (r["family"], r["provision"], r["version_seq"]))
        ids = [r["version_id"] for r in recs]
        dup = [k for k, v in Counter(ids).items() if v > 1]
        if dup:
            raise SystemExit(f"duplicate version ids {dup[:5]}")
        fields = list(json.loads((PKG / "schema/provision_version.schema.json").read_text())["required"])
        lines = [json.dumps({k: r[k] for k in fields}, ensure_ascii=False, sort_keys=False) for r in recs]
        jsonl = ("\n".join(lines) + "\n").encode("utf-8")
        cov = self.coverage(recs)
        files = OrderedDict()
        files["records/PROVISION_VERSIONS_C13.jsonl"] = jsonl
        files["outputs/VERSION_COVERAGE_C13.json"] = (json.dumps(cov, indent=1, ensure_ascii=False) + "\n").encode()
        files["outputs/TEMPORAL_AXES_A4.csv"] = csv_bytes(self.axes_rows(), ["question_id", "scope", "axes", "question", "evidence_constraint", "determination", "status"])
        files["outputs/CRIMINAL_LAW_TRANSITION_LINKS_A4.csv"] = csv_bytes(self.transition_links(), ["army_act_provision", "reference_as_recorded", "recorded_in", "evidence_level",
                                                                                                   "old_code", "successor_code_after_repeal", "successor_provision_mapping", "status"])
        for k, v in files.items():
            assert_no_restricted(k, v)
        return files

    def coverage(self, recs):
        fam = defaultdict(lambda: {"provisions": set(), "versions": 0})
        for r in recs:
            fam[r["family"]]["provisions"].add(r["provision"])
            fam[r["family"]]["versions"] += 1
        prio_rules = ["r.15", "r.22", "r.23", "r.24", "r.25", "r.180"]
        prio = {}
        for p in prio_rules:
            vs = [r for r in recs if r["family"] == "AR1954" and r["provision"] == p]
            prio[p] = [{"version_id": v["version_id"], "kind": v["version_kind"], "by": v["created_by"]["instrument"], "effective_from": v["effective_from"]["date"] or v["effective_from"]["status"],
                        "effective_to": v["effective_to"]["date"] or v["effective_to"]["status"], "text_status": v["text_status"], "conflicts": v["conflicts"],
                        "open_items": v["open_items"], "exceptions": [e["provision"] for e in v["applicability_exceptions"]]} for v in vs]
        tagc = Counter(t for r in recs for t in set(r["priority_tags"]))
        cited_ar = {t for (a, t) in self.cited if a == "rules-army-rules-1954" and re.match(r"r\d{1,3}[A-Z]?$", t) and int(re.match(r"r(\d+)", t).group(1)) <= 205}
        modelled_ar = {r["provision"].replace("r.", "r") for r in recs if r["family"] == "AR1954"}
        cited_aa = {t for (a, t) in self.cited if a == "act-army-1950"}
        modelled_aa = {r["provision"].replace("s.", "s") for r in recs if r["family"] == "AA1950"}
        return OrderedDict([
            ("version_model", "C13A4-VM-v1"), ("records", len(recs)),
            ("by_family", {k: {"provisions": len(v["provisions"]), "versions": v["versions"]} for k, v in sorted(fam.items())}),
            ("by_version_kind", dict(sorted(Counter(r["version_kind"] for r in recs).items()))),
            ("by_text_status", dict(sorted(Counter(r["text_status"] for r in recs).items()))),
            ("by_effective_from_status", dict(sorted(Counter(r["effective_from"]["status"] for r in recs).items()))),
            ("by_effective_to_status", dict(sorted(Counter(r["effective_to"]["status"] for r in recs).items()))),
            ("records_with_conflicts", sum(1 for r in recs if r["conflicts"])),
            ("records_with_open_items", sum(1 for r in recs if r["open_items"])),
            ("records_with_applicability_exceptions", sum(1 for r in recs if r["applicability_exceptions"])),
            ("records_with_savings_transitional", sum(1 for r in recs if r["savings_transitional"])),
            ("records_with_retrospective_deemed_effect", sum(1 for r in recs if r["retrospective_deemed_effect_from"])),
            ("records_legal_review_required", sum(1 for r in recs if r["legal_review_required"])),
            ("effective_from_date_established", sum(1 for r in recs if r["effective_from"]["date"])),
            ("priority_tag_counts", dict(sorted(tagc.items()))),
            ("army_rules_cited_rules_modelled", f"{len(cited_ar & modelled_ar)}/{len(cited_ar)}"),
            ("army_act_cited_sections_modelled", f"{len(cited_aa & modelled_aa)}/{len(cited_aa)}"),
            ("priority_rules", prio),
            ("not_modelled", [
                "Army Rules appendices and forms (A6 forms workstream scope); rule-level only here",
                "Army Act Bills (AA-11, AA-12), repeals of spent amending Acts (AA-03, AA-09, AA-10) and extension instruments (AA-C3-04): no text change, recorded in the chain register",
                "Regulations for the Army 1987 beyond Ch. V, DSR, pension regulations and circulars: instrument level only (texts not held)",
                "The restricted RM-001 item (config/restricted_material.json on claude/c13-gov) is excluded entirely",
                "Air Force Act 1950 and Navy Act 1957: outside the A4 priority list; compilations held but not modelled in C13"]),
        ])


def main(argv=None):
    require_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    files = Builder().build()
    if a.check:
        bad = [n for n, b in files.items() if not (PKG / n).exists() or (PKG / n).read_bytes() != b]
        if bad:
            print("CHECK FAILED: " + ", ".join(bad))
            return 1
        print(f"CHECK OK: {len(files)} version-model outputs reproduce byte-for-byte")
        return 0
    for n, b in files.items():
        (PKG / n).parent.mkdir(parents=True, exist_ok=True)
        (PKG / n).write_bytes(b)
    cov = json.loads(files["outputs/VERSION_COVERAGE_C13.json"])
    print(json.dumps({k: cov[k] for k in ("records", "by_family", "by_text_status", "army_rules_cited_rules_modelled", "army_act_cited_sections_modelled")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
