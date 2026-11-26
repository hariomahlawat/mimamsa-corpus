# C14 S4: unchanged retrieval oracle on the SYN site, hybrid off vs hybrid on with the calibrated floor.
param([ValidateSet('off', 'floor')][string]$Mode)
$W = 'E:\Dot Net Web Development\Mimamsa\.claude\worktrees\agent-a83e3eb3860d132e3'
$py = 'E:\Mimamsa-Data\venv\Scripts\python.exe'
$D = 'E:\Mimamsa-Data\c14s4'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PGPASSWORD = Get-Content -Raw 'E:\Mimamsa-Data\secrets\pg_superuser.pw'
$app = Get-Content -Raw 'E:\Mimamsa-Data\secrets\pg_mimamsa.pw'
$psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
& $psql -h 127.0.0.1 -p 55499 -U mimamsa_su -d postgres -q -c "DROP DATABASE IF EXISTS c14s4_oracle WITH (FORCE);" -c "CREATE DATABASE c14s4_oracle OWNER mimamsa;"
Remove-Item Env:PGPASSWORD
$env:MIMAMSA_REGISTER = 'E:\Mimamsa-Data\restricted_material.json'
if ($Mode -eq 'floor') {
  $env:Mimamsa__Hybrid__Enabled = 'true'
  $env:Mimamsa__Hybrid__ModelDir = 'E:\Mimamsa-Data\models\multilingual-e5-small\614241f622f53c4eeff9890bdc4f31cfecc418b3'
  $env:Mimamsa__Hybrid__ModelSha256 = 'ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665'
  $env:Mimamsa__Hybrid__CacheDir = "$D\embcache"
  $env:Mimamsa__Hybrid__MinSimilarity = '0.8579'
}
$out = "$D\oracle-$Mode"
Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue
& $py -I -B "$W\app\b1\tests\b1server.py" --site 'E:\Mimamsa-Data\syn\site' --port 5441 --log "$D\oracle-$Mode.log" `
    --dll "$W\app\b1\src\Mimamsa.Web\bin\Release\net10.0\Mimamsa.Web.dll" `
    --db "Host=127.0.0.1;Port=55499;Username=mimamsa;Password=$app;Database=c14s4_oracle;Maximum Pool Size=10" `
    -- $py -I -B "$W\app\b1\tests\oracles\run_retrieval_oracle.py" --map 'E:\Mimamsa-Data\syn\fixture_map.json' --out $out 2>&1 | Select-Object -Last 18
