"""Upload user-supplied MML originals to private Mimamsa dataset, after hash verification.

This is an explicit standalone upload, and does NOT run the full crawler checkpoint.
Usage: python scripts/push_mml_originals.py --source-dir /path/to/extracted/originals
Requires: huggingface_hub, authenticated HF write token or 'hf auth login'.
"""
import argparse
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "legal_knowledge" / "manual_sources" / "MML_Originals_Manifest.csv"
REPO = "hariomahlawat/mimamsa-corpus"
PREFIX = "legal_knowledge/manual_sources/originals"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    source_dir = args.source_dir.resolve()
    with MANIFEST.open(newline="", encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    assert len(rows) == 8, "Unexpected manifest count"
    for row in rows:
        filename = row["filename"]
        if Path(filename).name != filename:
            raise ValueError("Unsafe filename")
        source = source_dir / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != row["sha256"] or source.stat().st_size != int(row["bytes"]):
            raise ValueError(f"Original file differs from manifest: {filename}")
        print(f"Verified SHA-256: {filename}: {digest}")
    if args.dry_run:
        print("Dry run complete; no upload")
        return
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi()
    info = api.repo_info(repo_id=REPO, repo_type="dataset")
    if not info.private:
        raise RuntimeError("Refusing upload: destination dataset is not private")
    for row in rows:
        source = source_dir / row["filename"]
        dest = f'{PREFIX}/{row["filename"]}'
        committed = api.upload_file(repo_id=REPO, repo_type="dataset",
                        path_or_fileobj=str(source),
                        path_in_repo=dest,
                        commit_message=f'Archive source original (unverified): {row["filename"]}')
        revision = getattr(committed, "oid", None)
        if not revision:
            raise RuntimeError(f"No commit revision returned for {row['filename']}")
        remote = Path(hf_hub_download(repo_id=REPO, repo_type="dataset",
                                      filename=dest, revision=revision, force_download=True))
        if hashlib.sha256(remote.read_bytes()).hexdigest() != row["sha256"]:
            raise RuntimeError(f"Remote SHA-256 mismatch: {row['filename']}")
        print(f'Uploaded and read-back verified: {row["filename"]}')
    api.upload_file(repo_id=REPO, repo_type="dataset",
                    path_or_fileobj=str(MANIFEST),
                    path_in_repo="legal_knowledge/manual_sources/MML_Originals_Manifest.csv",
                    commit_message="Add original MML provenance and integrity manifest")
    print("VERIFIED 8 original MML binary files on private Hugging Face")

if __name__ == "__main__":
    main()
