"""Check WS-B pinpoints into the four JUDIS typed-text renditions against the renditions' own inline report pagination
(offline; read-only). No page text is emitted.

usage: python -I scr_pinpoint_check.py <scratchpad_root> <audit_work_dir> <out_csv> [--check]
For each WS-B holdings / treatment row whose copy sha256 is a JUDIS rendition:
  * the PDF page range stated (pdf_page) is compared with the PDF pages on which the cited printed-report (SCR) pages fall,
    using the bare-number page markers in the text layer (marker N on PDF page P = report page N begins on P);
  * a pinpoint whose PDF page precedes the 'JUDGMENT:' label page is flagged as database/headnote matter."""
import csv, io, re, sys
from pathlib import Path
import pymupdf

JUDIS = {"211dbaf4e20371cc476d09c158e41b976786d57f67336ff6fc802170178b3cca": "PPS_BEDI",
         "ed7cf31fd8fbe50822e0a60f80b96ed1187dcd465dc4ae2649424c58001ff399": "RANJIT",
         "eb4420801e978469e9c7407f8c079273f9cd483ad45a4427daa53e3d229969cc": "SN_MUKHERJEE",
         "3b75354869ffb928f73532f475f5f920e2f2a1f8817163caba2f7fb5e1eb215d": "NAVJOT"}
REGS = [("WS-B-JUDGMENTS/holdings_register.csv", "copy_sha256"), ("WS-B-JUDGMENTS/holdings_register_cycle3.csv", "copy_sha256"),
        ("WS-B-JUDGMENTS/subsequent_treatment.csv", "later_copy_sha256"), ("WS-B-JUDGMENTS/subsequent_treatment_cycle3.csv", "later_copy_sha256")]
COLS = ["register_row", "copy", "sha256_8", "pdf_page_stated", "para_pinpoint_stated", "report_pages_cited", "pdf_pages_holding_cited_report_pages",
        "judgment_label_page", "in_headnote_zone", "result"]


def rng(s):
    m = re.findall(r"\d+", s or "")
    return (int(m[0]), int(m[-1])) if m else None


def main():
    argv = [a for a in sys.argv[1:] if a != "--check"]
    root, aw, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    held = {}
    for r in csv.DictReader(open(aw / "SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv", encoding="utf-8")):
        held.setdefault(r["rehashed_sha256"], r["held_path"])
    maps = {}
    for sha in JUDIS:
        d = pymupdf.open(root / held[sha])
        starts, jp = {}, None
        for i, p in enumerate(d, 1):
            t = p.get_text()
            if jp is None and re.search(r"^JUDGMENT:", t, re.M):
                jp = i
            for l in t.splitlines():
                if re.fullmatch(r"\s*\d{2,4}\s*", l):
                    starts.setdefault(int(l), i)
        maps[sha] = (starts, jp, d.page_count)
    rows = []
    for reg, col in REGS:
        for r in csv.DictReader(open(aw / reg, encoding="utf-8")):
            sha = (r.get(col) or "").strip()
            if sha not in JUDIS:
                continue
            starts, jp, n = maps[sha]
            pr = rng(r.get("pdf_page"))
            m = re.search(r"SCR\s*pp?\.?\s*([\d\-–]+)", r.get("para_pinpoint", ""))
            cited = rng(m.group(1)) if m else None
            span, res = "", "NO_REPORT_PAGE_CITED"
            if cited and cited[0] in starts:
                lo = starts[cited[0]]
                nxt = starts.get(cited[1] + 1, n)
                hi = max(lo, nxt)
                span = f"{lo}-{hi}"
                if pr:
                    res = "CONSISTENT" if pr[0] <= hi and pr[1] >= lo else "INCONSISTENT"
                else:
                    res = "NO_PDF_PAGE_STATED"
            elif cited:
                res = "CITED_REPORT_PAGE_NOT_IN_RENDITION"
            head = "YES" if pr and jp and pr[0] < jp else ("NO" if pr else "")
            rows.append({"register_row": f"{reg.split('/')[-1]}#{r['row_id']}", "copy": JUDIS[sha], "sha256_8": sha[:8],
                         "pdf_page_stated": r.get("pdf_page", ""), "para_pinpoint_stated": r.get("para_pinpoint", "") or r.get("para", ""),
                         "report_pages_cited": f"{cited[0]}-{cited[1]}" if cited else "", "pdf_pages_holding_cited_report_pages": span,
                         "judgment_label_page": jp or "", "in_headnote_zone": head, "result": res})
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
    print(text)


if __name__ == "__main__":
    main()
