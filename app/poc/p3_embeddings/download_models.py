"""Resolve and download the candidate ONNX models; write models.lock.json (revision + sha256 of every artefact)."""
import hashlib, json, sys
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download
sys.path.insert(0, str(Path(__file__).resolve().parent))
from models import MODELS

out = Path(sys.argv[1]); lock_path = Path(__file__).resolve().parent / "models.lock.json"
lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
api = HfApi()
for key, (repo, onnx, *_rest) in MODELS.items():
    info = api.model_info(repo, revision=lock.get(key, {}).get("revision"))
    rev = info.sha
    names = {s.rfilename for s in info.siblings}
    files = [onnx] + [f for f in ("tokenizer.json", "tokenizer_config.json", "config.json", "special_tokens_map.json", "LICENSE", "README.md") if f in names]
    ent = {"repo": repo, "revision": rev, "license_card": (info.card_data or {}).get("license"), "files": {}}
    for f in files:
        p = hf_hub_download(repo, f, revision=rev, local_dir=out / key)
        h = hashlib.sha256(Path(p).read_bytes()).hexdigest()
        ent["files"][f] = {"sha256": h, "bytes": Path(p).stat().st_size}
    lock[key] = ent
    print(key, rev, flush=True)
lock_path.write_text(json.dumps(lock, indent=1))
