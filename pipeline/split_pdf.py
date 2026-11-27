"""Stage 'split': cut an Act's PDF into section records, for Acts that have no section records
at the source (the repealed codes India Code keeps only as a PDF).

Works on consolidated texts in the Legislative Department layout: a table "ARRANGEMENT OF
SECTIONS" at the front, each section printed as a bold "115. Heading.—text", amendment footnotes
in smaller type at the foot of the page, footnote markers as superscripts.

Safety: the Act's own table of sections is the check. A section start is accepted only if its
number is the next one (or nearly the next) in that table, and nothing is written unless at least
MIN_COVERAGE of the table's sections were found. A file that does not fit the layout (e.g. a poor
scan) therefore produces a report line, not bad records.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from .amendments import parse_note
from .common import SCHEMA_VERSION, Paths, require_corpus_writes, write_json
from .records import _edge, section_key

MIN_COVERAGE = 0.98
LOOKAHEAD = 6                     # a section start may skip at most this many table entries
NUM = r"\d{1,3}[A-Z]{0,2}"
START = re.compile(rf"^(?:\[\d+\]\s*)*\[?\s*({NUM})\.\s*(?=\D)(.*)$", re.S)   # "174A.Non-appearance" too
TOC_ENTRY = re.compile(rf"^_?({NUM})[.,]\s*(.*)$")
CHAPTER = re.compile(r"^CHAPTER\s+([IVXLC]+\s?[A-Z]?)\b\.?[\s—–-]*(.*)$")
HEAD_END = re.compile(r"\.\s*[—–-]{1,2}")
GONE = re.compile(r"^\s*(?:\[[^\]]*\]\s*\.?\s*[—–-]*\s*)?(Rep\.|Repealed\b|Omitted\b)", re.I)
FOOT_WORDING = re.compile(r"^1\.\s+(Subs\.|Ins\.|Omitted|Rep\.|Added|The words?\b|The brackets|Cl(ause)?s?\.?\s|Sub-section|"
                          r"Section \d|Explanation \d? ?(omitted|ins)|Proviso|Certain words|Now |See |Vide )")
FOOT_START = re.compile(r"^(\d{1,3})\.\s+(.*)$", re.S)


@dataclass
class Line:
    page: int        # 1-based PDF page
    x: float
    y: float
    text: str
    foot: bool       # set in smaller (footnote) type
    bold_number: bool


def _page_body_size(page_dict: dict) -> float:
    """The page's body type size: the largest size that carries at least 5% of the page's characters
    (a page can be mostly footnotes). Judged per page, because some files mix pages set in different sizes."""
    count: Counter = Counter()
    for b in page_dict.get("blocks", []):
        for ln in b.get("lines", []):
            for s in ln["spans"]:
                if s["text"].strip():
                    count[round(s["size"] * 2) / 2] += len(s["text"])
    total = sum(count.values())
    big = [s for s, n in count.items() if n >= 0.05 * total]
    return max(big) if big else 0.0


def read_lines(pdf) -> tuple[list[Line], float]:
    out: list[Line] = []
    body = 0.0
    for pno, page in enumerate(pdf, 1):
        d = page.get_text("dict")
        body = _page_body_size(d)
        lines = []
        for b in d.get("blocks", []):
            for ln in b.get("lines", []):
                dx, dy = ln["dir"]
                if abs(dy) > 0.2 and abs(dx) > 0.2:              # diagonal watermark
                    continue
                parts, sizes, bold_number, seen = [], [], False, False
                for s in ln["spans"]:
                    t = s["text"]
                    if not t.strip():
                        parts.append(t)
                        continue
                    if t.strip().isdigit() and ((s["flags"] & 1) or s["size"] <= body - 2.5):
                        parts.append(f"[{t.strip()}]")           # superscript footnote marker
                        continue
                    sizes.append(s["size"])
                    if not seen and (s["flags"] & 16) and re.match(rf"^\[?\s*{NUM}\.", t.lstrip()):
                        bold_number = True
                    if re.search(r"[A-Za-z0-9]", t):             # an opening bracket alone does not count
                        seen = True
                    parts.append(t)
                text = re.sub(r"[ \t\u00a0]+", " ", "".join(parts)).strip()
                if not text:
                    continue
                small = bool(sizes) and max(sizes) <= body - 0.9  # small caps start with a full-size capital
                lines.append(Line(pno, ln["bbox"][0], ln["bbox"][1], text, small, bold_number))
        lines.sort(key=lambda l: (round(l.y), l.x))
        # Pieces on the same printed row (a superscript, or text the PDF stores separately) are joined
        # left to right. Rows are at least 9 pt apart, so 4 pt is safe.
        rows: list[list[Line]] = []
        for l in lines:
            if rows and abs(l.y - rows[-1][0].y) <= 4 and l.foot == rows[-1][0].foot:
                rows[-1].append(l)
            else:
                rows.append([l])
        lines = []
        for row in rows:
            row.sort(key=lambda l: l.x)
            text = re.sub(r"\s+", " ", " ".join(l.text for l in row)).replace("] [", "][").strip()
            first = next((l for l in row if re.search(r"[A-Za-z0-9]", re.sub(r"\[\d+\]", "", l.text))), row[0])
            lines.append(Line(row[0].page, row[0].x, min(l.y for l in row), text, row[0].foot, first.bold_number))
        # Footnotes are the small-type block at the foot of the page that starts with note "1.".
        # Small type above that block is body text (illustrations, a table, a heading in small caps).
        starts = [i for i, l in enumerate(lines) if l.foot and re.match(r"^1\.\s", l.text)]
        if starts:
            zone = starts[-1]
            for i, l in enumerate(lines):
                l.foot = l.foot and i >= zone
        else:
            # Some pages set their footnotes in the body size. Then the block is recognised by wording:
            # a line in the lower half that starts note 1 the way amendment notes do.
            alike = [i for i, l in enumerate(lines)
                     if l.y > page.rect.height * 0.5 and FOOT_WORDING.match(l.text)]
            zone = alike[-1] if alike else len(lines)
            for i, l in enumerate(lines):
                l.foot = i >= zone and not l.text.isdigit()
        out += lines
    return out, body


def parse_toc(lines: list[Line]) -> list[tuple[str, str]]:
    """[(number, heading)] from the arrangement of sections."""
    toc: list[tuple[str, str]] = []
    seen = set()
    for i, ln in enumerate(lines):
        m = TOC_ENTRY.match(ln.text)
        if not m:
            continue
        num, head = m.group(1), m.group(2).strip()
        if not head and i + 1 < len(lines) and not TOC_ENTRY.match(lines[i + 1].text):
            head = lines[i + 1].text.strip()
        if num not in seen:
            seen.add(num)
            toc.append((num, head))
    return toc


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def split_pdf(pdf_path: Path, parent: str, act_repeal_note: str | None = None) -> tuple[list[dict], dict]:
    with pymupdf.open(pdf_path) as pdf:
        lines, _ = read_lines(pdf)
    stats: dict = {"toc_sections": 0, "found": 0, "missing": [], "heading_mismatches": [], "written": False,
                   "amendment_notes": 0, "reason": None}
    start = next((i for i, l in enumerate(lines) if re.match(r"^ACT NO\.?\s*\d+\s+OF\s+\d{4}", l.text, re.I)), None)
    if start is None:
        stats["reason"] = "no 'ACT NO. .. OF ....' line: cannot tell the table of sections from the body"
        return [], stats
    toc = parse_toc(lines[:start])
    stats["toc_sections"] = len(toc)
    if len(toc) < 5:
        stats["reason"] = "no table of sections found before the body"
        return [], stats
    order = [n for n, _ in toc]
    toc_head = dict(toc)

    # Footnotes: per page, {marker number: text}
    notes: dict[int, dict[str, str]] = {}
    current = None
    for ln in lines[start:]:
        if not ln.foot:
            continue
        m = FOOT_START.match(ln.text)
        if m:
            current = (ln.page, m.group(1))
            notes.setdefault(ln.page, {})[m.group(1)] = m.group(2).strip()
        elif current and current[0] == ln.page:
            notes[ln.page][current[1]] += " " + ln.text.strip()

    body = [l for l in lines[start:] if not l.foot and not l.text.isdigit()]
    left = Counter(round(l.x) for l in body).most_common(1)[0][0] if body else 0
    sections: list[dict] = []
    ptr, cur, chapter, pending_chapter = 0, None, None, False

    def close(sec):
        if sec is None:
            return
        paras: list[str] = []
        for l in sec.pop("_lines"):
            if paras and l.x <= left + 6:
                paras[-1] += " " + l.text
            else:
                paras.append(l.text)
        full = "\n".join(paras)
        m = START.match(full) or re.match(rf"^(?:\[\d+\]\s*)*\[?\s*({NUM})\s+(.*)$", full, re.S)
        rest = m.group(2) if m else full
        h = HEAD_END.search(rest[:400])
        br = re.match(r"^\s*(\[[^\]]{2,300}\])\s*\.?\s*[—–-]*\s*(.*)$", rest, re.S)
        if br and (not h or h.start() > br.end(1) + 3):       # "[Old heading.] Rep. by ..."
            heading, text = br.group(1).rstrip("."), br.group(2).strip()
            heading = heading[:-1].rstrip(".") + "]" if heading.endswith(".]") else heading
        else:
            heading = rest[:h.start()].strip() if h else None
            text = rest[h.end():].strip() if h else rest.strip()
        sec["heading"] = (heading if heading.endswith("]") else heading + ".") if heading else None
        sec["text"] = text or None
        history, plain = [], []
        for page, marker in sec.pop("_markers"):
            note = notes.get(page, {}).get(marker)
            if note is None:
                continue
            entry = parse_note(note, "footnote")
            (history if entry else plain).append(entry or note)
        gone = GONE.match(text or "")
        if gone:
            entry = parse_note(text, "inline")
            if entry:
                entry["footnote_text"] = re.sub(r"\s*\n\s*", " ", text)[:1000]
                history.append(entry)
        if gone:
            sec["status"] = "omitted" if gone.group(1).lower().startswith("omit") else "repealed"
            sec["status_note"] = re.sub(r"\s*\n\s*", " ", text)[:300]
        else:
            sec["status"] = "repealed" if act_repeal_note else ("amended" if history else "in_force")
            sec["status_note"] = act_repeal_note or (f"{len(history)} amendment note(s) on this section" if history else None)
        sec["amendment_history"], sec["notes"] = history, plain
        stats["amendment_notes"] += len(history)
        want = toc_head.get(sec["number"], "")
        if heading and want and _norm(heading)[:25] != _norm(want)[:25] and not want.startswith("["):
            stats["heading_mismatches"].append(f"{sec['number']}: body {heading[:50]!r} vs table {want[:50]!r}")
        sections.append(sec)

    for ln in body:
        ch = CHAPTER.match(ln.text)
        if ch:
            chapter = {"number": ch.group(1).strip(), "title": ch.group(2).strip() or None}
            pending_chapter = chapter["title"] is None
            continue
        if pending_chapter and ln.text.isupper() and not START.match(ln.text):
            chapter = {**chapter, "title": ln.text.strip()}
            pending_chapter = False
            continue
        pending_chapter = False
        m = START.match(ln.text)
        if not m and ptr < len(order):
            # A source typo drops the full stop: '17 "Government".—'. Only for exactly the next section.
            m2 = re.match(rf"^(?:\[\d+\]\s*)*\[?\s*({NUM})\s+([“\"].*)$", ln.text, re.S)
            if m2 and m2.group(1) == order[ptr] and HEAD_END.search(m2.group(2)[:200]):
                m = m2
                ln = Line(ln.page, ln.x, ln.y, ln.text, ln.foot, True)
                stats.setdefault("source_typos", []).append(f"section {m2.group(1)} is printed without its full stop")
        if m and not ln.bold_number:
            # Repealed sections are often not bold: "15. [Definition of "British India".] Rep. by ...".
            # Accepted only as exactly the next section in the table, with a bracketed heading.
            # A normal section printed without bold is accepted on the same condition, if it has a heading
            # ending ".—" like every other section.
            nxt = ptr < len(order) and m.group(1) == order[ptr]
            if not (nxt and (m.group(2).lstrip().startswith("[") or HEAD_END.search(m.group(2)[:200]))):
                m = None
        if m and m.group(1) in order[ptr:ptr + LOOKAHEAD]:
            close(cur)
            j = order.index(m.group(1), ptr)
            stats["missing"] += order[ptr:j]
            ptr = j + 1
            cur = {"schema_version": SCHEMA_VERSION, "section_id": f"{parent}#{section_key(m.group(1))}",
                   "parent_doc_id": parent, "unit": "section", "number": m.group(1), "chapter": chapter,
                   "order": len(sections) + 1, "page_start": ln.page, "page_end": ln.page,
                   "source_record": None,
                   "field_provenance": {"text": "rule", "heading": "rule", "chapter": "rule", "status": "rule",
                                        "amendment_history": "rule"},
                   "_lines": [], "_markers": []}
        if cur is not None:
            cur["_lines"].append(ln)
            cur["page_end"] = ln.page
            cur["_markers"] += [(ln.page, n) for n in re.findall(r"\[(\d+)\]", ln.text)]
    close(cur)
    stats["missing"] += order[ptr:]
    stats["found"] = len(sections)
    coverage = len(sections) / len(order)
    stats["coverage"] = round(coverage, 4)
    if coverage < MIN_COVERAGE:
        stats["reason"] = (f"only {len(sections)} of {len(order)} sections in the Act's table were found "
                           f"({coverage:.0%}); below the {MIN_COVERAGE:.0%} needed, nothing written")
        return [], stats
    return sections, stats


def run(paths: Paths, only: list[str] | None = None) -> dict:
    """Split every Act that has a text layer and no section records from its source."""
    require_corpus_writes("split")
    results: dict = {}
    rel_path = paths.data / "relations.jsonl"
    rels = [json.loads(l) for l in rel_path.read_text(encoding="utf-8").splitlines() if l.strip()] \
        if rel_path.exists() else []
    metas = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(paths.meta.glob("*.json"))}
    provided = {m["provides_sections_for"]: m for m in metas.values() if m.get("provides_sections_for")}
    for doc_id, meta in metas.items():
        src = meta.get("source_record") or {}
        if (meta["doc_type"] != "act" or meta.get("parent_doc_id") or src.get("listing_raw_path")
                or meta.get("mime_type") != "application/pdf" or (only and doc_id not in only)):
            continue
        text_doc = provided.get(doc_id, meta)          # a better copy of the same Act, if one was added
        note = meta["status_note"] if meta["status"] == "repealed" else None
        sections, stats = split_pdf(paths.raw_file(text_doc["raw_path"]), doc_id,
                                    f"The Act is repealed. {note}" if note else None)
        stats["text_from"] = text_doc["doc_id"]
        results[doc_id] = stats
        out_dir = paths.sections / doc_id
        if out_dir.exists():
            for old in out_dir.glob("*.json"):
                old.unlink()
        rels = [r for r in rels if not r["source_doc_id"].startswith(doc_id + "#")]
        used: Counter = Counter()
        for s in sections:
            key = s["section_id"].split("#")[1]
            used[key] += 1
            if used[key] > 1:
                key = f"{key}-dup{used[key]}"
                s["section_id"] = f"{doc_id}#{key}"
            if text_doc is not meta:
                s["text_source_doc_id"] = text_doc["doc_id"]
            write_json(out_dir / f"{key}.json", s)
            for h in s["amendment_history"]:
                rels.append(_edge(s["section_id"], "amended_by", None, h["by_ref_raw"] or h["footnote_text"][:200],
                                  h["footnote_text"], h["effective_date"]))
        stats["written"] = bool(sections)
    with rel_path.open("w", encoding="utf-8") as fh:
        for r in rels:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return results
