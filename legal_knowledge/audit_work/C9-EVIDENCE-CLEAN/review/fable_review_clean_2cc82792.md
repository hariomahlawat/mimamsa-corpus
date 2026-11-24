# Independent review: clean replacement branch `claude/c9-evidence-clean` at 2cc82792

Reviewer model: Fable 5.2 (claude-fable-5-2)
Date: 2026-11-23. Review only; nothing was committed, pushed or changed. No sensitive text is reproduced here: tokens are referred to as "the diagnosis term", "NSY service number 1" (N S Yadav p.1) and "service number 2".

## Verdict: ACCEPT WITH CONDITIONS

The transfer itself is sound. The reviewed evidence is byte-identical, no old-branch commit or intermediate blob is reachable, and the branch adds neither the diagnosis term nor either service number. Two conditions apply before the record is relied on:

1. **CR-01:** correct the record's absence statement. The diagnosis term and NSY service number 1 are already present in pre-existing staging files, so they are in this branch's tip tree and history through its base. The branch did not add them, but the record reads as if they were absent.
2. **CR-02:** correct "the two N S Yadav service numbers". Only one is from N S Yadav; the second is from the Ranjit Thakur copy (p.4), as the original B-03 finding says.

Neither condition changes any file under `C8-EVIDENCE/`.

## Findings

| ID | Sev | Statement | Evidence (counts and paths only) |
| --- | --- | --- | --- |
| CR-01 | P2 | The record implies the diagnosis term and NSY service number 1 are absent from the branch. They are absent from everything the branch adds, but present in the staging base. Retiring PR #36 therefore does not remove them from the repository. They are also outside PRIV-01: the `pii_scan.py` pattern (digits + `M`) does not match NSY service number 1. Needs a scoped statement and an owner decision alongside PRIV-01. | Diagnosis term (case-insensitive): 0 in `C8-EVIDENCE/`, 0 in `C9-EVIDENCE-CLEAN/`; 6 occurrences in 4 pre-existing tip files: `PILOT-01/findings/independent-reviewer-blind.json` (1), `WS-B-JUDGMENTS/holdings_register.csv` (2), `WS-B-JUDGMENTS/tools/manual_registers.py` (2), `curated_originals/knowledge_base/v0.9/records_658.jsonl` (1). In each file one line carries both the term and the individual's surname. 3 further history-only blobs (older versions of the two WS-B files) reachable through staging. NSY service number 1 (digit-exact, with suffix letter): 0 in C8, 0 in C9; 1 each in `AUTH-LEDGER/evidence/copy_facts.csv`, `C6-01-PROVENANCE/inputs/held_copy_facts.csv`, `PILOT-01/sources/independent-reviewer-blind.json`. All paths under `legal_knowledge/`, identical at staging 21e73b83. |
| CR-02 | P3 | Record section 4 says "the two N S Yadav service numbers". The removed dumps hold one N S Yadav service number (p.1) and one Ranjit Thakur service number (p.4); the 5212a95b review and 801d2c41 re-review say "two non-Mullikote service numbers". | N S Yadav dumped text (2 pages + 30 line fields) contains exactly 1 service-number-shaped token. Service number 2: 0 occurrences in any of 1,929 reachable blobs. |
| CR-03 | P3 | Two statements hold only at the tool's window size (40/30 characters, step 10). With 25-character windows at step 1, whitespace-normalised, shared runs appear in 24 C8 files, not 17. "No fragment matched any file" under `review/` and "all 7 N S Yadav fragments occur only in" two files are tool-resolution results. | Extra files include `SC-T2/evidence/ns_yadav.md` (3 runs, longest 48 chars) and `review/fable_review_c8_evidence_5212a95b.md` (1 run, 26 chars). Longest run anywhere: 248 chars in `SC-T2/page_checks_sc_c8.csv`. All are in the already-reviewed, byte-identical tree; none contains the diagnosis term or either service number. |
| CR-04 | P3 | Committed outputs were generated at the transfer commit b78b11de, not the head. The record's "4,465 objects" and the sweep's "839" blobs are transfer-commit values. No conclusion changes. | At 2cc82792: 4,492 reachable objects; sweep scans 850 blobs, still 41 files. Tools re-run at b78b11de reproduce all committed outputs exactly. |
| CR-05 | INFO | Of the 9 digit-bearing matched fragments, 7 are case-number forms; the record does not say what the other 2 are. | Both come from the Mullikote copy, each has one 5-digit run, neither is followed by `M`. |
| CR-06 | INFO | Local exposure confirmed as the record states. Remote state not checked (no network). | Refs containing 5212a95b: `refs/heads/claude/c8-evidence-verification` and `refs/remotes/origin/claude/c8-evidence-verification`. |
| CR-07 | INFO | Record line "An independent re-review accepted that tree" refers to the 801d2c41 re-review plus the 152045bd tip; I did not re-verify that acceptance, only tree identity with 152045bd. | Tree id d82436fe at both commits. |

