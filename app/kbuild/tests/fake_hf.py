"""Test-only stand-ins for the HF dataset (no network): a canonical-layout corpus and a Cycle 15 v7-style package built
from the SYN fixture mirror, served by an in-memory tree lister and byte opener with the pinned-tree semantics of
`hf_fetch.PinnedRepo` (git blob ids, optional LFS sha256). Everything is synthetic and fictional."""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

REPO = "hariomahlawat/mimamsa-corpus"     # build_sample pins provenance to this repo name; the revisions are fake
CANON_REV = "1" * 40
V7_REV = "2" * 40
V7_NS = "legal_knowledge/candidates/cycle15/v7"
LEXICON = "legal_knowledge/reference_data/abbreviations/v1.0/army_abbreviations_versioned_union_v1.0.json"


def blob_id(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class FakeHF:
    """{(repo, revision): {path: bytes}}; `lfs` paths report an LFS sha256 like large files on the real hub."""

    def __init__(self, trees: dict, lfs_suffixes=(".pdf", ".gz")):
        self.trees = trees
        self.lfs_suffixes = lfs_suffixes
        self.opened: list[str] = []
        self.listed: list[str] = []
        self.tamper: dict[str, bytes] = {}

    def transport(self, repo: str, revision: str):
        files = self.trees[(repo, revision)]

        def lister(paths):
            out = {}
            for p in paths:
                self.listed.append(p)
                if p.startswith("prefix:"):
                    pre = p[len("prefix:"):]
                    out.update({q: self._entry(q, b) for q, b in files.items() if q.startswith(pre)})
                elif p in files:
                    out[p] = self._entry(p, files[p])
            return out

        def opener(path):
            self.opened.append(path)
            yield self.tamper.get(path, files[path])
        return lister, opener

    def _entry(self, p, b):
        return {"size": len(b), "blob_id": blob_id(b), "lfs_sha256": sha(b) if p.endswith(self.lfs_suffixes) else None}

    def routed(self):
        """(lister, opener) for a build: routes by the revision each PinnedRepo was created for (PinnedRepo passes only
        paths, so the build's two repos are told apart by path; the fake trees have disjoint paths)."""
        def lister(paths):
            out = {}
            for (repo, rev), files in self.trees.items():
                lst, _ = self.transport(repo, rev)
                out.update(lst([p for p in paths if p in files or p.startswith("prefix:")]))
            return out

        def opener(path):
            for (repo, rev), files in self.trees.items():
                if path in files:
                    self.opened.append(path)
                    yield self.tamper.get(path, files[path])
                    return
            raise FileNotFoundError(path)
        return lister, opener


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def canonical_from_mirror(v1_root: Path) -> dict[str, bytes]:
    """The SYN fixture documents laid out as the canonical HF dataset (data/manifest.csv, raw_manifest.csv, meta, raw,
    text) plus a tiny abbreviation lexicon."""
    docs = _jsonl(v1_root / "data" / "documents.jsonl")
    ders = {d["doc_id"]: d for d in _jsonl(v1_root / "data" / "derived_text.jsonl")}
    files, rows, raws = {}, [], []
    for d in sorted(docs, key=lambda x: x["doc_id"]):
        did, h = d["doc_id"], d["source_copy"]["sha256"]
        raw = f"data/raw/syn/{h}.pdf"
        files[raw] = (v1_root / "originals" / f"{h}.pdf").read_bytes()
        files[f"data/text/{did}.txt"] = (v1_root / ders[did]["text_path"]).read_bytes()
        meta = {"doc_id": did, "sha256": h, "raw_path": raw, "text_path": f"data/text/{did}.txt", "mime_type": "application/pdf",
                "doc_type": d["doc_type"], "title": d.get("title"), "number": d.get("number"), "issuing_authority": d.get("issuing_authority"),
                "issue_date": d.get("issue_date"), "source": "indiacode", "status": "unknown", "text_method": "pdf_text", "language": "en",
                "retrieved_at": "2026-11-01T00:00:00Z", "source_url": f"https://example.invalid/{did}.pdf", "access_marking": None}
        files[f"data/meta/{did}.json"] = json.dumps(meta, sort_keys=True).encode()
        rows.append({"doc_id": did, "type": d["doc_type"], "status": "unknown", "source_url": meta["source_url"], "sha256": h,
                     "retrieved_at": meta["retrieved_at"]})
        raws.append({"sha256": h, "raw_path": raw, "bytes": len(files[raw]), "content_type": "application/pdf", "retrieved_at": meta["retrieved_at"],
                     "source_url": meta["source_url"], "doc_id": did, "parent_doc_id": "", "category": "syn", "title": d.get("title") or "",
                     "original_filename": f"{did}.pdf"})

    def csv_bytes(recs):
        s = io.StringIO()
        w = csv.DictWriter(s, fieldnames=list(recs[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(recs)
        return s.getvalue().encode()
    files["data/manifest.csv"] = csv_bytes(rows)
    files["data/raw_manifest.csv"] = csv_bytes(raws)
    files[LEXICON] = json.dumps({"abbreviations": {"JAG": {"preferred": ["Judge Advocate General"], "preferred_basis": "synthetic test"}}}).encode()
    return files


def v7_package(overlap_sha: str, overlap_doc: str, *, eligible: bool = False) -> dict[str, bytes]:
    """A two-record v7-style package: one candidate whose original is a canonical copy (overlap), one that is not."""
    pages = {overlap_doc: {1: "Section 69 of the Army Act applies here.", 2: "Second page."},
             "AFT-SYN-1": {1: "IN THE ARMED FORCES TRIBUNAL\nORDER"}}
    recs = []
    for did, osha in ((overlap_doc, overlap_sha), ("AFT-SYN-1", sha(b"synthetic v7 original"))):
        pmap = pages[did]
        mentions = [{"page": 1, "start": 0, "end": 10, "text": pmap[1][0:10]}] if did == overlap_doc else []
        recs.append({"schema": "mimamsa-c14-document-candidate-v1", "doc_id": did, "original_sha256": osha,
                     "derivative_sha256": sha(json.dumps(pmap, sort_keys=True).encode()), "application_eligible": eligible,
                     "page_count": len(pmap), "page_text_sha256": [sha(pmap[n].encode()) for n in sorted(pmap)],
                     "provision_mentions": mentions, "citation_mentions": [], "decision_date_metadata": None})
    rec_bytes = "".join(json.dumps(r, sort_keys=True) + "\n" for r in recs).encode()
    gz = io.BytesIO()
    with gzip.GzipFile(fileobj=gz, mode="wb", mtime=0) as fh:
        for did in sorted(pages):
            for n in sorted(pages[did]):
                fh.write((json.dumps([did, n, pages[did][n]]) + "\n").encode())
    return {f"{V7_NS}/records.jsonl": rec_bytes, f"{V7_NS}/pages.jsonl.gz": gz.getvalue()}


def plan(doc_ids: list[str], canon: dict[str, bytes], v7: dict[str, bytes]) -> dict:
    return {"record_kind": "kbuild_fetch_plan", "format": "mimamsa-kbuild-fetch-plan/1", "name": "syn-fake",
            "canonical": {"repo": REPO, "revision": CANON_REV, "layout": "HF_CANONICAL_V1",
                          "manifests": {"data/manifest.csv": sha(canon["data/manifest.csv"]), "data/raw_manifest.csv": sha(canon["data/raw_manifest.csv"])},
                          "doc_ids": sorted(doc_ids), "research": [{"path": LEXICON, "as": "abbreviations"}], "selection_basis": "test"},
            "v7": [{"name": "syn-v7", "repo": REPO, "revision": V7_REV, "namespace": V7_NS, "files": ["records.jsonl", "pages.jsonl.gz"],
                    "expected_sha256": {"records.jsonl": sha(v7[f"{V7_NS}/records.jsonl"]), "pages.jsonl.gz": sha(v7[f"{V7_NS}/pages.jsonl.gz"])},
                    "receipt": {"git_commit": None, "path": "test", "sha256": None}}],
            "transfer": {"max_workers": 2, "max_bytes_per_second": 0, "min_free_disk_bytes": 1, "retries": 0, "timeout_seconds": 10}}
