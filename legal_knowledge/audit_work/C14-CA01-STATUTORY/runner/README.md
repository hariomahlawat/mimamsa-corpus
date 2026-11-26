# Local corpus runner — CA-01A commissioning (26 Nov 2026)

This is an isolated Windows-compatible deterministic runner, not an agent, service, scheduler or general downloader. Scope: retrieve and verify 15 existing public-source preservation objects from the private HF dataset, at the exact Cycle 13 preservation revision; report current main revision/file count and presence of each path. No HF writes, external source crawling, ingestion, OCR, rendering, automatic approval or modification of existing originals. The two historic source-pin mismatches and three subject-identity holds remain in force even if HF bytes match.

## Isolation

Use a detached Git worktree at E:\Mimamsa-Corpus-Runner\checkout, distinct from the primary Mimamsa checkout and Claude worktrees. Use E:\Mimamsa-Corpus-Runner\jobs for fresh outputs. No changes to PRISM, MAVI, PostgreSQL, .NET, Windows services, Git credentials or global settings. Do not run on the air-gapped deployment LAN. No automatic package installation. Python 3.13 with the already configured huggingface_hub package and HF credentials is required; a dataset-scoped read token or existing secure HF login is sufficient. Never paste credentials into commands, reports or chats.

## Launch

Obtain the full reviewed commit from PR #58; use the exact immutable commit, not an unreviewed branch tip. In a fresh PowerShell window:

    $Repo = 'E:\Dot Net Web Development\Mimamsa'
    $Root = 'E:\Mimamsa-Corpus-Runner'
    $Checkout = Join-Path $Root 'checkout'
    $Commit = '<full reviewed PR #58 commit>'
    if (Test-Path $Checkout) { throw 'Checkout exists; inspect, never delete or overwrite.' }
    New-Item -ItemType Directory -Force -Path $Root | Out-Null
    git -C $Repo fetch origin corpus/c14-ca01-reconciliation-20261126
    if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
    $env:GIT_LFS_SKIP_SMUDGE = '1'
    git -C $Repo worktree add --detach $Checkout $Commit
    if ($LASTEXITCODE -ne 0) { throw 'Worktree setup failed' }
    Set-Location $Checkout
    $Runner = 'legal_knowledge/audit_work/C14-CA01-STATUTORY/runner/corpus_runner.py'
    python $Runner
    if ($LASTEXITCODE -ne 0) { throw 'Dry run failed' }

Expected dry-run scope: 15 PDFs, 17,565,129 bytes, no network or writes from the runner. The fetch/worktree setup itself is a normal Git operation. If Python cannot import huggingface_hub, stop and report; do not install into an existing project environment.

After successful dry run and review of the pinned commit:

    $Job = Join-Path $Root ('jobs\ca01a-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    python $Runner --execute-read-only --expected-commit $Commit --output $Job
    $Result = $LASTEXITCODE
    Write-Host "Runner exit code: $Result"
    Write-Host "Report: $Job\verification.json"

Exit 0 means all historical preservation hashes match, all paths exist at the observed current head, and main revision stayed unchanged during the job. It does NOT establish primary-source authenticity, current law or page fidelity. Exit 1 means review required. A partial report survives ordinary per-file failures; preserve its directory even when unsuccessful. An initial infrastructure error may occur before a report is available. Do not delete failed runs; use a fresh directory after review. Send only verification.json to the coordinator, not original PDFs or secrets; the report has no token field. The source files stay local in the dedicated job directory.

## Validation performed

- Python syntax compilation in an isolated Linux container.
- Eight offline unittest cases passed using a synthetic file and mocked HF API/downloader: preservation match with prior hold intact, mismatch, missing path at HEAD, drift, public-dataset refusal, sanitized exception, wrong download path, Git blob hash.
- Remote Git blob SHA matches tested runner: d928c1501fde04cc77cb0476aeb65cc3d50381ca; test: 039e80f92af5237196e402c7bdad3842ca7a078e.
- All 15 actual candidate records independently checked for pinned revision, expected hash syntax, path format and no exact-anchor eligibility.
- Actual Windows, HF API, installed client and authenticated download commissioning remain outstanding; the offline tests are not integration or independent assurance.
- The local copy of this subset is not a verified full second backup. A full backup requires a separate plan, capacity check and restore rehearsal.

## Next jobs (NOT implemented or authorised by this runner)

CA-01A full page-marking/identity/anchor review, CA-01B exact-URL source acquisition after independent crawler security review, CA-03 adoption implementation, CA-02 judicial batches (separate explicit approval), and additive HF upload/re-download verification. Do not turn the runner into an unrestricted remote execution mechanism.
