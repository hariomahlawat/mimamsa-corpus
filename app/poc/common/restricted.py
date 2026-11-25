"""Restricted-material guard for every PoC corpus, index and embedding job.

The source of truth is config/restricted_material.json on branch claude/c13-gov
(commit ea282cbd at the time of writing). This module loads it from git and
excludes a document when ANY of the following matches:
  - doc_id
  - source_sha256 (raw PDF hash recorded in meta.sha256)
  - sha256 of the meta or text blob (derived_sha256)
  - repository path (hosted_paths)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

GOV_REF = "claude/c13-gov"
GOV_PATH = "config/restricted_material.json"


@dataclass
class RestrictedSet:
    ref_commit: str
    doc_ids: set[str] = field(default_factory=set)
    shas: set[str] = field(default_factory=set)
    paths: set[str] = field(default_factory=set)
    raw: dict = field(default_factory=dict)

    def blocks(self, *, doc_id: str | None = None, sha256: str | None = None,
               path: str | None = None, blob: bytes | None = None) -> str | None:
        """Return a reason string if the item is restricted, else None."""
        if doc_id and doc_id.split("#")[0] in self.doc_ids:
            return f"doc_id:{doc_id}"
        if sha256 and sha256.lower() in self.shas:
            return f"sha256:{sha256}"
        if path and path in self.paths:
            return f"path:{path}"
        if blob is not None:
            h = hashlib.sha256(blob).hexdigest()
            if h in self.shas:
                return f"blob_sha256:{h}"
        return None


def load_restricted(repo: Path) -> RestrictedSet:
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", GOV_REF], text=True).strip()
    data = json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{GOV_PATH}"]))
    rs = RestrictedSet(ref_commit=commit, raw=data)
    for item in data["items"]:
        rs.doc_ids.add(item["doc_id"])
        rs.shas.add(item["source_sha256"].lower())
        rs.shas.update(s.lower() for s in item.get("derived_sha256", []))
        rs.paths.update(item.get("hosted_paths", []))
    if not rs.doc_ids or not rs.shas:
        raise RuntimeError("restricted list is empty; refusing to continue")
    return rs


def assert_clean_texts(rs: RestrictedSet, records) -> None:
    """Hard post-condition: no record in an output may match the restricted set."""
    for r in records:
        reason = rs.blocks(doc_id=r.get("doc_id"), sha256=r.get("sha256"), path=r.get("text_path"))
        if reason:
            raise AssertionError(f"restricted material leaked into output: {reason}")
