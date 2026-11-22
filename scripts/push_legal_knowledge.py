"""Publish curated, text-only legal-knowledge data to the *private* canonical HF dataset.

Does not change crawler-produced data/ or upload MML binary originals.
Requires huggingface_hub and an already authorized write login / HF_TOKEN.
"""
import argparse
from pathlib import Path
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
DATASET = "hariomahlawat/mimamsa-corpus"
BASE = ROOT / "legal_knowledge"
SUBDIRS = ("reconciliation", "verification_batches")
FILES = ("README.md", "DATA_AUTHORITY.md")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    payload = []
    for folder in SUBDIRS:
        path = BASE / folder
        if path.is_dir():
            payload.extend(sorted(f for f in path.rglob("*") if f.is_file()))
    payload.extend(BASE / name for name in FILES if (BASE / name).is_file())
    if not payload:
        raise RuntimeError("No local legal knowledge files found")
    for f in payload:
        print(f"STAGE {f.relative_to(ROOT).as_posix()} ({f.stat().st_size} bytes)")
    if args.dry_run:
        print(f"DRY RUN: {len(payload)} files")
        return

    api = HfApi()
    info = api.repo_info(repo_id=DATASET, repo_type="dataset")
    if not info.private:
        raise RuntimeError("Destination dataset is not private; refusing upload")
    # Additive operations only. No wildcard deletion or replacement of crawler folders.
    from huggingface_hub import CommitOperationAdd
    operations = [
        CommitOperationAdd(
            path_in_repo=f.relative_to(ROOT).as_posix(),
            path_or_fileobj=str(f)
        ) for f in payload
    ]
    result = api.create_commit(
        repo_id=DATASET, repo_type="dataset", operations=operations,
        commit_message="Stage curated military-law legal review data (not JAG approved)",
    )
    print(f"COMMIT {result.commit_oid}")
    # Verify each uploaded object's content from the remote dataset after commit.
    import hashlib
    from huggingface_hub import hf_hub_download
    for f in payload:
        remote = hf_hub_download(repo_id=DATASET, repo_type="dataset",
                                 filename=f.relative_to(ROOT).as_posix(),
                                 revision=result.commit_oid, force_download=True)
        local_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        remote_hash = hashlib.sha256(Path(remote).read_bytes()).hexdigest()
        if local_hash != remote_hash:
            raise RuntimeError(f"Read-back SHA-256 mismatch: {f}")
    print(f"VERIFIED {len(payload)} files on private Hugging Face")

if __name__ == "__main__":
    main()
