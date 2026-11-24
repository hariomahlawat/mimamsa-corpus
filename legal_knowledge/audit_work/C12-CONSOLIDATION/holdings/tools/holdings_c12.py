#!/usr/bin/env python3
"""Mimamsa C12 Workstream E (part 1): holdings-focused extraction driver.

Reads judgment text layers at a fixed git commit of the c7 repository (data/text/<doc_id>.txt with [[page N]]
markers) and writes AUTOMATED CANDIDATES only: questions of law, holdings, reasoning, obiter candidates,
operative directions, and (for audit) quoted precedent, submissions and lower-forum findings that carry legal
content. Nothing is legally verified; no item is a verified ratio; no overruling is inferred.

Commands
  run                       extract the scope set (SC DIRECT_MILITARY_LAW / MILITARY_ADMIN + held curated cases)
                            into outputs/ and write OUTPUT_SHA256SUMS and FREEZE.json
  ids --ids-file F --out-dir D
                            extract an arbitrary list of judgment_ids (one per line, '#' comments allowed)
                            into D (for blind evaluation); scope is not applied
  check                     verify tool hashes against FREEZE.json and re-extract the scope set in memory,
                            comparing every output byte-for-byte with OUTPUT_SHA256SUMS

Standard library only. Python 3.11+.
"""
import argparse
import csv
import difflib
import hashlib
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import holdings_core as core  # noqa: E402

ROOT = os.path.dirname(HERE)                                   # .../C12-CONSOLIDATION/holdings
AUDIT = os.path.dirname(os.path.dirname(ROOT))                 # .../audit_work
C10 = os.path.join(AUDIT, "C10-HF-JUDGMENTS", "outputs")
C10R = os.path.join(AUDIT, "C10-RECONCILIATION", "workstreams", "judicial")
REL = os.path.join(AUDIT, "C11-JUDICIAL-QUALITY", "relations", "outputs")
OUT = os.path.join(ROOT, "outputs")
DEF_REPO = "/home/user/c7"
DEF_COMMIT = "ad77758d"
TOOL_FILES = ["holdings_core.py", "holdings_c12.py"]
SCOPE_CLASSES = ("DIRECT_MILITARY_LAW", "MILITARY_ADMIN_SERVICE_PENSION")

INPUT_FILES = {
    "copy_register": os.path.join(C10, "HF_JUDGMENT_COPY_REGISTER.csv"),
    "metadata_audit": os.path.join(C10, "HF_JUDGMENT_METADATA_AUDIT.csv"),
    "relevance": os.path.join(C10, "HF_JUDGMENT_RELEVANCE.csv"),
    "curated_status": os.path.join(C10R, "CURATED_CASE_COPY_STATUS.csv"),
    "reconciliation": os.path.join(C10R, "JUDGMENT_RECONCILIATION.csv"),
    "statute_links": os.path.join(REL, "STATUTE_JUDGMENT_LINKS.csv"),
    "treatment_candidates": os.path.join(REL, "TREATMENT_CANDIDATES.csv"),
}

JUDGMENT_COLS = ["judgment_id", "sha256", "doc_id", "court", "scope_basis", "text_status", "body_start_page",
                 "body_start_method", "headnote_detected", "headnote_excluded_chars", "n_opinions", "opinions",
                 "n_numbered_paragraphs", "n_quote_spans", "n_sentences", "n_question_of_law", "n_holding",
                 "n_reasoning", "n_obiter_candidate", "n_operative_direction", "n_quoted_precedent", "n_submission",
                 "n_lower_court_finding", "shared_text_judgment_ids", "extractor", "status"]
SCOPE_COLS = ["judgment_id", "sha256", "court", "scope_basis", "relevance_class", "curated_case_ids", "text_doc", "in_corpus_text"]
CURATED_COLS = ["case_id", "title", "held_status_c10", "linked_groups", "judgment_ids_in_corpus", "disposition"]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tool_hashes():
    return {fn: sha256_file(os.path.join(HERE, fn)) for fn in TOOL_FILES}


