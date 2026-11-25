"""Path safety for a Windows-native target (NTFS) as well as POSIX.

A bundle path is accepted only if it is safe on both. Rejected:
- absolute paths, drive letters, UNC (\\\\server or //server), backslashes;
- parent traversal ("..") and empty or "." segments;
- NTFS alternate data streams and any ':';
- reserved device names in any segment, with or without extension (CON, PRN, AUX, NUL, COM0-9, LPT0-9, CONIN$, CONOUT$,
  and the superscript-digit COM/LPT forms);
- segments ending in '.' or ' ' (Win32 silently strips them, creating aliases) or starting with ' ';
- characters invalid on Windows (< > " | ? *) and control characters;
- segments longer than 255 characters or paths longer than MAX_RELATIVE (keeps vault + bundle root under MAX_PATH);
- duplicates that differ only by case (NTFS is case-insensitive): see case_collisions().
"""
from __future__ import annotations

import os
import re
import stat

MAX_RELATIVE = 200
MAX_SEGMENT = 255
_RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {f"COM{i}" for i in "0123456789¹²³"} | {f"LPT{i}" for i in "0123456789¹²³"}
_BAD_CHARS = re.compile(r'[<>"|?*\x00-\x1f]')
_SHORT_NAME = re.compile(r'~[0-9]')


def path_hazard(rel: str) -> str | None:
    """Return a reason string if rel is unsafe, else None."""
    if not rel:
        return "empty path"
    if len(rel) > MAX_RELATIVE:
        return f"path longer than {MAX_RELATIVE} characters"
    if rel.startswith(("/", "\\")) or rel.startswith("//"):
        return "absolute or UNC path"
    if "\\" in rel:
        return "backslash in path"
    if ":" in rel:
        return "':' (drive letter or NTFS alternate data stream)"
    if _BAD_CHARS.search(rel):
        return "character invalid on Windows"
    for seg in rel.split("/"):
        if seg in ("", ".", ".."):
            return "empty, '.' or '..' segment"
        if len(seg) > MAX_SEGMENT:
            return "segment longer than 255 characters"
        if seg.endswith((".", " ")) or seg.startswith(" "):
            return "segment with trailing dot/space or leading space"
        if seg.split(".", 1)[0].upper().rstrip(" ") in _RESERVED:
            return "reserved Windows device name"
        if _SHORT_NAME.search(seg):
            return "possible 8.3 short-name alias ('~' followed by a digit)"
    return None


def case_collisions(paths) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    out = []
    for p in paths:
        k = p.casefold()
        if k in seen and seen[k] != p:
            out.append((seen[k], p))
        seen.setdefault(k, p)
    return out


def is_link_or_reparse(path) -> bool:
    """Symlink, junction or any NTFS reparse point."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    attrs = getattr(st, "st_file_attributes", 0)
    if attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
        return True
    is_junction = getattr(os.path, "isjunction", None)
    return bool(is_junction and is_junction(path))
