#!/usr/bin/env python3
"""C12 Workstream H: merge TARGETS.csv + fetch_results.json into ACQUISITION_MANIFEST.csv (no network).

Also re-hashes every stored file so the manifest's sha256 is the hash of the bytes on disk.
Usage: python -I build_manifest.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ACQ = Path(__file__).resolve().parent.parent
COLS = ["target_id", "workstream_target", "priority", "description", "url", "host", "allow_listed", "robots_result",
        "status", "sha256", "bytes", "pages", "completeness", "relation_to_existing_copy", "stored_path",
        "expected_sha256", "expected_md5", "md5", "existing_sha256", "retrieved_at", "attempts", "selection_reason",
        "provenance"]

BLOCK_NOTE = {
    "BLOCKED_HOST_NOT_ALLOW_LISTED": "host not in any allowed_hosts entry of config/sources.yaml: not contacted",
    "NOT_TARGETED_COMPLETE_CONTENT_COPY_IN_CORPUS": "not one of the 22: complete content copy already in corpus",
    "NOT_ATTEMPTED_NO_PINNED_URL_OR_OVER_CAP": "not contacted",
}


def main() -> int:
    targets = list(csv.DictReader(open(ACQ / "TARGETS.csv")))
    res = json.loads((ACQ / "fetch_results.json").read_text()) if (ACQ / "fetch_results.json").exists() else {}
    out = []
    for t in targets:
        r = {c: t.get(c, "") for c in COLS}
        f = res.get(t["target_id"])
        if t["action"] != "FETCH":
            r["status"] = t["action"]
            r["robots_result"] = "NOT_CHECKED (" + BLOCK_NOTE.get(t["action"], "not contacted") + ")"
            if t["fallback_url"]:
                r["attempts"] = f"would use: {t['url']} ; alternative: {t['fallback_url']}"
        elif f is None:
            r["status"] = "NOT_RUN"
        else:
            r["robots_result"] = " | ".join(f"{a.get('url','').split('/')[2] if a.get('url') else ''}: {a.get('robots','')}"
                                            for a in f["attempts"])
            r["attempts"] = " || ".join(f"{a['status']} {a.get('url','')}" + (f" (from {a['redirect_from']})" if a.get("redirect_from") else "")
                                        for a in f["attempts"])
            if f["status"] == "DOWNLOADED":
                p = Path(f["path"])
                sha = hashlib.sha256(p.read_bytes()).hexdigest()
                assert sha == f["sha256"], p
                r.update(status="DOWNLOADED", url=f["url"], sha256=sha, bytes=f["bytes"], pages=f.get("pages") or "",
                         completeness=f["completeness"], relation_to_existing_copy=f["relation"], stored_path=str(p),
                         md5=f["md5"], retrieved_at=f["retrieved_at"], host=f["url"].split("/")[2])
            else:
                st = f["status"]
                if st == "REDIRECT_TO_NON_ALLOW_LISTED_HOST":
                    st = "BLOCKED_HOST_NOT_ALLOW_LISTED (redirect target)"
                r["status"] = st
                r["completeness"] = ""
        out.append(r)
    with open(ACQ / "ACQUISITION_MANIFEST.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    c = Counter((r["workstream_target"], r["status"].split(" (")[0], r["relation_to_existing_copy"].split(":")[0]) for r in out)
    for k, v in sorted(c.items()):
        print(v, k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