def read_csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ corpus
def load_corpus(repo, commit):
    reg = read_csv(INPUT_FILES["copy_register"])
    audit = read_csv(INPUT_FILES["metadata_audit"])
    by_sha = {}
    for r in audit:
        by_sha.setdefault(r["sha256"], []).append(r)
    names = set()
    try:
        ls = subprocess.run(["git", "-C", repo, "ls-tree", "--name-only", commit, "data/text/"],
                            capture_output=True, text=True, check=True).stdout.split()
        names = set(ls)
    except Exception:
        names = set()
    J = {}
    for r in reg:
        sha, jid = r["sha256"], r["judgment_id"]
        if not jid:
            continue
        recs = sorted(by_sha.get(sha, []), key=lambda x: x["doc_id"])
        doc_ids = [x["doc_id"] for x in recs]
        text_doc = next((x for x in doc_ids if "data/text/%s.txt" % x in names), "")
        J[jid] = {"judgment_id": jid, "sha256": sha, "doc_ids": doc_ids, "text_doc": text_doc,
                  "court": recs[0]["court"] if recs else ""}
    return J


class TextStore:
    """Reads blobs from git with one `git cat-file --batch` process."""

    def __init__(self, repo, commit):
        self.repo, self.commit, self.p = repo, commit, None

    def get(self, doc_id):
        if not doc_id:
            return None, ""
        if self.p is None:
            self.p = subprocess.Popen(["git", "-C", self.repo, "cat-file", "--batch"], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE)
        self.p.stdin.write(("%s:data/text/%s.txt\n" % (self.commit, doc_id)).encode())
        self.p.stdin.flush()
        header = self.p.stdout.readline().decode().split()
        if len(header) < 3 or header[1] == "missing":
            return None, ""
        size = int(header[2])
        data = self.p.stdout.read(size)
        self.p.stdout.read(1)
        return data.decode("utf-8", errors="replace"), header[0]

    def close(self):
        if self.p:
            self.p.stdin.close()
            self.p.wait()
            self.p = None


# ------------------------------------------------------------------ scope
def build_scope(J):
    rel = read_csv(INPUT_FILES["relevance"])
    relc = {r["judgment_id"]: r["relevance_class"] for r in rel}
    scope = {}
    for r in rel:
        if "supreme" in r["court"].lower() and r["relevance_class"] in SCOPE_CLASSES:
            scope.setdefault(r["judgment_id"], set()).add("SC_" + r["relevance_class"])
    groups = {}
    for r in read_csv(INPUT_FILES["reconciliation"]):
        groups.setdefault(r["group_id"], []).append(r["copy_sha256"])
    by_sha = {v["sha256"]: k for k, v in J.items()}
    curated_rows = []
    cur_ids = {}
    for r in read_csv(INPUT_FILES["curated_status"]):
        js = []
        if r["held_status_c10"] == "HELD":
            for g in [x.strip() for x in r["linked_groups"].split(";") if x.strip()]:
                js += [by_sha[s] for s in groups.get(g, []) if s in by_sha]
        js = sorted(set(js))
        for j in js:
            scope.setdefault(j, set()).add("CURATED_CASE_HELD")
            cur_ids.setdefault(j, []).append(r["case_id"])
        if r["held_status_c10"] != "HELD":
            disp = "NOT_IN_SCOPE_NOT_HELD (%s)" % r["held_status_c10"].split(" (")[0]
        elif not js:
            disp = "HELD_BUT_NO_JUDGMENT_ID_IN_CORPUS_REGISTER"
        elif not any(J[j]["text_doc"] for j in js):
            disp = "HELD_JUDGMENT_ID_WITHOUT_TEXT_LAYER_AT_COMMIT"
        else:
            disp = "IN_SCOPE"
        curated_rows.append({"case_id": r["case_id"], "title": r["title"], "held_status_c10": r["held_status_c10"],
                             "linked_groups": r["linked_groups"], "judgment_ids_in_corpus": ";".join(js), "disposition": disp})
    rows = []
    for j in sorted(scope):
        info = J.get(j, {})
        rows.append({"judgment_id": j, "sha256": info.get("sha256", ""), "court": info.get("court", ""),
                     "scope_basis": ";".join(sorted(scope[j])), "relevance_class": relc.get(j, ""),
                     "curated_case_ids": ";".join(sorted(cur_ids.get(j, []))), "text_doc": info.get("text_doc", ""),
                     "in_corpus_text": "YES" if info.get("text_doc") else "NO"})
    return rows, curated_rows


