<#
C16 S3-C (B07) acceptance on a Windows CI runner (Administrator; never on the owner's host):
  - virtual accounts: each probe job runs AS the service (NT SERVICE\<name>), proven by the token name and SID it reports
  - ACL probe matrix: each identity attempts every write; the forbidden ones fail and the allowed ones succeed
  - the activation tool runs real commands under its virtual account
  - store roots: inheritance disabled, owned by the activation identity
  - firewall: the only Mimamsa inbound rule is TCP 443
  - a reinstall keeps site data; uninstall removes services and binaries and keeps site data
  Test-MimamsaDevInstall.ps1 -Config <install.json> -WebPublish <dir> -ActivationPublish <dir> -Out <dir>
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $Config,
    [Parameter(Mandatory)] [string] $WebPublish,
    [Parameter(Mandatory)] [string] $ActivationPublish,
    [Parameter(Mandatory)] [string] $Out
)
$ErrorActionPreference = 'Stop'
trap { Write-Host "ERROR: $_"; Write-Host $_.ScriptStackTrace; break }
New-Item -ItemType Directory -Force $Out | Out-Null
$cfg = Get-Content -Raw $Config | ConvertFrom-Json
$R = $cfg.roots
$web = if ($cfg.identities.web) { $cfg.identities.web } else { 'MimamsaWeb' }
$act = if ($cfg.identities.activation) { $cfg.identities.activation } else { 'MimamsaActivation' }
$actExe = Join-Path $R.application 'activation\Mimamsa.Activation.exe'
$failures = New-Object System.Collections.Generic.List[string]
function Assert-That([bool]$ok, [string]$what) { if (-not $ok) { $failures.Add($what); Write-Host "FAIL $what" } else { Write-Host "ok   $what" } }

# ---------------------------------------------------------------- run a job AS a service's virtual account
function Invoke-AsService([string]$Service, [object[]]$Probes, [string[]]$Command) {
    $res = Join-Path $R.logs "probe-$Service.json"
    if (Test-Path $res) { Remove-Item $res -Force }
    $job = Join-Path $R.config "jobs\probe-$Service.json"
    $j = @{ out = $res; probes = $Probes }
    if ($Command) { $j.command = $Command }
    $j | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $job
    $orig = (Get-CimInstance Win32_Service -Filter "Name='$Service'").PathName
    sc.exe config $Service binPath= "`"$actExe`" service-job --job `"$job`"" | Out-Null
    try {
        Start-Service $Service -ErrorAction SilentlyContinue
        for ($i = 0; $i -lt 120 -and -not (Test-Path $res); $i++) { Start-Sleep -Milliseconds 500 }
        for ($i = 0; $i -lt 60 -and (Get-Service $Service).Status -ne 'Stopped'; $i++) { Start-Sleep -Milliseconds 500 }
    } finally { sc.exe config $Service binPath= $orig | Out-Null }
    if (-not (Test-Path $res)) { throw "probe job for $Service produced no result" }
    Get-Content -Raw $res | ConvertFrom-Json
}

$site = $R.site
$targets = [ordered]@{
    application = $R.application; site = $site; generations = (Join-Path $site 'generations'); vault = (Join-Path $site 'vault')
    journal = (Join-Path $site 'journal'); exclusions = (Join-Path $site 'exclusions'); 'activation-log' = (Join-Path $site 'activation-log')
    'activation-state' = (Join-Path $site 'activation-state'); models = (Join-Path $site 'models'); text_store = $R.text_store
    search_index = $R.search_index; vectors = $R.vectors; import = $R.import; uploads = $R.uploads; config = $R.config
    backup = $R.backup; logs = $R.logs; scratch = $R.scratch; 'scratch-web' = (Join-Path $R.scratch 'web')
}
# expected write permission per identity (true = may write)
$webWrites = @('activation-state', 'uploads', 'logs', 'scratch-web')
$actDenied = @('application')
$probes = foreach ($k in $targets.Keys) { @{ kind = 'write'; path = $targets[$k] }; @{ kind = 'read'; path = $targets[$k] } }

