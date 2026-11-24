# C12 Hugging Face byte verification (revision-pinned)

- Dataset: `hariomahlawat/mimamsa-corpus` (private), revision **`5524c3d99b6a069249012fecea75093b875a22c7`** (last modified 2026-11-24 12:08:44+00:00).
- Git references: c7 `ad77758d4569ba6aafa955cc7843d874489e10f7`, staging `origin/legal-knowledge/v2.5-staging` at `e0b3e7d2b8c3a1aa78f13ff99b67962534cf7e73`.
- Capture: started 2026-11-24T13:12:27Z, finished 2026-11-24T13:26:24Z; at most 4 concurrent downloads. READ-ONLY: nothing on Hugging Face was changed.

## Result

| Measure | Value |
|---|---|
| files | 15971 |
| bytes_listed | 1990747622 |
| files_downloaded_and_hashed | 15971 |
| bytes_hashed | 1990747622 |
| download_failed | 0 |
| files_needing_retries | 12 |
| byte_verified_server_hash_match | 15971 |
| lfs_files | 2450 |
| ledger_status_rederivation_drift | 0 |

Every file was downloaded from `/resolve/<revision>/<path>` and hashed locally. `BYTE_VERIFIED_SERVER_HASH_MATCH` means that the computed sha256 equals the LFS sha256 (LFS files), or the computed git-blob-sha1 equals the HF oid (other files), and that the size matches.

## Status counts (one file can carry several)

| Status | Files |
|---|---|
| `BYTE_VERIFIED_AND_MATCHES_GIT_AD77758D` | 15689 |
| `BYTE_VERIFIED_SERVER_HASH_MATCH` | 15971 |
| `C5_PACKAGE_SHA256SUMS_MATCH` | 105 |
| `HF_ONLY` | 277 |
| `MANIFEST_CSV_SHA256_LISTED` | 4018 |
| `MANIFEST_CSV_SHA256_NOT_LISTED` | 21 |
| `MATCHES_GITHUB_STAGING` | 89 |
| `MISMATCH_GIT_AD77758D_BLOB` | 5 |
| `NOT_IN_GITHUB_STAGING` | 184 |
| `RAW_FILENAME_SHA256_MATCH` | 4039 |
| `RAW_MANIFEST_GIT_AD77758D_SHA256_MATCH` | 4039 |
| `RAW_MANIFEST_HF_SHA256_MATCH` | 4039 |
| `SHA256SUMS_GIT_AD77758D_MATCH` | 4039 |
| `SHA256SUMS_HF_MATCH` | 4039 |

## Reference files: HF against git `ad77758d`

| File | Identical blob |
|---|---|
| `data/SHA256SUMS` | True |
| `data/manifest.csv` | True |
| `data/raw_manifest.csv` | False |
| `data/relations.jsonl` | True |
| `data/excluded_judgments.jsonl` | True |

- `data/SHA256SUMS`: 4039 entries on HF and 4039 in git; 0 entries differ between them. Mismatches against computed hashes: HF list 0, git list 0.
- `data/raw` filenames: 4039 match the computed sha256 and 0 do not, of 4039 files.
- `data/raw_manifest.csv` differs between HF and git only in its columns: git has `source_aliases`, `on_this_branch` and HF does not. Same raw paths: True; differing cells in the common columns: 0.
- `raw_manifest.csv`: 4039 rows on HF and 4039 in git. Mismatches: 0 (HF) and 0 (git). `manifest.csv`: 4327 rows; 0 of its sha256 values are not present on HF.

## Paths: HF against git `ad77758d`

| Relation | Paths |
|---|---|
| DIFFERENT_BLOB | 5 |
| GIT_ONLY | 42 |
| HF_ONLY | 277 |
| IDENTICAL_BLOB | 15689 |

HF-only paths by prefix: `.gitattributes` 1, `legal_knowledge/DATA_AUTHORITY.md` 1, `legal_knowledge/README.md` 1, `legal_knowledge/crosswalk` 14, `legal_knowledge/curated_originals` 2, `legal_knowledge/full_text_working` 12, `legal_knowledge/gazette_discovery` 1, `legal_knowledge/holding_review` 9, `legal_knowledge/judgment_originals` 13, `legal_knowledge/judgment_sources` 2, `legal_knowledge/judicial_treatment` 6, `legal_knowledge/legal_review` 17, `legal_knowledge/manual_sources` 11, `legal_knowledge/preservation` 107, `legal_knowledge/quality_audit` 9, `legal_knowledge/reconciliation` 8, `legal_knowledge/reference_data` 4, `legal_knowledge/source_acquisition` 1, `legal_knowledge/verification_batches` 55, `reports/phase2_report.md` 1, `reports/relevance.csv` 1, `schema/correspondence.schema.json` 1.

