"""Create the `documents` table for P1 and export a small public PDF store (restricted list applied).

python -I setup_db.py <work_dir> <c7_repo> <b-poc repo> <pdfstore_dir>
"""
import json, subprocess, sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.restricted import load_restricted  # noqa: E402

work, c7, repo, store = map(Path, sys.argv[1:5])
rs = load_restricted(repo)
store.mkdir(parents=True, exist_ok=True)
docs = [json.loads(l) for l in open(work / "corpus/corpus.jsonl")]
# PDFs for streaming: all statutes + the first 40 judgments (by doc_id) that have a raw PDF
picked = [d for d in docs if d["doc_type"] != "judgment"] + sorted([d for d in docs if d["doc_type"] == "judgment"], key=lambda d: d["doc_id"])[:40]
exported = {}
for d in picked:
    rp = d.get("raw_path")
    if not rp or not rp.endswith(".pdf") or rs.blocks(doc_id=d["doc_id"], sha256=d["sha256"], path=rp):
        continue
    blob = subprocess.run(["git", "-C", str(c7), "show", f"ad77758d:{rp}"], capture_output=True).stdout
    if not blob or rs.blocks(blob=blob):
        continue
    name = f"{d['sha256']}.pdf"
    (store / name).write_bytes(blob)
    exported[d["doc_id"]] = name
with psycopg.connect("host=127.0.0.1 port=55432 user=poc dbname=poc", autocommit=True) as c:
    c.execute("DROP TABLE IF EXISTS documents")
    c.execute("CREATE TABLE documents(doc_id text PRIMARY KEY, doc_type text, title text, meta jsonb, pdf_file text)")
    with c.cursor().copy("COPY documents FROM STDIN") as cp:
        for d in docs:
            meta = {k: v for k, v in d.items() if k != "text"}
            cp.write_row((d["doc_id"], d["doc_type"], d["title"], json.dumps(meta), exported.get(d["doc_id"])))
sizes = sorted(((store / n).stat().st_size, k) for k, n in exported.items())
print(json.dumps({"documents": len(docs), "pdfs": len(exported), "smallest": sizes[0], "median": sizes[len(sizes) // 2], "largest": sizes[-1]}))