# ------------------------------------------------------------------ links and treatment
def load_links():
    links, treat = {}, {}
    for r in read_csv(INPUT_FILES["statute_links"]):
        links.setdefault(r["judgment_id"], []).append(r)
    for r in read_csv(INPUT_FILES["treatment_candidates"]):
        if r["proposed_relation"] or r["status"] in ("DOCUMENTARY_CHECK_REQUIRED", "LEGAL_INTERPRETATION_ADVISER_REVIEW"):
            treat.setdefault(r["source_judgment_id"], []).append(r)
    return links, treat


def _overlap(a, b, need=30):
    a, b = core.norm_alnum(a), core.norm_alnum(b)
    if len(a) < need or len(b) < need:
        return False
    m = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return m.size >= need


def _pages(it):
    p0, p1 = it["page"], it["page_end"]
    if p0 is None:
        return set()
    return set(range(p0, (p1 if p1 is not None else p0) + 1))


def attach(items, links, treat):
    for it in items:
        pg = _pages(it)
        ex = it["excerpt_clean"]
        own = set()
        for st in it["statutes"]:
            if st["instrument_id"] and st["provision"]:
                own.add("%s:%s" % (st["instrument_id"], re.sub(r"\(.*$", "", st["provision"])))
        for r in links:
            lps = set(int(x) for x in re.split(r"[;,\s]+", r["pages"] or "") if x.isdigit())
            lp = int(r["page"]) if (r["page"] or "").isdigit() else None
            basis = None
            if r["provision_id"] and re.sub(r"\(.*$", "", r["provision_id"]) in own and (pg & lps):
                basis = "PROVISION_IN_SENTENCE_AND_MENTIONED_ON_SAME_PAGE"
            elif lp in pg and _overlap(ex, r["excerpt"]):
                basis = "CUE_PAGE_AND_TEXT_OVERLAP"
            if basis:
                it["statute_links"].append({"link_id": r["link_id"], "instrument_id": r["instrument_id"] or None,
                                            "provision_id": r["provision_id"] or None, "relationship": r["relationship"],
                                            "link_status": r["status"], "version_status": r["version_status"] or None,
                                            "match_basis": basis})
        for r in treat:
            try:
                cp = int(r["cue_page"] or r["citation_page"])
            except ValueError:
                continue
            if cp in pg and _overlap(ex, r["excerpt"]):
                it["treatment"].append({
                    "candidate_id": r["candidate_id"], "edge_id": r["edge_id"], "cue_relation": r["cue_relation"],
                    "proposed_relation": r["proposed_relation"] or None, "cue_text": r["cue_text"],
                    "cited_string": r["cited_string"], "target_doc_ids": r["target_doc_ids"] or None,
                    "target_title": r["target_title"] or None, "relation_status": r["status"],
                    "binding_status": r["binding_status"] or None, "attribution": r["attribution"],
                    "policy": "carried unchanged from C11 relations; no overruling inferred by this tool"})
        it["statute_links"].sort(key=lambda x: x["link_id"])
        it["treatment"].sort(key=lambda x: x["candidate_id"])


