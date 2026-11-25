#!/usr/bin/env python3
"""C13-A5 deliverable 4: reconfirm the 99 staged Supreme Court case-number corrections against the PDF bytes.

For each of the 99 records staged in C12 `SC_CASE_NUMBER_OVERLAY_C12.jsonl`:
  1. read the source PDF bytes as a git object at ad77758d of --repo, re-hash, and require sha256 == staged sha256;
  2. extract the cover pages' text layer with PyMuPDF directly from those bytes (independent of the pipeline
     text file and of the C11 parser);
  3. parse (number, year) pairs from that text (lists, ranges "22 to 26" / "4415-16", "of 1959", "831/93",
     Diary numbers) and require every staged (number, year) to be printed, and a case-type label of each
     staged type family to be printed;
  4. where (3) fails, a recorded page-image reading (`scnum/PAGE_IMAGE_CHECKS_C13.csv`, made by this agent
     from rendered page images) may confirm the value. That reading is an AI visual check, not a legal check.
Only RECONFIRMED records enter the controlled overlay `SC_CASE_NUMBER_OVERLAY_C13.jsonl` (metadata only; no
evidence or authentication status is promoted; `data/meta` is never rewritten). The 266 unreviewed candidates
and the 3 unresolved records are never read or applied by this tool.

  python -I -B scnum_reconfirm_c13.py [--repo /home/user/c7] [--check]
Requires PyMuPDF (fitz); version is recorded in the summary.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_c13 as C  # noqa: E402
import provenance_pin_c13  # noqa: E402

provenance_pin_c13.apply()   # deterministic register provenance (post-freeze fix, review A5-01b)

OVERLAY_C12 = C.AUDIT / "C12-CONSOLIDATION" / "metadata" / "SC_CASE_NUMBER_OVERLAY_C12.jsonl"
OVERLAY_C12_SHA = "fd849f20210d323b44ae299a1c3b0a064e30e8b294b6bdae2383c20f3f162e89"  # C12 staged overlay, pinned
OUT = C.PKG / "scnum"
VERSION = "scnum-reconfirm-c13/1.0.0"
COVER_PAGES = 3          # cover pages always read; jurisdiction blocks anywhere in the file are read too
HEADING_RE = re.compile(r"(?:APPELLATE|ORIGINAL|ADVISORY|EXTRAORDINARY)\s*J\s*[UV]\s*R\s*[IlT1]\s*S\s*D\s*[IlT1]\s*C\s*T\s*[IlT1]\s*[O0]\s*[NX]|JURISDICTION\s*:|IN THE SUPREME COURT OF INDIA|REPORTABLE", re.I)

# Type family -> label regex expected somewhere in the cover text.
TYPE_LABELS = {
    "CA": r"civil\s*appeal|c\.\s*a\.|\bappeals?\b",
    "CRLA": r"criminal\s*appeal|crl\.?\s*a|cr\.\s*a\.|\bappeals?\b",
    "WPC": r"writ\s*petition|w\.\s*p\.",
    "WPCRL": r"writ\s*petition|w\.\s*p\.",
    "WP": r"writ\s*petition|w\.\s*p\.|petition",
    "PET": r"petition",
    "SLPC": r"special\s*leave|s\.\s*l\.\s*p|\bslp",
    "SLPCRL": r"special\s*leave|s\.\s*l\.\s*p|\bslp",
    "TPC": r"transfer(red)?\s*petition|t\.\s*p\.",
    "TPCRL": r"transfer(red)?\s*petition|t\.\s*p\.",
    "TCC": r"transfer(red)?\s*case|t\.\s*c\.",
    "TC": r"transfer(red)?\s*case|t\.\s*c\.",
    "TCCRL": r"transfer(red)?\s*case|t\.\s*c\.",
    "CONTC": r"contempt",
    "CONT": r"contempt",
    "RP": r"review\s*petition|r\.\s*p\.",
    "IA": r"interlocutory|i\.\s*a\.",
    "MA": r"miscellaneous\s*application|m\.\s*a\.",
    "CMP": r"civil\s*misc|c\.\s*m\.\s*p",
    "CRLMP": r"criminal\s*misc|crl\.\s*m\.\s*p",
}
VAL = re.compile(r"^([A-Z]+?)(DIARY)?-(\d+)([A-Z]?)-(\d{4})$")
YEAR_RE = re.compile(r"(?:(?:\b|(?<=\d))of\s*|/\s*)((?:19|20)\d\d|\d\d)\b", re.I)
NUM_RE = re.compile(r"(\d{1,6})\s*([A-Z])?\s*(?:(?:-|–|—|to|TO)\s*(\d{1,6}))?(?!\d)")


# Digital SCR running header, which can interrupt a long connected-matter list across a page break.
SCR_HEADER = re.compile(r"\b\d{1,4}\s*\[\d{4}\]\s*\d{1,2}\s*S\.C\.R\.\s*(?:Digital Supreme Court Reports)?")


def norm_text(t: str) -> str:
    """Whitespace collapse plus OCR digit repair next to digits only (I, l, ! -> 1; O, o -> 0)."""
    t = t.replace("\u00a0", " ").replace("\u2019", "'")
    t = re.sub(r"[\x00-\x08\x0b-\x1f]", " ", t)
    t = re.sub(r"\s+", " ", t)
    for _ in range(2):
        t = re.sub(r"(?<=\d)[Il!](?=\d)|\b[Il!](?=9\d\d\b)", "1", t)
        t = re.sub(r"(?<=\d)[Oo](?=\d)", "0", t)
    return t


def list_start(t: str, end: int, floor: int) -> int:
    """Start of the pure number list ("9052, 9170, 9048 ... 8897") that ends at `end` (long connected-matter lists)."""
    i = end
    while i > floor:
        c = t[i - 1]
        if c.isdigit() or c in " ,&-\u2013":
            i -= 1
        elif t[max(floor, i - 3):i] == "and":
            i -= 3
        elif c.isupper() and i - 1 > floor and t[i - 2].isdigit():   # suffix letter, e.g. 1692A
            i -= 1
        else:
            break
    return i


def pairs_from_text(t: str):
    """Set of (number_with_suffix, four_digit_year_or_2digit) printed in t, plus the segments used."""
    found = set()
    prev_end = 0
    for m in YEAR_RE.finditer(t):
        y = m.group(1)
        seg_lo = max(prev_end, min(m.start() - 400, list_start(t, m.start(), prev_end)))
        seg = t[seg_lo:m.start()]
        prev_end = m.end()
        # do not let a segment run back across an earlier year expression
        for nm in NUM_RE.finditer(seg):
            a, suf, b = nm.group(1), nm.group(2) or "", nm.group(3)
            nums = [a]
            if b:
                ia, ib = int(a), int(b)
                if len(b) < len(a):  # 4415-16 -> 4416
                    ib = int(a[: len(a) - len(b)] + b)
                if 0 < ib - ia <= 400:
                    nums = [str(i) for i in range(ia, ib + 1)]
            for n in nums:
                found.add((n.lstrip("0") or "0", suf if n == a else "", y))
                found.add((n.lstrip("0") or "0", "", y))
    return found


def year_ok(printed: str, staged: str) -> bool:
    return printed == staged or (len(printed) == 2 and staged.endswith(printed))


def cover_text(pdf_bytes: bytes, fitz, n_values: int):
    """Return the text windows that can carry the case-number block: the first COVER_PAGES pages, plus a window
    after every jurisdiction heading anywhere in the file (SCR extracts often start inside a previous report)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = [SCR_HEADER.sub(" ", norm_text(doc.load_page(i).get_text("text"))) for i in range(doc.page_count)]
    n = doc.page_count
    doc.close()
    windows = [(i + 1, pages[i]) for i in range(min(COVER_PAGES, n))]
    span = max(6000, 70 * n_values)
    for i, p in enumerate(pages):
        for m in HEADING_RE.finditer(p):
            tail = p[m.start():]
            j = i + 1
            while len(tail) < span and j < n:
                tail += " " + pages[j]
                j += 1
            windows.append((i + 1, tail[:span]))
    return windows, n, sum(len(p.strip()) for p in pages[:COVER_PAGES])


