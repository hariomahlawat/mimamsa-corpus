"""Checkpoint to Hugging Face: upload the corpus data to a PRIVATE dataset repository.

Needs an access token with write permission: the environment variable HF_TOKEN, or a login stored
by `hf auth login`. Without one this script does nothing and says so (exit code 2).

What goes up (everything under data/ that is part of the corpus):
  data/raw/<source>/<year>/   raw files as served (rejected judgments are already deleted locally)
  data/meta, data/sections, data/text, data/correspondence, data/relations.jsonl, manifests,
  data/excluded_judgments.jsonl
Uploads are made folder by folder so that each commit stays a manageable size, and a file removed
locally (a judgment later rejected) is removed from the repository too.

    HF_TOKEN=... python scripts/push_hf.py "checkpoint message" [--repo owner/name] [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_REPO = "hariomahlawat/mimamsa-corpus"
SMALL = ["meta", "sections", "text", "correspondence"]
FILES = ["relations.jsonl", "manifest.csv", "excluded_judgments.jsonl", "raw_manifest.csv", "SHA256SUMS", "README.md"]

CARD = """---
license: other
pretty_name: Mimamsa corpus (Indian military law)
---
# Mimamsa corpus

Central data repository for the Mimamsa application. Code, schemas and reports are on GitHub:
[hariomahlawat/mimamsa-corpus](https://github.com/hariomahlawat/mimamsa-corpus) (private); its
`raw-data` branch holds a second, size-limited copy of this data.

Private working copy of a corpus of public Indian military-law documents: Acts and subordinate
legislation from India Code, and judgments about the armed forces. Built by the crawler and
pipeline in the project's code repository; every file is traceable through `data/raw_manifest.csv`
(source address, retrieval time, SHA-256).

- `data/raw/`: files exactly as served by the source.
- `data/meta/`, `data/sections/`, `data/text/`: metadata records, section records, extracted text.
- `data/correspondence/`: old-code/new-code section tables.
- `data/excluded_judgments.jsonl`: judgments removed as not about the armed forces (log only).
- `schema/`: the JSON Schemas every record validates against (copied from the code repository).
- Verify after download: `sha256sum -c data/SHA256SUMS`.

Sources include third-party open data (AWS Open Data court-judgment buckets, CC-BY-4.0, P. Vanga /
Dattam Labs). Some documents carry access markings; see `access_marking` in their metadata.
Keep this repository private.
"""


def write_manifest() -> int:
    """data/raw_manifest.csv and data/SHA256SUMS for the raw files that exist locally."""
    conn = sqlite3.connect(f"file:{ROOT / 'state' / 'crawl.sqlite'}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""SELECT f.sha256, f.raw_path, f.bytes, f.content_type, f.retrieved_at, f.first_url,
                                  u.doc_id_hint, u.meta FROM files f JOIN urls u ON u.url = f.first_url
                           ORDER BY f.raw_path""").fetchall()
    conn.close()
    local = [r for r in rows if (ROOT / r["raw_path"]).exists()]
    with (DATA / "raw_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sha256", "raw_path", "bytes", "content_type", "retrieved_at", "source_url", "doc_id",
                    "parent_doc_id", "category", "title", "original_filename"])
        for r in local:
            m = json.loads(r["meta"] or "{}")
            w.writerow([r["sha256"], r["raw_path"], r["bytes"], r["content_type"], r["retrieved_at"], r["first_url"],
                        r["doc_id_hint"] or "", m.get("parent_doc_id", ""), m.get("category", ""), m.get("title", ""),
                        m.get("filename", "")])
    with (DATA / "SHA256SUMS").open("w", encoding="utf-8") as fh:
        for r in local:
            fh.write(f"{r['sha256']}  {r['raw_path']}\n")
    return len(local)


def plan() -> list[tuple[Path, str]]:
    """(local folder, path in repo) for each upload step: one per raw year-folder, one per record folder."""
    steps = []
    raw = DATA / "raw"
    if raw.exists():
        for source in sorted(p for p in raw.iterdir() if p.is_dir()):
            for year in sorted(p for p in source.iterdir() if p.is_dir()):
                if any(year.iterdir()):
                    steps.append((year, f"data/raw/{source.name}/{year.name}"))
    for name in SMALL:
        if (DATA / name).exists():
            steps.append((DATA / name, f"data/{name}"))
    return steps


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("message", nargs="?", default="manual")
    ap.add_argument("--repo", help="owner/name of the dataset repository (default: hariomahlawat/mimamsa-corpus)")
    ap.add_argument("--dry-run", action="store_true", help="show what would be uploaded; no token needed")
    ap.add_argument("--only", action="append", metavar="PATH", help="upload only repo paths starting with this (repeatable)")
    args = ap.parse_args(argv)

    n_raw = write_manifest()
    steps = [s for s in plan() if not args.only or any(s[1].startswith(o) for o in args.only)]
    if args.dry_run:
        for folder, dest in steps:
            files = [p for p in folder.rglob("*") if p.is_file() and p.name != ".gitkeep"]
            print(f"{dest}: {len(files)} files, {sum(p.stat().st_size for p in files) / 1e6:.1f} MB")
        print(json.dumps({"dry_run": True, "raw_files": n_raw, "steps": len(steps)}))
        return 0
    from huggingface_hub import HfApi, get_token
    token = os.environ.get("HF_TOKEN") or get_token()         # env variable, or a stored `hf auth login`
    if not token:
        print("No Hugging Face token: nothing uploaded. Set HF_TOKEN or run `hf auth login` with a write token.")
        return 2
    api = HfApi(token=token)
    repo = args.repo or DEFAULT_REPO                         # no whoami call: that endpoint is tightly rate-limited
    api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    (DATA / "README.md").write_text(CARD, encoding="utf-8")
    uploaded = 0
    for folder, dest in steps:
        api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(folder), path_in_repo=dest,
                          ignore_patterns=[".gitkeep", "*.part"], delete_patterns=["*"],
                          commit_message=f"{dest} — {args.message}")
        uploaded += 1
    api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(DATA), path_in_repo="data",
                      allow_patterns=[f for f in FILES if f != "README.md"], commit_message=f"manifests — {args.message}")
    api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(ROOT / "schema"), path_in_repo="schema",
                      commit_message=f"schema — {args.message}")
    api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(ROOT / "reports"), path_in_repo="reports",
                      allow_patterns=["relevance.csv", "phase2_report.md"], commit_message=f"reports — {args.message}")
    api.upload_file(repo_id=repo, repo_type="dataset", path_or_fileobj=str(DATA / "README.md"), path_in_repo="README.md",
                    commit_message=f"dataset card — {args.message}")
    (DATA / "README.md").unlink(missing_ok=True)
    print(json.dumps({"repo": repo, "private": True, "raw_files": n_raw, "folders_uploaded": uploaded}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
