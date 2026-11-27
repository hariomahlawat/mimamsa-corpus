param([string]$W, [string]$Out)
Set-Location $W
$D='E:\Mimamsa-Data'
$bench = (Get-ChildItem app/b1/bench/IndexBench/bin/Release -Recurse -Filter IndexBench.dll | Select -First 1).FullName
$rows = @()
foreach($s in @(@('290-real', "$D\sample\site"), @('10k-synthetic', "$D\bench\c16r\10000\site"))){
  $name=$s[0]; $site=$s[1]; $st="$D\c16int\startup\$name"
  Remove-Item -Recurse -Force $st -EA SilentlyContinue; New-Item -ItemType Directory -Force $st | Out-Null
  $runs = @(@('memory-baseline','memory','memory',$false), @('disk-cold-build','disk','disk',$false), @('disk-warm-reopen-1','disk','disk',$false), @('disk-warm-reopen-2','disk','disk',$false))
  foreach($r in $runs){
    $label=$r[0]; $txt=$r[1]; $eng=$r[2]
    $args=@($bench,'--site',$site,'--engine',$eng,'--build-only')
    if($eng -eq 'disk'){ $args += @('--index-dir',"$st\index") }
    if($txt -eq 'disk'){ $args += @('--text-store','disk','--text-dir',"$st\text") }
    $sw=[Diagnostics.Stopwatch]::StartNew()
    $o = & dotnet @args 2>"$st\$label.err"
    $wall=$sw.ElapsedMilliseconds
    $j = ($o -join "`n") | ConvertFrom-Json
    $bind = (Select-String -Path "$st\$label.err" -Pattern 'bound (\d+) documents .* in (\d+) ms' | Select -First 1)
    $built = (Select-String -Path "$st\$label.err" -Pattern 'text store: built and published' | Measure-Object).Count
    $rows += [pscustomobject]@{ site=$name; run=$label; text=$txt; engine=$eng; process_wall_ms=$wall; load_ms=$j.load_ms; index_ms=$j.index_ms;
      bind_ms= if($bind){ [int]$bind.Matches[0].Groups[2].Value } else { $null }; text_store_built=($built -gt 0);
      heap_mb=$j.mem_after_index.managed_heap_mb; working_set_mb=$j.mem_after_index.working_set_mb; documents=$j.documents; passages=$j.passages }
  }
  "text.sqlite MB: " + [math]::Round((Get-ChildItem -Recurse "$st\text" -Filter text.sqlite | Measure-Object Length -Sum).Sum/1MB,1) | Out-File -Append "$Out.txt"
}
$rows | ConvertTo-Json | Set-Content $Out
$rows | Format-Table site,run,load_ms,bind_ms,index_ms,process_wall_ms,heap_mb,working_set_mb -AutoSize | Out-String -Width 200
