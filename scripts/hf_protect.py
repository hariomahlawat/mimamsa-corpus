"""Guards for writes to the private Hugging Face corpus dataset.

Implements the standing owner instruction (docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md, ADR-0004):

- Corpus writes are versioned and non-destructive.
- No remote file is deleted by a sync.
- No existing file under a protected prefix is overwritten with different bytes.

Deleting source documents needs separate owner approval, which these scripts never assume.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

# Original sources and preservation copies: may be added to, never replaced or removed by a sync.
PROTECTED_PREFIXES = (
    "data/raw/",
    "legal_knowledge/preservation/",
    "legal_knowledge/manual_sources/",
    "legal_knowledge/judgment_originals/",
    "legal_knowledge/curated_originals/",
    "legal_knowledge/judgment_sources/",
)

# Folders that a sync must never upload from a local tree, even additively. The canonical copy lives only on HF.
NEVER_SYNC_PATTERNS = ["preservation/**", "**/preservation/**"]


class ProtectedPathError(RuntimeError):
    pass


def is_protected(path_in_repo: str) -> bool:
    return any(path_in_repo.startswith(p) for p in PROTECTED_PREFIXES)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_sha256_index(api, repo_id: str, prefix: str, revision: str | None = None) -> dict:
    """path -> (lfs_sha256 | None, git_oid | None) for remote files under prefix.

    Only a missing folder (EntryNotFound) is treated as empty. A missing repository or revision, or any other
    failure, propagates, so the sync stops (fail closed; review R50-02).
    """
    out = {}
    try:
        entries = api.list_repo_tree(repo_id, repo_type="dataset", path_in_repo=prefix.rstrip("/"),
                                     recursive=True, revision=revision)
        for e in entries:
            if getattr(e, "size", None) is None:
                continue
            lfs = getattr(e, "lfs", None)
            out[e.path] = (getattr(lfs, "sha256", None) if lfs else None, getattr(e, "blob_id", None))
    except Exception as exc:
        if type(exc).__name__ == "EntryNotFoundError":
            return {}
        raise
    return out


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def check_additive(local_files: list[tuple[Path, str]], remote: dict) -> list[str]:
    """Return the protected repo paths that would be overwritten with different bytes. Empty means safe.

    local_files: (local path, path_in_repo).
    remote: path -> (lfs_sha256 | None, git_oid | None).
    """
    conflicts = []
    for local, rpath in local_files:
        if not is_protected(rpath) or rpath not in remote:
            continue
        lfs_sha, oid = remote[rpath]
        if lfs_sha:
            same = sha256_file(local) == lfs_sha
        elif oid:
            same = git_blob_sha1(local) == oid
        else:
            same = False  # cannot prove identity: treat as a conflict (fail closed)
        if not same:
            conflicts.append(rpath)
    return conflicts


def assert_additive(api, repo_id: str, local_files: list[tuple[Path, str]], revision: str | None = None) -> None:
    prefixes = sorted({rp.rsplit("/", 1)[0] + "/" for _, rp in local_files if is_protected(rp)})
    remote = {}
    for p in prefixes:
        remote.update(remote_sha256_index(api, repo_id, p, revision))
    bad = check_additive(local_files, remote)
    if bad:
        raise ProtectedPathError(
            f"refusing to overwrite {len(bad)} protected file(s) with different bytes, e.g. {bad[:3]}; "
            "originals are never replaced; write a new versioned path instead")
