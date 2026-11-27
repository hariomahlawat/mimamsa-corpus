#!/usr/bin/env python3
"""Mimamsa C12 Workstream D: judicial outcome extraction, version 3 (driver).

Reads the judgment text layer at a fixed git commit of the c7 repository (data/text/<doc_id>.txt, with
[[page N]] markers) and writes AUTOMATED CANDIDATES only (status AUTOMATED_CANDIDATE_NOT_VERIFIED). Nothing here is
legally verified. One output row per proceeding, with printed_disposal and substantive_result.

Commands
  run     process all PROCESSED judgments in resumable batches (outputs/batches/), then assemble
          outputs/OUTCOMES_V3.csv and outputs/OUTPUT_SHA256SUMS
  check   verify batch input keys, the assembled output against OUTPUT_SHA256SUMS, re-extract two batches to confirm
          byte-identical (deterministic) results, and validate vocabularies
  ids     extract an arbitrary list of judgment_ids into a separate directory (blind evaluation):
          ids --ids-file F --out DIR   (F: first CSV column judgment_id, or one id per line; '#' lines ignored)

Python 3.11+, standard library only. The text layer is read from git objects; the PDFs are not opened.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v3core  # noqa: E402

ROOT = os.path.dirname(HERE)                       # .../extractor_v3
AUDIT = os.path.dirname(os.path.dirname(ROOT))     # .../audit_work
C10 = os.path.join(AUDIT, "C10-HF-JUDGMENTS")
DEF_REPO = "/home/user/c7"
DEF_COMMIT = "ad77758d"
OUT = os.path.join(ROOT, "outputs")
BATCH_DIR = os.path.join(OUT, "batches")
BATCH_SIZE = 200
TOOL_FILES = ("v3core.py", "extract_v3.py")

OUTCOME_COLS = v3core.ROW_COLS + ["crawler_outcome", "text_source", "extractor", "status"]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def tool_fingerprint():
    h = hashlib.sha256()
    for fn in TOOL_FILES:
        with open(os.path.join(HERE, fn), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


# ------------------------------------------------------------------ inputs
def load_inputs(repo=DEF_REPO, commit=DEF_COMMIT):
    """Return (judgments: dict judgment_id -> info, order: sorted ids of PROCESSED judgments)."""
    with open(os.path.join(C10, "outputs", "HF_JUDGMENT_COPY_REGISTER.csv"), encoding="utf-8") as f:
        reg = list(csv.DictReader(f))
    with open(os.path.join(C10, "outputs", "HF_JUDGMENT_METADATA_AUDIT.csv"), encoding="utf-8") as f:
        audit = list(csv.DictReader(f))
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
        sha = r["sha256"]
        jid = r["judgment_id"]
        recs = sorted(by_sha.get(sha, []), key=lambda x: x["doc_id"])
        doc_ids = [x["doc_id"] for x in recs]
        text_doc = next((x for x in doc_ids if "data/text/%s.txt" % x in names), "")
        J[jid] = {"judgment_id": jid, "sha256": sha, "doc_ids": doc_ids, "text_doc": text_doc,
                  "disposition": r["disposition"],
                  "court": recs[0]["court"] if recs else "",
                  "case_numbers_meta": ";".join(sorted(set(x["case_numbers_meta"] for x in recs if x["case_numbers_meta"]))),
                  "crawler_outcome": "|".join(sorted(set(x["outcome_meta"] for x in recs if x["outcome_meta"])))}
    order = sorted(j for j, v in J.items() if v["disposition"] == "PROCESSED")
    return J, order


class TextStore:
    """Reads blobs from git with one `git cat-file --batch` process."""

    def __init__(self, repo=DEF_REPO, commit=DEF_COMMIT):
        self.repo, self.commit = repo, commit
        self.p = None

    def _start(self):
        self.p = subprocess.Popen(["git", "-C", self.repo, "cat-file", "--batch"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE)

    def get(self, doc_id):
        if not doc_id:
            return None, ""
        if self.p is None:
            self._start()
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
            self.p.stdout.close()
            self.p.wait()
            self.p = None


def process_one(info, store):
    text, blob = store.get(info["text_doc"]) if info.get("text_doc") else (None, "")
    meta = {"judgment_id": info["judgment_id"], "sha256": info["sha256"], "doc_ids": info["doc_ids"],
            "case_numbers_meta": info.get("case_numbers_meta", ""), "court": info.get("court", "")}
    rows, _ = v3core.analyze(text or "", meta)
    if not info.get("text_doc"):
        for r in rows:
            r["abstain_reason"] = "NO_TEXT_FILE_FOR_THIS_SHA_AT_COMMIT"
    src = ("%s:data/text/%s.txt@blob:%s" % (store.commit, info["text_doc"], blob)) if info.get("text_doc") else ""
    for r in rows:
        r["crawler_outcome"] = info.get("crawler_outcome", "")
        r["text_source"] = src
        r["extractor"] = v3core.VERSION
        r["status"] = v3core.STATUS
        for k in OUTCOME_COLS:
            r.setdefault(k, "")
            if r[k] is None:
                r[k] = ""
    return rows


def unknown_row(jid):
    r = {k: "" for k in OUTCOME_COLS}
    r.update({"judgment_id": jid, "proceeding": "UNIDENTIFIED", "printed_disposal": v3core.UNVERIFIED,
              "substantive_result": v3core.UNVERIFIED, "method": "abstain", "abstain_reason": "UNKNOWN_JUDGMENT_ID",
              "extractor": v3core.VERSION, "status": v3core.STATUS})
    return r


def batch_key(ids, J, fp):
    h = hashlib.sha256()
    h.update(v3core.VERSION.encode())
    h.update(fp.encode())
    h.update(DEF_COMMIT.encode())
    for j in ids:
        i = J[j]
        h.update(json.dumps([j, i["sha256"], i["doc_ids"], i["text_doc"], i["case_numbers_meta"], i["crawler_outcome"]],
                            sort_keys=True).encode())
    return h.hexdigest()


def run_batch(ids, J, store):
    outs = []
    for j in ids:
        outs.extend(process_one(J[j], store))
    return outs


def batch_payload(bi, ids, key, outs):
    return json.dumps({"batch": bi, "extractor": v3core.VERSION, "input_key": key, "judgment_ids": ids,
                       "outcomes": outs}, sort_keys=True, ensure_ascii=False).encode("utf-8")


def write_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def outcomes_csv(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=OUTCOME_COLS, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


# ------------------------------------------------------------------ commands
def cmd_run(args):
    J, order = load_inputs(args.repo, args.commit)
    os.makedirs(BATCH_DIR, exist_ok=True)
    fp = tool_fingerprint()
    store = TextStore(args.repo, args.commit)
    batches = [order[i:i + BATCH_SIZE] for i in range(0, len(order), BATCH_SIZE)]
    done = skipped = 0
    for bi, ids in enumerate(batches):
        if args.limit_batches is not None and bi >= args.limit_batches:
            break
        path = os.path.join(BATCH_DIR, "v3_batch_%04d.json.gz" % bi)
        key = batch_key(ids, J, fp)
        if os.path.exists(path) and not args.force:
            try:
                old = json.loads(gzip.open(path).read())
                if old.get("input_key") == key:
                    skipped += 1
                    continue
            except Exception:
                pass
        outs = run_batch(ids, J, store)
        write_atomic(path, gzip.compress(batch_payload(bi, ids, key, outs), mtime=0))
        done += 1
        print("batch %d: %d judgments, %d proceeding rows" % (bi, len(ids), len(outs)), flush=True)
    store.close()
    print("batches written %d, up-to-date %d, total %d" % (done, skipped, len(batches)))
    if args.limit_batches is None:
        assemble(J, order, fp)


def load_batches(J, order, fp):
    batches = [order[i:i + BATCH_SIZE] for i in range(0, len(order), BATCH_SIZE)]
    rows, problems = [], []
    for bi, ids in enumerate(batches):
        path = os.path.join(BATCH_DIR, "v3_batch_%04d.json.gz" % bi)
        if not os.path.exists(path):
            problems.append("missing batch %d" % bi)
            continue
        d = json.loads(gzip.open(path).read())
        if d.get("input_key") != batch_key(ids, J, fp):
            problems.append("stale batch %d (input key differs)" % bi)
        rows.extend(d["outcomes"])
    return rows, problems


def assemble(J, order, fp):
    rows, problems = load_batches(J, order, fp)
    if problems:
        print("NOT ASSEMBLED:", "; ".join(problems))
        sys.exit(2)
    write_atomic(os.path.join(OUT, "OUTCOMES_V3.csv"), outcomes_csv(rows))
    write_sums()
    print("assembled: %d proceeding rows for %d judgments" % (len(rows), len(order)))


SUM_FILES = ["OUTCOMES_V3.csv", "DEV_EVALUATION_V3.md", "DEV_EVALUATION_V3_ROWS.csv", "DEV_EVALUATION_V3_SUMMARY.json",
             "DEV_BATCH_COPIES_V3.csv", "DEV_SPOTCHECK_V3.csv", "FREEZE_V3.json", "../README.md"]


def write_sums():
    lines = []
    for name in SUM_FILES:
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            lines.append("%s  %s\n" % (sha256_bytes(open(p, "rb").read()), name))
    for name in sorted(os.listdir(BATCH_DIR)) if os.path.isdir(BATCH_DIR) else []:
        if name.endswith(".json.gz"):
            lines.append("%s  batches/%s\n" % (sha256_bytes(open(os.path.join(BATCH_DIR, name), "rb").read()), name))
    for fn in TOOL_FILES + ("eval_dev_v3.py", "build_dev_gold_v3.py", "dev_gold_v3.json"):
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            lines.append("%s  ../tools/%s\n" % (sha256_bytes(open(p, "rb").read()), fn))
    p = os.path.join(ROOT, "tests", "test_extract_v3.py")
    if os.path.exists(p):
        lines.append("%s  ../tests/test_extract_v3.py\n" % sha256_bytes(open(p, "rb").read()))
    write_atomic(os.path.join(OUT, "OUTPUT_SHA256SUMS"), "".join(lines).encode())


def validate_rows(rows):
    bad = []
    for r in rows:
        if r["printed_disposal"] not in v3core.PRINTED_VOCAB or r["substantive_result"] not in v3core.SUBST_VOCAB or \
                r["status"] != v3core.STATUS:
            bad.append(r)
        elif (r["printed_disposal"] == v3core.UNVERIFIED and r["substantive_result"] == v3core.UNVERIFIED) != \
                (r["final_or_interim"] == ""):
            bad.append(r)
        elif r["printed_disposal"] == v3core.UNVERIFIED and r["substantive_result"] == v3core.UNVERIFIED and \
                not r["abstain_reason"]:
            bad.append(r)
    return bad


def cmd_check(args):
    J, order = load_inputs(args.repo, args.commit)
    fp = tool_fingerprint()
    ok = True
    rows, problems = load_batches(J, order, fp)
    for p in problems:
        print("FAIL", p)
        ok = False
    p = os.path.join(OUT, "OUTCOMES_V3.csv")
    if not os.path.exists(p) or open(p, "rb").read() != outcomes_csv(rows):
        print("FAIL assembled OUTCOMES_V3.csv differs from batches")
        ok = False
    sums = os.path.join(OUT, "OUTPUT_SHA256SUMS")
    if os.path.exists(sums):
        for line in open(sums):
            h, name = line.rstrip("\n").split("  ", 1)
            q = os.path.normpath(os.path.join(OUT, name))
            if not os.path.exists(q) or sha256_bytes(open(q, "rb").read()) != h:
                print("FAIL checksum", name)
                ok = False
    else:
        print("FAIL OUTPUT_SHA256SUMS missing")
        ok = False
    batches = [order[i:i + BATCH_SIZE] for i in range(0, len(order), BATCH_SIZE)]
    store = TextStore(args.repo, args.commit)
    for bi in sorted(set([0, len(batches) - 1])):
        ids = batches[bi]
        fresh = batch_payload(bi, ids, batch_key(ids, J, fp), run_batch(ids, J, store))
        path = os.path.join(BATCH_DIR, "v3_batch_%04d.json.gz" % bi)
        if not os.path.exists(path) or gzip.open(path).read() != fresh:
            print("FAIL re-extraction of batch %d is not byte-identical" % bi)
            ok = False
        else:
            print("ok re-extraction of batch %d byte-identical (decompressed payload)" % bi)
    store.close()
    n_j = len(set(r["judgment_id"] for r in rows))
    if n_j != len(order):
        print("FAIL rows cover %d of %d judgments" % (n_j, len(order)))
        ok = False
    bad = validate_rows(rows)
    if bad:
        print("FAIL %d rows violate vocabulary/status/abstention rules" % len(bad))
        ok = False
    print("CHECK", "PASS" if ok else "FAIL", "(%s, %d judgments, %d proceeding rows)" % (v3core.VERSION, len(order), len(rows)))
    sys.exit(0 if ok else 1)


def read_ids(path):
    """judgment_ids from a CSV (the 'judgment_id' column when the header names one, else the first column) or a plain
    list (one id per line). Blank lines and '#' comments are ignored."""
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return []
    head = next(csv.reader([lines[0]]))
    col, start = 0, 0
    if "judgment_id" in [h.strip() for h in head]:
        col, start = [h.strip() for h in head].index("judgment_id"), 1
    ids = []
    for row in csv.reader(lines[start:]):
        if len(row) > col and row[col].strip():
            ids.append(row[col].strip())
    return ids


def cmd_ids(args):
    J, order = load_inputs(args.repo, args.commit)
    ids = []
    if args.ids:
        ids += [x.strip() for x in args.ids.split(",") if x.strip()]
    if args.ids_file:
        ids += read_ids(args.ids_file)
    os.makedirs(args.out, exist_ok=True)
    store = TextStore(args.repo, args.commit)
    rows = []
    for j in ids:
        rows.extend(process_one(J[j], store) if j in J else [unknown_row(j)])
    store.close()
    write_atomic(os.path.join(args.out, "OUTCOMES_V3.csv"), outcomes_csv(rows))
    meta = {"extractor": v3core.VERSION, "tool_sha256": {fn: sha256_bytes(open(os.path.join(HERE, fn), "rb").read())
                                                       for fn in TOOL_FILES},
            "repo_commit": args.commit, "n_ids": len(ids), "n_rows": len(rows)}
    write_atomic(os.path.join(args.out, "RUN_INFO.json"), (json.dumps(meta, indent=1, sort_keys=True) + "\n").encode())
    print("%s: %d judgment ids -> %d proceeding rows in %s" % (v3core.VERSION, len(ids), len(rows), args.out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=DEF_REPO)
    ap.add_argument("--commit", default=DEF_COMMIT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--force", action="store_true")
    r.add_argument("--limit-batches", type=int, default=None)
    sub.add_parser("check")
    i = sub.add_parser("ids")
    i.add_argument("--ids", default="")
    i.add_argument("--ids-file", default="")
    i.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    {"run": cmd_run, "check": cmd_check, "ids": cmd_ids}[args.cmd](args)


if __name__ == "__main__":
    main()