## What I checked (own commands)

1. **Tree identity.** `C8-EVIDENCE` tree id is `d82436febd49067348d88acadd31c21185cef73e` at both 2cc82792 and 152045bd. Diff against staging: 106 added under `C8-EVIDENCE/`, 11 added under `C9-EVIDENCE-CLEAN/`, nothing else, no modifications or deletions. Branch is three linear commits on 21e73b83.
2. **Ancestry and objects.** 3 old-branch commits; 0 are ancestors of 2cc82792; merge base of the two branches is 1a21a2e8. 190 distinct old C8 blobs, 106 final, 84 intermediate; 0 of the 84 reachable. Of 226 objects the old branch introduced, 118 are reachable, all of them final-tree objects. Branch adds 149 objects over staging.
3. **Direct token search.** Tokens identified in memory from the B-03 blobs at 5212a95b and searched in all 1,929 reachable blobs (including 6 binary-looking ones, also decoded as UTF-16), commit messages and object paths. Results in CR-01 and CR-02. Mullikote numbers (PRIV-01) kept separate: both digit strings occur in the same 12 C8 files the record lists.
4. **Hashes.** 6 Gazette and 6 Supreme Court rows chosen at random, then all rows: 40/40 and 28/28 file hashes match, 40/40 and 28/28 render hashes match (PyMuPDF 2.1 / MuPDF 1.28.6, 150 dpi, csGRAY, no alpha). `render_facts.jsonl` has no text field.
5. **Builder check.** `build_packages.py --check` exits 0 ("C8 packages reproduce (30 files)"). Worktree status empty afterwards; no `__pycache__` left.
6. **Record statements.** PRIV-01 counts confirmed with my own pattern: 72 tokens in 23 files at transfer and head; 36 in 12 C8 files; 36 in 11 pre-existing files; 0 in C9. Attribution output reproduces: 88 distinct, 89 per-copy sum, 9 / 7 / 0, 7 from N S Yadav. C9 files contain no shared text run and no service-number-shaped token. Owner actions are accurate and correctly left to the owner. The record claims no human confirmation and changes no provenance or legal conclusion.

## Disposition of CL-01 to CL-11

| ID | Disposition |
| --- | --- |
| CL-01 to CL-03 | Process gaps of the first attempt (no shell, no verdict). Superseded by this review. |
| CL-04 | Addressed in the record as a stated limitation; the direct token search is now done here. Its result is CR-01, which the record must reflect. |
| CL-05 | Closed. `tools/attribution.py` is committed and reproduces its output. |
| CL-06 | Closed. 88 distinct fragments, one shared by two copies, per-copy sum 89; verified. |
| CL-07 | Closed. Environment dependence stated; versions match what I ran. |
| CL-08 | Closed for PRIV-01 counts (verified). Open in part: NSY service number 1 falls outside that count (CR-01). |
| CL-09 | Not separately described to me; no residual seen beyond CR-03 and CR-04. |
| CL-10 | Closed. Local exposure stated accurately (CR-06). |
| CL-11 | Process gap of the first attempt. Superseded. |

## What I did not check

- Remote state: whether `origin` and `refs/pull/36/head` still serve 5212a95b, and anything on GitHub.
- Unreachable or dangling objects, reflogs, and other worktrees of the shared object store.
- Content inside compressed or encoded binaries; variants of the tokens other than case, space, hyphen and non-breaking space.
- Whether the pre-existing occurrences in CR-01 are appropriate for their own files (public judgment text in earlier, separately reviewed cycles). That is an owner decision.
- Legal correctness of any evidence reading; the earlier acceptance of the C8 tree.
- No destructive experiment or simulation was run.
