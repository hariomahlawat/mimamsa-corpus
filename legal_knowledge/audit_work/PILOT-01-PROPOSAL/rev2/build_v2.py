#!/usr/bin/env python3
"""PILOT-01 revision 2: MML structure + provision crosswalk + registers. Read-only on inputs.
argv: <audit checkout> <mml text dir (pdftotext/soffice output)> <mml originals dir> <out dir>"""
import csv, hashlib, json, re, sys, collections
from pathlib import Path
SRC, TXT, ORIG, OUT = map(Path, sys.argv[1:5]); OUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
FILES = {  # original name -> (text file, extraction method, component as observed)
 "MML 1.doc": ("MML 1.txt", "soffice --convert-to txt", "Part I: commentary (8 chapters)"),
 "MML 2.pdf": ("MML 2.pdf.txt", "pdftotext -layout", "Army Act 1950 AND Army Rules 1954 with notes + appendices (combined)"),
 "MML vol 2(AA).doc.doc": ("MML vol 2(AA).doc.txt", "soffice --convert-to txt", "Army Act 1950 with notes"),
 "MML vol 2(AA).pdf": ("MML vol 2(AA).pdf.txt", "pdftotext -layout", "Army Act 1950 with notes"),
 "MML vol 2(AR).doc-1.doc": ("MML vol 2(AR).doc-1.txt", "soffice --convert-to txt", "Army Rules 1954 with notes (with arrangement table)"),
 "MML vol 2(AR).doc.doc": ("MML vol 2(AR).doc.txt", "soffice --convert-to txt", "Army Rules 1954 with notes (from S.R.O. 484 preamble)"),
 "MML vol 3.doc.doc": ("MML vol 3.doc.txt", "soffice --convert-to txt", "Part III: other enactments"),
 "MML vol 3.pdf.pdf": ("MML vol 3.pdf.pdf.txt", "pdftotext -layout", "Part III: other enactments"),
}
manifest = {r["filename"]: r for r in csv.DictReader(open(SRC / "legal_knowledge/manual_sources/MML_Originals_Manifest.csv"))}
struct = []
for name, (tf, method, comp) in FILES.items():
    o = ORIG / name; t = (TXT / tf).read_text(encoding="utf-8", errors="replace")
    yrs = [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-2]\d)\b", t)]
    struct.append({
        "file": name, "sha256": sha(o), "manifest_sha256_match": sha(o) == manifest[name]["sha256"],
        "bytes": o.stat().st_size, "component_observed": comp,
        "component_in_v2.3_inventory": None, "extraction": method, "text_chars": len(t),
        "chapters_detected": len(re.findall(r"^\s*CHAPTER\s+[IVXLC]+[A-Z]?\b", t, re.M)),
        "notes_blocks": len(re.findall(r"^\s*NOTES?\s*$", t, re.M)),
        "amendment_footnotes": len(re.findall(r"\b(Omitted|Subs(?:tituted)?\.?|Ins(?:erted)?\.?)\s+(by|vide)", t, re.I)),
        "appendix_headings": len(re.findall(r"^\s*APPENDIX\s+[IVXL]+", t, re.M)),
        "case_citations_detected": len(re.findall(r"\bAIR\s?\d{4}\s?SC\s?\d+|\(\d{4}\)\s?\d+\s?SCC\s?\d+|\[\d{4}\]\s?\d*\s?SCR\s?\d+", t)),
        "latest_year_in_text": max(yrs) if yrs else None,
        "mentions_AFT_Act_2007": len(re.findall(r"Armed Forces Tribunal", t, re.I)),
        "mentions_BNS_BNSS_BSA": len(re.findall(r"Bharatiya|\bBNSS?\b", t)),
        "access_marking_text_detected": "none as a document marking (keyword hits were ordinary prose); headers/watermarks not inspected visually",
        "examination_status": "STRUCTURE_PROFILED_AUTOMATICALLY; targeted passages read (see report); NOT read in full",
    })
inv23 = {r["file_name"]: r["component"] for r in csv.DictReader(open(SRC / "legal_knowledge/reconciliation/v2.3/01_Uploaded_MML_File_Inventory.csv"))}
for s in struct: s["component_in_v2.3_inventory"] = inv23.get(s["file"])
(OUT / "mml_structure.json").write_text(json.dumps(struct, indent=2, ensure_ascii=False))

