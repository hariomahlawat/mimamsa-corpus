"""C13-A8: read-only index over the repository's source-copy registers.

Every anchor in the adviser package must resolve here: a sha256 that a committed register binds to a stored
file path, and a doc_id that a committed register binds to that same sha256. Standard library only; reads
committed files only (no network, no /home/user/c7), so CI can run it.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
AW = REPO / "legal_knowledge" / "audit_work"

# RM-001 (config/restricted_material.json). Hard-coded here as a deny-list so the build and the test fail
# even if the register file were changed; the test also cross-checks the register.
RM001_SHA = "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"
RM001_DOC = "regs-regulations-for-the-air-force-reprinted-edition-2000"

csv.field_size_limit(1 << 30)

# (register name, repo-relative path). Order is the order of preference when reporting a binding.
REGISTERS = {
    "CRAWLER_MANIFEST_HF5524": "legal_knowledge/audit_work/C12-CONSOLIDATION/hf_verification_c12/capture_refs/data__manifest.csv.gz",
    "HF_HASH_LEDGER_C12": "legal_knowledge/audit_work/C12-CONSOLIDATION/hf_verification_c12/HASH_LEDGER.csv.gz",
    "COPY_VERIFICATION_C12": "legal_knowledge/audit_work/C12-CONSOLIDATION/copy_verification_c12/COPY_VERIFICATION_MANIFEST.csv",
    "AUTH_LEDGER_V0_COPY_REGISTER": "legal_knowledge/audit_work/AUTH-LEDGER/effective/v0000/source_copy_register.csv",
    "HF_INGESTED_REDOWNLOAD_C12": "legal_knowledge/audit_work/C12-CONSOLIDATION/copy_verification_c12/HF_INGESTED_REDOWNLOAD_C12.csv",
    "C13_A1_RECOVERY_POPULATION": "legal_knowledge/audit_work/C13-A1-OCR/RECOVERY_POPULATION.csv",
    "C12_ACQUISITION_MANIFEST": "legal_knowledge/audit_work/C12-CONSOLIDATION/acquisition/ACQUISITION_MANIFEST.csv",
    "C13_A7_ACQUISITION_MANIFEST": "legal_knowledge/audit_work/C13-A7-ACQUISITION/acquisition/ACQUISITION_MANIFEST_C13.csv",
    "C13_A7_HF_VERIFY": "legal_knowledge/audit_work/C13-A7-ACQUISITION/acquisition/HF_VERIFY_C13.csv",
    "C11_RE_ACQUISITION_MANIFEST": "legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/excluded/RE_ACQUISITION_MANIFEST.csv",
    "C12_JUDICIAL_INGESTION_LOG": "legal_knowledge/audit_work/C12-CONSOLIDATION/judicial_recovery_c12/INGESTION_LOG.csv",
    "C13_A1_RELEVANCE_RERUN": "legal_knowledge/audit_work/C13-A1-OCR/RELEVANCE_RERUN.csv",
}


def _rows(rel: str):
    p = REPO / rel
    data = p.read_bytes()
    if rel.endswith(".gz"):
        data = gzip.decompress(data)
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Registers:
    """bind[(doc_id, sha)] -> set(register); path[sha] -> list((register, stored path))."""

    def __init__(self):
        self.bind: dict[tuple[str, str], set[str]] = {}
        self.path: dict[str, list[tuple[str, str]]] = {}
        self.ids_by_sha: dict[str, set[str]] = {}
        self.file_sha = {name: sha256_file(REPO / rel) for name, rel in REGISTERS.items()}
        self._load()

    def _b(self, doc_id, sha, reg):
        doc_id = (doc_id or "").strip()
        sha = (sha or "").strip().lower()
        if not doc_id or not re.fullmatch(r"[0-9a-f]{64}", sha):
            return
        self.bind.setdefault((doc_id, sha), set()).add(reg)
        self.ids_by_sha.setdefault(sha, set()).add(doc_id)

    def _p(self, sha, path, reg):
        sha = (sha or "").strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", sha) and path:
            self.path.setdefault(sha, []).append((reg, path.strip()))

    def _load(self):
        R = REGISTERS
        # Crawler manifest at HF 5524c3d9: doc_id -> sha256 (file is data/raw/<src>/<yyyy>/<sha>.pdf, see ledger).
        for r in _rows(R["CRAWLER_MANIFEST_HF5524"]):
            self._b(r["doc_id"], r["sha256"], "CRAWLER_MANIFEST_HF5524")
        # HF hash ledger: every byte-verified HF path and its computed sha256.
        for r in _rows(R["HF_HASH_LEDGER_C12"]):
            self._p(r["computed_sha256"], r["path"], "HF_HASH_LEDGER_C12")
        for r in _rows(R["COPY_VERIFICATION_C12"]):
            sha = r["computed_sha256"] or r["expected_sha256"]
            self._b(r["source_id"], sha, "COPY_VERIFICATION_C12")
            self._b(r["copy_id"], sha, "COPY_VERIFICATION_C12")
            for d in (r.get("crawler_doc_ids") or "").split(";"):
                self._b(d, sha, "COPY_VERIFICATION_C12")
            self._p(sha, r["hosted_path"], "COPY_VERIFICATION_C12")
        for r in _rows(R["AUTH_LEDGER_V0_COPY_REGISTER"]):
            self._b(r["source_id"], r["sha256"], "AUTH_LEDGER_V0_COPY_REGISTER")
            self._b(r["copy_id"], r["sha256"], "AUTH_LEDGER_V0_COPY_REGISTER")
            for hp in (r.get("held_paths") or "").split(";"):
                self._p(r["sha256"], hp, "AUTH_LEDGER_V0_COPY_REGISTER")
        for r in _rows(R["HF_INGESTED_REDOWNLOAD_C12"]):
            self._p(r["computed_sha256"], r["hf_path"], "HF_INGESTED_REDOWNLOAD_C12")
        # A1 recovery population: HF path and commit of every held flagged title (e.g. C12 preserved at 3864faf3).
        for r in _rows(R["C13_A1_RECOVERY_POPULATION"]):
            if r.get("held") == "YES" and r.get("held_hf_path"):
                self._b(r["doc_id"], r["sha256"], "C13_A1_RECOVERY_POPULATION")
                self._p(r["sha256"], r["held_hf_path"], "C13_A1_RECOVERY_POPULATION")
        for r in _rows(R["C12_ACQUISITION_MANIFEST"]):
            self._b(r["target_id"], r["sha256"], "C12_ACQUISITION_MANIFEST")
            self._p(r["sha256"], r.get("stored_path"), "C12_ACQUISITION_MANIFEST")
        for r in _rows(R["C13_A7_ACQUISITION_MANIFEST"]):
            self._b(r["target_id"], r["sha256"], "C13_A7_ACQUISITION_MANIFEST")
        for r in _rows(R["C13_A7_HF_VERIFY"]):
            self._p(r["redownloaded_sha256"], r["path_in_repo"], "C13_A7_HF_VERIFY")
        for r in _rows(R["C11_RE_ACQUISITION_MANIFEST"]):
            self._b(r["doc_id"], r["sha256"], "C11_RE_ACQUISITION_MANIFEST")
        for r in _rows(R["C12_JUDICIAL_INGESTION_LOG"]):
            self._b(r["doc_id"], r["sha256"], "C12_JUDICIAL_INGESTION_LOG")
        # A1 relevance re-run: binds the crawler-style doc_id to the sha256 A1 read (its own register of the
        # 136 held documents). It is a binding register only; a stored path must come from another register.
        for r in _rows(R["C13_A1_RELEVANCE_RERUN"]):
            self._b(r["doc_id"], r["sha256"], "C13_A1_RELEVANCE_RERUN")

    def resolve(self, doc_id: str, sha: str):
        """Return (binding registers, (path register, stored path)) or raise ValueError."""
        regs = self.bind.get((doc_id, sha))
        if not regs:
            raise ValueError(f"doc_id {doc_id!r} is not bound to sha256 {sha[:12]}... in any register")
        paths = self.path.get(sha)
        if not paths:
            raise ValueError(f"sha256 {sha[:12]}... has no stored path in any register")
        # Prefer a durable repository/HF path over an absolute scratch path (A8/A9 review F05).
        durable = [x for x in paths if not x[1].startswith("/")]
        return sorted(regs), (durable or paths)[0]

    def by_prefix(self, prefix: str):
        prefix = prefix.lower()
        hits = {s for s in set(self.path) | set(self.ids_by_sha) if s.startswith(prefix)}
        return hits
