#!/usr/bin/env python3
"""C12 revision-pinned byte verification of the Hugging Face dataset
hariomahlawat/mimamsa-corpus.  READ-ONLY on Hugging Face.

Modes
  capture  list every file at the pinned revision, stream-download each one
           (max 4 concurrent, backoff on 429/5xx), compute sha256, git-blob-sha1
           and size, analyse PDFs (PyMuPDF opens, trailing %%EOF, text-layer
           marking scan), then write HASH_LEDGER.csv.gz, CAPTURE_META.json and
           capture_refs/ (gzip copies of the small HF reference files that the
           report cross-checks: SHA256SUMS, manifests, PACKAGE_SHA256SUMS).
           A complete HF copy of a known-incomplete judgment that differs from
           the stored copy is saved under <scratch>/hf_retrieved_c12/<sha256>/.
           Nothing is ever overwritten.
  report   derive SUMMARY.json, REPORT.md, DISCREPANCIES.csv,
           HF_VS_GIT_PATHS.csv, INCOMPLETE_FILES_HF.csv, MARKING_HITS.csv,
           HF_RETRIEVED_CANDIDATES.csv and SHA256SUMS from the ledger, the
           capture refs and git (c7 @ ad77758d, worktree staging branch).
  report --check  regenerate everything in memory and byte-compare with the
           files on disk (also re-derives every ledger status).

Authentication is injected by the network proxy; this script never reads,
sets or logs a token.
"""
import argparse, csv, gzip, hashlib, io, json, os, re, subprocess, sys, time
import threading, random, shutil, tempfile, collections
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = "hariomahlawat/mimamsa-corpus"
REV = "5524c3d99b6a069249012fecea75093b875a22c7"
C7 = "/home/user/c7"
C7_COMMIT = "ad77758d"
STAGING_REF = "origin/legal-knowledge/v2.5-staging"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)                       # hf_verification_c12/
WT = os.path.abspath(os.path.join(OUT, "..", "..", "..", ".."))   # worktree root
SCRATCH = os.path.dirname(WT)
RETRIEVED_DIR = os.path.join(SCRATCH, "hf_retrieved_c12")
INCOMPLETE_LIST = "legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/identity/outputs/INCOMPLETE_23_RECOVERY_PLAN.csv"
ACQ_MANIFEST = "legal_knowledge/audit_work/C12-CONSOLIDATION/acquisition/ACQUISITION_MANIFEST.csv"
C5_DIR = "legal_knowledge/preservation/c5_working_store/"
REF_FILES = ["data/SHA256SUMS", "data/manifest.csv", "data/raw_manifest.csv",
             C5_DIR + "PACKAGE_SHA256SUMS", C5_DIR + "STAGED_SHA256SUMS"]
KNOWN_FOUO = "4284820e"

LEDGER_COLS = ["path", "size", "hf_oid", "lfs_sha256", "computed_size",
               "computed_sha256", "computed_git_sha1", "download_attempts",
               "download_log", "is_pdf", "pdf_opens", "pdf_pages",
               "pdf_text_errors", "trailing_eof", "marking_terms",
               "marking_line_hits", "marking_context", "retrieved_to",
               "statuses"]

TERMS = [("for_official_use_only", r"for\s+official\s+use\s+only"),
         ("restricted", r"\brestricted\b"),
         ("confidential", r"\bconfidential\b"),
         ("secret", r"\bsecret\b")]


# ------------------------------------------------------------------ helpers
def git(*args, cwd=C7, binary=False):
    r = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8")


