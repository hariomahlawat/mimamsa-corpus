<#
C16 S3-C (B07): DEVELOPMENT/TEST uninstaller. Removes the services (and with them the virtual accounts), the firewall rule
and the application binaries. It PRESERVES every site data root, the vault, the generations and the append-only stores
(journal, activation log, exclusions): architecture section 10, plan B07 "Uninstall preserves site data".
  Uninstall-MimamsaDev.ps1 -Config <install.json>
#>
[CmdletBinding()]
param([Parameter(Mandatory)] [string] $Config)
$ErrorActionPreference = 'Stop'
$cfg = Get-Content -Raw $Config | ConvertFrom-Json
$R = $cfg.roots
$web = if ($cfg.identities.web) { $cfg.identities.web } else { 'MimamsaWeb' }
$act = if ($cfg.identities.activation) { $cfg.identities.activation } else { 'MimamsaActivation' }
foreach ($s in @($web, $act)) {
    if (Get-Service -Name $s -ErrorAction SilentlyContinue) {
        Stop-Service -Name $s -Force -ErrorAction SilentlyContinue
        sc.exe delete $s | Out-Null
    }
}
Get-NetFirewallRule -Group 'Mimamsa' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
foreach ($d in @('web', 'activation')) {
    $p = Join-Path $R.application $d
    if (Test-Path $p) { Remove-Item -Recurse -Force $p }
}
$kept = foreach ($k in @('site', 'text_store', 'search_index', 'vectors', 'import', 'uploads', 'config', 'backup', 'logs')) { "$k=$($R.$k)" }
"uninstalled services and binaries; preserved: " + ($kept -join '; ')
