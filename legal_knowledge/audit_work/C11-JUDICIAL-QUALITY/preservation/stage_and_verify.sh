#!/usr/bin/env bash
# Owner-run preservation procedure for the 48 working-store-only registered copies (C11 Priority Zero).
# Step 1 (local, safe): stage byte-identical copies plus sidecars into DEST and verify every SHA-256.
# Step 2 (owner only, needs approval and the owner's own credentials): upload DEST to the approved store.
# Step 3 (owner only): re-download from the store into a fresh directory and verify against SOURCE_MANIFEST.sha256.
# The script never modifies, recompresses or deletes a source file. Usage:
#   stage_and_verify.sh <working-store root holding downloads/> <empty DEST dir>
set -euo pipefail
STORE="$1"; DEST="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
[ -d "$STORE/downloads" ] || { echo "no downloads/ under $STORE"; exit 2; }
mkdir -p "$DEST"; [ -z "$(ls -A "$DEST")" ] || { echo "DEST not empty"; exit 2; }
python3 -I - "$HERE/PRESERVATION_INVENTORY.csv" "$STORE" "$DEST" <<'PY'
import csv, hashlib, json, os, shutil, sys
inv, store, dest = sys.argv[1:4]
for r in csv.DictReader(open(inv, encoding="utf-8")):
    src = os.path.join(store, r["present_paths"].split(";")[0])
    sub = os.path.join(dest, r["sha256"][:2], r["sha256"])
    os.makedirs(sub)
    out = os.path.join(sub, os.path.basename(src))          # original filename kept
    shutil.copyfile(src, out)                                 # byte copy, no conversion
    h = hashlib.sha256(open(out, "rb").read()).hexdigest()
    if h != r["sha256"]:
        sys.exit(f"HASH MISMATCH after copy: {r['copy_id']}")
    side = {k: r[k] for k in ("copy_id", "source_id", "sha256", "bytes", "title", "working_store_paths", "source_url",
                              "provenance", "acquisition_provenance", "access_marking", "access_class", "kb_exact_anchor_rows")}
    json.dump(side, open(out + ".meta.json", "w", encoding="utf-8"), indent=1, sort_keys=True, ensure_ascii=False)
print("staged and verified")
PY
( cd "$DEST" && find . -type f ! -name '*.meta.json' ! -name STAGED_SHA256SUMS -print0 | sort -z | xargs -0 sha256sum ) > "$DEST.sums.tmp" && mv "$DEST.sums.tmp" "$DEST/STAGED_SHA256SUMS"
python3 -I - "$HERE/SOURCE_MANIFEST.sha256" "$DEST/STAGED_SHA256SUMS" <<'PY'
import sys
want = {l.split()[0] for l in open(sys.argv[1]) if l.strip()}
got = {l.split()[0] for l in open(sys.argv[2]) if l.strip()}
assert want == got, (len(want), len(got), sorted(want ^ got)[:3])
print(f"OK: {len(got)} staged copies equal the manifest")
PY
