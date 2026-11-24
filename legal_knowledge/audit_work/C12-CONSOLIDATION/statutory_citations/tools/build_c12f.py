#!/usr/bin/env python3
"""C12 Workstream F: statutory-citation improvement over the 983 frozen citation items.

Derivative research output only. Reads the frozen knowledge base (never writes it), the C5 source-library
registers, the C10 quality/statutory workstreams, the C11 statute-judgment links, the Army Rules chain
registers and the held source copies (read-only, hash-verified), and writes:

  outputs/IMPROVEMENT_MATRIX.csv      prioritised matrix over all 983 citation items
  outputs/PRIORITY_VERIFICATION.csv   page-level provision/version evidence for priority items
  outputs/CROSS_VOLUME_ISSUES.csv     contradictions / missing connections across the nine families
  outputs/CORRECTION_PROPOSALS_C12.csv versioned derivative correction proposals (none applied)
  outputs/SUMMARY.json                before/after counts by evidence state
  outputs/OUTPUT_SHA256SUMS

Usage:  build_c12f.py            (rebuild outputs)
        build_c12f.py --check    (rebuild in memory and fail if any output differs or a pin fails)

Evidence rules (see README): availability is not authentication and neither is applicability.
EXACT_ANCHOR is proposed only where every cited provision is anchored to a page of a REGISTERED copy whose
C5 eligible_for_exact_anchor is YES, for the principal text and for every located amending instrument
recorded against that provision, with no reserved wording conflict and no specific unlocated instrument
naming the provision. Nothing is ever promoted from MISSING_EVIDENCE.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
REPO = Path(os.environ.get("C12F_REPO", PKG.parents[3]))
SCRATCH = Path(os.environ.get("C12F_HELD_BASE", REPO.parent))  # held_paths in the C5 copy register are relative to this
C7 = Path(os.environ.get("C12F_C7", "/home/user/c7"))
OUT = PKG / "outputs"
AW = REPO / "legal_knowledge/audit_work"
VERSION = "C12F-v1.1"  # v1.1 = remediation of review_wsf_statutory F-01..F-10 (see REMEDIATION_C12.md)

FROZEN = {
    "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl":
        "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1",
    "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl":
        "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a",
}
FROZEN_COMMIT = "21e73b83"

INPUTS = OrderedDict([
    ("kb", "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"),
    ("cases", "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"),
    ("c10_citation", "legal_knowledge/audit_work/C10-RECONCILIATION/workstreams/quality/outputs/citation_coverage_c10.csv"),
    ("c10_preservation", "legal_knowledge/audit_work/C10-RECONCILIATION/workstreams/quality/outputs/preservation_risk_c10.csv"),
    ("c10_escalation", "legal_knowledge/audit_work/C10-RECONCILIATION/workstreams/statutory/escalation_matters_c10.csv"),
    ("c5_crosswalk", "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv"),
    ("c5_copy", "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/source_copy_register.csv"),
    ("c5_master", "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/source_master_register.csv"),
    ("c5_conflict", "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/source_conflict_register.csv"),
    ("ar_chronology", "legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv"),
    ("ar_instruments", "legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv"),
    ("wsa_pcl", "legal_knowledge/audit_work/WS-A-STATUTORY/provision_change_log.csv"),
    ("c11_links", "legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/relations/outputs/STATUTE_JUDGMENT_LINKS.csv"),
    ("pilot_corrections", "legal_knowledge/audit_work/PILOT-01/registers/corrections_register.csv"),
    ("page_evidence", "legal_knowledge/audit_work/C12-CONSOLIDATION/statutory_citations/tools/page_evidence_c12.csv"),
    # v1.1 (F-01): open alleged-amendment questions and gaps; cross-reference registers
    ("wsa_open_questions", "legal_knowledge/audit_work/WS-A-STATUTORY/open_questions.csv"),
    ("wsa_open_questions_c3", "legal_knowledge/audit_work/WS-A-STATUTORY/open_questions_cycle3.csv"),
    ("wsa_gaps", "legal_knowledge/audit_work/WS-A-STATUTORY/gaps_register.csv"),
    ("wsa_mml_xcheck", "legal_knowledge/audit_work/WS-A-STATUTORY/mml_footnote_crosscheck_cycle2.csv"),
    ("wsc_open_questions", "legal_knowledge/audit_work/WS-C-MML/open_questions.csv"),
    # v1.1 (F-06): r.15 trace (r.15B applicability)
    ("wsa_r15_trace", "legal_knowledge/audit_work/WS-A-STATUTORY/r15_military_secretary_trace_cycle3.csv"),
    # v1.1: independent review verdicts, used only for the reconciliation block in SUMMARY.json (never to set a state)
    ("review_promotions", "legal_knowledge/audit_work/C12-CONSOLIDATION/reviews/review_wsf_statutory_promotions.csv"),
])

# Baseline C5 reserved-conflict rules (SOURCE-LIBRARY-C5/tools/build_registers.py amended_rules()).
C5_RESERVED_RULES = {"r23", "r182", "r193", "r194"}

# F-07: records the X002 version-dependency regex matches but which do not rely on a 1993-only r.22 element.
X002_EXCLUDE = {"HCE-027": "r.36 record: says only that r.36 cannot be used to dispense with r.22; relies on no 1993-only r.22 element (review F-07)"}

# F-01: a WS-A open question / gap row is OPEN unless its state says it is closed.
CLOSED_STATE = re.compile(r"^\s*(CLOSED|RESOLVED|ANSWERED|DETERMINED|FOUND\b|LOCATED_VERIFIED|WITHDRAWN|NOT_AN_ISSUE)", re.I)
# ... and concerns an alleged / unlocated / unverified amendment when its text speaks of an instrument or an amending act.
ALLEGED_AMENDMENT = re.compile(r"amend|insert|substitut|omit|instrument|\bhint|S\.R\.O|footnote|Explanation|attribut|source of", re.I)

# F-02: citation locators that point to an annotation or note (not printed in the Gazette or the amending instruments).
ANNOTATION_LOCATOR = re.compile(r"explanatory note|annotat|\bnotes?\b", re.I)

ARMY_RULES_SRC = "C5-SRC-P0-ARMY-RULES-1954"
GAZETTE_1954_COPY = "C5-SRC-P0-ARMY-RULES-1954~C1"
GAZETTE_1954_OFFSET = 290  # printed page = PDF page + 290 (image-checked on PDF pp.9, 10, 51 = printed 299, 300, 341)
ARMY_ACT_COMPILATION_COPY = "C5-SRC-P0-ARMY-ACT-1950-INDIACODE~C1"

FAMILIES = [("KB-", "CORE_KB"), ("HCE-", "HCE"), ("COI-", "COI"), ("CM-", "CM"), ("ADM-", "ADM"), ("PEN", "PEN"),
            ("AFT-", "AFT_V7"), ("V7-", "AFT_V7"), ("CIV-", "CIV_V8"), ("V8-", "CIV_V8"), ("EV-", "EV_V9"), ("V9-", "EV_V9")]

SUBJECTS = OrderedDict([  # subject -> (rank, legal_consequence, tier)
    ("AR22_HEARING_OF_CHARGE", (1, 5, "A")),
    ("AR23_SUMMARY_OF_EVIDENCE_RULE", (2, 5, "A")),
    ("AR180_COI_CHARACTER", (3, 5, "A")),
    ("SUMMARY_OF_EVIDENCE", (4, 5, "A")),
    ("COURT_MARTIAL_JURISDICTION_PROCEDURE", (5, 5, "B")),
    ("DISCIPLINARY_POWERS", (6, 4, "B")),
    ("LIMITATION", (7, 5, "B")),
    ("PUNISHMENTS", (8, 4, "B")),
    ("STATUTORY_COMPLAINTS", (9, 3, "B")),
    ("ADMINISTRATIVE_ACTION", (10, 4, "B")),
    ("RIGHTS_PROCEDURAL_SAFEGUARDS", (11, 4, "B")),
    ("COURT_OF_INQUIRY_OTHER", (12, 3, "C")),
    ("EVIDENCE_LAW", (13, 3, "C")),
    ("AFT_REMEDIES", (14, 3, "C")),
    ("PENSION_ENTITLEMENT", (15, 2, "C")),
    ("CIVIL_CRIMINAL_INTERFACE", (16, 2, "C")),
    ("GENERAL_OTHER", (17, 1, "C")),
])

TEXT_SUBJECT_PATTERNS = [
    ("AR22_HEARING_OF_CHARGE", r"\b(?:army\s+)?(?:rule|r\.?|ar)\s*22\b|hearing of (?:the )?charge"),
    ("AR23_SUMMARY_OF_EVIDENCE_RULE", r"\b(?:army\s+)?(?:rule|r\.?|ar)\s*23\b"),
    ("AR180_COI_CHARACTER", r"\b(?:army\s+)?(?:rule|r\.?|ar)\s*180\b"),
    ("SUMMARY_OF_EVIDENCE", r"summary of evidence|\bSoE\b|abstract of evidence"),
    ("COURT_MARTIAL_JURISDICTION_PROCEDURE", r"court[- ]martial|\b(?:GCM|DCM|SCM|SGCM)\b|convening"),
    ("DISCIPLINARY_POWERS", r"summary (?:punishment|disposal|award)|minor punishment|(?:section|s\.?|§)\s*8[0-5]\b"),
    ("LIMITATION", r"limitation|time[- ]bar|(?:section|s\.?|§)\s*122\b"),
    ("PUNISHMENTS", r"punishment|sentence|cashier"),
    ("STATUTORY_COMPLAINTS", r"statutory complaint|redress of grievance|(?:section|s\.?|§)\s*2[67]\b"),
    ("ADMINISTRATIVE_ACTION", r"administrative action|terminat|show[- ]cause|censure|\b(?:rule|r\.?)\s*1[3-7]\b|(?:section|s\.?|§)\s*(?:19|20)\b"),
    ("RIGHTS_PROCEDURAL_SAFEGUARDS", r"natural justice|cross-examin|legal advis|defending officer|caution|fair (?:trial|hearing)"),
    ("COURT_OF_INQUIRY_OTHER", r"court of inquiry|\bCoI\b"),
    ("EVIDENCE_LAW", r"evidence act|\bBSA\b|admissib|electronic record|65B"),
    ("AFT_REMEDIES", r"tribunal|\bAFT\b"),
    ("PENSION_ENTITLEMENT", r"pension|disabilit|entitlement|invalid"),
    ("CIVIL_CRIMINAL_INTERFACE", r"civil court|police|criminal court|\bBNSS\b|\bCrPC\b|\bBNS\b"),
]


# ------------------------------------------------------------------ io helpers
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_csv(rel: str):
    with open(REPO / rel, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def csv_bytes(rows, fields) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    return buf.getvalue().encode("utf-8")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def family_of(rid: str) -> str:
    for p, f in FAMILIES:
        if rid.startswith(p):
            return f
    if re.match(r"^SC\d+$", rid) or re.match(r"^J-\d+$", rid):
        return "HCE"
    return "UNKNOWN"


def rule_key(r: str):
    m = re.match(r"r(\d+)([A-Z]?)$", r)
    return (int(m.group(1)), m.group(2)) if m else (9999, r)


# ------------------------------------------------------------------ pins
def verify_frozen():
    out = {}
    for rel, pin in FROZEN.items():
        got = sha256_file(REPO / rel)
        if got != pin:
            raise SystemExit(f"FROZEN ORIGINAL CHANGED: {rel} {got} != {pin}")
        git = "NOT_CHECKED_C7_ABSENT"
        if (C7 / ".git").exists() or (C7 / "HEAD").exists():
            try:
                b = subprocess.run(["git", "-C", str(C7), "show", f"{FROZEN_COMMIT}:{rel}"], capture_output=True, check=True).stdout
                git = "MATCH" if hashlib.sha256(b).hexdigest() == pin else "MISMATCH"
            except Exception:
                git = "NOT_CHECKED_GIT_ERROR"
            if git == "MISMATCH":
                raise SystemExit(f"FROZEN ORIGINAL differs from {FROZEN_COMMIT}: {rel}")
        out[rel] = {"sha256": pin, "worktree": "MATCH", f"git_{FROZEN_COMMIT}": git}
    return out


# ------------------------------------------------------------------ held copies
class HeldCopies:
    def __init__(self, copy_rows):
        self.rows = {r["copy_id"]: r for r in copy_rows}
        self._path = {}
        self._pages = {}

    def path(self, copy_id):
        if copy_id in self._path:
            return self._path[copy_id]
        r = self.rows.get(copy_id)
        found = None
        if r:
            for hp in [x for x in r["held_paths"].split(";") if x]:
                p = SCRATCH / hp
                if p.exists() and sha256_file(p) == r["sha256"]:
                    found = p
                    break
        self._path[copy_id] = found
        return found

    def pages(self, copy_id):
        if copy_id not in self._pages:
            p = self.path(copy_id)
            if p is None:
                self._pages[copy_id] = None
            else:
                import pymupdf  # noqa: PLC0415
                with pymupdf.open(str(p)) as d:
                    self._pages[copy_id] = [pg.get_text() for pg in d]
        return self._pages[copy_id]

    def eligible(self, copy_id):
        r = self.rows.get(copy_id)
        return bool(r) and r["eligible_for_exact_anchor"] == "YES"


def heading_index(pages, body_only_dash=True):
    """Rule/section heading -> (pdf_page, char offset, heading text) via longest increasing subsequence."""
    pat = re.compile(r"(?m)^[ \t]*['\"‘“!]?[ \t]*(\d{1,3})([A-Z]?)\.[ \t]*['\"‘“!]?[ \t]*([A-Z][^—\n]{0,90}(?:\n[^—\n]{0,90}){0,2}?)—")
    cands = []
    for i, t in enumerate(pages):
        for m in pat.finditer(t):
            cands.append((int(m.group(1)), m.group(2), i + 1, m.start(), ws(m.group(3))[:70]))
    keys = [c[0] * 30 + ((ord(c[1]) - 64) if c[1] else 0) for c in cands]
    tails, tidx, prev = [], [], [-1] * len(cands)
    for i, k in enumerate(keys):
        j = bisect.bisect_left(tails, k)
        if j == len(tails):
            tails.append(k)
            tidx.append(i)
        else:
            tails[j] = k
            tidx[j] = i
        prev[i] = tidx[j - 1] if j > 0 else -1
    seq, i = [], (tidx[-1] if tidx else -1)
    while i != -1:
        seq.append(cands[i])
        i = prev[i]
    seq.reverse()
    idx = {}
    for n, suf, pg, off, txt in seq:
        idx[f"{n}{suf}"] = {"page": pg, "offset": off, "heading": txt, "method": "TEXT_LAYER_HEADING_LIS"}
    # fallback for numbers missing from the LIS: first line-start "N." between the neighbours' pages
    nums = sorted({int(k) for k in idx if k.isdigit()})
    if nums:
        for n in range(1, nums[-1] + 1):
            if str(n) in idx:
                continue
            lo = max([idx[str(x)]["page"] for x in nums if x < n] or [1])
            hi = min([idx[str(x)]["page"] for x in nums if x > n] or [len(pages)])
            for pg in range(lo, hi + 1):
                m = re.search(rf"(?m)^[ \t]*['\"‘“]?{n}\.[ \t]+['\"‘“]?([A-Z][^\n]{{0,60}})", pages[pg - 1])
                if m:
                    idx[str(n)] = {"page": pg, "offset": m.start(), "heading": ws(m.group(1))[:70], "method": "TEXT_LAYER_FALLBACK_NOT_LIS"}
                    break
    return idx


HEADER_LINE = re.compile(r"GAZ|SEC|S[eEu][cC]\.|\[P|P[A-Za-z]{2,3}T\s")


def text_layer_end_page(pages, idx, n):
    """F-05: last PDF page of rule n from the text layer: the page of the next heading if body text precedes that heading
    on its page (the rule continues there), else the page before it. Running heads and short cross-heads are ignored."""
    st = idx[n]
    after = sorted((v["page"], v["offset"]) for v in idx.values() if (v["page"], v["offset"]) > (st["page"], st["offset"]))
    if not after:
        return st["page"]
    pg, off = after[0]
    if pg == st["page"]:
        return pg
    lines = pages[pg - 1][:off].splitlines()
    while lines and (len(lines[0].strip()) < 12 or HEADER_LINE.search(lines[0])):
        lines.pop(0)
    body = sum(len(ln.strip()) for ln in lines if len(ln.strip()) >= 45 or re.search(r"[.;,:]\s*$", ln))
    return pg if body >= 40 else max(st["page"], pg - 1)


def page_span(start, end, offset=0):
    return f"{start + offset}" if end == start else f"{start + offset}-{end + offset}"


def excerpt_at(pages, page, offset, n=260):
    t = pages[page - 1][offset:] + ("\n" + pages[page] if page < len(pages) else "")
    return ws(t)[:n]


# ------------------------------------------------------------------ rule parsing
def parse_rules(text: str):
    """All Army Rules numbers named in a register cell (comma lists and ranges after r./rr./rule)."""
    out = []
    for seg in re.split(r";", text or ""):
        seg2, prev_seg = seg, None
        while seg2 != prev_seg:  # strip parentheticals (innermost first) unless they name a rule
            prev_seg = seg2
            seg2 = re.sub(r"\([^()]*\)", lambda m: m.group(0).replace("(", "\x00").replace(")", "\x01") if re.search(r"\br\.\s*\d", m.group(0)) else " ", seg2)
        seg2 = seg2.replace("\x00", " ").replace("\x01", " ")
        m = re.search(r"\b(?:rr?\.|rules?\s+)\s*(?=\d)", seg2, re.I)
        if not m:
            continue
        tail = seg2[m.start():]
        for a, b in re.findall(r"(?<![\w.])(?:rr?\.|rules?\s+)?\s*(\d{1,3}[A-Z]?)(?:\s*-\s*(\d{1,3}))?(?![\d/])", tail):
            if b and a.isdigit():
                out += [f"r{x}" for x in range(int(a), int(b) + 1)]
            else:
                out.append(f"r{a}")
        # drop tokens preceded by Section/Pt/App/No./s.
        bad = set(re.findall(r"(?:Section|Pt|App\.?|No\.|s\.|Form|para|item|cl\.)\s*(\d{1,3}[A-Z]?)", tail, re.I))
        out = [x for x in out if x[1:] not in bad]
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


def named_rules(text: str):
    """Army Rules named in free text the WS-A way ('r.15', 'rr.193/194', 'r.23, r.193 or r.194', 'r.187(1)(r)').

    Stricter than parse_rules: every number must follow 'r.'/'rr.' or continue a list that started with one, so
    instrument numbers ('17(E)/1993') and other instruments' 'Rule 4-12' are never read as Army Rules."""
    out = []
    for m in re.finditer(r"\brr?\.\s*(\d{1,3}[A-Z]?)((?:\s*(?:/|,|\bor\b|\band\b)\s*(?:rr?\.\s*)?\d{1,3}[A-Z]?(?![\d(/]|\s*\(E\)))*)", text or ""):
        out.append("r" + m.group(1))
        out += ["r" + x for x in re.findall(r"(\d{1,3}[A-Z]?)", m.group(2))]
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


