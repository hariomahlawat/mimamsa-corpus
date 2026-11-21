"""Checkpoint: copy the corpus data to the `raw-data` branch and push it.

Pushed: raw files that are still in the corpus (rejected judgments are already deleted), the metadata,
section, text and correspondence records, relations, manifests, and the log of removed judgments.
Uses a separate git worktree (../raw-data-worktree) so the code checkout on `main` is not touched.
Raw files are committed in chunks of about 40 MB and each chunk is pushed on its own.

GitHub is not built for many gigabytes: once the raw files on the branch reach RAW_LIMIT_GB, further
judgment PDFs are NOT pushed (records and text still are) and the manifest says which files are
missing from the branch.

    python scripts/push_data.py "checkpoint message"
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WT = ROOT.parent / "raw-data-worktree"
RAW_LIMIT_GB = 4.0
CHUNK = 40e6
TRAILER = ("\n\nCo-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_01U1on2R5GUDbYwqG6fkFRuN")
IDENT = ["-c", "user.name=Mimamsa", "-c", "user.email=noreply@anthropic.com"]


def git(*args: str, cwd: Path = WT, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


def push() -> bool:
    for attempt in range(4):
        r = git("push", "origin", "raw-data", check=False)
        if r.returncode == 0:
            return True
        time.sleep(2 ** (attempt + 1))
    print("push failed:", r.stderr.strip()[-300:])
    return False


def commit(msg: str) -> bool:
    if not git("status", "--porcelain").stdout.strip():
        return False
    git(*IDENT, "commit", "-qm", msg + TRAILER)
    return True


def main(message: str) -> int:
    if not WT.exists():
        git("fetch", "origin", "raw-data", cwd=ROOT, check=False)
        git("worktree", "prune", cwd=ROOT, check=False)
        git("worktree", "add", str(WT), "raw-data", cwd=ROOT)
    else:
        git("pull", "--ff-only", "origin", "raw-data", check=False)

    # ---- raw files: which exist locally, which are already on the branch
    conn = sqlite3.connect(f"file:{ROOT / 'state' / 'crawl.sqlite'}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    aliases: dict[str, list[str]] = {}
    for a in conn.execute("SELECT sha256, url FROM aliases"):
        aliases.setdefault(a["sha256"], []).append(a["url"])
    rows = conn.execute("""SELECT f.sha256, f.raw_path, f.bytes, f.content_type, f.retrieved_at, f.first_url,
                                  u.doc_id_hint, u.meta, u.discovered_from
                           FROM files f JOIN urls u ON u.url = f.first_url ORDER BY f.raw_path""").fetchall()
    conn.close()
    local = [r for r in rows if (ROOT / r["raw_path"]).exists()]
    wanted = {r["raw_path"] for r in local}
    on_branch = {p.relative_to(WT).as_posix() for p in (WT / "data" / "raw").rglob("*") if p.is_file()}
    for gone in sorted(on_branch - wanted):                       # removed from the corpus since the last push
        (WT / gone).unlink()
    branch_bytes = sum((WT / p).stat().st_size for p in on_branch & wanted)
    limit = RAW_LIMIT_GB * 1e9
    to_copy, held_back = [], []
    for r in local:
        if r["raw_path"] in on_branch:
            continue
        if branch_bytes + r["bytes"] > limit:
            held_back.append(r["raw_path"])
            continue
        branch_bytes += r["bytes"]
        to_copy.append(r)

    # ---- records, text, logs (small): replace wholesale
    data = WT / "data"
    for name in ("meta", "sections", "text", "correspondence"):
        shutil.rmtree(data / name, ignore_errors=True)
        if (ROOT / "data" / name).exists():
            shutil.copytree(ROOT / "data" / name, data / name, ignore=shutil.ignore_patterns(".gitkeep"))
    for name in ("relations.jsonl", "manifest.csv", "excluded_judgments.jsonl"):
        if (ROOT / "data" / name).exists():
            shutil.copy2(ROOT / "data" / name, data / name)
    held = set(held_back)
    with (data / "raw_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sha256", "raw_path", "bytes", "content_type", "retrieved_at", "source_url", "source_aliases",
                    "doc_id", "parent_doc_id", "category", "title", "original_filename", "on_this_branch"])
        for r in local:
            m = json.loads(r["meta"] or "{}")
            w.writerow([r["sha256"], r["raw_path"], r["bytes"], r["content_type"], r["retrieved_at"], r["first_url"],
                        " ".join(aliases.get(r["sha256"], [])), r["doc_id_hint"] or "", m.get("parent_doc_id", ""),
                        m.get("category", ""), m.get("title", ""), m.get("filename", ""),
                        "no (size limit)" if r["raw_path"] in held else "yes"])
    with (data / "SHA256SUMS").open("w", encoding="utf-8") as fh:
        for r in local:
            if r["raw_path"] not in held:
                fh.write(f"{r['sha256']}  {r['raw_path']}\n")
    git("add", "-f", "-A", "data")
    ok = True
    if commit(f"Checkpoint: records and text — {message}"):
        ok = push()

    # ---- raw files in chunks
    group, size, parts = [], 0.0, 0
    def flush():
        nonlocal group, size, parts, ok
        if not group:
            return
        git("add", "-f", *group)
        parts += 1
        if commit(f"Checkpoint: raw files, part {parts} ({len(group)} files, {size / 1e6:.0f} MB) — {message}"):
            ok = push() and ok
        group, size = [], 0.0
    for r in to_copy:
        src, dst = ROOT / r["raw_path"], WT / r["raw_path"]
        if hashlib.sha256(src.read_bytes()).hexdigest() != r["sha256"]:
            print("hash mismatch, not pushed:", r["raw_path"])
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if group and size + r["bytes"] > CHUNK:
            flush()
        group.append(r["raw_path"])
        size += r["bytes"]
    flush()
    print(json.dumps({"pushed_ok": ok, "raw_files_local": len(local), "raw_files_added": len(to_copy),
                      "raw_files_held_back_for_size": len(held_back), "branch_raw_gb": round(branch_bytes / 1e9, 2)}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "manual"))
