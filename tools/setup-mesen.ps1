$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$coreRoot = Join-Path $projectRoot '.tools/mesen'
$archivePath = Join-Path $coreRoot 'mesen-s_libretro.dll.zip'
$corePath = Join-Path $coreRoot 'mesen-s_libretro.dll'
$url = 'https://buildbot.libretro.com/nightly/windows/x86_64/latest/mesen-s_libretro.dll.zip'
$archivePin = '3BC041CE07F5645602AAC9CF6682DF12FF8941E6231AA621C5B2332FAB96D754'
$dllPin = '87A90F31C331313C4F499D6DFAFB59F7911BC60DBB9E10B5D96F959040441ABD'

New-Item -ItemType Directory -Force -Path $coreRoot | Out-Null
if (-not (Test-Path -LiteralPath $archivePath) -or
    (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash -ne $archivePin) {
    $downloadPath = Join-Path $coreRoot 'mesen-s_libretro.dll.zip.download'
    & curl.exe -L --fail --silent --show-error $url -o $downloadPath
    if ($LASTEXITCODE -ne 0) { throw 'Official Mesen-S download failed.' }
    $actual = (Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash
    if ($actual -ne $archivePin) {
        throw "Rolling buildbot archive changed; expected $archivePin, got $actual. No core was installed."
    }
    Copy-Item -LiteralPath $downloadPath -Destination $archivePath -Force
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
try {
    if ($zip.Entries.Count -ne 1 -or $zip.Entries[0].FullName -ne 'mesen-s_libretro.dll') {
        throw 'Pinned Mesen-S archive contains unexpected entries.'
    }
    $stream = $zip.Entries[0].Open()
    try {
        $memory = [System.IO.MemoryStream]::new()
        $stream.CopyTo($memory)
        $bytes = $memory.ToArray()
    } finally { $stream.Dispose() }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $actual = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '') }
    finally { $sha.Dispose(); $memory.Dispose() }
    if ($actual -ne $dllPin) { throw "Mesen-S archive member hash mismatch: $actual" }
    [System.IO.File]::WriteAllBytes($corePath, $bytes)
} finally { $zip.Dispose() }

Write-Host "Pinned Mesen-S core ready: $corePath"
Write-Host "Archive SHA256: $archivePin"
Write-Host "DLL SHA256: $dllPin"
Write-Host 'No emulator window or audio device was opened.'
