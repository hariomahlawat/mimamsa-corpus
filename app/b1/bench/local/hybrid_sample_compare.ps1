# C14 S4: real sample, same build, hybrid off vs on (cached vectors, calibrated floor). Numbers only.
param([ValidateSet('off', 'on')][string]$Mode)
$W = 'E:\Dot Net Web Development\Mimamsa\.claude\worktrees\agent-a83e3eb3860d132e3'
$D = 'E:\Mimamsa-Data'; $S = "$D\c14s4"
$py = "$D\venv\Scripts\python.exe"
$env:PGPASSWORD = Get-Content -Raw "$D\secrets\pg_superuser.pw"
$psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
& $psql -h 127.0.0.1 -p 55499 -U mimamsa_su -d postgres -q -c "DROP DATABASE IF EXISTS c14s4_hyb WITH (FORCE);" -c "CREATE DATABASE c14s4_hyb OWNER mimamsa;"
Remove-Item Env:PGPASSWORD
$app = Get-Content -Raw "$D\secrets\pg_mimamsa.pw"
$dsn = "Host=127.0.0.1;Port=55499;Username=mimamsa;Password=$app;Database=c14s4_hyb;Maximum Pool Size=10"
$dll = "$W\app\b1\src\Mimamsa.Web\bin\Release\net10.0\Mimamsa.Web.dll"
$pw = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(18))
$env:MIMAMSA_NEW_PASSWORD = $pw; $env:Mimamsa__Db = $dsn; & dotnet $dll --add-user s4eval User | Out-Null; Remove-Item Env:MIMAMSA_NEW_PASSWORD
$env:ASPNETCORE_URLS = 'http://127.0.0.1:5442'; $env:Mimamsa__Site = "$D\sample\site"; $env:Mimamsa__RestrictedRegister = "$D\restricted_material.json"; $env:Mimamsa__Diagnostics__Enabled = 'true'
if ($Mode -eq 'on') {
  $env:Mimamsa__Hybrid__Enabled = 'true'; $env:Mimamsa__Hybrid__ModelDir = "$D\models\multilingual-e5-small\614241f622f53c4eeff9890bdc4f31cfecc418b3"
  $env:Mimamsa__Hybrid__ModelSha256 = 'ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665'; $env:Mimamsa__Hybrid__CacheDir = "$S\embcache"; $env:Mimamsa__Hybrid__MinSimilarity = '0.8579'
}
$t = [Diagnostics.Stopwatch]::StartNew()
$p = Start-Process dotnet -ArgumentList "`"$dll`"" -WorkingDirectory "$S\pwrun\webroot" -PassThru -WindowStyle Hidden -RedirectStandardOutput "$S\hyb-$Mode.log" -RedirectStandardError "$S\hyb-$Mode.err"
while ($true) { Start-Sleep -Milliseconds 250; if ($p.HasExited) { throw "exited" }; try { if ((Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5442/health -TimeoutSec 2).StatusCode -eq 200) { break } } catch {} }
$startup = $t.Elapsed.TotalSeconds
try {
  $env:B1_URL = 'http://127.0.0.1:5442'; $env:B1_USER = 's4eval'; $env:B1_PASSWORD = $pw; $env:PYTHONDONTWRITEBYTECODE = '1'
  git -C $W show origin/claude/c14-walkthrough-audit:legal_knowledge/audit_work/C14-WALKTHROUGH/scripts/search_eval.py | Set-Content -Encoding utf8 "$S\search_eval.py"
  & $py -I -B "$S\search_eval.py" "$S\walkthrough_queries.json" "$S\hyb-sample-$Mode.json" | Out-Null
  $env:B1_PID = $p.Id
  git -C $W show origin/claude/c14-walkthrough-audit:legal_knowledge/audit_work/C14-WALKTHROUGH/scripts/perf.py | Set-Content -Encoding utf8 "$S\perf.py"
  & $py -I -B "$S\perf.py" "$S\hyb-perf-$Mode.json" | Out-Null
  $mem = Invoke-RestMethod http://127.0.0.1:5442/api/diag/memory
  $phases = (Select-String -Path "$S\hyb-$Mode.log" -Pattern 'start-up phases: .*').Matches.Value
  [pscustomobject]@{ mode = $Mode; startup_s = [Math]::Round($startup, 1); phases = $phases; working_set_mb = $mem.working_set_mb; managed_heap_mb = $mem.managed_heap_mb } | ConvertTo-Json -Compress
} finally { Stop-Process -Id $p.Id -Force; Get-ChildItem Env:Mimamsa__* | Remove-Item; Remove-Item Env:B1_PASSWORD }
