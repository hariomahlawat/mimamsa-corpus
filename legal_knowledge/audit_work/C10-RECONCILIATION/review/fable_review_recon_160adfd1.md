# C10 unified corpus reconciliation: independent adversarial review

Reviewer model: Fable 5.2 (claude-fable-5-2)
Reviewed: branch `claude/c10-unified-reconciliation`, commit `160adfd1531726af95ab3cf9f4019b480318216c`, package `legal_knowledge/audit_work/C10-RECONCILIATION/` and `tests/test_legal_audit_c10_reconciliation.py`.
Review time: 2026-11-23, about 23:30 to 23:45 UTC. Read-only; the worktree was not modified.

## Verdict: ACCEPT WITH CONDITIONS

The numbers hold. Every material count I re-derived independently matches, the Hugging Face listing has no transcription error in 99 sampled rows, and I could not falsify the claim that 48 registered copies exist only in the working store. No P1 finding.

The conditions are five P2 findings, all about wording or labels that claim more than was checked, plus one checking gap that is cheap to close. Findings are in `findings.csv` in this folder.

## Conditions (P2)

| ID | Finding | Fix |
| --- | --- | --- |
| RC-01 | The equivalence register gives "identical SHA-256" as the basis, and "no review needed for identity", for 4,051 groups that include a Hugging Face copy. No Hugging Face byte was hashed. | Carry the HF verification level into the classification or basis. |
| RC-02 | Segment `data/raw_manifest.csv` is labelled `GITHUB_REHASHED;HF_PATH_SIZE_DECLARED`. It was not re-hashed and its HF size differs (1,863,896 against 1,926,766). The report table drops the size-differs column, and the integrity notes say "identical manifest sizes". | Fix the `startswith("data/raw")` test, show the column, correct the notes. |
| RC-03 | The authority matrix states "Publication is never commencement" and "Commencement needs the commencement notification itself" as rules. Both are overbroad legal conclusions. The Supreme Court hierarchy also has no tier for open-data bulk copies, although all 346 `data/raw/sci` files came from an AWS bucket, as did all 3,605 High Court files. | Reword to an evidence rule per instrument; add the tier and say that no crawler judgment came from a court portal. |
| RC-04 | "Revision not pinned" is missing from `DATASET_INTEGRITY_NOTES.md`, `DATASET_INTEGRITY_SUMMARY.csv` and every CSV output. `CAPTURE.md` says the limits are stated in every output. | Add an as-of and revision caveat to the notes and a snapshot column or header reference to the CSVs. |
| RC-05 | `CAPTURE.md` says the connector caps at about 700 entries, so `data/meta`, `data/text` and `data/sections` are count-only. The connector accepts `--limit` up to 10000, glob `find`, and `cat --offset`. A per-file path and size comparison of those 11,643 files, and a full read of the HF `SHA256SUMS`, were available. | Do the comparison, or correct the stated limit. |

The size difference in RC-02 is benign: re-serialising the GitHub manifest without its two GitHub-only columns gives exactly 1,863,896 bytes with CRLF line endings.

## What I reproduced

| Claim | Result | How |
| --- | --- | --- |
| Builders reproduce | Yes: 8 files and 2 files | Both tools with `--check` against `/home/user/c7`; no `__pycache__` left behind |
| 4,039 of 4,039 GitHub raw files re-hash to `SHA256SUMS` | Confirmed | My own loop with `git cat-file` and `sha256sum`; sorted output byte-identical to the `data/raw` lines of `SHA256SUMS` |
| HF `data/raw` same path and size | Confirmed on sample | 68 sampled raw rows and 8 directory counts, live |
| 16 HF-only binaries, 8 judgments and 8 MML | Confirmed | Live `find` of `legal_knowledge` returned the same 166 files as the listing; only these 16 are binaries |
| Declared hashes of the 8 judgments | Confirmed | I read all 7 HF sidecar JSON files; every sha256, size and URL in `lk_declared_sidecars.tsv` is correct |
| Declared hashes of the 8 MML files | Confirmed | HF `MML_Originals_Manifest.csv` read live; equal to the values used |
| 48 registered copies only in the working store | Not falsified | See below |
| 1954 Army Rules Gazette `c5ef95a9` among them | Confirmed | 5,032,579 bytes, re-hashed from the working store, 42 anchor rows; live HF `find` for `c5ef95a9*` returned nothing |
| Ram Sarup 1963 and Mani Ram Bhaira 2016 have no C5 row | Confirmed | No copy-register hash and no master-register title for either |
| W.P.(C) 140/2024 backs 209 records | Confirmed | One file, 209 Delhi HC records dated 2025-07-01; text opens "W.P.(C) 140/2024 & connected matters, Page 1 of 85" |
| 4,259 judgment records on 3,951 files; 42 shared files | Confirmed | Recomputed from the 4,327 metadata records |
| `raw-data` schema older than its records | Confirmed | Schema constant `0.1.0` in 3 files, no correspondence schema; all 4,327 records are `0.2.0`; HF schema sizes equal staging |
| Latest logged HF commit `e1a7fa47` | Accurate as stated | 119 distinct commits, 64 jobs, latest 2026-11-22T14:49:25Z; dataset card "Updated 22 Nov, 2026" confirmed live |

