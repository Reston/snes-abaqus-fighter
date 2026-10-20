$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$compatRoot = Join-Path $projectRoot '.tools/compat'
$archiveName = 'bsnes2014_accuracy_libretro.dll.zip'
$archivePath = Join-Path $compatRoot $archiveName
$downloadPath = Join-Path $compatRoot ($archiveName + '.download')
$coreDirectory = Join-Path $compatRoot 'bsnes2014-accuracy'
$corePath = Join-Path $coreDirectory 'bsnes2014_accuracy_libretro.dll'
$url = 'https://buildbot.libretro.com/nightly/windows/x86_64/latest/bsnes2014_accuracy_libretro.dll.zip'
$expectedArchiveHash = 'CB1211AE6B6838ED60BEB7CC8AE5AD8074327733F1042CCC8BABA32A62C6D18C'
$expectedDllHash = 'F2AAC1DDB314A001467A26B56604020F0A29C3A4DD1658B072884ACE75343CF4'

New-Item -ItemType Directory -Force -Path $compatRoot | Out-Null
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "Downloading pinned official Libretro core archive..."
& curl.exe -L --fail --silent --show-error $url -o $downloadPath
if ($LASTEXITCODE -ne 0) {
    throw "Could not download the official bsnes2014 Accuracy archive."
}

$archiveHash = (Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash.ToUpperInvariant()
if ($archiveHash -ne $expectedArchiveHash) {
    throw "Pinned bsnes2014 archive SHA256 mismatch. The rolling buildbot URL changed: expected $expectedArchiveHash, got $archiveHash."
}
Copy-Item -LiteralPath $downloadPath -Destination $archivePath -Force

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $archivePath))
try {
    $files = @($zip.Entries | Where-Object { -not $_.FullName.EndsWith('/') })
    if ($files.Count -ne 1 -or $files[0].FullName -ne 'bsnes2014_accuracy_libretro.dll') {
        throw "Pinned archive contains an unexpected file list."
    }
}
finally {
    $zip.Dispose()
}

New-Item -ItemType Directory -Force -Path $coreDirectory | Out-Null
Expand-Archive -LiteralPath $archivePath -DestinationPath $coreDirectory -Force
if (-not (Test-Path -LiteralPath $corePath)) {
    throw "Pinned archive did not extract bsnes2014_accuracy_libretro.dll."
}
$dllHash = (Get-FileHash -LiteralPath $corePath -Algorithm SHA256).Hash.ToUpperInvariant()
if ($dllHash -ne $expectedDllHash) {
    throw "Extracted bsnes2014 DLL SHA256 mismatch: expected $expectedDllHash, got $dllHash."
}

Write-Host "Pinned independent core is ready: $corePath"
Write-Host "Archive SHA256: $archiveHash"
Write-Host "DLL SHA256: $dllHash"
Write-Host "No GUI executable was launched. Run the silent test with the project-local Python host."
