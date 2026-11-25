"""GA4 evaluator: build PAGES.jsonl (sha256, page (1-based), text) from sha256-verified local copies of the
representative files (PyMuPDF text layer). Files whose bytes do not hash to the expected sha are refused."""
import glob, hashlib, json, os, sys
import fitz
S, need_file, out = sys.argv[1], sys.argv[2], sys.argv[3]
need = set(open(need_file).read().split())
cands = {}
for p in glob.glob(S + "/coding/**/*", recursive=True) + glob.glob(S + "/cache_a0/**/*", recursive=True):
    b = os.path.basename(p).split('.')[0]
    if b in need and os.path.isfile(p):
        cands.setdefault(b, []).append(p)
log = {"verified": 0, "missing": [], "mismatch": []}
with open(out, "w", encoding="utf-8") as f:
    for sha in sorted(need):
        ok = None
        for p in cands.get(sha, []):
            data = open(p, "rb").read()
            if hashlib.sha256(data).hexdigest() == sha:
                ok = data; break
            log["mismatch"].append(p)
        if ok is None:
            log["missing"].append(sha); continue
        log["verified"] += 1
        doc = fitz.open(stream=ok, filetype="pdf")
        for i, pg in enumerate(doc):
            f.write(json.dumps({"sha256": sha, "page": i + 1, "text": pg.get_text()}, ensure_ascii=False) + "\n")
print(json.dumps({k: (v if isinstance(v, int) else len(v)) for k, v in log.items()}), log["missing"][:5])
