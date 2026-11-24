"""Scan every held PDF for JUDIS typed-text renditions and JUDIS-path court-layout files (offline; read-only on inputs).

usage: python -I judis_scan.py <scratchpad_root> <audit_work_dir> <out_csv> [--check]
Inputs: <audit_work>/SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv (held paths, re-hashed here),
        <audit_work>/SOURCE-LIBRARY-C5/registers/source_copy_register.csv (copy id, C5 status, eligibility),
        <audit_work>/WS-B-JUDGMENTS/tools/held_copies.csv (recorded official URL).
A row is written for every held PDF whose producer is Ghostscript, whose page 1 carries 'JUDIS.NIC.IN', or whose recorded
official URL has a /judis/ path. Only structural facts are recorded (counts, page numbers, flags); no page text."""
import csv, hashlib, re, sys
from pathlib import Path
import pymupdf

COLS = ["sha256", "copy_id", "held_path", "rehash", "recorded_official_url", "producer", "pdf_format", "pages", "image_count",
        "p1_judis_header", "page_x_of_n_complete", "judis_watermark_text", "database_fields_p1", "headnote_label", "judgment_label_page",
        "inline_report_pages", "inline_report_continuous", "reporter_end_tag", "signature_or_date_block_last_page",
        "escape_literals", "c5_copy_effective_status", "c5_eligible_for_exact_anchor", "profile"]
FIELDS = ("PETITIONER:", "RESPONDENT:", "DATE OF JUDGMENT", "BENCH:", "CITATION:", "CITATOR INFO", "ACT:", "HEADNOTE:", "CASE NO.:")


def producer(d):
    """Producer string; a UTF-16BE value mis-decoded as CJK characters is re-decoded (Dharamvir/Anvar files)."""
    p = d.metadata.get("producer", "") or ""
    if p and sum(ord(ch) > 0x2E80 for ch in p) > len(p) // 2:
        try:
            return p.encode("utf-16-be").decode("latin-1") + " [re-decoded from UTF-16BE]"
        except UnicodeError:
            return p
    return p


def scan(path):
    d = pymupdf.open(path)
    pages = [p.get_text().replace("\xa0", " ") for p in d]
    p1 = pages[0]
    judis = "JUDIS.NIC.IN" in p1
    hdr = [bool(re.search(rf"Page {i + 1} of {len(pages)}\b", t)) for i, t in enumerate(pages)]
    jpage = next((i + 1 for i, t in enumerate(pages) if re.search(r"^JUDGMENT:", t, re.M)), "")
    nums = []
    for i, t in enumerate(pages if judis else [], 1):  # printed-report page numbers exist only in the database renditions
        nums += [(i, int(l.strip())) for l in t.splitlines() if re.fullmatch(r"\s*\d{2,4}\s*", l)]
    seq = [n for _, n in nums]
    cont = bool(seq) and all(b == a + 1 for a, b in zip(seq, seq[1:]))
    last = pages[-1]
    sig = bool(re.search(r"[.\u2026]{5,}\s*J\.|NEW DELHI|New Delhi", last))
    esc = dict(sorted({k: len(re.findall(re.escape(k), "".join(pages))) for k in ("\\005", "\\026", "\\027")}.items()))
    imgs = sum(len(p.get_images()) for p in d)
    return {"producer": producer(d), "pdf_format": d.metadata.get("format", ""), "pages": len(pages), "image_count": imgs,
            "p1_judis_header": "YES" if "JUDIS.NIC.IN" in p1 else "NO",
            "page_x_of_n_complete": "YES" if all(hdr) else ("PARTIAL" if any(hdr) else "NO"),
            "judis_watermark_text": "n/a (vector outline; see renders)",
            "database_fields_p1": ";".join(f.rstrip(":. ") for f in FIELDS if f in p1),
            "headnote_label": "YES" if "HEADNOTE:" in "".join(pages[:8]) else "NO", "judgment_label_page": jpage,
            "inline_report_pages": f"{seq[0]}-{seq[-1]} (p{nums[0][0]}-p{nums[-1][0]})" if seq else "",
            "inline_report_continuous": ("YES" if cont else "NO") if seq else "",
            "reporter_end_tag": "YES" if re.search(r"\b[A-Z]\.[A-Z]\.[A-Z]\.\s+(Appeal|Petition)", last) else "NO",
            "signature_or_date_block_last_page": "YES" if sig else "NO",
            "escape_literals": "; ".join(f"{k} x{v}" for k, v in esc.items() if v) or "none"}


def main():
    argv = [a for a in sys.argv[1:] if a != "--check"]
    root, aw, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    rd = lambda p: list(csv.DictReader(open(aw / p, newline="", encoding="utf-8")))
    held = {}
    for r in rd("SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv"):
        if r["held_path"].lower().endswith(".pdf"):
            held.setdefault(r["rehashed_sha256"], []).append(r["held_path"])
    cp = {r["sha256"]: r for r in rd("SOURCE-LIBRARY-C5/registers/source_copy_register.csv")}
    urls = {}
    for r in rd("WS-B-JUDGMENTS/tools/held_copies.csv"):
        urls.setdefault(r["sha256"], r["official_url"])
    rows = []
    for sha in sorted(held):
        hp = sorted(held[sha])[0]
        data = (root / hp).read_bytes()
        rh = "MATCH" if hashlib.sha256(data).hexdigest() == sha else "MISMATCH"
        try:
            d = pymupdf.open(root / hp)
            prod, p1 = d.metadata.get("producer", "") or "", d[0].get_text() if d.page_count else ""
        except Exception:
            continue
        url = urls.get(sha, "")
        if not ("Ghostscript" in prod or "JUDIS.NIC.IN" in p1 or "/judis/" in url):
            continue
        f = scan(root / hp)
        c = cp.get(sha, {})
        prof = ("JUDIS_TYPED_TEXT_DATABASE_RENDITION" if f["p1_judis_header"] == "YES" and "Ghostscript" in f["producer"]
                else "JUDIS_PATH_COURT_LAYOUT_PDF" if "/judis/" in url else "OTHER")
        rows.append({"sha256": sha, "copy_id": c.get("copy_id", ""), "held_path": hp, "rehash": rh, "recorded_official_url": url, **f,
                     "c5_copy_effective_status": c.get("copy_effective_status", ""), "c5_eligible_for_exact_anchor": c.get("eligible_for_exact_anchor", ""),
                     "profile": prof})
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    text = buf.getvalue()
    if "--check" in sys.argv[1:]:
        ok = out.is_file() and out.read_text(encoding="utf-8") == text
        print("CHECK", "OK" if ok else "DIFFERS")
        sys.exit(0 if ok else 1)
    out.write_text(text, encoding="utf-8")
    print(f"{len(rows)} rows; profiles: " + ", ".join(f"{p}={sum(r['profile'] == p for r in rows)}" for p in sorted({r['profile'] for r in rows})))


if __name__ == "__main__":
    main()