def git_blob_sha1_file(fp, size):
    h = hashlib.sha1(b"blob %d\0" % size)
    with open(fp, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sanitize_err(s):
    """Remove temp-file paths from PyMuPDF error strings (determinism)."""
    return re.sub(r"'[^']*/tmp/[^']*('|$)", "'<tmpfile>'", s)


def clean(s, n=160):
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


# ------------------------------------------------------------- PDF analysis
def analyse_pdf(fp):
    """Runs in a worker process. Returns dict."""
    import pymupdf
    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    res = {"pdf_opens": "", "pdf_pages": "", "pdf_text_errors": "",
           "trailing_eof": "", "marking_terms": "", "marking_line_hits": "",
           "marking_context": ""}
    with open(fp, "rb") as f:
        f.seek(0, 2); n = f.tell(); f.seek(max(0, n - 1024)); tail = f.read()
    res["trailing_eof"] = "YES" if b"%%EOF" in tail else "NO"
    try:
        doc = pymupdf.open(fp)
    except Exception as e:  # noqa
        res["pdf_opens"] = "NO:" + clean(sanitize_err(type(e).__name__ + " " + str(e)), 80)
        return res
    try:
        npages = doc.page_count
    except Exception as e:
        res["pdf_opens"] = "NO:" + clean(str(e), 80)
        return res
    res["pdf_opens"] = "YES" if npages > 0 else "NO:zero_pages"
    res["pdf_pages"] = str(npages)
    counts = collections.Counter(); lines = collections.Counter(); ctx = {}
    errors = 0
    for i in range(npages):
        try:
            t = doc.load_page(i).get_text("text")
        except Exception:
            errors += 1
            continue
        for key, rx in TERMS:
            for m in re.finditer(rx, t, flags=re.I):
                counts[key] += 1
                if key not in ctx:
                    a, b = max(0, m.start() - 70), min(len(t), m.end() + 70)
                    ctx[key] = "p%d: %s" % (i + 1, clean(t[a:b]))
        # heuristic "marking-like" line: the term in UPPER CASE (or FOUO in any
        # case) forming a short line of its own (<= 40 characters)
        for ln in t.splitlines():
            s = ln.strip()
            if not s or len(s) > 40:
                continue
            for key, rx in TERMS:
                m = re.search(rx, s, flags=re.I)
                if m and (key == "for_official_use_only" or m.group(0).isupper()):
                    lines[key] += 1
                    k2 = key + "_line"
                    if k2 not in ctx:
                        ctx[k2] = "p%d: %s" % (i + 1, clean(s))
    doc.close()
    res["pdf_text_errors"] = str(errors)
    res["marking_terms"] = ";".join("%s=%d" % (k, counts[k]) for k, _ in TERMS if counts[k])
    res["marking_line_hits"] = ";".join("%s=%d" % (k, lines[k]) for k, _ in TERMS if lines[k])
    res["marking_context"] = " | ".join("%s: %s" % (k, ctx[k]) for k in sorted(ctx))
    return res


# ------------------------------------------------------------------ capture
def incomplete_rows():
    txt = git("show", "HEAD:" + INCOMPLETE_LIST, cwd=WT)
    return list(csv.DictReader(io.StringIO(txt)))


def capture(args):
    import httpx
    from huggingface_hub import HfApi
    from multiprocessing import get_context
    t0 = time.time()
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    api = HfApi()
    info = api.dataset_info(REPO, revision=REV)
    assert info.sha == REV, info.sha
    files = []
    for f in api.list_repo_tree(REPO, repo_type="dataset", revision=REV, recursive=True):
        if f.__class__.__name__ == "RepoFile":
            files.append({"path": f.path, "size": f.size, "hf_oid": f.blob_id,
                          "lfs_sha256": f.lfs.sha256 if f.lfs else ""})
    files.sort(key=lambda r: r["path"])
    work = args.work
    os.makedirs(work, exist_ok=True)
    tmpd = os.path.join(work, "tmp")
    os.makedirs(tmpd, exist_ok=True)
    partial = os.path.join(work, "partial.jsonl")
    done = {}
    if os.path.exists(partial):
        for ln in open(partial):
            r = json.loads(ln)
            if r.get("computed_sha256"):
                done[r["path"]] = r
    inc = incomplete_rows()
    inc_by_path = {r["path"]: r for r in inc}
    inc_sha = {r["sha256"] for r in inc}
    refs_dir = os.path.join(OUT, "capture_refs")
    os.makedirs(refs_dir, exist_ok=True)
    lock = threading.Lock()
    pool = get_context("spawn").Pool(4, maxtasksperchild=50)
    client = httpx.Client(follow_redirects=True, timeout=httpx.Timeout(120, connect=30),
                          verify=os.environ.get("SSL_CERT_FILE") or True,
                          headers={"User-Agent": "mimamsa-c12-hf-verify/1.0 (read-only)"})
    out_f = open(partial, "a")
    todo = [f for f in files if f["path"] not in done]
    print("files %d, already done %d, todo %d" % (len(files), len(done), len(todo)), flush=True)
    counter = [0]

    def one(f):
        url = "https://huggingface.co/datasets/%s/resolve/%s/%s" % (REPO, REV, f["path"])
        log = []
        fp = None
        for attempt in range(1, 7):
            fd, fp = tempfile.mkstemp(dir=tmpd)
            try:
                h = hashlib.sha256(); n = 0
                with os.fdopen(fd, "wb") as w, client.stream("GET", url) as r:
                    if r.status_code != 200:
                        ra = r.headers.get("retry-after")
                        log.append("a%d:HTTP%d" % (attempt, r.status_code))
                        raise RuntimeError(("retry", r.status_code, ra))
                    for b in r.iter_bytes(1 << 20):
                        h.update(b); w.write(b); n += len(b)
                log.append("a%d:OK" % attempt)
                break
            except Exception as e:
                os.path.exists(fp) and os.unlink(fp)
                fp = None
                if not (log and log[-1].startswith("a%d:" % attempt)):
                    log.append("a%d:%s" % (attempt, type(e).__name__))
                code = e.args[0][1] if (e.args and isinstance(e.args[0], tuple)) else 0
                if code and code < 500 and code != 429:
                    break
                delay = min(120, 2 ** attempt) + random.random()
                if e.args and isinstance(e.args[0], tuple) and e.args[0][2]:
                    try: delay = max(delay, float(e.args[0][2]))
                    except ValueError: pass
                time.sleep(delay)
        rec = dict(f)
        rec.update({"download_attempts": len(log), "download_log": " ".join(log),
                    "computed_size": "", "computed_sha256": "", "computed_git_sha1": "",
                    "is_pdf": "", "retrieved_to": ""})
        if fp is None:
            return rec, None
        rec["computed_size"] = n
        rec["computed_sha256"] = h.hexdigest()
        rec["computed_git_sha1"] = git_blob_sha1_file(fp, n)
        with open(fp, "rb") as r_:
            rec["is_pdf"] = "YES" if r_.read(1024).find(b"%PDF") >= 0 else "NO"
        if f["path"] in REF_FILES:
            with open(fp, "rb") as r_, open(os.path.join(refs_dir, f["path"].replace("/", "__") + ".gz"), "wb") as w_:
                with gzip.GzipFile(fileobj=w_, mode="wb", mtime=0, filename="") as gz:
                    shutil.copyfileobj(r_, gz)
        return rec, fp

    def finish(rec, fp):
        if fp is not None and rec["is_pdf"] == "YES":
            try:
                rec.update(pool.apply_async(analyse_pdf, (fp,)).get(timeout=300))
            except Exception as e:
                rec["pdf_opens"] = "ANALYSIS_FAILED:" + type(e).__name__
            # candidate replacement for a known-incomplete judgment
            stored = inc_by_path.get(rec["path"])
            if (stored or rec["computed_sha256"] in inc_sha) and stored and \
                    rec["computed_sha256"] != stored["sha256"] and \
                    rec.get("pdf_opens") == "YES" and rec.get("trailing_eof") == "YES":
                d = os.path.join(RETRIEVED_DIR, rec["computed_sha256"])
                dst = os.path.join(d, os.path.basename(rec["path"]))
                if not os.path.exists(dst):
                    os.makedirs(d, exist_ok=True)
                    shutil.copyfile(fp, dst)
                rec["retrieved_to"] = dst
        if fp is not None and os.path.exists(fp):
            os.unlink(fp)
        with lock:
            out_f.write(json.dumps(rec, sort_keys=True) + "\n"); out_f.flush()
            counter[0] += 1
            if counter[0] % 250 == 0:
                print("%d/%d %.0fs" % (counter[0], len(todo), time.time() - t0), flush=True)

    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(lambda f=f: finish(*one(f))) for f in todo]
        for fu in as_completed(futs):
            fu.result()
    out_f.close(); pool.close(); pool.join(); client.close()
    shutil.rmtree(tmpd, ignore_errors=True)
    # assemble ledger
    recs = {}
    for ln in open(partial):
        r = json.loads(ln)
        if r["path"] not in recs or r.get("computed_sha256"):
            recs[r["path"]] = r
    rows = []
    for f in files:
        r = recs[f["path"]]
        rows.append({c: ("" if r.get(c) is None else str(r.get(c, ""))) for c in LEDGER_COLS})
        rows[-1]["pdf_opens"] = sanitize_err(rows[-1]["pdf_opens"])
    ctx = Context(rows)
    for r in rows:
        r["statuses"] = ";".join(ctx.statuses(r))
    write_ledger(rows)
    meta = {"repo": REPO, "repo_type": "dataset", "revision": REV,
            "revision_last_modified": str(info.last_modified),
            "capture_started_utc": started,
            "capture_finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "capture_runtime_seconds_this_invocation": round(time.time() - t0, 1),
            "files_listed": len(files), "bytes_listed": sum(f["size"] for f in files),
            "max_concurrency": 4, "pymupdf": __import__("pymupdf").VersionBind}
    with open(os.path.join(OUT, "CAPTURE_META.json"), "w") as w:
        json.dump(meta, w, indent=1, sort_keys=True); w.write("\n")
    print("capture done", meta, flush=True)


