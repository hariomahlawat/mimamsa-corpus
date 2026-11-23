#!/usr/bin/env python3
"""C10 dataset-integrity checks on the crawler data/ tree at the pinned GitHub raw-data commit.

The Hugging Face data/ tree has the same file counts (meta 4327, text 4318, sections 2998, raw 4039) and the same
manifest sizes, but its bytes were not downloaded; every result here is therefore a statement about the GitHub copy.
The Hugging Face copy is marked NOT_CHECKED at byte level in every output row.

Checks: schema validation of every metadata, section and relation record (schemas at the same commit); manifest <->
metadata <-> raw-file <-> text-file consistency; declared SHA-256 against SHA256SUMS and re-hash; duplicate identifiers;
section parent links; relation source and target resolution (dangling references); judgment metadata dates and numbers
against the raw manifest. Read-only; deterministic.

  python check_dataset_integrity.py --repo <git checkout>           write ../outputs/DATASET_INTEGRITY*.csv
  python check_dataset_integrity.py --repo <git checkout> --check   compare with the committed outputs
"""
import argparse, csv, hashlib, io, json, os, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"
COMMIT = "ad77758d4569ba6aafa955cc7843d874489e10f7"
# The raw-data branch carries an older schema/ (v0.1) than its own 0.2.0 records; the HF schema/ files have the same
# sizes as the staging copies, so records are validated against the staging schemas (recorded as a finding).
SCHEMA_COMMIT = "21e73b8348767d5f1524167fcec538e1aad6e732"


def git(repo, *a):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["git", "-c", "core.useReplaceRefs=false", "-C", repo, *a], capture_output=True, check=True, env=env).stdout


def batch(repo, oids):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    p = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
    try:
        for o in oids:
            p.stdin.write((o + "\n").encode()); p.stdin.flush()
            n = int(p.stdout.readline().split()[2]); d = p.stdout.read(n); p.stdout.read(1)
            yield o, d
    finally:
        p.stdin.close(); p.wait()


def validators(repo):
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    schemas = {}
    for name in ("document", "section", "relation", "correspondence"):
        schemas[name] = json.loads(git(repo, "cat-file", "blob", f"{SCHEMA_COMMIT}:schema/{name}.schema.json"))
    reg = Registry().with_resources([(s["$id"], Resource.from_contents(s)) for s in schemas.values()] +
                                    [(f"{n}.schema.json", Resource.from_contents(s)) for n, s in schemas.items()])
    return {n: Draft202012Validator(s, registry=reg) for n, s in schemas.items()}


