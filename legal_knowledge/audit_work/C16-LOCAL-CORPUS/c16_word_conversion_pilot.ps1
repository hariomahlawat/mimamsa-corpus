param(
    [Parameter(Mandatory=$true)][string]$Inventory,
    [Parameter(Mandatory=$true)][string]$OcrRegister,
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$Output,
    [int]$Count = 50
)

$ErrorActionPreference = 'Stop'
$wdFormatPDF = 17
$wdExportOptimizeForPrint = 0
$wdExportAllDocument = 0
$wdExportDocumentContent = 0
$wdExportCreateHeadingBookmarks = 1
$wdDoNotSaveChanges = 0
$msoAutomationSecurityForceDisable = 3

New-Item -ItemType Directory -Force $Output | Out-Null
$pdfRoot = Join-Path $Output 'pdf'
New-Item -ItemType Directory -Force $pdfRoot | Out-Null

$ocr = @{}
Get-Content -LiteralPath $OcrRegister | ForEach-Object {
    if ($_.Trim()) {
        $row = $_ | ConvertFrom-Json
        $ocr[$row.image_sha256] = $row
    }
}

$eligible = Get-Content -LiteralPath $Inventory | ForEach-Object {
    if (-not $_.Trim()) { return }
    $row = $_ | ConvertFrom-Json
    if ($row.extension -ne '.docx' -or $row.restricted -or $row.parsing_error) { return }
    $screened = $true
    foreach ($image in @($row.embedded_images)) {
        $result = $ocr[$image.image_sha256]
        if ($null -eq $result -or $result.state -ne 'COMPLETE' -or
            $result.access_disposition -ne 'SCREENED_NO_MARKING_DETECTED') {
            $screened = $false
            break
        }
    }
    if ($screened) { $row }
}

# Deterministic round-robin across first-level subjects and image/no-image
# classes. Source hashes provide stable tie-breaking.
$groups = $eligible | Group-Object {
    $subject = if ($_.original_folder_classification.Count) { $_.original_folder_classification[0] } else { '_ROOT' }
    $kind = if ($_.embedded_image_count -gt 0) { 'WITH_IMAGES' } else { 'NATIVE_ONLY' }
    "$subject|$kind"
} | Sort-Object Name
$queues = @($groups | ForEach-Object { ,@($_.Group | Sort-Object sha256) })
$selected = [System.Collections.Generic.List[object]]::new()
$index = 0
while ($selected.Count -lt $Count) {
    $added = $false
    for ($groupIndex = 0; $groupIndex -lt $queues.Count -and $selected.Count -lt $Count; $groupIndex++) {
        if ($index -lt $queues[$groupIndex].Count) {
            $selected.Add($queues[$groupIndex][$index])
            $added = $true
        }
    }
    if (-not $added) { break }
    $index++
}

$word = $null
$wordVersion = $null
$results = [System.Collections.Generic.List[object]]::new()
try {
    $word = New-Object -ComObject Word.Application
    $wordVersion = [string]$word.Version
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = $msoAutomationSecurityForceDisable
    $word.Options.UpdateLinksAtOpen = $false
    foreach ($row in $selected) {
        $sourcePath = Join-Path $Source ([string]$row.relative_path).Replace('/', '\')
        $destination = Join-Path $pdfRoot ($row.sha256 + '.pdf')
        $started = Get-Date
        $status = 'ERROR'
        $errorText = $null
        $document = $null
        try {
            $actualSourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToLowerInvariant()
            if ($actualSourceHash -ne $row.sha256) { throw 'source hash mismatch before conversion' }
            $document = $word.Documents.Open($sourcePath, $false, $true)
            $document.ExportAsFixedFormat($destination, $wdFormatPDF, $false, $wdExportOptimizeForPrint,
                $wdExportAllDocument, 1, 1, $wdExportDocumentContent, $false,
                $wdExportCreateHeadingBookmarks, $false, $true, $true, $false)
            $status = 'CONVERTED_LOCAL_RECONSTRUCTION'
        } catch {
            $errorText = $_.Exception.Message
        } finally {
            if ($null -ne $document) {
                $document.Close($wdDoNotSaveChanges)
                [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)
            }
        }
        $elapsed = ((Get-Date) - $started).TotalSeconds
        $pdf = if (Test-Path -LiteralPath $destination) { Get-Item -LiteralPath $destination } else { $null }
        $results.Add([ordered]@{
            inventory_id = $row.inventory_id
            relative_path = $row.relative_path
            source_sha256 = $row.sha256
            source_bytes = [long]$row.size_bytes
            embedded_image_count = [int]$row.embedded_image_count
            status = $status
            representation = 'LOCALLY_RECONSTRUCTED_REFERENCE_COPY'
            pdf_relative_path = if ($pdf) { 'pdf/' + $pdf.Name } else { $null }
            pdf_sha256 = if ($pdf) { (Get-FileHash -Algorithm SHA256 -LiteralPath $pdf.FullName).Hash.ToLowerInvariant() } else { $null }
            pdf_bytes = if ($pdf) { $pdf.Length } else { $null }
            duration_seconds = [math]::Round($elapsed, 3)
            error = $errorText
        })
    }
} finally {
    if ($null -ne $word) {
        $word.Quit($wdDoNotSaveChanges)
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)
    }
}

$manifest = Join-Path $Output 'PDF_CONVERSION_MANIFEST.jsonl'
$results | ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 8 } | Set-Content -LiteralPath $manifest -Encoding utf8NoBOM
$converted = @($results | Where-Object status -eq 'CONVERTED_LOCAL_RECONSTRUCTION')
$originalBytes = [long](($converted | ForEach-Object { [long]$_['source_bytes'] } | Measure-Object -Sum).Sum)
$convertedBytes = [long](($converted | ForEach-Object { [long]$_['pdf_bytes'] } | Measure-Object -Sum).Sum)
$duration = (($results | ForEach-Object { [double]$_['duration_seconds'] } | Measure-Object -Sum).Sum)
$summary = [ordered]@{
    selected = $selected.Count
    converted = $converted.Count
    failed = $results.Count - $converted.Count
    original_bytes = $originalBytes
    converted_pdf_bytes = $convertedBytes
    compression_ratio = if ($originalBytes) { [math]::Round($convertedBytes / $originalBytes, 6) } else { $null }
    total_duration_seconds = [math]::Round($duration, 3)
    word_version = $wordVersion
    macros = 'FORCE_DISABLED'
    external_link_updates = 'DISABLED'
    representation = 'LOCALLY_RECONSTRUCTED_REFERENCE_COPY'
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Output 'PDF_CONVERSION_SUMMARY.json') -Encoding utf8NoBOM
