<#  Install MimamsaPocApi (Kestrel) as a Windows Service under a virtual service account.
    Usage (elevated): .\install-aspnet-service.ps1 -PublishDir C:\mimamsa\aspnet -PdfRoot C:\mimamsa\pdfstore  #>
param(
  [Parameter(Mandatory)] [string] $PublishDir,
  [Parameter(Mandatory)] [string] $PdfRoot,
  [string] $Name = "MimamsaPocApi",
  [string] $Url = "http://127.0.0.1:5081",
  [string] $DbConnection = "Host=127.0.0.1;Port=5432;Username=poc;Password=poc;Database=poc;Maximum Pool Size=32"
)
$ErrorActionPreference = "Stop"
$exe = Join-Path $PublishDir "MimamsaPocApi.exe"
if (-not (Test-Path $exe)) { throw "missing $exe" }
@{ Urls = $Url; Mimamsa = @{ Db = $DbConnection; PdfRoot = $PdfRoot; DevToken = "dev-token" } } |
  ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $PublishDir "appsettings.Production.json")
$account = "NT SERVICE\$Name"
sc.exe create $Name binPath= "`"$exe`"" start= auto obj= $account DisplayName= "Mimamsa PoC API (ASP.NET Core)" | Out-Host
sc.exe description $Name "Mimamsa offline research platform: ASP.NET Core PoC service." | Out-Host
# restart on crash: 3 attempts, 2 s apart; failure counter resets after 60 s
sc.exe failure $Name reset= 60 actions= restart/2000/restart/2000/restart/2000 | Out-Host
sc.exe failureflag $Name 1 | Out-Host
# least privilege: read+execute on binaries, read on PDFs; nothing else
icacls $PublishDir /grant "${account}:(OI)(CI)RX" | Out-Host
icacls $PdfRoot /grant "${account}:(OI)(CI)R" | Out-Host
[Environment]::SetEnvironmentVariable("ASPNETCORE_ENVIRONMENT", "Production", "Machine")
Start-Service $Name
