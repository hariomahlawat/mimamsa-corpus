#!/usr/bin/env python3
"""Mimamsa C13 workstream A2: judicial outcome extraction, version 4 (driver).

Reads the judgment text layer at a fixed git commit of the c7 repository (data/text/<doc_id>.txt, with [[page N]]
markers) and writes AUTOMATED CANDIDATES only (status AUTOMATED_CANDIDATE_NOT_VERIFIED). Nothing here is legally
verified. One output row per proceeding, with printed_disposal and substantive_result, each anchored to a page,
character offsets and an excerpt.

Commands
  run     full corpus: every PROCESSED judgment in resumable batches (outputs/batches/), then
          outputs/OUTCOMES_V4.csv and outputs/OUTPUT_SHA256SUMS
  check   deterministic self-check: batch input keys, assembled CSV and checksums; re-extracts the first and last
          batch and confirms byte-identical payloads; validates vocabularies, anchors and abstention rules
  ids     extract a list of judgment_ids into a separate directory (blind evaluation):
          ids --ids-file F --out DIR   (F: CSV with a judgment_id column, headerless CSV, or one id per line)

Global option --exclude-ids FILE (same formats): those judgments are never analysed by `run` (each gets one row with
abstain_reason EXCLUDED_BY_EXCLUDE_IDS) and are refused by the development evaluator. `ids` ignores it (the
independent evaluator runs `ids` on the holdout).

Python 3.11+, standard library only. The text layer is read from git objects; PDFs are not opened.
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
import v4core  # noqa: E402

ROOT = os.path.dirname(HERE)                       # .../C13-A2-OUTCOME
AUDIT = os.path.dirname(ROOT)                      # .../audit_work
C10 = os.path.join(AUDIT, "C10-HF-JUDGMENTS")
DEF_REPO = "/home/user/c7"
DEF_COMMIT = "ad77758d"
OUT = os.path.join(ROOT, "outputs")
BATCH_DIR = os.path.join(OUT, "batches")
BATCH_SIZE = 200
TOOL_FILES = ("v4_text.py", "v4_quotes.py", "v4_proceedings.py", "v4_clauses.py", "v4_segment.py", "v4_decide.py",
              "v4core.py", "extract_v4.py")
# FOUO-marked Regulations for the Air Force 2000 copy: must never enter any derivative (C13 brief, hard rule)
RESTRICTED_SHA256 = {"4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"}
EXCLUDED_REASON = "EXCLUDED_BY_EXCLUDE_IDS"

OUTCOME_COLS = v4core.ROW_COLS + ["crawler_outcome", "text_source", "extractor", "status"]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def tool_fingerprint():
    h = hashlib.sha256()
    for fn in TOOL_FILES:
        with open(os.path.join(HERE, fn), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def tool_hashes():
    return {fn: sha256_bytes(open(os.path.join(HERE, fn), "rb").read()) for fn in TOOL_FILES}


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
    try:
        names = set(subprocess.run(["git", "-C", repo, "ls-tree", "--name-only", commit, "data/text/"],
                                   capture_output=True, text=True, check=True).stdout.split())
    except Exception:
        names = set()
    J = {}
    for r in reg:
        sha = r["sha256"]
        if sha in RESTRICTED_SHA256:
            continue
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


def _blank(jid, reason, info=None):
    r = {k: "" for k in OUTCOME_COLS}
    r.update({"judgment_id": jid, "proceeding": "UNIDENTIFIED", "printed_disposal": v4core.UNVERIFIED,
              "substantive_result": v4core.UNVERIFIED, "method": "abstain", "abstain_reason": reason,
              "extractor": v4core.VERSION, "status": v4core.STATUS})
    if info:
        r.update({"sha256": info["sha256"], "doc_ids": ";".join(info["doc_ids"]), "court": info["court"]})
    return r


def process_one(info, store):
    text, blob = store.get(info["text_doc"]) if info.get("text_doc") else (None, "")
    meta = {"judgment_id": info["judgment_id"], "sha256": info["sha256"], "doc_ids": info["doc_ids"],
            "case_numbers_meta": info.get("case_numbers_meta", ""), "court": info.get("court", "")}
    rows, _ = v4core.analyze(text or "", meta)
    if not info.get("text_doc"):
        for r in rows:
            r["abstain_reason"] = "NO_TEXT_FILE_FOR_THIS_SHA_AT_COMMIT"
    src = ("%s:data/text/%s.txt@blob:%s" % (store.commit, info["text_doc"], blob)) if info.get("text_doc") else ""
    for r in rows:
        r["crawler_outcome"] = info.get("crawler_outcome", "")
        r["text_source"] = src
        r["extractor"] = v4core.VERSION
        r["status"] = v4core.STATUS
        for k in OUTCOME_COLS:
            r.setdefault(k, "")
            if r[k] is None:
                r[k] = ""
    return rows


def read_ids(path):
    """judgment_ids from a CSV (the 'judgment_id' column when the header names one, else the first column) or a plain
    list (one id per line). Blank lines and '#' comments are ignored."""
    if not path:
        return []
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return []
    head = [h.strip() for h in next(csv.reader([lines[0]]))]
    col, start = 0, 0
    if "judgment_id" in head:
        col, start = head.index("judgment_id"), 1
    ids = []
    for row in csv.reader(lines[start:]):
        if len(row) > col and row[col].strip():
            ids.append(row[col].strip())
    return ids


def exclusion_key(excl):
    return sha256_bytes("\n".join(sorted(excl)).encode()) if excl else ""


def batch_key(ids, J, fp, excl=frozenset()):
    h = hashlib.sha256()
    h.update(v4core.VERSION.encode())
    h.update(fp.encode())
    h.update(DEF_COMMIT.encode())
    h.update(exclusion_key(set(ids) & set(excl)).encode())
    for j in ids:
        i = J[j]
        h.update(json.dumps([j, i["sha256"], i["doc_ids"], i["text_doc"], i["case_numbers_meta"], i["crawler_outcome"]],
                            sort_keys=True).encode())
    return h.hexdigest()


def run_batch(ids, J, store, excl=frozenset()):
    outs = []
    for j in ids:
        if j in excl:
            outs.append(_blank(j, EXCLUDED_REASON, J[j]))
        else:
            outs.extend(process_one(J[j], store))
    return outs


def batch_payload(bi, ids, key, outs):
    return json.dumps({"batch": bi, "extractor": v4core.VERSION, "input_key": key, "judgment_ids": ids,
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


def _batches(order):
    return [order[i:i + BATCH_SIZE] for i in range(0, len(order), BATCH_SIZE)]


def _bpath(bi):
    return os.path.join(BATCH_DIR, "v4_batch_%04d.json.gz" % bi)


# ------------------------------------------------------------------ commands
def cmd_run(args):
    J, order = load_inputs(args.repo, args.commit)
    excl = frozenset(read_ids(args.exclude_ids))
    os.makedirs(BATCH_DIR, exist_ok=True)
    fp = tool_fingerprint()
    store = TextStore(args.repo, args.commit)
    done = skipped = 0
    for bi, ids in enumerate(_batches(order)):
        if args.limit_batches is not None and bi >= args.limit_batches:
            break
        path = _bpath(bi)
        key = batch_key(ids, J, fp, excl)
        if os.path.exists(path) and not args.force:
            try:
                if json.loads(gzip.open(path).read()).get("input_key") == key:
                    skipped += 1
                    continue
            except Exception:
                pass
        outs = run_batch(ids, J, store, excl)
        write_atomic(path, gzip.compress(batch_payload(bi, ids, key, outs), mtime=0))
        done += 1
        print("batch %d: %d judgments, %d proceeding rows" % (bi, len(ids), len(outs)), flush=True)
    store.close()
    print("batches written %d, up-to-date %d, total %d" % (done, skipped, len(_batches(order))))
    if args.limit_batches is None:
        rows, problems = load_batches(J, order, fp, excl)
        if problems:
            print("NOT ASSEMBLED:", "; ".join(problems))
            sys.exit(2)
        write_atomic(os.path.join(OUT, "OUTCOMES_V4.csv"), outcomes_csv(rows))
        info = {"extractor": v4core.VERSION, "tool_sha256": tool_hashes(), "tool_fingerprint": fp,
                "repo_commit": args.commit, "n_judgments": len(order), "n_rows": len(rows),
                "excluded_judgments": len(excl & set(order)), "exclusion_list_sha256": exclusion_key(excl & set(order))}
        write_atomic(os.path.join(OUT, "RUN_INFO_V4.json"), (json.dumps(info, indent=1, sort_keys=True) + "\n").encode())
        write_sums()
        print("assembled: %d proceeding rows for %d judgments (%d excluded)" % (len(rows), len(order), len(excl & set(order))))


def load_batches(J, order, fp, excl=frozenset()):
    rows, problems = [], []
    for bi, ids in enumerate(_batches(order)):
        path = _bpath(bi)
        if not os.path.exists(path):
            problems.append("missing batch %d" % bi)
            continue
        d = json.loads(gzip.open(path).read())
        if d.get("input_key") != batch_key(ids, J, fp, excl):
            problems.append("stale batch %d (input key differs)" % bi)
        rows.extend(d["outcomes"])
    return rows, problems


SUM_FILES = ["OUTCOMES_V4.csv", "RUN_INFO_V4.json"]


def write_sums():
    lines = []
    for name in SUM_FILES:
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            lines.append("%s  %s\n" % (sha256_bytes(open(p, "rb").read()), name))
    for name in sorted(os.listdir(BATCH_DIR)) if os.path.isdir(BATCH_DIR) else []:
        if name.endswith(".json.gz"):
            lines.append("%s  batches/%s\n" % (sha256_bytes(open(os.path.join(BATCH_DIR, name), "rb").read()), name))
    for fn in TOOL_FILES:
        lines.append("%s  ../tools/%s\n" % (sha256_bytes(open(os.path.join(HERE, fn), "rb").read()), fn))
    write_atomic(os.path.join(OUT, "OUTPUT_SHA256SUMS"), "".join(lines).encode())


def validate_rows(rows):
    """Rows breaking a vocabulary, status, abstention or anchor rule."""
    bad = []
    for r in rows:
        p, s = r["printed_disposal"], r["substantive_result"]
        both_abstain = p == v4core.UNVERIFIED and s == v4core.UNVERIFIED
        if p not in v4core.PRINTED_VOCAB or s not in v4core.SUBST_VOCAB or r["status"] != v4core.STATUS:
            bad.append((r, "vocabulary/status"))
        elif both_abstain != (r["final_or_interim"] == ""):
            bad.append((r, "final_or_interim"))
        elif both_abstain and not r["abstain_reason"]:
            bad.append((r, "abstain_reason"))
        elif not both_abstain and not (str(r["page"]) and str(r["char_start"]) and str(r["char_end"]) and r["excerpt"]):
            bad.append((r, "anchor"))
    return bad


def cmd_check(args):
    J, order = load_inputs(args.repo, args.commit)
    excl = frozenset(read_ids(args.exclude_ids))
    fp = tool_fingerprint()
    ok = True
    rows, problems = load_batches(J, order, fp, excl)
    for p in problems:
        print("FAIL", p)
        ok = False
    p = os.path.join(OUT, "OUTCOMES_V4.csv")
    if not os.path.exists(p) or open(p, "rb").read() != outcomes_csv(rows):
        print("FAIL assembled OUTCOMES_V4.csv differs from batches")
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
    batches = _batches(order)
    store = TextStore(args.repo, args.commit)
    for bi in sorted({0, len(batches) - 1}):
        ids = batches[bi]
        fresh = batch_payload(bi, ids, batch_key(ids, J, fp, excl), run_batch(ids, J, store, excl))
        path = _bpath(bi)
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
    if any(r["sha256"] in RESTRICTED_SHA256 for r in rows):
        print("FAIL restricted copy present in output")
        ok = False
    bad = validate_rows(rows)
    if bad:
        print("FAIL %d rows violate vocabulary/status/abstention/anchor rules, e.g. %s %s" %
              (len(bad), bad[0][0]["judgment_id"], bad[0][1]))
        ok = False
    print("CHECK", "PASS" if ok else "FAIL", "(%s, %d judgments, %d proceeding rows)" % (v4core.VERSION, len(order), len(rows)))
    sys.exit(0 if ok else 1)


def cmd_ids(args):
    J, _ = load_inputs(args.repo, args.commit)
    ids = [x.strip() for x in args.ids.split(",") if x.strip()] + read_ids(args.ids_file)
    os.makedirs(args.out, exist_ok=True)
    store = TextStore(args.repo, args.commit)
    rows = []
    for j in ids:
        rows.extend(process_one(J[j], store) if j in J else [_blank(j, "UNKNOWN_JUDGMENT_ID")])
    store.close()
    write_atomic(os.path.join(args.out, "OUTCOMES_V4.csv"), outcomes_csv(rows))
    try:
        commit = subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = ""
    meta = {"extractor": v4core.VERSION, "tool_sha256": tool_hashes(), "tool_fingerprint": tool_fingerprint(),
            "tool_repo_head": commit, "repo_commit": args.commit, "n_ids": len(ids), "n_rows": len(rows)}
    write_atomic(os.path.join(args.out, "RUN_INFO.json"), (json.dumps(meta, indent=1, sort_keys=True) + "\n").encode())
    print("%s: %d judgment ids -> %d proceeding rows in %s" % (v4core.VERSION, len(ids), len(rows), args.out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=DEF_REPO)
    ap.add_argument("--commit", default=DEF_COMMIT)
    ap.add_argument("--exclude-ids", default="", help="judgments never analysed by run (fresh holdout ids)")
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
    if "--check" in sys.argv[1:]:      # `extract_v4.py --check` is an alias of `extract_v4.py check`
        sys.argv = [a for a in sys.argv if a != "--check"] + ["check"]
    main()