def run(repo):
    tree = {}
    for line in git(repo, "ls-tree", "-r", "-l", COMMIT, "--", "data/").decode().splitlines():
        meta, path = line.split("\t", 1)
        _, _, oid, size = meta.split()
        tree[path] = (oid, int(size))
    show = lambda p: git(repo, "cat-file", "blob", f"{COMMIT}:{p}")
    sums = {}
    for l in show("data/SHA256SUMS").decode().splitlines():
        h, p = l.split(None, 1); sums[p.strip()] = h
    manifest = list(csv.DictReader(io.StringIO(show("data/manifest.csv").decode("utf-8-sig"))))
    rawman = {r["raw_path"]: r for r in csv.DictReader(io.StringIO(show("data/raw_manifest.csv").decode("utf-8-sig")))}
    V = validators(repo)
    issues = []

    def issue(check, scope, ident, detail):
        issues.append(dict(check=check, scope=scope, id=ident, detail=detail[:300]))

    # metadata records
    meta_paths = sorted(p for p in tree if p.startswith("data/meta/") and p.endswith(".json"))
    metas = {}
    for p, (o, d) in zip(meta_paths, batch(repo, [tree[p][0] for p in meta_paths])):
        try:
            rec = json.loads(d)
        except ValueError as e:
            issue("META_JSON", "meta", p, str(e)); continue
        for err in sorted(V["document"].iter_errors(rec), key=lambda e: list(e.path)):
            issue("META_SCHEMA", "meta", p, f"{'/'.join(map(str, err.path))}: {err.message}")
        stem = p.rsplit("/", 1)[1][:-5]
        if rec.get("doc_id") != stem:
            issue("META_DOCID_FILENAME", "meta", p, f"doc_id {rec.get('doc_id')!r} != filename {stem!r}")
        metas[rec.get("doc_id")] = rec
    ids = Counter(r.get("doc_id") for r in metas.values())
    for k, n in ids.items():
        if n > 1:
            issue("DUPLICATE_DOC_ID", "meta", k, f"{n} records")
    rehash = {}
    raw_paths = sorted(p for p in tree if p.startswith("data/raw/"))
    for p, (o, d) in zip(raw_paths, batch(repo, [tree[p][0] for p in raw_paths])):
        rehash[p] = hashlib.sha256(d).hexdigest()
    used_raw = set()
    for did, rec in sorted(metas.items()):
        rp, sh, tp = rec.get("raw_path"), rec.get("sha256"), rec.get("text_path")
        if rp:
            used_raw.add(rp)
            if rp not in tree:
                issue("META_RAW_MISSING", "meta", did, rp)
            else:
                if sh and rehash.get(rp) != sh:
                    issue("META_SHA_MISMATCH", "meta", did, f"declared {sh} rehash {rehash.get(rp)}")
                if rp in rawman and rawman[rp]["source_url"] and rec.get("source_url") and rawman[rp]["source_url"] != rec["source_url"] \
                        and rec["source_url"] not in (rec.get("source_aliases") or []):
                    issue("META_URL_DIFFERS_FROM_RAW_MANIFEST", "meta", did, f"{rec['source_url']} vs {rawman[rp]['source_url']}")
                if rp in rawman and rawman[rp]["retrieved_at"] and rec.get("retrieved_at") and rawman[rp]["retrieved_at"] != rec["retrieved_at"]:
                    issue("META_RETRIEVED_AT_DIFFERS", "meta", did, f"{rec['retrieved_at']} vs {rawman[rp]['retrieved_at']}")
        if tp and tp not in tree:
            issue("META_TEXT_MISSING", "meta", did, tp)
        if rec.get("doc_type") == "judgment":
            if not rec.get("case_numbers"):
                issue("JUDGMENT_NO_CASE_NUMBER", "meta", did, "case_numbers empty")
            if not rec.get("issue_date"):
                issue("JUDGMENT_NO_DATE", "meta", did, "issue_date null")
            fn = rec.get("original_filename") or ""
            if rec.get("issue_date") and fn.count("_") >= 2 and fn.rsplit("_", 1)[-1][:10] != rec["issue_date"] and fn.rsplit("_", 1)[-1][:4].isdigit():
                issue("JUDGMENT_DATE_DIFFERS_FROM_FILENAME", "meta", did, f"issue_date {rec['issue_date']} vs filename {fn}")
        for rel in rec.get("relations") or []:
            for err in V["relation"].iter_errors(rel):
                issue("META_RELATION_SCHEMA", "meta", did, err.message)
    users = defaultdict(list)
    for did, rec in metas.items():
        users[rec.get("raw_path")].append(did)
    for rp, dids in sorted(users.items(), key=lambda x: str(x[0])):
        if rp is None:
            for did in sorted(dids):
                issue("META_WITHOUT_RAW_FILE", "meta", did, str(metas[did].get("doc_type")))
        elif len(dids) > 1:
            issue("RAW_FILE_SHARED_BY_MULTIPLE_META", "raw", rp, f"{len(dids)} records: " + ", ".join(sorted(dids)[:6]))
    for p in raw_paths:
        if p not in used_raw and not p.endswith(".json"):
            listing = any(((r.get("source_record") or {}).get("listing_raw_path") == p) for r in metas.values())
            if not listing:
                issue("RAW_FILE_WITHOUT_META", "raw", p, rawman.get(p, {}).get("title", ""))
    text_paths = {p for p in tree if p.startswith("data/text/")}
    referenced_text = {r.get("text_path") for r in metas.values() if r.get("text_path")}
    for p in sorted(text_paths - referenced_text):
        issue("TEXT_WITHOUT_META", "text", p, "")
    # manifest.csv rows
    mids = Counter(r["doc_id"] for r in manifest)
    for r in manifest:
        m = metas.get(r["doc_id"])
        if m is None:
            issue("MANIFEST_ROW_WITHOUT_META", "manifest", r["doc_id"], ""); continue
        if r["sha256"] and m.get("sha256") and r["sha256"] != m["sha256"]:
            issue("MANIFEST_SHA_DIFFERS_FROM_META", "manifest", r["doc_id"], f"{r['sha256']} vs {m['sha256']}")
        if r["status"] and m.get("status") and r["status"] != m["status"]:
            issue("MANIFEST_STATUS_DIFFERS_FROM_META", "manifest", r["doc_id"], f"{r['status']} vs {m['status']}")
    for k, n in mids.items():
        if n > 1:
            issue("MANIFEST_DUPLICATE_DOC_ID", "manifest", k, f"{n} rows")
    for d in sorted(set(metas) - set(mids)):
        issue("META_NOT_IN_MANIFEST", "manifest", d, "")
    # sections
    sec_paths = sorted(p for p in tree if p.startswith("data/sections/"))
    sec_ids = Counter()
    for p, (o, d) in zip(sec_paths, batch(repo, [tree[p][0] for p in sec_paths])):
        rec = json.loads(d)
        for err in V["section"].iter_errors(rec):
            issue("SECTION_SCHEMA", "sections", p, f"{'/'.join(map(str, err.path))}: {err.message}")
        sec_ids[rec.get("section_id")] += 1
        if rec.get("parent_doc_id") not in metas:
            issue("SECTION_PARENT_MISSING", "sections", p, str(rec.get("parent_doc_id")))
        if p.split("/")[2] != rec.get("parent_doc_id"):
            issue("SECTION_DIR_PARENT_MISMATCH", "sections", p, str(rec.get("parent_doc_id")))
    for k, n in sec_ids.items():
        if n > 1:
            issue("DUPLICATE_SECTION_ID", "sections", k, f"{n}")
    # relations.jsonl
    known = set(metas) | set(sec_ids)
    rel_lines = show("data/relations.jsonl").decode().splitlines()
    for i, line in enumerate(rel_lines, 1):
        rel = json.loads(line)
        for err in V["relation"].iter_errors(rel):
            issue("RELATION_SCHEMA", "relations", f"line {i}", err.message)
        if rel.get("source_doc_id") not in known:
            issue("RELATION_SOURCE_DANGLING", "relations", f"line {i}", str(rel.get("source_doc_id")))
        t = rel.get("target_doc_id")
        if t and t not in known:
            issue("RELATION_TARGET_DANGLING", "relations", f"line {i}", t)
    # correspondence tables
    for p in sorted(x for x in tree if x.startswith("data/correspondence/")):
        for i, line in enumerate(show(p).decode().splitlines(), 1):
            for err in V["correspondence"].iter_errors(json.loads(line)):
                issue("CORRESPONDENCE_SCHEMA", "correspondence", f"{p}:{i}", err.message)
    # stale schema copy on the raw-data branch
    for name in ("document", "section", "relation", "correspondence"):
        try:
            a = git(repo, "cat-file", "blob", f"{COMMIT}:schema/{name}.schema.json")
        except subprocess.CalledProcessError:
            a = b""
        b = git(repo, "cat-file", "blob", f"{SCHEMA_COMMIT}:schema/{name}.schema.json")
        if a != b:
            issue("RAW_DATA_SCHEMA_DIFFERS_FROM_CURRENT", "schema", f"schema/{name}.schema.json",
                  f"raw-data copy {len(a)} bytes vs staging {len(b)} bytes (HF listing shows the staging size)")
    # SHA256SUMS
    for p, h in sums.items():
        if rehash.get(p) != h:
            issue("SHA256SUMS_MISMATCH", "raw", p, f"declared {h} rehash {rehash.get(p)}")
    unresolved_targets = sum(1 for l in rel_lines if json.loads(l).get("target_doc_id") is None)
    summary = [
        ("meta_records", len(meta_paths)), ("judgment_meta_records", sum(1 for r in metas.values() if r.get("doc_type") == "judgment")),
        ("section_records", len(sec_paths)), ("text_files", len(text_paths)), ("raw_files", len(raw_paths)),
        ("manifest_rows", len(manifest)), ("relations_lines", len(rel_lines)), ("relations_unresolved_target_refs_raw_only", unresolved_targets),
        ("raw_files_rehashed_equal_to_SHA256SUMS", sum(1 for p, h in sums.items() if rehash.get(p) == h))]
    by_check = Counter(i["check"] for i in issues)
    srows = [dict(item="schemas_validated_against", value="staging " + SCHEMA_COMMIT[:8], scope="schema/", hf_copy="HF schema/ sizes equal staging")]
    srows += [dict(item=k, value=v, scope="GitHub raw-data " + COMMIT[:8], hf_copy="NOT_CHECKED (same counts; bytes not downloaded)") for k, v in summary]
    srows += [dict(item="issue:" + k, value=v, scope="GitHub raw-data " + COMMIT[:8], hf_copy="NOT_CHECKED") for k, v in sorted(by_check.items())]
    issues.sort(key=lambda r: (r["check"], r["scope"], r["id"], r["detail"]))
    buf1, buf2 = io.StringIO(), io.StringIO()
    w = csv.DictWriter(buf1, ["item", "value", "scope", "hf_copy"], lineterminator="\n"); w.writeheader(); w.writerows(srows)
    w = csv.DictWriter(buf2, ["check", "scope", "id", "detail"], lineterminator="\n"); w.writeheader(); w.writerows(issues)
    return {"DATASET_INTEGRITY_SUMMARY.csv": buf1.getvalue(), "DATASET_INTEGRITY_ISSUES.csv": buf2.getvalue()}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    out = run(a.repo)
    if a.check:
        bad = [k for k, v in out.items() if not (OUT / k).is_file() or (OUT / k).read_text(encoding="utf-8") != v]
        if bad:
            print("INTEGRITY CHECK FAILED: " + ", ".join(bad), file=sys.stderr); return 1
        print(f"dataset integrity outputs reproduce ({len(out)} files)"); return 0
    for k, v in out.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print(f"wrote {len(out)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