# ------------------------------------------------------------------ extraction
def extract(ids, J, scope_basis, repo, commit):
    links, treat = load_links()
    store = TextStore(repo, commit)
    by_sha = {}
    for j, v in J.items():
        by_sha.setdefault(v["sha256"], []).append(j)
    items_all, jrows = [], []
    blob_owner = {}
    try:
        for jid in ids:
            info = J.get(jid)
            row = {c: "" for c in JUDGMENT_COLS}
            row.update({"judgment_id": jid, "scope_basis": scope_basis.get(jid, "REQUESTED_ID"),
                        "extractor": core.VERSION, "status": core.STATUS})
            if not info:
                row["text_status"] = "UNKNOWN_JUDGMENT_ID"
                jrows.append(row)
                continue
            row.update({"sha256": info["sha256"], "doc_id": info["text_doc"], "court": info["court"]})
            text, blob = store.get(info["text_doc"])
            if not text:
                row["text_status"] = "NO_TEXT_LAYER_AT_COMMIT"
                jrows.append(row)
                continue
            row["text_status"] = "TEXT_LAYER_READ"
            blob_owner.setdefault(blob, []).append(jid)
            summ, items = core.analyze(text, {"judgment_id": jid, "sha256": info["sha256"], "court": info["court"],
                                              "text_doc": info["text_doc"]})
            attach(items, links.get(jid, []), treat.get(jid, []))
            for k in ("body_start_page", "body_start_method", "headnote_detected", "headnote_excluded_chars", "n_opinions",
                      "opinions", "n_numbered_paragraphs", "n_quote_spans", "n_sentences"):
                row[k] = summ[k]
            for t in core.ITEM_TYPES:
                row["n_" + t] = summ["counts"].get(t, 0)
            row["_blob"] = blob
            jrows.append(row)
            items_all.extend(items)
    finally:
        store.close()
    for row in jrows:
        b = row.pop("_blob", None)
        if b and len(blob_owner.get(b, [])) > 1:
            row["shared_text_judgment_ids"] = ";".join(sorted(x for x in blob_owner[b] if x != row["judgment_id"]))
    items_all.sort(key=lambda r: (r["judgment_id"], r["char_start"], r["char_end"], r["item_type"]))
    jrows.sort(key=lambda r: r["judgment_id"])
    return items_all, jrows


def to_jsonl(items):
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in items).encode("utf-8")


def to_csv(rows, cols):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


def build_outputs(J, repo, commit):
    scope_rows, curated_rows = build_scope(J)
    ids = [r["judgment_id"] for r in scope_rows]
    basis = {r["judgment_id"]: r["scope_basis"] for r in scope_rows}
    items, jrows = extract(ids, J, basis, repo, commit)
    return {
        "HOLDINGS_C12.jsonl": to_jsonl(items),
        "HOLDINGS_C12_JUDGMENTS.csv": to_csv(jrows, JUDGMENT_COLS),
        "SCOPE_C12.csv": to_csv(scope_rows, SCOPE_COLS),
        "CURATED_SCOPE_C12.csv": to_csv(curated_rows, CURATED_COLS),
    }


def write_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def freeze_payload(repo, commit, outputs):
    return {
        "extractor": core.VERSION,
        "status_of_every_item": core.STATUS,
        "text_source": {"repo": repo, "commit": commit, "path": "data/text/<doc_id>.txt"},
        "tool_sha256": tool_hashes(),
        "evaluation_tool_sha256": {"eval_dev_holdings.py": sha256_file(os.path.join(HERE, "eval_dev_holdings.py"))},
        "input_sha256": {k: sha256_file(v) for k, v in sorted(INPUT_FILES.items())},
        "output_sha256": {k: hashlib.sha256(v).hexdigest() for k, v in sorted(outputs.items())},
        "thresholds": {"T_HOLDING": core.T_HOLDING, "T_REASONING": core.T_REASONING, "T_NONCOURT_EMIT": core.T_NONCOURT_EMIT},
        "blind_eval_command": "python3.11 -I -B tools/holdings_c12.py ids --ids-file <ids.txt> --out-dir <dir>",
    }


def cmd_run(args):
    J = load_corpus(args.repo, args.commit)
    outs = build_outputs(J, args.repo, args.commit)
    os.makedirs(OUT, exist_ok=True)
    for k, v in outs.items():
        write_atomic(os.path.join(OUT, k), v)
    sums = "".join("%s  %s\n" % (hashlib.sha256(v).hexdigest(), k) for k, v in sorted(outs.items()))
    write_atomic(os.path.join(OUT, "OUTPUT_SHA256SUMS"), sums.encode())
    write_atomic(os.path.join(OUT, "FREEZE.json"),
                 (json.dumps(freeze_payload(args.repo, args.commit, outs), indent=2, sort_keys=True) + "\n").encode())
    n = outs["HOLDINGS_C12.jsonl"].count(b"\n")
    print("RUN OK: %d items; outputs in %s" % (n, OUT))
    return 0


