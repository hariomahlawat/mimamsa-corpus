# C15 S2: run the UNCHANGED retrieval oracle on the SYN site with hybrid off and on. Local helper (paths of this host).
# Usage: c15_oracle_hybrid.ps1 -Out <dir> [-Floor 0.8579] [-Extra @{ 'Mimamsa__Hybrid__X' = '...' }] [-OffToo]
param([Parameter(Mandatory)][string]$Out, [string]$Floor = '0.8579', [hashtable]$Extra = @{}, [switch]$OffToo, [int]$Port = 5522,
      [string]$ModelDir = 'E:\Mimamsa-Data\models\multilingual-e5-small\614241f622f53c4eeff9890bdc4f31cfecc418b3',
      [string]$ModelSha = 'ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665')
$D = 'E:\Mimamsa-Data'; $W = (Resolve-Path "$PSScriptRoot\..\..\..\..").Path
$py = "$D\venv\Scripts\python.exe"; $app = (Get-Content -Raw "$D\secrets\pg_mimamsa.pw")
New-Item -ItemType Directory -Force $Out | Out-Null
"oracle blob: " + (git -C $W hash-object app/b1/tests/oracles/run_retrieval_oracle.py) | Set-Content "$Out\oracle_identity.txt"
function Run($mode) {
  $env:PGPASSWORD = Get-Content -Raw "$D\secrets\pg_superuser.pw"
  & 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h 127.0.0.1 -p 55499 -U mimamsa_su -d postgres -q -c "DROP DATABASE IF EXISTS c15s2_oracle WITH (FORCE);" -c "CREATE DATABASE c15s2_oracle OWNER mimamsa;" 2>&1 | Out-Null
  Remove-Item Env:PGPASSWORD
  Remove-Item Env:Mimamsa__Hybrid__* -EA SilentlyContinue
  if ($mode -eq 'on') {
    $env:Mimamsa__Hybrid__Enabled = 'true'; $env:Mimamsa__Hybrid__ModelDir = $ModelDir; $env:Mimamsa__Hybrid__ModelSha256 = $ModelSha
    $env:Mimamsa__Hybrid__CacheDir = "$D\c15s2\vectors-syn"; $env:Mimamsa__Hybrid__MinSimilarity = $Floor
    foreach ($k in $Extra.Keys) { Set-Item "Env:$k" $Extra[$k] }
  }
  & $py -I -B "$W\app\b1\tests\b1server.py" --site "$D\syn\site" --port $Port --log "$Out\oracle-$mode.log" `
    --db "Host=127.0.0.1;Port=55499;Username=mimamsa;Password=$app;Database=c15s2_oracle;Maximum Pool Size=10" `
    -- $py -I -B "$W\app\b1\tests\oracles\run_retrieval_oracle.py" --map "$D\syn\fixture_map.json" --out "$Out\$mode" 2>&1 | Select-String 'RET-|oracle:' | Tee-Object "$Out\oracle-$mode.txt"
  Remove-Item Env:Mimamsa__Hybrid__* -EA SilentlyContinue
}
if ($OffToo) { "--- hybrid off"; Run 'off' }
"--- hybrid on"; Run 'on'
