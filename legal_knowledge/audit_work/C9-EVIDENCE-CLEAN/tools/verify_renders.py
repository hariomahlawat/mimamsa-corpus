"""Re-hash held files and re-render every row of the committed Gazette render_log.csv and SC render_facts.jsonl; compare hashes. Renders are kept in memory only."""
import csv, json, hashlib, sys, os, pymupdf
scratch, ev = sys.argv[1], sys.argv[2]
def sh(b): return hashlib.sha256(b).hexdigest()
def render(path, page):
    d = pymupdf.open(path); pm = d[page-1].get_pixmap(dpi=150, colorspace=pymupdf.csGRAY, alpha=False)
    return sh(pm.tobytes("png"))
res = {"gazette": [0,0,0,0], "sc": [0,0,0,0]}  # rows, file match, render match, missing
rows = list(csv.DictReader(open(os.path.join(ev, "GAZETTE-T1/render_log.csv"), encoding="utf-8")))
for r in rows:
    p = os.path.join(scratch, r["held_path"]); res["gazette"][0] += 1
    if not os.path.isfile(p): res["gazette"][3] += 1; continue
    if sh(open(p,"rb").read()) == r["sha256"]: res["gazette"][1] += 1
    if render(p, int(r["pdf_page"])) == r["png_sha256"]: res["gazette"][2] += 1
    else: print("GAZ RENDER DIFF", r["tranche_id"], r["pdf_page"])
for line in open(os.path.join(ev, "SC-T2/tools/render_facts.jsonl"), encoding="utf-8"):
    r = json.loads(line); res["sc"][0] += 1
    p = os.path.join(scratch, r["held_path"])
    if not os.path.isfile(p): res["sc"][3] += 1; print("SC missing", r["held_path"]); continue
    if sh(open(p,"rb").read()) == r["sha256"]: res["sc"][1] += 1
    pg = r.get("page") or r.get("pdf_page")
    if render(p, int(pg)) == r["png_sha256"]: res["sc"][2] += 1
    else: print("SC RENDER DIFF", r["held_path"], pg)
print(json.dumps({k: dict(zip(["rows","file_sha256_match","render_sha256_match","held_file_missing"], v)) for k, v in res.items()}))
