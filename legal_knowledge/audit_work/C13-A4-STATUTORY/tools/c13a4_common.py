"""Shared helpers for C13 workstream A4 (statutory evidence and temporal legal knowledge).

Derivative research tooling only. Nothing here writes to a frozen original, a register of an earlier cycle or a
held source copy. Held copies are read read-only and hash-verified before use.

Anchoring copies: the 48 C5 working-store copies preserved on the Hugging Face dataset under
legal_knowledge/preservation/c5_working_store/ (C12 copy_verification_c12 overlay, revision 5524c3d9). They are
expected in a local download directory (C13A4_HF_ANCHOR). For C5 copies that are not in the preservation overlay
(India Code compilations held in the canonical data snapshot) the C5 held_paths under the scratchpad are used,
again hash-verified.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
REPO = Path(os.environ.get("C13A4_REPO", PKG.parents[2]))
AW = REPO / "legal_knowledge/audit_work"
C12F_TOOLS = AW / "C12-CONSOLIDATION/statutory_citations/tools"
SCRATCH = Path(os.environ.get("C13A4_SCRATCH", REPO.parent.parent))  # held_paths in the C5 copy register are relative to this
HF_ANCHOR = Path(os.environ.get("C13A4_HF_ANCHOR", SCRATCH / "c13/a4work/hf_anchor"))
HELD_BASE = Path(os.environ.get("C13A4_HELD_BASE", SCRATCH / "c13/a4work/heldbase"))
OVERLAY = AW / "C12-CONSOLIDATION/copy_verification_c12/SOURCE_REGISTER_PRESERVATION_OVERLAY_C12.csv"
C5_COPY = AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv"

FROZEN = {
    "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl":
        "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1",
    "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl":
        "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a",
}

# Restricted material (owner directive, Cycle 13 s.31). Single source of truth: config/restricted_material.json with
# scripts/restricted_material.py on branch claude/c13-gov. That file is not on this branch, so the identifiers are
# mirrored here verbatim (read with `git show claude/c13-gov:config/restricted_material.json` on 2026-11-25); when the
# config file exists in the worktree it is loaded and must agree with this mirror.
RESTRICTED_MIRROR = {
    "doc_ids": {"regs-regulations-for-the-air-force-reprinted-edition-2000"},
    "sha256": {"4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14",
               "212ac873869bf3298b8194f6ad8a1a994b990242a3dab5d0f927e3e4c4ce2cea",
               "f26d3de7dfda70143b10b02dc664f13de342a74f0bee767387492363ac1421c5"},
    "paths": {"data/raw/indiacode/0000/4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14.pdf",
              "data/meta/regs-regulations-for-the-air-force-reprinted-edition-2000.json",
              "data/text/regs-regulations-for-the-air-force-reprinted-edition-2000.txt"},
}
RESTRICTED_TITLE_PAT = re.compile(r"regulations\s+for\s+the\s+air\s+force", re.I)


def restricted_sets():
    cfg = REPO / "config/restricted_material.json"
    r = {k: set(v) for k, v in RESTRICTED_MIRROR.items()}
    if cfg.exists():
        data = json.loads(cfg.read_text(encoding="utf-8"))
        for it in data["items"]:
            r["doc_ids"].add(it["doc_id"])
            r["sha256"].add(it["source_sha256"].lower())
            r["sha256"].update(s.lower() for s in it.get("derived_sha256", []))
            r["paths"].update(it.get("hosted_paths", []))
    return r


def assert_no_restricted(name: str, data: bytes):
    """Fail if any restricted identifier (sha256, doc_id, hosted path) or the restricted title appears in an output."""
    r = restricted_sets()
    t = data.decode("utf-8", "replace")
    tl = t.lower()
    for tok in sorted(r["sha256"] | r["doc_ids"] | r["paths"]):
        if tok.lower() in tl:
            raise SystemExit(f"RESTRICTED MATERIAL referenced in {name}: {tok}")
    if RESTRICTED_TITLE_PAT.search(t):
        raise SystemExit(f"RESTRICTED title (Regulations for the Air Force) referenced in {name}")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_csv(p: Path):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csv_bytes(rows, fields) -> bytes:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    return s.getvalue().encode("utf-8")


def verify_frozen():
    out = {}
    for rel, pin in FROZEN.items():
        got = sha256_file(REPO / rel)
        if got != pin:
            raise SystemExit(f"FROZEN ORIGINAL CHANGED: {rel} {got} != {pin}")
        out[rel] = pin
    return out


def prepare_held_base():
    """Build HELD_BASE as a tree of symlinks at the C5 held_paths, pointing at the hash-verified HF preservation
    copies where one exists and otherwise at the scratchpad working copy. Returns {copy_id: provenance}."""
    overlay = {r["copy_id"]: r for r in read_csv(OVERLAY)}
    prov = {}
    for c in read_csv(C5_COPY):
        hps = [x for x in c["held_paths"].split(";") if x]
        if not hps:
            continue
        target, origin = None, None
        o = overlay.get(c["copy_id"])
        if o:
            p = HF_ANCHOR / o["permanent_hosted_path"]
            if p.exists() and sha256_file(p) == c["sha256"]:
                target, origin = p, f"HF_PRESERVATION {o['permanent_hosted_path']} @ {o['hf_revision'][:8]}"
        if target is None:
            for hp in hps:
                p = SCRATCH / hp
                if p.exists() and sha256_file(p) == c["sha256"]:
                    target, origin = p, f"WORKING_COPY {hp}" + (" (HF preservation copy not available locally)" if o else "")
                    break
        if target is None:
            prov[c["copy_id"]] = "NOT_HELD"
            continue
        link = HELD_BASE / hps[0]
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() or link.exists():
            if link.resolve() != target.resolve():
                link.unlink()
                link.symlink_to(target.resolve())
        else:
            link.symlink_to(target.resolve())
        prov[c["copy_id"]] = origin
    return prov


def require_env():
    if sys.version_info < (3, 11):
        raise SystemExit("Python >= 3.11 required (tested with 3.13 in the scratchpad venv)")
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        raise SystemExit("PyMuPDF is required: use the scratchpad venv named in README.md") from None
