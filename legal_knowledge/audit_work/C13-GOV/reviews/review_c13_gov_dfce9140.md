# Independent review: `claude/c13-gov` at `dfce9140`

- **Reviewer:** an independent Opus instance. I did not write the work under review.
- **Date:** 2026-11-25.
- **Mode:** read-only. Nothing was committed, pushed or uploaded.
- **Scope:** the commits `ea282cbd` (RM-001 register, guard, test and decision note) and `dfce9140` (backup tool, instructions, backup register and task register).

## Verdict

**ACCEPT WITH CHANGES.** I found no P1 issues, 3 P2 issues, 8 P3 issues, and recorded 4 INFO notes. The findings are listed in `review_c13_gov_dfce9140_findings.csv`.

The register covers every hosted **file** copy of the FOUO item: three paths on HF and three paths on `raw-data`. The backup tool excludes those files correctly and detects tampering. There are three problems:

- The register and the decision note miss audit records on staging that contain **verbatim text excerpts** from the item.
- The guard has false negatives that matter for section-level IDs and for Windows paths.
- `verify` would certify a backup whose `create` step reported mismatches.

## Baseline drift

The HF head has moved beyond the brief's baseline. It is now `9e3cf9868a5d553cd6218ed5ac51c383560bbf0b`, the A7 commit of 2026-11-25 10:31Z, with 16,171 files.

I checked `3864faf3` independently: 16,041 files and 1,998,897,965 bytes. This matches the instructions' figure of "about 2.0 GB at revision 3864faf3, for 16,041 files".

All checks below were run at `9e3cf986` unless stated otherwise.

## 1. Restriction coverage (measured)

| Location | Result |
| --- | --- |
| HF head `9e3cf986`, full `list_repo_tree` | Exactly 3 files match by path or hash: `data/raw/indiacode/0000/4284820e….pdf` (LFS sha256 matches the source), `data/meta/regs-…-2000.json` and `data/text/regs-…-2000.txt`. I re-downloaded the meta and text files: their sha256 values are `212ac873…` and `f26d3de7…`, which match RM-001. I deleted both downloaded copies after hashing. No `data/sections/` entry exists for this doc_id. |
| HF history | I sampled every 40th commit plus the oldest. The meta and text blob ids are the same in every sampled revision (`fe2683f7`, `359fe512`), so there are no other versions to list. The files first appear between `35295f5e` and `94aa1d0f`, both dated 2026-11-21. |
| HF aggregate files (447 non-per-document files downloaded and grepped) | The item is referenced, as metadata only and without text, in these files: `data/manifest.csv` (line 3939), `data/raw_manifest.csv`, `data/SHA256SUMS`, `data/relations.jsonl` (an `implements` edge to act-air-force-1950), `reports/phase2_report.md` (2 lines, including the FOUO marking line) and `.gitattributes`. `legal_knowledge/preservation/c5_working_store/README.md` says only that the item is not included. No HF file under `legal_knowledge/` (`full_text_working`, holdings, `judgment_originals_derived` and so on) carries the doc_id, the hash or the title. |
| c7 `ad77758d` | The tree has exactly the 3 paths. Each path has a single version in all history, added at `ad77758d`. The same item is referenced in `manifest.csv`, `raw_manifest.csv`, `SHA256SUMS` and `relations.jsonl`. `origin/raw-data` is `ad77758d`. |
| main `21de3531` | No hits. |
| staging `a4c0c382` (inherited by all `claude/c13-*` branches) | 23 audit files reference the item. Most of them carry only the hash, path and title. **Two of them contain verbatim text from the document:** `C12-CONSOLIDATION/hf_verification_c12/MARKING_HITS.csv` (row 482: five context excerpts from pp. 1, 50 and 125) and `C10-RECONCILIATION/workstreams/statutory/readings_c10.csv` (row `C10R-RAF-01`: the page-1 header quoted). In addition, `C12-CONSOLIDATION/forms_registry` lists the item as source `RAF2000-C7`: `SOURCE_COVERAGE.csv` COV-26 and `SUMMARY.json`, which records 43 unregistered heading hits as counts only. `forms_registry` is an `exclude_from` scope in RM-001. |
| C13 branches (all 12) | Only deny-list entries, reviews and tool constants. `claude/c13-b-poc` `p2_corpus_stats.json` records the item as excluded from the P2 index. I probed every branch, staging and `origin/*` for seven distinctive sentences from deep in the FOUO text. They occur only in `raw-data:data/text/regs-…-2000.txt`. No C12 or C13 output contains extracted body text, outcomes or holdings for this doc_id. This is expected, because it is a regulations document and not a judgment. |
| Session scratch (not hosted) | `scratchpad/c13/a1_work/c7meta/data/meta/regs-…-2000.json` is a local copy of a restricted derivative. The A1 snapshot of the register is byte-identical to `config/restricted_material.json` at `dfce9140`. |

