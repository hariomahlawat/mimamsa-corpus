# Consolidated independent technical assurance — Cycle 14 corpus tranche

Reviewer: Codex. Read-only review first; no merge, no source acquisition, no HF writes, no credentials printed, no edits to Claude/B1 worktree. Use disposable fixtures and isolated worktrees. Evidence policy v1 and repository governance apply.

## Immutable review subjects

- Staging: c1e4d461e208bf961fd6bc51584dad01df220e61
- PR #58 code/data/runner subject: 88ef329e77723468fa5c85e14cd2f6816610e35f (this review brief is a later documentation-only commit; verify that fact against the live head).
- PR #59: 1b101d04a07224a4969beca67f06ca9162265931.

If any substantive change occurs after these pins, review the new diff and record the actual tested head. Review against staging separately, not an invented combined merge. No application engineering review or duplicate Cycle 13 review.

## A. CA-01 reconciliation and provenance

1. Rebuild the join from original 45 A4 rows, 126 A7 targets and manifest, and A7 HF verification records. Check exact URL/MD5 joins, compound-request group mappings, unique SHA paths and all disposition counts. Pay special attention to partial versus full closure and unresolved archive targets.
2. Recheck 15 sidecar mappings against candidate inventory, C5 copy/master registers, and prior byte verification. Two mismatched original MD5/size pins must remain HOLD_PIN_MISMATCH even if the preserved bytes match; three further post-2022 items must remain subject-unconfirmed. No claims of exact-page verification or legal status. Verify C5 source-group mapping is only a proposal, not identity.
3. Confirm new government source locators are discovery leads only; validate the reported ISO Act-number discrepancy before treating it as a finding. No public search for private material or RM-001.

## B. CA-01B acquisition security

4. Recompute the 23 archive targets / 61 redirect URLs / 13 unprobed hosts from the baseline source rows. Ensure every candidate remains disabled. Investigate archive path canonicalization, percent encoding, redirects, credentials in URL, ports, DNS/rebinding/SSRF risk, robots and CAPTCHA handling, blocked domains and TLS trust boundary. The standalone exact_scope_guard is not wired to active crawler; review proposed integration separately before any actual fetch. Run its synthetic assertions.
5. Review C13 patch 0003 and existing C13 A7 networking code only where needed to identify security gaps; no configuration activation. Require exact file and target scoping, raw and resolved redirect validation, dedicated robots handling, verified TLS, bounded streamed size and pin validation, provenance logging, preservation quarantine, dedup and non-destructive behavior.

## C. Local runner

6. Verify tested Git blobs: runner d928c1501fde04cc77cb0476aeb65cc3d50381ca, tests 039e80f92af5237196e402c7bdad3842ca7a078e, candidate inventory 5be838d109b9d785fcd092977e04c56f808c7034. Run python -B -m unittest -v test_corpus_runner in runner directory, then python -B corpus_runner.py (dry run; 15 files, 17,565,129 bytes).
7. Add adversarial tests as review findings or in a separate review-only worktree: tampered inventory including Windows CRLF, malformed paths, symlink/junction containment, unsafe output paths, dirty worktree, missing dependency, invalid HF revision, interrupted run, report corruption, credential leaks from SDK logging/errors, changed HEAD, missing path, inconsistent hash and size. Check actual installed Windows Python and HF SDK compatibility without installing packages or exposing token. Mock network unless owner explicitly authorises authenticated read-only verification. Validate current-HF path presence is not current-HF byte verification. Verify no upload calls, no destructive operations or global configuration changes. Prior source mismatch and legal eligibility must never change.
8. Check PowerShell launch commands use detached isolated worktree and immutable reviewed commit, and job directory outside all existing project trees. Record scope and integration limits. Local subset is not full second backup.

## D. CA-03 test-first adoption

9. Read pipeline/judgments.py, records.py, relevance_states.py, text_quality.py, report.py and existing tests. Confirm deletion and historical exclusion paths, stale-output cleanup and separation of source integrity from relevance and eligibility.
10. On disposable synthetic fixtures run PR #59 acceptance_relevance.py explicitly. Expected legacy failures are evidence of defect, not a regression from the proposal. Check tests do not access actual corpus; add missing cases for valid civil PDF retention, alias preservation, historical exclusion recovery, OCR page binding and idempotence. Assess the full 16-case acceptance matrix. No live implementation or active corpus run as part of this review.

## Deliverable

One review report, with each finding's severity P0/P1/P2/P3, exact file/line, reproduction, expected vs actual, proposed correction and test evidence. Separate independently verified facts, documentary uncertainty, policy/owner decisions and untested integration. Include exact reviewed heads, commands and results; state whether each PR is suitable to advance to implementation/commissioning, not legally approved. No auto-merge or write to HF. If changes are needed, report them to ChatGPT for corpus work; do not redirect routine collection to Claude.
