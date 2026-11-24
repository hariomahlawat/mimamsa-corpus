# Dispositions: Fable 5.2 (claude-fable-5-2) review of the coordinator-written C11 tools (at c0c7362f)

**Verdict: ACCEPT WITH CHANGES.** No P1; 4 P2, 8 P3, 6 INFO. The fixes below are in the next commit, which awaits a narrow confirmation review.

| ID | Sev | Disposition |
| --- | --- | --- |
| C-01 | P2 | **FIXED.** `release_filter_c11.py` also downgrades every file in a multi-copy judgment of the identity register, revision 2 (414 ids), and every row whose label names more than one distinct case reference. Downgraded rows: SHARED_BATCH_TEXT 226, MULTI_COPY_JUDGMENT 74, MULTI_NUMBER_LABEL 278. `v2_outcome_original` is kept. |
| C-02 | P2 | **FIXED.** `excluded_rank_c11.py`: a bare `naval` no longer counts as a signal, because it matches the personal name Naval (Kishore); a naval body is required. Rank-against-Union now matches "Vs" or "versus", with the rank on either side. Added "MIN.OF DEFENCE" and "defence services". Coast Guard is moved out of CAPF, since it is under the Ministry of Defence. **New tiers:** T1 1,790 / T2 1,570 / T3 706 / T4 317 / T5 3,694. Nothing acquired. |
| C-03 | P2 | **FIXED.** `curated_c11.py` also matches a record to a case through the C5 crosswalk `source_id` and the C8 gap matrix: V7-S11 is Tarsem and V6-S19 is the Girish clarification. All seven named records (AFT-001, -033, -044, -014, V7-SC-14, V7-SC-16, PEN-049) are now included. **32 records / 37 record-case pairs**; each row carries `match_basis`. |
| C-04 | P2 | **FIXED.** The marking scan counts pages without a text layer. Copies are now reported as NOT_SCANNED_IMAGE_ONLY (3), NO_MARKING_FOUND_ON_TEXT_PAGES_n_PAGES_NOT_SCANNED (14) or NO_MARKING_FOUND_ALL_PAGES_TEXT (31); 73 pages were not scanned. The register value is no longer rewritten as "none recorded". The package text says those pages need a visual check before any publication. |
| P3 | — | **FIXED:** the git-object claim is scoped to the shallow local store; the composition text points to the inventory instead of a wrong count; 47 anchor rows are stated (42 + 5); `holdout_sample_c11.py --check` no longer writes, and the Delhi shortfall is explained; Coast Guard is reclassified; the curated finding text no longer hard-codes values that drift; actions are phrased as adviser questions. **DEFERRED:** unit tests for the seven tools (each has a byte-reproducing `--check`), and the two comparison labels flagged on Prithi Pal Singh Bedi and Ratan Singh, which need a reading. |
| INFO | — | Noted. The 34 marking hits are all ordinary word use; the pytest-style crawler suites are collected only by pytest (122 passed, 1 skipped); the relations failures the reviewer saw came from concurrent edits during round 3. |

## Round 2 (bfd295d1): **ACCEPT**
C-01 to C-04 are closed. The P3 residuals are carried to the follow-up change:

| ID | Disposition |
| --- | --- |
| R2-01 | **Follow-up.** Two single-copy files registered under several proceedings, and 25 range labels ("9367-9369 of 2011"), still carry released outcomes. Ranges are to count as multiple proceedings. |
| R2-02 | **Follow-up.** About 22% of T5 titles still name the Union with a rank or "defence" (service-number prefixes, punctuation after the rank, "NAIK" matched on one side only, J&K "U.O.I.TH.DEFENCE" forms). Widen the rules and add `excluded/README.md`. The tiers remain leads only. |
| R2-03 | **Follow-up (wording).** `PRESERVATION_PACKAGE.md` §3 step 5 says "all 42 anchors"; it should read "the 47 anchor rows, including all 42 Army Rules 1954 anchors". |