**Conclusion.** RM-001's `hosted_paths` is complete for files. It does not list the reference and excerpt records described above (F01, F04). The decision note's statement that "earlier audit records cite it by sha256; they do not contain its text" is inaccurate (F01).

## 2. Guard robustness (measured, `guard_probe_out.txt`)

**False negatives:**
- **Section-level doc_id `…-2000#s5`** (F02). The B-app contract (`claude/c13-b-app:app/contract/README.md` §4) states that matching "follows `scripts/restricted_material.py::is_restricted` … section-level `#s…` ids inherit". The guard does not do this, so the planned parity test will diverge. Section records are a planned derivative under CLAUDE.md.
- **Case variants** (F02). An upper-case doc_id is missed. So are upper-case Windows paths (`C:\CORPUS\DATA\TEXT\REGS-….TXT`) and upper-case hashes inside paths. This matters because the app target is Windows, where the file system ignores case.
- **Format variants** (F02). A hash with surrounding whitespace or a `sha256:` prefix is missed. So are a percent-encoded doc_id (`regs%2Dregulations…`), a vault path split as `ab/cdef…`, and the India Code source URL.

**Passes:** an upper-case sha argument, mixed-case Windows paths written with backslashes, absolute paths, `./` prefixes, percent-encoded slashes (because the guard matches substrings), full HF resolve URLs, the `data/sections/<doc_id>/` path and the derived hashes.

**False positives:** any path that contains the doc_id as a substring, such as a hypothetical `…-2000-corrigendum.txt`, is restricted. This errs on the safe side and is acceptable. I found no risky false positives: `act-air-force-1950` and a `…air-force-1964` path are not matched.

**Related issue:** `filter_unrestricted` reads the `doc_id` key by default. Relation records use the keys `source_doc_id` and `target_doc_id`, so the RAF `implements` edge would pass through a default call (F04).

The repository test still passes: 3 passed.

## 3. Decision note

**Verified against the records:**
- the source URL, the retrieval time (2026-11-21T14:33:04Z), the sha256 value and the size of 5,075,455 bytes;
- the derived hashes;
- that the item is held on HF at head and in history, and on `raw-data` `ad77758d`;
- that the Navy `68dd1cea` hit is `TERM_IN_RUNNING_TEXT` in MARKING_HITS.

**Inaccuracies and omissions:**
- "row 3939" is the file line number. It is data row 3938 (P3, F06).
- The statement "earlier audit records … do not contain its text" is wrong (P2, F01).
- The note does not record the page-1 legend, which says the information "is not to be communicated … to the Press or to any person not holding an official position in the service of the Government of India". This printed restriction is material to the owner's decision (P3, F05).

**Legal conclusions.** The note draws none. Its framing is appropriately conditional.

**Option implications:**
- **Option C** does not mention what would remain after the three paths are deleted (F05):
  - the aggregate rows (manifest, raw_manifest, SHA256SUMS, relations edge, phase2 report);
  - the staging excerpts.
- **Option D** misses several points (F05):
  - An HF history squash alone may not purge LFS objects from storage. Purging may also require deleting the LFS files themselves.
  - A GitHub history rewrite would have to cover the staging branch as well, because of the excerpts.
  - Cached refs and pull-request refs persist until GitHub support purges them.
- **Options A and B** are described accurately.

## 4. Backup tool

