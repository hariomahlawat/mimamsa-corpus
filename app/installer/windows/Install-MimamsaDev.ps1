<#
C16 Tranche B Stage 3 S3-C (B07): DEVELOPMENT/TEST installer for Windows. Not a production installer: target hardware and
edition (OG-1), production keys and the Authenticode certificate (OG-2), and operational migration/backup (OG-3) remain
owner gates. Run as Administrator, on a disposable host or CI runner ONLY (it creates services, virtual accounts, ACLs
and a firewall rule).

  Install-MimamsaDev.ps1 -Config <install.json> -WebPublish <dir> -ActivationPublish <dir> [-Evidence <dir>]

Idempotent: a re-run re-asserts services, ACLs and the firewall rule and never deletes or overwrites site data.
Steps:
  1. measured disk preflight + four-release layout (Mimamsa.Activation install-layout; refuses on failure)
  2. application release copied under <application>\web and <application>\activation
  3. services with VIRTUAL SERVICE ACCOUNTS (WD-5): MimamsaWeb (web), MimamsaActivation (activation tool, run as a
     bounded job service); manual start, recovery actions, unrestricted service SID
  4. store-root ownership and ACLs (CG-3): inheritance disabled; store roots OWNED by the activation identity, which
     may write them; the web identity may read but never write them; site data roots as documented below
  5. firewall: one inbound rule, TCP 443, for the web executable (nothing else inbound)
  6. evidence: icacls output, service configuration and the install record
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $Config,
    [Parameter(Mandatory)] [string] $WebPublish,
    [Parameter(Mandatory)] [string] $ActivationPublish,
    [string] $Evidence = ""
)
$ErrorActionPreference = 'Stop'
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw "Install-MimamsaDev.ps1 must run as Administrator (CI or a disposable test host only)" }

$cfg = Get-Content -Raw $Config | ConvertFrom-Json
if ($cfg.mode -notin @('development', 'test')) { throw "only development/test installations are supported" }
$R = $cfg.roots
$web = if ($cfg.identities.web) { $cfg.identities.web } else { 'MimamsaWeb' }
$act = if ($cfg.identities.activation) { $cfg.identities.activation } else { 'MimamsaActivation' }
$webSid = "NT SERVICE\$web"; $actSid = "NT SERVICE\$act"

# ---- 1. preflight + layout (the activation tool from the publish folder; nothing is written if the preflight fails)
$tool = Join-Path $ActivationPublish 'Mimamsa.Activation.exe'
$out = & $tool install-layout --config $Config --payload "application-web=application=$WebPublish" --payload "application-activation=application=$ActivationPublish"
$rec = $out | Select-Object -Last 1 | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $rec.ok) { throw "install-layout refused: $($rec.code) $($rec.message)" }

# ---- 2. application release (binaries only; versioned under the application root)
$appWeb = Join-Path $R.application 'web'; $appAct = Join-Path $R.application 'activation'
foreach ($p in @(@($WebPublish, $appWeb), @($ActivationPublish, $appAct))) {
    New-Item -ItemType Directory -Force $p[1] | Out-Null
    Copy-Item -Recurse -Force (Join-Path $p[0] '*') $p[1]
}
$webExe = Join-Path $appWeb 'Mimamsa.Web.exe'; $actExe = Join-Path $appAct 'Mimamsa.Activation.exe'
$jobs = Join-Path $R.config 'jobs'; New-Item -ItemType Directory -Force $jobs | Out-Null
$defaultJob = Join-Path $jobs 'activation-status.json'
if (-not (Test-Path $defaultJob)) {
    @{ out = (Join-Path $R.logs 'activation-status.json'); probes = @(); command = @('status', '--site', $R.site, '--development') } | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $defaultJob
}

# ---- 3. services under virtual accounts
function Set-MimamsaService([string]$Name, [string]$BinPath, [string]$Display) {
    if (-not (Get-Service -Name $Name -ErrorAction SilentlyContinue)) {
        New-Service -Name $Name -BinaryPathName $BinPath -DisplayName $Display -StartupType Manual | Out-Null
    } else {
        sc.exe config $Name binPath= $BinPath | Out-Null
    }
    sc.exe config $Name obj= "NT SERVICE\$Name" | Out-Null
    sc.exe sidtype $Name unrestricted | Out-Null
    sc.exe failure $Name reset= 60 actions= restart/2000 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "service configuration failed for $Name" }
}
Set-MimamsaService $web "`"$webExe`"" 'Mimamsa web service (development)'
Set-MimamsaService $act "`"$actExe`" service-job --job `"$defaultJob`"" 'Mimamsa activation tool (development job service)'
# the service SIDs must exist before they can appear in ACLs
foreach ($s in @($web, $act)) { $null = (New-Object Security.Principal.NTAccount("NT SERVICE\$s")).Translate([Security.Principal.SecurityIdentifier]) }

