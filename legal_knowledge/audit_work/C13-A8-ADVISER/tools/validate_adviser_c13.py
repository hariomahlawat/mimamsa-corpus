"""C13-A8 validator: schema, de-duplication, anchor resolution and RM-001 exclusion.

Usage: python -I -B tools/validate_adviser_c13.py      (exit 0 = all checks pass)
Each check_* function returns a list of error strings; the unittest suite calls them one by one.
Standard library only; reads committed files only.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a8_registers import REPO, RM001_DOC, RM001_SHA, Registers, sha256_file  # noqa: E402
import build_adviser_c13 as B  # noqa: E402

OUT = B.OUT
ANSWER_STATES = {"AWAITING_ADVISER", "ANSWERED", "DEFERRED_BY_ADVISER", "WITHDRAWN"}
ANSWER_FIELDS = ("adviser_answer", "adviser_role", "answer_date", "answer_reference")
SHA = re.compile(r"^[0-9a-f]{64}$")


def load():
    def r(n):
        with open(OUT / n, encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            return rd.fieldnames, list(rd)
    return r("ADVISER_QUESTIONS_C13.csv"), r("ADVISER_ANCHORS_C13.csv"), r("DEDUP_MAP_C13.csv")


def restricted_identifiers():
    reg = json.loads((REPO / "config" / "restricted_material.json").read_text(encoding="utf-8"))
    shas, docs = {RM001_SHA}, {RM001_DOC}
    for it in reg["items"]:
        shas.add(it["source_sha256"].lower())
        shas.update(s.lower() for s in it.get("derived_sha256", []))
        docs.add(it["doc_id"])
    return shas, docs


def check_schema():
    (qc, q), (ac, a), (dc, d) = load()
    e = []
    if qc != B.Q_COLS:
        e.append(f"question columns {qc} != {B.Q_COLS}")
    if ac != B.A_COLS:
        e.append(f"anchor columns {ac} != {B.A_COLS}")
    if dc != B.D_COLS:
        e.append(f"dedup columns {dc} != {B.D_COLS}")
    ids = [x["question_id"] for x in q]
    if ids != [f"A8-Q{i:03d}" for i in range(1, len(q) + 1)]:
        e.append("question ids are not A8-Q001.. in sequence")
    acount = {}
    for x in a:
        acount[x["question_id"]] = acount.get(x["question_id"], 0) + 1
    for x in q:
        i = x["question_id"]
        if x["priority"] not in ("P0", "P1", "P2"):
            e.append(f"{i}: priority {x['priority']}")
        if x["question_kind"] not in B.KINDS:
            e.append(f"{i}: kind {x['question_kind']}")
        if not x["question"].strip() or not x["topic"].strip() or not x["priority_basis"].strip():
            e.append(f"{i}: empty question/topic/priority_basis")
        if x["legal_review_status"] != B.NLR:
            e.append(f"{i}: legal_review_status must be '{B.NLR}'")
        st = x["adviser_answer_status"]
        if st not in ANSWER_STATES:
            e.append(f"{i}: adviser_answer_status {st}")
        filled = [f for f in ANSWER_FIELDS if x[f].strip()]
        if st == "AWAITING_ADVISER" and filled:
            e.append(f"{i}: answer fields filled while AWAITING_ADVISER")
        if st == "ANSWERED" and len(filled) != len(ANSWER_FIELDS):
            e.append(f"{i}: ANSWERED without all answer fields")
        if str(acount.get(i, 0)) != x["anchor_count"] or acount.get(i, 0) < 1:
            e.append(f"{i}: anchor_count {x['anchor_count']} vs {acount.get(i, 0)}")
    for x in a:
        k = f"{x['question_id']}#{x['anchor_seq']}"
        if x["anchor_kind"] not in ("SOURCE_PAGE", "RECORD"):
            e.append(f"{k}: anchor_kind")
        if not SHA.match(x["sha256"]):
            e.append(f"{k}: sha256 not 64-hex")
        if x["page_kind"] not in B.PAGE_KINDS:
            e.append(f"{k}: page_kind {x['page_kind']}")
        if x["page"]:
            if not x["page"].isdigit() or int(x["page"]) < 1:
                e.append(f"{k}: page {x['page']}")
            if x["page_kind"] in ("NOT_STATED_IN_SOURCE", "RECORD_ROW"):
                e.append(f"{k}: page given with page_kind {x['page_kind']}")
        elif x["page_kind"] not in ("NOT_STATED_IN_SOURCE", "RECORD_ROW"):
            e.append(f"{k}: no page but page_kind {x['page_kind']}")
        if x["anchor_kind"] == "RECORD" and x["page_kind"] != "RECORD_ROW":
            e.append(f"{k}: RECORD anchor must use RECORD_ROW")
    return e


def check_dedup():
    (_, q), (_, a), (_, d) = load()
    e = []
    oids = [(x["origin_workstream"], x["origin_id"]) for x in d]
    if len(oids) != len(set(oids)):
        e.append("an origin id is mapped to more than one question")
    qids = {x["question_id"] for x in q}
    prim = {}
    for x in d:
        if x["question_id"] not in qids:
            e.append(f"dedup row points to unknown {x['question_id']}")
        if x["relation"] not in ("PRIMARY", "MERGED_DUPLICATE"):
            e.append(f"relation {x['relation']}")
        if x["relation"] == "PRIMARY":
            prim[x["question_id"]] = prim.get(x["question_id"], 0) + 1
    for x in q:
        if prim.get(x["question_id"]) != 1:
            e.append(f"{x['question_id']}: {prim.get(x['question_id'], 0)} PRIMARY origins")
        listed = x["origin_ids"].split(";")
        mapped = [f"{r['origin_workstream']}:{r['origin_id']}" for r in d if r["question_id"] == x["question_id"]]
        if sorted(listed) != sorted(mapped):
            e.append(f"{x['question_id']}: origin_ids disagree with DEDUP_MAP")
    # no two questions may ask the same thing about the same passage
    refs = {}
    for r in a:
        if r["anchor_kind"] == "SOURCE_PAGE":
            refs.setdefault(r["question_id"], set()).add((r["sha256"], r["page"], r["origin_ref"]))
    seen = {}
    for x in q:
        key = (B.norm(x["question"]), frozenset(refs.get(x["question_id"], ())))
        if key in seen:
            e.append(f"{x['question_id']} duplicates {seen[key]}")
        seen[key] = x["question_id"]
    # every originating question is carried exactly once
    c12 = {r["id"] for r in B.rows(B.C12Q)}
    a4 = {r["packet_id"] for r in B.rows(B.A4P)}
    got = {}
    for w, i in oids:
        got.setdefault(w, set()).add(i)
    if got.get("C12", set()) != c12:
        e.append(f"C12 coverage: missing {sorted(c12 - got.get('C12', set()))}")
    if got.get("A4", set()) != a4:
        e.append(f"A4 coverage: missing {sorted(a4 - got.get('A4', set()))}")
    a5_edges = {i for i in got.get("A5", set()) if i.startswith("GT-")}
    if a5_edges != set(B.A5_EDGE_TO_C12):
        e.append("A5 OVERRULES/DISAPPROVES candidates not all carried")
    a1 = {i.split("/", 1)[1] for i in got.get("A1", set())}
    ing = {r["doc_id"]: r for r in B.rows(B.A1ING)}
    want = {r["doc_id"] for r in B.rows(B.A1RR)
            if ing[r["doc_id"]]["action"] == "ALREADY_INGESTED_C12_MANUAL_REVIEW_REQUIRED"
            or r["state"] in ("CLASSIFICATION_UNCERTAIN", "MANUAL_REVIEW_REQUIRED")}
    if a1 != want:
        e.append(f"A1 coverage differs: {len(a1)} vs {len(want)}")
    if not any(i.startswith("FF-AR54-APPIII-P1D-CHAR") for i in got.get("A6", set())):
        e.append("A6 IAFD-905 question missing")
    return e


def check_anchors(R: Registers | None = None):
    (_, q), (_, a), _ = load()
    R = R or Registers()
    e = []
    for x in a:
        k = f"{x['question_id']}#{x['anchor_seq']}"
        if x["anchor_kind"] == "SOURCE_PAGE":
            try:
                regs, _ = R.resolve(x["doc_id"], x["sha256"])
            except ValueError as err:
                e.append(f"{k}: {err}")
                continue
            claimed = set(x["binding_registers"].split(";"))
            if not claimed or not claimed <= set(regs):
                e.append(f"{k}: binding_registers {claimed} not all confirmed ({regs})")
            if (x["stored_path_register"], x["stored_path"]) not in R.path.get(x["sha256"], []):
                e.append(f"{k}: stored path not in register {x['stored_path_register']}")
        else:
            p = REPO / x["doc_id"]
            sums = REPO / x["binding_registers"]
            if not p.is_file():
                e.append(f"{k}: record file {x['doc_id']} missing")
                continue
            if sha256_file(p) != x["sha256"]:
                e.append(f"{k}: record file hash changed")
            try:
                if B.sums_entry(sums, p) != x["sha256"]:
                    e.append(f"{k}: hash not the one listed in {x['binding_registers']}")
            except SystemExit as err:
                e.append(f"{k}: {err}")
    return e


def check_rm001():
    shas, docs = restricted_identifiers()
    e = []
    if RM001_SHA not in shas or RM001_DOC not in docs:
        e.append("RM-001 identifiers no longer match config/restricted_material.json")
    pkg = B.PKG
    for p in sorted(pkg.rglob("*")):
        if not p.is_file() or "tools" in p.relative_to(pkg).parts or "__pycache__" in p.parts:
            continue
        t = p.read_text(encoding="utf-8", errors="replace").lower()
        for s in shas:
            if s in t or s[:8] in t:
                e.append(f"{p.relative_to(REPO)} contains a restricted sha256 (or its prefix)")
        for d in docs:
            if d.lower() in t:
                e.append(f"{p.relative_to(REPO)} contains a restricted doc_id")
    _, (_, a), _ = load()
    for x in a:
        if x["sha256"] in shas or x["doc_id"] in docs:
            e.append(f"{x['question_id']}: anchor is restricted material")
    return e


def check_build_reproduces():
    files = B.build()
    return [f"{n} differs from a fresh build" for n, t in files.items()
            if (OUT / n).read_text(encoding="utf-8") != t]


CHECKS = [check_schema, check_dedup, check_anchors, check_rm001, check_build_reproduces]


def main():
    bad = 0
    for c in CHECKS:
        errs = c()
        print(f"{c.__name__}: {'OK' if not errs else f'{len(errs)} error(s)'}")
        for x in errs[:20]:
            print("  -", x)
        bad += bool(errs)
    print("VALIDATION " + ("OK" if not bad else "FAILED"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
