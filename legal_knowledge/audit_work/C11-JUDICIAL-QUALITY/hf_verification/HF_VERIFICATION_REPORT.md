# C11 Hugging Face verification report

**Result: INCOMPLETE. No Hugging Face-hosted byte was hashed.** This is a limit of the access available, not a finding of a defect.

## Access actually available
- **The Hugging Face MCP connector** is authenticated as the dataset owner through OAuth, with scopes `read-repos` and `read-mcp`. It can list files, stat them (size, and whether the file is stored in LFS) and read text.
- **It cannot:**
  - return a revision commit id;
  - return a file's LFS object id (which would be the hosted SHA-256);
  - read binary content.
- **The shell has no Hugging Face credential.** None was requested, as the assignment requires.

## Revision
- **Not pinned.** Nothing available exposes a commit id.
- The latest commit recorded in GitHub Actions logs is `e1a7fa47` (2026-11-22 14:49Z), from C10.
- The dataset page reports "Updated: 22 Nov, 2026", which is consistent with that commit.

## What was verified
| Check | Result |
| --- | --- |
| HF `data/SHA256SUMS` against GitHub `raw-data` `ad77758d` | Equal size (614,935 bytes). Identical content at offsets 0, 307,000 and 613,435 (end of file), 1,500 bytes each. **SAMPLED_TEXT_MATCH, not a full comparison** (`hf_capture_c11.json`). |
| GitHub `raw-data` copies | 4,039 of 4,039 re-hashed equal to their declared SHA-256 (C10). |
| HF-only judgments with an identical-hash working copy | 4 of 8 (Virendra Kumar, Navjot Sandhu, N.C. Isaac, P.S. Gill): the local bytes are verified, but **the hosted bytes are not**. |

## Status of every distinct copy (`HF_INTEGRITY_STATUS.csv`; `tools/hf_verify_c11.py --check`)
| Presence | HF status | Copies |
| --- | --- | --- |
| HF and GitHub `raw-data` | DECLARED_HASH_ONLY (HF `SHA256SUMS`; path and size equal) | 4,039 |
| HF only | DECLARED_HASH_ONLY (HF sidecar, or an upload-run log) | 8 |
| HF only (MML `.doc` originals) | PATH_SIZE_MATCH_ONLY | 8 |
| Working store only | UNAVAILABLE on HF | 48 |

**No copy is BYTE_VERIFIED on HF, and no MISMATCH was observed.**

## Needed to finish
Any one of these:
- a read-only Hugging Face token injected into the session environment through the platform's secret mechanism, never pasted into chat or committed;
- an owner-run download of the dataset at a pinned revision, followed by `sha256sum -c data/SHA256SUMS` and a comparison of the result.

With either, `hf_status` can become BYTE_VERIFIED or MISMATCH for every copy, and the revision can be pinned.
