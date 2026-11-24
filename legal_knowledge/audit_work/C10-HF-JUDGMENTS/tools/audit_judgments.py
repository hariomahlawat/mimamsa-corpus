#!/usr/bin/env python3
"""C10 complete Hugging Face judicial-corpus audit: enumeration, checkpointed batch extraction, assembly.

Collections (all enumerated; every item gets an explicit disposition):
  A. judgment metadata records   data/meta/*.json with doc_type == judgment            (HF data/meta; GitHub raw-data copy)
  B. judgment source files       data/raw/sci/**, data/raw/hc/**                       (HF data/raw; byte source: GitHub raw-data,
                                                                                        whose SHA-256 equals the HF declared SHA-256)
  C. curated judgment binaries   legal_knowledge/judgment_originals|judgment_sources/** (HF only; bytes processed only where an
                                                                                        identical-SHA working copy is held)
  D. excluded judgments          data/excluded_judgments.jsonl                          (log only: files were not retained)

Commands:
  python audit_judgments.py extract  --repo <git checkout> [--batch-size 200] [--workers 4] [--only N]
        process distinct judgment files in deterministic batches; each batch is written to work/batches/batch_NNNN.jsonl with
        its input list; an existing batch whose input list matches is skipped (resume). --only N stops after N new batches.
  python audit_judgments.py assemble --repo <git checkout> [--check]
        build outputs/ from the batches; writes CONTINUATION_MANIFEST.csv for anything not yet processed.
HF bytes are never downloaded here: source-document verification means the GitHub raw-data object re-hashed equal to the HF
declared SHA-256 (or a working copy re-hashed equal to the HF sidecar SHA-256). That is stated in every output.
"""
import argparse, csv, hashlib, io, json, os, re, subprocess, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
WORK = PKG / "work" / "batches"
OUT = PKG / "outputs"
sys.path.insert(0, str(HERE))
import jextract as J  # noqa: E402

RAW = "ad77758d4569ba6aafa955cc7843d874489e10f7"
STAGING = "21e73b8348767d5f1524167fcec538e1aad6e732"
RECON_INV = PKG.parent / "C10-RECONCILIATION" / "outputs" / "UNIFIED_CORPUS_INVENTORY.csv"
SIDECARS = PKG.parent / "C10-RECONCILIATION" / "inputs" / "hf_snapshot" / "lk_declared_sidecars.tsv"
HELD_MANIFEST = "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv"
CASES = "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
COPY_REG = "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/source_copy_register.csv"


def env():
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(repo, *a):
    return subprocess.run(["git", "-c", "core.useReplaceRefs=false", "-C", repo, *a], capture_output=True, check=True, env=env()).stdout


def scratch_root():
    """The C5 working store root: the directory holding downloads/ and mml_x/ (passed via MIMAMSA_WORKING_STORE)."""
    return os.environ.get("MIMAMSA_WORKING_STORE", "")


# ---------------------------------------------------------------- enumeration
def enumerate_all(repo):
    tree = {}
    for line in git(repo, "ls-tree", "-r", "-l", RAW, "--", "data/").decode().splitlines():
        meta, path = line.split("\t", 1)
        _, _, oid, size = meta.split()
        tree[path] = (oid, int(size))
    sums = {}
    for l in git(repo, "cat-file", "blob", f"{RAW}:data/SHA256SUMS").decode().splitlines():
        h, p = l.split(None, 1); sums[p.strip()] = h
    meta_paths = sorted(p for p in tree if p.startswith("data/meta/"))
    metas = []
    p = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env())
    for path in meta_paths:
        p.stdin.write((tree[path][0] + "\n").encode()); p.stdin.flush()
        n = int(p.stdout.readline().split()[2]); d = json.loads(p.stdout.read(n)); p.stdout.read(1)
        if d.get("doc_type") == "judgment":
            d["_meta_path"] = path
            metas.append(d)
    p.stdin.close(); p.wait()
    files = {}
    for path, (oid, size) in sorted(tree.items()):
        if path.startswith(("data/raw/sci/", "data/raw/hc/")):
            files[sums[path]] = dict(sha256=sums[path], location="HF_DATA_RAW+GITHUB_RAW_DATA", path=path, oid=oid, bytes=size,
                                     byte_source="github_raw_data")
    side = list(csv.DictReader(open(SIDECARS, encoding="utf-8"), delimiter="\t"))
    held = {r["rehashed_sha256"]: r["held_path"] for r in csv.DictReader(io.StringIO(git(repo, "cat-file", "blob", f"{STAGING}:{HELD_MANIFEST}").decode()))}
    for r in side:
        h = r["declared_sha256"]
        if h in files:
            continue
        files[h] = dict(sha256=h, location="HF_LEGAL_KNOWLEDGE_ONLY", path=r["path"], oid="", bytes=int(r["declared_bytes"]),
                        byte_source=("working_store:" + held[h]) if h in held else "NOT_AVAILABLE")
    return metas, files


