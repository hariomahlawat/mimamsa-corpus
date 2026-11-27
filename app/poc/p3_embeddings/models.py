"""Candidate local embedding models (ONNX, CPU). Exact revisions + artefact sha256 are resolved once and frozen in models.lock.json."""

MODELS = {
    # key: (repo, onnx_path, pooling, query_prefix, passage_prefix, dim)
    "bge-small-en-v1.5": ("BAAI/bge-small-en-v1.5", "onnx/model.onnx", "cls",
                          "Represent this sentence for searching relevant passages: ", "", 384),
    "bge-base-en-v1.5": ("BAAI/bge-base-en-v1.5", "onnx/model.onnx", "cls",
                         "Represent this sentence for searching relevant passages: ", "", 768),
    "e5-small-v2": ("intfloat/e5-small-v2", "model.onnx", "mean",
                    "query: ", "passage: ", 384),
    "e5-base-v2": ("intfloat/e5-base-v2", "onnx/model.onnx", "mean",
                   "query: ", "passage: ", 768),
    "arctic-embed-s": ("Snowflake/snowflake-arctic-embed-s", "onnx/model.onnx", "cls",
                       "Represent this sentence for searching relevant passages: ", "", 384),
    "arctic-embed-m-v1.5": ("Snowflake/snowflake-arctic-embed-m-v1.5", "onnx/model.onnx", "cls",
                            "Represent this sentence for searching relevant passages: ", "", 768),
    "all-MiniLM-L6-v2": ("sentence-transformers/all-MiniLM-L6-v2", "onnx/model.onnx", "mean",
                         "", "", 384),
    "nomic-embed-text-v1.5": ("nomic-ai/nomic-embed-text-v1.5", "onnx/model.onnx", "mean",
                              "search_query: ", "search_document: ", 768),
}