def check_record(rec, pdf_bytes, fitz):
    windows, npages, chars = cover_text(pdf_bytes, fitz, len(rec["proposed_value"]))
    pages = [w for _, w in windows]
    if chars < 200:
        return dict(text_layer="NO_OR_THIN_TEXT_LAYER", missing=rec["proposed_value"], type_missing=[], page="",
                    excerpt="", npages=npages)
    found = set()
    first_page = None
    for p in pages:
        found |= pairs_from_text(p)
    full = " ".join(pages)
    missing, hit_pages = [], set()
    for v in rec["proposed_value"]:
        m = VAL.match(v)
        if not m:
            missing.append(v)
            continue
        num, suf, yr = m.group(3), m.group(4), m.group(5)
        num_year = any(n == num and year_ok(y, yr) for (n, s, y) in found)
        if not suf:
            ok = num_year
        else:
            ok = any(n == num and s == suf and year_ok(y, yr) for (n, s, y) in found) or (
                num_year and re.search(r"\b%s\s*-?\s*%s\b" % (num, suf), full) is not None)
        if not ok:
            missing.append(v)
    type_missing = []
    for fam in sorted({VAL.match(v).group(1) for v in rec["proposed_value"] if VAL.match(v)}):
        is_diary = any(VAL.match(v) and VAL.match(v).group(1) == fam and VAL.match(v).group(2) for v in rec["proposed_value"])
        rx = TYPE_LABELS.get(fam)
        if rx and not re.search(rx, full, re.I):
            type_missing.append(fam)
        if is_diary and not re.search(r"diary|\bD\.\s*No", full, re.I):
            type_missing.append(fam + "DIARY")
    # locate the page of the first staged number for the anchor
    excerpt, pt = "", ""
    m0 = VAL.match(rec["proposed_value"][0]) if rec["proposed_value"] else None
    for pg, p in windows:
        if m0 and re.search(r"\b%s\b" % m0.group(3), p):
            first_page, pt = pg, p
            break
    if first_page:
        m0 = VAL.match(rec["proposed_value"][0])
        k = re.search(r"\b%s\b" % m0.group(3), pt)
        excerpt = pt[max(0, k.start() - 120): k.end() + 120] if k else ""
    return dict(text_layer="TEXT_LAYER", missing=missing, type_missing=type_missing, page=first_page or "",
                excerpt=excerpt, npages=npages)


