"""C13-A0 shared helpers: paths, deterministic CSV/JSON rendering, hashing, write-or-check.

Standard library only (CI runs Python 3.11 without extra packages). Every tool renders its outputs into memory first;
`--check` compares the rendering with the committed bytes and writes nothing.
"""
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent                                   # legal_knowledge/audit_work/C13-A0-EVAL
AW = PKG.parent                                     # legal_knowledge/audit_work
REPO = AW.parent.parent
C10 = AW / "C10-HF-JUDGMENTS"
C11 = AW / "C11-JUDICIAL-QUALITY"
C12 = AW / "C12-CONSOLIDATION"
OUT = PKG / "outputs"

# Pinned corpus snapshot (raw-data commit holding data/meta, data/text, data/raw and the manifests).
CORPUS_COMMIT = "ad77758d4569ba6aafa955cc7843d874489e10f7"
# HF commits that added the C12 judicial records (judicial_recovery_c12/HF_COMMITS.csv).
HF_C12_COMMITS = {"A": "af7f9d069e71314879c1756f914943d9d2ab777a", "B": "15bd03ccce7241b1294176fa7c19ab1c5dc109cb"}
# FOUO-marked Regulations for the Air Force 2000 copy: excluded from every derivative, index and packet.
FOUO_EXCLUDED_SHA256 = {"4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"}
CANDIDATE_STATUS = "AUTOMATED_CANDIDATE_NOT_VERIFIED"


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def render_csv(rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        if not rows:
            raise ValueError("render_csv: empty rows need explicit fieldnames")
        fieldnames = list(rows[0].keys())
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=fieldnames, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({k: _cell(r.get(k, "")) for k in fieldnames})
    return s.getvalue()


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.6f}".rstrip("0").rstrip(".") if v == v else "nan"
    return v


def render_json(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def seeded_hash(seed, key):
    """Deterministic pseudo-random rank used by every sampler: lowest SHA-256(seed|key) first."""
    return hashlib.sha256(f"{seed}|{key}".encode("utf-8")).hexdigest()


def write_or_check(outputs, base, check, label):
    """outputs: {relative path: text}. In check mode compare bytes and report; otherwise write. Returns exit code."""
    base = Path(base)
    bad = []
    for rel, text in sorted(outputs.items()):
        p = base / rel
        data = text.encode("utf-8") if isinstance(text, str) else text
        if check:
            if not p.is_file() or p.read_bytes() != data:
                bad.append(rel)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
    if check:
        if bad:
            print(f"{label}: CHECK FAILED for {len(bad)} file(s): " + ", ".join(bad))
            return 1
        print(f"{label}: check OK, {len(outputs)} output(s) reproduce byte for byte")
        return 0
    print(f"{label}: wrote {len(outputs)} output(s) under {base.relative_to(REPO) if base.is_relative_to(REPO) else base}")
    return 0


# ----------------------------------------------------------------------------------------------- corpus access
def corpus_git_dir():
    """Locate a git directory that holds CORPUS_COMMIT (env MIMAMSA_CORPUS_GIT, /home/user/c7, or this repository)."""
    cands = [os.environ.get("MIMAMSA_CORPUS_GIT"), "/home/user/c7", str(REPO)]
    for c in cands:
        if not c:
            continue
        r = subprocess.run(["git", "-C", c, "cat-file", "-e", CORPUS_COMMIT + "^{commit}"], capture_output=True)
        if r.returncode == 0:
            return c
    return None


class CorpusBlobs:
    """Read blobs at CORPUS_COMMIT through one `git cat-file --batch` process (fast, read-only)."""

    def __init__(self, git_dir=None):
        self.git_dir = git_dir or corpus_git_dir()
        if not self.git_dir:
            raise RuntimeError(f"corpus commit {CORPUS_COMMIT} not available; set MIMAMSA_CORPUS_GIT")
        self.p = subprocess.Popen(["git", "-C", self.git_dir, "cat-file", "--batch"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE)

    def get(self, path):
        self.p.stdin.write(f"{CORPUS_COMMIT}:{path}\n".encode())
        self.p.stdin.flush()
        header = self.p.stdout.readline().decode()
        if header.endswith("missing\n"):
            return None
        size = int(header.split()[2])
        data = self.p.stdout.read(size)
        self.p.stdout.read(1)
        return data

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def additions_cache_dir():
    """Local copy of the C12 HF-added text/meta files (verified against STAGED_MANIFEST.csv sha256 on every read)."""
    return Path(os.environ.get("MIMAMSA_C12_ADDITIONS", str(REPO.parent / "cache_a0" / "c12_additions")))


def split_pages(text):
    """Split page-marked text ('[[page N]]') into {page_no: text}. Text before the first marker is page 0."""
    import re
    pages, cur, buf = {}, 0, []
    for line in text.split("\n"):
        m = re.fullmatch(r"\[\[page (\d+)\]\]", line.strip())
        if m:
            pages[cur] = "\n".join(buf)
            cur, buf = int(m.group(1)), []
        else:
            buf.append(line)
    pages[cur] = "\n".join(buf)
    if not pages.get(0, "").strip():
        pages.pop(0, None)
    return pages


def argv_check():
    return "--check" in sys.argv[1:]
