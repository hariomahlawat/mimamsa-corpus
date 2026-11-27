<#  Install the Django PoC (hypercorn in pywin32 ServiceFramework) as a Windows Service under a virtual account.
    Usage (elevated): .\install-django-service.ps1 -AppDir C:\mimamsa\django -Python C:\Python312\python.exe -PdfRoot C:\mimamsa\pdfstore #>
param(
  [Parameter(Mandatory)] [string] $AppDir,
  [Parameter(Mandatory)] [string] $Python,
  [Parameter(Mandatory)] [string] $PdfRoot,
  [string] $Name = "MimamsaPocDjango",
  [string] $Bind = "127.0.0.1:5082",
  [string] $DbConnection = "host=127.0.0.1 port=5432 user=poc password=poc dbname=poc"
)
$ErrorActionPreference = "Stop"
Push-Location $AppDir
& $Python winservice.py --startup auto install
Pop-Location
$account = "NT SERVICE\$Name"
sc.exe config $Name obj= $account | Out-Host
sc.exe failure $Name reset= 60 actions= restart/2000/restart/2000/restart/2000 | Out-Host
sc.exe failureflag $Name 1 | Out-Host
$logDir = Join-Path $AppDir "logs"; New-Item -ItemType Directory -Force $logDir | Out-Null
# per-service environment block (REG_MULTI_SZ), read by the SCM when it starts the process
$envBlock = @("MIMAMSA_DB=$DbConnection", "MIMAMSA_PDF_ROOT=$PdfRoot", "MIMAMSA_BIND=$Bind", "MIMAMSA_LOG_DIR=$logDir",
              "MIMAMSA_SECRET_KEY=$([guid]::NewGuid().ToString('N'))")
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$Name" -Name Environment -PropertyType MultiString -Value $envBlock -Force | Out-Null
$pyDir = Split-Path $Python
icacls $AppDir /grant "${account}:(OI)(CI)RX" | Out-Host
icacls $logDir /grant "${account}:(OI)(CI)M" | Out-Host
icacls $pyDir /grant "${account}:(OI)(CI)RX" | Out-Host
icacls $PdfRoot /grant "${account}:(OI)(CI)R" | Out-Host
Start-Service $Name