def cmd_ids(args):
    with open(args.ids_file, encoding="utf-8") as f:
        ids = []
        for ln in f:
            ln = ln.split("#", 1)[0].strip()
            if ln and ln not in ids:
                ids.append(ln.split(",")[0].strip())
    J = load_corpus(args.repo, args.commit)
    items, jrows = extract(ids, J, {}, args.repo, args.commit)
    os.makedirs(args.out_dir, exist_ok=True)
    outs = {"HOLDINGS_C12.jsonl": to_jsonl(items), "HOLDINGS_C12_JUDGMENTS.csv": to_csv(jrows, JUDGMENT_COLS)}
    for k, v in outs.items():
        write_atomic(os.path.join(args.out_dir, k), v)
    meta = {"extractor": core.VERSION, "tool_sha256": tool_hashes(), "text_source": {"repo": args.repo, "commit": args.commit},
            "ids_file_sha256": sha256_file(args.ids_file), "n_ids": len(ids),
            "output_sha256": {k: hashlib.sha256(v).hexdigest() for k, v in sorted(outs.items())}}
    write_atomic(os.path.join(args.out_dir, "RUN_META.json"), (json.dumps(meta, indent=2, sort_keys=True) + "\n").encode())
    print("IDS OK: %d judgment_ids, %d items -> %s" % (len(ids), len(items), args.out_dir))
    return 0


def cmd_check(args):
    ok = True
    fz_path = os.path.join(OUT, "FREEZE.json")
    with open(fz_path, encoding="utf-8") as f:
        fz = json.load(f)
    th = tool_hashes()
    for fn, h in sorted(fz["tool_sha256"].items()):
        good = th.get(fn) == h
        ok &= good
        print("%s tool %s %s" % ("OK  " if good else "FAIL", fn, h[:16]))
    if fz["extractor"] != core.VERSION:
        ok = False
        print("FAIL extractor version %s != %s" % (fz["extractor"], core.VERSION))
    for k, p in sorted(INPUT_FILES.items()):
        good = sha256_file(p) == fz["input_sha256"].get(k)
        ok &= good
        print("%s input %s" % ("OK  " if good else "FAIL", k))
    sums = {}
    with open(os.path.join(OUT, "OUTPUT_SHA256SUMS"), encoding="utf-8") as f:
        for ln in f:
            h, name = ln.split()
            sums[name] = h
    for name, h in sorted(sums.items()):
        good = sha256_file(os.path.join(OUT, name)) == h
        ok &= good
        print("%s stored %s" % ("OK  " if good else "FAIL", name))
    J = load_corpus(fz["text_source"]["repo"], fz["text_source"]["commit"])
    outs = build_outputs(J, fz["text_source"]["repo"], fz["text_source"]["commit"])
    for name, v in sorted(outs.items()):
        good = hashlib.sha256(v).hexdigest() == sums.get(name)
        ok &= good
        print("%s re-extracted %s byte-identical" % ("OK  " if good else "FAIL", name))
    # invariants
    n = 0
    for ln in outs["HOLDINGS_C12.jsonl"].decode("utf-8").splitlines():
        r = json.loads(ln)
        n += 1
        if r["status"] != core.STATUS or r["verification"] != core.VERIFICATION or r["item_type"] not in core.ITEM_TYPES:
            ok = False
            print("FAIL invariant on", r["item_id"])
            break
    print("CHECK %s: %d items" % ("PASS" if ok else "FAIL", n))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=DEF_REPO)
    ap.add_argument("--commit", default=DEF_COMMIT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("check")
    p = sub.add_parser("ids")
    p.add_argument("--ids-file", required=True)
    p.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    return {"run": cmd_run, "ids": cmd_ids, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