$matrix = @()
foreach ($svc in @($web, $act)) {
    $cmd = if ($svc -eq $act) { @('install-preflight', '--config', $Config) } else { $null }
    $pr = Invoke-AsService $svc $probes $cmd   # NB: not $r - PowerShell names are case-insensitive and $R holds the roots
    $pr | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 (Join-Path $Out "probe-$svc.json")
    Assert-That ($pr.identity -eq "NT SERVICE\$svc") "$svc job ran under its virtual account (got $($pr.identity))"
    $sid = (New-Object Security.Principal.NTAccount("NT SERVICE\$svc")).Translate([Security.Principal.SecurityIdentifier]).Value
    Assert-That ($pr.sid -eq $sid) "$svc token SID is the service SID $sid"
    foreach ($k in $targets.Keys) {
        $w = $pr.probes | Where-Object { $_.kind -eq 'write' -and $_.path -eq $targets[$k] }
        $rd = $pr.probes | Where-Object { $_.kind -eq 'read' -and $_.path -eq $targets[$k] }
        $expectWrite = if ($svc -eq $web) { $webWrites -contains $k } else { -not ($actDenied -contains $k) }
        $expectRead = if ($svc -eq $web) { $k -notin @('backup', 'scratch') } else { $true }
        Assert-That ($w.allowed -eq $expectWrite) "$svc write $k expected=$expectWrite actual=$($w.allowed)"
        Assert-That ($rd.allowed -eq $expectRead) "$svc read $k expected=$expectRead actual=$($rd.allowed)"
        $matrix += [pscustomobject]@{ identity = $svc; target = $k; write_expected = $expectWrite; write_actual = $w.allowed; read_expected = $expectRead; read_actual = $rd.allowed }
    }
    if ($svc -eq $act) { Assert-That ($pr.command_exit -eq 0) "activation identity ran install-preflight as itself: $($pr.command_stdout)" }
}
$matrix | ConvertTo-Json -Depth 3 | Out-File -Encoding utf8 (Join-Path $Out 'acl-probe-matrix.json')

# ---------------------------------------------------------------- ownership, inheritance
foreach ($k in @('site', 'text_store', 'search_index', 'vectors', 'import')) {
    $a = Get-Acl $R.$k
    Assert-That ($a.Owner -eq "NT SERVICE\$act") "$k owned by the activation identity (owner $($a.Owner))"
    Assert-That $a.AreAccessRulesProtected "$k inheritance disabled"
    $webRule = $a.Access | Where-Object { $_.IdentityReference -eq "NT SERVICE\$web" }
    Assert-That (-not ($webRule | Where-Object { $_.FileSystemRights.ToString() -match 'Write|Modify|FullControl' })) "$k grants the web identity no write right"
    $broad = $a.Access | Where-Object { $_.IdentityReference -match 'Everyone|Users|Authenticated Users' }
    Assert-That (-not $broad) "$k has no Everyone/Users/Authenticated Users entry"
}

# ---------------------------------------------------------------- firewall: TCP 443 only
$rules = @(Get-NetFirewallRule -Group 'Mimamsa' -ErrorAction SilentlyContinue | Where-Object { $_.Direction -eq 'Inbound' -and $_.Action -eq 'Allow' })
$ports = $rules | ForEach-Object { ($_ | Get-NetFirewallPortFilter).LocalPort }
Assert-That ($rules.Count -eq 1 -and ($ports -join ',') -eq '443') "the only Mimamsa inbound rule is TCP 443 (rules $($rules.Count), ports $($ports -join ','))"

# ---------------------------------------------------------------- reinstall keeps site data; uninstall keeps site data
$sentinels = @((Join-Path $site 'journal\SENTINEL.txt'), (Join-Path $R.uploads 'SENTINEL.txt'), (Join-Path $site 'vault\SENTINEL.txt'), (Join-Path $R.backup 'SENTINEL.txt'))
foreach ($s in $sentinels) { Set-Content -Path $s -Value "keep $s" }
& (Join-Path $PSScriptRoot 'Install-MimamsaDev.ps1') -Config $Config -WebPublish $WebPublish -ActivationPublish $ActivationPublish | Out-Null
foreach ($s in $sentinels) { Assert-That ((Get-Content $s) -eq "keep $s") "reinstall kept $s" }
& (Join-Path $PSScriptRoot 'Uninstall-MimamsaDev.ps1') -Config $Config | Out-Null
Assert-That (-not (Get-Service $web -ErrorAction SilentlyContinue) -and -not (Get-Service $act -ErrorAction SilentlyContinue)) "uninstall removed the services"
Assert-That (-not (Test-Path (Join-Path $R.application 'web'))) "uninstall removed the application binaries"
foreach ($s in $sentinels) { Assert-That ((Test-Path $s) -and (Get-Content $s) -eq "keep $s") "uninstall kept $s" }
Assert-That (@(Get-NetFirewallRule -Group 'Mimamsa' -ErrorAction SilentlyContinue).Count -eq 0) "uninstall removed the firewall rule"

@{ failures = $failures; checks_failed = $failures.Count } | ConvertTo-Json | Out-File -Encoding utf8 (Join-Path $Out 'install-acceptance.json')
if ($failures.Count -gt 0) { throw "$($failures.Count) installer acceptance check(s) failed" }
"installer acceptance: all checks passed"
