# Local corpus runner — CA-01A commissioning (26 Nov 2026)

This is an isolated Windows-compatible deterministic runner, not an agent, service, scheduler or general downloader. Scope: retrieve and verify 15 existing public-source preservation objects from the private HF dataset, at the exact Cycle 13 preservation revision; report current main revision/file count and presence of each path. No HF writes, external source crawling, ingestion, OCR, rendering, automatic approval or modification of existing originals. The two historic source-pin mismatches and three subject-identity holds remain in force even if HF bytes match.

## Isolation and supported Windows checkout

The commissioned runner uses the **standalone independent clone** at E:\Mimamsa-Corpus-Runner\checkout, not a linked worktree. Job outputs are under E:\Mimamsa-Corpus-Runner\jobs and PDF-review dependencies under E:\Mimamsa-Corpus-Runner\.venv. The initial linked-worktree attempt failed Git ownership validation; no safe.directory exception or ownership change is required. Do not use Claude's checkout, PRISM, MAVI or an air-gapped deployment network. Do not change global network settings. No automatic dependency installation.

For a new installation only, clone with GIT_LFS_SKIP_SMUDGE=1, --no-checkout, --single-branch and --filter=blob:none. Check out the exact independently reviewed full commit using git checkout --detach. Never overwrite the commissioned clone. For the existing runner, fetch the corpus branch, verify a clean checkout, and detach to the approved commit. The original successful read-only commissioning ran at 11aee06cf3b4fb1d141f5e5fe36ff1e7834286b8; newer commits are not automatically commissioned.

## Read-only preservation command

    Set-Location 'E:\Mimamsa-Corpus-Runner\checkout'
    $Runner = 'legal_knowledge/audit_work/C14-CA01-STATUTORY/runner/launch_ipv4.py'
    python -B $Runner

Expected dry-run scope: 15 PDFs, 17,565,129 bytes. The optional IPv4 launcher confines the resolver override and Xet disabling to the process; certificate verification remains enabled. Its inline predecessor was commissioned successfully; the wrapper has offline tests but no live Windows run yet. Use the existing HF-enabled Python, not the PDF-only virtual environment unless separately configured.

An actual run requires a separately reviewed commit, read-only credential, fresh job directory and explicit authorization. Do not rerun merely to validate this README. Exact command format after approval:

    python -B $Runner --execute-read-only --expected-commit $Commit --output $Job

The primary runner canonicalizes CRLF to LF only to check the pinned Git inventory blob; successful receipt and source byte hashes are exact raw digests and must not be newline-normalized. Historical preservation hashes are not current-HF byte checks. Only report current-head existence as presence. The older verify_preserved_copies.py is historical/noncommissioned; do not use it as an alternate live runner. No upload or legal promotion.

The six-source acquisition utility is explicitly interlocked and cannot execute even if JSON enable flags are changed. Its approval verifier is not a deployed trust configuration. The 23 archive proposals also remain disabled. Native Windows ACL, reparse-point, SDK log and current-head verification requirements remain outstanding.

## Validation performed

- Python syntax compilation in an isolated Linux container.
- Eight offline unittest cases passed using a synthetic file and mocked HF API/downloader: preservation match with prior hold intact, mismatch, missing path at HEAD, drift, public-dataset refusal, sanitized exception, wrong download path, Git blob hash.
- Remote Git blob SHA matches tested runner: d928c1501fde04cc77cb0476aeb65cc3d50381ca; test: 039e80f92af5237196e402c7bdad3842ca7a078e.
- All 15 actual candidate records independently checked for pinned revision, expected hash syntax, path format and no exact-anchor eligibility.
- Actual Windows, HF API, installed client and authenticated download commissioning remain outstanding; the offline tests are not integration or independent assurance.
- The local copy of this subset is not a verified full second backup. A full backup requires a separate plan, capacity check and restore rehearsal.

## Next jobs (NOT implemented or authorised by this runner)

CA-01A full page-marking/identity/anchor review, CA-01B exact-URL source acquisition after independent crawler security review, CA-03 adoption implementation, CA-02 judicial batches (separate explicit approval), and additive HF upload/re-download verification. Do not turn the runner into an unrestricted remote execution mechanism.
