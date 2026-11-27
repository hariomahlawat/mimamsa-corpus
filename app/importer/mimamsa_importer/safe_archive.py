"""Safe reading of DOCX (ZIP) containers for the importer's byte checks (consumer requirement I4).

Re-implements the PR #76 `safe_archive_member` rules here; nothing is imported from the producer's branch. The
container is never extracted to disk and nothing in it is executed. A member is read only if:
- its name is a relative POSIX path: no absolute path, drive, backslash, NUL, empty or '..' segment;
- it is unique in the archive (also case-insensitively, as on NTFS) and is a file, not a directory;
- it is not encrypted, and uses STORED or DEFLATED compression;
- its declared and actual uncompressed sizes are within the per-member and whole-archive limits, and the
  compression ratio is bounded (zip-bomb guard).
Any violation raises UnsafeArchive; callers treat that as "the fact cannot be recomputed" (fail closed).
"""
from __future__ import annotations

import io
import zipfile

MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_MEMBERS = 10_000
MAX_RATIO = 200


class UnsafeArchive(ValueError):
    pass


def _name_problem(name: str) -> str | None:
    if not name or "\x00" in name or "\\" in name:
        return "empty name, NUL or backslash"
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return "absolute path or drive"
    parts = name.split("/")
    if any(p in ("", ".", "..") for p in parts[:-1]) or parts[-1] in (".", ".."):
        return "empty, '.' or '..' segment"
    return None


def read_members(data: bytes, wanted: set[str]) -> dict[str, bytes]:
    """Return {name: bytes} for the wanted member names that exist; raise UnsafeArchive if the archive or any wanted
    member breaks a rule. Members not wanted are inspected (names, sizes, flags) but never decompressed."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, ValueError, OSError) as exc:
        raise UnsafeArchive(f"not a readable ZIP container ({type(exc).__name__})") from exc
    infos = zf.infolist()
    if len(infos) > MAX_MEMBERS:
        raise UnsafeArchive("too many members")
    seen, total = set(), 0
    for i in infos:
        raw = i.orig_filename  # before zipfile normalises os.sep (on Windows it turns backslashes into slashes)
        why = _name_problem(raw.rstrip("/") if i.is_dir() else raw) or (None if raw == i.filename else "name altered by normalisation")
        if why:
            raise UnsafeArchive(f"unsafe member name ({why})")
        key = i.filename.casefold()
        if key in seen:
            raise UnsafeArchive("duplicate member name (also case-insensitively)")
        seen.add(key)
        if i.flag_bits & 0x1:
            raise UnsafeArchive("encrypted member")
        if i.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise UnsafeArchive("unsupported compression method")
        if i.file_size > MAX_MEMBER_BYTES:
            raise UnsafeArchive("member exceeds the size limit")
        if i.compress_size and i.file_size / i.compress_size > MAX_RATIO:
            raise UnsafeArchive("compression ratio exceeds the limit")
        total += i.file_size
        if total > MAX_TOTAL_BYTES:
            raise UnsafeArchive("archive exceeds the total size limit")
    out = {}
    by_name = {i.filename: i for i in infos}
    for name in sorted(wanted):
        i = by_name.get(name)
        if i is None or i.is_dir():
            continue
        with zf.open(i) as fh:
            body = fh.read(MAX_MEMBER_BYTES + 1)
        if len(body) != i.file_size or len(body) > MAX_MEMBER_BYTES:
            raise UnsafeArchive("member size differs from its declaration")
        out[name] = body
    return out
