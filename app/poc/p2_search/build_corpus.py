"""Build the P2/P3 benchmark corpus from the c7 object store at data snapshot ad77758d.

Output (scratch, not committed): <work>/corpus/corpus.jsonl and chunks.jsonl
Committed: docs/architecture/poc/data/p2_corpus_manifest.csv (doc_id, type, text sha256)

Usage: python -I build_corpus.py --c7 /home/user/c7 --repo <b-poc worktree> --work <dir>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.restricted import load_restricted, assert_clean_texts  # noqa: E402

SNAPSHOT = "ad77758d"
SEED = 13
N_JUDGMENTS = 2400
STATUTE_TYPES = {"act", "rules", "regulations", "notification", "schedule", "executive_order"}
CHUNK_WORDS = 180          # ~256 word-piece tokens for BERT-class tokenisers
JUDGMENT_MAX_CHUNKS = 8    # head-weighted sample of passages per judgment (P3 cost control)
PAGE_RE = re.compile(r"\[\[?page[^\]]*\]\]?|<<<\s*page[^>]*>>>|^=+\s*page\s*\d+\s*=+$", re.I | re.M)


class Batch:
    def __init__(self, repo: Path):
        self.p = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def get(self, spec: str) -> bytes | None:
        self.p.stdin.write(spec.encode() + b"\n"); self.p.stdin.flush()
        header = self.p.stdout.readline().split()
        if len(header) < 3 or header[1] == b"missing":
            return None
        size = int(header[2]); data = self.p.stdout.read(size); self.p.stdout.read(1)
        return data


def chunk_words(text: str, n: int) -> list[str]:
    w = text.split()
    return [" ".join(w[i:i + n]) for i in range(0, len(w), n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--c7", type=Path, required=True)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--manifest-out", type=Path, required=True)
    a = ap.parse_args()
    rs = load_restricted(a.repo)
    print("restricted list commit", rs.ref_commit, "doc_ids", sorted(rs.doc_ids))
    b = Batch(a.c7)
    manifest = list(csv.DictReader(io.StringIO(b.get(f"{SNAPSHOT}:data/manifest.csv").decode())))
    excluded, judgments, statutes = [], [], []
    for row in manifest:
        reason = rs.blocks(doc_id=row["doc_id"], sha256=row["sha256"])
        if reason:
            excluded.append((row["doc_id"], reason)); continue
        if row["type"] == "judgment":
            judgments.append(row)
        elif row["type"] in STATUTE_TYPES:
            statutes.append(row)
    rnd = random.Random(SEED)
    sci = [r for r in judgments if r["doc_id"].startswith("sc-")]
    other = [r for r in judgments if not r["doc_id"].startswith("sc-")]
    rnd.shuffle(other)
    candidates = sci + other  # all SC judgments, then a seeded random sample of HC/other

    out_docs, out_chunks = [], []
    def load(row):
        mpath = f"data/meta/{row['doc_id']}.json"
        mblob = b.get(f"{SNAPSHOT}:{mpath}")
        if mblob is None:
            return None, "no_meta"
        meta = json.loads(mblob)
        tpath = meta.get("text_path") or f"data/text/{row['doc_id']}.txt"
        tblob = b.get(f"{SNAPSHOT}:{tpath}")
        for kw in (dict(blob=mblob), dict(blob=tblob), dict(path=mpath), dict(path=tpath),
                   dict(sha256=meta.get("sha256")), dict(doc_id=meta.get("doc_id"))):
            if (kw.get("blob", b"x") is not None) and rs.blocks(**kw):
                return None, "restricted:" + rs.blocks(**kw)
        if tblob is None:
            return None, "no_text"
        text = tblob.decode("utf-8", "replace")
        if len(text.strip()) < 500:
            return None, "short_text"
        if meta.get("language") not in (None, "en"):
            return None, "non_english"
        return dict(
            doc_id=meta["doc_id"], doc_type=meta.get("doc_type"), title=meta.get("title"),
            number=meta.get("number"), case_numbers=meta.get("case_numbers") or [],
            neutral_citation=meta.get("neutral_citation"),
            reported_citations=meta.get("reported_citations") or [],
            parties=meta.get("parties"), court=meta.get("court"), bench=meta.get("bench"),
            issue_date=meta.get("issue_date"), sha256=meta.get("sha256"), raw_path=meta.get("raw_path"),
            text_path=tpath, text_sha256=hashlib.sha256(tblob).hexdigest(), text=text), None

    skipped = {}
    for row in statutes:
        d, why = load(row)
        if d: out_docs.append(d)
        else: skipped[why] = skipped.get(why, 0) + 1
    nj = 0
    for row in candidates:
        if nj >= N_JUDGMENTS: break
        d, why = load(row)
        if d: out_docs.append(d); nj += 1
        else: skipped[why] = skipped.get(why, 0) + 1
    assert_clean_texts(rs, out_docs)

    for d in out_docs:
        clean = PAGE_RE.sub(" ", d["text"])
        chunks = chunk_words(clean, CHUNK_WORDS)
        if d["doc_type"] == "judgment" and len(chunks) > JUDGMENT_MAX_CHUNKS:
            head = chunks[:4]
            rest = chunks[4:]
            step = len(rest) / 4
            chunks = head + [rest[int(i * step)] for i in range(4)]
        for i, c in enumerate(chunks):
            out_chunks.append(dict(chunk_id=f"{d['doc_id']}::{i}", doc_id=d["doc_id"], text=c))

    a.work.mkdir(parents=True, exist_ok=True)
    with open(a.work / "corpus.jsonl", "w") as f:
        for d in out_docs: f.write(json.dumps(d) + "\n")
    with open(a.work / "chunks.jsonl", "w") as f:
        for c in out_chunks: f.write(json.dumps(c) + "\n")
    # derived unit files used by the dense indexes and by the like-for-like lexical index (tantivy_p3)
    types = {d["doc_id"]: d["doc_type"] for d in out_docs}
    P3_STATUTES = {"act-army-1950", "act-air-force-1950", "act-navy-1957", "act-armed-forces-tribunal-2007",
                   "rules-army-rules-1954", "rules-aft-procedure-rules-2008"}
    with open(a.work / "vchunks.jsonl", "w") as fv, open(a.work / "p3chunks.jsonl", "w") as fp:
        for c in out_chunks:
            i = int(c["chunk_id"].rsplit("::", 1)[1]); judgment = types[c["doc_id"]] == "judgment"
            if not judgment or i < 2:
                fv.write(json.dumps(c) + "\n")       # 2 head chunks per judgment + all statute chunks
            if (judgment and i == 0) or c["doc_id"] in P3_STATUTES:
                fp.write(json.dumps(c) + "\n")       # P3/dense units: 1 head chunk per judgment + 6 military statutes
    a.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.manifest_out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["doc_id", "doc_type", "text_sha256", "words"])
        for d in out_docs: w.writerow([d["doc_id"], d["doc_type"], d["text_sha256"], len(d["text"].split())])
    stats = dict(snapshot=SNAPSHOT, seed=SEED, restricted_list_commit=rs.ref_commit,
                 excluded_by_restricted_list=excluded, skipped=skipped,
                 docs=len(out_docs), judgments=nj, statutes=len(out_docs) - nj,
                 chunks=len(out_chunks), words=sum(len(d["text"].split()) for d in out_docs))
    (a.manifest_out.parent / "p2_corpus_stats.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
