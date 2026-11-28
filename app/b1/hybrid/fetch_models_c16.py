"""C16 S3-E: fetch larger candidate dense models (read-only, pinned revisions) and write/verify per-model manifests.

Same procedure as fetch_models_c15.py (public files only, no token sent, each LFS file checked against the SHA-256 the
Hub publishes for the pinned revision). Candidates: permissive licence (MIT / Apache-2.0), multilingual (the library
holds Hindi), and an int8 ONNX published by the model's owner or a well-known converter, because the fp32 large models
(2.2 GB of weights) do not fit the RAM left on the shared host. Models are NOT committed.

  python -I hf_ipv4.py fetch_models_c16.py <dest-root> [name ...] [--verify-only]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_models_c15 as c15  # noqa: E402

c15.MODELS = {
    "multilingual-e5-large": {
        "repo": "intfloat/multilingual-e5-large", "revision": "3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3",
        "license": "mit", "role": "dense embedding model (1024-d, XLM-R vocabulary, mean pooling); owner's int8 ONNX",
        "files": ["onnx/model_qint8_avx512_vnni.onnx", "onnx/sentencepiece.bpe.model", "onnx/tokenizer.json", "onnx/config.json"],
    },
    "bge-m3": {
        "repo": "Xenova/bge-m3", "revision": "4de13258303883538bd53b696b452bf8099f0858",
        "license": "mit", "role": "dense embedding model (1024-d, XLM-R vocabulary, CLS pooling); int8 ONNX conversion of BAAI/bge-m3 (MIT)",
        "files": ["onnx/model_int8.onnx", "sentencepiece.bpe.model", "tokenizer.json", "config.json"],
    },
    "snowflake-arctic-embed-m-v2.0": {
        "repo": "Snowflake/snowflake-arctic-embed-m-v2.0", "revision": "95c2741480856aa9666782eb4afe11959938017f",
        "license": "apache-2.0", "role": "dense embedding model (768-d, multilingual, CLS pooling); owner's int8 ONNX",
        "files": ["onnx/model_int8.onnx", "tokenizer.json", "config.json"],
    },
}

if __name__ == "__main__":
    sys.exit(c15.main())