def batch_plan(files, size):
    shas = sorted(files)
    return [shas[i:i + size] for i in range(0, len(shas), size)]


# ---------------------------------------------------------------- extraction worker
def _work(args):
    repo, item = args
    import pymupdf as fitz
    fitz.TOOLS.mupdf_display_errors(False)
    rec = {"sha256": item["sha256"], "path": item["path"], "location": item["location"], "byte_source": item["byte_source"]}
    data = None
    if item["byte_source"] == "github_raw_data":
        data = git(repo, "cat-file", "blob", item["oid"])
    elif item["byte_source"].startswith("working_store:"):
        root = scratch_root()
        fp = os.path.join(root, item["byte_source"].split(":", 1)[1]) if root else ""
        if fp and os.path.isfile(fp):
            data = open(fp, "rb").read()
    if data is None:
        rec.update(integrity="NOT_AVAILABLE", extraction="NOT_PROCESSED_BYTES_UNAVAILABLE")
        return rec
    h = hashlib.sha256(data).hexdigest()
    rec["pdf_eof_marker"] = b"%%EOF" in data[-2048:]
    rec["rehash_sha256"] = h
    rec["integrity"] = "SHA256_MATCH" if h == item["sha256"] else "SHA256_MISMATCH"
    if rec["integrity"] != "SHA256_MATCH":
        rec["extraction"] = "NOT_PROCESSED_HASH_MISMATCH"
        return rec
    try:
        rec.update(J.extract(data, fitz))
        rec["extraction"] = "PROCESSED" if rec.get("pdf_status") == "OPENED" else "PROCESSED_UNREADABLE_PDF"
    except Exception as e:  # noqa: BLE001  a damaged PDF is an audit result, recorded, never a crash
        rec.update(pdf_status="UNREADABLE", pdf_error=f"{type(e).__name__}: {str(e)[:200]}", extraction="PROCESSED_UNREADABLE_PDF")
    if rec.get("extraction") == "PROCESSED_UNREADABLE_PDF" and not rec["pdf_eof_marker"]:
        rec["extraction"] = "INCOMPLETE_COPY_TRUNCATED"
    return rec


