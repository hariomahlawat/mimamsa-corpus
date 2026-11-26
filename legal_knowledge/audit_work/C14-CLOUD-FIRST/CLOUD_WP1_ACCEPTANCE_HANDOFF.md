# WP1 targeted independent acceptance handoff — 26 November 2026

This is a review assignment, not a release, acquisition, merge or dispatch authorization.

## Exact review inputs
- PR #62 head e77598731177774c7c5da0c66c79a2db093748ae, stacked on PR #58 head f1bbd15dc9a57531b0b061578fdceba94ff35753.
- PR #63 head 5962b541d5cd53e6d6c13e07fceb230f879a500d, base main 21de35313397d77c915a9b11c9ea0493be00f4bd. Inert registration workflow only.
- Final cloud synthetic job 139915725920: six tests passed. Full audit job 139915724518: 1132 total, 28 skipped, zero failures. Live metadata job skipped.
- Owner screenshot shows environment hf-corpus-metadata-read, selected branches/tags, one branch/zero tags, secret name HF_WP1_READ_TOKEN. Exact branch string truncated. Required reviewers not visible. No activation variable configured as instructed. Secret scope not yet verified by provider. GitHub connector cannot read the protected environment or dispatch a new workflow.

## Review only the new cloud boundary
1. Verify exact dispatch SHA/ref, owner/triggering actor, immutable workflow and environment commit pin; ensure pull requests, main registration stub and retries do not receive credential or execute live metadata. Assess mutable branch/repository writer trust, not a claim that an environment variable alone prevents malicious workflow changes. Verify private-repo and environment deployment rules. Consider a narrowly bounded alternative if required reviewer protection is unavailable.
2. Review token handling and third-party action pins, runtime byte verification, worker invocation, request allowlist and credential preflight. Preserve strict provider grant checks. No actual token, authenticated HF request or network corpus operation is part of this review.
3. Review synthetic full round trip, restricted filtering, incomplete receipt handling, artifact scope/retention and safe aggregate output. Verify no source download, HF write, release promotion, legal closure or Authority Ledger change.
4. Review default-branch registration semantics and PR #63 one-file diff. Confirm registration is inert on main; actual reviewed cloud ref is explicitly selected on dispatch. No merge as part of this review.
5. Report only new actionable P0/P1/P2 findings (with reproducible evidence), residual prerequisites and precise ACCEPT / HOLD recommendation for the first bounded metadata-only run. No re-audit of previous Cycle 14 or Windows implementation. No modifications unless specifically directed.

## First-run constraints after independent acceptance
- Preserve existing local failed receipt. No local retry.
- Owner must confirm exact deployment branch, private artifact access and available hosted Actions allowance. Set environment variable WP1_CLOUD_APPROVED_COMMIT to exact accepted head, not a boolean.
- Register the inert workflow through approved main merge, then select branch corpus/cloud-wp1-20261126; operation METADATA_GET_ONLY; HF revision f4e6ba443ec9c0b89b2c5d21d0b5cda38f55d2dc; exact accepted code SHA. No dispatch on main for corpus operation. One attempt, eight-minute job cap, seven roots, no source blobs, no writes.
- Capture aggregate status/digest and securely retain filtered receipt before one-day artifact expiration. Revoke temporary token/remove environment secret after completion or failure; no automatic retry or broadened permissions.
- If receipt is incomplete, remain acquisition-ineligible. Do not claim local-store coverage or independent byte verification from LFS metadata.
