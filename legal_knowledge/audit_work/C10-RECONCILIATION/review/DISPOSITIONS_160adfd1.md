# Dispositions of the reconciliation review of `160adfd1`

The review verdict was **ACCEPT WITH CONDITIONS**: no P1 and five P2s. The report is copied verbatim beside this file. Fixes are in the next commit, which **has not been re-reviewed**.

| Id | Severity | Disposition |
| --- | --- | --- |
| RC-01 | P2 | **Fixed.** The equivalence `basis` now names which stores were re-hashed. Any group that includes a Hugging Face copy adds "HF copy: same path and size with the HF-declared SHA-256, HF bytes NOT_CHECKED", and its `review` is `HF_BYTES_NOT_CHECKED` instead of `NONE_NEEDED_FOR_IDENTITY` |
| RC-02 | P2 | **Fixed.** The re-hashed level now applies only to `data/raw/*`. `data/raw_manifest.csv` shows as size-differs (1 file). The report table gains a size-differs column, and the integrity notes state the size difference and its cause |
| RC-03 | P2 | **Fixed.** The commencement wording is now an evidence rule, not a statement of law: an instrument may commence on publication by its own terms, but publication is never assumed to be commencement. An open-data bulk-copy tier (the AWS S3 source of all `data/raw/sci` and `data/raw/hc` files) is added to the Supreme Court hierarchy |
| RC-04 | P2 | **Fixed.** Inventory and repository rows that refer to Hugging Face carry `hf_snapshot = UNPINNED_LISTING_2026-11-24`. `CAPTURE.md` and the integrity notes state that the revision is unpinned |
| RC-05 | P2 | **Fixed (wording); work open.** `CAPTURE.md` now states the observed output truncation, and that a per-file listing of `data/meta`, `data/text` and `data/sections` and a full read of HF `SHA256SUMS` were possible but not done. They remain open |
| RC-06 | P3 | **Fixed.** The group is renamed `SAME_C5_SOURCE_ID_DIFFERENT_BYTES`, with a review note that a shared source id does not prove the same legal text |
| RC-07 | P3 | **Fixed.** MML hashes are labelled `GITHUB_MML_MANIFEST_DECLARED`. The reviewer read the HF manifest and found equal values |
| RC-08 | P3 | **Fixed.** The sidecar input carries `declared_case_name`. The tier is blank where the sidecar has none (Ravishankar, Chandrabhan) |
| RC-09 | P3 | **Recorded** in `CAPTURE.md`. Both missing revisions predate `e1a7fa47` |
| RC-10 | P3 | **Fixed.** A missing pinned C9 mapping commit now stops the build |
| RC-11 | P3 | **Fixed.** Judgment doc_ids with more than one distinct file are included in the identity-review groups (13 groups, previously 8) |
| RC-12 | P3 | **Fixed.** The notes no longer attribute the 9 missing text files to OCR |
| RC-13 | INFO | Recorded: 12 of the 16 HF-only copies are also in the working store |
| RC-14 | INFO | **Corrected:** four HF-only judgments have no C5 register row (Ram Sarup, Mani Ram Bhaira, Ravishankar Tandon, Chandrabhan Sudam Sanap) |
| RC-15 | INFO | **Fixed.** The manifest also hashes the companion files (the hand-written `.md` outputs and the integrity CSVs). The capture date note gives the UTC clock |
