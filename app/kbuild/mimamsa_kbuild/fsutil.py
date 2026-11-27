"""File helpers: hashing, atomic writes, ordered tree listings, robust removal (importer vault files are read-only)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_atomic(path: Path, data: bytes) -> None:
    """Write `<path>.partial`, flush and fsync, then rename over `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".partial")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def json_pretty(obj) -> bytes:
    """Deterministic human-readable JSON (sorted keys, LF, final LF) for build reports."""
    return (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def files_under(root: Path) -> list[Path]:
    """Every regular file under root, ordered by POSIX relative path (byte order of the UTF-8 path)."""
    out = [p for p in root.rglob("*") if p.is_file()]
    return sorted(out, key=lambda p: p.relative_to(root).as_posix().encode("utf-8"))


def _retry_writable(func, path, _exc):
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)   # importer vault objects are written read-only
        func(path)
    except OSError:
        pass


def rmtree(path: Path) -> None:
    if path.exists():
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_retry_writable)
        else:
            shutil.rmtree(path, onerror=_retry_writable)


def link_or_copy(src: Path, dst: Path) -> None:
    """Hard link when the volume allows (no extra disk on the shared host), else copy. Never follows symlinks."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        os.chmod(dst, stat.S_IWRITE | stat.S_IREAD)
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
