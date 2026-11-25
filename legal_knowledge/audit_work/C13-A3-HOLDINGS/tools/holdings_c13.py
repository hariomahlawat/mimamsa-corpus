#!/usr/bin/env python3
"""Mimamsa C13-A3 holdings / legal-proposition extractor driver (c13-holdings).

Commands (run from any directory; Python 3.11+, standard library only at extraction time):
  run   [--exclude-ids F]                 extract the SC scope (C12 SCOPE_C12.csv) into outputs/, write
                                          OUTPUT_SHA256SUMS and RUN_META.json
  ids   --ids-file F --out-dir D [--exclude-ids F] [--all-passages]
                                          extract any list of judgment_ids (blind evaluation entry point)
  check                                   verify tool/model hashes against RUN_META.json and re-extract the scope
                                          in memory, comparing every output byte for byte
Global options (before the command): --repo /home/user/c7 --commit ad77758d --model ../model/c13_holdings_model.json

Outputs
  HOLDINGS_C13.jsonl          items: question_of_law, holding, dissent_holding_candidate,
                              split_opinion_holding_candidate, obiter, operative_direction
  HOLDINGS_C13_JUDGMENTS.csv  one row per judgment: text status, opinions with roles, class counts
  PASSAGES_C13.tsv.gz         every body sentence: offsets, page, opinion id, passage class, p_holding, p_issue
                              (deterministic gzip, mtime 0)
Every item: status AUTOMATED_CANDIDATE_NOT_VERIFIED. No ratio is verified, no overruling inferred.
The FOUO-marked RAF 2000 copy (sha256 4284820e...) is refused if ever requested.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c13_corpus as cc  # noqa: E402
import c13_extract as cx  # noqa: E402
import c13_features as cf  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "outputs")
DEF_MODEL = os.path.join(ROOT, "model", "c13_holdings_model.json")
TOOL_FILES = ["c13_corpus.py", "c13_segment.py", "c13_features.py", "c13_extract.py", "holdings_c13.py"]
C12_DEPS = [os.path.join(cc.C12_TOOLS, "holdings_core.py"), os.path.join(cc.C12_TOOLS, "holdings_c12.py")]
JCOLS = ["judgment_id", "sha256", "doc_id", "court", "text_status", "excluded_reason", "body_start_page", "body_start_method",
         "n_opinions", "opinions", "n_numbered_paragraphs", "n_quote_spans", "n_sentences"] + ["n_" + c for c in cx.PASSAGE_CLASSES] + \
        ["n_items_holding", "n_items_dissent_holding_candidate", "n_items_split_opinion_holding_candidate", "extractor", "status"]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    with open(p, "rb") as f:
        return sha256_bytes(f.read())


def tool_hashes(model_path):
    h = {fn: sha256_file(os.path.join(HERE, fn)) for fn in TOOL_FILES}
    for p in C12_DEPS:
        h["C12:" + os.path.basename(p)] = sha256_file(p)
    h["model:" + os.path.basename(model_path)] = sha256_file(model_path)
    return h


def extract(ids, repo, commit, model_path, exclude=(), all_passages=False):
    model = cf.Model(model_path)
    J = cc.load_corpus(repo, commit)
    ts = cc.TextStore(repo, commit)
    items, jrows, passages = [], [], []
    for jid in ids:
        row = {k: "" for k in JCOLS}
        row.update({"judgment_id": jid, "extractor": cx.VERSION, "status": cx.STATUS})
        if jid in exclude:
            row["text_status"], row["excluded_reason"] = "EXCLUDED", "EXCLUDE_IDS"
            jrows.append(row)
            continue
        j = J.get(jid)
        if not j:
            row["text_status"] = "UNKNOWN_JUDGMENT_ID"
            jrows.append(row)
            continue
        row.update({"sha256": j["sha256"], "doc_id": j["text_doc"], "court": j["court"]})
        if j["sha256"] in cc.EXCLUDED_SHA256:
            row["text_status"], row["excluded_reason"] = "EXCLUDED", "RESTRICTED_FOUO_COPY"
            jrows.append(row)
            continue
        text, _ = ts.get(j["text_doc"]) if j["text_doc"] else (None, "")
        if not text:
            row["text_status"] = "NO_TEXT_LAYER_AT_COMMIT"
            jrows.append(row)
            continue
        meta = {"judgment_id": jid, "sha256": j["sha256"], "court": j["court"], "text_doc": j["text_doc"]}
        summ, its, pas, _ = cx.analyze(text, meta, model, all_passages=all_passages)
        row["text_status"] = "TEXT_LAYER_READ"
        for k in ("body_start_page", "body_start_method", "n_opinions", "opinions", "n_numbered_paragraphs", "n_quote_spans", "n_sentences"):
            row[k] = summ[k]
        for c in cx.PASSAGE_CLASSES:
            row["n_" + c] = summ["counts"].get(c, 0)
        for t in ("holding", "dissent_holding_candidate", "split_opinion_holding_candidate"):
            row["n_items_" + t] = sum(1 for x in its if x["item_type"] == t)
        items.extend(its)
        for p in pas:
            passages.append((jid,) + p)
        jrows.append(row)
    ts.close()
    return items, jrows, passages


def render(items, jrows, passages):
    jl = "".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n" for x in items).encode("utf-8")
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=JCOLS, lineterminator="\n")
    w.writeheader()
    for r in jrows:
        w.writerow(r)
    jc = s.getvalue().encode("utf-8")
    t = io.StringIO()
    t.write("judgment_id\tchar_start\tchar_end\tpage\topinion_id\tpassage_class\tp_holding\tp_issue\n")
    for p in passages:
        t.write("\t".join("" if v is None else str(v) for v in p) + "\n")
    bio = io.BytesIO()
    with gzip.GzipFile(fileobj=bio, mode="wb", mtime=0, filename="") as g:
        g.write(t.getvalue().encode("utf-8"))
    return {"HOLDINGS_C13.jsonl": jl, "HOLDINGS_C13_JUDGMENTS.csv": jc, "PASSAGES_C13.tsv.gz": bio.getvalue()}


def scope_ids():
    return [r["judgment_id"] for r in cc.sc_scope()]


def write(outdir, files, meta):
    os.makedirs(outdir, exist_ok=True)
    for fn, b in files.items():
        with open(os.path.join(outdir, fn), "wb") as f:
            f.write(b)
    with open(os.path.join(outdir, "OUTPUT_SHA256SUMS"), "w", encoding="utf-8") as f:
        for fn in sorted(files):
            f.write("%s  %s\n" % (sha256_bytes(files[fn]), fn))
    with open(os.path.join(outdir, "RUN_META.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1, sort_keys=True)
        f.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=cc.DEF_REPO)
    ap.add_argument("--commit", default=cc.DEF_COMMIT)
    ap.add_argument("--model", default=DEF_MODEL)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--exclude-ids", default="")
    i = sub.add_parser("ids")
    i.add_argument("--ids-file", required=True)
    i.add_argument("--out-dir", required=True)
    i.add_argument("--exclude-ids", default="")
    i.add_argument("--all-passages", action="store_true")
    sub.add_parser("check")
    a = ap.parse_args(argv)
    if a.cmd in ("run", "ids"):
        exclude = set(cc.read_ids(a.exclude_ids))
        ids = scope_ids() if a.cmd == "run" else cc.read_ids(a.ids_file)
        items, jrows, passages = extract(ids, a.repo, a.commit, a.model, exclude, getattr(a, "all_passages", False))
        files = render(items, jrows, passages)
        meta = {"extractor": cx.VERSION, "command": a.cmd, "repo_commit": a.commit, "tool_sha256": tool_hashes(a.model),
                "n_ids": len(ids), "n_items": len(items), "exclude_ids_sha256": sha256_file(a.exclude_ids) if a.exclude_ids else None,
                "excluded_ids": sorted(exclude), "ids_file_sha256": sha256_file(a.ids_file) if a.cmd == "ids" else None,
                "status": cx.STATUS, "external_calls": "none"}
        write(OUT if a.cmd == "run" else a.out_dir, files, meta)
        counts = {}
        for x in items:
            counts[x["item_type"]] = counts.get(x["item_type"], 0) + 1
        print(len(ids), "ids;", len(items), "items;", json.dumps(counts, sort_keys=True))
    elif a.cmd == "check":
        with open(os.path.join(OUT, "RUN_META.json"), encoding="utf-8") as f:
            meta = json.load(f)
        bad = []
        now = tool_hashes(a.model)
        for k, v in meta["tool_sha256"].items():
            if now.get(k) != v:
                bad.append("tool hash differs: %s" % k)
        excl = set(meta.get("excluded_ids") or [])
        items, jrows, passages = extract(scope_ids(), a.repo, a.commit, a.model, excl)
        files = render(items, jrows, passages)
        want = {}
        with open(os.path.join(OUT, "OUTPUT_SHA256SUMS"), encoding="utf-8") as f:
            for ln in f:
                h, fn = ln.split()
                want[fn] = h
        for fn, b in files.items():
            if want.get(fn) != sha256_bytes(b):
                bad.append("output differs: %s" % fn)
        if bad:
            print("CHECK FAILED\n" + "\n".join(bad))
            sys.exit(1)
        print("CHECK OK: %d files byte-identical; tool and model hashes match" % len(files))


if __name__ == "__main__":
    main()
