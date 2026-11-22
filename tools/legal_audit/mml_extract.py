#!/usr/bin/env python3
"""Reproducible, private MML text extraction (derived layer) with page/line locators.

Never publishes manual text. Writes derived text ONLY to an output directory outside the
repository working tree, verifies every original against the MML manifest first, and can emit a
non-restricted metadata manifest (hashes, page/line counts, tool versions) suitable for committing.

Usage (authorised private environment, originals obtained from the private HF dataset):
  python tools/legal_audit/mml_extract.py --originals /secure/mml/originals --out /secure/mml/derived \
      --record legal_knowledge/audit_work/PILOT-01/mml_derived_manifest.json
  python tools/legal_audit/mml_extract.py --originals ... --out ... --verify legal_knowledge/audit_work/PILOT-01/mml_derived_manifest.json
  python tools/legal_audit/mml_extract.py --originals ... --render "MML 2.pdf:152" --out ...   # page image for checks

Requires poppler-utils (pdftotext, pdfinfo, pdftoppm) and LibreOffice (soffice) for .doc files.
Locator formats (must stay stable; pilot findings depend on them):
  PDF  -> '=== PDF_PAGE n / file=<name> ===' before each page (pdftotext -layout, page by page)
  DOC  -> first line '=== DOC_TEXT (no pages; locator = LINE n) file=<stem> ===', then 'Lnnnnn| <text>'
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "legal_knowledge" / "manual_sources" / "MML_Originals_Manifest.csv"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def tool_versions() -> dict:
    v = {}
    for name, cmd in (("pdftotext", ["pdftotext", "-v"]), ("soffice", ["soffice", "--version"])):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            v[name] = (r.stdout + r.stderr).strip().splitlines()[0]
        except FileNotFoundError:
            v[name] = None
    return v


def inside_repo(p: Path) -> bool:
    try:
        p.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def load_manifest() -> dict:
    with MANIFEST.open(encoding="utf-8") as fh:
        return {r["filename"]: r["sha256"] for r in csv.DictReader(fh)}


def extract_pdf(src: Path, dst: Path):
    pages = int(next(l.split()[1] for l in run(["pdfinfo", str(src)]).splitlines() if l.startswith("Pages:")))
    with dst.open("w", encoding="utf-8") as out:
        for p in range(1, pages + 1):
            out.write(f"=== PDF_PAGE {p} / file={src.name} ===\n")
            out.write(run(["pdftotext", "-layout", "-f", str(p), "-l", str(p), str(src), "-"]))
    return {"pages": pages}


def extract_doc(src: Path, dst: Path, stem: str):
    with tempfile.TemporaryDirectory() as td:
        # Isolated LibreOffice profile so results do not depend on user settings.
        prof = Path(td) / "profile"
        subprocess.run(["soffice", f"-env:UserInstallation=file://{prof}", "--headless", "--convert-to", "txt:Text",
                        "--outdir", td, str(src)], check=True, capture_output=True)
        txt = next(Path(td).glob("*.txt"))
        lines = txt.read_text(encoding="utf-8", errors="replace").split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    with dst.open("w", encoding="utf-8") as out:
        out.write(f"=== DOC_TEXT (no pages; locator = LINE n) file={stem} ===\n")
        for n, l in enumerate(lines, 1):
            out.write(f"L{n:05d}| {l}\n")
    return {"lines": len(lines)}


def derived_name(orig: str) -> tuple[str, str]:
    if orig.lower().endswith(".pdf"):
        return f"{orig}.pages.txt", "pdf"
    stem = orig[:-4] if orig.lower().endswith(".doc") else orig  # 'MML vol 2(AA).doc.doc' -> 'MML vol 2(AA).doc'
    return f"{stem}.lines.txt", "doc"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--originals", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--record", type=Path, help="write non-restricted metadata manifest here")
    ap.add_argument("--verify", type=Path, help="compare derived hashes with a recorded manifest")
    ap.add_argument("--render", action="append", default=[], help="'<file>:<page>' -> PNG page image (110 dpi)")
    a = ap.parse_args()
    if inside_repo(a.out):
        print("REFUSED: --out is inside the repository; derived manual text must stay outside version control.", file=sys.stderr)
        return 2
    a.out.mkdir(parents=True, exist_ok=True)
    expected = load_manifest()
    rec = {"tool": "tools/legal_audit/mml_extract.py", "tool_versions": tool_versions(),
           "mml_manifest_sha256": sha(MANIFEST), "files": []}
    for name, want in expected.items():
        src = a.originals / name
        if not src.is_file():
            print(f"MISSING original: {name}", file=sys.stderr); return 1
        got = sha(src)
        if got != want:
            print(f"HASH MISMATCH: {name} {got} != manifest {want}", file=sys.stderr); return 1
        dname, kind = derived_name(name)
        dst = a.out / dname
        info = extract_pdf(src, dst) if kind == "pdf" else extract_doc(src, dst, dname[:-len(".lines.txt")])
        rec["files"].append({"original": name, "original_sha256": got, "derived": dname, "derived_sha256": sha(dst),
                             "kind": kind, **info})
    for spec in a.render:
        fname, page = spec.rsplit(":", 1)
        prefix = a.out / "page_images" / f"{Path(fname).stem}_p{int(page):03d}"
        prefix.parent.mkdir(exist_ok=True)
        subprocess.run(["pdftoppm", "-r", "110", "-f", page, "-l", page, "-png", str(a.originals / fname), str(prefix)], check=True)
    if a.record:
        a.record.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    status = 0
    if a.verify:
        old = {f["derived"]: f["derived_sha256"] for f in json.loads(a.verify.read_text(encoding="utf-8"))["files"]}
        for f in rec["files"]:
            ok = old.get(f["derived"]) == f["derived_sha256"]
            print(f"{'MATCH   ' if ok else 'MISMATCH'} {f['derived']}")
            status |= 0 if ok else 3
    print(json.dumps({"files": len(rec["files"]), "out": str(a.out), "tool_versions": rec["tool_versions"]}))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
