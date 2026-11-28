"""Bounded-memory access to bundle files for the importer (C16 Stage 3, stream S3-A).

The importer used to read every original, every derivative text and every accelerator file of a bundle into memory
at once, so peak memory grew with the corpus. Here a bundle file is held as a PATH plus the sha256 computed by a
streaming hash, and its bytes are read only when one check needs them (one file at a time; the largest single file
bounds memory, never the corpus). Every later read or copy re-verifies the bytes against the hash that was checked,
so a file changed after verification fails closed (`BlobChanged`) instead of being served.

- `BlobIndex`: sha256 -> bundle path (originals, derivative texts), a read-only Mapping[str, bytes].
- `PathFiles`: bundle path -> bytes on demand (derivative texts by their bundle path), a read-only Mapping.
- `VerifiedFile`: a file verified by streaming hash; materialised by a streaming, re-hashing copy.
- `copy_verified`: write `src` to `dst` atomically (temp, fsync, rename), hashing while copying; refuses a mismatch.
- `PageCache`: a small LRU of split derivative pages, re-read and re-verified on a miss.
"""
from __future__ import annotations

import hashlib
import os
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

CHUNK = 1 << 20


class BlobChanged(RuntimeError):
    """A bundle file no longer hashes to the value verified earlier in this import (fail closed)."""


def sha256_path(p: Path) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(CHUNK), b""):
            h.update(b)
            n += len(b)
    return h.hexdigest(), n


def read_verified(p: Path, sha: str) -> bytes:
    data = Path(p).read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        raise BlobChanged(f"{Path(p).name}: bytes changed after verification")
    return data


def copy_verified(src: Path, dst: Path, sha: str) -> int:
    """Streaming copy with hash check; atomic (temporary file, fsync, rename). Returns the byte count."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    h, n = hashlib.sha256(), 0
    try:
        with open(src, "rb") as fi, open(tmp, "wb") as fo:
            for b in iter(lambda: fi.read(CHUNK), b""):
                h.update(b)
                n += len(b)
                fo.write(b)
            fo.flush()
            os.fsync(fo.fileno())
        if h.hexdigest() != sha:
            raise BlobChanged(f"{Path(src).name}: bytes changed after verification")
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()
    return n


@dataclass(frozen=True)
class VerifiedFile:
    path: Path
    sha256: str
    size: int

    @classmethod
    def of(cls, p: Path) -> "VerifiedFile":
        sha, n = sha256_path(p)
        return cls(Path(p), sha, n)

    def read(self) -> bytes:
        return read_verified(self.path, self.sha256)

    def write_to(self, dst: Path) -> None:
        copy_verified(self.path, dst, self.sha256)


class BlobIndex(Mapping):
    """sha256 -> bytes, backed by bundle paths; the first path seen for a hash wins (like dict.setdefault)."""

    def __init__(self, paths=(), *, entries=()):
        """paths: hashed here (streaming). entries: (path, sha256, size) whose sha256 the signed-bundle validation has
        already checked against SHA256SUMS; not re-hashed now, but every later read or copy re-verifies the bytes."""
        self._by_sha: dict[str, tuple[Path, int]] = {}
        for p, sha, n in entries:
            self._by_sha.setdefault(sha, (Path(p), int(n)))
        for p in paths:
            sha, n = sha256_path(p)
            self._by_sha.setdefault(sha, (Path(p), n))

    def __getitem__(self, sha: str) -> bytes:
        p, _n = self._by_sha[sha]
        return read_verified(p, sha)

    def __contains__(self, sha) -> bool:
        return sha in self._by_sha

    def __iter__(self):
        return iter(self._by_sha)

    def __len__(self) -> int:
        return len(self._by_sha)

    def size(self, sha: str) -> int:
        return self._by_sha[sha][1]

    def path(self, sha: str) -> Path:
        return self._by_sha[sha][0]

    def copy_to(self, sha: str, dst: Path) -> None:
        copy_verified(self._by_sha[sha][0], dst, sha)


class PathFiles(Mapping):
    """bundle-relative path -> bytes, read on demand (consumers verify the bytes against their records)."""

    def __init__(self, root: Path, rels):
        self._root = Path(root)
        self._rels = {r for r in rels if (self._root / r).is_file()}

    def __getitem__(self, rel: str) -> bytes:
        if rel not in self._rels:
            raise KeyError(rel)
        return (self._root / rel).read_bytes()

    def __contains__(self, rel) -> bool:
        return rel in self._rels

    def __iter__(self):
        return iter(sorted(self._rels))

    def __len__(self) -> int:
        return len(self._rels)

    def copy_to(self, rel: str, dst: Path, sha: str) -> None:
        copy_verified(self._root / rel, dst, sha)


class PageCache:
    """LRU of {page: text} for verified derivatives (key -> loader); a miss re-reads and re-verifies the file."""

    def __init__(self, loader, capacity: int = 64):
        self._loader = loader
        self._cap = capacity
        self._d: OrderedDict = OrderedDict()

    def get(self, key):
        if key in self._d:
            self._d.move_to_end(key)
            return self._d[key]
        v = self._loader(key)
        self._d[key] = v
        if len(self._d) > self._cap:
            self._d.popitem(last=False)
        return v