**Code review findings:**
- **Hashes verified.** For LFS files, the tool compares the sha256 of the downloaded bytes with the LFS sha256. For non-LFS files, it compares a recomputed git blob SHA-1 with the tree's `blob_id`. It also checks the size. Both checks are correct.
- **Restricted items.** They are filtered at plan time by LFS sha256 and path, so they are never downloaded. I called `plan()` on the full tree at `9e3cf986`: it returns 16,168 items (2,022,912,932 bytes) and excludes exactly the 3 RM-001 paths. Per-prefix plans for `data/raw/indiacode/0000`, `data/text` and `data/meta` each exclude the expected single file.
- **Defects:**
  - **F03 (P2).** `verify` compares only against the `computed_sha256` recorded in the manifest. It ignores `mismatches` and each item's `status`, and does not re-check `lfs_sha256` or `git_oid`.
  - **F07 (P3).** The revision is not forced to a full commit sha; `main` is accepted and recorded as given.
  - **F08 (P3).** Stray files outside `data/` are not detected, and `SHA256SUMS` is not cross-checked against the manifest.
  - **F09 (P3).** There is no resume, and a network error aborts with a traceback, leaving the destination non-empty.

**Runs at `9e3cf986`, prefix `data/raw/hc/2007` (7 files: 2 LFS and 5 non-LFS, 559,162 bytes):**

| Test | Result | Exit code |
| --- | --- | --- |
| `create` | files 7, mismatches 0, excluded 0; all 7 files BYTE_VERIFIED | 0 |
| `verify` | failed 0, unexpected 0 | 0 |
| `sha256sum -c SHA256SUMS` | 7 OK | — |
| One bit flipped in an LFS file | failed 1 | 1 |
| One bit flipped in a non-LFS file | failed 1 | 1 |
| Extra file under `data/` | unexpected 1 | 1 |
| Missing file | failed 1 | 1 |
| Stray file at the backup root | **not detected** | **0** |
| Manifest marked `MISMATCH` with `mismatches` populated | **passes** | **0** |
| File altered and `computed_sha256` updated to match (`lfs_sha256` unchanged) | **passes** | **0** |
| Prefix typo (`data/raw/hc/20077`) | EntryNotFoundError traceback; no empty "verified" backup is produced | 1 |

**Exit codes.** They propagate through `sys.exit(main())`: create returns 0, 1 or 2, and verify returns 0 or 1.

**Credentials.** None are printed. The script never reads or prints a token. I grepped the logs and the manifest for token and Bearer patterns and found nothing. The traceback shows only the API URL.

**Layout.** Files land at `data/data/…` because `local_dir=dest/data` and repository paths already begin with `data/`. This is consistent with `SHA256SUMS` and `verify`, but the instructions do not mention it.

## 5. Instructions and registers

- **No claim of a second backup.** The instructions state explicitly that "no verified second backup exists yet", and `BACKUP_REGISTER.csv` contains only its header.
- **F10 (P3).** Several statements need updating or qualifying:
  - The head has moved to `9e3cf986`: 16,171 files, about 2.02 GB to back up after the exclusions.
  - `sha256sum -c` is offered as an equivalent alternative to `verify`. It does not detect extra files, and it does not re-anchor to the HF hashes.
  - The statement that exit code `0` "means every file is byte-verified" should say "every non-excluded file".
  - The HF `data/SHA256SUMS` included in the backup still lists the excluded PDF, so `sha256sum -c data/data/SHA256SUMS` will report it as missing.
- **Task register.** It is consistent with what I observed. Its claim that the guard is a "single source of truth" is not yet true in practice: A0, A2, A3 and A7 hard-code the source sha only, A1 uses a snapshot and A6 uses a mirror (F11).

## Reviewer's own handling of restricted material

To confirm the derived hashes, I downloaded the restricted meta and text files once into `reviews/gov/hfdl/`. I deleted them, together with a scratch file holding seven probe phrases, right after the check. I sent nothing to any external service other than read calls to the HF API.

## Artefacts in `scratchpad/c13/reviews/gov/`

- `hf_tree_head.json`: the full head listing.
- `git_ref_hits.txt`
- `guard_probe.py` and `guard_probe_out.txt`
- `create1.log`
- `bk1/`: the verified prefix backup.
- `review_c13_gov_dfce9140_findings.csv`
