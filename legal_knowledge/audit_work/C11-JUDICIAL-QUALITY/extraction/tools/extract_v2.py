#!/usr/bin/env python3
"""Mimamsa C11: structured outcome and legal-proposition extraction, version 2 (driver).

Reads the judgment text layer at a fixed git commit of the c7 repository (data/text/<doc_id>.txt, with
[[page N]] markers) and writes AUTOMATED CANDIDATES only. Nothing here is legally verified.

Commands
  run     process all PROCESSED judgments in resumable batches, then assemble the outputs
  check   verify batch input keys, assembled outputs against OUTPUT_SHA256SUMS, and re-extract two
          batches to confirm byte-identical (deterministic) results
  ids     extract an arbitrary list of judgment_ids into a separate directory (for holdout evaluation)

Python 3.11+, standard library only (no PyMuPDF needed: the text layer is read, not the PDFs).
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
import v2core  # noqa: E402

ROOT = os.path.dirname(HERE)                       # .../extraction
AUDIT = os.path.dirname(os.path.dirname(ROOT))     # .../audit_work
C10 = os.path.join(AUDIT, "C10-HF-JUDGMENTS")
DEF_REPO = "/home/user/c7"
DEF_COMMIT = "ad77758d"
OUT = os.path.join(ROOT, "outputs")
BATCH_DIR = os.path.join(OUT, "batches")
BATCH_SIZE = 200

OUTCOME_COLS = ["judgment_id", "sha256", "doc_ids", "court", "proceeding", "outcome", "page", "paragraph",
                "char_start", "char_end", "excerpt", "method", "abstain_reason", "flags", "crawler_outcome",
                "old_candidate", "agree_crawler", "agree_old", "text_source", "extractor", "status"]

CRAWLER_FAMILY = {"allowed": "allowed", "partly_allowed": "partly_allowed", "dismissed": "dismissed",
                  "dismissed_as_withdrawn": "dismissed", "dismissed_as_infructuous": "dismissed",
                  "disposed_of_with_directions": "disposed", "transferred": "disposed", "remanded": "allowed",
                  "set_aside_and_remanded": "allowed"}
OLD_FAMILY = {"allowed": {"allowed"}, "partly_allowed": {"partly_allowed"}, "dismissed": {"dismissed"},
              "dismissed_as_withdrawn": {"dismissed"}, "dismissed_as_infructuous": {"dismissed"},
              "disposed_of_with_directions": {"disposed"}, "transferred": {"transferred", "disposed"},
              "remanded": {"remanded"}, "set_aside_and_remanded": {"remanded", "set_aside_quashed"}}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def tool_fingerprint():
    h = hashlib.sha256()
    for fn in ("v2core.py", "extract_v2.py"):
        with open(os.path.join(HERE, fn), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


# ------------------------------------------------------------------ inputs
def load_inputs(repo=DEF_REPO, commit=DEF_COMMIT):
    """Return (judgments: dict judgment_id -> info, order: sorted ids of PROCESSED judgments)."""
    reg = list(csv.DictReader(open(os.path.join(C10, "outputs", "HF_JUDGMENT_COPY_REGISTER.csv"), encoding="utf-8")))
    audit = list(csv.DictReader(open(os.path.join(C10, "outputs", "HF_JUDGMENT_METADATA_AUDIT.csv"), encoding="utf-8")))
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
                  "crawler_outcome": "|".join(sorted(set(x["outcome_meta"] for x in recs if x["outcome_meta"]))),
                  "old_candidate": "|".join(sorted(set(x["outcome_text_candidate"] for x in recs if x["outcome_text_candidate"])))}
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
            self.p.wait()
            self.p = None


def agree(v2, crawler, old):
    def one(lbls, fam_fn):
        if not lbls:
            return "NA_NO_VALUE"
        if v2 in ("OUTCOME_UNVERIFIED",):
            return "NA_V2_ABSTAINED"
        if v2 == "not_final":
            return "NA_V2_NOT_FINAL"
        return "AGREE" if any(fam_fn(l) for l in lbls.split("|")) else "DISAGREE"
    a_c = one(crawler, lambda l: CRAWLER_FAMILY.get(v2) == l)
    a_o = one(old if old != "NOT_FOUND" else "", lambda l: l in OLD_FAMILY.get(v2, set()))
    return a_c, a_o


def process_one(info, store):
    text, blob = store.get(info["text_doc"]) if info.get("text_doc") else (None, "")
    meta = {"judgment_id": info["judgment_id"], "sha256": info["sha256"], "doc_ids": info["doc_ids"],
            "case_numbers_meta": info.get("case_numbers_meta", ""), "court": info.get("court", "")}
    rows, props, _ = v2core.analyze(text or "", meta)
    if not info.get("text_doc"):
        for r in rows:
            r["abstain_reason"] = "NO_TEXT_FILE_FOR_THIS_SHA_AT_COMMIT"
    src = ("%s:data/text/%s.txt@blob:%s" % (store.commit, info["text_doc"], blob)) if info.get("text_doc") else ""
    for r in rows:
        r["crawler_outcome"] = info.get("crawler_outcome", "")
        r["old_candidate"] = info.get("old_candidate", "")
        r["agree_crawler"], r["agree_old"] = agree(r["outcome"], r["crawler_outcome"], r["old_candidate"])
        r["text_source"] = src
        r["extractor"] = v2core.VERSION
        r["status"] = v2core.STATUS
        for k in OUTCOME_COLS:
            r.setdefault(k, "")
            if r[k] is None:
                r[k] = ""
    return rows, props


def batch_key(ids, J, fp):
    h = hashlib.sha256()
    h.update(v2core.VERSION.encode())
    h.update(fp.encode())
    h.update(DEF_COMMIT.encode())
    for j in ids:
        i = J[j]
        h.update(json.dumps([j, i["sha256"], i["doc_ids"], i["text_doc"], i["case_numbers_meta"], i["crawler_outcome"],
                             i["old_candidate"]], sort_keys=True).encode())
    return h.hexdigest()


def run_batch(ids, J, store):
    outs, props = [], []
    for j in ids:
        r, p = process_one(J[j], store)
        outs.extend(r)
        props.extend(p)
    return outs, props


def batch_payload(bi, ids, key, outs, props):
    return json.dumps({"batch": bi, "extractor": v2core.VERSION, "input_key": key, "judgment_ids": ids,
                       "outcomes": outs, "propositions": props}, sort_keys=True, ensure_ascii=False).encode("utf-8")


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


def props_jsonl(props):
    return "".join(json.dumps(p, sort_keys=True, ensure_ascii=False) + "\n" for p in props).encode("utf-8")


# ------------------------------------------------------------------ disagreement analysis
def disagreement_csv(all_rows):
    audit = list(csv.DictReader(open(os.path.join(C10, "outputs", "HF_JUDGMENT_METADATA_AUDIT.csv"), encoding="utf-8")))
    by_j = {}
    for r in all_rows:
        by_j.setdefault(r["judgment_id"], []).append(r)
    cols = ["doc_id", "judgment_id", "sha256", "court", "crawler_outcome", "old_text_candidate", "v2_outcome",
            "v2_rows", "v2_supports", "v2_page", "v2_paragraph", "v2_excerpt", "v2_method", "v2_abstain_reason",
            "c10_contradiction_note", "note", "status"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    n = 0
    for a in sorted(audit, key=lambda x: x["doc_id"]):
        if "crawler outcome '" not in a["contradictions"] or "differs from text outcome candidate" not in a["contradictions"]:
            continue
        n += 1
        rows = by_j.get(a["judgment_id"], [])
        cr, old = a["outcome_meta"], a["outcome_text_candidate"]
        outs = [r["outcome"] for r in rows]
        if not rows:
            sup, v2o = "NOT_PROCESSED_BY_V2", ""
        elif len(rows) > 1:
            sup, v2o = "V2_MIXED_PER_PROCEEDING", "MIXED"
        else:
            v2o = outs[0]
            if v2o == v2core.UNVERIFIED:
                sup = "V2_ABSTAINED"
            elif v2o == "not_final":
                sup = "V2_NOT_FINAL"
            else:
                c_ok = CRAWLER_FAMILY.get(v2o) == cr
                o_ok = old in OLD_FAMILY.get(v2o, set())
                sup = "BOTH" if (c_ok and o_ok) else "CRAWLER" if c_ok else "OLD_EXTRACTOR" if o_ok else "NEITHER"
        r0 = rows[-1] if rows else {}
        w.writerow({"doc_id": a["doc_id"], "judgment_id": a["judgment_id"], "sha256": a["sha256"], "court": a["court"],
                    "crawler_outcome": cr, "old_text_candidate": old, "v2_outcome": v2o,
                    "v2_rows": " | ".join("%s=%s" % (r["proceeding"][:60], r["outcome"]) for r in rows),
                    "v2_supports": sup, "v2_page": r0.get("page", ""), "v2_paragraph": r0.get("paragraph", ""),
                    "v2_excerpt": r0.get("excerpt", ""), "v2_method": r0.get("method", ""),
                    "v2_abstain_reason": r0.get("abstain_reason", ""), "c10_contradiction_note": a["contradictions"],
                    "note": "both prior readings preserved verbatim; v2 is a third automated reading, not a correction",
                    "status": v2core.STATUS})
    return buf.getvalue().encode("utf-8"), n


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
        path = os.path.join(BATCH_DIR, "v2_batch_%04d.json.gz" % bi)
        key = batch_key(ids, J, fp)
        if os.path.exists(path) and not args.force:
            try:
                old = json.loads(gzip.open(path).read())
                if old.get("input_key") == key:
                    skipped += 1
                    continue
            except Exception:
                pass
        outs, props = run_batch(ids, J, store)
        write_atomic(path, gzip.compress(batch_payload(bi, ids, key, outs, props), mtime=0))
        done += 1
        print("batch %d: %d judgments, %d outcome rows, %d propositions" % (bi, len(ids), len(outs), len(props)), flush=True)
    store.close()
    print("batches written %d, up-to-date %d, total %d" % (done, skipped, len(batches)))
    if args.limit_batches is None:
        assemble(J, order, fp)


def load_batches(J, order, fp, strict=True):
    batches = [order[i:i + BATCH_SIZE] for i in range(0, len(order), BATCH_SIZE)]
    rows, props, problems = [], [], []
    for bi, ids in enumerate(batches):
        path = os.path.join(BATCH_DIR, "v2_batch_%04d.json.gz" % bi)
        if not os.path.exists(path):
            problems.append("missing batch %d" % bi)
            continue
        d = json.loads(gzip.open(path).read())
        if d.get("input_key") != batch_key(ids, J, fp):
            problems.append("stale batch %d (input key differs)" % bi)
        rows.extend(d["outcomes"])
        props.extend(d["propositions"])
    return rows, props, problems


def build_outputs(J, order, fp):
    rows, props, problems = load_batches(J, order, fp)
    files = {"OUTCOMES_V2.csv": outcomes_csv(rows), "PROPOSITIONS_V2.jsonl": props_jsonl(props)}
    dis, n = disagreement_csv(rows)
    files["CRAWLER_DISAGREEMENT_ANALYSIS.csv"] = dis
    return files, problems, rows, props


def assemble(J, order, fp):
    files, problems, rows, props = build_outputs(J, order, fp)
    if problems:
        print("NOT ASSEMBLED:", "; ".join(problems))
        sys.exit(2)
    for name, data in files.items():
        write_atomic(os.path.join(OUT, name), data)
    write_sums()
    print("assembled: %d outcome rows for %d judgments, %d propositions" % (len(rows), len(order), len(props)))


SUM_FILES = ["OUTCOMES_V2.csv", "PROPOSITIONS_V2.jsonl", "CRAWLER_DISAGREEMENT_ANALYSIS.csv", "DEV_EVALUATION.md",
             "DEV_EVALUATION_ROWS.csv", "README.md"]


def write_sums():
    lines = []
    for name in SUM_FILES:
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            lines.append("%s  %s\n" % (sha256_bytes(open(p, "rb").read()), name))
    for name in sorted(os.listdir(BATCH_DIR)) if os.path.isdir(BATCH_DIR) else []:
        if name.endswith(".json.gz"):
            lines.append("%s  batches/%s\n" % (sha256_bytes(open(os.path.join(BATCH_DIR, name), "rb").read()), name))
    for fn in ("v2core.py", "extract_v2.py", "eval_dev.py", "dev_gold.json"):
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            lines.append("%s  ../tools/%s\n" % (sha256_bytes(open(p, "rb").read()), fn))
    write_atomic(os.path.join(OUT, "OUTPUT_SHA256SUMS"), "".join(lines).encode())


def cmd_check(args):
    J, order = load_inputs(args.repo, args.commit)
    fp = tool_fingerprint()
    ok = True
    files, problems, rows, props = build_outputs(J, order, fp)
    for p in problems:
        print("FAIL", p)
        ok = False
    for name, data in files.items():
        p = os.path.join(OUT, name)
        if not os.path.exists(p) or open(p, "rb").read() != data:
            print("FAIL assembled output differs from batches:", name)
            ok = False
    sums = os.path.join(OUT, "OUTPUT_SHA256SUMS")
    if os.path.exists(sums):
        for line in open(sums):
            h, name = line.rstrip("\n").split("  ", 1)
            p = os.path.normpath(os.path.join(OUT, name))
            if not os.path.exists(p) or sha256_bytes(open(p, "rb").read()) != h:
                print("FAIL checksum", name)
                ok = False
    else:
        print("FAIL OUTPUT_SHA256SUMS missing")
        ok = False
    # determinism: re-extract two batches and compare bytes
    batches = [order[i:i + BATCH_SIZE] for i in range(0, len(order), BATCH_SIZE)]
    store = TextStore(args.repo, args.commit)
    for bi in sorted(set([0, len(batches) - 1])):
        ids = batches[bi]
        outs, pr = run_batch(ids, J, store)
        fresh = batch_payload(bi, ids, batch_key(ids, J, fp), outs, pr)
        path = os.path.join(BATCH_DIR, "v2_batch_%04d.json.gz" % bi)
        # compare the decompressed payload: gzip/zlib byte streams can differ between Python builds
        if not os.path.exists(path) or gzip.open(path).read() != fresh:
            print("FAIL re-extraction of batch %d is not byte-identical" % bi)
            ok = False
        else:
            print("ok re-extraction of batch %d byte-identical (decompressed payload)" % bi)
    store.close()
    n_j = len(set(r["judgment_id"] for r in rows))
    if n_j != len(order):
        print("FAIL outcome rows cover %d of %d judgments" % (n_j, len(order)))
        ok = False
    bad = [r for r in rows if r["outcome"] not in v2core.OUTCOME_VOCAB or r["status"] != v2core.STATUS]
    if bad:
        print("FAIL %d rows with outcome outside vocabulary or wrong status" % len(bad))
        ok = False
    if any(p.get("status") != v2core.STATUS or p.get("origin") not in v2core.ORIGINS for p in props):
        print("FAIL proposition with wrong status or origin")
        ok = False
    print("CHECK", "PASS" if ok else "FAIL", "(%s, %d judgments, %d rows, %d propositions)" % (v2core.VERSION, len(order), len(rows), len(props)))
    sys.exit(0 if ok else 1)


def cmd_ids(args):
    J, order = load_inputs(args.repo, args.commit)
    ids = []
    if args.ids:
        ids += [x.strip() for x in args.ids.split(",") if x.strip()]
    if args.ids_file:
        for line in open(args.ids_file, encoding="utf-8"):
            x = line.strip().split(",")[0].strip()
            if x and x != "judgment_id" and not x.startswith("#"):
                ids.append(x)
    os.makedirs(args.out, exist_ok=True)
    store = TextStore(args.repo, args.commit)
    rows, props = [], []
    for j in ids:
        if j not in J:
            r = {k: "" for k in OUTCOME_COLS}
            r.update({"judgment_id": j, "proceeding": "ALL", "outcome": v2core.UNVERIFIED, "method": "abstain",
                      "abstain_reason": "UNKNOWN_JUDGMENT_ID", "extractor": v2core.VERSION, "status": v2core.STATUS})
            rows.append(r)
            continue
        r, p = process_one(J[j], store)
        rows.extend(r)
        props.extend(p)
    store.close()
    write_atomic(os.path.join(args.out, "OUTCOMES_V2.csv"), outcomes_csv(rows))
    write_atomic(os.path.join(args.out, "PROPOSITIONS_V2.jsonl"), props_jsonl(props))
    print("%s: %d judgment ids -> %d outcome rows, %d propositions in %s" % (v2core.VERSION, len(ids), len(rows), len(props), args.out))


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
