"""Read amendment notes ('Subs. by Act 19 of 1955, s. 2 ...', 'Omitted by ... (w.e.f. 6-9-1992)').

Rule-based only. A note that does not say who changed the text is not an amendment entry.
"""
from __future__ import annotations

import re

from .common import iso_date

_WORDS = r"subs|substituted|ins|inserted|omitted|added|rep|repealed|renumbered|re-numbered|amended"
# "Subs. by Act 19 of 1955 ...", "Section 52 renumbered as sub-section (1) thereof by s. 12, ibid."
_ACTION = re.compile(rf"\b({_WORDS})\b\.?(?:[^.;\n]{{0,60}}?)\s+by\s+(?P<by>.+)", re.I | re.S)
# "Subs. ibid., for clause (h).", "The words ... omitted, ibid."  (same instrument as the note before)
_IBID = re.compile(rf"\b({_WORDS})\b\.?\s*,?\s+(?P<by>ibid\.?)", re.I)
# The source sometimes drops the "by": "Ins. s. 6, ibid.", "Subs. Act, 48 of 1982, s. 5, for ...".
# Only accepted at the very start of a note.
_NO_BY = re.compile(rf"^\s*({_WORDS})\.?\s+(?P<by>(?:s\.\s*\d|Act\b).+)", re.I | re.S)
_SECTION_ONLY = re.compile(r"^s(?:ec|s)?\.\s*\d", re.I)
_ACTION_MAP = {"subs": "substituted", "substituted": "substituted", "ins": "inserted", "inserted": "inserted",
               "added": "inserted", "omitted": "omitted", "rep": "repealed", "repealed": "repealed",
               "renumbered": "renumbered", "re-numbered": "renumbered", "amended": "amended"}
_BY_END = re.compile(r",\s*s(?:ec|s)?\.|,\s*sections?\b|\s*\(w\.\s*e\.\s*f|,\s*for\b|,\s*ibid|\s+for\s+[\"“]|;|\n", re.I)
_WEF = re.compile(r"w\.\s*e\.\s*f\.?\s*([0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{1,4})", re.I)
_MARKER = re.compile(r"(?:^|\n)\s*\[(\d{1,3})\]\s*\.?\s*")


def split_footnotes(text: str) -> list[str]:
    """'[1]. first note [2]. second' -> ['first note', 'second']. Text before the first marker is kept."""
    parts = _MARKER.split(text or "")
    notes = [parts[0].strip()] if parts and parts[0].strip() else []
    notes += [parts[i + 1].strip() for i in range(1, len(parts) - 1, 2) if parts[i + 1].strip()]
    return [re.sub(r"\s*\n\s*", " ", n) for n in notes]


def parse_note(note: str, origin: str) -> dict | None:
    """One amendment_history entry, or None if the note is not an amendment."""
    m = _ACTION.search(note) or _NO_BY.match(note)
    if m:
        by = m.group("by")
        if _SECTION_ONLY.match(by):
            # "by s. 7, ibid. (w.e.f. ...)": the instrument is named only as "ibid."; keep the phrase whole.
            end = re.search(r"\s*\(w\.\s*e\.\s*f|,\s*for\b|;|\n", by, re.I)
            by = (by[:end.start()] if end else by).strip()
        else:
            end = _BY_END.search(by)
            by = (by[:end.start()] if end else by).strip().rstrip(".").strip()
            by = re.sub(r"^the\s+", "", by, flags=re.I)
    else:
        m = _IBID.search(note)
        if not m:
            return None
        by = "ibid."
    wef = _WEF.search(note)
    wef_raw = wef.group(1) if wef else None
    wef_iso = iso_date(wef_raw)
    return {
        "action": _ACTION_MAP[m.group(1).lower()],
        "by_ref_raw": by or None,
        "by_doc_id": None,
        "effective_date": wef_iso,
        "effective_date_raw": wef_raw if (wef_raw and not wef_iso) else None,
        "footnote_text": note,
        "confidence": "extracted",
        "origin": origin,
    }
