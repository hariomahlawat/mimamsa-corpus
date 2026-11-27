"""Licence summary from ACTUAL metadata: pip-licenses output, npm licence checker, the .NET CycloneDX SBOM,
and model-card front matter of the downloaded model revisions.

python -I licence_summary.py <p7_dir> <models_dir> <models.lock.json> <out.csv>
"""
import csv, json, re, sys
from pathlib import Path

p7, models_dir, lock_path, out = map(Path, sys.argv[1:5])
CANDIDATES = {"tantivy", "faiss-cpu", "onnxruntime", "tokenizers", "numpy", "psycopg", "psycopg-binary", "psycopg-pool",
              "pypdfium2", "pdfminer.six", "pdfplumber", "PyMuPDF", "pymupdf", "Django", "asgiref", "sqlparse", "Hypercorn",
              "uvicorn", "waitress", "h11", "h2", "wsproto", "cryptography", "huggingface-hub", "huggingface_hub", "protobuf",
              "flatbuffers", "pillow", "Pillow", "charset-normalizer", "pymupdf4llm", "pymupdf_layout", "pymupdf-layout"}
rows = []
for p in json.loads((p7 / "python-licenses.json").read_text()):
    if p["Name"] in CANDIDATES:
        rows.append(dict(ecosystem="pypi", name=p["Name"], version=p["Version"], licence_from_metadata=p["License"],
                         source="pip-licenses --from=mixed (installed package metadata)", flag=""))
try:
    for k, v in json.loads((p7 / "npm-licenses-pdfjs.json").read_text()).items():
        name, ver = k.rsplit("@", 1)
        if name in ("pdfjs-dist", "vite") or name.startswith("@napi-rs/canvas"):
            rows.append(dict(ecosystem="npm", name=name, version=ver, licence_from_metadata=v.get("licenses"),
                             source="license-checker (package.json)", flag=""))
except FileNotFoundError:
    pass
sb = json.loads((p7 / "sbom-dotnet-aspnet.cdx.json").read_text())
for c in sb.get("components", []):
    lic = ";".join((l.get("license", {}).get("id") or l.get("license", {}).get("name") or l.get("expression") or "")
                   for l in c.get("licenses", [])) or "NOT IN NUSPEC METADATA"
    rows.append(dict(ecosystem="nuget", name=c["name"], version=c.get("version"), licence_from_metadata=lic,
                     source="CycloneDX .NET SBOM (nuspec)", flag=""))
lock = json.loads(lock_path.read_text())
for key, ent in lock.items():
    readme = models_dir / key / "README.md"
    lic = None
    if readme.exists():
        m = re.search(r"^license:\s*(\S+)", readme.read_text(errors="replace"), re.M)
        lic = m.group(1) if m else None
    rows.append(dict(ecosystem="hf-model", name=ent["repo"], version=ent["revision"][:12],
                     licence_from_metadata=lic or ent.get("license_card"), source="model card front matter (README.md at pinned revision)",
                     flag="" if "LICENSE" in ent["files"] else "no LICENSE file in repo; licence from card only"))
for r in rows:
    l = str(r["licence_from_metadata"]).lower()
    if "agpl" in l or "affero" in l:
        r["flag"] = (r["flag"] + "; " if r["flag"] else "") + "COPYLEFT (AGPL): network/distribution obligations or commercial licence"
    elif "lgpl" in l:
        r["flag"] = (r["flag"] + "; " if r["flag"] else "") + "WEAK COPYLEFT (LGPL): fine as an unmodified, replaceable dependency; keep relinkable"
    elif "unknown" in l or l in ("none", ""):
        r["flag"] = (r["flag"] + "; " if r["flag"] else "") + "LICENCE NOT DECLARED IN METADATA: review before use"
    elif "gpl" in l:
        r["flag"] = (r["flag"] + "; " if r["flag"] else "") + "COPYLEFT (GPL)"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["ecosystem", "name", "version", "licence_from_metadata", "flag", "source"])
    w.writeheader(); w.writerows(rows)
for r in rows:
    print(r["ecosystem"], r["name"], r["version"], "|", r["licence_from_metadata"], "|", r["flag"])
