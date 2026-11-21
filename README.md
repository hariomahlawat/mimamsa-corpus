# Mimamsa corpus

Crawler and processing pipeline that collect public Indian military-law documents (Acts, rules,
regulations and judgments about the armed forces) into a versioned repository with metadata, for an
offline search and RAG application. The brief is in `CLAUDE.md`; the work log is `PROGRESS.md`.

## Where things live

| What | Where |
| --- | --- |
| Code, schemas, configuration, reports | this repository, branch `main` |
| **Data (central copy)**: raw files, metadata, sections, text, relations, manifests | Hugging Face dataset [`hariomahlawat/mimamsa-corpus`](https://huggingface.co/datasets/hariomahlawat/mimamsa-corpus) (private) |
| Data (secondary copy, raw files capped at 10 GB) | this repository, branch [`raw-data`](https://github.com/hariomahlawat/mimamsa-corpus/tree/raw-data) |

The Hugging Face dataset is the complete data store the application should read from. The `raw-data`
branch is a second copy that stops taking judgment PDFs once it reaches its size limit
(`data/raw_manifest.csv` there says which files it holds). Both are written by the same checkpoint
(`scripts/push_hf.py`, `scripts/push_data.py`) and both are private.

Get the data:

```bash
hf download hariomahlawat/mimamsa-corpus --type dataset --local-dir .
```

```bash
sha256sum -c data/SHA256SUMS
```

## Run

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python -m crawler.cli dry-run
```

```bash
.venv/bin/python -m pipeline all
```

Every record validates against the JSON Schemas in `schema/`. Raw files are never modified; all
processed records can be rebuilt from them.
