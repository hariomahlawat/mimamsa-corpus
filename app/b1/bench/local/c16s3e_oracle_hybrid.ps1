# C16 S3-E: run the UNCHANGED retrieval oracle on the SYN site, hybrid off and/or on. Local helper (paths of this host).
# Derived from c15_oracle_hybrid.ps1; differences: disposable database c16s3e_oracle (dropped at the end), vector caches
# under E:\Mimamsa-Data\c16s3e, embedding threads bounded to half the CPUs, and any Mimamsa__Hybrid__* key passed in -Extra.
# Usage: c16s3e_oracle_hybrid.ps1 -Out <dir> [-Floor 0.8579] [-Extra @{ 'Mimamsa__Hybrid__X' = '...' }] [-OffToo] [-OnlyOff]
param([Parameter(Mandatory)][string]$Out, [string]$Floor = '0.8579', [hashtable]$Extra = @{}, [switch]$OffToo, [switch]$OnlyOff, [int]$Port = 5523,
      [string]$ModelDir = 'E:\Mimamsa-Data\models\multilingual-e5-small\614241f622f53c4eeff9890bdc4f31cfecc418b3',
      [string]$ModelSha = 'ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665',
      [string]$CacheDir = 'E:\Mimamsa-Data\c16s3e\vectors-syn')
$D = 'E:\Mimamsa-Data'; $W = (Resolve-Path "$PSScriptRoot\..\..\..\..").Path
$py = "$D\venv\Scripts\python.exe"; $app = (Get-Content -Raw "$D\secrets\pg_mimamsa.pw")
$psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
New-Item -ItemType Directory -Force $Out, $CacheDir | Out-Null
"oracle blob: " + (git -C $W hash-object app/b1/tests/oracles/run_retrieval_oracle.py) | Set-Content "$Out\oracle_identity.txt"
$threads = [Math]::Max(1, [int]([Environment]::ProcessorCount / 2))
function Db($sql) {
  $env:PGPASSWORD = Get-Content -Raw "$D\secrets\pg_superuser.pw"
  & $psql -h 127.0.0.1 -p 55499 -U mimamsa_su -d postgres -q -c $sql 2>&1 | Out-Null
  Remove-Item Env:PGPASSWORD
}
function Run($mode) {
  Db "DROP DATABASE IF EXISTS c16s3e_oracle WITH (FORCE);"; Db "CREATE DATABASE c16s3e_oracle OWNER mimamsa;"
  Remove-Item Env:Mimamsa__Hybrid__* -EA SilentlyContinue
  if ($mode -eq 'on') {
    $env:Mimamsa__Hybrid__Enabled = 'true'; $env:Mimamsa__Hybrid__ModelDir = $ModelDir; $env:Mimamsa__Hybrid__ModelSha256 = $ModelSha
    $env:Mimamsa__Hybrid__CacheDir = $CacheDir; $env:Mimamsa__Hybrid__MinSimilarity = $Floor; $env:Mimamsa__Hybrid__Threads = "$threads"
    foreach ($k in $Extra.Keys) { Set-Item "Env:$k" $Extra[$k] }
  }
  & $py -I -B "$W\app\b1\tests\b1server.py" --site "$D\syn\site" --port $Port --log "$Out\oracle-$mode.log" `
    --db "Host=127.0.0.1;Port=55499;Username=mimamsa;Password=$app;Database=c16s3e_oracle;Maximum Pool Size=10" `
    -- $py -I -B "$W\app\b1\tests\oracles\run_retrieval_oracle.py" --map "$D\syn\fixture_map.json" --out "$Out\$mode" 2>&1 | Select-String 'RET-|oracle:|REGRESSION' | Tee-Object "$Out\oracle-$mode.txt"
  Remove-Item Env:Mimamsa__Hybrid__* -EA SilentlyContinue
  Db "DROP DATABASE IF EXISTS c16s3e_oracle WITH (FORCE);"
}
if ($OffToo -or $OnlyOff) { "--- hybrid off"; Run 'off' }
if (-not $OnlyOff) { "--- hybrid on"; Run 'on' }