### Attempt to falsify the 48
- **Working store:** all 48 files are present and re-hash to the registered value.
- **GitHub:** I listed every blob in the local clone, 17,510 including unreachable objects across 101 refs. None has the byte size of any of the 48, so none can match.
- **`SHA256SUMS`:** none of the 48 hashes appears.
- **Hugging Face:** none of the 4,221 listed files has the byte size of any of the 48, and no path contains any of the hashes. Live `find` for `*.pdf` under `data/meta` and `data/text`, and for `*.zip` anywhere, returned nothing.

This rests on the local clone, not the GitHub server, and on the HF main branch as listed, not other HF refs (RC-15).

## Hugging Face sample

99 rows checked live against the committed `listing_*.tsv`: 99 match on path and size, 0 errors. Full results are in `sample_result.tsv`.

| Area | Rows |
| --- | --- |
| `data/raw/hc` (2006, 2007, 2014, 2025, 2026) | 32 |
| `data/raw/sci` (1996, 2019) | 14 |
| `data/raw/indiacode` (1950, 2023) and `official_copies` | 22 |
| `legal_knowledge` | 22 |
| `data/` top level, root, `reports`, `schema` | 9 |

Directory totals verified live, all equal to the snapshot:

| Directory | Files |
| --- | --- |
| `data/raw/hc/2006`, `2007`, `2014` | 11, 7, 39 |
| `data/raw/sci/1996`, `2019` | 8, 30 |
| `data/raw/indiacode/1950`, `2023` | 12, 18 |
| `data/raw/official_copies` | 4 |
| `data/sections/act-army-af-disposal-private-property-1950` | 17 |
| `data/sections/act-armed-forces-tribunal-2007` | 44 |
| `data/correspondence`, `schema`, `reports` | 3, 4, 2 |
| `data/sections` subdirectories | 11 |
| `legal_knowledge` (recursive) | 166 |

Beyond the brief, I compared 22 `data/meta` and `data/sections` files by size against GitHub (the package marks these count-only): all match. One 400-byte range of the HF `SHA256SUMS` is identical to GitHub and to the recorded range hash.

I did not verify the `data/meta` (4,327) and `data/text` (4,318) totals; a full listing was too large to read in this review.

## Builder logic

- **Presence and register state:** correct for the current inputs. The 4,103 rows split as 4,039 mirrored, 16 HF-only and 48 working-store-only; 67 registered, all from the C5 copy register.
- **Determinism:** sound. Sorted iteration, no timestamps, sorted JSON, input and output hashes in the manifest.
- **Authenticity:** never asserted; every row carries `NOT_AUTHENTICATED_BY_THIS_RECONCILIATION`.
- **Overclaims:** RC-01 (HF byte identity), RC-02 (segment level), RC-06 (`SAME_LEGAL_DOCUMENT` from a shared source id), RC-07 (MML hash labelled as an HF sidecar).
- **Failure modes:** missing raw-data or register commits fail closed. A missing C9 mapping commit is swallowed, and truncation is caught only by a hand-written marker (RC-10).
- **Traceability:** every field traces to a pinned input except the blank titles of four HF-only judgments, where the builder reads a column the snapshot does not have (RC-08).
- **Revision handling:** the builder, report and manifest state "not pinned" correctly. The log evidence is accurate but incomplete: two HF revisions cited in `upload_run_remote_verified.tsv` are missing from `hf_commits_from_logs.tsv` (RC-09). The connector exposes no revision id; I confirmed this with `stat` and the repository overview.

## Authority matrix and integrity notes

- Storage location is not treated as authority; the matrix says so and holds to it.
- Two commencement statements are overbroad and the Supreme Court tier list has a gap (RC-03).
- The notes' "identical manifest sizes" is wrong for one file (RC-02), and the reason given for nine records without text is not supported by the data (RC-12).
- The HF `DATA_AUTHORITY.md` still says the eight MML binaries "are not presently uploaded"; they are listed on HF. The matrix cites that document for store roles only, so nothing depends on the stale line.

## Not checked

- Hugging Face bytes: none downloaded or hashed, by rule.
- GitHub server state, GitHub Actions logs and the upload-run read-back claims: no network.
- The `data/meta` and `data/text` HF totals.
- Legal correctness of matrix items that cite earlier cycles (S.R.O. 34/1963, Mullikote, P-D3).
- The untracked `workstreams/` folder. A second untracked folder, `legal_knowledge/audit_work/C10-HF-JUDGMENTS/`, appeared in the worktree during the review; it is not mine and I did not read it.

## Files in this folder

- `findings.csv`: 15 findings (5 P2, 7 P3, 3 INFO).
- `hf_sample_observed.tsv`, `sample_result.tsv`: the 99 sampled rows as I read them from Hugging Face, and the comparison.
- `falsify.py`, `an.py`, `an2.py`, `an3.py`: the scripts I ran. They read some temporary extracts that I deleted afterwards, so they need those re-created to run again.
