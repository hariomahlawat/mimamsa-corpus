"""Restricted-material exclusion, keyed on the repository register config/restricted_material.json.

That file (introduced by the governance workstream, register RM-001 onwards) is the single source of truth.
This module never carries its own list of hashes, ids or paths: it reads the register and fails closed when the
register is missing or malformed. Matching semantics follow scripts/restricted_material.py::is_restricted so that
pipeline tooling and the application agree.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

ENV_OVERRIDE = "MIMAMSA_RESTRICTED_MATERIAL_CONFIG"
REGISTER_RELATIVE_PATH = "config/restricted_material.json"


class RestrictedConfigError(RuntimeError):
    """Register missing or malformed. Callers must treat this as 'reject everything'."""


def repository_root() -> Path:
    # app/contract/mimamsa_contract/restricted.py -> repository root is three levels above the package directory
    return Path(__file__).resolve().parents[3]


def default_config_path() -> Path:
    override = os.environ.get(ENV_OVERRIDE)
    if override:
        return Path(override)
    return repository_root() / REGISTER_RELATIVE_PATH


@dataclass(frozen=True)
class RestrictedRegister:
    config_path: Path
    config_sha256: str
    restriction_ids: frozenset[str]
    sha256s: frozenset[str]
    doc_ids: frozenset[str]
    paths: frozenset[str]

    @staticmethod
    def _norm_path(path: str) -> str:
        p = path.replace("\\", "/")
        while p.startswith("./"):
            p = p[2:]
        return p.lstrip("/")

    def match(self, *, sha256: str | None = None, doc_id: str | None = None, path: str | None = None) -> str | None:
        """Return a short reason if the item is restricted, else None."""
        if sha256 and sha256.lower() in self.sha256s:
            return "sha256 listed in restricted-material register"
        if doc_id:
            base = doc_id.split("#", 1)[0]
            if doc_id in self.doc_ids or base in self.doc_ids:
                return "doc_id listed in restricted-material register"
        if path:
            p = self._norm_path(path)
            if p in self.paths:
                return "path listed in restricted-material register"
            low = p.lower()
            if any(s in low for s in self.sha256s):
                return "path contains a restricted sha256"
            if any(i in p for i in self.doc_ids):
                return "path contains a restricted doc_id"
        return None

    def is_restricted(self, **kw) -> bool:
        return self.match(**kw) is not None


def load_register(config_path: Path | str | None = None) -> RestrictedRegister:
    path = Path(config_path) if config_path else default_config_path()
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RestrictedConfigError(
            f"restricted-material register not readable at {path}: {exc}. Validation fails closed."
        ) from exc
    try:
        data = json.loads(raw.decode("utf-8"))
        items = data["items"]
        if not isinstance(items, list) or not items:
            raise ValueError("register has no items")
        ids, shas, docs, paths = set(), set(), set(), set()
        for it in items:
            rid = it["restriction_id"]
            src = it["source_sha256"].lower()
            if len(src) != 64 or any(c not in "0123456789abcdef" for c in src):
                raise ValueError(f"{rid}: malformed source_sha256")
            ids.add(rid)
            shas.add(src)
            shas.update(s.lower() for s in it.get("derived_sha256", []))
            if it.get("doc_id"):
                docs.add(it["doc_id"])
            paths.update(RestrictedRegister._norm_path(p) for p in it.get("hosted_paths", []))
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise RestrictedConfigError(f"restricted-material register at {path} is malformed: {exc}") from exc
    return RestrictedRegister(
        config_path=path,
        config_sha256=hashlib.sha256(raw).hexdigest(),
        restriction_ids=frozenset(ids),
        sha256s=frozenset(shas),
        doc_ids=frozenset(docs),
        paths=frozenset(paths),
    )
