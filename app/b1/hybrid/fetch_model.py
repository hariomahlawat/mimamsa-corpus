"""Fetch the hybrid-retrieval embedding model (read-only, pinned revision) and verify/record SHA-256.

Model: intfloat/multilingual-e5-small (MIT). Multilingual because the library holds Hindi texts (B1 UX-19, RET-09
requirement PR-06); chosen before any oracle run. The model is NOT committed; MODEL_MANIFEST.json (in git) pins the
revision and file hashes, and the service refuses a model directory whose hashes differ.

  python -I fetch_model.py <dest-root> [--verify-only]
Run through E:\\Mimamsa-Data\\scripts\\hf_ipv4.py where the network needs the IPv4 client. Read-only: no HF writes.
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
FILES = ["onnx/model.onnx", "onnx/tokenizer.json", "onnx/sentencepiece.bpe.model", "onnx/config.json",
         "onnx/special_tokens_map.json", "onnx/tokenizer_config.json"]
MANIFEST = Path(__file__).with_name("MODEL_MANIFEST.json")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    dest = Path(sys.argv[1]) / "multilingual-e5-small" / REVISION
    verify_only = "--verify-only" in sys.argv
    if not verify_only:
        from huggingface_hub import hf_hub_download
        for f in FILES:
            hf_hub_download(REPO, f, revision=REVISION, local_dir=str(dest))
    got = {f: {"sha256": sha(dest / f), "bytes": (dest / f).stat().st_size} for f in FILES}
    if MANIFEST.exists():
        want = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
        bad = [f for f in FILES if want.get(f, {}).get("sha256") != got[f]["sha256"]]
        print("verify:", "OK" if not bad else f"MISMATCH {bad}")
        return 0 if not bad else 1
    MANIFEST.write_text(json.dumps({"repo": REPO, "revision": REVISION, "license": "MIT",
                                    "files": got}, indent=1) + "\n", encoding="utf-8")
    print("manifest written", MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
