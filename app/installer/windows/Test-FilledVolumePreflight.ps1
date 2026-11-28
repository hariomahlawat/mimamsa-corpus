<#
C16 S3-C (B07, FG-DISK-PREFLIGHT mechanism): the measured disk preflight refuses on a deliberately FILLED volume and accepts
once space is freed, with the record showing the measured values. CI only (Administrator): a small fixed VHDX is created,
formatted and mounted with diskpart, filled with fsutil, and detached and deleted at the end.
  Test-FilledVolumePreflight.ps1 -ActivationPublish <dir> -Work <dir> -Out <dir>
#>
[CmdletBinding()]
param([Parameter(Mandatory)] [string] $ActivationPublish, [Parameter(Mandatory)] [string] $Work, [Parameter(Mandatory)] [string] $Out)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force $Work, $Out | Out-Null
$vhd = Join-Path $Work 's3c-fill.vhdx'
$used = (Get-PSDrive -PSProvider FileSystem).Name
$letter = ('S', 'T', 'U', 'V', 'W', 'X', 'Y', 'R', 'Q', 'P') | Where-Object { $_ -notin $used } | Select-Object -First 1
@"
create vdisk file="$vhd" maximum=128 type=fixed
select vdisk file="$vhd"
attach vdisk
create partition primary
format fs=ntfs quick label=S3CFILL
assign letter=$letter
"@ | Set-Content -Encoding ASCII (Join-Path $Work 'dp-create.txt')
diskpart /s (Join-Path $Work 'dp-create.txt') | Out-File -Encoding utf8 (Join-Path $Out 'diskpart-create.txt')
if (-not (Test-Path "${letter}:\")) { throw "the test volume was not mounted" }
try {
    $tool = Join-Path $ActivationPublish 'Mimamsa.Activation.exe'
    $roots = [ordered]@{}
    foreach ($k in @('application', 'site', 'text_store', 'search_index', 'vectors', 'uploads', 'config', 'backup', 'logs', 'import', 'scratch')) { $roots[$k] = "${letter}:\Mimamsa\$($k -replace '_','-')" }
    $cfg = Join-Path $Work 'install-filled.json'
    @{ format = 'mimamsa-dev-install/1'; mode = 'test'; roots = $roots; headroom_fraction = 0.1; retention = @{ keep_previous = 2 } } | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $cfg
    # a 40 MiB payload to land on the test volume
    $payload = Join-Path $Work 'payload'; New-Item -ItemType Directory -Force $payload | Out-Null
    fsutil file createnew (Join-Path $payload 'release.bin') 41943040 | Out-Null
    # fill the volume, leaving ~20 MiB free (less than 40 MiB * 1.1)
    $free = (Get-PSDrive $letter).Free
    fsutil file createnew "${letter}:\filler.bin" ([int64]($free - 20MB)) | Out-Null
    $o1 = & $tool install-layout --config $cfg --payload "release=import=$payload" | Select-Object -Last 1
    $c1 = $LASTEXITCODE
    $o1 | Out-File -Encoding utf8 (Join-Path $Out 'preflight-filled.json')
    $r1 = $o1 | ConvertFrom-Json
    if ($c1 -ne 2 -or $r1.code -ne 'PREFLIGHT_FAILED') { throw "preflight did not refuse on the filled volume: $o1" }
    if (Test-Path "${letter}:\Mimamsa\site") { throw "a refused install wrote the layout" }
    $vol = $r1.preflight.volumes | Where-Object { $_.volume -eq "${letter}:\" }
    if (-not $vol -or $vol.required_bytes -le $vol.free_bytes -or $vol.measured_payload_bytes -ne 41943040) { throw "the record does not show the measured values: $o1" }
    Remove-Item "${letter}:\filler.bin" -Force
    $o2 = & $tool install-layout --config $cfg --payload "release=import=$payload" | Select-Object -Last 1
    $c2 = $LASTEXITCODE
    $o2 | Out-File -Encoding utf8 (Join-Path $Out 'preflight-freed.json')
    if ($c2 -ne 0) { throw "preflight did not accept after space was freed: $o2" }
    if (-not (Test-Path "${letter}:\Mimamsa\site\journal")) { throw "layout missing after the accepted install" }
    "filled-volume preflight: refused ($($vol.free_bytes) free < $($vol.required_bytes) required), accepted after freeing"
}
finally {
    @"
select vdisk file="$vhd"
detach vdisk
"@ | Set-Content -Encoding ASCII (Join-Path $Work 'dp-detach.txt')
    diskpart /s (Join-Path $Work 'dp-detach.txt') | Out-File -Encoding utf8 (Join-Path $Out 'diskpart-detach.txt')
    Remove-Item $vhd -Force -ErrorAction SilentlyContinue
}
