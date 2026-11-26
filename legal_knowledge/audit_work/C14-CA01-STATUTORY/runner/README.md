# Local corpus runner — CA-01A commissioning (26 Nov 2026)

The draft runner supports an offline inventory dry run for 15 existing public-source preservation objects at one exact Cycle 13 revision. Live preservation reads and source acquisition are held in this draft. The historical preservation run compared SHA-256, MD5 and size at the preservation revision, and reported path presence at the observed current revision. Both historic source-pin mismatch holds and all three subject-identity holds still apply.

## Isolation and supported Windows checkout

The commissioned runner uses the **standalone independent clone** at E:\Mimamsa-Corpus-Runner\checkout, not a linked worktree. Job outputs are under E:\Mimamsa-Corpus-Runner\jobs and PDF-review dependencies under E:\Mimamsa-Corpus-Runner\.venv. The initial linked-worktree attempt failed Git ownership validation; no safe.directory exception or ownership change is required. Do not use Claude's checkout, PRISM, MAVI or an air-gapped deployment network. Do not change global network settings. No automatic dependency installation.

For a new installation only, clone with GIT_LFS_SKIP_SMUDGE=1, --no-checkout, --single-branch and --filter=blob:none. Check out the exact independently reviewed full commit using git checkout --detach. Never overwrite the commissioned clone. For the existing runner, fetch the corpus branch, verify a clean checkout, and detach to the approved commit. The original successful read-only commissioning ran at 11aee06cf3b4fb1d141f5e5fe36ff1e7834286b8; newer commits are not automatically commissioned.

## Offline preservation dry run

    Set-Location 'E:\Mimamsa-Corpus-Runner\checkout'
    $Runner = 'legal_knowledge/audit_work/C14-CA01-STATUTORY/runner/corpus_runner.py'
    python -B $Runner

Expected dry-run scope: 15 PDFs, 17,565,129 bytes. It reads the pinned inventory metadata and requires neither an HF package nor credentials. The optional `launch_ipv4.py` wrapper applies a process-local resolver override and Xet setting. Its inline predecessor ran during historical commissioning. The wrapper has offline checks and still needs a native Windows sign-off for operational use.

`--execute-read-only` and `--execute-approved` are refusal paths on this draft. The older `verify_preserved_copies.py` is an offline historical inventory checker. Operational commissioning requires separate owner approval and evidence for the reviewed commit, Windows version, Python and HF SDK versions, credential scope, SDK logging/redaction, and a dedicated ACL-controlled job root with native handle and reparse-point checks. Acquisition also requires independently provisioned owner and reviewer trust pins, a process-wide deadline that covers blocking calls, and approved egress controls. Both the six-source and 23 archive proposals remain disabled.

The runner checks the inventory against its Git blob and canonicalizes CRLF to LF if needed. Its inventory SHA-256 covers those same verified bytes. Source and generated receipt SHA-256 values cover their exact raw bytes. This distinction matters when checking receipts copied between platforms. Current-head byte integrity would require a separate comparison of bytes read at the current pinned revision. A full backup requires separate coverage and restore evidence.

## Validation performed

- The following records describe the original runner and its commissioning; see the integration tranche receipt for updated synthetic coverage.
- Eight offline unittest cases passed using a synthetic file and mocked HF API/downloader: preservation match with prior hold intact, mismatch, missing path at HEAD, drift, public-dataset refusal, sanitized exception, wrong download path, Git blob hash.
- Remote Git blob SHA matches tested runner: d928c1501fde04cc77cb0476aeb65cc3d50381ca; test: 039e80f92af5237196e402c7bdad3842ca7a078e.
- All 15 actual candidate records independently checked for pinned revision, expected hash syntax, path format and no exact-anchor eligibility.
- Native path isolation, runtime pins, SDK logging controls and independently verified current-revision bytes remain outstanding for the corrective draft.
- The local copy of this subset is not a verified full second backup. A full backup requires a separate plan, capacity check and restore rehearsal.

## Next jobs (NOT implemented or authorised by this runner)

CA-01A full page-marking/identity/anchor review, CA-01B exact-URL source acquisition after independent crawler security review, CA-03 adoption implementation, CA-02 judicial batches (separate explicit approval), and additive HF upload/re-download verification. Do not turn the runner into an unrestricted remote execution mechanism.
