"""Access-restricted material guard (owner directive, Cycle 13 section 31).

Use is_restricted() before indexing, embedding, packaging, publishing or sending any item anywhere.
The list lives in config/restricted_material.json; it is the single source of truth.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config" / "restricted_material.json"


@lru_cache(maxsize=1)
def _load():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    shas, ids, paths = set(), set(), set()
    for it in data["items"]:
        shas.add(it["source_sha256"].lower())
        shas.update(s.lower() for s in it.get("derived_sha256", []))
        ids.add(it["doc_id"])
        paths.update(it.get("hosted_paths", []))
    return frozenset(shas), frozenset(ids), frozenset(paths)


def is_restricted(*, sha256: str | None = None, doc_id: str | None = None, path: str | None = None) -> bool:
    shas, ids, paths = _load()
    if sha256 and sha256.lower() in shas:
        return True
    if doc_id and doc_id in ids:
        return True
    if path:
        p = path.replace("\\", "/").lstrip("./")
        if p in paths or any(s in p for s in shas) or any(i in p for i in ids):
            return True
    return False


def filter_unrestricted(records, *, sha_key="sha256", id_key="doc_id", path_key="path"):
    """Yield only records that are not restricted (dict-like records)."""
    for r in records:
        if not is_restricted(sha256=r.get(sha_key), doc_id=r.get(id_key), path=r.get(path_key)):
            yield r