# ---- provision crosswalk: AA sections and AR rules
def heads(t, maxn):
    found = {}
    for m in re.finditer(r"^\s*\[?\s*(\d{1,3}[A-Z]?)\.\s*(?:\[\s*)?([A-Z][^\n]{0,90})", t, re.M):
        n, rest = m.group(1), m.group(2)
        num = int(re.match(r"\d+", n).group())
        if num > maxn or n in found: continue
        if re.match(r"(Omitted|\(?Omitted)", rest, re.I) or ("—" in rest or ".-" in rest or ".—" in rest or "-" in rest[:80]):
            found[n] = "OMITTED" if re.match(r"\(?\[?\s*Omitted", rest, re.I) else "PRESENT"
    return found
txt = {k: (TXT / v[0]).read_text(encoding="utf-8", errors="replace") for k, v in FILES.items()}
mml2 = txt["MML 2.pdf"]; cut = mml2.find("S.R.O. 484") if "S.R.O. 484" in mml2 else len(mml2) // 2
aa_src = {"MML vol 2(AA).pdf": heads(txt["MML vol 2(AA).pdf"], 193), "MML 2.pdf(AA part)": heads(mml2[:cut], 193)}
ar_src = {"MML vol 2(AR).doc.doc": heads(txt["MML vol 2(AR).doc.doc"], 205), "MML 2.pdf(AR part)": heads(mml2[cut:], 205)}

kb = [json.loads(l) for l in open(SRC / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl")]
def nums(spec):
    out = set()
    for a, b in re.findall(r"(\d+[A-Z]?)(?:\s*[–\-]\s*(\d+))?", spec):
        if b and a.isdigit() and 0 < int(b) - int(a) < 30: out |= {str(i) for i in range(int(a), int(b) + 1)}
        else: out.add(a)
    return out
AA, AR = collections.defaultdict(set), collections.defaultdict(set)
for r in kb:
    t = r["title"] + " " + r["body"] + " " + str(r["references"])
    for m in re.finditer(r"(?:Army Rules?|\bAR\b|\bRules?\b|\br)\s*\.?\s*((?:\d+[A-Z]?(?:\(\d+\))?(?:\s*[–\-]\s*\d+)?(?:\s*(?:,|and|&)\s*)?)+)", t):
        ctx = t[max(0, m.start() - 40):m.start()]
        if re.search(r"AFT|Tribunal|Entitlement|Pension|ISO|adjustment|1978|Procedure", ctx): continue
        for n in nums(re.sub(r"\(\d+\)", "", m.group(1))): AR[n].add(r["id"])
    for m in re.finditer(r"(?:Army Act|\bAA\b)?\s*(?:\bs|\bss|§§|§|\bsection|\bsections)\s?\.?\s*((?:\d+[A-Z]?(?:\(\d+\))?(?:\s*[–\-]\s*\d+)?(?:\s*(?:,|and|&)\s*)?)+)", t, re.I):
        ctx = t[max(0, m.start() - 60):m.start()]
        if re.search(r"BNS|BNSS|BSA|AFT|Tribunal|IPC|CrPC|Evidence|ISO|AFSPA|Constitution|Art", ctx): continue
        for n in nums(re.sub(r"\(\d+\)", "", m.group(1))): AA[n].add(r["id"])
with open(OUT / "mml_provision_crosswalk.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["instrument", "provision", "mml_vol2_status", "mml2_pdf_status", "kb_records_citing_HEURISTIC", "kb_ids_sample", "gap_flag"])
    for inst, src, kbmap, rng in [("Army Act 1950", aa_src, AA, range(1, 194)), ("Army Rules 1954", ar_src, AR, range(1, 206))]:
        a, b = list(src.values())
        keys = sorted(set(a) | set(b) | {str(i) for i in rng}, key=lambda k: (int(re.match(r"\d+", k).group()), k))
        for k in keys:
            if int(re.match(r"\d+", k).group()) not in rng: continue
            ids = sorted(kbmap.get(k, ()))
            st1, st2 = a.get(k, "NOT_DETECTED"), b.get(k, "NOT_DETECTED")
            gap = "NO_KB_RECORD" if not ids and "PRESENT" in (st1, st2) else ("OMITTED_BUT_CITED" if ids and "OMITTED" in (st1, st2) else "")
            w.writerow([inst, k, st1, st2, len(ids), ";".join(ids[:6]), gap])
print("crosswalk written")
for inst, src in [("AA", aa_src), ("AR", ar_src)]:
    for k, v in src.items(): print(inst, k, "detected", len(v), "omitted", sum(1 for x in v.values() if x == "OMITTED"))