def open_alleged_amendments(oq_rows, gap_rows, wsc_rows, xc_rows):
    """F-01: rule -> OPEN WS-A open-question / gap rows about an alleged, unlocated or unverified amendment naming it.

    Only WS-A registers create a blocker; WS-C open questions and the WS-A MML footnote cross-check rows that name the
    same rule (or cite the WS-A id) are attached as cross-references."""
    trig = defaultdict(list)
    for r in oq_rows + gap_rows:
        rid = r.get("question_id") or r.get("gap_id")
        state = r.get("state", "")
        if CLOSED_STATE.search(state):
            continue
        head = r.get("question") or r.get("subject") or ""
        text = " ".join([head, r.get("context_and_evidence", ""), r.get("evidence", "")])
        if not ALLEGED_AMENDMENT.search(text):
            continue
        for rule in named_rules(head + " ; " + (r.get("affects") or r.get("affected_ids") or "")):
            trig[rule].append({"id": rid, "state": state, "text": ws(head)[:160]})
    out = {}
    for rule, rows in trig.items():
        ids = {x["id"] for x in rows}
        xref = []
        for x in xc_rows:
            if x.get("result", "").startswith("AGREES"):
                continue
            if rule in named_rules(x.get("provision", "")) or any(i in (x.get("detail", "") + x.get("gazette_evidence", "")) for i in ids):
                xref.append(f"{x['xcheck_id']} {x['result'].split(' ')[0]}")
        for q in wsc_rows:
            if CLOSED_STATE.search(q.get("status", "")):
                continue
            if rule in named_rules(q.get("question", "")) or any(i in q.get("blocks", "") for i in ids):
                xref.append(f"WS-C {q['oq_id']}")
        out[rule] = {"ids": sorted(ids), "rows": rows, "xref": sorted(set(xref))}
    return out


def c5_amended_rules(pcl, chron, instr):
    """Exact replica of the C5 baseline amended_rules() (first number after r./rr. only)."""
    out = set(C5_RESERVED_RULES)
    texts = [r["provision"] for r in pcl if not r["instrument_ref"].startswith("AA")]
    texts += [r["provision"] for r in chron if r["event"].lower() not in ("enacted", "enacts", "principal")]
    texts += [r["provisions_affected"] for r in instr if r["instr_id"] != "AR-000"]
    for t in texts:
        for n in re.findall(r"\br{1,2}\.?\s*(\d+[A-Z]?)", t):
            out.add("r" + n)
    return out


