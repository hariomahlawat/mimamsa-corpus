#!/usr/bin/env python3
"""C13-A0 v1.1 leak guard (confirmation finding C01): no holdout judgment text may sit in C13-A0-EVAL.

Build (needs the corpus commit and the C12 additions copy): read the representative-copy text of every holdout
judgment (H-OUT-C13, H-HOLD-C13 including the opened reserve, H-REL-C13), form normalised 8-word shingles, drop
boilerplate shingles shared by >= 3 holdout judgments, and keep a 1/8 hash sample as truncated SHA-256 values
(12 hex characters). Boilerplate is judged against the whole corpus. The fingerprint holds no readable text. Output: outputs/leakguard/HOLDOUT_SHINGLE_FINGERPRINT.txt.

Scan (standard library, no corpus): every file under C13-A0-EVAL except the fingerprint itself is shingled the same
way; a file FAILS when it shares >= MIN_HITS fingerprint hashes (about 16 consecutive quoted words are enough to
expect a hit; a 600-character excerpt gives about 12 expected hits; calibration in EXPOSURE_REGISTER.md).

  python -I -B c13_leakguard.py [--check]     # rebuild / verify the fingerprint (corpus needed)
  python -I -B c13_leakguard.py --scan [PATH ...]
"""
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c13_common import (OUT, PKG, CorpusBlobs, additions_cache_dir, read_csv, write_or_check, argv_check)  # noqa: E402

N = 8
SAMPLE_MOD = 8
BOILERPLATE_DF = 3
MIN_HITS = 5        # calibrated on the removed a4865e76 files: holdout excerpts >= 8 hits, generic text <= 3
FP = OUT / "leakguard" / "HOLDOUT_SHINGLE_FINGERPRINT.txt"
SCAN_SUFFIXES = {".md", ".csv", ".json", ".txt", ".py", ".tsv", ".jsonl"}


def shingle_hashes(text):
    toks = re.findall(r"[a-z0-9]+", text.lower())
    out = set()
    for i in range(len(toks) - N + 1):
        h = hashlib.sha256(" ".join(toks[i:i + N]).encode()).hexdigest()
        if int(h[:8], 16) % SAMPLE_MOD == 0:
            out.add(h[:12])
    return out


def holdout_reps():
    reps = {}
    for h, f in (("H-OUT-C13", "SAMPLE"), ("H-HOLD-C13", "SAMPLE"), ("H-HOLD-C13", "RESERVE"), ("H-REL-C13", "SAMPLE")):
        for r in read_csv(OUT / "holdouts" / h / f"{f}.csv"):
            reps[r["judgment_key"]] = r["rep_doc_id"]
    return reps


def _text(blobs, src):
    if src.startswith("git:"):
        return blobs.get(src[4:])
    if src.startswith("hf:"):
        return (additions_cache_dir() / "text" / src.rsplit("/", 1)[-1]).read_bytes()
    return None


def build():
    """Boilerplate = a sampled shingle present in >= BOILERPLATE_DF distinct judgments of the WHOLE corpus.
    Shingles shared only by a holdout judgment and one sibling order are kept: such sibling text reveals the
    holdout's content too."""
    feats = {r["doc_id"]: r for r in read_csv(OUT / "frame" / "TEXT_FEATURES.csv")}
    key_of = {r["doc_id"]: r["judgment_key"] for r in read_csv(OUT / "frame" / "FRAME_RECORDS.csv")}
    reps = holdout_reps()
    blobs = CorpusBlobs()
    per_key = defaultdict(set)
    try:
        for doc, f in sorted(feats.items()):
            b = _text(blobs, f["text_source"])
            if b:
                per_key[key_of[doc]] |= shingle_hashes(b.decode("utf-8", errors="replace"))
    finally:
        blobs.close()
    df = defaultdict(int)
    for hs in per_key.values():
        for x in hs:
            df[x] += 1
    per_doc = {k: per_key[k] for k in reps if per_key.get(k)}
    keep = sorted({x for hs in per_doc.values() for x in hs if df[x] < BOILERPLATE_DF})
    head = (f"# C13-A0 holdout shingle fingerprint: {len(per_doc)} holdout judgments; {N}-word shingles; 1/{SAMPLE_MOD} "
            f"hash sample; corpus boilerplate (in >={BOILERPLATE_DF} judgments) removed; truncated sha256; no text\n")
    return {"leakguard/HOLDOUT_SHINGLE_FINGERPRINT.txt": head + "\n".join(keep) + "\n"}


def load_fp():
    return {l.strip() for l in FP.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")}


def scan_text(text, fp=None):
    fp = fp if fp is not None else load_fp()
    return len(shingle_hashes(text) & fp)


def scan_tree(root=PKG, fp=None):
    """Return {relative path: hits} for files at or above MIN_HITS."""
    fp = fp if fp is not None else load_fp()
    bad = {}
    for p in sorted(Path(root).rglob("*")):
        if not p.is_file() or p == FP or p.suffix not in SCAN_SUFFIXES or "__pycache__" in p.parts:
            continue
        n = scan_text(p.read_text(encoding="utf-8", errors="replace"), fp)
        if n >= MIN_HITS:
            bad[str(p.relative_to(root))] = n
    return bad


def main():
    if "--scan" in sys.argv[1:]:
        paths = [a for a in sys.argv[1:] if a != "--scan"]
        if paths:
            fp = load_fp()
            res = {p: scan_text(Path(p).read_text(encoding="utf-8", errors="replace"), fp) for p in paths}
        else:
            res = scan_tree()
        print(json.dumps(res, indent=1))
        return 1 if any(v >= MIN_HITS for v in res.values()) else 0
    return write_or_check(build(), OUT, argv_check(), "c13_leakguard")


if __name__ == "__main__":
    sys.exit(main())