Git-only paths by prefix: `.gitignore` 1, `CLAUDE.md` 1, `PROGRESS.md` 1, `README_RAW_DATA.md` 1, `config/sources.yaml` 1, `crawler/__init__.py` 1, `crawler/__main__.py` 1, `crawler/audit.py` 1, `crawler/cli.py` 1, `crawler/config.py` 1, `crawler/fetch.py` 1, `crawler/http.py` 1, `crawler/indiacode.py` 1, `crawler/plan.py` 1, `crawler/probe.py` 1, `crawler/state.py` 1, `pipeline/__init__.py` 1, `pipeline/schemas.py` 1, `reports/.gitkeep` 1, `requirements.in` 1, `requirements.txt` 1, `snapshots/.gitkeep` 1, `state/.gitkeep` 1, `tests/__init__.py` 1, `tests/fixtures` 15, `tests/test_crawler_foundation.py` 1, `tests/test_indiacode.py` 1, `tests/test_schemas.py` 1.

## `legal_knowledge/` on HF against the GitHub staging branch

Differences are reported without judging which side is right.

- `MATCHES_GITHUB_STAGING`: 89
- `NOT_IN_GITHUB_STAGING`: 184
- Staging-only paths (not on HF): 1174

## `c5_working_store`

- 105 files against 106 `PACKAGE_SHA256SUMS` entries: `C5_PACKAGE_SHA256SUMS_MATCH` 105. Listed but absent on HF: 0. The HF `PACKAGE_SHA256SUMS` equals the C12 copy (`PACKAGE_SHA256SUMS_C12.txt`): True.

## Known incomplete judgments (23)

A file counts as complete only if PyMuPDF opens it AND a `%%EOF` marker is in its last 1,024 bytes.

