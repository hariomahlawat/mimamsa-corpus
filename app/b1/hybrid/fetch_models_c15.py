"""C15 WP2: fetch candidate retrieval models (read-only, pinned revisions) and write/verify per-model manifests.

Candidates were chosen for licence (permissive, offline redistribution allowed), multilingual coverage (the library
holds Hindi) and CPU fit on the development host (i7-10750H, AVX2, no AVX-512 VNNI). Models are NOT committed;
manifests/<name>.json (in git) pin the revision and file hashes, and loaders refuse files whose hashes differ.

  python -I hf_ipv4.py fetch_models_c15.py <dest-root> [name ...] [--verify-only]
Read-only: no HF writes.
"""
import hashlib
import json
import sys
from pathlib import Path

MODELS = {
    "mmarco-mMiniLMv2-L12-H384-v1": {
        "repo": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1", "revision": "1427fd652930e4ba29e8149678df786c240d8825",
        "license": "apache-2.0", "role": "cross-encoder reranker (multilingual, XLM-R vocabulary)",
        "files": ["onnx/model.onnx", "onnx/model_quint8_avx2.onnx", "sentencepiece.bpe.model", "tokenizer.json", "config.json"],
    },
    "multilingual-e5-base": {
        "repo": "intfloat/multilingual-e5-base", "revision": "d128750597153bb5987e10b1c3493a34e5a4502a",
        "license": "mit", "role": "dense embedding model (768-d, XLM-R vocabulary)",
        "files": ["onnx/model.onnx", "onnx/sentencepiece.bpe.model", "onnx/tokenizer.json", "onnx/config.json"],
    },
}
MANIFESTS = Path(__file__).with_name("manifests")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch(m, dest: Path):
    """Public files only, no token sent. Streams resolve/<revision>/<file> following redirects (Xet CDN) with the
    process-wide IPv4 client, then checks each LFS file against the SHA-256 the Hub publishes for that revision."""
    import httpx2
    from huggingface_hub import HfApi
    info = HfApi().model_info(m["repo"], revision=m["revision"], files_metadata=True)
    lfs = {s.rfilename: (s.lfs.sha256 if s.lfs else None) for s in info.siblings}
    with httpx2.Client(transport=httpx2.HTTPTransport(local_address="0.0.0.0", retries=2), follow_redirects=True, timeout=120) as c:
        for f in m["files"]:
            out = dest / f
            out.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://huggingface.co/{m['repo']}/resolve/{m['revision']}/{f}"
            tmp = out.with_suffix(out.suffix + ".part")
            with c.stream("GET", url) as r:
                r.raise_for_status()
                with tmp.open("wb") as fh:
                    for chunk in r.iter_bytes(1 << 20):
                        fh.write(chunk)
            if lfs.get(f) and sha(tmp) != lfs[f]:
                tmp.unlink()
                raise SystemExit(f"{f}: SHA-256 does not match the Hub's LFS metadata at {m['revision']}")
            tmp.replace(out)
            print("  fetched", f, out.stat().st_size)


def main():
    root = Path(sys.argv[1])
    verify_only = "--verify-only" in sys.argv
    names = [a for a in sys.argv[2:] if not a.startswith("--")] or list(MODELS)
    MANIFESTS.mkdir(exist_ok=True)
    rc = 0
    for name in names:
        m = MODELS[name]
        dest = root / name / m["revision"]
        if not verify_only:
            fetch(m, dest)
        got = {f: {"sha256": sha(dest / f), "bytes": (dest / f).stat().st_size} for f in m["files"]}
        mf = MANIFESTS / f"{name}.json"
        if mf.exists():
            want = json.loads(mf.read_text(encoding="utf-8"))["files"]
            bad = [f for f in m["files"] if want.get(f, {}).get("sha256") != got[f]["sha256"]]
            print(name, "verify:", "OK" if not bad else f"MISMATCH {bad}")
            rc |= 1 if bad else 0
        else:
            mf.write_text(json.dumps({k: v for k, v in m.items() if k != "files"} | {"files": got}, indent=1) + "\n", encoding="utf-8")
            print(name, "manifest written", mf)
    return rc


if __name__ == "__main__":
    sys.exit(main())