def write_ledger(rows):
    buf = io.StringIO()
    wr = csv.DictWriter(buf, LEDGER_COLS, lineterminator="\n")
    wr.writeheader(); wr.writerows(rows)
    with open(os.path.join(OUT, "HASH_LEDGER.csv.gz"), "wb") as w:
        with gzip.GzipFile(fileobj=w, mode="wb", mtime=0, filename="") as gz:
            gz.write(buf.getvalue().encode())


def read_ledger():
    with gzip.open(os.path.join(OUT, "HASH_LEDGER.csv.gz"), "rt", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- reference
def ref_text(path):
    fp = os.path.join(OUT, "capture_refs", path.replace("/", "__") + ".gz")
    if not os.path.exists(fp):
        return None
    with gzip.open(fp, "rt", newline="") as f:
        return f.read()


def parse_sums(txt, prefix=""):
    d = {}
    for ln in (txt or "").splitlines():
        if not ln.strip():
            continue
        sha, p = ln.split(None, 1)
        p = p.lstrip("*")
        if p.startswith("./"):
            p = p[2:]
        d[prefix + p] = sha
    return d


class Context:
    def __init__(self, rows):
        self.c7_tree = {}
        for ln in git("ls-tree", "-r", "-l", C7_COMMIT).splitlines():
            meta, p = ln.split("\t", 1)
            _, _, oid, size = meta.split()
            self.c7_tree[p] = (oid, int(size))
        self.stg_tree = {}
        for ln in git("ls-tree", "-r", "-l", STAGING_REF, "--", "legal_knowledge", cwd=WT).splitlines():
            meta, p = ln.split("\t", 1)
            _, _, oid, size = meta.split()
            self.stg_tree[p] = (oid, int(size))
        self.stg_commit = git("rev-parse", STAGING_REF, cwd=WT).strip()
        self.c7_full = git("rev-parse", C7_COMMIT).strip()
        self.sums_git = parse_sums(git("show", C7_COMMIT + ":data/SHA256SUMS"))
        self.sums_hf = parse_sums(ref_text("data/SHA256SUMS"))
        self.c5_sums = parse_sums(ref_text(C5_DIR + "PACKAGE_SHA256SUMS"), C5_DIR)
        self.c5_staged = parse_sums(ref_text(C5_DIR + "STAGED_SHA256SUMS"), C5_DIR)
        rm = ref_text("data/raw_manifest.csv")
        self.raw_manifest_hf = {r["raw_path"]: r for r in csv.DictReader(io.StringIO(rm or ""))}
        rmg = git("show", C7_COMMIT + ":data/raw_manifest.csv")
        self.raw_manifest_git = {r["raw_path"]: r for r in csv.DictReader(io.StringIO(rmg))}
        m = ref_text("data/manifest.csv")
        self.manifest_hf = list(csv.DictReader(io.StringIO(m or "")))
        self.manifest_hf_sha = {r["sha256"] for r in self.manifest_hf if r.get("sha256")}
        self.rows = {r["path"]: r for r in rows}

    def statuses(self, r):
        st = []
        p = r["path"]
        if not r["computed_sha256"]:
            return ["DOWNLOAD_FAILED(attempts=%s:%s)" % (r["download_attempts"], r["download_log"])]
        size_ok = str(r["computed_size"]) == str(r["size"])
        if r["lfs_sha256"]:
            hash_ok = r["computed_sha256"] == r["lfs_sha256"]
            if not hash_ok: st.append("MISMATCH_LFS_SHA256")
        else:
            hash_ok = r["computed_git_sha1"] == r["hf_oid"]
            if not hash_ok: st.append("MISMATCH_HF_OID_GIT_SHA1")
        if not size_ok: st.append("MISMATCH_SIZE")
        server_ok = hash_ok and size_ok
        if server_ok: st.insert(0, "BYTE_VERIFIED_SERVER_HASH_MATCH")
        if p in self.c7_tree:
            if r["computed_git_sha1"] == self.c7_tree[p][0]:
                st.append("BYTE_VERIFIED_AND_MATCHES_GIT_AD77758D" if server_ok else "MATCHES_GIT_AD77758D")
            else:
                st.append("MISMATCH_GIT_AD77758D_BLOB")
        else:
            st.append("HF_ONLY")
        if p.startswith("data/raw/"):
            for name, sums in (("HF", self.sums_hf), ("GIT_AD77758D", self.sums_git)):
                if p in sums:
                    st.append("SHA256SUMS_%s_MATCH" % name if sums[p] == r["computed_sha256"]
                              else "MISMATCH_SHA256SUMS_%s" % name)
                else:
                    st.append("NOT_IN_SHA256SUMS_%s" % name)
            stem = os.path.basename(p).split(".")[0]
            if re.fullmatch(r"[0-9a-f]{64}", stem):
                st.append("RAW_FILENAME_SHA256_MATCH" if stem == r["computed_sha256"]
                          else "MISMATCH_RAW_FILENAME_SHA256")
            for name, man in (("HF", self.raw_manifest_hf), ("GIT_AD77758D", self.raw_manifest_git)):
                if p in man:
                    mr = man[p]
                    ok = mr["sha256"] == r["computed_sha256"]
                    st.append("RAW_MANIFEST_%s_SHA256_MATCH" % name if ok else "MISMATCH_RAW_MANIFEST_%s_SHA256" % name)
                    if mr.get("bytes") and mr["bytes"] != str(r["computed_size"]):
                        st.append("MISMATCH_RAW_MANIFEST_%s_BYTES" % name)
                else:
                    st.append("NOT_IN_RAW_MANIFEST_%s" % name)
            st.append("MANIFEST_CSV_SHA256_LISTED" if r["computed_sha256"] in self.manifest_hf_sha
                      else "MANIFEST_CSV_SHA256_NOT_LISTED")
        if p.startswith("legal_knowledge/"):
            if p in self.stg_tree:
                st.append("MATCHES_GITHUB_STAGING" if self.stg_tree[p][0] == r["computed_git_sha1"]
                          else "DIFFERS_FROM_GITHUB_STAGING")
            else:
                st.append("NOT_IN_GITHUB_STAGING")
        if p.startswith(C5_DIR) and not p.endswith("SHA256SUMS"):
            if p in self.c5_sums:
                st.append("C5_PACKAGE_SHA256SUMS_MATCH" if self.c5_sums[p] == r["computed_sha256"]
                          else "MISMATCH_C5_PACKAGE_SHA256SUMS")
            else:
                st.append("NOT_IN_C5_PACKAGE_SHA256SUMS")
        return st


# ------------------------------------------------------------------- report
def csv_text(header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header); w.writerows(rows)
    return buf.getvalue()


def build_reports():
    rows = read_ledger()
    meta = json.load(open(os.path.join(OUT, "CAPTURE_META.json")))
    ctx = Context(rows)
    out = {}
    status_drift = []
    for r in rows:
        s = ";".join(ctx.statuses(r))
        if s != r["statuses"]:
            status_drift.append(r["path"])
    P = ctx.rows
    st_count = collections.Counter()
    for r in rows:
        for s in r["statuses"].split(";"):
            st_count[s.split("(")[0]] += 1
    failed = [r for r in rows if not r["computed_sha256"]]
    server_ok = [r for r in rows if "BYTE_VERIFIED_SERVER_HASH_MATCH" in r["statuses"].split(";")]
    retries = [r for r in rows if r["download_attempts"] and int(r["download_attempts"]) > 1]

    # ---------------- discrepancies
    disc = []
    for r in rows:
        for s in r["statuses"].split(";"):
            if s.startswith("MISMATCH") or s.startswith("DOWNLOAD_FAILED") or s == "DIFFERS_FROM_GITHUB_STAGING" \
                    or s == "NOT_IN_C5_PACKAGE_SHA256SUMS" or s.startswith("NOT_IN_SHA256SUMS") \
                    or s.startswith("NOT_IN_RAW_MANIFEST") or s == "MANIFEST_CSV_SHA256_NOT_LISTED":
                detail = ""
                p = r["path"]
                if s == "MISMATCH_GIT_AD77758D_BLOB":
                    detail = "git blob %s (%d bytes) vs HF computed git-sha1 %s (%s bytes)" % (
                        ctx.c7_tree[p][0], ctx.c7_tree[p][1], r["computed_git_sha1"], r["computed_size"])
                elif s == "DIFFERS_FROM_GITHUB_STAGING":
                    detail = "staging %s blob %s (%d bytes) vs HF %s (%s bytes)" % (
                        ctx.stg_commit[:8], ctx.stg_tree[p][0], ctx.stg_tree[p][1], r["computed_git_sha1"], r["computed_size"])
                elif s.startswith("MISMATCH_SHA256SUMS"):
                    sums = ctx.sums_hf if s.endswith("HF") else ctx.sums_git
                    detail = "listed %s computed %s" % (sums.get(p), r["computed_sha256"])
                elif s.startswith("MISMATCH_LFS"):
                    detail = "lfs %s computed %s" % (r["lfs_sha256"], r["computed_sha256"])
                elif s.startswith("MISMATCH_HF_OID"):
                    detail = "hf_oid %s computed %s" % (r["hf_oid"], r["computed_git_sha1"])
                elif s.startswith("MISMATCH_SIZE"):
                    detail = "listed %s computed %s" % (r["size"], r["computed_size"])
                elif s.startswith("MISMATCH_C5"):
                    detail = "listed %s computed %s" % (ctx.c5_sums.get(p), r["computed_sha256"])
                elif s.startswith("MISMATCH_RAW_MANIFEST"):
                    man = ctx.raw_manifest_hf if "_HF_" in s else ctx.raw_manifest_git
                    detail = "manifest sha256 %s bytes %s; computed %s %s" % (
                        man[p]["sha256"], man[p].get("bytes"), r["computed_sha256"], r["computed_size"])
                disc.append([p, s.split("(")[0], detail or s, r["computed_sha256"]])
    # listed in reference files but absent on HF
    for name, sums in (("SHA256SUMS_HF", ctx.sums_hf), ("SHA256SUMS_GIT_AD77758D", ctx.sums_git),
                       ("C5_PACKAGE_SHA256SUMS", ctx.c5_sums)):
        for p in sorted(sums):
            if p not in P:
                disc.append([p, "LISTED_IN_%s_BUT_ABSENT_ON_HF" % name, "listed sha256 %s" % sums[p], ""])
    for name, man in (("RAW_MANIFEST_HF", ctx.raw_manifest_hf), ("RAW_MANIFEST_GIT_AD77758D", ctx.raw_manifest_git)):
        for p in sorted(man):
            if p not in P:
                disc.append([p, "LISTED_IN_%s_BUT_ABSENT_ON_HF" % name, "listed sha256 %s" % man[p]["sha256"], ""])
    disc.sort()
    out["DISCREPANCIES.csv"] = csv_text(["path", "kind", "detail", "hf_computed_sha256"], disc)

    # ---------------- reference-file comparisons
    def hf_blob(p):
        return P[p]["computed_git_sha1"] if p in P else None
    ref_cmp = {}
    for p in ["data/SHA256SUMS", "data/manifest.csv", "data/raw_manifest.csv", "data/relations.jsonl",
              "data/excluded_judgments.jsonl"]:
        ref_cmp[p] = {"hf_git_sha1": hf_blob(p), "git_ad77758d_blob": ctx.c7_tree.get(p, (None,))[0],
                      "identical": hf_blob(p) == ctx.c7_tree.get(p, (None,))[0]}
    rm_hf_cols = list(next(iter(ctx.raw_manifest_hf.values())).keys()) if ctx.raw_manifest_hf else []
    rm_git_cols = list(next(iter(ctx.raw_manifest_git.values())).keys())
    common = [c for c in rm_hf_cols if c in rm_git_cols]
    rm_cell_diffs = sum(1 for p, r in ctx.raw_manifest_hf.items() for c in common
                        if p in ctx.raw_manifest_git and ctx.raw_manifest_git[p][c] != r[c])
    raw_manifest_cmp = {"hf_columns": rm_hf_cols, "git_columns": rm_git_cols,
                        "git_only_columns": [c for c in rm_git_cols if c not in rm_hf_cols],
                        "hf_only_columns": [c for c in rm_hf_cols if c not in rm_git_cols],
                        "same_raw_paths": sorted(ctx.raw_manifest_hf) == sorted(ctx.raw_manifest_git),
                        "differing_cells_in_common_columns": rm_cell_diffs}
    sums_diff = sorted(set(ctx.sums_hf.items()) ^ set(ctx.sums_git.items()))
    raw_files = [r for r in rows if r["path"].startswith("data/raw/")]
    hf_sha_set = {r["computed_sha256"] for r in rows}
    manifest_sha_missing = sorted({r["sha256"] for r in ctx.manifest_hf if r.get("sha256")} - hf_sha_set)

    # ---------------- HF vs git paths
    allp = sorted(set(P) | set(ctx.c7_tree))
    hvg = []
    rel_count = collections.Counter()
    for p in allp:
        h = P.get(p); g = ctx.c7_tree.get(p)
        if h and g:
            rel = "IDENTICAL_BLOB" if h["computed_git_sha1"] == g[0] else "DIFFERENT_BLOB"
        elif h:
            rel = "HF_ONLY"
        else:
            rel = "GIT_ONLY"
        rel_count[rel] += 1
        stg = ""
        if p.startswith("legal_knowledge/"):
            s = ctx.stg_tree.get(p)
            stg = ("STAGING_IDENTICAL" if s[0] == h["computed_git_sha1"] else "STAGING_DIFFERENT") if (s and h) \
                else ("NOT_IN_STAGING" if h else "")
        hvg.append([p, rel, h["computed_git_sha1"] if h else "", g[0] if g else "",
                    h["computed_size"] if h else "", g[1] if g else "", stg])
    out["HF_VS_GIT_PATHS.csv"] = csv_text(["path", "relation_hf_vs_git_ad77758d", "hf_computed_git_sha1",
                                           "git_ad77758d_blob", "hf_size", "git_size", "legal_knowledge_vs_staging"], hvg)
    hf_only_groups = collections.Counter("/".join(p.split("/")[:2]) for p, rel, *_ in hvg if rel == "HF_ONLY")
    git_only_groups = collections.Counter("/".join(p.split("/")[:2]) for p, rel, *_ in hvg if rel == "GIT_ONLY")
    lk = [r for r in rows if r["path"].startswith("legal_knowledge/")]
    lk_cnt = collections.Counter(next((s for s in r["statuses"].split(";") if "STAGING" in s), "") for r in lk)
    stg_only = sorted(p for p in ctx.stg_tree if p not in P)

    # ---------------- c5 working store
    c5_files = [r for r in rows if r["path"].startswith(C5_DIR) and not r["path"].endswith("SHA256SUMS")]
    c5_cnt = collections.Counter(next((s for s in r["statuses"].split(";") if "C5" in s), "") for r in c5_files)
    c5_missing = sorted(p for p in ctx.c5_sums if p not in P)
    c5_package_hf = P.get(C5_DIR + "PACKAGE_SHA256SUMS")
    c5_vs_c12 = None
    c12p = os.path.join(WT, "legal_knowledge/audit_work/C12-CONSOLIDATION/preservation/PACKAGE_SHA256SUMS_C12.txt")
    if os.path.exists(c12p):
        c12 = git("show", "HEAD:legal_knowledge/audit_work/C12-CONSOLIDATION/preservation/PACKAGE_SHA256SUMS_C12.txt", cwd=WT)
        c5_vs_c12 = parse_sums(c12, C5_DIR) == ctx.c5_sums

    # ---------------- incomplete files
    inc = incomplete_rows()
    try:
        acq = {r["existing_sha256"]: r for r in csv.DictReader(io.StringIO(git("show", "HEAD:" + ACQ_MANIFEST, cwd=WT)))}
    except subprocess.CalledProcessError:
        acq = {}
    sha_paths = collections.defaultdict(list)
    for r in rows:
        sha_paths[r["computed_sha256"]].append(r["path"])
    inc_rows = []; inc_cnt = collections.Counter(); retrieved = []
    for ir in sorted(inc, key=lambda x: x["sha256"]):
        h = P.get(ir["path"])
        others = [p for p in sha_paths.get(ir["sha256"], []) if p != ir["path"]]
        if not h:
            verdict = "NOT_ON_HF_AT_STORED_PATH"
        elif not h["computed_sha256"]:
            verdict = "DOWNLOAD_FAILED"
        elif h["computed_sha256"] == ir["sha256"] and ir.get("source_completeness") == "NOT_AVAILABLE":
            # C11 never held these bytes (NOT_PROCESSED_BYTES_UNAVAILABLE); the
            # recorded sha256 came from an HF-side record, so HF is the only copy
            complete = h["pdf_opens"] == "YES" and h["trailing_eof"] == "YES"
            verdict = "HF_ONLY_NO_LOCAL_BYTES_HF_COPY_" + ("OPENS_WITH_EOF_RETRIEVED" if complete else "INCOMPLETE")
            if complete:
                dst = os.path.join(RETRIEVED_DIR, h["computed_sha256"], os.path.basename(h["path"]))
                retrieved.append([h["computed_sha256"], h["computed_size"], "", h["path"], dst, h["pdf_pages"],
                                  "HF_ONLY_COPY_RETRIEVED_NO_LOCAL_COPY_EXISTED" if os.path.exists(dst) else "NOT_YET_RETRIEVED"])
        elif h["computed_sha256"] == ir["sha256"]:
            complete = h["pdf_opens"] == "YES" and h["trailing_eof"] == "YES"
            verdict = "HF_IDENTICAL_TO_STORED_COPY_" + ("BUT_PASSES_OPEN_AND_EOF_CHECK" if complete else "ALSO_INCOMPLETE")
        else:
            complete = h["pdf_opens"] == "YES" and h["trailing_eof"] == "YES"
            verdict = "HF_DIFFERS_" + ("COMPLETE_CANDIDATE_RETRIEVED" if complete else "ALSO_INCOMPLETE")
            if complete:
                retrieved.append([h["computed_sha256"], h["computed_size"], ir["sha256"], ir["path"],
                                  h["retrieved_to"], h["pdf_pages"], "CANDIDATE_REPLACEMENT_NOT_APPLIED"])
        inc_cnt[verdict] += 1
        a = acq.get(ir["sha256"], {})
        inc_rows.append([ir["sha256"], ir["path"], ir.get("court", ""), ir.get("case_numbers_meta", ""),
                         ir.get("bytes", ""), h["computed_sha256"] if h else "", h["computed_size"] if h else "",
                         h["lfs_sha256"] and "LFS" or "GIT" if h else "",
                         h["pdf_opens"] if h else "", h["pdf_pages"] if h else "", h["trailing_eof"] if h else "",
                         ";".join(others), "HF_ONLY" if (h and "HF_ONLY" in h["statuses"]) else ("IN_GIT_AD77758D" if h else ""),
                         a.get("completeness", ""), verdict])
    out["INCOMPLETE_FILES_HF.csv"] = csv_text(
        ["stored_sha256", "path", "court", "case_numbers", "stored_bytes", "hf_computed_sha256", "hf_size", "hf_storage",
         "hf_pdf_opens", "hf_pdf_pages", "hf_trailing_eof", "other_hf_paths_same_sha256", "hf_vs_git_ad77758d",
         "c12_acquisition_completeness", "verdict"], inc_rows)
    out["HF_RETRIEVED_CANDIDATES.csv"] = csv_text(
        ["hf_sha256", "bytes", "replaces_stored_sha256", "hf_path", "saved_to", "pages", "status"], retrieved)

    # ---------------- marking hits
    mh = []; mh_cnt = collections.Counter(); line_files = []
    for r in rows:
        if r["is_pdf"] != "YES" or not r["marking_terms"]:
            continue
        for kv in r["marking_terms"].split(";"):
            mh_cnt[kv.split("=")[0]] += 1
        known = "KNOWN_FOUO_RAF_2000" if r["computed_sha256"].startswith(KNOWN_FOUO) else ""
        if r["marking_line_hits"]:
            line_files.append(r["path"])
        mh.append([r["path"], r["computed_sha256"], r["marking_terms"], r["marking_line_hits"],
                   "MARKING_LIKE_LINE" if r["marking_line_hits"] else "TERM_IN_RUNNING_TEXT", known,
                   r["marking_context"]])
    out["MARKING_HITS.csv"] = csv_text(["path", "sha256", "term_counts_case_insensitive", "marking_like_line_counts",
                                        "class", "known", "first_context_per_term"], mh)
    fouo = [x for x in mh if "for_official_use_only" in x[2]]
    pdfs = [r for r in rows if r["is_pdf"] == "YES"]
    known_fouo_present = sorted(r["path"] for r in rows if r["computed_sha256"].startswith(KNOWN_FOUO))

    summary = {
        "repo": REPO, "revision": REV, "revision_last_modified": meta.get("revision_last_modified"),
        "git_reference": {"c7_commit": ctx.c7_full, "staging_ref": STAGING_REF, "staging_commit": ctx.stg_commit},
        "capture": {k: meta[k] for k in sorted(meta) if k.startswith("capture") or k in ("max_concurrency", "pymupdf")},
        "files": len(rows), "bytes_listed": sum(int(r["size"]) for r in rows),
        "files_downloaded_and_hashed": len(rows) - len(failed),
        "bytes_hashed": sum(int(r["computed_size"]) for r in rows if r["computed_size"]),
        "download_failed": len(failed), "files_needing_retries": len(retries),
        "byte_verified_server_hash_match": len(server_ok),
        "lfs_files": sum(1 for r in rows if r["lfs_sha256"]),
        "status_counts": dict(sorted(st_count.items())),
        "ledger_status_rederivation_drift": len(status_drift),
        "reference_files_hf_vs_git_ad77758d": ref_cmp,
        "raw_manifest_hf_vs_git_columns": raw_manifest_cmp,
        "sha256sums": {"hf_entries": len(ctx.sums_hf), "git_entries": len(ctx.sums_git),
                       "hf_vs_git_entry_differences": len(sums_diff),
                       "mismatch_vs_computed_hf": st_count.get("MISMATCH_SHA256SUMS_HF", 0),
                       "mismatch_vs_computed_git": st_count.get("MISMATCH_SHA256SUMS_GIT_AD77758D", 0)},
        "raw": {"files": len(raw_files),
                "filename_sha256_match": st_count.get("RAW_FILENAME_SHA256_MATCH", 0),
                "filename_sha256_mismatch": st_count.get("MISMATCH_RAW_FILENAME_SHA256", 0)},
        "manifests": {"raw_manifest_hf_rows": len(ctx.raw_manifest_hf), "raw_manifest_git_rows": len(ctx.raw_manifest_git),
                      "raw_manifest_hf_mismatch": st_count.get("MISMATCH_RAW_MANIFEST_HF_SHA256", 0),
                      "raw_manifest_git_mismatch": st_count.get("MISMATCH_RAW_MANIFEST_GIT_AD77758D_SHA256", 0),
                      "manifest_csv_rows": len(ctx.manifest_hf),
                      "manifest_csv_sha256_not_present_on_hf": len(manifest_sha_missing),
                      "manifest_csv_sha256_not_present_on_hf_list": manifest_sha_missing},
        "hf_vs_git_ad77758d_paths": dict(sorted(rel_count.items())),
        "hf_only_by_prefix": dict(sorted(hf_only_groups.items())),
        "git_only_by_prefix": dict(sorted(git_only_groups.items())),
        "legal_knowledge_vs_staging": {"hf_files": len(lk), "counts": dict(sorted(lk_cnt.items())),
                                       "staging_only_paths": len(stg_only)},
        "c5_working_store": {"files": len(c5_files), "counts": dict(sorted(c5_cnt.items())),
                             "listed_but_absent_on_hf": c5_missing,
                             "package_sha256sums_entries": len(ctx.c5_sums),
                             "hf_package_sha256sums_equals_C12_copy": c5_vs_c12},
        "incomplete_files": {"listed": len(inc), "verdicts": dict(sorted(inc_cnt.items())),
                             "complete_candidates_retrieved": len(retrieved)},
        "marking_scan": {"pdfs_scanned": len(pdfs),
                         "pdfs_opened": sum(1 for r in pdfs if r["pdf_opens"] == "YES"),
                         "pdfs_with_any_term": len(mh), "files_per_term": dict(sorted(mh_cnt.items())),
                         "pdfs_with_marking_like_line": len(line_files),
                         "pdfs_with_for_official_use_only": [x[0] for x in fouo],
                         "known_fouo_4284820e_paths_on_hf": known_fouo_present},
    }
    out["SUMMARY.json"] = json.dumps(summary, indent=1, sort_keys=True) + "\n"
    out["REPORT.md"] = render_report(summary, disc, inc_rows, retrieved, mh, fouo, line_files, stg_only)
    names = sorted(list(out) + ["HASH_LEDGER.csv.gz", "CAPTURE_META.json", "tools/hf_verify_c12.py"]
                   + ["capture_refs/" + f for f in sorted(os.listdir(os.path.join(OUT, "capture_refs")))])
    lines = []
    for n in names:
        if n in out:
            b = out[n].encode()
        else:
            b = open(os.path.join(OUT, n), "rb").read()
        lines.append("%s  %s\n" % (hashlib.sha256(b).hexdigest(), n))
    out["SHA256SUMS"] = "".join(lines)
    return out


def render_report(s, disc, inc_rows, retrieved, mh, fouo, line_files, stg_only):
    L = []
    a = L.append
    a("# C12 Hugging Face byte verification (revision-pinned)\n")
    a("- Dataset: `%s` (private), revision **`%s`** (last modified %s)." % (s["repo"], s["revision"], s["revision_last_modified"]))
    a("- Git references: c7 `%s`, staging `%s` at `%s`." % (s["git_reference"]["c7_commit"], s["git_reference"]["staging_ref"], s["git_reference"]["staging_commit"]))
    a("- Capture: started %s, finished %s; at most 4 concurrent downloads. READ-ONLY: nothing on Hugging Face was changed.\n" % (
        s["capture"].get("capture_started_utc"), s["capture"].get("capture_finished_utc")))
    a("## Result\n")
    a("| Measure | Value |\n|---|---|")
    for k in ("files", "bytes_listed", "files_downloaded_and_hashed", "bytes_hashed", "download_failed",
              "files_needing_retries", "byte_verified_server_hash_match", "lfs_files", "ledger_status_rederivation_drift"):
        a("| %s | %s |" % (k, s[k]))
    a("\nEvery file was downloaded from `/resolve/<revision>/<path>` and hashed locally. `BYTE_VERIFIED_SERVER_HASH_MATCH` means that the computed sha256 equals the LFS sha256 (LFS files), or the computed git-blob-sha1 equals the HF oid (other files), and that the size matches.\n")
    a("## Status counts (one file can carry several)\n")
    a("| Status | Files |\n|---|---|")
    for k, v in s["status_counts"].items():
        a("| `%s` | %d |" % (k, v))
    a("\n## Reference files: HF against git `ad77758d`\n")
    a("| File | Identical blob |\n|---|---|")
    for k, v in s["reference_files_hf_vs_git_ad77758d"].items():
        a("| `%s` | %s |" % (k, v["identical"]))
    ss = s["sha256sums"]
    a("\n- `data/SHA256SUMS`: %d entries on HF and %d in git; %d entries differ between them. Mismatches against computed hashes: HF list %d, git list %d." % (
        ss["hf_entries"], ss["git_entries"], ss["hf_vs_git_entry_differences"], ss["mismatch_vs_computed_hf"], ss["mismatch_vs_computed_git"]))
    a("- `data/raw` filenames: %d match the computed sha256 and %d do not, of %d files." % (s["raw"]["filename_sha256_match"], s["raw"]["filename_sha256_mismatch"], s["raw"]["files"]))
    rc = s["raw_manifest_hf_vs_git_columns"]
    a("- `data/raw_manifest.csv` differs between HF and git only in its columns: git has %s and HF does not. Same raw paths: %s; differing cells in the common columns: %d." % (
        ", ".join("`%s`" % c for c in rc["git_only_columns"]) or "none", rc["same_raw_paths"], rc["differing_cells_in_common_columns"]))
    m = s["manifests"]
    a("- `raw_manifest.csv`: %d rows on HF and %d in git. Mismatches: %d (HF) and %d (git). `manifest.csv`: %d rows; %d of its sha256 values are not present on HF." % (
        m["raw_manifest_hf_rows"], m["raw_manifest_git_rows"], m["raw_manifest_hf_mismatch"], m["raw_manifest_git_mismatch"], m["manifest_csv_rows"], m["manifest_csv_sha256_not_present_on_hf"]))
    a("\n## Paths: HF against git `ad77758d`\n")
    a("| Relation | Paths |\n|---|---|")
    for k, v in s["hf_vs_git_ad77758d_paths"].items():
        a("| %s | %d |" % (k, v))
    a("\nHF-only paths by prefix: " + ", ".join("`%s` %d" % kv for kv in s["hf_only_by_prefix"].items()) + ".")
    a("\nGit-only paths by prefix: " + (", ".join("`%s` %d" % kv for kv in s["git_only_by_prefix"].items()) or "none") + ".")
    a("\n## `legal_knowledge/` on HF against the GitHub staging branch\n")
    a("Differences are reported without judging which side is right.\n")
    for k, v in s["legal_knowledge_vs_staging"]["counts"].items():
        a("- `%s`: %d" % (k, v))
    a("- Staging-only paths (not on HF): %d" % s["legal_knowledge_vs_staging"]["staging_only_paths"])
    c5 = s["c5_working_store"]
    a("\n## `c5_working_store`\n")
    a("- %d files against %d `PACKAGE_SHA256SUMS` entries: %s. Listed but absent on HF: %d. The HF `PACKAGE_SHA256SUMS` equals the C12 copy (`PACKAGE_SHA256SUMS_C12.txt`): %s." % (
        c5["files"], c5["package_sha256sums_entries"], ", ".join("`%s` %d" % kv for kv in c5["counts"].items()), len(c5["listed_but_absent_on_hf"]), c5["hf_package_sha256sums_equals_C12_copy"]))
    a("\n## Known incomplete judgments (%d)\n" % s["incomplete_files"]["listed"])
    a("A file counts as complete only if PyMuPDF opens it AND a `%%EOF` marker is in its last 1,024 bytes.\n")
    a("| Stored sha256 | Path | HF opens | HF %%EOF | HF vs git | Verdict |\n|---|---|---|---|---|---|")
    for r in inc_rows:
        a("| `%s` | `%s` | %s | %s | %s | %s |" % (r[0][:12], r[1], r[8], r[10], r[12], r[14]))
    a("\nHF copies saved to `hf_retrieved_c12/<sha256>/` (`HF_RETRIEVED_CANDIDATES.csv`): %d. HF copies that differ from the stored copy and are complete: %d. The HF-only SC copies had no local bytes at all (C11: `NOT_PROCESSED_BYTES_UNAVAILABLE`). Their HF bytes match the recorded sha256, open in PyMuPDF and end with `%%%%EOF`, so they were saved as new copies. Passing these checks proves the file is not truncated; it does not prove the text is complete. Nothing was replaced or overwritten." % (len(retrieved), sum(1 for r in inc_rows if r[14] == "HF_DIFFERS_COMPLETE_CANDIDATE_RETRIEVED")))
    ms = s["marking_scan"]
    a("\n## Marking scan (PyMuPDF text layer only)\n")
    a("- %d PDFs scanned, %d opened. %d contain at least one of the terms (case-insensitive, whole word): %s." % (
        ms["pdfs_scanned"], ms["pdfs_opened"], ms["pdfs_with_any_term"], ", ".join("%s %d" % kv for kv in ms["files_per_term"].items())))
    a("- Marking-like lines (the term in upper case, or FOUO in any case, as a short line of its own; a heuristic): %d PDFs." % ms["pdfs_with_marking_like_line"])
    a("- PDFs with 'For Official Use Only': %s." % (", ".join("`%s`" % p for p in ms["pdfs_with_for_official_use_only"]) or "none"))
    a("- Known FOUO copy `4284820e...` (RAF 2000) on HF: %s." % (", ".join("`%s`" % p for p in ms["known_fouo_4284820e_paths_on_hf"]) or "not present"))
    a("- Scanned images without a text layer cannot be checked this way. Every hit is listed in `MARKING_HITS.csv` for review. Nothing was changed.")
    a("\n## Discrepancies\n")
    kinds = collections.Counter(d[1] for d in disc)
    a("%d rows in `DISCREPANCIES.csv`:\n" % len(disc))
    for k, v in sorted(kinds.items()):
        a("- `%s`: %d" % (k, v))
    a("\n## Reproduce\n")
    a("```\npython tools/hf_verify_c12.py capture --work <tmpdir>   # network; writes the ledger\npython tools/hf_verify_c12.py report                    # derives the reports\npython tools/hf_verify_c12.py report --check            # regenerates and byte-compares\n```")
    return "\n".join(L) + "\n"


def retrieve(args):
    """Download (pinned) the HF-only complete copies selected by the report
    criteria into hf_retrieved_c12/<sha256>/; verify sha256; never overwrite."""
    import httpx
    out = build_reports()
    rows = list(csv.DictReader(io.StringIO(out["HF_RETRIEVED_CANDIDATES.csv"])))
    c = httpx.Client(follow_redirects=True, timeout=120, verify=os.environ.get("SSL_CERT_FILE") or True)
    for r in rows:
        dst = r["saved_to"]
        if os.path.exists(dst):
            print("exists", dst); continue
        url = "https://huggingface.co/datasets/%s/resolve/%s/%s" % (REPO, REV, r["hf_path"])
        b = c.get(url).content
        if hashlib.sha256(b).hexdigest() != r["hf_sha256"]:
            print("HASH MISMATCH, not saved", r["hf_path"]); continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "xb") as w:
            w.write(b)
        print("saved", dst)


def report(args):
    out = build_reports()
    if args.check:
        bad = []
        for n, t in out.items():
            fp = os.path.join(OUT, n)
            if not os.path.exists(fp) or open(fp, "rb").read() != t.encode():
                bad.append(n)
        s = json.loads(out["SUMMARY.json"])
        if s["ledger_status_rederivation_drift"]:
            bad.append("ledger statuses drift")
        print("CHECK", "FAIL " + ", ".join(bad) if bad else "OK (%d files byte-identical)" % len(out))
        sys.exit(1 if bad else 0)
    for n, t in out.items():
        with open(os.path.join(OUT, n), "w", newline="") as w:
            w.write(t)
    print("wrote", ", ".join(sorted(out)))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="mode", required=True)
    c = sp.add_parser("capture"); c.add_argument("--work", required=True)
    r = sp.add_parser("report"); r.add_argument("--check", action="store_true")
    sp.add_parser("retrieve")
    a = ap.parse_args()
    {"capture": capture, "report": report, "retrieve": retrieve}[a.mode](a)


if __name__ == "__main__":
    main()
