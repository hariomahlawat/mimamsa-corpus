# Cycle 14 tranche 03 — independent review addendum

Use this addendum with CODEX_REVIEW_PACKET.md; older head pins are historical, not the review subjects for new changes.

## Pinned review subjects

- Staging: c1e4d461e208bf961fd6bc51584dad01df220e61
- PR #58 substantive head before this addendum: 4ce32763ddbe4ee54bc520dfc543bf439749f34c
- PR #59 substantive head: 5bf8cd5dd89b82dd141e264983c408012746967a

Verify the live heads and review any subsequent substantive change. No merge, HF writes, bulk retrieval, legal promotion, active pipeline run or application changes. Do not use RM-001. Use synthetic fixtures or explicitly approved read-only local inputs.

## CA-01B: six-source batch

LOCAL_ACQUISITION_BATCH_01.json excludes the one-page 1955 India Code duplicate; existing BNS/BNSS/BSA compilation page counts differ from proposed enacted Gazette editions. Live connector filename searches do not rule out hashes held under other names. Independently recheck the discovery leads, exact editions, historical Schedule and source scopes. Produce a revision-pinned known-hash inventory from the actual HF manifest plus all relevant preservation stores (report any incomplete coverage); no acquisition until this gate and owner approval. Do not claim that the candidate URL, title or new digest alone proves authenticity. Scope remains disabled. The 23 archive candidates remain separate and disabled.

Review acquisition_batch.py, blob 4b96999cefb26ef1dcbcb6e61fe3051c4eaf65eb. It rejects redirects, uses default verified TLS, checks DNS, requests robots, bounds file size, preserves partial downloads, checks carrier pins and quarantines every result. Thirteen offline assertions passed in an isolated Linux Python 3.13 environment: exact plan, four tamper cases, normal receipt, known hash, bad PDF signature, length mismatch, carrier pin mismatch, non-PDF response, no overwrite and redirect rejection. No live integration test. Test assertions were run ad hoc, not yet committed as a reusable test module.

Known review items: DNS check is not connection-IP pinning (TOCTOU / rebinding); standard urllib robotparser support for wildcard and longest-match rules must be evaluated; socket timeout is not an overall wall-clock budget; exact origin redirects or unavailable robots currently stop the job; output report should record HTTP status, safe headers, and observed fetch UTC; known-hash input is caller-provided and its completeness/provenance not enforced by the prototype; symlink/junction and concurrent file creation require adversarial checks. Verify approved-scope authority cannot be represented as mere self-approval by an unreviewed edit. No activation until corrections and independent acceptance.

## IPv4 launcher

launch_ipv4.py, blob 1dda2c94d90435b9a9e531342e124c28646b7d97, wraps only corpus_runner.py. Offline mocked assertions passed for AF_UNSPEC-to-AF_INET conversion, preservation of explicitly requested families, argument forwarding and restoration after SystemExit. No permanent network settings change. Previous owner-local inline equivalent successfully commissioned 15 PDFs; this new wrapper itself not live-tested. README's initial linked worktree was superseded by separate clone due to Git ownership mismatch. Keep the existing E:\Mimamsa-Corpus-Runner\checkout independent.

## CA-03 and CA-05

Review pipeline/shadow_assessment.py (blob b5bddfb34890ff48dc3a66aa84c698839916c8a8) and test_shadow_assessment.py (blob 96971aa0fa6450b1c9a5383f8d505b0e2c81078f). Seven tests passed with real synthetic PDFs under PyMuPDF 1.26.7 and injected classifier/quality functions. The production C13 classifier and pinned Windows PyMuPDF version have not been tested with this prototype. From the repository root run python -B -m pytest legal_knowledge/audit_work/C14-CA03-PIPELINE/test_shadow_assessment.py on a disposable checkout. No active pipeline integration. Inspect legacy extraction's stale text unlink in pipeline/extract.py, in addition to judgments.py and records.py. Require byte immutability of metadata, text, raw and historical ledger, no stale citations, no inferred OCR confidence. Check actual C13 classifier integration, text extraction choices, vector/hidden text, visual blank-page evidence, multilingual quality, metadata/hash binding, resource caps and deterministic assessment identity. All research eligibility remains false; no source authenticity or access clearance inferred.

Review pipeline/instrument_scope.py (blob a21d8a259d565dbf80f45ada12ebb19071f39337). Eight synthetic assertions passed: shared page split, unassigned full page, deterministic ordering, no anchor/research eligibility, overlap, out-of-range page, out-of-bounds box and NaN rejection (assertion count groups related checks). This validates candidate geometry only. No crop, indexing, OCR, source image binding or actual Army Act region approval. Validate actual page coordinate system, rotation/crop transforms, source SHA and page dimension binding before adoption; ensure unassigned partial regions cannot enter retrieval.

## Deliverable

One consolidated review of both updated draft PRs. Report exact reviewed heads, severity, reproducible evidence, corrections, independent test results, and whether local acquisition may advance to owner approval. Distinguish prototype tests from full integration tests. Do not merge or run the 534-judgment recovery. No legal status changes. Follow the original review packet for documentary batches and prior scope guard; review new source discovery separately. Return findings to the corpus coordinator, not Claude.