def artifact_check(repo):
    """--check without PyMuPDF (post-freeze integration fix, review A5-01a). States what it skips; never claims a full
    reproduction. Verifies the committed artefacts against each other, the pinned C12 input, the HF staged manifest and,
    when the object store is present, the PDF bytes' sha256."""
    skipped = ["PDF text-layer re-extraction (PyMuPDF absent)", "text-layer matching of staged numbers"]
    problems = []
    staged_raw = OVERLAY_C12.read_bytes()
    if C.sha256_bytes(staged_raw) != OVERLAY_C12_SHA:
        problems.append("C12 staged overlay sha256 changed")
    staged = {json.loads(l)["doc_id"]: json.loads(l) for l in staged_raw.decode("utf-8").splitlines() if l.strip()}
    ov_path = OUT / "SC_CASE_NUMBER_OVERLAY_C13.jsonl"
    overlay = [json.loads(l) for l in ov_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rec = C.read_csv(OUT / "SCNUM_RECONFIRMATION_C13.csv")
    summ = json.loads((OUT / "SCNUM_SUMMARY_C13.json").read_text(encoding="utf-8"))
    imgs = {r["doc_id"] for r in C.read_csv(OUT / "PAGE_IMAGE_CHECKS_C13.csv")}
    if len(overlay) != 99 or len(rec) != 99 or summ.get("overlay_records") != len(overlay):
        problems.append("record counts differ (overlay %d, reconfirmation %d)" % (len(overlay), len(rec)))
    for o in overlay:
        st = staged.get(o["doc_id"])
        if st is None or o["overlay_value"] != st["proposed_value"] or o["source_copy_sha256"] != st["sha256"]:
            problems.append("overlay row differs from the C12 staged value: %s" % o["doc_id"])
    for r in rec:
        if r["verdict"] != "RECONFIRMED" or r["sha256_verified"] != "TRUE":
            problems.append("row not reconfirmed: %s" % r["doc_id"])
        if (r["not_found_in_text_layer"] or r["type_label_not_found"]) and r["doc_id"] not in imgs:
            problems.append("text-layer gap without page-image reading: %s" % r["doc_id"])
    man = {m["hf_path"]: m["sha256"] for m in C.read_csv(C.PKG / "hf" / "STAGED_MANIFEST.csv")}
    if man.get("data/meta_overlays/c13_2026-11-25_sc_case_numbers.jsonl") != C.sha256_file(ov_path):
        problems.append("overlay differs from the HF staged manifest")
    ins = summ.get("input_sha256", {})
    if ins.get("page_image_checks") != C.sha256_file(OUT / "PAGE_IMAGE_CHECKS_C13.csv"):
        problems.append("page-image checks file changed since the summary")
    if summ.get("restricted_register", {}).get("sha256") != C.Restricted().provenance["sha256"]:
        problems.append("restricted register changed since the summary")
    pdfs = "not checked (object store %s absent)" % repo
    if Path(repo).is_dir():
        tree = C.ls_tree(repo, C.TEXT_COMMIT, "data/raw")
        by_sha = {Path(p).stem: p for p in tree}
        specs = {r["doc_id"]: "%s:%s" % (C.TEXT_COMMIT, by_sha.get(r["sha256"], "missing")) for r in rec}
        blobs = C.cat_blobs(repo, specs.values())
        bad = [d for d, sp in specs.items() if blobs.get(sp) is None
               or C.sha256_bytes(blobs[sp]) != next(r["sha256"] for r in rec if r["doc_id"] == d)]
        pdfs = "%d of %d PDF byte hashes equal the staged sha256" % (len(rec) - len(bad), len(rec))
        if bad:
            problems.append("PDF bytes differ: %s" % bad[:3])
    else:
        skipped.append("PDF byte re-hash (object store absent)")
    if problems:
        print("CHECK FAILED (artefact check, PyMuPDF absent): " + "; ".join(problems[:5]))
        return 1
    print("CHECK PARTIAL (PyMuPDF absent): skipped %s. Verified: 99 overlay rows equal the pinned C12 staged values; "
          "99 reconfirmation rows RECONFIRMED, every text-layer gap has a page-image reading; overlay sha256 equals the HF "
          "staged manifest; %s." % ("; ".join(skipped), pdfs))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=C.DEFAULT_REPO)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    try:
        import fitz  # PyMuPDF (AGPL); needed only to re-extract the PDF text layer
    except ImportError:
        if a.check:
            return artifact_check(a.repo)
        raise SystemExit("PyMuPDF (fitz) is required to rebuild the reconfirmation; --check without it verifies committed artefacts only")

    restricted = C.Restricted()
    staged_raw = OVERLAY_C12.read_bytes()
    assert C.sha256_bytes(staged_raw) == OVERLAY_C12_SHA, "C12 staged overlay changed; stop and re-review"
    staged = [json.loads(l) for l in staged_raw.decode("utf-8").splitlines() if l.strip()]
    assert len(staged) == 99, len(staged)
    assert all(r["status"] == "CORRECTION_STAGED_DERIVATIVE_OVERLAY_ORIGINAL_UNCHANGED" for r in staged)
    image_checks = {}
    icp = OUT / "PAGE_IMAGE_CHECKS_C13.csv"
    if icp.exists():
        for r in C.read_csv(icp):
            image_checks[r["doc_id"]] = r

    raw_tree = C.ls_tree(a.repo, C.TEXT_COMMIT, "data/raw")
    by_sha = {Path(p).stem: p for p in raw_tree}
    specs = []
    for r in staged:
        assert not restricted.hit(sha256=r["sha256"], doc_id=r["doc_id"])
        specs.append("%s:%s" % (C.TEXT_COMMIT, by_sha[r["sha256"]]))
    blobs = C.cat_blobs(a.repo, specs)

    rows, overlay, tally = [], [], {}
    for r, spec in zip(staged, specs):
        b = blobs[spec]
        assert b is not None and C.sha256_bytes(b) == r["sha256"], "byte mismatch for %s" % r["doc_id"]
        res = check_record(r, b, fitz)
        ic = image_checks.get(r["doc_id"])
        if not res["missing"] and not res["type_missing"]:
            verdict, basis = "RECONFIRMED", "PDF text layer (PyMuPDF, cover pages 1-%d and every jurisdiction-heading block): every staged number, year and type label printed" % COVER_PAGES
        elif ic and ic["verdict"] == "RECONFIRMED_PAGE_IMAGE":
            verdict, basis = "RECONFIRMED", "page image read by AI agent (C13-A5): " + ic["note"]
        elif ic and ic["verdict"] == "NOT_RECONFIRMED_PAGE_IMAGE":
            verdict, basis = "NOT_RECONFIRMED", "page image read by AI agent (C13-A5): " + ic["note"]
        else:
            verdict, basis = "NOT_RECONFIRMED_NEEDS_PAGE_IMAGE_CHECK", "text-layer check incomplete; no page-image reading recorded"
        tally[verdict] = tally.get(verdict, 0) + 1
        rows.append(dict(doc_id=r["doc_id"], judgment_id=r["judgment_id"], sha256=r["sha256"], raw_path=by_sha[r["sha256"]],
                         sha256_verified="TRUE", c12_evidence_basis=r["evidence_basis"],
                         staged_value=";".join(r["proposed_value"]), staged_count=len(r["proposed_value"]),
                         text_layer=res["text_layer"], pdf_pages=res["npages"],
                         not_found_in_text_layer=";".join(res["missing"]), type_label_not_found=";".join(res["type_missing"]),
                         page_image_check=(ic or {}).get("verdict", ""), anchor_page=res["page"],
                         excerpt=res["excerpt"][:300], verdict=verdict, basis=basis))
        if verdict == "RECONFIRMED":
            overlay.append(dict(
                overlay_id="SCNUM-C13-%s" % r["sha256"][:12], overlay_version="C13-v1", supersedes_overlay_version="C12-v1 (staged, not applied)",
                doc_id=r["doc_id"], judgment_id=r["judgment_id"], source_copy_sha256=r["sha256"], field="case_numbers",
                original_value=r["original_value"], overlay_value=r["proposed_value"],
                unnormalised_references=r["unnormalised_references"],
                evidence=dict(c12_basis=r["evidence_basis"], c13_reconfirmation=basis, raw_path=by_sha[r["sha256"]],
                              anchor_page=res["page"] or None, source_commit=C.TEXT_COMMIT),
                scope="METADATA_ONLY_NO_EVIDENCE_OR_AUTHENTICATION_STATUS_PROMOTED",
                status="METADATA_OVERLAY_ORIGINAL_UNCHANGED",
                verification="AI_DOCUMENTARY_RECONFIRMATION_NOT_LEGAL_VALIDATION",
                tool=VERSION))
    summary = dict(tool=VERSION, pymupdf=" / ".join(str(x) for x in fitz.version if x),
                   basis_counts=dict(text_layer_only=sum(1 for x in rows if x["verdict"] == "RECONFIRMED" and not x["page_image_check"] and x["basis"].startswith("PDF")), page_image_assisted=sum(1 for x in rows if x["verdict"] == "RECONFIRMED" and x["basis"].startswith("page image"))), staged_records=len(staged),
                   staged_numbers=sum(len(r["proposed_value"]) for r in staged), tally=dict(sorted(tally.items())),
                   overlay_records=len(overlay), overlay_numbers=sum(len(o["overlay_value"]) for o in overlay),
                   not_applied_out_of_scope=dict(APPLY_CANDIDATE_UNREVIEWED_CONFIRMED=266, UNRESOLVED=3),
                   input_sha256={str(OVERLAY_C12.relative_to(C.WT)): C.sha256_bytes(staged_raw),
                                 "page_image_checks": C.sha256_file(icp) if icp.exists() else None},
                   restricted_register=restricted.provenance,
                   policy="metadata overlay only; data/meta never rewritten; 266 unreviewed candidates not read or applied")
    files = {"SCNUM_RECONFIRMATION_C13.csv": C.to_csv(rows), "SC_CASE_NUMBER_OVERLAY_C13.jsonl": C.to_jsonl(overlay),
             "SCNUM_SUMMARY_C13.json": C.dumps(summary)}
    rc = C.write_or_check(files, OUT, a.check)
    if not a.check:
        print(json.dumps(summary["tally"]), summary["overlay_records"], summary["overlay_numbers"])
    return rc


if __name__ == "__main__":
    sys.exit(main())
