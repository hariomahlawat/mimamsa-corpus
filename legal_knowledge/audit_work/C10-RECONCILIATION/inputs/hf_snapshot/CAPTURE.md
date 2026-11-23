# Hugging Face snapshot capture (C10)

**Dataset:** `datasets/hariomahlawat/mimamsa-corpus`, private. Captured on 2026-11-24, read-only.

## What was available
- The Hugging Face MCP connector, authenticated as the owner, could list directories (paths and sizes), stat files and read small text files.
- No Hugging Face token was available to the shell, so the API and CLI returned 401. **No Hugging Face file was downloaded, and no Hugging Face byte was hashed by this audit.**
- The connector does not expose a revision id, so the snapshot is **not pinned to a revision**. The latest Hugging Face commit recorded in any GitHub workflow log is `e1a7fa47…` (2026-11-22 14:49 UTC). See `hf_revision_evidence.json` and `hf_commits_from_logs.tsv`.

## Files
- **`listing_*.tsv`:** one row per Hugging Face file (`FILE`, size, an LFS flag where the connector showed one, path) for `data/raw/*`, `legal_knowledge/`, `schema/`, `reports/` and the root.
  - Large listings were split by directory or filename glob because the connector caps output at about 700 entries.
  - Rows were transcribed by helper agents. Every `data/raw` row was then compared with the pinned GitHub `raw-data` tree by path and size: 4,039 of 4,039 agree. A transcription error would show up as a mismatch.
  - **The LFS flag is unreliable and is not used.**
- **`dir_totals.tsv`:** file totals for `data/meta`, `data/text`, `data/sections/*` and `data/correspondence`, taken from the connector's "showing N of M" counts or from full listings. These are counts only; no per-file comparison was made.
- **`lk_declared_sidecars.tsv`:** sha256, size and source URL declared by the Hugging Face sidecar JSON files of the 8 `legal_knowledge` judgment binaries.
- **`upload_run_remote_verified.tsv`:** sha256 values that GitHub upload jobs logged after reading the file back from Hugging Face, with the Hugging Face revision where the log gives one.
- **`hf_manifest_samples.json`:** the sampled comparison of the Hugging Face `data/` manifests with the GitHub copies.

## Limits stated in every output
- Hugging Face byte integrity is `NOT_CHECKED`.
- Path and size agreement plus a declared hash is not a byte check.
- A full byte-level reconciliation needs a read-only Hugging Face token in the environment, a connector that can download, or the owner running `sha256sum -c data/SHA256SUMS` on a full download. The tool is written so that this evidence can be added as a further input.
