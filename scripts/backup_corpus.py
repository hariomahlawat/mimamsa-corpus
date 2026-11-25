"""Owner-run offline backup and restore verification for the private HF corpus (Cycle 13 section 31).

  python scripts/backup_corpus.py create  --revision <sha> --dest <empty dir>
  python scripts/backup_corpus.py verify  --dest <backup dir>          # after copying to owner storage / on restore

The create step downloads every file at a pinned revision and hashes the actual bytes.
- Each LFS file must match its LFS sha256.
- Each non-LFS file must match its git blob id.

It writes SHA256SUMS and BACKUP_MANIFEST.json, recording the revision, the file count, the bytes and each file's
expected and computed hashes.

Access-restricted items (config/restricted_material.json) are EXCLUDED by default and listed in the manifest. Routine
operations must not copy them.

The verify step recomputes every hash from the stored bytes and compares the result with the manifest. Run it on the
restored copy; a backup counts as verified only after this step passes on the owner's storage.

Authentication for huggingface.co comes from the environment, for example an injected network secret or HF_TOKEN. This
tool never prints credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from restricted_material import is_restricted  # noqa: E402

REPO = "hariomahlawat/mimamsa-corpus"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(p: Path) -> str:
    h = hashlib.sha1()
    h.update(b"blob %d\0" % p.stat().st_size)
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def plan(api, revision: str, only_prefix: str | None = None):
    items, excluded = [], []
    for e in api.list_repo_tree(REPO, repo_type="dataset", recursive=True, revision=revision,
                                path_in_repo=only_prefix.rstrip("/") if only_prefix else None):
        if getattr(e, "size", None) is None:
            continue
        lfs = getattr(e, "lfs", None)
        rec = {"path": e.path, "size": e.size, "lfs_sha256": getattr(lfs, "sha256", None) if lfs else None,
               "git_oid": getattr(e, "blob_id", None)}
        (excluded if is_restricted(sha256=rec["lfs_sha256"], path=e.path) else items).append(rec)
    return items, excluded


def create(revision: str, dest: Path, only_prefix: str | None = None) -> int:
    from huggingface_hub import HfApi, hf_hub_download
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        print("destination must be empty", file=sys.stderr)
        return 2
    api = HfApi()
    if not api.dataset_info(REPO).private:
        print("dataset is not private; refusing", file=sys.stderr)
        return 2
    items, excluded = plan(api, revision, only_prefix)
    data = dest / "data"
    bad = []
    for i, rec in enumerate(items, 1):
        p = Path(hf_hub_download(REPO, rec["path"], repo_type="dataset", revision=revision, local_dir=data))
        rec["computed_sha256"] = sha256_file(p)
        ok = (rec["computed_sha256"] == rec["lfs_sha256"]) if rec["lfs_sha256"] else (git_blob_sha1(p) == rec["git_oid"])
        ok = ok and p.stat().st_size == rec["size"]
        rec["status"] = "BYTE_VERIFIED" if ok else "MISMATCH"
        if not ok:
            bad.append(rec["path"])
        if i % 500 == 0:
            print(f"{i}/{len(items)}", flush=True)
    cache = data / ".cache"
    if cache.exists():  # hf local_dir metadata; not part of the backup
        import shutil
        shutil.rmtree(cache)
    (dest / "SHA256SUMS").write_text("".join(f"{r['computed_sha256']}  data/{r['path']}\n" for r in items), encoding="utf-8")
    manifest = {"repo": REPO, "revision": revision, "only_prefix": only_prefix, "files": len(items), "bytes": sum(r["size"] for r in items),
                "mismatches": bad, "excluded_restricted": excluded, "items": items}
    (dest / "BACKUP_MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({"revision": revision, "files": len(items), "bytes": manifest["bytes"], "mismatches": len(bad),
                      "excluded_restricted": len(excluded)}))
    return 1 if bad else 0


def verify(dest: Path) -> int:
    m = json.loads((dest / "BACKUP_MANIFEST.json").read_text(encoding="utf-8"))
    bad = []
    if m.get("mismatches"):                # create already found bytes that did not match HF: never a valid backup
        bad.extend(m["mismatches"])
    for r in m["items"]:
        p = dest / "data" / r["path"]
        if r.get("status") != "BYTE_VERIFIED" or not p.is_file() or p.stat().st_size != r["size"]:
            bad.append(r["path"]); continue
        h = sha256_file(p)
        expected_ok = (h == r["lfs_sha256"]) if r.get("lfs_sha256") else (git_blob_sha1(p) == r.get("git_oid"))
        if h != r["computed_sha256"] or not expected_ok:   # recheck against the HF-declared identity too (review F03)
            bad.append(r["path"])
    bad = sorted(set(bad))
    extra = {str(p.relative_to(dest / "data")).replace(os.sep, "/") for p in (dest / "data").rglob("*") if p.is_file()} - {
        r["path"] for r in m["items"]}
    print(json.dumps({"revision": m["revision"], "files": len(m["items"]), "failed": len(bad), "unexpected_files": len(extra)}))
    for x in bad[:20]:
        print("FAILED", x)
    return 0 if not bad and not extra else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create"); c.add_argument("--revision", required=True); c.add_argument("--dest", required=True, type=Path)
    c.add_argument("--only-prefix", help="back up only paths under this prefix (testing or partial backups)")
    v = sub.add_parser("verify"); v.add_argument("--dest", required=True, type=Path)
    a = ap.parse_args(argv)
    return create(a.revision, a.dest, a.only_prefix) if a.cmd == "create" else verify(a.dest)


if __name__ == "__main__":
    sys.exit(main())
