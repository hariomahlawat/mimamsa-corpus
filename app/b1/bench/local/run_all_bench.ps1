# C14 S4: run the scale benchmark matrix sequentially (numbers only; secrets read from files, never printed).
$W = 'E:\Dot Net Web Development\Mimamsa\.claude\worktrees\agent-a83e3eb3860d132e3'
$py = 'E:\Mimamsa-Data\venv\Scripts\python.exe'
$dll = "$W\app\b1\src\Mimamsa.Web\bin\Release\net10.0\Mimamsa.Web.dll"
$env:PGPASSWORD = Get-Content -Raw 'E:\Mimamsa-Data\secrets\pg_superuser.pw'
$env:MIMAMSA_APP_PW = Get-Content -Raw 'E:\Mimamsa-Data\secrets\pg_mimamsa.pw'
$out = 'E:\Mimamsa-Data\c14s4\bench'
New-Item -ItemType Directory -Force $out | Out-Null
$runs = @(
  @{ label = '290';   site = 'E:\Mimamsa-Data\sample\site';      gc = 'server' },
  @{ label = '1000';  site = 'E:\Mimamsa-Data\bench\1000\site';  gc = 'server' },
  @{ label = '4000';  site = 'E:\Mimamsa-Data\bench\4000\site';  gc = 'server' },
  @{ label = '10000'; site = 'E:\Mimamsa-Data\bench\10000\site'; gc = 'server' },
  @{ label = '4000';  site = 'E:\Mimamsa-Data\bench\4000\site';  gc = 'workstation' },
  @{ label = '4000';  site = 'E:\Mimamsa-Data\bench\4000\site';  gc = 'server-nodatas' }
)
foreach ($r in $runs) {
  $f = "$out\$($r.label)-$($r.gc).json"
  "$(Get-Date -Format HH:mm:ss) start $($r.label) $($r.gc)"
  & $py -I "$W\app\b1\bench\run_scale_bench.py" --site $r.site --label $r.label --gc $r.gc --dll $dll `
      --register 'E:\Mimamsa-Data\restricted_material.json' --port 5443 --out $f --cycles 5 2>&1 | Select-Object -Last 3
  "$(Get-Date -Format HH:mm:ss) done $($r.label) $($r.gc)"
}
Remove-Item Env:PGPASSWORD, Env:MIMAMSA_APP_PW
