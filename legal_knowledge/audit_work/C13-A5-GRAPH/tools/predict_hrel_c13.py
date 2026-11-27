#!/usr/bin/env python3
"""C13-A5 GA3: frozen predictions for H-REL-C13 with the frozen treatment extractor (no tuning, no coding read).

Inputs (item pointers only): `H-REL-C13/ITEM_MAP.csv` and the identifier columns of `SAMPLE.csv` (rep_doc_id,
rep_sha256, page, judgment_key) at A0 commit f1d61f71. No coder sheet, coding, reference or review file is read.
For each item, the item's page of data/text/<rep_doc_id>.txt at ad77758d is processed (rep_sha256 must equal the
data/meta sha256): every reporter/neutral citation (C11 detector `find_citations`, parallel citations clustered as one
authority) and every case-number citation other than the judgment's own numbers is a unit; each unit is classified
with the frozen `treatment_c13.classify` and mapped onto the H-REL vocabulary (fixed below, before any scoring).
A page with no detected citation gets one NONE row. Output is the coding-sheet format that c13_score.py reads.

Recall limit (known, not tuned): citations printed only as case names are not detected.

  python -I -B predict_hrel_c13.py [--repo /home/user/c7] [--check]
The tool prints counts only; it never prints predictions.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_c13 as C  # noqa: E402
import treatment_c13 as T  # noqa: E402

A0_COMMIT = "f1d61f71"
A0 = "legal_knowledge/audit_work/C13-A0-EVAL/outputs/holdouts/H-REL-C13/"
SAMPLE_ID_COLS = ("rep_doc_id", "rep_sha256", "page", "judgment_key")
OUT = C.PKG / "freeze"
PRED_VERSION = "predict-hrel-c13/1.0.0"
FIELDS = ["item_id", "pred_id", "page", "cited_string", "cited_case_name", "target", "relation_type", "voice", "excerpt",
          "confidence", "notes"]
# Fixed mapping from the frozen A5 relation to the H-REL coding vocabulary (decided before any scoring).
REL_MAP = {"CITES": "cites", "CONSIDERS": "cites", "EXPLAINS": "cites", "FOLLOWS": "follows", "APPLIES": "applies",
           "DISTINGUISHES": "distinguishes", "OVERRULES": "overrules", "DOUBTS": "doubts"}
VOICE_MAP = {"COURT_OWN_VOICE": "court_own", "QUOTED_PASSAGE": "quoted_passage", "PARTY_SUBMISSION": "party_submission",
             "REPORTER_EDITORIAL": "editorial", "SEPARATE_OR_DISSENT_OPINION": "court_own",
             "HIGH_COURT_OVERRULING_WORDS_NOT_ROUTED": "court_own", "NO_TREATMENT_CUE": "court_own",
             "CUES_REJECTED": "unclear"}
LOW = {"DISTINGUISHES", "APPLIES", "EXPLAINS", "DOUBTS"}


def map_relation(res, court):
    rel = res["relation"]
    if rel == "DISAPPROVES":   # guide: 'overrules' = the court itself, with authority, says no longer good law
        return "overrules" if court.startswith("Supreme") and res.get("overruling_language", "").startswith("DECLARATORY") else "not_followed"
    return REL_MAP[rel]


def item_pointers():
    imap = list(csv.DictReader(io.StringIO(C.git(C.WT, "show", A0_COMMIT + ":" + A0 + "ITEM_MAP.csv").decode())))
    samp = []
    for r in csv.DictReader(io.StringIO(C.git(C.WT, "show", A0_COMMIT + ":" + A0 + "SAMPLE.csv").decode())):
        samp.append({k: r[k] for k in SAMPLE_ID_COLS})
    by = {(s["rep_sha256"], s["page"]): s for s in samp}
    items = []
    for m in imap:
        s = by[(m["rep_sha256"], m["page"])]
        assert s["judgment_key"] == m["judgment_key"]
        items.append(dict(item_id=m["item_id"], doc_id=s["rep_doc_id"], sha=m["rep_sha256"], page=int(m["page"])))
    return items, dict(item_map_sha256=C.sha256_bytes(C.git(C.WT, "show", A0_COMMIT + ":" + A0 + "ITEM_MAP.csv")),
                       sample_sha256=C.sha256_bytes(C.git(C.WT, "show", A0_COMMIT + ":" + A0 + "SAMPLE.csv")))


def own_keys(meta, t, R11):
    keys = set()
    for cn in meta.get("case_numbers") or []:
        mm = re.match(r"(.+?)/(\d+)/(\d{4})$", cn)
        if mm:
            keys.add((mm.group(2), mm.group(3)))
    first = t[:6000]
    for c in R11.find_case_numbers(first):
        p = c["key"].split("|")
        keys.add((p[2], p[3]))
    return keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=C.DEFAULT_REPO)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    R11 = T.R11
    restricted = C.Restricted()
    items, src = item_pointers()
    docs = sorted({i["doc_id"] for i in items})
    assert not any(restricted.hit(doc_id=d) for d in docs)
    tb = C.cat_blobs(a.repo, ["%s:data/text/%s.txt" % (C.TEXT_COMMIT, d) for d in docs])
    mb = C.cat_blobs(a.repo, ["%s:data/meta/%s.json" % (C.TEXT_COMMIT, d) for d in docs])
    graph = C.read_csv(T.REL / "CASE_CITATION_GRAPH.csv")
    resolved = {}
    for g in graph:
        if g["target_state"] == "RESOLVED":
            for k in g["citation_keys"].split(" || "):
                resolved[(g["source_doc_id"], k.strip())] = g["target_doc_ids"].split(";")[0].strip()
    meta_cache = {}

    def target_label(doc_id, key, raw):
        tdoc = resolved.get((doc_id, key))
        if tdoc:
            if tdoc not in meta_cache:
                b = C.cat_blobs(a.repo, ["%s:data/meta/%s.json" % (C.TEXT_COMMIT, tdoc)])
                v = list(b.values())[0]
                meta_cache[tdoc] = json.loads(v) if v else {}
            m = meta_cache[tdoc]
            nc = m.get("neutral_citation") or (m.get("number") if re.search(r"\bINSC\b", m.get("number") or "") else None)
            if nc:
                return nc
        return raw

    rows, tally, status = [], Counter(), Counter()
    for it in sorted(items, key=lambda x: x["item_id"]):
        tkey, mkey = "%s:data/text/%s.txt" % (C.TEXT_COMMIT, it["doc_id"]), "%s:data/meta/%s.json" % (C.TEXT_COMMIT, it["doc_id"])
        if tb[tkey] is None or mb[mkey] is None:
            status["NO_TEXT_OR_META"] += 1
            rows.append(dict(item_id=it["item_id"], page=it["page"], cited_string="", notes="PREDICTION_ABSTAINED:NO_TEXT"))
            continue
        meta = json.loads(mb[mkey])
        if meta.get("sha256") != it["sha"]:
            status["SHA_MISMATCH"] += 1
            rows.append(dict(item_id=it["item_id"], page=it["page"], cited_string="", notes="PREDICTION_ABSTAINED:SHA_MISMATCH"))
            continue
        t = T.collapse(tb[tkey].decode("utf-8", "replace"))
        court = meta.get("court") or meta.get("issuing_authority") or ""
        doc = R11.Doc(it["doc_id"], t, court)
        if it["page"] not in doc.page_nos:
            status["PAGE_NOT_IN_TEXT"] += 1
            rows.append(dict(item_id=it["item_id"], page=it["page"], cited_string="", notes="PREDICTION_ABSTAINED:PAGE_NOT_IN_TEXT"))
            continue
        k = doc.page_nos.index(it["page"])
        lo = doc.page_offs[k]
        hi = doc.page_offs[k + 1] if k + 1 < len(doc.page_offs) else len(t)
        own = own_keys(meta, t, R11)
        cits = R11.find_citations(t, lo, hi)
        cases = [c for c in R11.find_case_numbers(t[:hi], lo) if c["start"] < hi and tuple(c["key"].split("|")[2:4]) not in own]
        units = [cl for cl in R11.cluster(cits, t)] + [[c] for c in cases
                                                      if not any(x["start"] <= c["start"] < x["end"] for x in cits)]
        units.sort(key=lambda cl: cl[0]["start"])
        seen = {}
        page_text = t[lo:hi]
        for cl in units:
            lead = next((c for c in cl if "SCC" in c["raw"]), cl[0])
            raw = lead["raw"]
            zone = "REPORTER_EDITORIAL" if lead["start"] < doc.editorial_end else "BODY"
            res = T.classify(t, court, lead["start"], cl[-1]["end"], "OPINION_NOT_IDENTIFIED", zone, "")
            rel = map_relation(res, court)
            voice = VOICE_MAP.get(res["voice"], "unclear")
            s0, s1 = max(res["s0"], lo), min(res["s1"], hi)
            excerpt = re.sub(r"\[\[page \d+\]\]", " ", t[s0:s1]).strip()
            ukey = raw.upper()
            row = dict(item_id=it["item_id"], page=it["page"], cited_string=raw, cited_case_name="",
                       target=target_label(it["doc_id"], lead["key"], raw), relation_type=rel, voice=voice,
                       excerpt=excerpt[:600], confidence="low" if res["relation"] in LOW else ("medium" if rel != "cites" else "high"),
                       notes="a5:%s; %s" % (res["relation"], (res.get("reasons") or "")[:120]))
            if ukey in seen:     # one unit per citation on the page: keep the first typed treatment
                prev = rows[seen[ukey]]
                if prev["relation_type"] == "cites" and rel != "cites":
                    rows[seen[ukey]] = row
                continue
            seen[ukey] = len(rows)
            rows.append(row)
        if not seen:
            rows.append(dict(item_id=it["item_id"], page=it["page"], cited_string="NONE", cited_case_name="", target="",
                             relation_type="other", voice="unclear", excerpt="", confidence="high", notes="a5: no citation detected"))
            status["NONE_ROW"] += 1
        status["ITEMS_PREDICTED"] += 1
    for r in rows:
        if r.get("cited_string") not in ("", "NONE", None):
            tally[r["relation_type"]] += 1
    for n, r in enumerate(rows, 1):
        r["pred_id"] = "A5P%05d" % n
        for f in FIELDS:
            r.setdefault(f, "")
    text = C.to_csv(rows, FIELDS)
    assert not restricted.hit(text=text)
    hashes = {p: C.sha256_file(C.WT / p) for p in (
        "legal_knowledge/audit_work/C13-A5-GRAPH/tools/treatment_c13.py",
        "legal_knowledge/audit_work/C13-A5-GRAPH/tools/common_c13.py",
        "legal_knowledge/audit_work/C13-A5-GRAPH/tools/predict_hrel_c13.py",
        "legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/relations/tools/relations_c11.py")}
    manifest = dict(tool=PRED_VERSION, extractor=T.VERSION, holdout="H-REL-C13", a0_commit=A0_COMMIT, inputs=src,
                    text_commit=C.TEXT_COMMIT, items=len(items), prediction_rows=len(rows),
                    units_by_relation=dict(sorted(tally.items())), status=dict(sorted(status.items())),
                    predictions_sha256=C.sha256_bytes(text.encode()), tool_sha256=hashes,
                    c11_citation_graph_sha256=C.sha256_file(T.REL / "CASE_CITATION_GRAPH.csv"),
                    restricted_register=restricted.provenance, coding_read=False,
                    relation_map=dict(REL_MAP, DISAPPROVES="overrules (Supreme Court, declaratory) / not_followed"),
                    voice_map=VOICE_MAP)
    files = {"H-REL-C13_PREDICTIONS.csv": text, "H-REL-C13_PREDICTIONS_MANIFEST.json": C.dumps(manifest)}
    rc = C.write_or_check(files, OUT, a.check)
    if not a.check:
        print(json.dumps(dict(items=len(items), rows=len(rows), units_by_relation=manifest["units_by_relation"],
                              status=manifest["status"]), indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