| Stored sha256 | Path | HF opens | HF %%EOF | HF vs git | Verdict |
|---|---|---|---|---|---|
| `028ce643f09f` | `data/raw/hc/2025/028ce643f09f1cecaad0258387f63acbaf62a99b0ab88a89fa5b423efb474963.pdf` | NO:code=7: Invalid number of pages | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `02e3320fa26f` | `data/raw/hc/2025/02e3320fa26f4fff02f1ca26759f4aa0f879b9be76a74436de8dd25c76a80699.pdf` | NO:FileDataError Failed to open file '<tmpfile>' | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `187bfd9e00f2` | `legal_knowledge/judgment_originals/sci/2025/chandrabhan_sudam_sanap_2025.pdf` | YES | YES | HF_ONLY | HF_ONLY_NO_LOCAL_BYTES_HF_COPY_OPENS_WITH_EOF_RETRIEVED |
| `2137dd14d58a` | `data/raw/hc/2025/2137dd14d58a2c7269e2a36e6d0f00683150e2441d8903c833ca27d7c2cfc9ab.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `268ee3d706ea` | `data/raw/hc/2025/268ee3d706eadcd48f7db0029c28259c248a6114325ab8533156b06f8bdd92a0.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `2c098828c7ba` | `data/raw/hc/2025/2c098828c7bac3e51ef62eceadff4625dddbe91e230616607b4616e15a3e08f9.pdf` | NO:code=7: Invalid number of pages | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `30cf7d583e01` | `data/raw/hc/2025/30cf7d583e0151f35e3e05a5c25dad6df9388ac60b206e203de419e294a25574.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `38bd54ea27ee` | `data/raw/hc/2025/38bd54ea27ee36969e80a3ca0661a68cbeb1e7fdec46eb6cdef31e27519cb74e.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `8189c602ff49` | `data/raw/hc/2026/8189c602ff49bd414c6b33b983fb98070bedc41f9a85338218652ae64db28154.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `88f84411abdb` | `legal_knowledge/judgment_originals/sci/historical/v3.3/ram_sarup_1963.pdf` | YES | YES | HF_ONLY | HF_ONLY_NO_LOCAL_BYTES_HF_COPY_OPENS_WITH_EOF_RETRIEVED |
| `8a4689b542d4` | `data/raw/hc/2025/8a4689b542d4ff57ece6cccb45cb8830944df190d98f2212d987fe15155761d3.pdf` | NO:code=7: Invalid number of pages | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `928d53398c77` | `data/raw/hc/2025/928d53398c7716f84ff7c1ee867f469152bcdf79847511bab62a5e6e8f9f6698.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `adae1b11687f` | `legal_knowledge/judgment_originals/sci/2024/ravishankar_tandon_2024.pdf` | YES | YES | HF_ONLY | HF_ONLY_NO_LOCAL_BYTES_HF_COPY_OPENS_WITH_EOF_RETRIEVED |
| `b1aa2d028bf8` | `data/raw/hc/2025/b1aa2d028bf8282d81fd8262c0b73e6a356f12932f36970641016be42ebf4c6e.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `cce64004ab57` | `legal_knowledge/judgment_sources/third_party_court_document_copies/2016/mani_ram_bhaira_mirror_2016.pdf` | YES | YES | HF_ONLY | HF_ONLY_NO_LOCAL_BYTES_HF_COPY_OPENS_WITH_EOF_RETRIEVED |
| `cda4a7260447` | `data/raw/hc/2025/cda4a72604478d2989393597025bb2a83e93e9821c6eb27fde6c5f7daf07f653.pdf` | NO:code=7: Invalid number of pages | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `d992ac2bb73a` | `data/raw/hc/2025/d992ac2bb73a90d1e2cc1c11a60e53faae290301ad851d94708b79fe43842826.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `e04a2422b792` | `data/raw/hc/2025/e04a2422b7927c2d39b0ccea511a6afebd9c8a36593d7c12fc91c19c29fdf201.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `e81cf875c745` | `data/raw/hc/2025/e81cf875c745b334746e1e30f521d8854cfe514868bc363e6cf491ee456f06e4.pdf` | NO:code=7: Invalid number of pages | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `ed1344e0d571` | `data/raw/hc/2025/ed1344e0d571e662cf43379a3ef3297832c388fbfe685360c7b9993ef59d368c.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `f14d5ae83261` | `data/raw/hc/2025/f14d5ae83261688f5aae839099b8fe3de03a04e9bda6e2f5e2f1f1e1e410abf6.pdf` | NO:FileDataError Failed to open file '<tmpfile>' | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `f841d3fb6761` | `data/raw/hc/2025/f841d3fb6761bd279293822254d0c66000262379a1c9f381a2a507e554b7321c.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |
| `fb634cc630f8` | `data/raw/hc/2025/fb634cc630f8c4e473c9723af855a3d783a3739ec79b37bd6fd9b052cc95ba2b.pdf` | YES | NO | IN_GIT_AD77758D | HF_IDENTICAL_TO_STORED_COPY_ALSO_INCOMPLETE |

HF copies saved to `hf_retrieved_c12/<sha256>/` (`HF_RETRIEVED_CANDIDATES.csv`): 4. HF copies that differ from the stored copy and are complete: 0. The HF-only SC copies had no local bytes at all (C11: `NOT_PROCESSED_BYTES_UNAVAILABLE`). Their HF bytes match the recorded sha256, open in PyMuPDF and end with `%%EOF`, so they were saved as new copies. Passing these checks proves the file is not truncated; it does not prove the text is complete. Nothing was replaced or overwritten.

## Marking scan (PyMuPDF text layer only)

- 4077 PDFs scanned, 4070 opened. 636 contain at least one of the terms (case-insensitive, whole word): confidential 134, for_official_use_only 2, restricted 526, secret 56.
- Marking-like lines (the term in upper case, or FOUO in any case, as a short line of its own; a heuristic): 22 PDFs.
- PDFs with 'For Official Use Only': `data/raw/indiacode/0000/4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14.pdf`, `data/raw/indiacode/0000/68dd1cea126dc5c4c0ebce20fbd1b5ab0a350ef5d77d5f3601046461a1034985.pdf`.
- Known FOUO copy `4284820e...` (RAF 2000) on HF: `data/raw/indiacode/0000/4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14.pdf`.
- Scanned images without a text layer cannot be checked this way. Every hit is listed in `MARKING_HITS.csv` for review. Nothing was changed.

## Discrepancies

26 rows in `DISCREPANCIES.csv`:

- `MANIFEST_CSV_SHA256_NOT_LISTED`: 21
- `MISMATCH_GIT_AD77758D_BLOB`: 5

## Reproduce

```
python tools/hf_verify_c12.py capture --work <tmpdir>   # network; writes the ledger
python tools/hf_verify_c12.py report                    # derives the reports
python tools/hf_verify_c12.py report --check            # regenerates and byte-compares
```

## Coordinator spot-check (independent of the verification author)
The coordinator re-downloaded 30 files at revision `5524c3d9`: 15 LFS and 15 non-LFS, drawn with the seeded sample `c12-owner-spotcheck`. Each was hashed independently. **30 of 30 match the ledger** on SHA-256 and size. `report --check` passes.

## Owner attention (no action taken)
- The FOUO-marked RAF 2000 copy `4284820e…` is already in the **private** HF dataset. This is not publication. Removing or quarantining it would be a deletion or visibility decision, which needs owner approval under `docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md` §3.
- The 4 HF-only SC files open and end with `%%EOF`. They were retrieved to the session working store as candidates. Their HF copies remain the preserved originals.
