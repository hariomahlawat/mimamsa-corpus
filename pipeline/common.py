"""Shared helpers for the processing pipeline."""
from __future__ import annotations

import html
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SCHEMA_VERSION = "0.2.0"
ROOT = Path(__file__).resolve().parent.parent


def require_corpus_writes(stage: str) -> None:
    """Enforce the C14 hold at legacy write entry points."""
    raise RuntimeError(f"C14 corpus mutation hold: legacy {stage} writer is suspended")


@dataclass
class Paths:
    """Where a pipeline run reads and writes. `data` holds raw/ (input) and the outputs."""
    root: Path
    db: Path
    data: Path

    @classmethod
    def default(cls, root: Path | str = ROOT) -> "Paths":
        root = Path(root)
        return cls(root=root, db=root / "state" / "crawl.sqlite", data=root / "data")

    @property
    def meta(self) -> Path:
        return self.data / "meta"

    @property
    def sections(self) -> Path:
        return self.data / "sections"

    @property
    def text(self) -> Path:
        return self.data / "text"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    def raw_file(self, raw_path: str) -> Path:
        """raw_path is stored as 'data/raw/...'; resolve it under this run's data folder."""
        return self.data.parent / raw_path


def connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{db.absolute().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slug(s: str, max_len: int = 70) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:max_len].strip("-") or "untitled"


def html_to_text(h: str | None) -> str:
    """Plain text from the site's HTML fragments. Footnote markers <sup>1</sup> become [1]."""
    if not h:
        return ""
    h = re.sub(r"<sup>\s*([^<]{1,6}?)\s*</sup>", r"[\1]", h, flags=re.I)
    h = re.sub(r"<(br|hr)\b[^>]*>", "\n", h, flags=re.I)
    h = re.sub(r"</(p|div|center|tr|li|h[1-6])\s*>", "\n", h, flags=re.I)
    h = html.unescape(re.sub(r"<[^>]+>", "", h))
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in h.split("\n")]
    out: list[str] = []
    for ln in lines:
        if ln or (out and out[-1]):
            out.append(ln)
    return "\n".join(out).strip()


def iso_date(value: str | None) -> str | None:
    """A full calendar date as YYYY-MM-DD, or None. Accepts YYYY-MM-DD and DD-MM-YYYY (also / and .).
    Anything else (a bare year, a typo) is None: dates are never guessed."""
    if not value:
        return None
    v = value.strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", v)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", v)
        if not m:
            return None
        d, mo, y = map(int, m.groups())
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None
