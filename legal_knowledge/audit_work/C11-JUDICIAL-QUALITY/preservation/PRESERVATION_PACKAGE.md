# C11 Priority Zero: preservation package for the 48 working-store-only registered copies

**Status: VERIFIED IN PLACE; NOT YET PRESERVED.** All 48 copies exist and re-hash equal to their registered SHA-256. They are still held only in a temporary session working store, which can be cleared at any time. **No authorised persistent destination was available to this session**, so no transfer was made. This package is the owner-action package required by the assignment, §3.2.

## 1. What was verified (reproducible: `tools/preservation_c11.py --check`)
| Check | Result |
| --- | --- |
| Copies enumerated (C10 `MISSING_SOURCE_EVIDENCE.csv`, kind `REGISTERED_COPY_BYTES_NOT_IN_CANONICAL_STORE`) | 48 |
| Files present at their registered working-store path | 48 |
| Re-hashed SHA-256 equal to the register | **48 of 48**; size equal to the register in every row (`size_matches_register`) |
| Total bytes | 37,312,132 |
| Identical bytes in any git object of the local repository object store (the fetched branches; the clone is shallow at `ad77758d`, so older history was not checked) | **0** |
| Identical bytes in the Hugging Face listing captured by C10 | **0** |
| Access marking in the C5 master register | none recorded as a marking; the register value is empty or `NOT_OBSERVED_OR_NOT_CHECKED` |
| Printed-marking scan of every text page (`MARKING_SCAN.csv`) | 34 hits, all ordinary word use (e.g. "confidential reports", "restricted to") or blank-form text (Army Rules Appendix III "Form of Delay Report"). No document-level restriction marking was found **on pages with a text layer**. **73 pages in 17 copies have no text layer and were not scanned; 3 copies are image-only** (per-copy `printed_marking_scan` and `pages_without_text_layer`). Those pages need a visual check before any publication. |

Composition: 31 P0 statutory items (Army Act and Army Rules amendment Gazettes, the Army Act 37 of 1992 copies, the 1954 Army Rules Gazette; per-item titles in `PRESERVATION_INVENTORY.csv`), 1 P1, 2 P2, and 14 Supreme Court judgments.

**Six copies carry KB exact-anchor rows, 47 rows in total.** These are:
- `C5-SRC-P0-ARMY-RULES-1954~C1` (`c5ef95a9`), with **42** anchor rows;
- one anchor row each for Prithi Pal Singh Bedi, Anvar, Arjun, Jasbir and Parashotam.

The master register gives a source URL for only 2 of the 48. Re-acquisition is therefore **not** a dependable fallback: the bytes in hand are the evidence.

## 2. Why nothing was transferred
| Candidate destination | Assessment |
| --- | --- |
| Hugging Face dataset `hariomahlawat/mimamsa-corpus` | The canonical store. Uploading needs owner approval (Cycle 11 §20), and the connector here is read-only. |
| GitHub `raw-data` branch | A source branch. Changes are not authorised. |
| A new commit on a development branch | It would put 37 MB of source PDFs into git history permanently, and removal would need history rewriting, which is not authorised. Git is also not an approved preservation store for source documents. |
| Session scratchpad | Ephemeral. This is the risk being reported. |

## 3. Owner actions (in order)
1. **Approve a destination.** Recommended: the Hugging Face dataset, under a new folder such as `legal_knowledge/preservation/c5_working_store/<sha256[:2]>/<sha256>/<original filename>`, with a `.meta.json` sidecar per file. The dataset is private and access-controlled, and it is already the canonical store.
2. **While this session's working store still exists,** run `preservation/stage_and_verify.sh <store> <empty dir>`. It stages byte-identical copies with their original filenames and sidecars, and verifies all 48 hashes against `SOURCE_MANIFEST.sha256`. A copy of the working store can be taken at the same time.
3. **Upload the staged directory** with the owner's own credentials. This is not done here.
4. **Verify the hosted bytes.** Download into a fresh directory and run `sha256sum -c` against `SOURCE_MANIFEST.sha256` (paths adjusted), or compare with `STAGED_SHA256SUMS`. **Preservation is complete only after this hosted-byte check passes.**
5. **Then** register the new hosted path in the next C5 register revision (`held_paths`), through a reviewed change. The C10 preservation risk (274 citation items, all 42 anchors) closes only at that point.

## 4. Recovery procedure if the working store is lost before step 2
- Every one of the 48 is identified here by its SHA-256, size, original working-store path, title, source id and provenance excerpt.
- A copy obtained from anywhere (an earlier download, a colleague, an official site) can be accepted only if its SHA-256 equals the registered value. A different file is a different copy, and it would need new registration and new page-equivalence review. It can **never** silently carry the existing exact anchors.

## 5. Not done, and why
- No upload, synchronisation, deletion, modification or recompression of any file.
- No change to registers or anchors.
