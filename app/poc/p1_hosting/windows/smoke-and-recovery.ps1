<#  Smoke test + restart + crash-recovery test for one installed PoC service. Writes a JSON result.
    Usage: .\smoke-and-recovery.ps1 -Name MimamsaPocApi -Base http://127.0.0.1:5081 -Out result.json  #>
param([Parameter(Mandatory)] [string] $Name, [Parameter(Mandatory)] [string] $Base, [Parameter(Mandatory)] [string] $Out)
$ErrorActionPreference = "Stop"
$H = @{ Authorization = "Bearer dev-token" }
$r = [ordered]@{ service = $Name; checks = [ordered]@{} }
function Wait-Healthy([int]$timeoutSec = 60) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt $timeoutSec) {
    try { if ((Invoke-WebRequest "$Base/health" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { return $sw.Elapsed.TotalSeconds } } catch {}
    Start-Sleep -Milliseconds 200
  }
  throw "service $Name not healthy after $timeoutSec s"
}
function Get-SvcPid { (Get-CimInstance Win32_Service -Filter "Name='$Name'").ProcessId }

$r.checks.start_to_healthy_s = Wait-Healthy
$r.checks.account = (Get-CimInstance Win32_Service -Filter "Name='$Name'").StartName
try { Invoke-WebRequest "$Base/api/search?q=army" -UseBasicParsing | Out-Null; $r.checks.auth_401 = $false }
catch { $r.checks.auth_401 = ($_.Exception.Response.StatusCode.value__ -eq 401) }
$s = Invoke-RestMethod "$Base/api/search?q=disability%20pension&limit=3" -Headers $H
$r.checks.search_results = @($s.results).Count
$m = Invoke-RestMethod "$Base/api/documents/fx-army-act" -Headers $H
$r.checks.metadata_ok = ($m.doc_id -eq "fx-army-act")
$p = Invoke-WebRequest "$Base/api/documents/fx-army-act/pdf" -Headers ($H + @{ Range = "bytes=0-7" }) -UseBasicParsing
$r.checks.pdf_range_status = $p.StatusCode
$r.checks.pdf_range_header = "$($p.Headers['Content-Range'])"

# graceful restart
$sw = [Diagnostics.Stopwatch]::StartNew(); Restart-Service $Name; $null = Wait-Healthy
$r.checks.restart_to_healthy_s = [math]::Round($sw.Elapsed.TotalSeconds, 2)

# crash recovery: kill the service process; SCM failure actions must restart it
$pid1 = Get-SvcPid; Stop-Process -Id $pid1 -Force
$sw = [Diagnostics.Stopwatch]::StartNew(); Start-Sleep -Seconds 1
$pid2 = $null
while ($sw.Elapsed.TotalSeconds -lt 60) { $pid2 = Get-SvcPid; if ($pid2 -and $pid2 -ne 0 -and $pid2 -ne $pid1) { break }; Start-Sleep -Milliseconds 250 }
$null = Wait-Healthy
$r.checks.crash_recovered = ($pid2 -and $pid2 -ne $pid1)
$r.checks.crash_to_healthy_s = [math]::Round($sw.Elapsed.TotalSeconds, 2)
$r.checks.pid_before = $pid1; $r.checks.pid_after = $pid2
$r | ConvertTo-Json -Depth 4 | Tee-Object -FilePath $Out
if (-not ($r.checks.auth_401 -and $r.checks.search_results -ge 1 -and $r.checks.metadata_ok -and $r.checks.pdf_range_status -eq 206 -and $r.checks.crash_recovered)) { throw "checks failed for $Name" }
