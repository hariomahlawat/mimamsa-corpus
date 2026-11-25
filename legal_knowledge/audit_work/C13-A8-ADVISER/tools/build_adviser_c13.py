"""C13-A8: build the consolidated legal-adviser package from questions the workstreams already raised.

Inputs (committed files only, read-only):
  C12 adviser package (59 questions + excerpt verification), A4 adviser packet (96), A6 form register / R04 status /
  README examples, A5 treatment candidates (OVERRULES/DISAPPROVES) and SC case-number reconfirmation (99) plus the
  C11 unreviewed candidates (266), A1 relevance review queue (6 MANUAL_REVIEW + UNCERTAIN), A7 dispositions (no legal
  question found; recorded in BUILD_INFO).

Outputs (outputs/): ADVISER_QUESTIONS_C13.csv, ADVISER_ANCHORS_C13.csv, DEDUP_MAP_C13.csv, ADVISER_BRIEF_C13.md,
BUILD_INFO.json. `--check` rebuilds in memory and compares byte for byte.

No legal conclusion is drawn. Question wording is carried verbatim from the originating artefact; where A8 had to
phrase a question (A6 form items, A1 relevance items, A5 case-number items) it restates what the artefact records as
open and cites no authority the artefact does not cite. Nothing is legally reviewed. RM-001 is excluded.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a8_registers import AW, REPO, RM001_DOC, RM001_SHA, Registers, sha256_file  # noqa: E402

PKG = AW / "C13-A8-ADVISER"
OUT = PKG / "outputs"
VERSION = "C13-A8-v1"
NLR = "NOT LEGALLY REVIEWED"
AWAIT = "AWAITING_ADVISER"

C12Q = AW / "C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv"
C12X = AW / "C12-CONSOLIDATION/adviser_package/EXCERPT_VERIFICATION.csv"
C12SUMS = AW / "C12-CONSOLIDATION/adviser_package/SHA256SUMS"
A4P = AW / "C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv"
A4SUMS = AW / "C13-A4-STATUTORY/SHA256SUMS"
C12F_V = AW / "C12-CONSOLIDATION/statutory_citations/outputs/PRIORITY_VERIFICATION.csv"
C12F_PE = AW / "C12-CONSOLIDATION/statutory_citations/tools/page_evidence_c12.csv"
A4_EP = AW / "C13-A4-STATUTORY/outputs/EVIDENCE_PROPOSALS_C13.csv"
A4_PE = AW / "C13-A4-STATUTORY/inputs/page_evidence_c13.csv"
A6REG = AW / "C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv"
A6R04 = AW / "C13-A6-FORMS/outputs/R04_FAMILY_STATUS.csv"
A6SUMS = AW / "C13-A6-FORMS/SHA256SUMS"
A6REV = AW / "C13-A6-FORMS/reviews/review_c13_a6_1b05490f_findings.csv"
A5EDGES = AW / "C13-A5-GRAPH/graph/edges_candidate.jsonl.gz"
A5SCN = AW / "C13-A5-GRAPH/scnum/SCNUM_RECONFIRMATION_C13.csv"
A5SUMS = AW / "C13-A5-GRAPH/SHA256SUMS"
A5PIC = AW / "C13-A5-GRAPH/scnum/PAGE_IMAGE_CHECKS_C13.csv"
C11SCN = AW / "C11-JUDICIAL-QUALITY/scnum/review/SC_CASE_NUMBER_REVIEWED_STATUS.csv"
A1RR = AW / "C13-A1-OCR/RELEVANCE_RERUN.csv"
A1ING = AW / "C13-A1-OCR/INGESTION_DECISIONS.csv"
A1SUMS = AW / "C13-A1-OCR/SHA256SUMS"
A7DISP = AW / "C13-A7-ACQUISITION/DISPOSITIONS_C13.md"

csv.field_size_limit(1 << 30)

Q_COLS = [
    "question_id", "priority", "priority_basis", "topic", "question_kind", "question", "also_asked_as",
    "origin_ids", "origin_workstreams", "origin_priorities", "dedup_note", "affected_records", "anchor_count",
    "anchor_basis", "anchors_summary", "legal_review_status", "adviser_answer_status", "adviser_answer",
    "adviser_role", "answer_date", "answer_reference",
]
A_COLS = [
    "question_id", "anchor_seq", "anchor_kind", "doc_id", "sha256", "page", "page_kind", "locator",
    "origin_ref", "binding_registers", "stored_path_register", "stored_path",
]
D_COLS = ["origin_id", "origin_workstream", "question_id", "relation", "note"]

KINDS = {
    "STATUS_RELATION", "TEXT_CONFLICT", "COMMENCEMENT_TEMPORAL", "CROSS_REFERENCE", "EVIDENCE_PROMOTION",
    "LEGAL_INTERPRETATION", "FORM_TEXT", "RELEVANCE_SCOPE", "DOCUMENTARY_VERIFICATION", "ROLE_PROCESS",
    "SOURCE_AUTHORITY",
}
PAGE_KINDS = {
    "TEXT_LAYER_PAGE_ad77758d", "PDF_PAGE", "PRINTED_PAGE", "PAGE_AS_STATED_IN_SOURCE", "COVER_PAGE_WHOLE_DOCUMENT",
    "NOT_STATED_IN_SOURCE", "RECORD_ROW",
}

PRIORITY_RUBRIC = {
    "P0": "Answer controls the wording of a procedural safeguard that would be put to an accused (operative text in "
          "direct conflict between held copies).",
    "P1": "Answer controls whether a military-law authority or provision is current, binding or in force on a date "
          "(overruling/relation, commencement, temporal axis, repealed-code cross-references), the operative text of "
          "a rule used in court-martial or court-of-inquiry procedure, the pension-rules version, a form that blocks "
          "R04 closure or every template, or who may approve operational use.",
    "P2": "Everything else: citation-level evidence promotions, own-voice overruling leads outside military law, "
          "relevance-scope decisions, documentary verification (case numbers), form text discrepancies, source "
          "authority ranking, acquisition and historical-window questions.",
}


# ---------------------------------------------------------------- helpers
def rows(p: Path):
    data = p.read_bytes()
    if p.suffix == ".gz":
        data = gzip.decompress(data)
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))


def rel(p: Path) -> str:
    return p.resolve().relative_to(REPO).as_posix()


def sums_entry(sums: Path, target: Path) -> str:
    """sha256 recorded for `target` in a SHA256SUMS file (paths relative to the SUMS directory)."""
    want = target.resolve()
    for line in sums.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([0-9a-f]{64})\s+\*?(.+)$", line.strip())
        if m and (sums.parent / m.group(2)).resolve() == want:
            return m.group(1)
    raise SystemExit(f"{rel(target)} not listed in {rel(sums)}")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


class Builder:
    def __init__(self):
        self.R = Registers()
        self.q: list[dict] = []
        self.anchors: dict[str, list[dict]] = {}
        self.dedup: list[dict] = []
        self.doc2sha = {}
        for (d, s), regs in self.R.bind.items():
            if "CRAWLER_MANIFEST_HF5524" in regs:
                self.doc2sha.setdefault(d, set()).add(s)

    # ---- anchors
    def preferred_id(self, sha: str) -> str:
        ids = sorted(self.R.ids_by_sha.get(sha, ()))
        good = [i for i in ids if "~" not in i and not i.startswith("C12CV-")]
        crawler = [i for i in good if re.match(r"^[a-z]", i)]
        return (crawler or good or ids)[0]

    def sha_from_prefix(self, prefix: str) -> str:
        hits = self.R.by_prefix(prefix)
        if len(hits) != 1:
            raise SystemExit(f"sha prefix {prefix} resolves to {len(hits)} copies")
        return hits.pop()

    def src_anchor(self, doc_id, sha, page, page_kind, locator="", origin_ref=""):
        if sha == RM001_SHA or doc_id == RM001_DOC:
            raise SystemExit("RM-001 reached an anchor")
        regs, (preg, ppath) = self.R.resolve(doc_id, sha)
        return {
            "anchor_kind": "SOURCE_PAGE", "doc_id": doc_id, "sha256": sha,
            "page": "" if page in (None, "") else str(int(page)), "page_kind": page_kind,
            "locator": locator, "origin_ref": origin_ref, "binding_registers": ";".join(regs),
            "stored_path_register": preg, "stored_path": ppath,
        }

    def anchor_by_prefix(self, prefix, page, page_kind, locator="", origin_ref=""):
        sha = self.sha_from_prefix(prefix)
        return self.src_anchor(self.preferred_id(sha), sha, page, page_kind, locator, origin_ref)

    def anchor_by_doc(self, doc_id, page, page_kind, locator="", origin_ref=""):
        shas = self.doc2sha.get(doc_id)
        if not shas or len(shas) != 1:
            raise SystemExit(f"doc_id {doc_id} has {len(shas or [])} crawler-manifest copies")
        return self.src_anchor(doc_id, next(iter(shas)), page, page_kind, locator, origin_ref)

    def record_anchor(self, record: Path, sums: Path, locator: str, origin_ref=""):
        sha = sums_entry(sums, record)
        if sha256_file(record) != sha:
            raise SystemExit(f"{rel(record)} does not match {rel(sums)}")
        return {
            "anchor_kind": "RECORD", "doc_id": rel(record), "sha256": sha, "page": "", "page_kind": "RECORD_ROW",
            "locator": locator, "origin_ref": origin_ref, "binding_registers": rel(sums),
            "stored_path_register": rel(sums), "stored_path": rel(record),
        }

    def pe_anchor(self, pe_id, origin_ref=""):
        for f in (C12F_PE, A4_PE):
            for r in self._pe(f):
                if r["evidence_id"] == pe_id:
                    loc = f"printed p.{r['printed_page']}" if r.get("printed_page") else ""
                    return self.src_anchor(self.preferred_id(r["sha256"]), r["sha256"], r["pdf_page"], "PDF_PAGE",
                                           f"{pe_id}; {loc}".strip("; "), origin_ref)
        raise SystemExit(f"page evidence {pe_id} not found")

    _pe_cache: dict = {}

    def _pe(self, f):
        if f not in self._pe_cache:
            self._pe_cache[f] = rows(f)
        return self._pe_cache[f]

    # ---- questions
    def add(self, *, origins, priority, basis, topic, kind, question, also="", origin_priorities="",
            dedup_note="", affected="", anchors):
        assert kind in KINDS, kind
        assert priority in ("P0", "P1", "P2"), priority
        qid = f"A8-Q{len(self.q) + 1:03d}"
        if not anchors:
            raise SystemExit(f"{qid} has no anchor")
        seen, uniq = set(), []
        for a in anchors:
            key = (a["anchor_kind"], a["doc_id"], a["sha256"], a["page"], a["locator"])
            if key not in seen:
                seen.add(key)
                uniq.append(a)
        for i, a in enumerate(uniq, 1):
            a["question_id"], a["anchor_seq"] = qid, str(i)
        self.anchors[qid] = uniq
        src = [a for a in uniq if a["anchor_kind"] == "SOURCE_PAGE"]
        if src:
            _seen, _src = set(), []
            for a in src:
                if (a["doc_id"], a["sha256"], a["page"]) not in _seen:
                    _seen.add((a["doc_id"], a["sha256"], a["page"]))
                    _src.append(a)
            src_all, src = src, _src
            summ = "; ".join(
                f"{a['doc_id']} {a['sha256'][:12]} " + (f"p.{a['page']}" if a["page"] else "page not stated")
                for a in src[:6]) + (f"; +{len(src) - 6} more" if len(src) > 6 else "")
            basis_a = "SOURCE_PAGE" if all(a["page"] for a in src_all) else "SOURCE_COPY_SOME_PAGES_NOT_STATED"
        else:
            summ = "; ".join(f"{a['doc_id']} [{a['locator']}]" for a in uniq)
            basis_a = "RECORD_ONLY_NO_SOURCE_PAGE_IN_ORIGINATING_ARTEFACT"
        ws = sorted({o.split(":", 1)[0] for o, _ in origins})
        self.q.append({
            "question_id": qid, "priority": priority, "priority_basis": basis, "topic": topic,
            "question_kind": kind, "question": question, "also_asked_as": also,
            "origin_ids": ";".join(o for o, _ in origins), "origin_workstreams": ";".join(ws),
            "origin_priorities": origin_priorities, "dedup_note": dedup_note, "affected_records": affected,
            "anchor_count": str(len(uniq)), "anchor_basis": basis_a, "anchors_summary": summ,
            "legal_review_status": NLR, "adviser_answer_status": AWAIT, "adviser_answer": "", "adviser_role": "",
            "answer_date": "", "answer_reference": "",
        })
        for o, rel_ in origins:
            ws_, oid = o.split(":", 1)
            self.dedup.append({"origin_id": oid, "origin_workstream": ws_, "question_id": qid,
                               "relation": rel_, "note": dedup_note if rel_ != "PRIMARY" else ""})
        return qid


# ---------------------------------------------------------------- sources
def c12_anchors(b: Builder, qid_c12: str, xrows):
    out = []
    for x in xrows:
        if qid_c12 not in x["used_by"].split(";"):
            continue
        d = x["doc_id_or_copy"]
        page = x["stated_page"] or None
        loc = (f"para {x['paragraph']}" if x["paragraph"] else "") + f" [{x['kind']}; C12 {x['verification']}]"
        m = re.search(r"wt:([0-9a-f]{8})", d) or re.search(r"\b([0-9a-f]{8})\b", d)
        if d.startswith(("sc-", "hc-", "act-", "rules-")):
            out.append(b.anchor_by_doc(d, page, "TEXT_LAYER_PAGE_ad77758d", loc.strip(), x["excerpt_ref"]))
        elif m:
            out.append(b.anchor_by_prefix(m.group(1), page, "PDF_PAGE", loc.strip(), x["excerpt_ref"]))
        else:
            raise SystemExit(f"unresolvable C12 excerpt {x['excerpt_ref']}")
    return out


# A4 rows outside the promotion categories: anchors transcribed from the packet's `evidence` column.
# (prefix or PE id, page, page_kind, locator)
A4_MANUAL = {
    "A4-ADV-068": [("c5ef95a9", 10, "PDF_PAGE", "S.R.O. 484 printed p.300; C12 PE-1954-300-R23"),
                   ("48f52219", 41, "PAGE_AS_STATED_IN_SOURCE", "India Code compilation p.41")],
    "A4-ADV-069": [("PE:PE-1993-18-R179-R182",)],
    "A4-ADV-070": [("ca5d79c2", None, "NOT_STATED_IN_SOURCE", "S.R.O. 8(E)/2003; no C12/C13 page row for r.177")],
    "A4-ADV-071": [("be7fefc9", None, "NOT_STATED_IN_SOURCE", "S.R.O. 215/1965 (HF preserved; not eligible)")],
    "A4-ADV-072": [("4392f326", None, "NOT_STATED_IN_SOURCE", "S.R.O. 302/1987"),
                   ("31fedb68", None, "NOT_STATED_IN_SOURCE", "S.R.O. 332/1989"),
                   ("e9bf2114", 19, "PAGE_AS_STATED_IN_SOURCE", "S.R.O. 17(E)/1993 item 38 (p.19)")],
    "A4-ADV-073": [("PE:PE-1954-331-R134-R136",), ("PE:PE-1993-17-R134-136",)],
    "A4-ADV-074": [("138c1da0", None, "NOT_STATED_IN_SOURCE", "AR-034 S.R.O. 17(E)/2019 (eligible NO)")],
    "A4-ADV-075": [("c5ef95a9", 297, "PRINTED_PAGE", "1954 Gazette printed p.297 (image-checked)"),
                   ("ID:C5-SRC-P0-AR-AMD-AR-006", 142, "PRINTED_PAGE", "S.R.O. 205/1961 printed p.142 (image-checked)")],
    "A4-ADV-076": [("PE:PE-1993-14-R22",),
                   ("e9bf2114", 12, "PAGE_AS_STATED_IN_SOURCE", "r.1(2) in force on publication 06-12-1993 (p.12)")],
    "A4-ADV-078": [("1d67bddd", None, "NOT_STATED_IN_SOURCE", "S.R.O. 216/1988 (WSA-PIC-41)")],
    "A4-ADV-079": [("7a5551ba", 53, "PAGE_AS_STATED_IN_SOURCE", "Finance Act 2017 p.53"),
                   ("7a5551ba", 64, "PAGE_AS_STATED_IN_SOURCE", "Finance Act 2017 p.64"),
                   ("0c2f4e9e", 1, "PAGE_AS_STATED_IN_SOURCE", "TRA 2021 p.1"),
                   ("0c2f4e9e", 13, "PAGE_AS_STATED_IN_SOURCE", "TRA 2021 p.13"),
                   ("be619533", 1, "PAGE_AS_STATED_IN_SOURCE", "TRA 2026 p.1")],
    "A4-ADV-080": [("d4449e99", 16, "PAGE_AS_STATED_IN_SOURCE", "BNS compilation footnote p.16"),
                   ("572c7988", None, "NOT_STATED_IN_SOURCE", "BNSS compilation"),
                   ("554b2b4a", 10, "PAGE_AS_STATED_IN_SOURCE", "BSA compilation footnote p.10")],
    "A4-ADV-081": [("fa51a4b1", None, "NOT_STATED_IN_SOURCE", "Rajya Sabha papers-laid record (HF preserved)")],
}


def a4_anchors(b: Builder, row):
    pid = row["packet_id"]
    out = []
    if row["category"] == "PROMOTION_C12F":
        V = {r["verification_id"]: r for r in b._pe(C12F_V)}
        for vid in re.findall(r"C12F-V\d+", row["cross_refs"]):
            v = V[vid]
            shas = [s for s in v["copy_sha256"].split(";") if s]
            cids = [c.strip() for c in v["source_copy_id"].split("+")]
            for tok in [t.strip() for t in v["pdf_page"].split(";") if t.strip()]:
                m = re.match(r"^([A-Za-z0-9-]+):(\d+)(?:-(\d+))?$", tok)
                if m:
                    idx = next(i for i, c in enumerate(cids) if m.group(1) in c)
                    lo, hi = int(m.group(2)), int(m.group(3) or m.group(2))
                    loc = f"{m.group(1)}"
                else:
                    idx = 0
                    m2 = re.search(r"p\.(\d+)", tok) or re.match(r"^(\d+)(?:-(\d+))?$", tok)
                    if not m2:
                        raise SystemExit(f"{vid}: page token {tok!r}")
                    lo = int(m2.group(1))
                    hi = int(m2.group(2)) if m2.re.groups > 1 and m2.group(2) else lo
                    loc = tok.split(":")[0] if tok.startswith("para") else ""
                sha = shas[idx]
                for pg in range(lo, hi + 1):
                    out.append(b.src_anchor(b.preferred_id(sha), sha, pg, "PDF_PAGE", loc, vid))
    elif row["category"] == "PROMOTION_C13":
        EP = {r["proposal_id"]: r for r in b._pe(A4_EP)}
        for epid in re.findall(r"C13A4-EP\d+", row["cross_refs"]):
            for pe in [p for p in EP[epid]["page_evidence_ids"].split(";") if p]:
                out.append(b.pe_anchor(pe, epid))
    else:
        for spec in A4_MANUAL.get(pid, []):
            if spec[0].startswith("PE:"):
                out.append(b.pe_anchor(spec[0][3:], pid))
            elif spec[0].startswith("ID:"):
                sid = spec[0][3:]
                sha = next(s for (d, s) in b.R.bind if d == sid)
                out.append(b.src_anchor(b.preferred_id(sha), sha, spec[1], spec[2], spec[3], pid))
            else:
                out.append(b.anchor_by_prefix(spec[0], spec[1], spec[2], spec[3], pid))
    out.append(b.record_anchor(A4P, A4SUMS, f"packet_id={pid}", pid))
    return out


# C12 <-> A4 duplicate clusters (explicit cross-references in the A4 packet `cross_refs` column).
CLUSTERS = [
    # (C12 ids, A4 ids, priority, basis)
    (["AQ-STA-01"], ["A4-ADV-068"], "P0", "C12 P0 carried (C9 binding scale: r.23(3)); A4 CONFLICT C-01"),
    (["AQ-STA-12"], ["A4-ADV-069"], "P1", "operative text of a court-of-inquiry rule (r.182); C12 P2 raised by rubric"),
    (["AQ-STA-14"], ["A4-ADV-070"], "P1", "operative text of a court-of-inquiry rule (r.177); C12 P3 raised by rubric"),
    (["AQ-STA-13"], ["A4-ADV-071"], "P1", "operative text of a punishment rule (r.192 proviso); C12 P3 raised by rubric"),
    (["AQ-STA-15", "AQ-STA-16"], ["A4-ADV-072"], "P1", "operative text of rules on the prescribed officer (rr.193-194); C12 P2 raised by rubric"),
    (["AQ-STA-06", "AQ-STA-11"], ["A4-ADV-077"], "P1", "commencement of military statutes and rules with no commencement clause (C12 P1 carried)"),
    (["AQ-STA-10"], ["A4-ADV-079"], "P1", "commencement of AFT Act s.9A in each form; C12 P2 raised by rubric"),
    (["AQ-STA-19"], ["A4-ADV-080"], "P1", "IPC/CrPC/IEA to BNS/BNSS/BSA commencement (C12 P1 carried)"),
    (["AQ-STA-05"], ["A4-ADV-081"], "P2", "date of a CCCM Rules amendment (C12 P3 -> P2 floor)"),
    (["AQ-STA-20"], ["A4-ADV-096"], "P1", "Army Act references to the repealed IEA 1872 (C12 P1 carried)"),
]
A4_CRPC_GROUP = ["A4-ADV-090", "A4-ADV-091", "A4-ADV-092", "A4-ADV-093", "A4-ADV-094"]

# C12 single questions whose priority A8 changes, with the reason (all other C12 P0/P1/P2 carried; P3 -> P2).
C12_PRIORITY_OVERRIDE = {
    "AQ-PEN-06": ("P1", "named known-supersession case in the project acceptance checks (Dharamvir Singh 1982 Rules "
                        "vs the 2026 ruling on the 2008 Rules); affects disability-pension research records; C12 P2 raised"),
    "AQ-STA-03": ("P1", "named known-supersession case (field punishment omitted 1992) in the project acceptance "
                        "checks; operative text of r.168(2); C12 P2 raised"),
}

# A5 OVERRULES/DISAPPROVES candidate edges -> the C12 question that already asks about the same passage.
A5_EDGE_TO_C12 = {
    "GT-ba24ae19e50b1234": "AQ-HCW-01", "GT-5658e76a4b335e0d": "AQ-OVR-01", "GT-4f617d291a6063e7": "AQ-OVR-02",
    "GT-28a981e23cf66dd7": "AQ-OVR-03", "GT-ead10597f5f39d43": "AQ-OVR-04", "GT-d04ccb04c0e7e6fa": "AQ-OVR-09",
    "GT-2c7770c7657753d3": "AQ-OVR-10", "GT-d26cd0d0a8deb09a": "AQ-OVR-12", "GT-a1b1e75b33e03f5e": "AQ-OVR-13",
    "GT-60cda48a60cca1cf": "AQ-OVR-14", "GT-3ba9f9117abe58e3": "AQ-OVR-18", "GT-4f7f5f2a23de4afc": "AQ-OVR-18",
}


def c12_priority(qid, given):
    if qid in C12_PRIORITY_OVERRIDE:
        return C12_PRIORITY_OVERRIDE[qid]
    g = given.split(" ")[0]
    if g in ("P0", "P1", "P2"):
        return g, f"C12 {given} carried"
    return "P2", f"C12 {given}: A8 uses three tiers; P3 mapped to P2 (lowest)"


C12_KIND = {"HCW": "STATUS_RELATION", "PEN": "STATUS_RELATION", "OVR": "STATUS_RELATION", "STA": "TEXT_CONFLICT",
            "AUT": "SOURCE_AUTHORITY", "ROL": "ROLE_PROCESS"}
C12_KIND_EXCEPT = {"AQ-STA-06": "COMMENCEMENT_TEMPORAL", "AQ-STA-08": "COMMENCEMENT_TEMPORAL",
                   "AQ-STA-09": "COMMENCEMENT_TEMPORAL", "AQ-STA-10": "COMMENCEMENT_TEMPORAL",
                   "AQ-STA-11": "COMMENCEMENT_TEMPORAL", "AQ-STA-18": "COMMENCEMENT_TEMPORAL",
                   "AQ-STA-19": "COMMENCEMENT_TEMPORAL", "AQ-STA-20": "CROSS_REFERENCE",
                   "AQ-STA-07": "LEGAL_INTERPRETATION", "AQ-STA-02": "DOCUMENTARY_VERIFICATION",
                   "AQ-STA-04": "DOCUMENTARY_VERIFICATION", "AQ-STA-05": "DOCUMENTARY_VERIFICATION",
                   "AQ-STA-17": "DOCUMENTARY_VERIFICATION", "AQ-HCW-05": "DOCUMENTARY_VERIFICATION",
                   "AQ-PEN-03": "SOURCE_AUTHORITY", "AQ-PEN-05": "DOCUMENTARY_VERIFICATION",
                   "AQ-STA-21": "LEGAL_INTERPRETATION"}
A4_KIND = {"PROMOTION_C12F": "EVIDENCE_PROMOTION", "PROMOTION_C13": "EVIDENCE_PROMOTION", "CONFLICT": "TEXT_CONFLICT",
           "COMMENCEMENT": "COMMENCEMENT_TEMPORAL", "TEMPORAL_AXIS": "COMMENCEMENT_TEMPORAL",
           "CROSS_REFERENCE": "CROSS_REFERENCE", "ALLEGED_AMENDMENT": "TEXT_CONFLICT", "SCOPE": "LEGAL_INTERPRETATION",
           "APPLICABILITY": "LEGAL_INTERPRETATION", "RETROSPECTIVITY": "COMMENCEMENT_TEMPORAL",
           "DATE_DISPUTE": "DOCUMENTARY_VERIFICATION", "VERSION_IDENTITY": "SOURCE_AUTHORITY"}
A4_PRIORITY = {
    "PROMOTION_C12F": ("P2", "citation-level evidence promotion (no record wording change)"),
    "PROMOTION_C13": ("P2", "citation-level evidence promotion (no record wording change)"),
    "CONFLICT": ("P1", "operative text of an Army Rule in conflict between held copies"),
    "COMMENCEMENT": ("P1", "commencement of a military or criminal-law statute"),
    "CROSS_REFERENCE": ("P1", "Army Act reference to a repealed code"),
    "ALLEGED_AMENDMENT": ("P1", "operative text of an Army Rule pending an unlocated instrument"),
    "SCOPE": ("P1", "operative text of r.135 (summary/abstract of evidence)"),
    "APPLICABILITY": ("P2", "applicability exception limited to one office (r.15B)"),
    "RETROSPECTIVITY": ("P2", "historical window 1979-1988 only"),
    "DATE_DISPUTE": ("P2", "date of a CCCM Rules amendment"),
    "VERSION_IDENTITY": ("P1", "which Entitlement Rules 2008 text governs pension entitlement"),
}
A4_TEMPORAL_P2 = {"A4-ADV-089"}  # instruments not held; modelled at instrument level only


def build_c12_and_a4(b: Builder):
    c12 = rows(C12Q)
    x = rows(C12X)
    a4 = {r["packet_id"]: r for r in rows(A4P)}
    c12by = {r["id"]: r for r in c12}
    clustered_c12 = {i for c in CLUSTERS for i in c[0]}
    clustered_a4 = {i for c in CLUSTERS for i in c[1]} | set(A4_CRPC_GROUP)

    def c12_anchor_set(cid):
        an = c12_anchors(b, cid, x)
        an.append(b.record_anchor(C12Q, C12SUMS, f"id={cid}", cid))
        return an

    # A6 F07 (human spot-check before the legal gate) duplicates AQ-ROL-03 (who confirms AI page readings).
    a6rev = {r["id"]: r for r in rows(A6REV)}
    a5edges = {}
    with gzip.open(A5EDGES, "rt", encoding="utf-8") as fh:
        for line in fh:
            e = json.loads(line)
            if e["edge_id"] in A5_EDGE_TO_C12:
                a5edges[e["edge_id"]] = e
    if set(a5edges) != set(A5_EDGE_TO_C12):
        raise SystemExit("A5 edge ids changed")

    for r in c12:
        cid = r["id"]
        if cid in clustered_c12:
            cl = next(c for c in CLUSTERS if cid in c[0])
            if cid != cl[0][0]:
                continue
            c12ids, a4ids, pri, basis = cl
            an, also, aff = [], [], []
            for i in c12ids:
                an += c12_anchor_set(i)
                if i != c12ids[0]:
                    also.append(f"[C12 {i}] {c12by[i]['question']}")
                aff.append(c12by[i]["affected_records"])
            for a in a4ids:
                an += a4_anchors(b, a4[a])
                also.append(f"[A4 {a}] {a4[a]['exact_question']}")
                aff.append(a4[a]["affected_records"])
            kind = C12_KIND_EXCEPT.get(c12ids[0], C12_KIND[c12ids[0].split("-")[1]])
            b.add(origins=[(f"C12:{c12ids[0]}", "PRIMARY")] + [(f"C12:{i}", "MERGED_DUPLICATE") for i in c12ids[1:]]
                  + [(f"A4:{a}", "MERGED_DUPLICATE") for a in a4ids],
                  priority=pri, basis=basis, topic=f"{r['topic']} | A4 {a4[a4ids[0]]['subject']}", kind=kind,
                  question=r["question"], also=" || ".join(also),
                  origin_priorities="; ".join([f"C12 {i}={c12by[i]['priority']}" for i in c12ids] + [f"A4 {a}=none stated" for a in a4ids]),
                  dedup_note="same question raised in C12 and A4 (A4 cross_refs cites the C12 id)",
                  affected="; ".join(s for s in aff if s), anchors=an)
            continue
        pri, basis = c12_priority(cid, r["priority"])
        origins = [(f"C12:{cid}", "PRIMARY")]
        an = c12_anchor_set(cid)
        also, note = [], ""
        edges = [eid for eid, t in A5_EDGE_TO_C12.items() if t == cid]
        for eid in sorted(edges):
            e = a5edges[eid]
            ev = e["evidence"]
            an.append(b.src_anchor(ev["doc_id"], ev["source_copy_sha256"], ev["page"], "TEXT_LAYER_PAGE_ad77758d",
                                   f"A5 {e['edge_type']} candidate", eid))
            origins.append((f"A5:{eid}", "MERGED_DUPLICATE"))
            note = "A5 candidate edge(s) on the same page/passage merged; A5 README: every OVERRULES/DISAPPROVES candidate needs a human legal adviser"
        if cid == "AQ-ROL-03":
            f7 = a6rev["F07"]
            also.append(f"[A6 review F07] {f7['requested_action']}")
            origins.append(("A6:review_c13_a6_1b05490f/F07", "MERGED_DUPLICATE"))
            an.append(b.record_anchor(A6REG, A6SUMS, "all 21 R04_CLOSURE_RECOMMENDED families (r04_status)", "A6 F07"))
            note = "A6 F07 (human spot-check of AI transcriptions before the Document Studio 3.3 legal gate) is the same who-confirms question"
        kind = C12_KIND_EXCEPT.get(cid, C12_KIND[cid.split("-")[1]])
        b.add(origins=origins, priority=pri, basis=basis, topic=r["topic"], kind=kind, question=r["question"],
              also=" || ".join(also), origin_priorities=f"C12 {cid}={r['priority']}", dedup_note=note,
              affected=r["affected_records"], anchors=an)

    # A4 rows not in a cluster
    for pid, r in a4.items():
        if pid in clustered_a4:
            if pid == A4_CRPC_GROUP[0]:
                an, secs = [], []
                for g in A4_CRPC_GROUP:
                    an += a4_anchors(b, a4[g])
                    secs.append(a4[g]["subject"].split(" ->")[0])
                b.add(origins=[(f"A4:{A4_CRPC_GROUP[0]}", "PRIMARY")] + [(f"A4:{g}", "MERGED_DUPLICATE") for g in A4_CRPC_GROUP[1:]],
                      priority="P1", basis="Army Act reference to a repealed code (CrPC 1973); related to C12 AQ-STA-19 limb 2",
                      topic="CROSS_REFERENCE | Army Act references to CrPC 1973 (" + ", ".join(secs) + ")",
                      kind="CROSS_REFERENCE",
                      question=r["exact_question"] + " (asked identically for AA " + ", ".join(secs) + ")",
                      also="", origin_priorities="A4 none stated",
                      dedup_note="five A4 rows ask the identical question for different sections; merged (sections listed)",
                      affected="; ".join(a4[g]["affected_records"] for g in A4_CRPC_GROUP), anchors=an)
            continue
        cat = r["category"]
        pri, basis = A4_PRIORITY.get(cat, ("P2", ""))
        if cat == "TEMPORAL_AXIS":
            pri, basis = (("P2", "temporal axis for instruments not held (instrument level only)") if pid in A4_TEMPORAL_P2
                          else ("P1", "which date selects the governing version of a military or criminal-law provision"))
        b.add(origins=[(f"A4:{pid}", "PRIMARY")], priority=pri, basis=basis, topic=f"{cat} | {r['subject']}",
              kind=A4_KIND[cat], question=r["exact_question"], origin_priorities="A4 none stated",
              affected=r["affected_records"], anchors=a4_anchors(b, r))


def build_a6(b: Builder):
    reg = {r["form_id"]: r for r in rows(A6REG)}
    r04 = {r["form_family_id"]: r for r in rows(A6R04)}

    def ra(fid, what="row"):
        return b.record_anchor(A6REG, A6SUMS, f"form_id={fid}", f"A6 {fid}")

    def pg(prefix, page, loc):
        return b.anchor_by_prefix(prefix, page, "PDF_PAGE", loc, "A6")

    ar41 = sorted(f for f, r in reg.items() if "AR 4(1) not determined" in r["outstanding_uncertainties"])
    items = [
        dict(o="A6:FF-AR54-APPIII-P1D-CHAR", p="P1",
             basis="the only R04 family still deferred (blocks full R04 closure); field list otherwise MML-only",
             t="Forms | IAFD-905 (Appendix III Part I, statement as to character and particulars of service)",
             k="FORM_TEXT",
             q="Only para 9 of IAFD-905, as substituted by S.R.O. 17(E)/1993 item 39(a) (AR-AMD-1993 p.19), is held in an "
               "official copy; the Appendix III Part I base text is not printed in the held 1954 Gazette (p.72 passes from "
               "Appendix I to Appendix III Part II). Which official instrument is to be treated as prescribing the IAFD-905 "
               "base text, and may the 14 field rows held only from MML copies be shown at all (and if so with what label) "
               "until an official copy is held (A6-ACQ-02)?",
             a=[pg("e9bf2114", 19, "S.R.O. 17(E)/1993 item 39(a), IAFD-905 para 9"),
                pg("c5ef95a9", 72, "1954 Gazette: Appendix I ends, Appendix III Part II begins"),
                ra("FF-AR54-APPIII-P1D-CHAR")],
             aff="FF-AR54-APPIII-P1D-CHAR; R04_FAMILY_STATUS r04_disposition R04_STILL_DEFERRED"),
        dict(o="A6:FORM_REGISTER_C13/AR-4(1)", p="P1",
             basis="recorded as open for every Army Rules form family; gates any template or checklist use",
             t="Forms | Interaction of the form-prescribing rules with Army Rule 4(1)", k="LEGAL_INTERPRETATION",
             q="The A6 register records, for each Army Rules form family listed, 'Interaction between any specific rule "
               "quoted here and AR 4(1) not determined (legal review). Competent legal review required before any "
               "template or checklist use.' How does AR 4(1) bear on the use of these forms?",
             a=[ra(f) for f in ar41],
             aff=f"{len(ar41)} form families: " + ", ".join(ar41)),
        dict(o="A6:FF-AR54-APPIII-P3C", p="P2", basis="form designation conflict (documentary; CONFLICT_QUEUE)",
             t="Forms | Summons to witnesses (c): designation IAFD-919C vs IAFD-919A", k="FORM_TEXT",
             q="The S.R.O. 17(E)/1993 printing of summons form (c) reads 'IAFD-919C'; MML 2 p.303 shows 'IAFD 919 C' at the "
               "heading and 'IAFD-919A' after the signature block. Which designation is the prescribed one?",
             a=[pg("e9bf2114", 19, "S.R.O. 17(E)/1993: summons (c)"),
                b.anchor_by_prefix("db211918", 303, "PAGE_AS_STATED_IN_SOURCE", "MML 2 p.303 (as cited by A6)", "A6"),
                ra("FF-AR54-APPIII-P3C")],
             aff="FF-AR54-APPIII-P3C"),
        dict(o="A6:FF-AR54-APPIV-P1-F1+F2", p="P2", basis="heading section range conflict (CONFLICT_QUEUE)",
             t="Forms | Appendix IV Part I Forms 1 and 2: heading 'sections 83-84' vs '83 to 85'", k="FORM_TEXT",
             q="The 1954 Gazette heading of Appendix IV Part I Forms 1 and 2 prints 'sections 83-84 Army Act'; MML 2 prints "
               "'83 to 85'. No amending instrument has been identified. Which section range is the operative heading?",
             a=[pg("c5ef95a9", 75, "Appendix IV Part I Form 1"), pg("c5ef95a9", 76, "Appendix IV Part I Form 2"),
                ra("FF-AR54-APPIV-P1-F1"), ra("FF-AR54-APPIV-P1-F2")],
             aff="FF-AR54-APPIV-P1-F1; FF-AR54-APPIV-P1-F2"),
        dict(o="A6:FF-AR54-APPV-FH", p="P2", basis="mandatory-or-specimen classification of a warrant form",
             t="Forms | Appendix V warrants: 'may ... by a warrant in one of the forms' (AR 169)", k="LEGAL_INTERPRETATION",
             q="A6 records that AR 169 says 'may, if he thinks fit, by a warrant in one of the forms in Appendix V' and does "
               "not say the warrant 'shall' be in the form; the family was classified under the C12 'shall' rule (WSG-R02). "
               "Is the Appendix V form mandatory or a specimen?",
             a=[pg("c5ef95a9", 84, "Appendix V Form H"), ra("FF-AR54-APPV-FH")], aff="FF-AR54-APPV-FH"),
        dict(o="A6:FF-AR54-APPIV-P2-FD", p="P2", basis="identity of a form inferred from position (documentary)",
             t="Forms | Appendix IV Part II Form D: letter not printed", k="DOCUMENTARY_VERIFICATION",
             q="The heading on 1954 Gazette p.80 prints only 'FORM' with no letter; A6 identifies it as Form D by position "
               "(between Form C p.79 and Form E p.81), recorded as an inference. May it be registered as Form D?",
             a=[pg("c5ef95a9", 80, "heading 'FORM' (no letter)"), ra("FF-AR54-APPIV-P2-FD")], aff="FF-AR54-APPIV-P2-FD"),
        dict(o="A6:FF-AR54-APPIV-P2-FA+FE", p="P2", basis="currency of form wording after later law (no conclusion drawn)",
             t="Forms | Forms A and E refer to 'transportation'; editorial note on Form E", k="FORM_TEXT",
             q="Forms A and E as printed in 1954 refer to 'transportation'. Both MML vol 2 (AR) DOC transcriptions print after "
               "Form E: 'NOTE. -In view of IPC s. 53A(4)(b). this Form is redundant.' (editorial; not in the MML 2 PDF text; "
               "A6 notes IPC since replaced by BNS w.e.f. 01-07-2024). Are these forms, as printed, still to be presented, "
               "and with what status label?",
             a=[pg("c5ef95a9", 77, "Form A"), pg("c5ef95a9", 81, "Form E"), ra("FF-AR54-APPIV-P2-FA"),
                ra("FF-AR54-APPIV-P2-FE")], aff="FF-AR54-APPIV-P2-FA; FF-AR54-APPIV-P2-FE"),
        dict(o="A6:FF-AR54-APPIII-P2", p="P2", basis="field-set difference official vs MML (documentary/legal)",
             t="Forms | IAFD-901 summary-trial form: 'Findings' column absent in 1954 Gazette", k="FORM_TEXT",
             q="The 1954 Gazette page image of IAFD-901 prints 8 numbered columns and no 'Findings' column; MML 2 prints a "
               "ninth column 'Findings' and different headings ('Name of witnesses', 'Punishments'). Which field set is "
               "prescribed, and does an amending instrument add the column?",
             a=[pg("c5ef95a9", 72, "IAFD-901 table"), pg("c5ef95a9", 73, "IAFD-901 column instructions"),
                ra("FF-AR54-APPIII-P2")], aff="FF-AR54-APPIII-P2"),
        dict(o="A6:FF-AR54-APPIV-P2-FB", p="P2", basis="version applicability of a warrant form (temporal)",
             t="Forms | Form B: custody set-off paragraph inserted by S.R.O. 17(E)/1993", k="COMMENCEMENT_TEMPORAL",
             q="Form B as printed in 1954 has no custody set-off paragraph; S.R.O. 17(E)/1993 inserts it. Which version of "
               "Form B applies to a given warrant, and from what date does the inserted paragraph operate?",
             a=[pg("c5ef95a9", 78, "Form B (1954)"), pg("e9bf2114", 19, "S.R.O. 17(E)/1993 insertion"),
                ra("FF-AR54-APPIV-P2-FB")], aff="FF-AR54-APPIV-P2-FB"),
        dict(o="A6:OUTSIDE_R04/8-statutory-forms", p="P2", basis="statutory forms with no official copy held",
             t="Forms | 8 statutory forms held only as MML vol 3 transcriptions", k="SOURCE_AUTHORITY",
             q="For DPP Rules 1953 Schedule I Forms I-III, Indian Soldiers (Litigation) Forms A-D and the Indian Tolls (Army) "
               "Pass, the only copy held is an MML vol 3 transcription (UNVERIFIED_MANUAL); no official copy with the "
               "schedules is held (A6 records them OUTSIDE_R04). Which official instrument is to be treated as prescribing "
               "each, and may the MML field lists be shown pending an official copy?",
             a=[b.anchor_by_prefix("dfce01c1", p_, "PDF_PAGE", f"MML vol 3 PDF p.{p_} (C12 locator)", "A6")
                for p_ in (12, 13, 14, 207, 208, 237)]
               + [ra(f) for f in ("FF-DPPR53-S1-F1", "FF-DPPR53-S1-F2", "FF-DPPR53-S1-F3", "FF-ISLR38-FA", "FF-ISLR38-FB",
                                  "FF-ISLR38-FC", "FF-ISLR38-FD", "FF-ITR42-PASS")],
             aff="FF-DPPR53-S1-F1..F3; FF-ISLR38-FA..FD; FF-ITR42-PASS"),
        dict(o="A6:FF-AR54-APPIII-MOCERT", p="P2", basis="whether a printed certificate is part of the rules (documentary)",
             t="Forms | Medical officer's certificate printed in MML 2 between IAFD-937 and editorial matter",
             k="SOURCE_AUTHORITY",
             q="It is not established whether the medical officer's certificate (fit/unfit to undergo trial) printed in MML 2 "
               "is part of the Army Rules appendix or an editorial insertion; it is printed between IAFD-937 and the "
               "editorial 'Arrangement of the Court Room'. Is it part of the prescribed appendix?",
             a=[pg("db211918", 272, "MML 2 PDF p.272 (C12 locator)"), ra("FF-AR54-APPIII-MOCERT")],
             aff="FF-AR54-APPIII-MOCERT"),
    ]
    assert r04["FF-AR54-APPIII-P1D-CHAR"]["r04_disposition"].startswith("R04_STILL_DEFERRED")
    for it in items:
        b.add(origins=[(it["o"], "PRIMARY")], priority=it["p"], basis=it["basis"], topic=it["t"], kind=it["k"],
              question=it["q"], origin_priorities="A6 none stated", affected=it["aff"], anchors=it["a"])


def build_a5_scnum(b: Builder):
    scn = rows(A5SCN)
    pic = {}
    for r in rows(A5PIC):
        pic.setdefault(r["doc_id"], []).append(r["pdf_page"])
    an = []
    for r in scn:
        loc = f"basis={r['text_layer'] or ''}; page_image_check={'yes' if r['page_image_check'] else 'no'}"
        pages = [r["anchor_page"]] if r["anchor_page"] else pic.get(r["doc_id"], [])
        if not pages:
            an.append(b.src_anchor(r["doc_id"], r["sha256"], None, "NOT_STATED_IN_SOURCE",
                                   loc + "; anchor_page empty in A5 record", r["judgment_id"]))
        for pg_ in pages:
            an.append(b.src_anchor(r["doc_id"], r["sha256"], pg_, "PDF_PAGE",
                                   loc + ("" if r["anchor_page"] else "; page from PAGE_IMAGE_CHECKS_C13.csv"),
                                   r["judgment_id"]))
    an.append(b.record_anchor(A5SCN, A5SUMS, "all 99 rows", "A5 scnum"))
    n_img = sum(1 for r in scn if r["page_image_check"])
    b.add(origins=[("A5:SCNUM_RECONFIRMATION_C13/99", "PRIMARY")], priority="P2",
          basis="metadata (case numbers) only; no evidence or authentication status is promoted",
          topic="SC case numbers | 99 staged corrections reconfirmed by A5 (overlay C13-v1)",
          kind="DOCUMENTARY_VERIFICATION",
          question=f"A5 reconfirmed all 99 staged Supreme Court case-number corrections (1,747 numbers) against the PDF "
                   f"bytes: 81 by the text layer and {n_img} by an AI page-image reading. The check is a presence check, "
                   f"not a completeness check (A5 errata F07). May a human reviewer confirm the overlay values (the "
                   f"{n_img} page-image readings first) so that the metadata overlay can be relied on?",
          origin_priorities="A5 none stated",
          dedup_note="", affected="SC_CASE_NUMBER_OVERLAY_C13.jsonl (99 records)", anchors=an)
    c11 = [r for r in rows(C11SCN) if r["application_status"] == "APPLY_CANDIDATE_UNREVIEWED_CONFIRMED"]
    an = [b.src_anchor(r["doc_id"], r["sha256"], None, "NOT_STATED_IN_SOURCE",
                       f"parser value {r['proposed_value'][:60]}", r["judgment_id"]) for r in c11]
    b.add(origins=[("A5:C11_SC_CASE_NUMBER_REVIEWED_STATUS/266", "PRIMARY")], priority="P2",
          basis="metadata (case numbers) only; not read or applied by A5",
          topic=f"SC case numbers | {len(c11)} parser-confirmed candidates never reviewed",
          kind="DOCUMENTARY_VERIFICATION",
          question=f"{len(c11)} Supreme Court case-number candidates classified by the C11 parser as confirmed from source "
                   f"were never sampled for review and were not read or applied by A5 "
                   f"(status PROPOSAL_NOT_APPLIED_OWNER_APPROVAL_REQUIRED). Should they be reviewed (in full or by sample) "
                   f"before any is applied? The page of each number is not stated in the source register.",
          origin_priorities="A5 none stated", affected=f"{len(c11)} C11 SC_CASE_NUMBER_REVIEWED_STATUS rows",
          anchors=an)
    return len(c11)


def build_a1(b: Builder):
    rr = rows(A1RR)
    ing = {r["doc_id"]: r for r in rows(A1ING)}
    six = [r for r in rr if ing[r["doc_id"]]["action"] == "ALREADY_INGESTED_C12_MANUAL_REVIEW_REQUIRED"]
    sixids = {r["doc_id"] for r in six}
    rest = [r for r in rr if r["doc_id"] not in sixids and r["state"] in ("CLASSIFICATION_UNCERTAIN", "MANUAL_REVIEW_REQUIRED")]
    for grp, lst in (("MANUAL_REVIEW", six), ("UNCERTAIN", rest)):
        for r in lst:
            act = ing[r["doc_id"]]["action"]
            q = (f"A1's relevance state machine placed {r['doc_id']} ({r['court']}) at {r['state']} "
                 f"(ingestion action {act}; keywords: {r['keywords'] or 'none'}; context families: "
                 f"{r['second_check_families'] or 'none'}). Is this judgment within the corpus scope (Indian military "
                 f"law: armed-forces service, court-martial, AFT, pension) so that it should be "
                 + ("kept" if act.startswith("ALREADY_INGESTED") or act.startswith("IN_CORPUS") else "ingested")
                 + ", or outside it?")
            an = [b.src_anchor(r["doc_id"], r["sha256"], 1, "COVER_PAGE_WHOLE_DOCUMENT",
                               "whole-document relevance question; cover page cited for title and parties",
                               f"A1 {r['group']}"),
                  b.record_anchor(A1RR, A1SUMS, f"doc_id={r['doc_id']}", "A1 RELEVANCE_RERUN")]
            b.add(origins=[(f"A1:{grp}/{r['doc_id']}", "PRIMARY")], priority="P2",
                  basis="relevance-scope decision; no document is deleted pending review",
                  topic=f"Relevance scope | A1 {grp} | {r['group']}", kind="RELEVANCE_SCOPE", question=q,
                  origin_priorities="A1 none stated", affected=r["doc_id"], anchors=an)
    return len(six), len(rest)


def a7_legal_questions():
    """A7 dispositions record acquisition, TLS and CI items only. Return the scan result for BUILD_INFO."""
    text = A7DISP.read_text(encoding="utf-8")
    hits = [ln.strip()[:120] for ln in text.splitlines() if re.search(r"\blegal\b|adviser", ln, re.I)]
    return {"file": rel(A7DISP), "sha256": sha256_file(A7DISP), "lines_mentioning_legal_or_adviser": hits,
            "legal_questions_found": 0,
            "note": "F01-F16 and the PR #7/#8/#9/#17/#23 dispositions concern crawler configuration, TLS, CI and "
                    "acquisition scope; they are owner/technical decisions (see C13-A9 OWNER_DECISIONS_C13.md), not "
                    "legal-adviser questions. F09 (two pins resolve to Navy Act S.R.O.s) is documentary identity, "
                    "already recorded by A7."}


# ---------------------------------------------------------------- output
def to_csv(cols, recs):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in recs:
        w.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue()


def brief(b: Builder, info) -> str:
    q = b.q
    cnt = {p: sum(1 for x in q if x["priority"] == p) for p in ("P0", "P1", "P2")}
    L = []
    L.append("# Mimamsa Cycle 13: consolidated legal-adviser package (A8)\n")
    L.append("**PREPARED BY AUTOMATED AGENTS. EVERY QUESTION IS NOT LEGALLY REVIEWED.** This package draws no legal "
             "conclusion, changes no record, status, edge or register, and invents no citation. Each question is one "
             "the Cycle 12 or Cycle 13 workstreams already raised. Readings of source pages were made by AI agents and "
             "are not human-confirmed. AUTH-LEDGER stays at version 0.\n")
    L.append("Restricted material RM-001 (see `config/restricted_material.json`) is excluded from every question, "
             "anchor and file in this package. It is referred to here by its restriction id only.\n")
    L.append("## 1. How to use this package\n")
    L.append("- `outputs/ADVISER_QUESTIONS_C13.csv` is the register: one row per de-duplicated question. Record your "
             "answer in the columns `adviser_answer_status` (AWAITING_ADVISER, ANSWERED, DEFERRED_BY_ADVISER or "
             "WITHDRAWN), `adviser_answer`, `adviser_role`, `answer_date` and `answer_reference`. Every row starts as "
             "`AWAITING_ADVISER`, with `legal_review_status` = `NOT LEGALLY REVIEWED`.")
    L.append("- `outputs/ADVISER_ANCHORS_C13.csv` gives the exact source anchors of each question: `doc_id`, the "
             "sha256 of the held copy, and the page. `page_kind` says which page numbering is meant "
             "(`TEXT_LAYER_PAGE_ad77758d` is the `[[page N]]` marker in `data/text/<doc_id>.txt` at raw-data commit "
             "ad77758d; `PDF_PAGE` is the PDF page of the copy; `PRINTED_PAGE` is the page number printed on it; "
             "`PAGE_AS_STATED_IN_SOURCE` is a bare 'p.N' in the originating artefact; `NOT_STATED_IN_SOURCE` means the "
             "artefact gives no page). `RECORD` anchors point to the originating audit row, hash-pinned to that "
             "workstream's SHA256SUMS. Every anchor resolves to a register that binds the doc_id to the sha256 and "
             "records a stored path (`binding_registers`, `stored_path`).")
    L.append("- `outputs/DEDUP_MAP_C13.csv` maps every originating question id to the A8 question that carries it.")
    L.append("- Applying any answer is a separate, reviewed change with owner approval. Do not edit this package to "
             "record decisions other than in the status columns of the register.\n")
    L.append("## 2. Priorities\n")
    L.append("Priorities are a triage order by operational impact, set by the coordinator; the adviser sets the final "
             "priority. Originating priorities are kept in `origin_priorities`.\n")
    L.append("| Priority | Rule | Questions |\n| --- | --- | ---: |")
    for p in ("P0", "P1", "P2"):
        L.append(f"| {p} | {PRIORITY_RUBRIC[p]} | {cnt[p]} |")
    L.append(f"| **Total** | | **{len(q)}** |\n")
    L.append("## 3. Sources and de-duplication\n")
    L.append("| Source | Origin items | Carried in |\n| --- | ---: | --- |")
    for k, v in info["origin_counts"].items():
        L.append(f"| {k} | {v} | see DEDUP_MAP_C13.csv |")
    L.append("")
    L.append(f"{info['merged_duplicates']} origin items were merged into another question because they ask the same "
             f"thing (C12/A4 pairs that cross-reference each other, five identical A4 CrPC cross-reference rows, "
             f"12 A5 overruling/disapproval candidates on passages C12 already asks about, and A6 review F07, which is "
             f"the C12 'who confirms AI page readings' question). A7's dispositions contain no legal question "
             f"(`BUILD_INFO.json` `a7_scan`).\n")
    L.append("## 4. Questions by priority\n")
    for p in ("P0", "P1", "P2"):
        sub = [x for x in q if x["priority"] == p]
        L.append(f"### {p} ({len(sub)})\n")
        if p == "P2":
            groups = {}
            for x in sub:
                groups.setdefault(x["topic"].split(" | ")[0], []).append(x)
            L.append("| Group | Questions | Ids |\n| --- | ---: | --- |")
            for g, xs in groups.items():
                ids = [x["question_id"] for x in xs]
                shown = ", ".join(ids) if len(ids) <= 10 else f"{ids[0]} to {ids[-1]} (all {len(ids)} in this group are P2)"
                L.append(f"| {g} | {len(xs)} | {shown} |")
            L.append("")
            L.append("P2 questions are listed in full in the CSV. Selected P2 questions with source page anchors:\n")
            sub = [x for x in sub if not x["question_kind"] in ("EVIDENCE_PROMOTION", "RELEVANCE_SCOPE")][:40]
        for x in sub:
            L.append(f"**{x['question_id']}** ({x['question_kind']}; from {x['origin_ids'].replace(';', ', ')})  ")
            L.append(f"*{x['topic']}*  ")
            qq = x["question"] if len(x["question"]) < 900 else x["question"][:900] + " [...] (full text in the CSV)"
            L.append(f"{qq}  ")
            L.append(f"Anchors ({x['anchor_count']}): {x['anchors_summary']}  ")
            L.append(f"Status: {NLR}; adviser answer: {AWAIT}\n")
    L.append("## 5. Limits\n")
    L.append("- AI readings only; no human has confirmed any page reading or excerpt in this package.")
    L.append("- A8 phrased the A6, A5 case-number and A1 relevance questions from what those artefacts record as open. "
             "All other question text is verbatim from the originating artefact.")
    L.append("- Some anchors carry no page because the originating artefact gives none (`NOT_STATED_IN_SOURCE`); they are "
             "listed so the adviser can see which copy the question concerns.")
    L.append("- The C12 package's excerpt checks are not repeated here; see `C12-CONSOLIDATION/adviser_package/"
             "EXCERPT_VERIFICATION.csv`.")
    L.append(f"\nBuilt by `tools/build_adviser_c13.py` ({VERSION}); validated by `tools/validate_adviser_c13.py`.\n")
    return "\n".join(L)


def build():
    b = Builder()
    build_c12_and_a4(b)
    build_a6(b)
    n266 = build_a5_scnum(b)
    n6, nunc = build_a1(b)
    # Identical template wording is allowed only where the passage differs (different excerpt/lead): record it.
    groups = {}
    for x in b.q:
        groups.setdefault(norm(x["question"]), []).append(x)
    for xs in groups.values():
        if len(xs) > 1:
            for x in xs:
                others = [y["question_id"] for y in xs if y is not x]
                refs = sorted({a["origin_ref"] for a in b.anchors[x["question_id"]] if a["anchor_kind"] == "SOURCE_PAGE"})
                note = (f"same template wording as {', '.join(others)} but a different passage or target "
                        f"(source anchors {', '.join(refs)}); not merged")
                x["dedup_note"] = (x["dedup_note"] + " | " if x["dedup_note"] else "") + note
    oc = {}
    for d in b.dedup:
        key = {"C12": "C12 adviser package (59)", "A4": "A4 adviser packet (96)", "A6": "A6 forms (register, README, review F07)",
               "A5": "A5 treatment candidates and case numbers", "A1": "A1 MANUAL_REVIEW (6) and UNCERTAIN queue"}[d["origin_workstream"]]
        oc[key] = oc.get(key, 0) + 1
    inputs = [C12Q, C12X, C12SUMS, A4P, A4SUMS, C12F_V, C12F_PE, A4_EP, A4_PE, A6REG, A6R04, A6SUMS, A6REV, A5EDGES,
              A5SCN, A5PIC, A5SUMS, C11SCN, A1RR, A1ING, A1SUMS, A7DISP]
    info = {
        "version": VERSION,
        "status": NLR,
        "questions": len(b.q),
        "by_priority": {p: sum(1 for x in b.q if x["priority"] == p) for p in ("P0", "P1", "P2")},
        "by_kind": {k: sum(1 for x in b.q if x["question_kind"] == k) for k in sorted(KINDS)},
        "anchors": sum(len(v) for v in b.anchors.values()),
        "source_page_anchors": sum(1 for v in b.anchors.values() for a in v if a["anchor_kind"] == "SOURCE_PAGE"),
        "record_anchors": sum(1 for v in b.anchors.values() for a in v if a["anchor_kind"] == "RECORD"),
        "origin_counts": oc,
        "merged_duplicates": sum(1 for d in b.dedup if d["relation"] == "MERGED_DUPLICATE"),
        "a1": {"manual_review": n6, "uncertain_and_other_manual_review_state": nunc},
        "a5_unreviewed_case_numbers": n266,
        "a7_scan": a7_legal_questions(),
        "rm001_excluded": "RM-001 (config/restricted_material.json): no anchor, question or output references it",
        "inputs_sha256": {rel(p): sha256_file(p) for p in inputs},
        "registers_sha256": {k: v for k, v in b.R.file_sha.items()},
    }
    q_csv = to_csv(Q_COLS, b.q)
    a_csv = to_csv(A_COLS, [a for qid in sorted(b.anchors) for a in b.anchors[qid]])
    d_csv = to_csv(D_COLS, b.dedup)
    files = {
        "ADVISER_QUESTIONS_C13.csv": q_csv,
        "ADVISER_ANCHORS_C13.csv": a_csv,
        "DEDUP_MAP_C13.csv": d_csv,
        "ADVISER_BRIEF_C13.md": brief(b, info),
        "BUILD_INFO.json": json.dumps(info, indent=1, sort_keys=True) + "\n",
    }
    for name, text in files.items():
        if RM001_SHA in text or RM001_SHA[:8] in text or RM001_DOC in text:
            raise SystemExit(f"RM-001 reference in {name}")
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = build()
    if a.check:
        bad = [n for n, t in files.items() if not (OUT / n).exists() or (OUT / n).read_text(encoding="utf-8") != t]
        print("CHECK " + ("OK" if not bad else "FAILED: " + ", ".join(bad)))
        sys.exit(1 if bad else 0)
    OUT.mkdir(parents=True, exist_ok=True)
    for n, t in files.items():
        (OUT / n).write_text(t, encoding="utf-8")
    info = json.loads(files["BUILD_INFO.json"])
    print(json.dumps({k: info[k] for k in ("questions", "by_priority", "anchors", "merged_duplicates")}))


if __name__ == "__main__":
    main()
