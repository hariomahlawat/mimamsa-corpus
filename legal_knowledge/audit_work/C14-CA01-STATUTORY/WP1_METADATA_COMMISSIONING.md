# WP1 metadata-only commissioning

This procedure covers one immutable revision of the private Hugging Face dataset `hariomahlawat/mimamsa-corpus`. The operation reads credential scope, revision identity, and tree metadata for the seven stores in [the plan](WP1_METADATA_COMMISSIONING_PLAN.json). It reconciles PDF metadata for those stores and records provider-asserted LFS SHA-256 claims. It does not establish local-store coverage, original-byte integrity or acquisition eligibility.

## Owner preparation

1. In the Hugging Face dataset’s **Files and versions** view, select the intended commit from **History** and copy its full 40-character commit ID. The history reference for the dataset’s main branch is [commit history](https://huggingface.co/datasets/hariomahlawat/mimamsa-corpus/commits/main). A copied full commit ID is the input for review. Do not open, preview, resolve or download any file. The plan’s historical observation is not an approval or current-head assertion.
2. In HF token settings, prepare a short-lived fine-grained token with repository-content read access for this dataset alone. Keep global permissions and gated-repository access disabled. Record this scope and the owner approval separately. The worker checks that the token being used proves those exact grants through the credential endpoint. If the provider omits the required grant evidence, the job returns incomplete without asking for any tree. Do not use a generic read token or a token with wider scope.
3. Establish the owner’s Ed25519 public-key fingerprint independently of the job files. The approved value is SHA-256 of the 32 raw public-key bytes, in lowercase hexadecimal. Keep the signing key in the owner’s controlled signing environment. Confirm direct outbound TLS to `huggingface.co:443` on the commissioning workstation and use an owner-controlled local checkout and private job root.

## Exact PowerShell procedure

Run in **Windows PowerShell 5.1** as the dedicated owner account on a local NTFS drive. Supply the full corrected PR SHA recorded in the acceptance report and the separately reviewed full HF commit ID. The code checkout, venv and approval files below are siblings of the private receipt directory. Use new paths on a dedicated owner-controlled parent. Keep Git line-ending conversion disabled for this checkout.

```powershell
$ErrorActionPreference = 'Stop'
$Base = 'E:\Mimamsa-Corpus-Runner'
$Checkout = Join-Path $Base 'wp1-reviewed-checkout'
$Venv = Join-Path $Base 'wp1-python'
$Jobs = Join-Path $Base 'wp1-private-jobs'
$Approved = Join-Path $Base 'wp1-owner-approval'
$Reviewed = Read-Host 'Full corrected GitHub PR commit SHA from report'
$Revision = Read-Host 'Full reviewed HF dataset commit SHA'
$Job = 'wp1-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
if ($Reviewed -cnotmatch '^[0-9a-f]{40}$' -or $Revision -cnotmatch '^[0-9a-f]{40}$') { throw 'Exact immutable SHA required' }

if (-not (Test-Path -LiteralPath $Base -PathType Container)) { throw 'Provision the owner-controlled parent directory first' }
foreach ($Path in @($Checkout, $Venv, $Jobs, $Approved)) {
    if (Test-Path -LiteralPath $Path) { throw 'Use fresh WP1 locations' }
}
$Sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$PrivateACL = New-Object System.Security.AccessControl.DirectorySecurity
$PrivateACL.SetSecurityDescriptorSddlForm("O:${Sid}D:P(A;OICI;FA;;;${Sid})(A;OICI;FA;;;SY)")
[void][System.IO.Directory]::CreateDirectory($Jobs, $PrivateACL)
[void][System.IO.Directory]::CreateDirectory($Approved, $PrivateACL)
$Jobs = (Get-Item -LiteralPath $Jobs).FullName

git clone --config core.autocrlf=false --filter=blob:none --no-checkout --single-branch `
  --branch corpus/c14-ca01-reconciliation-20261126 https://github.com/hariomahlawat/mimamsa-corpus.git $Checkout
if ($LASTEXITCODE -ne 0) { throw 'Git clone failed' }
$Area = 'legal_knowledge/audit_work/C14-CA01-STATUTORY'
git -C $Checkout sparse-checkout set --no-cone "/$Area/runner/" "/$Area/WP1_METADATA_COMMISSIONING_PLAN.json" '/config/restricted_material.json' '/scripts/restricted_material.py'
if ($LASTEXITCODE -ne 0) { throw 'Sparse checkout setup failed' }
git -C $Checkout checkout --detach $Reviewed
if ($LASTEXITCODE -ne 0) { throw 'Exact Git checkout failed' }

py -3.12 -m venv $Venv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 venv creation failed' }
$Python = Join-Path $Venv 'Scripts\python.exe'
& $Python -m pip install --disable-pip-version-check --only-binary=:all: 'cryptography==50.0.2'
if ($LASTEXITCODE -ne 0) { throw 'Approval runtime installation failed' }

$Runner = Join-Path $Checkout "$Area/runner/hf_metadata_job.py"
$Boot = "import runpy,sys; from pathlib import Path; p=sys.argv.pop(1); sys.path.append(str(Path(p).parent)); runpy.run_path(p,run_name='__main__')"
$Approval = Join-Path $Approved 'wp1.json'
$Signature = Join-Path $Approved 'wp1.sig'
$ScopeArgs = @('--revision', $Revision, '--code-commit', $Reviewed, '--jobs-root', $Jobs, '--job-name', $Job, '--approval', $Approval)
& $Python -I -B -c $Boot $Runner --prepare-approval @ScopeArgs
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare a checkout-bound approval' }
```

The owner reviews the unsigned JSON against the seven roots, immutable HF revision, exact corrected code and plan, read-only credential grant and intended private job. Sign the exact file bytes with the established Ed25519 key within the four-hour approval interval. On the owner’s controlled signing system with OpenSSL 3 the signing command is:

```powershell
openssl pkeyutl -sign -rawin -inkey $OwnerPrivatePem -in $Approval -out $Signature
if ($LASTEXITCODE -ne 0) { throw 'Owner signing failed' }
```

Place the signature in `$Signature` and the established public PEM in `$OwnerPublicPem`. Obtain the trusted fingerprint from the owner’s independently controlled record. Run only after owner approval:

```powershell
$OwnerPublicPem = Read-Host 'Path to the established owner Ed25519 public PEM'
$OwnerFingerprint = Read-Host 'Independently trusted SHA-256 of the raw 32-byte public key'
& $Python -I -B -c $Boot $Runner --execute-metadata-only @ScopeArgs `
  --signature $Signature --owner-key $OwnerPublicPem --owner-key-sha256 $OwnerFingerprint
$Wp1Exit = $LASTEXITCODE
```

The token prompt is interactive and hidden. Do not pass a token as a command argument, environment variable or file. The worker performs no retry and receives the token only in a local pipe. Revoke the temporary token after the run. To retry an incomplete job, preserve its receipt and obtain a new approval for a new job name.

## Evidence and exit status

- **0** means the seven approved remote store inventories reconciled. The console prints only an aggregate status, exact revision, receipt digest and false acquisition eligibility.
- **1** means incomplete. The private receipt contains a fixed failure code and either partial validated inventory or a null inventory. An incomplete receipt is never usable as complete coverage.
- **2** means refusal before an accepted private receipt, such as failed approval, checkout, directory, or publication verification. Console diagnostics are fixed and carry no local location or identity.

The private file is `<jobs root>\<approved job>\metadata_inventory.json`. The envelope contains `schema`, `operation`, `repository`, `revision`, `code_commit`, `approval_sha256`, exact runtime and plan digests, register and guard pins, `status`, `failure`, and `inventory`. The latter, when available, has per-store counts and provider digest claims with a deterministic inventory digest. The outer file’s SHA-256 includes its final LF. Share only the aggregate status, revision, counts and digests with the reviewer. Keep detailed path and hash rows in the private receipt.

The native sink requires a canonical fixed NTFS directory with a protected DACL for the owner account and SYSTEM. A fresh private child and no-replace publication are mandatory. The worker has a 180-second metadata budget, a 195-second supervised process deadline, and bounded stdout. The exact routes exclude file resolution, downloads and writes. Acquisition and preservation retain their separate interlocks.
