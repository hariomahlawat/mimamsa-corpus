# C13 holdout exposure register

This file records every known exposure of fresh-holdout content (H-OUT-C13, H-HOLD-C13 including its opened reserve, H-REL-C13). The machine-readable copy is `inputs/EXPOSURE_EVENTS.csv`, which `tools/c13_sensitivity.py` merges into `outputs/holdouts/PRE_EXPOSED_SUBSET.csv`. **No holdout was redrawn and no judgment was dropped.** Exposed judgments stay in the sample. Every headline is reported with and without them, and a pass must hold without them (PROTOCOL_C13 v1.1 sections 4.4 and 6).

## E1. Reviewer scratch committed to the branch (confirmation finding C01, P1)

**What happened.**
- Commit `a4865e76` (2026-11-25T11:11:56Z, C13-A0 author) copied the GA0 reviewer's scratch evidence into `C13-A0-EVAL/reviews/`. The files remained in `06340486`.
- `reviews/frame_sample/*.txt` held about 1,800 characters from the start and 2,500 characters from the end of 40 judgments.
- `reviews/party_ppv.txt` held cue sentences and the last 600 characters of party-cue candidates.
- The endings carry the operative disposal.

**Removal.**
- The files were removed from the tree in the commit that adds this register. Removed: `frame_sample/` (40 `.txt` files and `SAMPLE.csv`), `party_ppv.txt`, `leak/`, `scripts/`, `fuzzy_frame_pairs.csv`, `my_spent_core.json`, `scan_all.tsv`, `sim_hetero.json`, `sim_p98.json`.
- `neardup_holdout_vs_spent.csv`, which holds keys and scores only, was moved to `inputs/`.
- Only the review report, its findings CSV and the confirmation report are kept, as copies. Quoted judgment text in the report and findings CSV was redacted in these copies.
- The reviewer's originals stay in the coordinator scratchpad.

**History.**
- The branch was pushed, so **the files remain in git history at `a4865e76` and `06340486`**.
- History was **not** rewritten and nothing was force-pushed, as instructed.
- Anyone who checks out or diffs those commits can read the excerpts.

**Exposed holdout judgments.** There are 19, all registered as `REVIEW_TEXT_EXPOSED` (PRIMARY):
- 18 are the reviewer's list. I verified it independently by mapping every judgment id, doc id and file name in the removed files to judgment keys and intersecting the result with the holdouts:
  JK-1aa3838f30b79141, JK-204366fba3be87b1, JK-2890b7b47a443252, JK-3775f27e8c6d1265, JK-3c00f93d93f6804f, JK-566556d10756008c, JK-6ad23cfb89323b87, JK-7b198edc7afe64e3, JK-81730e236b81cfd5, JK-8d5739ca50ff6b89, JK-9c9c75f4aff795be, JK-9da05d5ec12aa6fb, JK-a5fe29566f0774ec, JK-c72781c1391284ec, JK-cbf165489b0d8623, JK-dc279e9f44680bd8, JK-e3c9f7c5d9d5a27c, JK-f3a273f09da43b54.
- 1 more was found by the leak guard (E3): **JK-8edc4af5fdd3d9cf**, in H-OUT and the H-HOLD reserve. A committed excerpt of a *non-holdout* judgment is a near-identical sibling order of it (16 sampled shingle hits).

**By holdout:** H-OUT 18; H-HOLD 4 (JK-1aa3838f, JK-c72781c1 and JK-f3a273f0 in the sample, JK-8edc4af5 in the reserve); H-REL 1.

**Who saw the text:**
- the GA0 reviewer, who wrote the excerpts;
- the A0 author, who copied the files without reading them and later scanned them by machine;
- anyone with access to the pushed branch since `a4865e76`.

**Required of A2, A3 and A5 extractor authors (coordinator to collect):**
- do not open `C13-A0-EVAL/reviews/` at `a4865e76` or `06340486`, or the scratchpad `reviews/a0/`;
- state in writing whether you have already viewed them;
- record any viewing in your freeze record.

## E2. A0 author development snippets (disclosed by the A0 author)

While developing the party-specific cue, **before the holdouts were drawn**, the A0 author printed about 100–200 characters of cue context, near the operative part, for 12 corpus judgments in its own session. The snippets were not committed.

Ten of those judgments were later drawn into H-OUT, because Delhi's party-specific cell was taken whole. All ten are registered as `AUTHOR_DEV_SNIPPET_VIEWED` (PRIMARY):
- JK-6bf3505baf3dafcd, JK-8d5739ca50ff6b89, JK-7b198edc7afe64e3, JK-204366fba3be87b1, JK-cbf165489b0d8623, JK-6a53e0643665d179, JK-3c00f93d93f6804f, JK-e3c9f7c5d9d5a27c, JK-badb628a2c6d1385, JK-328c43bddf60aeed.
- Six of them are also in E1.

The A0 author is neither an extractor author nor a coder, but the snippets exist in its session transcript.

## E3. Leak guard (`tools/c13_leakguard.py`) and its calibration

**What it holds.**
- The fingerprint holds 1/8-sampled, truncated sha256 hashes of 8-word shingles from all 455 holdout judgments' representative texts.
- Shingles present in 3 or more corpus judgments are removed as boilerplate.
- It holds no readable text.

**What it checks.** The test `test_legal_audit_c13_eval_leakguard.py` fails if any file under `C13-A0-EVAL/` shares at least 5 fingerprint hashes.

**Calibration** on the 56 files removed in E1, read from `a4865e76`:
- all 11 excerpt files of holdout judgments scored 8–90 hits, and `party_ppv.txt` scored 108, so all were flagged;
- non-holdout excerpts scored 0–3, except one (16), which is the sibling of JK-8edc4af5 (E1);
- the current tree scores 0 everywhere.

## E4. Earlier registered pre-exposure

These were registered earlier, from GA0 F04/F06, and are unchanged:
- `CURATED_KB_CONTENT`: 4 judgments;
- `NEAR_IDENTICAL_SPENT_SIBLING`: 16 judgments;
- `CASE_NUMBER_REVIEWED`: 27 judgments, case-number fields only.

## Totals (`PRE_EXPOSED_SUBSET.csv`)

- 68 holdout judgments carry at least one category.
- 42 are PRIMARY, meaning excluded in the "without" sensitivity analysis: H-OUT 35, H-HOLD 8 (including the reserve), H-REL 7.