# ---- 4. ACLs (inheritance disabled everywhere; explicit grants only)
$admins = '*S-1-5-32-544'; $system = '*S-1-5-18'
function Set-Acl2([string]$Path, [string[]]$Grants, [string]$Owner = "") {
    New-Item -ItemType Directory -Force $Path | Out-Null
    $args1 = @($Path, '/inheritance:r', '/grant:r', "${system}:(OI)(CI)F", "${admins}:(OI)(CI)F") + ($Grants | ForEach-Object { @('/grant:r', $_) })
    & icacls @args1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "icacls failed on $Path" }
    if ($Owner) { & icacls $Path /setowner $Owner /T /C /Q | Out-Null; if ($LASTEXITCODE -ne 0) { throw "setowner failed on $Path" } }
    # replace explicit grants of children with inherited ones (a re-run converges), without touching data
    & icacls "$Path\*" /reset /T /C /Q 2>$null | Out-Null
}
# application release: everyone reads and executes, nobody but administrators writes
Set-Acl2 $R.application @("${webSid}:(OI)(CI)RX", "${actSid}:(OI)(CI)RX")
# knowledge and intelligence store roots: owned and written by the activation identity; the web identity reads only
foreach ($k in @('site', 'text_store', 'search_index', 'vectors', 'import')) {
    Set-Acl2 $R.$k @("${actSid}:(OI)(CI)M", "${webSid}:(OI)(CI)RX") $actSid
}
# the web process's exclusion reader persists its high-water mark (monotone check, I-6): that one directory only
& icacls (Join-Path $R.site 'activation-state') /grant "${webSid}:(OI)(CI)M" | Out-Null
# site data roots
Set-Acl2 $R.uploads @("${webSid}:(OI)(CI)M", "${actSid}:(OI)(CI)RX") $actSid
Set-Acl2 $R.config @("${actSid}:(OI)(CI)M", "${webSid}:(OI)(CI)RX") $actSid
Set-Acl2 $R.backup @("${actSid}:(OI)(CI)M") $actSid
Set-Acl2 $R.logs @("${webSid}:(OI)(CI)M", "${actSid}:(OI)(CI)M") $actSid
Set-Acl2 $R.scratch @("${actSid}:(OI)(CI)M") $actSid
$webScratch = Join-Path $R.scratch 'web'; New-Item -ItemType Directory -Force $webScratch | Out-Null
& icacls $webScratch /grant "${webSid}:(OI)(CI)M" | Out-Null
# secrets (role passwords written by db-setup): administrators and the activation identity only
$secrets = Join-Path $R.config 'secrets'
if (Test-Path $secrets) { & icacls $secrets /inheritance:r /grant:r "${system}:(OI)(CI)F" "${admins}:(OI)(CI)F" "${actSid}:(OI)(CI)R" | Out-Null }

# ---- 5. firewall: inbound TCP 443 for the web executable only
$rule = 'Mimamsa web HTTPS (development)'
if (-not (Get-NetFirewallRule -DisplayName $rule -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $rule -Group 'Mimamsa' -Direction Inbound -Protocol TCP -LocalPort 443 -Program $webExe -Action Allow -Profile Any | Out-Null
}

# ---- 6. evidence
if ($Evidence) {
    New-Item -ItemType Directory -Force $Evidence | Out-Null
    $acl = foreach ($k in @('application', 'site', 'text_store', 'search_index', 'vectors', 'import', 'uploads', 'config', 'backup', 'logs', 'scratch')) {
        "== $k ($($R.$k))"; & icacls $R.$k; "owner: " + (Get-Acl $R.$k).Owner; "protected: " + (Get-Acl $R.$k).AreAccessRulesProtected
    }
    $acl | Out-File -Encoding utf8 (Join-Path $Evidence 'icacls.txt')
    foreach ($s in @($web, $act)) { sc.exe qc $s | Out-File -Encoding utf8 (Join-Path $Evidence "sc-qc-$s.txt"); sc.exe qsidtype $s | Out-File -Append -Encoding utf8 (Join-Path $Evidence "sc-qc-$s.txt") }
    Get-NetFirewallRule -Group 'Mimamsa' | Select-Object DisplayName, Direction, Action, Enabled | Out-File -Encoding utf8 (Join-Path $Evidence 'firewall.txt')
    Copy-Item (Join-Path $R.config 'INSTALL_RECORD.json') $Evidence -Force
}
"installed: web=$webSid activation=$actSid application=$($R.application)"