def cmd_extract(a):
    metas, files = enumerate_all(a.repo)
    plan = batch_plan(files, a.batch_size)
    WORK.mkdir(parents=True, exist_ok=True)
    done_new = 0
    for i, shas in enumerate(plan):
        bp = WORK / f"batch_{i:04d}.jsonl"
        key = hashlib.sha256("\n".join(shas).encode()).hexdigest()
        if bp.is_file():
            head = json.loads(bp.read_text(encoding="utf-8").splitlines()[0])
            if head.get("input_key") == key and head.get("extractor") == J.EXTRACTOR_VERSION:
                continue
        if a.only is not None and done_new >= a.only:
            break
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            res = list(ex.map(_work, [(a.repo, files[s]) for s in shas], chunksize=4))
        res.sort(key=lambda r: r["sha256"])
        lines = [json.dumps({"batch": i, "input_key": key, "extractor": J.EXTRACTOR_VERSION, "count": len(shas), "shas": shas}, sort_keys=True)]
        lines += [json.dumps(r, sort_keys=True, ensure_ascii=False) for r in res]
        tmp = bp.with_suffix(".tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp.replace(bp)
        done_new += 1
        print(f"batch {i:04d}: {len(shas)} files", flush=True)
    print(f"plan: {len(plan)} batches of <= {a.batch_size}; new this run: {done_new}")
    return 0


def summary_md(st, review):
    f, m = st["file_dispositions"], st["record_dispositions"]
    proc = f.get("PROCESSED", 0)
    L = ["# Hugging Face judicial corpus audit: summary (generated)", "",
         "Generated by `tools/audit_judgments.py assemble` from the persisted batches in `work/batches/`. Every value in the "
         "extraction outputs is an **automated candidate read from the PDF text layer**. Nothing is legally verified by this audit.", "",
         "## Inventory (independently recomputed; the historical figure of about 3,413 judgment records is superseded)", "",
         f"- Judgment metadata records (HF `data/meta`, `doc_type = judgment`): **{st['metadata_records']}**.",
         f"- Distinct judgment source files: **{st['source_files']}**, by location {json.dumps(st['files_by_location'], sort_keys=True)}.",
         f"- Distinct judgments, counted by source file (a common judgment disposing of connected matters is one file serving many records): **{st['distinct_judgments']}**.",
         f"- Excluded judgments in `data/excluded_judgments.jsonl`: **{st['excluded_records']}**. Their files were not retained. Dispositions: {json.dumps(st['excluded_dispositions'], sort_keys=True)}.", "",
         "## Completion accounting (identities asserted by the builder)", "",
         f"- Source files: {st['source_files']} = processed {proc} + unprocessed or unresolved {st['source_files'] - proc} {json.dumps({k: v for k, v in f.items() if k != 'PROCESSED'}, sort_keys=True)}.",
         f"- Metadata records: {st['metadata_records']} = {' + '.join(f'{k} {v}' for k, v in m.items())}.",
         f"- Excluded-log records: {st['excluded_records']}, each with an explicit disposition in `HF_JUDGMENT_EXCLUDED_DISPOSITIONS.csv.gz`.",
         f"- Batches: {st['batches_complete']} of {st['batches']} complete. Anything unprocessed is listed in `CONTINUATION_MANIFEST.csv`.", "",
         "## Three coverage measures (kept separate)", "",
         f"1. **Automated processing coverage:** {proc} of {st['source_files']} source files ({100 * proc / st['source_files']:.1f}%) were opened and processed by the "
         "extractor (case numbers, dates, citations, statutes, topics, outcome phrase, candidate propositions, relevance).",
         f"2. **Source-document verification coverage:** {proc} of {st['source_files']} files were re-hashed equal to the HF-declared SHA-256. The bytes came from the GitHub "
         "`raw-data` mirror, or for curated binaries from an identical working copy. **HF-hosted bytes themselves: NOT_CHECKED** (no download access; HF revision not pinned).",
         f"3. **Independent legal-review coverage:** {review}", "",
         "## Results (automated)", "",
         f"- Relevance classes: {json.dumps(st['relevance'], sort_keys=True)}.",
         f"- Text layer: {json.dumps(st['text_extraction'], sort_keys=True)}.",
         f"- Metadata date against text: {json.dumps(st['date_status'], sort_keys=True)}.",
         f"- Metadata case number against text: {json.dumps(st['case_number_status'], sort_keys=True)}.",
         f"- Neutral citation against text: {json.dumps(st['neutral_citation_status'], sort_keys=True)}.",
         f"- Outcome phrase candidates: {json.dumps(st['outcome'], sort_keys=True)}; conflicting phrases in {st['outcome_conflicts']}.",
         f"- Candidate propositions extracted (page and paragraph pinpoints): {st['propositions']}.",
         f"- Duplicate and version groups: {json.dumps(st['duplicates'], sort_keys=True)}.",
         f"- Relationships: {json.dumps(st['relationships'], sort_keys=True)}; curated Mimamsa cases matched deterministically: {st['curated_cases_matched']} of 53.", "",
         "## Distribution", "", "| Court | Records |", "| --- | --- |"]
    L += [f"| {k} | {v} |" for k, v in sorted(st["courts"].items(), key=lambda x: -x[1])]
    L += ["", "| Year | Records |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in st["years"].items()]
    L += ["", "| Excluded log by court | Records |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in sorted(st["excluded_by_court"].items(), key=lambda x: -x[1])]
    L += ["", "## Limits", "",
          "- Automated extraction can be wrong: dates, case numbers, outcome phrases and propositions are candidates for human checking (see `HF_JUDGMENT_VERIFICATION_QUEUE.csv`).",
          "- Relevance is assigned by fixed term rules. The excluded log was filtered by the crawler for military keywords, and its files were not retained. "
          "Re-screening those judgments for general-law relevance needs the files, and acquiring them is not authorised here. Titles were re-screened instead.",
          "- No judgment has been legally verified. Holdings are not cleared for use."]
    return "\n".join(L) + "\n"


def cmd_assemble(a):
    import jassemble
    out, binary, st = jassemble.build(a.repo)
    rev = PKG / "review" / "INDEPENDENT_REVIEW_COVERAGE.txt"
    review = rev.read_text(encoding="utf-8").strip() if rev.is_file() else "none yet: no judgment in this collection has received independent legal review in this audit."
    out["HF_JUDGMENT_AUDIT_SUMMARY.md"] = summary_md(st, review)
    manifest = dict(schema="c10-hf-judgment-audit/1", raw_data_commit=RAW, staging_commit=STAGING, extractor=J.EXTRACTOR_VERSION,
                    hf_bytes="NOT_CHECKED", hf_revision="UNPINNED", stats=st,
                    outputs={k: hashlib.sha256(v.encode()).hexdigest() for k, v in sorted(out.items())},
                    binary_outputs={k: hashlib.sha256(v).hexdigest() for k, v in binary.items()})
    out["AUDIT_MANIFEST.json"] = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    if a.check:
        bad = [k for k, v in out.items() if not (OUT / k).is_file() or (OUT / k).read_text(encoding="utf-8") != v]
        bad += [k for k, v in binary.items() if not (OUT / k).is_file() or (OUT / k).read_bytes() != v]
        if bad:
            print("JUDGMENT AUDIT CHECK FAILED: " + ", ".join(bad), file=sys.stderr)
            return 1
        print(f"judgment audit outputs reproduce ({len(out) + len(binary)} files)")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for k, v in out.items():
        (OUT / k).write_text(v, encoding="utf-8")
    for k, v in binary.items():
        (OUT / k).write_bytes(v)
    print(f"wrote {len(out) + len(binary)} files")
    return 0


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "assemble":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--check", action="store_true")
    sys.exit(cmd_assemble(ap.parse_args()))


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "extract":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", type=int)
    sys.exit(cmd_extract(ap.parse_args()))