# ------------------------------------------------------------------ main build
def build():
    pins = verify_frozen()
    input_hashes = OrderedDict((k, sha256_file(REPO / v)) for k, v in INPUTS.items())

    kb = {}
    with open(REPO / INPUTS["kb"], encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            kb[r["id"]] = r
    c10 = read_csv(INPUTS["c10_citation"])
    items = [r for r in c10 if r["item_kind"] == "CITATION_ITEM"]
    copies_rows = read_csv(INPUTS["c5_copy"])
    held = HeldCopies(copies_rows)
    conflicts = read_csv(INPUTS["c5_conflict"])
    chron = read_csv(INPUTS["ar_chronology"])
    instr = read_csv(INPUTS["ar_instruments"])
    pcl = read_csv(INPUTS["wsa_pcl"])
    links = read_csv(INPUTS["c11_links"])
    pres = read_csv(INPUTS["c10_preservation"])
    pe_rows = read_csv(INPUTS["page_evidence"])
    pilot = read_csv(INPUTS["pilot_corrections"])
    esc = read_csv(INPUTS["c10_escalation"])
    open_alleged = open_alleged_amendments(read_csv(INPUTS["wsa_open_questions"]) + read_csv(INPUTS["wsa_open_questions_c3"]),
                                           read_csv(INPUTS["wsa_gaps"]), read_csv(INPUTS["wsc_open_questions"]),
                                           read_csv(INPUTS["wsa_mml_xcheck"]))
    r15_trace = read_csv(INPUTS["wsa_r15_trace"])
    review_rows = read_csv(INPUTS["review_promotions"])

    base_counts = Counter(r["C_resolution_c10"] for r in items)
    if len(items) != 983 or base_counts != Counter({"PARTIAL_MATCH": 652, "MISSING_EVIDENCE": 289, "EXACT_ANCHOR": 42}):
        raise SystemExit(f"baseline mismatch: {len(items)} {dict(base_counts)}")

    # ---- curated page evidence: validate every probe against the held copy's text layer
    pe_status = {}
    pe_by_rule = defaultdict(list)  # (rule, instrument) -> evidence rows
    for e in pe_rows:
        p = held.path(e["copy_id"])
        pages = held.pages(e["copy_id"])
        ok = p is not None and held.rows[e["copy_id"]]["sha256"] == e["sha256"]
        miss = []
        if ok:
            t = norm(pages[int(e["pdf_page"]) - 1])
            for probe in e["probe"].split(" || "):
                if norm(probe) not in t:
                    miss.append(probe)
        if ok and e.get("continues_rule"):
            if e["continues_rule"] not in e["provisions"].split(";") or int(e["continues_to_pdf_page"]) <= int(e["pdf_page"]):
                miss.append("continuation fields inconsistent")
            elif norm(e["continuation_probe"]) not in norm(pages[int(e["continues_to_pdf_page"]) - 1]):
                miss.append("continuation:" + e["continuation_probe"])
        status = "VERIFIED" if ok and not miss else ("COPY_NOT_HELD_OR_HASH_MISMATCH" if not ok else "PROBE_NOT_FOUND:" + "|".join(miss))
        pe_status[e["evidence_id"]] = status
        if status != "VERIFIED":
            raise SystemExit(f"page evidence {e['evidence_id']} failed: {status}")
        for r in e["provisions"].split(";"):
            pe_by_rule[(r, e["instrument_id"])].append(e)

    # ---- 1954 Gazette heading index (text layer of the registered, hash-verified copy)
    g_pages = held.pages(GAZETTE_1954_COPY)
    if g_pages is None:
        raise SystemExit("1954 Gazette copy c5ef95a9 not held at any registered path")
    g_idx = heading_index(g_pages)
    # printed-page offset check against image-checked pages
    for e in pe_rows:
        if e["copy_id"] == GAZETTE_1954_COPY and int(e["printed_page"]) != int(e["pdf_page"]) + GAZETTE_1954_OFFSET:
            raise SystemExit("1954 printed-page offset inconsistent")
    for e in pe_rows:  # image-checked headings must agree with the index
        if e["copy_id"] == GAZETTE_1954_COPY:
            for r in e["provisions"].split(";"):
                if g_idx.get(r[1:], {}).get("page") != int(e["pdf_page"]):
                    raise SystemExit(f"index/image disagreement for {r}: {g_idx.get(r[1:])} vs {e['pdf_page']}")

    # F-05: page ranges. Text-layer end page for every indexed rule; an image-checked row must agree with it.
    g_end = {n: text_layer_end_page(g_pages, g_idx, n) for n in g_idx}
    for e in pe_rows:
        if e["copy_id"] == GAZETTE_1954_COPY:
            for r in e["provisions"].split(";"):
                img_end = int(e["continues_to_pdf_page"]) if e.get("continues_rule") == r else int(e["pdf_page"])
                if g_end.get(r[1:]) != img_end:
                    raise SystemExit(f"page-range disagreement for {r}: text layer ends p.{g_end.get(r[1:])}, image check ends p.{img_end}")

    def evidence_end(e, rule):
        return int(e["continues_to_pdf_page"]) if e.get("continues_rule") == rule else int(e["pdf_page"])

    # ---- Army Rules amendment events per rule
    eligible_instr = {}
    for c in copies_rows:
        m = re.match(r"C5-SRC-P0-AR-AMD-(AR-\d{3})~", c["copy_id"])
        if m and c["eligible_for_exact_anchor"] == "YES":
            eligible_instr[m.group(1)] = c["copy_id"]
    instr_by_id = {r["instr_id"]: r for r in instr}
    events = defaultdict(list)  # rule -> [(instr_id, origin, text)]
    for r in pcl:
        if r["instrument_ref"].startswith("AA") or r["instrument_ref"] in ("AR-000",):
            continue
        if "enacted" in r["change_type"].lower() or "no amendment" in r["change_type"].lower():
            continue
        for rr in parse_rules(r["provision"]):
            events[rr].append((r["instrument_ref"] or "UNIDENTIFIED", f"WS-A provision_change_log#{r['change_id']}", r["change_type"]))
    for r in chron:
        if "NO AMENDMENT" in r["event"] or not r["instrument_id"]:
            continue
        for rr in parse_rules(r["provision"]):
            events[rr].append((r["instrument_id"], f"ARMY-RULES-CHAIN-01 chronology ({r['instrument']})", r["event"]))
    for r in instr:
        if r["instr_id"] in ("AR-000", "AR-029"):  # AR-029 is itemised rule-by-rule in WS-A PCL-93-*
            continue
        for rr in parse_rules(r["provisions_affected"]):
            events[rr].append((r["instr_id"], f"ARMY-RULES-CHAIN-01 instrument register ({r['status']})", r["provisions_affected"][:80]))

    reserved = defaultdict(list)
    for r in C5_RESERVED_RULES:
        reserved[r].append("C5 baseline reserved conflict")
    for c in conflicts:
        st = (c.get("status") or "") + " " + (c.get("reserved_status") or "")
        if not re.search(r"CONFLICTING|OPEN", st):
            continue
        ap = c.get("affected_provision") or ""
        if "Army Rule" not in ap and "Army Rules" not in ap:
            continue
        for n in re.findall(r"\br\.?\s*(\d+[A-Z]?)|\bRule\s+(\d+[A-Z]?)", ap):
            rr = "r" + (n[0] or n[1])
            reserved[rr].append(f"{c['conflict_id']} ({ws(c.get('status'))[:40]})")

    c5_amended = c5_amended_rules(pcl, chron, instr)

    # F-06: applicability (not wording) limitation from r.15B (S.R.O. 17(E)/2019, AR-034), per the WS-A r.15 trace
    applicability = {}
    for t in r15_trace:
        if "15B" in t.get("touches_r15", ""):
            m = re.search(r"disapplies\s+(rr?\.[^,]*?(?:,\s*\d{1,3}[A-Z]?)*)\s+to", t["touches_r15"])
            dis = named_rules(m.group(1)) if m else []
            cps = [c for c in copies_rows if c["copy_id"].startswith("C5-SRC-P0-AR-AMD-AR-034~")]
            elig = ";".join(f"{c['copy_id']} eligible_for_exact_anchor={c['eligible_for_exact_anchor']}" for c in cps) or "no registered copy"
            for rr in dis:
                applicability[rr] = (f"APPLICABILITY NOTE (F-06; not a wording or evidence-state change): S.R.O. 17(E)/2019 (AR-034) inserted r.15B, which disapplies "
                                     f"{', '.join(x.replace('r', 'r.') for x in dis)} in relation to the office of the Chief of Defence Staff "
                                     f"(WS-A r15_military_secretary_trace_cycle3 item {t['item']}; {t['evidence_level']}). Registered copy: {elig}, so r.15B is not "
                                     "anchored here. The citation's scope after 28-12-2019 is NOT claimed.")

    def rule_unit(rule):
        """Version/page evidence for one Army Rule as cited (current text on located instruments)."""
        u = {"provision": rule, "pages": [], "blockers": [], "events": []}
        n = rule[1:]
        hi = g_idx.get(n)
        if hi:
            pdfp = hi["page"]
            img = [e for e in pe_by_rule.get((rule, "AR-000"), []) if "IMAGE" in e["check_type"]]
            endp = evidence_end(img[0], rule) if img else g_end[n]
            u["principal"] = {"copy": GAZETTE_1954_COPY, "pdf_page": pdfp, "printed_page": pdfp + GAZETTE_1954_OFFSET,
                              "pdf_end": endp, "pdf_span": page_span(pdfp, endp), "printed_span": page_span(pdfp, endp, GAZETTE_1954_OFFSET),
                              "span_method": ("IMAGE_CHECKED" if img else "TEXT_LAYER_NEXT_HEADING"),
                              "method": (img[0]["check_type"] + " " + img[0]["evidence_id"] + " (" + (img[0].get("checker") or "C12 WS-F") + ")") if img
                              else hi["method"] + " (text layer only; no per-page C12 image check of this 1954 page; ARMY-RULES-CHAIN-01 AR-000 register-level ALL_IMAGE_CHECKED assertion)",
                              "excerpt": (img[0]["observed_on_image"] if img else excerpt_at(g_pages, pdfp, hi["offset"])),
                              "excerpt_source": "IMAGE_READ_C12" if img else "TEXT_LAYER_OCR_UNCORRECTED",
                              "fallback": hi["method"] == "TEXT_LAYER_FALLBACK_NOT_LIS"}
            if hi["method"] == "TEXT_LAYER_FALLBACK_NOT_LIS" and not img:
                u["blockers"].append("1954 page located only by fallback line match (heading order not confirmed)")
        else:
            u["principal"] = None
            u["blockers"].append("1954 page not located in the text layer")
        evs = events.get(rule, [])
        seen_instr = OrderedDict()
        for iid, origin, txt in evs:
            seen_instr.setdefault(iid, []).append((origin, txt))
        for iid, rows in sorted(seen_instr.items(), key=lambda kv: (instr_by_id.get(kv[0], {}).get("instrument_date", "9999"), kv[0])):
            ir = instr_by_id.get(iid, {})
            label = ir.get("instrument", iid) + (f" of {ir['instrument_date'][:4]}" if re.match(r"\d{4}", ir.get("instrument_date", "")) else "")
            ev = {"instrument": iid, "instrument_label": label, "origins": [o for o, _ in rows],
                  "change": rows[0][1], "status": ir.get("status", "UNKNOWN"),
                  "commencement": ir.get("effective_date_status", "") or "NOT_RECORDED",
                  "effective_date": ir.get("effective_date", ""), "publication_date": ir.get("publication_date", "")}
            if iid in eligible_instr:
                pes = pe_by_rule.get((rule, iid), [])
                pclp = [r for r in pcl if r["instrument_ref"] == iid and rule in parse_rules(r["provision"]) and re.search(r"p\.\s*\d", r["page_anchor"])]
                if pes:
                    e = pes[0]
                    # F-05: span over every evidence row for this rule in this instrument (e.g. 1993 item 7, r.26, pp.14-15)
                    ps = min(int(x["pdf_page"]) for x in pes)
                    ee = max(evidence_end(x, rule) for x in pes)
                    off = int(e["printed_page"]) - int(e["pdf_page"])
                    ev.update({"copy": eligible_instr[iid], "pdf_page": page_span(ps, ee), "printed_page": page_span(ps, ee, off),
                               "evidence_ids": ";".join(x["evidence_id"] for x in pes),
                               "method": "; ".join(f"{x['check_type']} {x['evidence_id']}" for x in pes) + " (text-layer probe verified)",
                               "excerpt": e["observed_on_image"], "pcl": ";".join(r["change_id"] for r in pclp)})
                else:
                    ev["blocker"] = f"{iid}: no C12 page evidence for {rule}"
            elif ir.get("status") in ("GAP", "TO_CHECK"):
                ev["blocker"] = f"{iid} ({ir.get('instrument')}) {ir.get('status')}: alleged/unopened instrument naming {rule}"
            elif ir.get("status") == "LOCATED_UNVERIFIED":
                ev["blocker"] = f"{iid} ({ir.get('instrument')}) located from text layer only; copy not registered as eligible"
            elif ir.get("status") == "LOCATED_NOT_AMENDMENT":
                ev["note"] = "declaration, not an amendment"
            else:
                ev["blocker"] = f"{iid} ({ir.get('instrument', iid)}): amending copy not registered as eligible_for_exact_anchor"
            if "blocker" in ev:
                u["blockers"].append(ev["blocker"])
            u["events"].append(ev)
        for ev in u["events"]:
            ch = ev["change"].strip().lower()
            if ch in ("omitted", "heading and rules omitted") or ch.startswith("omitted w.e.f"):
                u["blockers"].append(f"whole rule omitted by {ev['instrument_label']} ({ev['instrument']}): a live citation is not supportable")
                u["omitted"] = True
        if rule in open_alleged:  # F-01
            oa = open_alleged[rule]
            u["open_alleged"] = oa
            u["blockers"].append("OPEN alleged/unlocated amendment naming the rule in the WS-A registers: " + "; ".join(oa["ids"]) +
                                 (" (cross-refs: " + "; ".join(oa["xref"]) + ")" if oa["xref"] else "") + " - " + oa["rows"][0]["text"][:120])
        if rule in reserved:
            u["blockers"].append("reserved wording conflict: " + "; ".join(sorted(set(reserved[rule]))))
        u["reserved"] = sorted(set(reserved.get(rule, [])))
        u["c5_flagged"] = rule in c5_amended
        u["established"] = not u["blockers"]
        return u

    unit_cache = {}

    def unit(rule):
        if rule not in unit_cache:
            unit_cache[rule] = rule_unit(rule)
        return unit_cache[rule]

    # ---- Army Act compilation section index (government compilation; NOT eligible for EXACT)
    aa_pages = held.pages(ARMY_ACT_COMPILATION_COPY)
    aa_idx = heading_index(aa_pages) if aa_pages else {}

    # ---- judgment paragraph anchors for eligible held copies
    jud_copy = {}
    for c in copies_rows:
        if c["source_id"].startswith("C5-SRC-J-") and c["eligible_for_exact_anchor"] == "YES":
            jud_copy.setdefault(c["source_id"], c["copy_id"])

    para_cache = {}

    def para_map(copy_id):
        if copy_id in para_cache:
            return para_cache[copy_id]
        pages = held.pages(copy_id)
        res = None
        if pages:
            starts = []
            for i, t in enumerate(pages):
                for m in re.finditer(r"(?m)^\s*(\d{1,3})\.\s+(\S[^\n]{0,60})", t):
                    starts.append((int(m.group(1)), i + 1, ws(m.group(2))[:40]))
            # split into renditions at a restart to para 1 after para >= 3
            rends, cur, last = [], [], 0
            for n, pg, tx in starts:
                if n == 1 and last >= 3:
                    rends.append(cur)
                    cur, last = [], 0
                if n == last + 1:
                    cur.append((n, pg, tx))
                    last = n
            rends.append(cur)
            rends = [r for r in rends if r]
            if rends:
                r1 = {n: (pg, tx) for n, pg, tx in rends[0]}
                ambiguous = set()
                for other in rends[1:]:
                    o = {n: (pg, tx) for n, pg, tx in other}
                    for n in set(r1) | set(o):
                        if n not in r1 or n not in o or norm(r1[n][1])[:25] != norm(o[n][1])[:25]:
                            ambiguous.add(n)
                res = {"paras": r1, "renditions": len(rends), "ambiguous": ambiguous,
                       "max": max(r1) if r1 else 0, "rendition_pages": [r[0][1] for r in rends]}
        para_cache[copy_id] = res
        return res

    def kb_para_locator(rec, code):
        refs = str(rec.get("references", ""))
        out = []
        for m in re.finditer(re.escape(code) + r"[\s:|'\"]*(?:'[^']*'\s*:\s*')?([^\]\};|]{0,80})", refs):
            seg = m.group(1)
            pm = re.search(r"paras?\.?\s*([\d\s,–\-and]+)", seg)
            if pm:
                for a, b in re.findall(r"(\d+)\s*(?:[–-]\s*(\d+))?", pm.group(1)):
                    out += list(range(int(a), int(b) + 1)) if b else [int(a)]
        return sorted(set(out))

    # ---- per-item evaluation
    links_by_prov = defaultdict(set)
    for l in links:
        m = re.match(r"AR-1954:r\.(\d+[A-Z]?)$", l["provision_id"] or "")
        if m:
            links_by_prov["r" + m.group(1)].add(l["judgment_id"])
        m = re.match(r"AA-1950:s\.(\d+[A-Z]?)$", l["provision_id"] or "")
        if m:
            links_by_prov["s" + m.group(1)].add(l["judgment_id"])

    pres_by_sha = {}
    for p in pres:
        for k in ("sha256", "copy_sha256", "file_sha256"):
            if p.get(k):
                pres_by_sha[p[k]] = p

    matrix, verif, proposals = [], [], []
    vcount = 0

    def add_verif(row):
        nonlocal vcount
        vcount += 1
        row["verification_id"] = f"C12F-V{vcount:04d}"
        verif.append(row)
        return row["verification_id"]

    for it in items:
        rid = it["knowledge_base_record_id"]
        rec = kb[rid]
        text = " ".join([rec.get("title", ""), rec.get("body", ""), str(rec.get("references", ""))])
        prov = it["provision_id"]
        src = it["source_id"]
        basis = it["C_crosswalk_basis"]
        base = it["C_resolution_c10"]
        units = []
        loc = prov.split("#", 1)[1].split(",") if "#" in prov else []
        loc = list(OrderedDict.fromkeys(loc))
        code_m = re.search(r"WS-D (?:code|statute|case):([^\[]+)\[(\w[\w-]*)\]", basis)
        ident = code_m.group(2) if code_m else ""
        code = code_m.group(1).strip() if code_m else ""

        # subject
        tags = []
        if src == ARMY_RULES_SRC and loc:
            for r in loc:
                n = rule_key(r)[0]
                tags.append({22: "AR22_HEARING_OF_CHARGE", 23: "AR23_SUMMARY_OF_EVIDENCE_RULE", 180: "AR180_COI_CHARACTER",
                             24: "SUMMARY_OF_EVIDENCE", 25: "SUMMARY_OF_EVIDENCE"}.get(n) or (
                    "ADMINISTRATIVE_ACTION" if 13 <= n <= 18 else "RIGHTS_PROCEDURAL_SAFEGUARDS" if 19 <= n <= 21 else
                    "DISCIPLINARY_POWERS" if n in (26, 27, 186) else "COURT_MARTIAL_JURISDICTION_PROCEDURE" if 28 <= n <= 176 else
                    "COURT_OF_INQUIRY_OTHER" if 177 <= n <= 185 else "GENERAL_OTHER"))
        elif prov.startswith("act-army-1950#"):
            for s in loc:
                m = re.match(r"s(\d+)", s)
                if not m:
                    continue
                n = int(m.group(1))
                tags.append("LIMITATION" if n in (122, 123) else "STATUTORY_COMPLAINTS" if n in (26, 27) else
                            "ADMINISTRATIVE_ACTION" if 18 <= n <= 25 else "PUNISHMENTS" if (71 <= n <= 78 or 168 <= n <= 178) else
                            "DISCIPLINARY_POWERS" if 79 <= n <= 91 else "RIGHTS_PROCEDURAL_SAFEGUARDS" if 101 <= n <= 107 else
                            "COURT_MARTIAL_JURISDICTION_PROCEDURE" if (2 <= n <= 6 or 34 <= n <= 70 or 108 <= n <= 167) else "GENERAL_OTHER")
        elif prov.startswith("act-armed-forces-tribunal-2007#"):
            tags += ["LIMITATION" if s in ("s22", "s21") else "AFT_REMEDIES" for s in loc]
        elif prov.startswith(("act-bsa", "act-bnss", "act-bns")):
            tags.append("EVIDENCE_LAW" if "bsa" in prov else "CIVIL_CRIMINAL_INTERFACE")
        if not tags:
            for subj, pat in TEXT_SUBJECT_PATTERNS:
                if re.search(pat, text, re.I):
                    tags.append(subj)
                    break
        if not tags:
            tags = ["GENERAL_OTHER"]
        tags = sorted(set(tags), key=lambda s: SUBJECTS[s][0])
        subject = tags[0]
        rank, consequence, tier = SUBJECTS[subject]
        p0 = "(P0)" in (it["D_pilot01_open_p0_p2"] + it["D_wsb_adverse_open"])
        if p0:
            consequence = 5

        # gap & availability (baseline)
        if base == "EXACT_ANCHOR":
            gap, gap_reason = 1, "EXACT_ANCHOR in baseline but no page anchor recorded"
        elif base == "MISSING_EVIDENCE":
            gap = 4
            gap_reason = ("source not identified" if src == "UNMAPPED" else "source identified but not held")
        elif "recorded amendment or reserved conflict" in basis:
            gap, gap_reason = 2, "as-notified text held; amendment chain / reserved conflict unresolved"
        elif "held copy is HELD_GOVERNMENT_COMPILATION" in basis:
            gap, gap_reason = 2, "only a government compilation (provenance undocumented) is held"
        elif "inferred identity" in basis:
            gap, gap_reason = 3, "identity inferred, not established"
        elif "no provision locator" in basis:
            gap, gap_reason = 3, "no provision/paragraph locator"
        else:
            gap, gap_reason = 3, basis.split(";")[-1].strip()[:80]
        regs = [x.split(":")[0] for x in it["A_registered_copies"].split("; ") if x]
        if any(held.eligible(c) for c in regs):
            avail = 4
        elif it["A_availability_c10"] == "HELD_HF_AND_GITHUB":
            avail = 3
        elif it["A_availability_c10"] in ("HELD_WORKING_STORE_ONLY_EPHEMERAL", "HELD_HF_ONLY_HF_BYTES_NOT_CHECKED",
                                          "NOT_REGISTERED_UNREGISTERED_COPY_IN_CANONICAL_STORE"):
            avail = 2
        else:
            avail = 1
        score = consequence * gap * avail

        # ---- C12 verification
        vids, blockers = [], []
        new_state, change = base, "NONE"
        if src == ARMY_RULES_SRC and loc:
            if ident != "id":
                blockers.append(f"source identity '{ident}' in the C5 crosswalk (rule number inferred from text, not an identified citation)")
            ann = [sg for sg in re.findall(r"(?:SRC-AR|Army Rules?)[^\]\}]*", str(rec.get("references", ""))) if ANNOTATION_LOCATOR.search(sg)]
            if ann:  # F-02
                blockers.append(f"citation locator is an annotation/note ('{ws(ann[0])[:80]}'): no such note is printed in the 1954 Gazette or the amending "
                                "instruments, so the locator cannot carry an exact anchor (review F-02)")
            bad_tokens = [r for r in loc if not re.match(r"r\d{1,3}[A-Z]?$", r) or rule_key(r)[0] > 205]
            for r in loc:
                if r in bad_tokens:
                    vids.append(add_verif({"item_id": it["item_id"], "kb_record_id": rid, "provision": r, "status": "NOT_ESTABLISHED",
                                           "note": "locator token is not a valid Army Rules 1954 rule number (crosswalk parsing artefact)"}))
                    blockers.append(f"{r}: invalid locator token")
                    continue
                u = unit(r)
                pr = u["principal"]
                ev_txt = []
                for ev in u["events"]:
                    s = f"{ev['instrument']} {ev['instrument_label']}: {ev['change']}"
                    if ev.get("pdf_page"):
                        s += f" [registered eligible copy {ev['copy']}, PDF p.{ev['pdf_page']} / printed p.{ev['printed_page']}; {ev['method']}]"
                    if ev.get("blocker"):
                        s += f" [BLOCKER: {ev['blocker']}]"
                    ev_txt.append(s)
                comm = ["1954 principal: no commencement clause (AQ-05; NOT_ESTABLISHED)"] + [
                    f"{ev['instrument']}: {ev['commencement']}" + (f" (effective {ev['effective_date']})" if ev.get("effective_date") else "")
                    for ev in u["events"]]
                located = [ev for ev in u["events"] if ev.get("pdf_page")]
                if u["established"]:
                    status = "ESTABLISHED_EXACT_VERSION_ANCHOR"
                elif u.get("omitted"):
                    status = "PROVISION_OMITTED_PAGES_ANCHORED"
                elif u["reserved"]:
                    status = "CONFLICTING_RESERVED_NOT_RESOLVED"
                elif any(("GAP" in b or "TO_CHECK" in b) and "OPEN alleged" not in b for b in u["blockers"]):
                    status = "PAGES_ANCHORED_SPECIFIC_UNLOCATED_INSTRUMENT" if pr and not any("no C12 page" in b for b in u["blockers"]) else "NOT_ESTABLISHED"
                elif u.get("open_alleged") and pr and not any("no C12 page" in b or "not located" in b for b in u["blockers"] if "OPEN alleged" not in b):
                    status = "PAGES_ANCHORED_OPEN_ALLEGED_AMENDMENT_UNLOCATED"
                elif pr:
                    status = "PRINCIPAL_PAGE_ONLY_AMENDMENT_NOT_ANCHORABLE"
                else:
                    status = "NOT_ESTABLISHED"
                last = located[-1] if located else None
                version = "Army Rules 1954, S.R.O. 484, Gazette of India Pt II s.4 No.47, 27-11-1954, pp.291-378 (as notified)"
                if located:
                    version += " as amended by " + "; ".join(f"{ev['instrument_label']} ({ev['instrument']})" for ev in located)
                supers = ("1954 as-notified text -> " + " -> ".join(f"{ev['instrument_label']} ({ev['change']})" for ev in located)) if located else "no amendment located on the 31+ examined instruments"
                temporal = ("current wording on located instruments only: chain gaps AR-001 (E-7/1960 not found), AR-030 (S.R.O. 258/2002 not found), "
                            "AR-036 (after 06-06-2022 not searched), unopened hints AR-012/013/015/037-046; currency NOT_ESTABLISHED")
                if located:
                    temporal = f"text from {located[-1]['instrument_label']} ({located[-1].get('effective_date') or 'commencement not stated'}) onward; " + temporal
                else:
                    temporal = "1954 as-notified text (commencement not stated in r.1) onward; " + temporal
                vids.append(add_verif({
                    "item_id": it["item_id"], "kb_record_id": rid, "provision": f"Army Rules 1954 {r.replace('r', 'r.')}",
                    "source_copy_id": GAZETTE_1954_COPY + ((" + " + " + ".join(ev["copy"] for ev in located)) if located else ""),
                    "copy_sha256": held.rows[GAZETTE_1954_COPY]["sha256"] + ((";" + ";".join(held.rows[ev["copy"]]["sha256"] for ev in located)) if located else ""),
                    "edition_or_version": version,
                    "pdf_page": (pr["pdf_span"] if pr else "") + "".join(f"; {ev['instrument']}:{ev['pdf_page']}" for ev in located),
                    "printed_page": (pr["printed_span"] if pr else "") + "".join(f"; {ev['instrument']}:{ev['printed_page']}" for ev in located),
                    "page_evidence_method": (pr["method"] + f"; 1954 page span {pr['span_method']}" if pr else "NOT_LOCATED") + "".join(f"; {ev['instrument']}: {ev['method']}" for ev in located),
                    "excerpt": (pr["excerpt"] if pr else "") + ("".join(f" || {ev['instrument']}: {ev['excerpt']}" for ev in located)),
                    "excerpt_source": (pr["excerpt_source"] if pr else "") + ("; amendment excerpts IMAGE_READ_C12 or prior PIC" if located else ""),
                    "amendment_evidence": " | ".join(ev_txt) or "none recorded (31+ instruments examined; chain incomplete)",
                    "commencement_evidence": " | ".join(comm),
                    "supersession": supers,
                    "temporal_applicability": temporal,
                    "reserved_conflict": "; ".join(u["reserved"]),
                    "blockers": " | ".join(u["blockers"]),
                    "judgment_links_c11": str(len(links_by_prov.get(r, ()))),
                    "status": status,
                    "applicability_note": applicability.get(r, ""),
                }))
                if not u["established"]:
                    blockers += [f"{r}: {b}" for b in u["blockers"]]
            all_ok = not blockers
            if base == "PARTIAL_MATCH" and all_ok:
                new_state, change = "EXACT_ANCHOR", "PROMOTE_PARTIAL_TO_EXACT_PROPOSED"
            elif base == "EXACT_ANCHOR" and all_ok:
                change = "EXACT_RETAINED_PAGE_ANCHOR_ADDED"
                if any(unit(r)["events"] for r in loc) and not all(unit(r)["c5_flagged"] for r in loc if unit(r)["events"]):
                    change = "EXACT_RETAINED_BASIS_CORRECTED_AMENDMENT_ANCHORED"
            elif base == "EXACT_ANCHOR" and not all_ok:
                if any(("amending copy" in b or "GAP" in b or "TO_CHECK" in b or "reserved" in b or "LOCATED_UNVERIFIED" in b or "text layer only" in b
                        or "OPEN alleged" in b or "annotation/note" in b) for b in blockers):
                    new_state, change = "PARTIAL_MATCH", "DEMOTE_EXACT_TO_PARTIAL_PROPOSED"
                else:
                    change = "EXACT_RETAINED_PAGE_ANCHOR_NOT_ESTABLISHED_FLAG"
            elif base == "PARTIAL_MATCH":
                change = "PARTIAL_RETAINED_PAGE_EVIDENCE_ADDED"
        elif src in jud_copy and base != "MISSING_EVIDENCE":
            cid = jud_copy[src]
            paras = kb_para_locator(rec, code) if code else []
            pm = para_map(cid)
            if held.path(cid) is None:
                status, blockers = "NOT_ESTABLISHED", ["registered copy bytes not available at any held path"]
            elif not paras:
                status, blockers = "NOT_ESTABLISHED", ["no paragraph locator for this source in the record references"]
            elif pm is None or not pm["paras"]:
                status, blockers = "NOT_ESTABLISHED", ["paragraph numbering not detectable in the text layer"]
            else:
                missing = [p for p in paras if p not in pm["paras"]]
                amb = [p for p in paras if p in pm["ambiguous"]]
                blockers = ([f"paras {missing} not found"] if missing else []) + (
                    [f"paras {amb} differ between the {pm['renditions']} renditions in the held file"] if amb else [])
                if ident != "id":
                    blockers.append(f"source identity '{ident}' (not 'id') in the C5 crosswalk")
                status = "ESTABLISHED_PARA_PAGE_ANCHOR" if not blockers else ("PARA_VERSION_AMBIGUOUS" if amb and not missing else "NOT_ESTABLISHED")
            pages_s = ""
            exc = ""
            if pm and paras:
                pages_s = "; ".join(f"para {p}: p.{pm['paras'][p][0]}" for p in paras if p in pm["paras"])
                exc = " || ".join(f"para {p}: {pm['paras'][p][1]}" for p in paras if p in pm["paras"])
            vids.append(add_verif({
                "item_id": it["item_id"], "kb_record_id": rid, "provision": f"{src} paras {','.join(map(str, paras)) or '(none)'}",
                "source_copy_id": cid, "copy_sha256": held.rows[cid]["sha256"],
                "edition_or_version": "official judgment copy registered in C5 (first rendition in file" + (f"; {pm['renditions']} renditions at PDF pp.{pm['rendition_pages']}" if pm else "") + ")",
                "pdf_page": pages_s, "printed_page": "", "page_evidence_method": "TEXT_LAYER_PARAGRAPH_NUMBER (C12); hash-verified local bytes",
                "excerpt": exc, "excerpt_source": "TEXT_LAYER (first words of each paragraph)",
                "amendment_evidence": "NOT_APPLICABLE (judgment)", "commencement_evidence": "NOT_APPLICABLE (judgment)",
                "supersession": "later treatment NOT_ESTABLISHED in C12 (see C11 treatment registers)",
                "temporal_applicability": "applicability of the holding to the record's proposition NOT_ASSESSED (legal review)",
                "reserved_conflict": "", "blockers": " | ".join(blockers), "judgment_links_c11": "", "status": status}))
            if status == "ESTABLISHED_PARA_PAGE_ANCHOR" and base == "PARTIAL_MATCH":
                new_state, change = "EXACT_ANCHOR", "PROMOTE_PARTIAL_TO_EXACT_PROPOSED"
            elif base == "PARTIAL_MATCH":
                change = "PARTIAL_RETAINED_PAGE_EVIDENCE_ADDED" if pages_s else "PARTIAL_RETAINED_NOT_ESTABLISHED"
        elif prov.startswith("act-army-1950#") and tier in ("A", "B"):
            for s in loc:
                n = s[1:]
                hi = aa_idx.get(n)
                vids.append(add_verif({
                    "item_id": it["item_id"], "kb_record_id": rid, "provision": f"Army Act 1950 s.{n}",
                    "source_copy_id": ARMY_ACT_COMPILATION_COPY, "copy_sha256": held.rows[ARMY_ACT_COMPILATION_COPY]["sha256"] if aa_pages else "",
                    "edition_or_version": "India Code compilation of the Army Act 1950 (as-on date not printed; provenance undocumented; not eligible for EXACT_ANCHOR)",
                    "pdf_page": str(hi["page"]) if hi else "", "printed_page": "",
                    "page_evidence_method": (hi["method"] if hi else "NOT_LOCATED"),
                    "excerpt": excerpt_at(aa_pages, hi["page"], hi["offset"], 200) if hi else "",
                    "excerpt_source": "TEXT_LAYER" if hi else "",
                    "amendment_evidence": "compilation footnotes not verified against amending Acts in C12 (Act 37 of 1992 copy f11d443e is registered eligible but the base Act has no eligible copy)",
                    "commencement_evidence": "NOT_ESTABLISHED from a documented primary copy",
                    "supersession": "NOT_ESTABLISHED", "temporal_applicability": "NOT_ESTABLISHED (compilation currency not established)",
                    "reserved_conflict": "", "blockers": "no registered eligible copy of the Army Act 1950 (Gazette 1950 not held)",
                    "judgment_links_c11": str(len(links_by_prov.get(s, ()))),
                    "status": "PAGE_LOCATED_IN_COMPILATION_ONLY" if hi else "NOT_ESTABLISHED"}))
            if base == "PARTIAL_MATCH":
                change = "PARTIAL_RETAINED_PAGE_EVIDENCE_ADDED"
        elif tier == "A":
            vids.append(add_verif({
                "item_id": it["item_id"], "kb_record_id": rid, "provision": prov or f"(no locator) {src}",
                "source_copy_id": "", "copy_sha256": "", "edition_or_version": "", "pdf_page": "", "printed_page": "",
                "page_evidence_method": "", "excerpt": "", "excerpt_source": "",
                "amendment_evidence": "", "commencement_evidence": "", "supersession": "", "temporal_applicability": "",
                "reserved_conflict": "", "blockers": gap_reason, "judgment_links_c11": "",
                "status": "NOT_ESTABLISHED"}))
            if base == "PARTIAL_MATCH":
                change = "PARTIAL_RETAINED_NOT_ESTABLISHED"

        # improvement action
        if change.startswith("PROMOTE"):
            action = "Review proposal; preserve the anchoring copies in the canonical store (C10 preservation risk where WS_ONLY)"
        elif any("annotation/note" in b for b in blockers):
            action = "Re-cite the proposition to the rule text itself (derivative); an annotation or compilation note cannot be anchored in the Gazette"
        elif any("reserved wording conflict" in b for b in blockers):
            action = "Legal-adviser determination of the reserved conflict; custodian-certified copy (C-01 route) before any promotion"
        elif any("AR-030" in b for b in blockers):
            action = "Locate S.R.O. 258/2002 (AR-030) or confirm it does not amend the rule; until then PARTIAL"
        elif any("OPEN alleged" in b for b in blockers):
            ids = sorted({i for b in blockers if "OPEN alleged" in b for i in re.findall(r"OQ-A-\d+|GAP-\d+", b.split(" (cross-refs")[0].split(" - ")[0])})
            action = f"Locate the instrument behind the open WS-A question(s) {', '.join(ids)} or confirm none exists; until then PARTIAL"
        elif any("amending copy not registered" in b or "LOCATED_UNVERIFIED" in b for b in blockers):
            action = "Register documented-primary copies of the amending Gazette instruments (provenance) and image-check"
        elif base == "MISSING_EVIDENCE" and src == "UNMAPPED":
            action = "Identify the cited source (register a source ID) before any acquisition"
        elif base == "MISSING_EVIDENCE":
            action = "Acquire the identified source from an official host (approved acquisition only)"
        elif "GOVERNMENT_COMPILATION" in basis:
            action = "Obtain the enacted Gazette text (documented primary copy); page-locate in it"
        elif "no provision locator" in basis:
            action = "Add a provision/paragraph locator to the citation (derivative), then page-anchor"
        elif "inferred identity" in basis:
            action = "Establish the cited source's identity (case number, date, copy)"
        elif base == "EXACT_ANCHOR":
            action = "None beyond preservation of the anchoring copy"
        else:
            action = "Review"
        matrix.append({
            "item_id": it["item_id"], "crosswalk_line": it["crosswalk_line"], "kb_record_id": rid,
            "volume_family": family_of(rid), "module": rec.get("module", ""), "record_kind": rec.get("kind", ""),
            "kb_status": rec.get("status", ""), "source_id": src, "provision_id": prov,
            "primary_subject": subject, "subject_tags": ";".join(tags), "tier": tier, "open_p0_finding": "YES" if p0 else "",
            "legal_consequence": consequence, "evidence_gap": gap, "source_availability": avail, "priority_score": score,
            "baseline_state": base, "c12_state_proposed": new_state, "c12_change": change,
            "gap_reason": gap_reason, "c12_blockers": " | ".join(blockers)[:1500], "improvement_action": action,
            "verification_ids": ";".join(vids),
        })

    # ---- F-04: record-level state = minimum over the record's citation items; a citation-level EXACT never propagates
    rank_of = {"MISSING_EVIDENCE": 0, "PARTIAL_MATCH": 1, "EXACT_ANCHOR": 2}
    by_rec = defaultdict(list)
    for r in matrix:
        by_rec[r["kb_record_id"]].append(r)
    judgment_exact_partial_statute = OrderedDict()
    for rid in sorted(by_rec):
        rs = by_rec[rid]
        rls = min((r["c12_state_proposed"] for r in rs), key=lambda x: rank_of[x])
        lower = [r for r in rs if rank_of[r["c12_state_proposed"]] < 2]
        for r in rs:
            r["record_level_state"] = rls
            if r["c12_state_proposed"] == "EXACT_ANCHOR":
                r["exact_scope"] = ("CITATION_AND_RECORD" if rls == "EXACT_ANCHOR" else
                                    f"CITATION_LOCATOR_ONLY: record-level state {rls} (minimum over the record's {len(rs)} citation items; "
                                    f"not EXACT: {','.join(x['item_id'] for x in lower)})")
            else:
                r["exact_scope"] = ""
        jp = [r for r in rs if r["source_id"].startswith("C5-SRC-J-") and r["c12_change"] == "PROMOTE_PARTIAL_TO_EXACT_PROPOSED"]
        sp = [r for r in rs if r["c12_state_proposed"] == "PARTIAL_MATCH" and (r["source_id"] == ARMY_RULES_SRC or r["provision_id"].startswith(("act-", "rules-")))]
        if jp and sp:
            judgment_exact_partial_statute[rid] = {
                "judgment_items_exact": [f"{r['item_id']} ({r['source_id']})" for r in jp],
                "statutory_items_partial": [f"{r['item_id']} ({r['provision_id']})" for r in sp],
                "record_level_state": rls}

    # priority ranking: tier A, then B, then C; within tier by score desc, subject rank, item id
    tier_order = {"A": 0, "B": 1, "C": 2}
    matrix.sort(key=lambda r: (tier_order[r["tier"]], -r["priority_score"], SUBJECTS[r["primary_subject"]][0], r["item_id"]))
    for i, r in enumerate(matrix, 1):
        r["priority_rank"] = i

    # ---- proposals
    pcount = 0

    def prop(**kw):
        nonlocal pcount
        pcount += 1
        kw["proposal_id"] = f"C12F-P{pcount:04d}"
        kw["version"] = VERSION
        kw["status"] = "PROPOSED_NOT_APPLIED"
        proposals.append(kw)
        return kw["proposal_id"]

    by_item = {r["item_id"]: r for r in matrix}
    for r in sorted(matrix, key=lambda x: x["item_id"]):
        if r["c12_change"] in ("PROMOTE_PARTIAL_TO_EXACT_PROPOSED", "DEMOTE_EXACT_TO_PARTIAL_PROPOSED",
                               "EXACT_RETAINED_BASIS_CORRECTED_AMENDMENT_ANCHORED", "EXACT_RETAINED_PAGE_ANCHOR_ADDED",
                               "EXACT_RETAINED_PAGE_ANCHOR_NOT_ESTABLISHED_FLAG"):
            kind = {"PROMOTE_PARTIAL_TO_EXACT_PROPOSED": "EVIDENCE_STATE_PROMOTION",
                    "DEMOTE_EXACT_TO_PARTIAL_PROPOSED": "EVIDENCE_STATE_DEMOTION",
                    "EXACT_RETAINED_BASIS_CORRECTED_AMENDMENT_ANCHORED": "ANCHOR_BASIS_CORRECTION",
                    "EXACT_RETAINED_PAGE_ANCHOR_ADDED": "PAGE_ANCHOR_ADDITION",
                    "EXACT_RETAINED_PAGE_ANCHOR_NOT_ESTABLISHED_FLAG": "PAGE_ANCHOR_GAP_FLAG"}[r["c12_change"]]
            conds = "anchor is to the version text on located instruments; currency, authentication of the archival facsimile and legal applicability are NOT established; no record wording changes"
            if kind == "ANCHOR_BASIS_CORRECTION":
                conds = ("C5 baseline missed an amendment recorded in WS-A PCL (comma-list parsing); the anchor is retained only because the amending instrument "
                         "is itself a registered eligible copy with an image-checked page. " + conds)
            if r["c12_state_proposed"] == "EXACT_ANCHOR" and r["record_level_state"] != "EXACT_ANCHOR":
                conds += (f". RECORD SCOPE (F-04): EXACT covers this citation locator only; record {r['kb_record_id']} stays {r['record_level_state']} at record level "
                          "(minimum over its citation items) and must not be shown or aggregated as EXACT")
                if r["kb_record_id"] in judgment_exact_partial_statute:
                    conds += "; the record's statutory content stays PARTIAL: " + ", ".join(judgment_exact_partial_statute[r["kb_record_id"]]["statutory_items_partial"])
            pid = prop(proposal_type=kind, target=f"{r['item_id']} ({r['kb_record_id']})", target_register="SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv line " + r["crosswalk_line"],
                       field="evidence_status", current_value=r["baseline_state"], proposed_value=r["c12_state_proposed"],
                       evidence_class=r["c12_state_proposed"], evidence_refs=r["verification_ids"], conditions=conds,
                       reviewer_required="independent statutory reviewer (evidence class); legal adviser for applicability")
            r["proposal_ids"] = pid
    # rule-level version notes for r.22 and r.23 (all citing items)
    for rule, kind, pv in [
        ("r22", "VERSION_NOTE", "Cite r.22 as substituted by S.R.O. 17(E)/1993 item 5 (printed p.14; in force 06-12-1993 per r.1(2), printed p.12); 1954 text (printed p.299) is the pre-1993 version. Keep PARTIAL: alleged S.R.O. 258/2002 (AR-030) may add an Explanation and is NOT_FOUND."),
        ("r23", "RESERVED_CONFLICT_NOTE", "Cite r.23 to the 1954 Gazette printed p.300 (no amendment located). r.23(3) caution wording conflict C-01 ('not obliged' in the Gazette vs 'obliged' in the India Code compilation) remains CONFLICTING; keep PARTIAL until legal-adviser determination and custodian-certified copy."),
        ("r182", "RESERVED_CONFLICT_NOTE", "r.182 as substituted by S.R.O. 17(E)/1993 item 36 (printed p.18) omits the words 'evidence against a person subject to the Act,' (SC4-01 OPEN); 1954 text printed p.341. Keep PARTIAL."),
        ("r177", "RESERVED_CONFLICT_NOTE", "r.177 substituted by S.R.O. 8(E)/2003 (registered eligible copy ca5d79c2 has no text layer; C-03 CONFLICTING pending text comparison). Keep PARTIAL."),
        ("r135", "VERSION_NOTE", "FOR THE LEGAL ADVISER (F-09; no conclusion drawn here): S.R.O. 17(E)/1993 item 25 (printed p.17) omits the words 'or abstract' in rr.134, 135 and 136. "
                 "The 1954 r.135 (printed p.331) contains 'or abstract' twice ('any summary or abstract of evidence given to the accused'; 'such notice or abstract having been "
                 "given'), while 'together with an abstract of his proposed evidence' does not contain the omitted phrase. Whether both occurrences are omitted, and how the "
                 "records' 'notice/abstract procedure' wording (V9-WF-10, V9-SC-14) should read after 06-12-1993, is for legal determination. The anchor basis correction stands."),
    ] + [(rr, "APPLICABILITY_NOTE", applicability[rr]) for rr in sorted(applicability, key=rule_key)] + [
        (rr, "OPEN_ALLEGED_AMENDMENT_NOTE",
         f"{rr.replace('r', 'r.')} carries an OPEN alleged/unlocated amendment in the WS-A registers ({'; '.join(open_alleged[rr]['ids'])}"
         + (f"; cross-refs {'; '.join(open_alleged[rr]['xref'])}" if open_alleged[rr]["xref"] else "") + f"): {open_alleged[rr]['rows'][0]['text']}. "
         "Every item citing the rule stays PARTIAL until the instrument is located and image-checked, or WS-A records that none exists (F-01).")
        for rr in sorted(open_alleged, key=rule_key)]:
        its = sorted(r["item_id"] for r in matrix if r["source_id"] == ARMY_RULES_SRC and rule in (r["provision_id"].split("#")[1].split(",") if "#" in r["provision_id"] else []))
        if its:
            prop(proposal_type=kind, target=f"{len(its)} items citing Army Rules {rule.replace('r', 'r.')}: " + ";".join(its),
                 target_register="derivative version note (KB records unchanged)", field="citation_version_note", current_value="(none)",
                 proposed_value=pv, evidence_class="NOT_AN_EVIDENCE_STATE_CHANGE (citing items: " + ", ".join(
                     f"{k} {v}" for k, v in sorted(Counter(by_item[i]["c12_state_proposed"] for i in its).items())) + ")",
                 evidence_refs=";".join(sorted({v for i in its for v in by_item[i]["verification_ids"].split(";") if v})[:40]),
                 conditions="derivative note only; no frozen original edited", reviewer_required="legal adviser")

    # ---- cross-volume issues
    xv = cross_volume(kb, matrix, unit, links_by_prov, pilot, esc)
    for x in xv:
        if x.get("proposal"):
            x["proposal_id"] = prop(proposal_type="CROSS_VOLUME_CORRECTION", target=x["records"][:600],
                                    target_register="derivative cross-volume note (KB records unchanged)", field="record_text_review",
                                    current_value="(as frozen)", proposed_value=x["proposal"], evidence_class="NOT_AN_EVIDENCE_STATE_CHANGE",
                                    evidence_refs=x["evidence"][:600], conditions="human/legal review; no wording change applied",
                                    reviewer_required="cross-volume reviewer; legal adviser")
        x.pop("proposal", None)

    # ---- summary
    after = Counter(r["c12_state_proposed"] for r in matrix)
    changes = Counter(r["c12_change"] for r in matrix)
    vstat = Counter(v["status"] for v in verif)
    tierc = Counter(r["tier"] for r in matrix)
    subj = OrderedDict()
    for s in SUBJECTS:
        rs = [r for r in matrix if r["primary_subject"] == s]
        if rs:
            subj[s] = {"items": len(rs), "baseline": dict(sorted(Counter(r["baseline_state"] for r in rs).items())),
                       "c12_proposed": dict(sorted(Counter(r["c12_state_proposed"] for r in rs).items()))}
    fam = OrderedDict()
    for f in sorted({r["volume_family"] for r in matrix}):
        rs = [r for r in matrix if r["volume_family"] == f]
        fam[f] = {"items": len(rs), "baseline": dict(sorted(Counter(r["baseline_state"] for r in rs).items())),
                  "c12_proposed": dict(sorted(Counter(r["c12_state_proposed"] for r in rs).items()))}
    rules_summary = OrderedDict()
    for rr in sorted(unit_cache, key=rule_key):
        u = unit_cache[rr]
        rules_summary[rr] = {"principal_pdf_page": u["principal"]["pdf_page"] if u["principal"] else None,
                             "principal_printed_page": u["principal"]["printed_page"] if u["principal"] else None,
                             "principal_printed_span": u["principal"]["printed_span"] if u["principal"] else None,
                             "principal_page_basis": (u["principal"]["span_method"] if u["principal"] else None),
                             "amending_instruments": [e["instrument"] for e in u["events"]],
                             "established": u["established"], "blockers": u["blockers"]}
    clusters = OrderedDict()
    for rr in ("r22", "r23", "r24", "r25", "r180"):
        rs = [r for r in matrix if r["source_id"] == ARMY_RULES_SRC and "#" in r["provision_id"] and rr in r["provision_id"].split("#")[1].split(",")]
        clusters[rr] = {"army_rules_items_citing": len(rs),
                        "baseline": dict(sorted(Counter(r["baseline_state"] for r in rs).items())),
                        "c12_proposed": dict(sorted(Counter(r["c12_state_proposed"] for r in rs).items())),
                        "unit_status": ("ESTABLISHED" if unit(rr)["established"] else "; ".join(unit(rr)["blockers"]))}
    # v1.1 remediation blocks
    promoted = {r["item_id"] for r in matrix if r["c12_change"] == "PROMOTE_PARTIAL_TO_EXACT_PROPOSED"}
    rv = {re.match(r"(\S+)", x["item"]).group(1): x["verdict"] for x in review_rows}
    review_recon = OrderedDict([
        ("review_rows", len(rv)),
        ("supported_and_promoted", sum(1 for i, v in rv.items() if v == "SUPPORTED" and i in promoted)),
        ("supported_not_promoted", sorted(i for i, v in rv.items() if v == "SUPPORTED" and i not in promoted)),
        ("not_supported_withdrawn", sorted(f"{i} ({by_item[i]['kb_record_id']})" for i, v in rv.items() if v != "SUPPORTED" and i not in promoted)),
        ("not_supported_still_promoted", sorted(i for i, v in rv.items() if v != "SUPPORTED" and i in promoted)),
        ("promoted_not_in_review", sorted(promoted - set(rv))),
        ("note", "read only for reconciliation; states are set by the evidence rules, never by the review file"),
    ])
    oa_summary = OrderedDict()
    for rr in sorted(open_alleged, key=rule_key):
        its = [r for r in matrix if r["source_id"] == ARMY_RULES_SRC and "#" in r["provision_id"] and rr in r["provision_id"].split("#")[1].split(",")]
        oa_summary[rr] = {"wsa_ids": open_alleged[rr]["ids"], "cross_refs": open_alleged[rr]["xref"],
                          "questions": [f"{x['id']} [{x['state']}]: {x['text']}" for x in open_alleged[rr]["rows"]],
                          "citing_army_rules_items": len(its),
                          "citing_items_exact": sorted(r["item_id"] for r in its if r["c12_state_proposed"] == "EXACT_ANCHOR"),
                          "other_blockers_on_rule": [b for b in unit(rr)["blockers"] if "OPEN alleged" not in b],
                          "only_blocker_is_open_alleged": not [b for b in unit(rr)["blockers"] if "OPEN alleged" not in b]}
    spans = OrderedDict()
    for rr in sorted(unit_cache, key=rule_key):
        u = unit_cache[rr]
        sp = []
        if u["principal"] and u["principal"]["pdf_end"] != u["principal"]["pdf_page"]:
            sp.append(f"1954 printed pp.{u['principal']['printed_span']} ({u['principal']['span_method']})")
        sp += [f"{e['instrument']} printed pp.{e['printed_page']} (image-checked)" for e in u["events"] if "-" in str(e.get("printed_page", ""))]
        if sp:
            spans[rr] = sp
    ar_exact = [r for r in matrix if r["source_id"] == ARMY_RULES_SRC and r["c12_state_proposed"] == "EXACT_ANCHOR" and "#" in r["provision_id"]]
    basis = Counter()
    for r in ar_exact:
        bs = {unit(x)["principal"]["span_method"] for x in r["provision_id"].split("#")[1].split(",") if unit(x)["principal"]}
        basis[("promoted " if r["c12_change"].startswith("PROMOTE") else "baseline EXACT ") + ("all 1954 pages image-checked" if bs == {"IMAGE_CHECKED"} else "some 1954 pages text-layer only")] += 1
    soe = [r for r in matrix if r["primary_subject"] in ("AR23_SUMMARY_OF_EVIDENCE_RULE", "SUMMARY_OF_EVIDENCE")]
    clusters["summary_of_evidence_subject_items"] = {"items": len(soe), "baseline": dict(sorted(Counter(r["baseline_state"] for r in soe).items())),
                                                     "c12_proposed": dict(sorted(Counter(r["c12_state_proposed"] for r in soe).items()))}
    summary = OrderedDict([
        ("workstream", "C12-F statutory citations"), ("version", VERSION),
        ("frozen_originals", pins),
        ("input_sha256", input_hashes),
        ("page_evidence_validation", dict(sorted(pe_status.items()))),
        ("pymupdf_version", __import__("pymupdf").VersionBind),
        ("citation_items", len(matrix)),
        ("before", dict(sorted(base_counts.items()))),
        ("after_proposed", dict(sorted(after.items()))),
        ("delta", {k: after.get(k, 0) - base_counts.get(k, 0) for k in sorted(set(after) | set(base_counts))}),
        ("transitions", dict(sorted(Counter(f"{r['baseline_state']}->{r['c12_state_proposed']}" for r in matrix).items()))),
        ("c12_change_counts", dict(sorted(changes.items()))),
        ("promotions_by_source", dict(sorted(Counter(r["source_id"] for r in matrix if r["c12_change"] == "PROMOTE_PARTIAL_TO_EXACT_PROPOSED").items()))),
        ("promotions_by_rule_set", dict(sorted(Counter(r["provision_id"].split("#")[1] for r in matrix
                                                       if r["c12_change"] == "PROMOTE_PARTIAL_TO_EXACT_PROPOSED" and "#" in r["provision_id"]).items()))),
        ("tier_counts", dict(sorted(tierc.items()))),
        ("verification_rows", len(verif)), ("verification_status_counts", dict(sorted(vstat.items()))),
        ("cross_volume_issues", len(xv)), ("cross_volume_issue_types", dict(sorted(Counter(x["issue_type"] for x in xv).items()))),
        ("correction_proposals", len(proposals)), ("proposal_types", dict(sorted(Counter(p["proposal_type"] for p in proposals).items()))),
        ("priority_rule_clusters", clusters), ("by_subject", subj), ("by_volume_family", fam),
        ("army_rules_provision_units", rules_summary),
        ("open_alleged_amendment_blockers_F01", oa_summary),
        ("annotation_locator_blocked_items_F02", sorted(f"{r['item_id']} ({r['kb_record_id']})" for r in matrix if "annotation/note" in r["c12_blockers"])),
        ("army_rules_exact_items_by_1954_page_basis_F03", dict(sorted(basis.items()))),
        ("record_scope_F04", OrderedDict([
            ("rule", "record-level state = minimum of c12_state_proposed over the record's citation items; a citation-level EXACT never propagates (matrix columns record_level_state, exact_scope)"),
            ("exact_items_citation_locator_only", sum(1 for r in matrix if r["exact_scope"].startswith("CITATION_LOCATOR_ONLY"))),
            ("records_with_exact_item_but_record_level_below_exact", len({r["kb_record_id"] for r in matrix if r["exact_scope"].startswith("CITATION_LOCATOR_ONLY")})),
            ("judgment_promotions_on_records_with_partial_statutory_content", judgment_exact_partial_statute)])),
        ("page_ranges_F05", spans),
        ("review_reconciliation", review_recon),
        ("honesty_notes", [
            "Counts under after_proposed are PROPOSALS; corpus_crosswalk.csv, the C10 outputs and the KB records are unchanged.",
            "EXACT_ANCHOR means an exact page anchor in a registered documented-primary copy of the version text on located instruments; it does not authenticate the archival facsimile, establish currency after the located instruments, or establish legal applicability.",
            "No MISSING_EVIDENCE item is promoted; MISSING items need source identification or approved acquisition.",
            "Army Act / AFT Act / BSA / BNSS citations stay PARTIAL: only government compilations with undocumented provenance are held.",
            "Anchoring copies held only in the ephemeral working store (e.g. the 1954 Gazette c5ef95a9) remain a C10 preservation risk.",
            "Subject classification is a deterministic keyword/provision heuristic, not a legal characterisation.",
            "v1.1: every OPEN alleged-amendment question or gap in the WS-A registers that names a rule blocks EXACT for that rule (F-01); annotation/note locators are not anchorable (F-02); a citation-level EXACT is never a record-level state (F-04).",
        ]),
    ])
    return matrix, verif, xv, proposals, summary


# ------------------------------------------------------------------ cross-volume
def cross_volume(kb, matrix, unit, links_by_prov, pilot, esc):
    out = []

    def snip(rid, pat, w=110):
        s = " ".join([kb[rid].get("title", ""), kb[rid].get("body", ""), str(kb[rid].get("references", ""))])
        m = re.search(pat, s, re.I)
        return ws(s[max(0, m.start() - w):m.end() + w]) if m else ""

    def recs(pat):
        return sorted(r for r in kb if re.search(pat, " ".join([kb[r].get("title", ""), kb[r].get("body", ""), str(kb[r].get("references", ""))]), re.I))

    def fams(ids):
        c = defaultdict(list)
        for i in ids:
            c[family_of(i)].append(i)
        return "; ".join(f"{f}: {','.join(v)}" for f, v in sorted(c.items()))

    cites = defaultdict(set)
    for r in matrix:
        if r["source_id"] == ARMY_RULES_SRC and "#" in r["provision_id"]:
            for x in r["provision_id"].split("#")[1].split(","):
                cites[x].add(r["kb_record_id"])

    n = 0
    P_R22 = r"dispens|proviso|22\(4\)"
    P_R25 = r"r\.? ?25|22\s*[–-]\s*26"

    def add(subject, itype, ids, desc, evidence, severity, refs="", proposal=""):
        nonlocal n
        n += 1
        out.append({"issue_id": f"C12F-X{n:03d}", "subject": subject, "issue_type": itype, "families": ",".join(sorted({family_of(i) for i in ids})),
                    "records": fams(ids), "description": desc, "evidence": evidence, "severity": severity,
                    "existing_finding_refs": refs, "proposal": proposal})

    # X: r.23(3) caution wording across volumes
    caution = recs(r"\b(?:rule|r\.?|ar)\s*23\b|summary of evidence|\bSoE\b")
    quoted = [r for r in caution if re.search(r"obliged", " ".join([kb[r]["body"], str(kb[r].get("references", ""))]), re.I)]
    caution_only = [r for r in caution if re.search(r"\bcaution", kb[r]["body"], re.I) and r not in quoted]
    add("AR23_SUMMARY_OF_EVIDENCE_RULE", "RESERVED_CONFLICT_DEPENDENCY", sorted(set(quoted + caution_only)),
        f"Records describing the r.23(3) caution. {len(quoted)} paraphrase it ('not obliged', consistent with the 1954 Gazette printed p.300); "
        f"{len(caution_only)} refer to a caution without wording. All depend on reserved conflict C-01 (India Code compilation p.41 omits 'not'). "
        "No record states the compilation wording, but no record flags the conflict either except HCE-010's risk line.",
        "Gazette c5ef95a9 PDF p.10 / printed p.300 image-read (PE-1954-300-R23); " + "; ".join(f"{r}: {snip(r, 'obliged|caution', 70)}" for r in (quoted + caution_only)[:6]),
        "HIGH", "C5-CF-C-01; ESC-R23-3; PILOT-01 F-XVOL-001/F-XVOL-002/F-STAT-001",
        "Add a derivative caution note to every SoE record: quote the 1954 Gazette wording with its page and state that C-01 is unresolved; do not quote the compilation wording.")

    # X: r.22 version dependency (1993 substituted text vs 1954)
    r22 = sorted(cites.get("r22", set()) | set(recs(r"\b(?:army\s+)?(?:rule|r\.?|ar)\s*22\b")))
    v93 = [r for r in r22 if re.search(r"dispens|22\s*\(1\)\s*proviso|22\(4\)|r\s*22\(1\)\s*[–-]\s*\(4\)|frame suitable charge|reasonable time", " ".join([kb[r]["body"], str(kb[r].get("references", ""))]), re.I)
           and r not in X002_EXCLUDE]
    add("AR22_HEARING_OF_CHARGE", "VERSION_DEPENDENCY", v93,
        f"{len(v93)} of {len(r22)} r.22 records rely on elements that exist only in the r.22 substituted by S.R.O. 17(E)/1993 item 5 (proviso dispensing with r.22(1) where a CoI complied with r.180; sub-rule (4); hearing of every person incl. officers). "
        "The 1954 text (printed p.299) applies only to persons other than officers and has no proviso or sub-rule (4). Records do not say which version they state; the alleged S.R.O. 258/2002 (AR-030, NOT_FOUND) may add an Explanation.",
        "1993 PDF p.14 image-read (PE-1993-14-R22); 1954 PDF p.9 image-read (PE-1954-299-R22); " + "; ".join(f"{r}: {snip(r, P_R22, 60)}" for r in v93[:5]),
        "MEDIUM", "ARMY-RULES-CHAIN-01 AR-030; WS-A PCL-93-5" + "".join(f"; excluded {k}: {v}" for k, v in X002_EXCLUDE.items()),
        "Add derivative version notes: r.22 as substituted 06-12-1993 (S.R.O. 17(E)/1993 p.14); flag AR-030 gap.")
    r22_other = [r for r in r22 if r not in v93]
    add("AR22_HEARING_OF_CHARGE", "MISSING_CONNECTION", r22_other,
        f"{len(r22_other)} r.22 records (other volumes) do not mention the 1993 r.22(1) proviso or r.22(4), although records in CORE_KB/HCE/COI treat them as central; cross-volume guidance on when the hearing may be dispensed with is uneven.",
        "; ".join(f"{r}" for r in r22_other[:30]), "LOW", "", "")

    # X: r.25 omitted 1993
    r25 = sorted(cites.get("r25", set()) | set(recs(r"\b(?:rule|r\.?)\s*25\b|rr\.?\s*22\s*[–-]\s*26")))
    add("SUMMARY_OF_EVIDENCE", "OBSOLETE_PROVISION_REFERENCE", r25,
        "Army Rule 25 (procedure on charge against officer; abstract of evidence) was omitted by S.R.O. 17(E)/1993 item 6 (printed p.14), with consequential omissions in rr.26(1),(3), 33(7), 36, 37(4) (items 7-10, printed pp.14-15). "
        "HCE-015 correctly marks r.25 omitted; records citing ranges such as 'rr 22-26' include the omitted rule without a note.",
        "PE-1993-14-R25-R26; PE-1993-15-R26-R37; " + "; ".join(f"{r}: {snip(r, P_R25, 50)}" for r in r25[:5]),
        "LOW", "WS-A PCL-93-6..10", "Replace ranges that include r.25 with explicit live rules and a note that r.25 was omitted w.e.f. 06-12-1993.")

    # X: r.182 SC4-01 antecedent omission vs record paraphrases
    r182 = sorted(cites.get("r182", set()) | set(recs(r"\b(?:rule|r\.?)\s*182\b")))
    antecedent = [r for r in r182 if re.search(r"against (?:a|the) person subject to the (?:Army )?Act", kb[r]["body"], re.I)]
    proviso = [r for r in r182 if re.search(r"cross-examin", kb[r]["body"], re.I)]
    add("COURT_OF_INQUIRY_OTHER", "TEXT_VERSION_CONFLICT", sorted(set(antecedent + proviso)),
        f"r.182 records span COI, CORE_KB and EV volumes. {len(proviso)} rely on the 1993 proviso (use for cross-examination), which exists only in the S.R.O. 17(E)/1993 item 36 substitution (printed p.18); "
        f"{len(antecedent)} also paraphrase 'against a person subject to the Act', words present in the 1954 text (printed p.341) but absent from the 1993 Gazette substitution (SC4-01 OPEN). The records combine the two versions.",
        "PE-1993-18-R179-R182; PE-1954-341-R181-183; " + "; ".join(f"{r}: {snip(r, 'against (?:a|the) person subject|cross-examin', 60)}" for r in sorted(set(antecedent + proviso))[:6]),
        "MEDIUM", "CALIBRATION-02 SC4-01; C5-CF-SC4-01",
        "Derivative note on each r.182 record: proviso = 1993 text; the 'against a person subject to the Act' phrase is not in the 1993 Gazette text (SC4-01 unresolved).")

    # X: r.180 and Virendra holding (mandatory vs effect)
    r180 = sorted(cites.get("r180", set()) | set(recs(r"\b(?:rule|r\.?|ar)\s*180\b")))
    vk = set(recs(r"virendra|SRC-VIR|SC_VK|V9-S07"))
    no_vk = [r for r in r180 if r not in vk]
    add("AR180_COI_CHARACTER", "MISSING_CONNECTION", no_vk,
        f"{len(r180)} records rely on r.180 (1954 Gazette printed p.341, no amendment located). {len(r180) - len(no_vk)} connect it to Virendra Kumar (2020), the held SC authority on the consequence of r.180 lapses; "
        f"{len(no_vk)} do not, so the 'mandatory but context-specific effect' qualification (KB-026, CM-JD-04) is not carried across volumes. C11 records {len(links_by_prov.get('r180', ()))} corpus judgments linked to r.180.",
        "PE-1954-341-R180; C11 STATUTE_JUDGMENT_LINKS AR-1954:r.180; " + ",".join(no_vk[:40]), "MEDIUM", "",
        "Add a derivative cross-reference from r.180 records to Virendra Kumar (2020) paras 11-15 and the KB-026 caution on remedy.")

    # X: SoE records that do not cite r.23
    soe = recs(r"summary of evidence|\bSoE\b")
    soe_no23 = [r for r in soe if r not in (cites.get("r23", set()) | cites.get("r24", set()))
                and not re.search(r"\b(?:rule|r\.?|ar|rr)\s*2[34]\b|22\s*[–-]\s*2[4-6]", " ".join([kb[r]["body"], str(kb[r].get("references", ""))]), re.I)]
    add("SUMMARY_OF_EVIDENCE", "MISSING_CONNECTION", soe_no23,
        f"{len(soe_no23)} of {len(soe)} records that discuss the Summary of Evidence cite neither r.23 nor r.24 by number in a resolvable form, so they are not linked to the provision page (printed p.300).",
        ",".join(soe_no23[:50]), "LOW", "", "")

    # X: limitation period wording s.122 across CM / HCE / CIV / ADM
    lim = recs(r"(?:section|s\.?|§§?)\s*122\b|ss\.?\s*122")
    yrs = defaultdict(list)
    for r in lim:
        for m in re.finditer(r"\b(one|two|three|four|five|six|seven|ten|\d{1,2})[- ]years?\b", kb[r]["body"], re.I):
            yrs[m.group(1).lower()].append(r)
    add("LIMITATION", "CONSISTENCY_CHECK", lim,
        f"{len(lim)} records across {len({family_of(r) for r in lim})} families rely on Army Act s.122 (with s.123). Period wording found: "
        + ", ".join(f"'{k}-year' in {sorted(set(v))}" for k, v in sorted(yrs.items())) +
        ". No contradictory period stated, but s.122 is cited only to the India Code compilation (no eligible copy), so every limitation computation record remains PARTIAL.",
        "Army Act compilation e47a4265 s.122 page located (text layer); " + "; ".join(f"{r}: {snip(r, '122', 50)}" for r in lim[:4]),
        "MEDIUM", "", "")

    # X: pre-1993 judgments cited with rules substituted/omitted/amended in 1993
    jsrc = defaultdict(set)
    for r in matrix:
        m = re.match(r"C5-SRC-J-SC-(\d{4})-", r["source_id"])
        if m:
            jsrc[r["kb_record_id"]].add((int(m.group(1)), r["source_id"]))
    t_ids, t_ev = [], []
    for rid in sorted(jsrc):
        old_j = sorted(x for x in jsrc[rid] if x[0] < 1993)
        rules93 = sorted(x for x in ("r22", "r25", "r26", "r33", "r182") if rid in cites.get(x, set()))
        if old_j and rules93:
            t_ids.append(rid)
            t_ev.append(f"{rid}: {','.join(rules93)} with {','.join(j[1].split('C5-SRC-J-SC-')[1] for j in old_j)}")
    add("AR22_HEARING_OF_CHARGE", "TEMPORAL_MISMATCH_RISK", t_ids,
        f"{len(t_ids)} records pair rules substituted or amended by S.R.O. 17(E)/1993 (in force 06-12-1993) with Supreme Court judgments decided before 1993; those judgments construe the 1954 text "
        "(e.g. r.22 confined to persons other than officers, with r.25 for officers). The records do not say that the judgment applied the earlier version.",
        "; ".join(t_ev), "MEDIUM", "WS-A PCL-93-5..10, PCL-93-36",
        "Add derivative temporal notes: judgment applied the 1954 text of the rule; current text from 06-12-1993.")

    # X: r.14 / r.15 / r.17 version chain for administrative-action records
    adm = sorted(cites.get("r14", set()) | cites.get("r15", set()) | cites.get("r17", set()))
    oa15 = unit("r15").get("open_alleged")
    r15_txt = (f" r.15 also carries an OPEN alleged amendment ({'; '.join(oa15['ids'])}; {'; '.join(oa15['xref'])}): MML 2 p.142 prints '[or Military Secretary]' and attributes it to "
               "S.R.O. 17(E)/1993, which has no r.15 item; the source is not located, so r.15 citations stay PARTIAL." if oa15 else "")
    add("ADMINISTRATIVE_ACTION", "VERSION_DEPENDENCY", adm,
        f"{len(adm)} records cite rr.14/15/17 (termination, dismissal or removal). The 1954 text (printed pp.296-297) was substituted by S.R.O. 205/1961 (printed pp.141-143; commencement not stated, AQ-05) "
        "and r.14(4),(5) again by S.R.O. 17(E)/1993 item 2 (printed p.12; 'compulsorily retired' replaces 'called upon to retire/resign'). Records and the judgments they cite do not state which text applied to the facts."
        + r15_txt + " r.15B (S.R.O. 17(E)/2019, AR-034; copy not eligible) disapplies rr.14, 15 and 15A for the CDS office (applicability only).",
        "PE-1961-141-R14; PE-1961-142-R15; PE-1961-143-R16-R17; PE-1993-12-R14; " + ",".join(adm), "LOW",
        "WS-A PCL-205-1961-r14; PCL-93-2" + (f"; {'; '.join(oa15['ids'])}; {'; '.join(oa15['xref'])}" if oa15 else "") + "; WS-A r15_military_secretary_trace_cycle3 item 8",
        "Derivative version note on r.14/15/17 records (1954 -> 1961 -> 1993); r.15 note on the unlocated '[or Military Secretary]' words; r.15B applicability note.")

    # X: statutory complaints (AA ss.26-27) <-> AFT s.21 exhaustion / s.22 limitation
    sc = sorted({r["kb_record_id"] for r in matrix if re.search(r"act-army-1950#(?:.*,)?s2[67](?:,|$)", r["provision_id"])})
    aft21 = sorted({r["kb_record_id"] for r in matrix if re.search(r"act-armed-forces-tribunal-2007#(?:.*,)?s2[12](?:,|$)", r["provision_id"])})
    sc_linked = [r for r in sc if r in aft21]
    aft_no_sc = [r for r in aft21 if r not in sc and not re.search(r"statutory complaint|section 2[67]|§\s*2[67]|s\.?\s*2[67]\b", kb[r]["body"], re.I)]
    add("STATUTORY_COMPLAINTS", "MISSING_CONNECTION", sorted(set(sc) | set(aft_no_sc)),
        f"{len(sc)} ADM records cite Army Act ss.26-27 (statutory complaints); {len(sc_linked)} of them also cite AFT Act s.21/s.22 (exhaustion and limitation). "
        f"{len(aft_no_sc)} AFT-volume records on s.21/s.22 do not mention the statutory-complaint route. Both sides are cited only to India Code compilations (PARTIAL).",
        "ADM: " + ",".join(sc) + " | AFT s.21/22 without complaint link: " + ",".join(aft_no_sc[:30]), "LOW", "", "")

    # X: unsupported 'r.23 amended 2022' (C10 escalation) - check frozen text
    claim = [r for r in ("EV-016", "HCE-010", "SC03") if r in kb and re.search(r"2022", kb[r]["body"] + str(kb[r].get("references", "")))]
    add("AR23_SUMMARY_OF_EVIDENCE_RULE", "UNSUPPORTED_CLAIM_CHECK", ["EV-016", "HCE-010", "SC03"],
        "C10 escalation ESC-R23-2022 records an unsupported claim that r.23 was amended in 2022. In the frozen v0.9 text of EV-016, HCE-010 and SC03 the claim "
        + ("is present in: " + ",".join(claim) if claim else "is not present (no '2022' in body or references)") + ". S.R.O. 6(E)/2022 amends r.16A(4) only.",
        "C10 escalation_matters_c10.csv ESC-R23-2022; ARMY-RULES-CHAIN-01 AR-035", "LOW" if not claim else "HIGH", "ESC-R23-2022", "")

    # X: r.177 composition (2003 substitution) - CoI records
    r177 = sorted(cites.get("r177", set()))
    add("COURT_OF_INQUIRY_OTHER", "RESERVED_CONFLICT_DEPENDENCY", r177,
        f"{len(r177)} records cite r.177 (CoI composition/assembly). r.177 was substituted by S.R.O. 8(E)/2003 (registered eligible copy ca5d79c2; image-only, no text layer) and C-03 remains CONFLICTING; records do not state which text they follow.",
        "C5-CF-C-03; WS-A PCL-8E-2003", "MEDIUM", "C5-CF-C-03",
        "Derivative note: r.177 as substituted 24-06-2003; C-03 pending.")
    return out


# ------------------------------------------------------------------ write / check
MATRIX_FIELDS = ["priority_rank", "tier", "item_id", "crosswalk_line", "kb_record_id", "volume_family", "module", "record_kind", "kb_status",
                 "source_id", "provision_id", "primary_subject", "subject_tags", "open_p0_finding", "legal_consequence", "evidence_gap",
                 "source_availability", "priority_score", "baseline_state", "c12_state_proposed", "c12_change", "gap_reason", "c12_blockers",
                 "improvement_action", "verification_ids", "proposal_ids", "record_level_state", "exact_scope"]
VERIF_FIELDS = ["verification_id", "item_id", "kb_record_id", "provision", "source_copy_id", "copy_sha256", "edition_or_version", "pdf_page",
                "printed_page", "page_evidence_method", "excerpt", "excerpt_source", "amendment_evidence", "commencement_evidence",
                "supersession", "temporal_applicability", "reserved_conflict", "blockers", "judgment_links_c11", "status", "applicability_note", "note"]
XV_FIELDS = ["issue_id", "subject", "issue_type", "families", "records", "description", "evidence", "severity", "existing_finding_refs", "proposal_id"]
PROP_FIELDS = ["proposal_id", "version", "proposal_type", "target", "target_register", "field", "current_value", "proposed_value",
               "evidence_class", "evidence_refs", "conditions", "reviewer_required", "status"]


def render():
    matrix, verif, xv, proposals, summary = build()
    files = OrderedDict()
    files["IMPROVEMENT_MATRIX.csv"] = csv_bytes(matrix, MATRIX_FIELDS)
    files["PRIORITY_VERIFICATION.csv"] = csv_bytes(verif, VERIF_FIELDS)
    files["CROSS_VOLUME_ISSUES.csv"] = csv_bytes(xv, XV_FIELDS)
    files["CORRECTION_PROPOSALS_C12.csv"] = csv_bytes(proposals, PROP_FIELDS)
    files["SUMMARY.json"] = (json.dumps(summary, indent=1, ensure_ascii=False, sort_keys=False) + "\n").encode("utf-8")
    files["OUTPUT_SHA256SUMS"] = "".join(f"{hashlib.sha256(b).hexdigest()}  {n}\n" for n, b in files.items()).encode()
    return files


def require_env():
    """F-10: fail early and clearly outside the pinned environment (README "Running")."""
    if sys.version_info < (3, 11):
        raise SystemExit(f"Python >= 3.11 required (outputs recorded with 3.13); got {sys.version.split()[0]}")
    try:
        import pymupdf  # noqa: F401, PLC0415
    except ImportError:
        raise SystemExit("PyMuPDF (pymupdf) is not installed for " + sys.executable +
                         ": use the pinned venv named in README.md (Python 3.13, PyMuPDF VersionBind recorded in SUMMARY.json)") from None


def main(argv=None):
    require_env()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="rebuild in memory and compare with outputs/")
    a = ap.parse_args(argv)
    files = render()
    if a.check:
        bad = []
        for n, b in files.items():
            p = OUT / n
            if not p.exists() or p.read_bytes() != b:
                bad.append(n)
        if bad:
            print("CHECK FAILED: " + ", ".join(bad))
            return 1
        print(f"CHECK OK: {len(files)} outputs reproduce byte-for-byte; frozen originals verified")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for n, b in files.items():
        (OUT / n).write_bytes(b)
    s = json.loads(files["SUMMARY.json"])
    print(json.dumps({"before": s["before"], "after_proposed": s["after_proposed"], "changes": s["c12_change_counts"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
